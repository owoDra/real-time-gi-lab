// Opt-in independent GPU pixel path tracer for the N010 comparison pilot.
#include "b002_hwrt.hpp"
#include "i001_compute.hpp"
#include "a001_runtime.hpp"
#include "allocation_ledger.hpp"
#include "vk_init.hpp"
#include <array>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <optional>
#include <stdexcept>
#include <vector>
namespace fs=std::filesystem;
namespace b=phos::gi::research::lane_b;
namespace i=phos::gi::research::integration;
namespace a=phos::gi::lane_a;
namespace n=phos::gi::research::n010;
using Clock=std::chrono::steady_clock;
template<class T> T read(std::ifstream& f) {
    T value{}; f.read(reinterpret_cast<char*>(&value),sizeof(T));
    if(!f) throw std::runtime_error("truncated state");
    return value;
}
void check(VkResult result) { if(result!=VK_SUCCESS) throw std::runtime_error("Vulkan operation failed"); }
struct State {
    std::vector<b::Triangle> triangles;
    a::A001ParamsGpu params{};
    uint32_t width{},height{};
};
State load_state(const fs::path& state) {
    State result;
    std::ifstream geometry(state/"geometry-state.bin",std::ios::binary);
    if(read<uint32_t>(geometry)!=1) throw std::runtime_error("state version");
    auto count=read<uint32_t>(geometry);
    if(count==0||fs::file_size(state/"geometry-state.bin")!=8+uint64_t(count)*52)
        throw std::runtime_error("invalid geometry state");
    result.triangles.resize(count);
    for(auto& t:result.triangles) {
        t.v0=read<b::Vec3>(geometry);t.v1=read<b::Vec3>(geometry);t.v2=read<b::Vec3>(geometry);
        t.primitive_id=read<uint32_t>(geometry);t.material_id=read<uint32_t>(geometry);
        t.instance_id=read<uint32_t>(geometry);t.two_sided=read<uint32_t>(geometry)!=0;
        if(!t.two_sided) throw std::runtime_error("BF-P requires two-sided geometry");
    }
    std::ifstream frame(state/"frame-state.bin",std::ios::binary);
    char magic[12]{};frame.read(magic,12);
    if(std::memcmp(magic,"N007-STATE1\0",12)!=0||fs::file_size(state/"frame-state.bin")!=148)
        throw std::runtime_error("invalid frame state");
    result.width=read<uint32_t>(frame);result.height=read<uint32_t>(frame);
    result.params=read<a::A001ParamsGpu>(frame);
    if(result.width!=result.params.counts[1]||result.height!=result.params.counts[2])
        throw std::runtime_error("frame shape");
    return result;
}
void copy_state(const fs::path& state,const fs::path& out) {
    fs::create_directories(out);
    for(const auto* name:{"geometry-state.bin","frame-state.bin"})
        fs::copy_file(state/name,out/name);
}
void pfm(const fs::path& path,uint32_t w,uint32_t h,const std::vector<float>& image,size_t component) {
    std::ofstream f(path,std::ios::binary);
    f<<"PF\n"<<w<<" "<<h<<"\n-1.0\n";
    for(uint32_t y=h;y-->0;) for(uint32_t x=0;x<w;++x) {
        float v=image[4*(size_t(y)*w+x)+component];
        const float rgb[]{v,v,v}; f.write(reinterpret_cast<const char*>(rgb),sizeof(rgb));
    }
    if(!f) throw std::runtime_error("PFM write failed");
}
int main(int argc,char** argv) {
    try {
        fs::path state,target_path,out; uint32_t spp=16,vertices=2,seed=0x13579bdfu,frames=1;
        std::string family="pixel-pt";
        for(int k=1;k<argc;++k) {
            std::string arg=argv[k];
            if(k+1>=argc) throw std::runtime_error("missing argument value");
            const std::string value=argv[++k];
            if(arg=="--state") state=value;
            else if(arg=="--target-state") target_path=value;
            else if(arg=="--out") out=value;
            else if(arg=="--spp") spp=std::stoul(value);
            else if(arg=="--vertices") vertices=std::stoul(value);
            else if(arg=="--seed") seed=std::stoul(value);
            else if(arg=="--frames") frames=std::stoul(value);
            else if(arg=="--family") family=value;
            else throw std::runtime_error("unknown option "+arg);
        }
        if(state.empty()||out.empty()||spp==0||spp>16384||
           (family!="pixel-pt"&&family!="dense-rc")||(family=="dense-rc"&&spp!=1)||
           (vertices!=1&&vertices!=2&&vertices!=8)||frames==0||frames>256)
            throw std::runtime_error("required --state DIR --out NEWDIR; bounded spp/vertices/frames");
        if(!target_path.empty()&&frames<2) throw std::runtime_error("transition requires source and target frames");
        if(fs::exists(out)) throw std::runtime_error("refuse to overwrite output directory");
        fs::create_directories(out);
        n::LedgerOutput ledger(out/"allocation-ledger.json");
        auto source=load_state(state);
        auto& triangles=source.triangles;
        auto width=source.width,height=source.height;
        auto params=source.params;
        std::optional<State> target;
        if(!target_path.empty()) {
            target=load_state(target_path);
            if(target->width!=width||target->height!=height||target->triangles.size()!=triangles.size())
                throw std::runtime_error("pilot transitions require fixed resolution and primitive slot count");
        }
        copy_state(target ? target_path : state,out);
        const auto setup_start=Clock::now();
        b::B002VulkanContext context(false,b::kB002TargetDeviceName,true);
        b::B002HwrtTraversal hwrt(context,triangles,"",false);
        auto uniform=context.upload_device_buffer(&params,sizeof(params),VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT);
        auto image=context.create_device_buffer(VkDeviceSize(width)*height*16,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        const std::array<i::I001Binding,4> bindings{{
            {0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&image},
            {1,VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,nullptr,hwrt.top_level()},
            {2,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&hwrt.triangle_buffer()},
            {3,VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,&uniform}}};
        i::I001ComputeStage stage(context,std::string(PHOS_GI_INTEGRATION_SHADER_DIR)+
                                 (family=="pixel-pt"?"/n010_pixel_pt.spv":"/n010_dense_rc.spv"),bindings,16);
        auto pool_info=phos::gi::detail::make_vk_info<VkCommandPoolCreateInfo>(VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
        pool_info.queueFamilyIndex=context.queue_family(); pool_info.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        VkCommandPool pool{}; check(context.vk().createCommandPool(&pool_info,nullptr,&pool));
        auto alloc=phos::gi::detail::make_vk_info<VkCommandBufferAllocateInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
        alloc.commandPool=pool;alloc.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;alloc.commandBufferCount=1;
        VkCommandBuffer command{};check(context.vk().allocateCommandBuffers(&alloc,&command));
        auto qi=phos::gi::detail::make_vk_info<VkQueryPoolCreateInfo>(VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
        qi.queryType=VK_QUERY_TYPE_TIMESTAMP;qi.queryCount=2;
        VkQueryPool query{};check(context.vk().createQueryPool(&qi,nullptr,&query));
        auto fi=phos::gi::detail::make_vk_info<VkFenceCreateInfo>(VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
        VkFence fence{};check(context.vk().createFence(&fi,nullptr,&fence));
        double setup_wall=std::chrono::duration<double,std::micro>(Clock::now()-setup_start).count();
        std::ofstream times(out/"frames.json");times<<std::setprecision(17);
        times<<"{\"schema\":\"n010-pixel-pt/1\",\"timing_classification\":\"DIAGNOSTIC_UNCALIBRATED\","
             <<"\"boundary\":\"complete pixel Renderer: uniform/geometry uploads + BLAS/TLAS UPDATE + primary/NEE/all bounces/composite; initial setup/readback separate\","
             <<"\"family\":\""<<family<<"\",\"spp\":"<<spp<<",\"vertices\":"<<vertices<<",\"seed\":"<<seed
             <<",\"setup_wall_us\":"<<setup_wall<<",\"timestamp_period_ns\":"<<context.timestamp_period_ns()
             <<",\"width\":"<<width<<",\"height\":"<<height<<",\"frames\":[";
        for(uint32_t f=0;f<frames;++f) {
            const std::string label=(target ? (f==0 ? "source" : (f==1 ? "first-target" : "recovery")) : "static");
            n::AllocationLedger::instance().phase("frame-"+label+"-"+std::to_string(f));
            const auto start=Clock::now();
            double maintenance_gpu=0,blas=0,tlas=0,uniform_gpu=0,geometry_gpu=0;
            size_t changed_count=0;
            if(target&&f==1) {
                std::vector<uint32_t> changed;
                for(size_t index=0;index<triangles.size();++index) {
                    const auto old=b::to_gpu_triangle(triangles[index]),next=b::to_gpu_triangle(target->triangles[index]);
                    if(std::memcmp(&old,&next,sizeof(old))!=0) changed.push_back(uint32_t(index));
                }
                changed_count=changed.size();
                if(!changed.empty()) {
                    const auto update=hwrt.update_geometry(target->triangles,changed);
                    blas=update.blas_update_us;tlas=update.tlas_update_us;geometry_gpu=update.geometry_upload_gpu_us;
                    maintenance_gpu+=blas+tlas+geometry_gpu;
                }
                params=target->params;
                const b::B002BufferUpdate update{0,&params,sizeof(params)};
                uniform_gpu=context.update_device_buffer_timed(uniform,std::span(&update,1));
                maintenance_gpu+=uniform_gpu;
            }
            check(context.vk().resetFences(1,&fence));check(context.vk().resetCommandPool(pool,0));
            auto begin=phos::gi::detail::make_vk_info<VkCommandBufferBeginInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
            begin.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;check(context.vk().beginCommandBuffer(command,&begin));
            context.vk().cmdResetQueryPool(command,query,0,2);
            context.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);
            const std::array<uint32_t,4> push{spp,vertices,seed+f,0};
            stage.record(command,(width+7)/8,(height+7)/8,1,push.data(),sizeof(push));
            i::i001_compute_barrier(context,command);
            context.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,1);
            check(context.vk().endCommandBuffer(command));
            auto submit=phos::gi::detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
            submit.commandBufferCount=1;submit.pCommandBuffers=&command;
            check(context.vk().queueSubmit(context.queue(),1,&submit,fence));
            check(context.vk().waitForFences(1,&fence,VK_TRUE,UINT64_MAX));
            std::array<uint64_t,2> ts{};
            check(context.vk().getQueryPoolResults(query,0,2,sizeof(ts),ts.data(),8,VK_QUERY_RESULT_64_BIT|VK_QUERY_RESULT_WAIT_BIT));
            double gpu=(ts[1]-ts[0])*context.timestamp_period_ns()/1000.;
            double wall=std::chrono::duration<double,std::micro>(Clock::now()-start).count();
            times<<(f?",":"")<<"{\"index\":"<<f<<",\"state\":\""<<label<<"\",\"seed\":"<<seed+f
                 <<",\"gpu_us\":"<<gpu+maintenance_gpu<<",\"image_gpu_us\":"<<gpu
                 <<",\"maintenance_gpu_us\":"<<maintenance_gpu<<",\"uniform_upload_gpu_us\":"<<uniform_gpu
                 <<",\"geometry_upload_gpu_us\":"<<geometry_gpu<<",\"blas_update_us\":"<<blas
                 <<",\"tlas_update_us\":"<<tlas<<",\"changed_slots\":"<<changed_count<<",\"wall_us\":"<<wall<<"}";
            n::AllocationLedger::instance().phase("diagnostic-readback-"+std::to_string(f));
            std::vector<float> values(size_t(width)*height*4);
            context.download_device_buffer(image,values.data(),values.size()*sizeof(float));
            auto frame_out=out/"frames"/std::to_string(f);
            copy_state(target&&f>0 ? target_path : state,frame_out);
            for(size_t c=0;c<3;++c) {
                const char* name=std::array<const char*,3>{"direct.pfm","indirect.pfm","total.pfm"}[c];
                pfm(frame_out/name,width,height,values,c);
                if(f+1==frames) pfm(out/name,width,height,values,c);
            }
        }
        times<<"]}\n"; if(!times) throw std::runtime_error("timing output failed");
        context.vk().destroyFence(fence,nullptr);context.vk().destroyQueryPool(query,nullptr);context.vk().destroyCommandPool(pool,nullptr);
        context.destroy_buffer(image);context.destroy_buffer(uniform);
        std::cout<<"N010 independent HWRT pixel path tracer captured "<<out<<"\n";
    } catch(const std::exception& e) { std::cerr<<e.what()<<"\n";return 1; }
}

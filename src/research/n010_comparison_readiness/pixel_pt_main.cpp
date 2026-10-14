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
        fs::path state,out; uint32_t spp=16,vertices=2,seed=0x13579bdfu,frames=1;
        std::string family="pixel-pt";
        for(int k=1;k<argc;++k) {
            std::string arg=argv[k];
            if(k+1>=argc) throw std::runtime_error("missing argument value");
            const std::string value=argv[++k];
            if(arg=="--state") state=value;
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
        if(fs::exists(out)) throw std::runtime_error("refuse to overwrite output directory");
        fs::create_directories(out);
        n::LedgerOutput ledger(out/"allocation-ledger.json");
        std::ifstream geometry(state/"geometry-state.bin",std::ios::binary);
        if(read<uint32_t>(geometry)!=1) throw std::runtime_error("state version");
        auto count=read<uint32_t>(geometry);
        if(count==0||fs::file_size(state/"geometry-state.bin")!=8+uint64_t(count)*52)
            throw std::runtime_error("invalid geometry state");
        std::vector<b::Triangle> triangles(count);
        for(auto& t:triangles) {
            t.v0=read<b::Vec3>(geometry); t.v1=read<b::Vec3>(geometry); t.v2=read<b::Vec3>(geometry);
            t.primitive_id=read<uint32_t>(geometry); t.material_id=read<uint32_t>(geometry);
            t.instance_id=read<uint32_t>(geometry); t.two_sided=read<uint32_t>(geometry)!=0;
            if(!t.two_sided) throw std::runtime_error("BF-P requires two-sided geometry");
        }
        std::ifstream frame(state/"frame-state.bin",std::ios::binary);
        char magic[12]{};frame.read(magic,12);
        if(std::memcmp(magic,"N007-STATE1\0",12)!=0 || fs::file_size(state/"frame-state.bin")!=148)
            throw std::runtime_error("invalid frame state");
        auto width=read<uint32_t>(frame),height=read<uint32_t>(frame);
        auto params=read<a::A001ParamsGpu>(frame);
        if(width!=params.counts[1]||height!=params.counts[2]) throw std::runtime_error("frame shape");
        fs::copy_file(state/"geometry-state.bin",out/"geometry-state.bin");
        fs::copy_file(state/"frame-state.bin",out/"frame-state.bin");
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
             <<"\"boundary\":\"static complete pixel Renderer: primary+NEE+all finite bounces+composite; initial AS setup/readback separate\","
             <<"\"family\":\""<<family<<"\",\"spp\":"<<spp<<",\"vertices\":"<<vertices<<",\"seed\":"<<seed
             <<",\"setup_wall_us\":"<<setup_wall<<",\"timestamp_period_ns\":"<<context.timestamp_period_ns()
             <<",\"width\":"<<width<<",\"height\":"<<height<<",\"frames\":[";
        for(uint32_t f=0;f<frames;++f) {
            n::AllocationLedger::instance().phase("recurring-frame");
            const auto start=Clock::now();
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
            times<<(f?",":"")<<"{\"index\":"<<f<<",\"seed\":"<<seed+f<<",\"gpu_us\":"<<gpu<<",\"wall_us\":"<<wall<<"}";
        }
        times<<"]}\n"; if(!times) throw std::runtime_error("timing output failed");
        n::AllocationLedger::instance().phase("diagnostic-readback");
        std::vector<float> values(size_t(width)*height*4);
        context.download_device_buffer(image,values.data(),values.size()*sizeof(float));
        for(size_t c=0;c<3;++c) pfm(out/(std::array<const char*,3>{"direct.pfm","indirect.pfm","total.pfm"}[c]),width,height,values,c);
        context.vk().destroyFence(fence,nullptr);context.vk().destroyQueryPool(query,nullptr);context.vk().destroyCommandPool(pool,nullptr);
        context.destroy_buffer(image);context.destroy_buffer(uniform);
        std::cout<<"N010 independent HWRT pixel path tracer captured "<<out<<"\n";
    } catch(const std::exception& e) { std::cerr<<e.what()<<"\n";return 1; }
}

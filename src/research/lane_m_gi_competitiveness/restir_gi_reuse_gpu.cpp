//042 actual 041 producer -> receiver-frame SDK ReSTIR GI initial/temporal/spatial/shade.
// Reuses the qualified022 context, HWRT, state loader and bounded ownership ledger.
#include "integrated_state.hpp"
#include "i001_compute.hpp"
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <thread>
using namespace m022;
namespace i=phos::gi::research::integration;
using u32=std::uint32_t;
constexpr u32 W=320,H=180,N=W*H,STREAMS=4,FRAMES=64,PASSES=9,VARIANTS=2;
constexpr u32 BLOCK_ROW=((W+15)/16)*256,PITCH=BLOCK_ROW*((H+15)/16),ARRAYS=3*VARIANTS;
constexpr std::array<u32,3> RECORD{0,1,63};
// Variant 0 is registered V1 (explicit null trial); variant 1 is control V0 (MISS M=0).
static void check(VkResult value){need(value==VK_SUCCESS,"042 Vulkan operation");}
static u32 jenkins(u32 a){
    a=(a+0x7ed55d16u)+(a<<12);a=(a^0xc761c23cu)^(a>>19);a=(a+0x165667b1u)+(a<<5);
    a=(a+0xd3a2646cu)^(a<<9);a=(a+0xfd7046c5u)+(a<<3);return (a^0xb55a4f09u)^(a>>16);
}
static u32 producer_seed(u32 s,u32 f){return ((0x0a420000u+64u*s+f)*0x9e3779b1u)^0xa042a042u;}
static void binary(const fs::path& path,const void* data,std::size_t size){
    need(!fs::exists(path),"042 existing output");std::ofstream f(path,std::ios::binary);
    f.write(static_cast<const char*>(data),std::streamsize(size));need(bool(f),"042 binary output");
}
struct Controls {
    float camera[3];float epsilon;float forward[3];u32 width;
    u32 height,pixels,unit,pad0;
    u32 runtime[4];u32 reservoir[4];
    float t_depth,t_normal;u32 t_history,t_fallback,t_bias,t_age,t_permutation,t_uniform;
    float s_depth,s_normal;u32 s_samples;float s_radius;u32 s_bias,s_pad[3];
};
static_assert(sizeof(Controls)==144);
enum Buffer:u32 {IMAGE,HITS,SOURCES,WITNESSES,CANDIDATES,LOCAL,PARAMS,RESERVOIRS,OWNERS,SURFACES,OFFSETS,SHADING,FRAME,CONTROLS,DIAGNOSTICS,COUNTERS,COUNT};
struct Runtime {
    b::B002VulkanContext& c;fs::path out;std::ofstream log;
    std::array<b::B002Buffer,COUNT> buffers{};std::array<std::uint64_t,COUNT> sizes{};
    std::unique_ptr<i::I001ComputeStage> producer;std::array<std::unique_ptr<i::I001ComputeStage>,5> stages;
    VkCommandPool pool{};VkCommandBuffer command{};VkFence fence{};VkQueryPool query{};
    VkPhysicalDeviceProperties properties{};VkPhysicalDeviceDriverProperties driver{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES};
    u32 bits{},frames{},dispatches{},base{};double active_us{};
    Runtime(b::B002VulkanContext& context,const fs::path& output):c(context),out(output),log(out/"frames.jsonl"){
        need(bool(log),"042 journal");log<<std::setprecision(17);
        VkPhysicalDeviceProperties2 p{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};p.pNext=&driver;
        vkGetPhysicalDeviceProperties2(c.physical_device(),&p);properties=p.properties;
        u32 count=0;vkGetPhysicalDeviceQueueFamilyProperties(c.physical_device(),&count,nullptr);
        std::vector<VkQueueFamilyProperties> families(count);vkGetPhysicalDeviceQueueFamilyProperties(c.physical_device(),&count,families.data());
        need(c.queue_family()<count,"042 queue family");bits=families[c.queue_family()].timestampValidBits;
        need(bits>0&&bits<=64&&properties.limits.maxPerStageDescriptorStorageBuffers>=12,"042 device limits");
        VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=c.queue_family();pi.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        check(c.vk().createCommandPool(&pi,nullptr,&pool));
        VkCommandBufferAllocateInfo ai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ai.commandPool=pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;
        check(c.vk().allocateCommandBuffers(&ai,&command));
        VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};check(c.vk().createFence(&fi,nullptr,&fence));
        VkQueryPoolCreateInfo qi{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};qi.queryType=VK_QUERY_TYPE_TIMESTAMP;qi.queryCount=PASSES+1;
        check(c.vk().createQueryPool(&qi,nullptr,&query));
    }
    ~Runtime(){producer.reset();for(auto& s:stages)s.reset();for(auto& buf:buffers)c.destroy_buffer(buf);
        if(query)c.vk().destroyQueryPool(query,nullptr);if(fence)c.vk().destroyFence(fence,nullptr);if(pool)c.vk().destroyCommandPool(pool,nullptr);}
    template<class T=unsigned char> T* map(Buffer j){return static_cast<T*>(buffers[j].mapped);}
    void zero(Buffer j){std::memset(buffers[j].mapped,0,std::size_t(sizes[j]));}
    void allocate(const State& state,b::B002HwrtTraversal& hwrt,const fs::path& shaders,const fs::path& offsets,u32 vertices){
        sizes={16ull*N,32ull*N,4ull*N,80ull*N*vertices,128ull*N,16ull*N,sizeof(state.params),32ull*PITCH*ARRAYS,16ull*PITCH*ARRAYS,
               48ull*2*N,8ull*8192,32ull*VARIANTS*N,16ull*N,sizeof(Controls),4ull*3*VARIANTS*N,4ull*8};
        for(u32 j=0;j<COUNT;j++){
            need(sizes[j]+256<=properties.limits.maxStorageBufferRange,"042 descriptor range");
            buffers[j]=c.create_host_buffer(sizes[j]+256,j==PARAMS?VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT:VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            need(buffers[j].mapped,"042 coherent mapping");zero(Buffer(j));
            std::memset(static_cast<char*>(buffers[j].mapped)+sizes[j],0xa7,256);
        }
        std::memcpy(map(PARAMS),&state.params,sizeof(state.params));
        need(fs::file_size(offsets)==16384,"042 neighbor offset bytes");std::ifstream o(offsets,std::ios::binary);std::array<signed char,16384> raw{};
        o.read(reinterpret_cast<char*>(raw.data()),16384);need(bool(o),"042 offset read");
        auto* offset=map<float>(OFFSETS);for(u32 j=0;j<16384;j++)offset[j]=std::max(float(raw[j])/127.0f,-1.0f);
        Controls k{};const auto& p=state.params;
        for(int a=0;a<3;a++){k.camera[a]=p.camera_pos_near[a];k.forward[a]=p.camera_forward_far[a];}
        k.epsilon=state.camera[16];k.width=W;k.height=H;k.pixels=N;k.unit=64;
        k.runtime[0]=8191;k.reservoir[0]=BLOCK_ROW;k.reservoir[1]=PITCH;
        k.t_depth=.1f;k.t_normal=.6f;k.t_history=8;k.t_fallback=1;k.t_bias=3;k.t_age=30;k.t_permutation=0;
        k.s_depth=.1f;k.s_normal=.6f;k.s_samples=2;k.s_radius=32.f;k.s_bias=3;
        std::memcpy(map(CONTROLS),&k,sizeof k);
        std::vector<i::I001Binding> bind{{0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[IMAGE]},
            {1,VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,nullptr,hwrt.top_level()},
            {2,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&hwrt.triangle_buffer()},
            {3,VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,&buffers[PARAMS]},
            {4,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[HITS]},{5,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[SOURCES]},
            {6,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[WITNESSES]},{7,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[CANDIDATES]},
            {8,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[LOCAL]}};
        producer=std::make_unique<i::I001ComputeStage>(c,(shaders/"physical_producer.spv").string(),bind,16);
        std::vector<i::I001Binding> reuse{{0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[RESERVOIRS]},{1,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[OWNERS]},
            {2,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[CANDIDATES]},{3,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[LOCAL]},
            {4,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[SURFACES]},{5,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[OFFSETS]},
            {6,VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,nullptr,hwrt.top_level()},
            {7,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[SHADING]},{8,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[FRAME]},
            {9,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[IMAGE]},{10,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[CONTROLS]},
            {11,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[DIAGNOSTICS]},{12,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[COUNTERS]}};
        for(u32 s=0;s<5;s++)stages[s]=std::make_unique<i::I001ComputeStage>(c,(shaders/("reuse_s"+std::to_string(s)+".spv")).string(),reuse,16);
    }
    void barrier(){
        VkMemoryBarrier m{VK_STRUCTURE_TYPE_MEMORY_BARRIER};m.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT|VK_ACCESS_HOST_WRITE_BIT;m.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT|VK_ACCESS_HOST_READ_BIT;
        c.vk().cmdPipelineBarrier(command,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&m,0,nullptr,0,nullptr);
    }
    void reuse(u32 stage,u32 variant,u32 frame_index){
        std::array<u32,4> push{variant,frame_index,jenkins(frame_index),0};
        stages[stage]->record(command,(W+7)/8,(H+7)/8,1,push.data(),16);dispatches++;
    }
    std::array<double,PASSES> frame(u32 stream,u32 f,u32 vertices){
        wall_guard();Ledger::instance().phase("stream"+std::to_string(stream)+"-frame"+std::to_string(f));
        const u32 frame_index=4096*(base+stream)+f,seed=producer_seed(base+stream,f);
        std::memset(map(COUNTERS),0,32);
        check(c.vk().resetFences(1,&fence));check(c.vk().resetCommandPool(pool,0));
        VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        check(c.vk().beginCommandBuffer(command,&bi));c.vk().cmdResetQueryPool(command,query,0,PASSES+1);barrier();
        c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);u32 q=1;
        auto mark=[&]{barrier();c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,q++);};
        for(u32 start=0;start<N;start+=128){std::array<u32,4> push{1,vertices,seed,start};producer->record(command,4,1,1,push.data(),16);dispatches++;}
        mark();reuse(0,0,frame_index);mark();
        for(u32 stage=1;stage<4;stage++)for(u32 v=0;v<VARIANTS;v++){reuse(stage,v,frame_index);mark();}
        reuse(4,0,frame_index);mark();need(q==PASSES+1,"042 pass count");
        check(c.vk().endCommandBuffer(command));
        VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&command;
        check(c.vk().queueSubmit(c.queue(),1,&si,fence));
        if(c.vk().waitForFences(1,&fence,VK_TRUE,250000000ull)!=VK_SUCCESS)incomplete_fence("042-frame");
        std::array<std::uint64_t,PASSES+1> tick{};check(c.vk().getQueryPoolResults(query,0,PASSES+1,sizeof tick,tick.data(),8,VK_QUERY_RESULT_64_BIT));
        auto mask=bits==64?UINT64_MAX:((std::uint64_t(1)<<bits)-1);std::array<double,PASSES> us{};double total=0;
        for(u32 j=0;j<PASSES;j++){us[j]=double((tick[j+1]-tick[j])&mask)*properties.limits.timestampPeriod/1000.;need(std::isfinite(us[j])&&us[j]>=0&&us[j]<=250000,"042 timestamp guard");total+=us[j];}
        active_us+=total;const u32* counter=map<u32>(COUNTERS);need(counter[0]==0,"042 shader error flags");
        log<<"{\"stream\":"<<stream<<",\"frame\":"<<f<<",\"frame_index\":"<<frame_index<<",\"producer_seed\":"<<seed<<",\"uniform_random\":"<<jenkins(frame_index)
           <<",\"timestamps\":[";for(u32 j=0;j<=PASSES;j++)log<<(j?",":"")<<tick[j];
        log<<"],\"pass_gpu_us_diagnostic\":[";for(u32 j=0;j<PASSES;j++)log<<(j?",":"")<<us[j];
        log<<"],\"loads\":[";for(u32 j=1;j<7;j++)log<<(j>1?",":"")<<counter[j];log<<"],\"errors\":"<<counter[0]<<"}\n";log.flush();frames++;
        return us;
    }
    void dump(const fs::path& folder,std::initializer_list<std::pair<Buffer,const char*>> list){
        for(auto [j,name]:list){
            auto* ptr=map(j);for(u32 k=0;k<256;k++)need(ptr[sizes[j]+k]==0xa7,"042 trailing guard corrupted");
            binary(folder/name,ptr,std::size_t(sizes[j]));
        }
    }
    void history(const fs::path& folder){
        // History-in before the frame: spatial arrays of both variants with owners and previous surfaces.
        for(u32 v=0;v<VARIANTS;v++){
            auto a=std::size_t(v*3+2)*PITCH;
            const char* name=v?"m0":"null";
            binary(folder/("history-reservoirs-"+std::string(name)+".bin"),map(RESERVOIRS)+32*a,32ull*PITCH);
            binary(folder/("history-owners-"+std::string(name)+".bin"),map(OWNERS)+16*a,16ull*PITCH);
        }
        binary(folder/"previous-surfaces.bin",map(SURFACES)+48ull*N,48ull*N);
    }
    void device(){
        std::ofstream f(out/"device.json");f<<std::setprecision(17)<<"{\"name\":"<<std::quoted(properties.deviceName)<<",\"driver_name\":"<<std::quoted(driver.driverName)<<",\"driver_info\":"<<std::quoted(driver.driverInfo)<<",\"vendor_id\":"<<properties.vendorID<<",\"device_id\":"<<properties.deviceID<<",\"timestamp_valid_bits\":"<<bits<<",\"timestamp_period_ns\":"<<properties.limits.timestampPeriod<<",\"queue_family\":"<<c.queue_family()<<"}\n";need(bool(f),"042 device receipt");
    }
};
int main(int argc,char** argv){fs::path output;
    try{
        need(argc==14,"042 usage --cpu-check|--gpu --state DIR --out NEWDIR --vertices 2|8 --shaders DIR --offsets FILE --stream-base 0|16");
        std::string mode=argv[1];need(mode=="--cpu-check"||mode=="--gpu","042 mode");std::map<std::string,std::string> args;
        for(int j=2;j<argc;j+=2)need(args.emplace(argv[j],argv[j+1]).second,"042 duplicate option");
        need(args.size()==6&&args.contains("--stream-base")&&(args["--stream-base"]=="0"||args["--stream-base"]=="16")&&args.contains("--state")&&args.contains("--out")&&args.contains("--vertices")&&args.contains("--shaders")&&args.contains("--offsets"),"042 options");
        need(args["--vertices"]=="2"||args["--vertices"]=="8","042 depth");u32 vertices=args["--vertices"]=="2"?2:8;
        State state=load_state(args["--state"]);
        for(const char* name:{"physical_producer.spv","reuse_s0.spv","reuse_s1.spv","reuse_s2.spv","reuse_s3.spv","reuse_s4.spv"})shader(fs::path(args["--shaders"])/name);
        need(fs::file_size(args["--offsets"])==16384,"042 offsets");
        fs::path target=args["--out"];need(!fs::exists(target)&&fs::is_directory(target.parent_path())&&fs::create_directory(target),"042 exclusive output");
        output=target;safety_output=output;safety_started=Clock::now();
        for(const char* name:{"geometry-state.bin","frame-state.bin"})fs::copy_file(fs::path(args["--state"])/name,output/name);
        if(mode=="--cpu-check"){
            std::ofstream f(output/"complete.json");f<<"{\"complete\":true,\"gpu_initialized\":false,\"triangles\":"<<state.triangles.size()<<",\"vertices\":"<<vertices<<",\"epsilon\":"<<std::setprecision(9)<<state.camera[16]<<"}\n";return 0;
        }
        double setup_us{},frame_us{},readback_us{},active_us{};u32 frames{},dispatches{};
        {
            auto start=Clock::now();Ledger::instance().phase("context-upload-as-pipelines");b::B002VulkanContext context(false,b::kB002TargetDeviceName,true);
            b::B002HwrtTraversal hwrt(context,state.triangles,"",false);Runtime run(context,output);run.base=std::stoul(args["--stream-base"]);run.allocate(state,hwrt,args["--shaders"],args["--offsets"],vertices);run.device();
            setup_us=std::chrono::duration<double,std::micro>(Clock::now()-start).count();auto stats=hwrt.setup_stats();
            std::ofstream setup(output/"setup.json");setup<<std::setprecision(17)<<"{\"setup_wall_us\":"<<setup_us<<",\"vertex_upload_wall_us\":"<<stats.vertex_upload_us<<",\"metadata_upload_wall_us\":"<<stats.metadata_upload_us<<",\"blas_build_gpu_us\":"<<stats.blas_build_us<<",\"tlas_build_gpu_us\":"<<stats.tlas_build_us<<",\"accepted_timing\":false}\n";
            std::vector<float> images(std::size_t(FRAMES)*N*4);
            for(u32 s=0;s<STREAMS;s++){
                for(Buffer j:{RESERVOIRS,OWNERS,SURFACES,SHADING,FRAME,DIAGNOSTICS})run.zero(j);
                auto stream=output/("stream-"+std::to_string(s));need(fs::create_directory(stream),"042 stream output");
                for(u32 f=0;f<FRAMES;f++){
                    bool full=std::find(RECORD.begin(),RECORD.end(),f)!=RECORD.end();fs::path folder=stream/("frame-"+std::to_string(f));
                    if(full){need(fs::create_directory(folder),"042 record output");run.history(folder);}
                    auto begin=Clock::now();run.frame(s,f,vertices);frame_us+=std::chrono::duration<double,std::micro>(Clock::now()-begin).count();
                    auto readback=Clock::now();std::memcpy(images.data()+std::size_t(f)*N*4,run.map(FRAME),16ull*N);
                    if(full)run.dump(folder,{{IMAGE,"producer-image.f32"},{HITS,"hits.u32"},{CANDIDATES,"candidates.bin"},{LOCAL,"local-endpoints.f32"},{RESERVOIRS,"reservoirs.bin"},{OWNERS,"owners.f32"},
                        {SURFACES,"surfaces.bin"},{SHADING,"shading.f32"},{FRAME,"frame-image.f32"},{DIAGNOSTICS,"diagnostics.u32"},{COUNTERS,"counters.u32"}});
                    readback_us+=std::chrono::duration<double,std::micro>(Clock::now()-readback).count();
                }
                binary(stream/"frames.f32",images.data(),images.size()*4);
            }
            run.dump(output,{{OFFSETS,"neighbor-offsets.f32"},{CONTROLS,"controls.bin"},{PARAMS,"params.bin"}});
            active_us=run.active_us;frames=run.frames;dispatches=run.dispatches;need(frames==STREAMS*FRAMES,"042 incomplete frames");Ledger::instance().phase("teardown");
        }
        Ledger::instance().save(output/"allocation-ledger.json");need(reserved_bytes==0,"042 ownership teardown");
        std::ofstream f(output/"complete.json");f<<std::setprecision(17)<<"{\"complete\":true,\"gpu_initialized\":true,\"frames\":"<<frames<<",\"streams\":"<<STREAMS<<",\"dispatches\":"<<dispatches<<",\"vertices\":"<<vertices<<",\"stream_base\":"<<args["--stream-base"]<<",\"variants\":2,\"record_frames\":[0,1,63],\"input_images_uploaded\":0,\"input_candidates_uploaded\":0,\"aggregate_reserved_peak\":"<<reserved_peak<<",\"aggregate_reserved_at_teardown\":"<<reserved_bytes<<",\"setup_wall_us\":"<<setup_us<<",\"frame_wall_us_including_fences\":"<<frame_us<<",\"readback_wall_us\":"<<readback_us<<",\"active_gpu_us_diagnostic\":"<<active_us<<",\"quality_admitted\":false,\"accepted_timing\":false}\n";
        need(bool(f),"042 completion receipt");return 0;
    }catch(const std::exception& e){if(!output.empty()){Ledger::instance().save(output/"allocation-ledger.json");std::ofstream(output/"failure.txt")<<e.what()<<'\n';}std::cerr<<e.what()<<'\n';return 2;}
}

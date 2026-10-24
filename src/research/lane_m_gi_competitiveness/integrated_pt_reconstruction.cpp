//022 opt-in physical image producer and GPU-resident quadratic reconstruction.
#include "integrated_state.hpp"
#include "i001_compute.hpp"
#include <charconv>
#include <iomanip>
#include <iostream>
#include <memory>
#include <thread>
namespace i=phos::gi::research::integration;
using namespace m022;
using u32=std::uint32_t;
static constexpr u32 N=320*180;
static void vkcheck(VkResult r){need(r==VK_SUCCESS,"022 Vulkan operation failed");}
static u32 integer(const std::string& s){u32 v=0;auto r=std::from_chars(s.data(),s.data()+s.size(),v);need(r.ec==std::errc{}&&r.ptr==s.data()+s.size(),"022 unsigned integer syntax/range");return v;}
static void binary(const fs::path& p,const void* data,std::size_t bytes){std::ofstream f(p,std::ios::binary);f.write(static_cast<const char*>(data),std::streamsize(bytes));need(bool(f),"022 binary output failed");}
static void pfm(const fs::path& path,const float* pixels,unsigned component){
    std::ofstream f(path,std::ios::binary);f<<"PF\n320 180\n-1.0\n";
    for(unsigned y=180;y-->0;)for(unsigned x=0;x<320;x++){float v=pixels[4*(y*320+x)+component];float rgb[]{v,v,v};f.write(reinterpret_cast<char*>(rgb),sizeof rgb);}need(bool(f),"022 PFM output failed");
}
struct Runtime {
    b::B002VulkanContext& c;fs::path out;std::ofstream journal;std::array<b::B002Buffer,11> buffers{};
    std::unique_ptr<i::I001ComputeStage> producer,quadratic,compose;
    VkCommandPool pool{};VkCommandBuffer command{};VkFence fence{};VkQueryPool query{};
    VkPhysicalDeviceProperties properties{};VkPhysicalDeviceDriverProperties driver{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES};u32 bits{},units{};
    double active_us{},envelope_us{};
    explicit Runtime(b::B002VulkanContext& context,const fs::path& output):c(context),out(output),journal(out/"dispatches.jsonl"){
        need(bool(journal),"022 journal open");journal<<std::setprecision(17);
        VkPhysicalDeviceProperties2 p{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};p.pNext=&driver;vkGetPhysicalDeviceProperties2(c.physical_device(),&p);properties=p.properties;
        u32 count=0;vkGetPhysicalDeviceQueueFamilyProperties(c.physical_device(),&count,nullptr);std::vector<VkQueueFamilyProperties> q(count);vkGetPhysicalDeviceQueueFamilyProperties(c.physical_device(),&count,q.data());
        need(c.queue_family()<count,"022 queue family");bits=q[c.queue_family()].timestampValidBits;need(bits>0&&bits<=64&&properties.limits.maxPerStageDescriptorStorageBuffers>=8,"022 device limits/timestamps");
        VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=c.queue_family();pi.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;vkcheck(c.vk().createCommandPool(&pi,nullptr,&pool));
        VkCommandBufferAllocateInfo ai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ai.commandPool=pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;vkcheck(c.vk().allocateCommandBuffers(&ai,&command));
        VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};vkcheck(c.vk().createFence(&fi,nullptr,&fence));VkQueryPoolCreateInfo qi{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};qi.queryType=VK_QUERY_TYPE_TIMESTAMP;qi.queryCount=4;vkcheck(c.vk().createQueryPool(&qi,nullptr,&query));
    }
    ~Runtime(){compose.reset();quadratic.reset();producer.reset();for(auto& buf:buffers)c.destroy_buffer(buf);if(query)c.vk().destroyQueryPool(query,nullptr);if(fence)c.vk().destroyFence(fence,nullptr);if(pool)c.vk().destroyCommandPool(pool,nullptr);}
    void allocate(const State& s,b::B002HwrtTraversal& hwrt,const fs::path& shaders){
        const std::array<std::uint64_t,11> bytes{8ull*N*4,80,8ull*N*4,75ull*N*4,6ull*N*4,1ull*N*4,3ull*N*4,3ull*N*4,4ull*N*4,4ull*N*4,sizeof(s.params)};
        for(unsigned j=0;j<11;j++){need(bytes[j]<=properties.limits.maxStorageBufferRange,"022 storage range");buffers[j]=c.create_host_buffer(bytes[j],j==10?VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT:VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);need(buffers[j].mapped,"022 coherent mapping absent");std::memset(buffers[j].mapped,0,std::size_t(bytes[j]));}
        // Only deterministic camera metadata and original physical frame input.
        std::memcpy(buffers[1].mapped,s.camera.data(),80);std::memcpy(buffers[10].mapped,&s.params,sizeof(s.params));
        std::array<i::I001Binding,6> pb{{{0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[8]},{1,VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,nullptr,hwrt.top_level()},{2,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&hwrt.triangle_buffer()},{3,VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,&buffers[10]},{4,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[0]},{5,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[5]}}};
        producer=std::make_unique<i::I001ComputeStage>(c,(shaders/"integrated_producer.spv").string(),pb,16);
        std::array<i::I001Binding,8> qb{};for(u32 j=0;j<8;j++)qb[j]={j,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[j]};
        quadratic=std::make_unique<i::I001ComputeStage>(c,(shaders/"surface_quadratic_device.spv").string(),qb,16);
        std::array<i::I001Binding,3> cb{{{0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[8]},{1,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[6]},{2,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[9]}}};
        compose=std::make_unique<i::I001ComputeStage>(c,(shaders/"integrated_composite.spv").string(),cb);
    }
    double elapsed(std::uint64_t begin,std::uint64_t end){auto mask=bits==64?UINT64_MAX:((std::uint64_t(1)<<bits)-1);double us=double((end-begin)&mask)*properties.limits.timestampPeriod/1000.;need(std::isfinite(us)&&us>=0,"022 timestamp arithmetic");return us;}
    void unit(const std::string& kind,u32 stage,u32 start,u32 count,u32 spp,u32 vertices,u32 seed){
        wall_guard();need(count>0&&start<N&&count<=N-start,"022 dispatch range");bool first=units==0,last=kind=="composite";
        Ledger::instance().phase(kind+"-s"+std::to_string(stage)+"-p"+std::to_string(start));
        journal<<"{\"event\":\"begin\",\"unit\":"<<units<<",\"kind\":"<<std::quoted(kind)<<",\"stage\":"<<stage<<",\"start\":"<<start<<",\"count\":"<<count<<"}\n";journal.flush();
        vkcheck(c.vk().resetFences(1,&fence));vkcheck(c.vk().resetCommandPool(pool,0));VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;vkcheck(c.vk().beginCommandBuffer(command,&bi));
        c.vk().cmdResetQueryPool(command,query,0,2);if(first){c.vk().cmdResetQueryPool(command,query,2,2);c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,2);}
        VkMemoryBarrier before{VK_STRUCTURE_TYPE_MEMORY_BARRIER};before.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT|VK_ACCESS_SHADER_WRITE_BIT;before.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;
        c.vk().cmdPipelineBarrier(command,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&before,0,nullptr,0,nullptr);
        c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);
        std::array<u32,4> push{};
        if(kind=="producer"){need(count<=128,"022 producer chunk");push={spp,vertices,seed,start};producer->record(command,(count+31)/32,1,1,push.data(),16);}
        else if(kind=="composite")compose->record(command,(count+31)/32);
        else {u32 mode=kind=="geometry"?0:kind=="fit"?1:2;need(kind=="geometry"||kind=="fit"||kind=="filter","022 unit kind");if(mode==1)need(count<=128,"022 fit chunk");push={mode,stage,start,count};quadratic->record(command,(count+31)/32,1,1,push.data(),16);}
        VkMemoryBarrier after{VK_STRUCTURE_TYPE_MEMORY_BARRIER};after.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;after.dstAccessMask=VK_ACCESS_HOST_READ_BIT|VK_ACCESS_SHADER_READ_BIT;
        c.vk().cmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&after,0,nullptr,0,nullptr);
        c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,1);if(last)c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,3);vkcheck(c.vk().endCommandBuffer(command));
        VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&command;vkcheck(c.vk().queueSubmit(c.queue(),1,&si,fence));
        VkResult wait=c.vk().waitForFences(1,&fence,VK_TRUE,250000000ull);if(wait!=VK_SUCCESS){journal<<"{\"event\":\"incomplete\",\"unit\":"<<units<<",\"wait_result\":"<<int(wait)<<"}\n";journal.flush();incomplete_fence("integrated-unit");}
        std::uint64_t ticks[2]{};vkcheck(c.vk().getQueryPoolResults(query,0,2,sizeof ticks,ticks,8,VK_QUERY_RESULT_64_BIT));double us=elapsed(ticks[0],ticks[1]);active_us+=us;
        journal<<"{\"event\":\"complete\",\"unit\":"<<units<<",\"timestamp_begin\":"<<ticks[0]<<",\"timestamp_end\":"<<ticks[1]<<",\"gpu_us_diagnostic\":"<<us<<"}\n";journal.flush();units++;need(us<=250000,"022 unit duration guard");
        if(last){vkcheck(c.vk().getQueryPoolResults(query,2,2,sizeof ticks,ticks,8,VK_QUERY_RESULT_64_BIT));envelope_us=elapsed(ticks[0],ticks[1]);std::ofstream f(out/"envelope.json");f<<std::setprecision(17)<<"{\"timestamp_begin\":"<<ticks[0]<<",\"timestamp_end\":"<<ticks[1]<<",\"gpu_us_including_pauses\":"<<envelope_us<<",\"active_unit_sum_us\":"<<active_us<<",\"accepted_timing\":false}\n";need(bool(f),"022 envelope write");}
        else std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    void save(){
        Ledger::instance().phase("diagnostic-readback-after-composition");
        const std::array<const char*,10> names{"hits.u32","camera.f32","geometry.f32","coefficients.f32","maps.u32","sources.f32","stages.f32","unclipped.f32","raw-pt.f32","final.f32"};for(unsigned j=0;j<10;j++)binary(out/names[j],buffers[j].mapped,buffers[j].size);
        for(unsigned part=0;part<3;part++){const char* name=std::array<const char*,3>{"direct","indirect","total"}[part];pfm(out/(std::string("raw-")+name+".pfm"),static_cast<float*>(buffers[8].mapped),part);pfm(out/(std::string(name)+".pfm"),static_cast<float*>(buffers[9].mapped),part);}
        std::ofstream f(out/"device.json");f<<std::setprecision(17)<<"{\"name\":"<<std::quoted(properties.deviceName)<<",\"driver_name\":"<<std::quoted(driver.driverName)<<",\"driver_info\":"<<std::quoted(driver.driverInfo)<<",\"vendor_id\":"<<properties.vendorID<<",\"device_id\":"<<properties.deviceID<<",\"driver_version\":"<<properties.driverVersion<<",\"api_version\":"<<properties.apiVersion<<",\"queue_family\":"<<c.queue_family()<<",\"timestamp_valid_bits\":"<<bits<<",\"timestamp_period_ns\":"<<properties.limits.timestampPeriod<<"}\n";need(bool(f),"022 device write");
    }
};
int main(int argc,char** argv){fs::path output;
    try{
        need(argc==12||argc==14,"022 usage --cpu-check|--gpu --state DIR --out NEWDIR --spp N --vertices N --seed N [--shaders DIR]");
        std::string mode=argv[1];need(mode=="--cpu-check"||mode=="--gpu","022 mode");std::map<std::string,std::string> args;
        for(int j=2;j<argc;j+=2){std::string key=argv[j];need(j+1<argc&&args.emplace(key,argv[j+1]).second,"022 duplicate/missing option");need(key=="--state"||key=="--out"||key=="--spp"||key=="--vertices"||key=="--seed"||(mode=="--gpu"&&key=="--shaders"),"022 unknown option");}
        for(const char* key:{"--state","--out","--spp","--vertices","--seed"})need(args.contains(key)&&!args[key].empty(),"022 required option");
        need(args.size()==(mode=="--gpu"?6u:5u),"022 mode option count");auto spp=integer(args["--spp"]),vertices=integer(args["--vertices"]),seed=integer(args["--seed"]);budget(spp,vertices,seed);
        auto state=load_state(args["--state"]);fs::path candidate=args["--out"];need(!fs::exists(candidate)&&fs::is_directory(candidate.parent_path()),"022 output exists/parent absent");
        if(mode=="--gpu")for(const char* name:{"integrated_producer.spv","surface_quadratic_device.spv","integrated_composite.spv"})shader(fs::path(args["--shaders"])/name);
        need(fs::create_directory(candidate),"022 exclusive output creation");output=candidate;safety_output=output;safety_started=Clock::now();
        for(const char* name:{"geometry-state.bin","frame-state.bin"})fs::copy_file(fs::path(args["--state"])/name,output/name);
        binary(output/"camera.f32",state.camera.data(),80);
        if(mode=="--cpu-check"){std::ofstream f(output/"complete.json");f<<"{\"schema\":\"m001-integrated022-native-cpu-input/1\",\"complete\":true,\"gpu_initialized\":false,\"triangles\":"<<state.triangles.size()<<",\"spp\":"<<spp<<",\"vertices\":"<<vertices<<",\"seed\":"<<seed<<"}\n";need(bool(f),"022 CPU audit write");return 0;}
        double setup_us=0,frame_wall_us=0,readback_us=0;u32 units=0;
        {
            const auto setup=Clock::now();Ledger::instance().phase("initial-context-geometry-uploads-as-and-pipelines");b::B002VulkanContext context(false,b::kB002TargetDeviceName,true);
            b::B002HwrtTraversal hwrt(context,state.triangles,"",false);Runtime run(context,output);run.allocate(state,hwrt,args["--shaders"]);setup_us=std::chrono::duration<double,std::micro>(Clock::now()-setup).count();
            auto stats=hwrt.setup_stats();std::ofstream sf(output/"setup.json");sf<<std::setprecision(17)<<"{\"setup_wall_us\":"<<setup_us<<",\"vertex_upload_wall_us\":"<<stats.vertex_upload_us<<",\"metadata_upload_wall_us\":"<<stats.metadata_upload_us<<",\"blas_build_gpu_us\":"<<stats.blas_build_us<<",\"tlas_build_gpu_us\":"<<stats.tlas_build_us<<",\"hwrt_persistent_bytes\":"<<stats.persistent_bytes<<",\"hwrt_scratch_bytes\":"<<stats.scratch_bytes<<",\"initial_allocation_upload_as_pipeline_costs_separate\":true,\"accepted_timing\":false}\n";need(bool(sf),"022 setup write");sf.close();
            const auto frame=Clock::now();for(u32 p=0;p<N;p+=128)run.unit("producer",0,p,std::min(128u,N-p),spp,vertices,seed);
            run.unit("geometry",0,0,N,spp,vertices,seed);for(u32 s=0;s<3;s++)for(u32 p=0;p<N;p+=128)run.unit("fit",s,p,std::min(128u,N-p),spp,vertices,seed);
            for(u32 s=0;s<3;s++)run.unit("filter",s,0,N,spp,vertices,seed);run.unit("composite",0,0,N,spp,vertices,seed);units=run.units;need(units==1805,"022 complete unit count");frame_wall_us=std::chrono::duration<double,std::micro>(Clock::now()-frame).count();
            const auto rb=Clock::now();run.save();readback_us=std::chrono::duration<double,std::micro>(Clock::now()-rb).count();Ledger::instance().phase("teardown");
        }
        Ledger::instance().save(output/"allocation-ledger.json");need(reserved_bytes==0,"022 nonzero aggregate teardown");
        std::ofstream f(output/"complete.json");f<<std::setprecision(17)<<"{\"schema\":\"m001-integrated022-native-gpu/1\",\"complete\":true,\"gpu_initialized\":true,\"units\":"<<units<<",\"spp\":"<<spp<<",\"vertices\":"<<vertices<<",\"seed\":"<<seed<<",\"new_primary_paths\":57600,\"new_indirect_paths\":"<<std::uint64_t(spp)*N<<",\"input_images_uploaded\":0,\"input_hits_uploaded\":0,\"cpu_coefficients_uploaded\":0,\"intermediate_readbacks\":0,\"aggregate_reserved_peak\":"<<reserved_peak<<",\"aggregate_reserved_at_teardown\":"<<reserved_bytes<<",\"setup_wall_us\":"<<setup_us<<",\"frame_wall_us\":"<<frame_wall_us<<",\"readback_wall_us\":"<<readback_us<<",\"quality_admitted\":false,\"accepted_timing\":false}\n";need(bool(f),"022 completion write");std::cout<<"022 integrated image complete; independent admission required\n";return 0;
    }catch(const std::exception& e){if(!output.empty()){Ledger::instance().save(output/"allocation-ledger.json");std::ofstream(output/"failure.txt")<<e.what()<<'\n';}std::cerr<<e.what()<<'\n';return 2;}
}

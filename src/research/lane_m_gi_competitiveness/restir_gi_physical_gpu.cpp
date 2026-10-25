//037 standalone physical producer -> actual SDK Make/Pack -> GPU Unpack/image.
// Reuses the qualified022 context, HWRT, state loader and bounded allocator.
#include "integrated_state.hpp"
#include "i001_compute.hpp"
#include <charconv>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <thread>
using namespace m022;
namespace i=phos::gi::research::integration;
using u32=std::uint32_t;
constexpr u32 N=320*180;
constexpr std::array<u32,4> seeds{0x12345678u^0xa037a037u,0x9abcdef0u^0xa037a037u,0x89abcdefu^0xa037a037u,0x76543210u^0xa037a037u};
static void check(VkResult value){need(value==VK_SUCCESS,"037 Vulkan operation");}
static void binary(const fs::path& path,const void* data,std::size_t size){
    need(!fs::exists(path),"037 existing output");std::ofstream f(path,std::ios::binary);
    f.write(static_cast<const char*>(data),std::streamsize(size));need(bool(f),"037 binary output");
}
static void pfm(const fs::path& path,const float* data,u32 stride,u32 offset){
    std::ofstream f(path,std::ios::binary);f<<"PF\n320 180\n-1.0\n";
    for(u32 y=180;y-->0;)for(u32 x=0;x<320;x++)f.write(reinterpret_cast<const char*>(data+(y*320+x)*stride+offset),12);
    need(bool(f),"037 image output");
}
struct Runtime {
    b::B002VulkanContext& c;fs::path out;std::ofstream log;
    std::array<b::B002Buffer,11> buffers{};std::array<std::uint64_t,11> sizes{};
    std::array<std::unique_ptr<i::I001ComputeStage>,4> stages;
    VkCommandPool pool{};VkCommandBuffer command{};VkFence fence{};VkQueryPool query{};
    VkPhysicalDeviceProperties properties{};VkPhysicalDeviceDriverProperties driver{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES};
    u32 bits{},units{};double active_us{};
    Runtime(b::B002VulkanContext& context,const fs::path& output):c(context),out(output),log(out/"dispatches.jsonl"){
        need(bool(log),"037 journal");log<<std::setprecision(17);
        VkPhysicalDeviceProperties2 p{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};p.pNext=&driver;
        vkGetPhysicalDeviceProperties2(c.physical_device(),&p);properties=p.properties;
        u32 count=0;vkGetPhysicalDeviceQueueFamilyProperties(c.physical_device(),&count,nullptr);
        std::vector<VkQueueFamilyProperties> families(count);vkGetPhysicalDeviceQueueFamilyProperties(c.physical_device(),&count,families.data());
        need(c.queue_family()<count,"037 queue family");bits=families[c.queue_family()].timestampValidBits;
        need(bits>0&&bits<=64&&properties.limits.maxPerStageDescriptorStorageBuffers>=6,"037 device limits");
        VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=c.queue_family();pi.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        check(c.vk().createCommandPool(&pi,nullptr,&pool));
        VkCommandBufferAllocateInfo ai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ai.commandPool=pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;
        check(c.vk().allocateCommandBuffers(&ai,&command));
        VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};check(c.vk().createFence(&fi,nullptr,&fence));
        VkQueryPoolCreateInfo qi{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};qi.queryType=VK_QUERY_TYPE_TIMESTAMP;qi.queryCount=4;
        check(c.vk().createQueryPool(&qi,nullptr,&query));
    }
    ~Runtime(){for(auto& s:stages)s.reset();for(auto& buf:buffers)c.destroy_buffer(buf);
        if(query)c.vk().destroyQueryPool(query,nullptr);if(fence)c.vk().destroyFence(fence,nullptr);if(pool)c.vk().destroyCommandPool(pool,nullptr);}
    void allocate(const State& state,b::B002HwrtTraversal& hwrt,const fs::path& shaders,u32 vertices){
        sizes={16ull*N,32ull*N,4ull*N,16ull*N,32ull*N,4ull*N,80ull*N*vertices,128ull*N,32ull*N,96ull*N,sizeof(state.params)};
        for(u32 j=0;j<11;j++){
            need(sizes[j]+256<=properties.limits.maxStorageBufferRange,"037 descriptor range");
            buffers[j]=c.create_host_buffer(sizes[j]+256,j==10?VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT:VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            need(buffers[j].mapped,"037 coherent mapping");std::memset(buffers[j].mapped,0,std::size_t(sizes[j]));
            std::memset(static_cast<char*>(buffers[j].mapped)+sizes[j],0xa7,256);
        }
        std::memcpy(buffers[10].mapped,&state.params,sizeof(state.params));
        for(u32 role=0;role<2;role++){
            std::vector<i::I001Binding> bind{{0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[role*3]},
                {1,VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,nullptr,hwrt.top_level()},
                {2,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&hwrt.triangle_buffer()},
                {3,VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,&buffers[10]},
                {4,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[role*3+1]},
                {5,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[role*3+2]}};
            if(role){bind.push_back({6,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[6]});bind.push_back({7,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[7]});}
            stages[role]=std::make_unique<i::I001ComputeStage>(c,(shaders/(role?"physical_producer.spv":"original_producer.spv")).string(),bind,16);
        }
        std::array<i::I001Binding,4> bind{{{0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[8]},
            {1,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[7]},{2,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[9]},
            {3,VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,nullptr,hwrt.top_level()}}};
        for(u32 j=2;j<4;j++)stages[j]=std::make_unique<i::I001ComputeStage>(c,(shaders/(j==2?"physical_make.spv":"physical_load.spv")).string(),bind,16);
    }
    void unit(u32 seed_index,u32 stage,u32 start,u32 vertices){
        wall_guard();need(stage<4&&start<N&&start%128==0,"037 dispatch boundary");
        Ledger::instance().phase("seed"+std::to_string(seed_index)+"-stage"+std::to_string(stage));
        log<<"{\"event\":\"begin\",\"unit\":"<<units<<",\"seed_index\":"<<seed_index<<",\"stage\":"<<stage<<",\"start\":"<<start<<",\"count\":128}\n";log.flush();
        check(c.vk().resetFences(1,&fence));check(c.vk().resetCommandPool(pool,0));
        VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        check(c.vk().beginCommandBuffer(command,&bi));c.vk().cmdResetQueryPool(command,query,0,2);
        if(stage==0&&start==0){c.vk().cmdResetQueryPool(command,query,2,2);c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,2);}
        VkMemoryBarrier before{VK_STRUCTURE_TYPE_MEMORY_BARRIER};before.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT|VK_ACCESS_SHADER_WRITE_BIT;before.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;
        c.vk().cmdPipelineBarrier(command,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&before,0,nullptr,0,nullptr);
        c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);
        std::array<u32,4> push=stage<2?std::array<u32,4>{1,vertices,seeds[seed_index],start}:std::array<u32,4>{start,128,0,0};
        stages[stage]->record(command,4,1,1,push.data(),16);
        VkMemoryBarrier after{VK_STRUCTURE_TYPE_MEMORY_BARRIER};after.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;after.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_HOST_READ_BIT;
        c.vk().cmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&after,0,nullptr,0,nullptr);
        c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,1);
        if(stage==3&&start==N-128)c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,3);
        check(c.vk().endCommandBuffer(command));
        VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&command;
        check(c.vk().queueSubmit(c.queue(),1,&si,fence));
        if(c.vk().waitForFences(1,&fence,VK_TRUE,250000000ull)!=VK_SUCCESS)incomplete_fence("037-physical-unit");
        std::uint64_t tick[2]{};check(c.vk().getQueryPoolResults(query,0,2,sizeof tick,tick,8,VK_QUERY_RESULT_64_BIT));
        auto mask=bits==64?UINT64_MAX:((std::uint64_t(1)<<bits)-1);double us=double((tick[1]-tick[0])&mask)*properties.limits.timestampPeriod/1000.;
        need(std::isfinite(us)&&us>=0&&us<=250000,"037 timestamp unit guard");active_us+=us;
        log<<"{\"event\":\"complete\",\"unit\":"<<units<<",\"timestamp_begin\":"<<tick[0]<<",\"timestamp_end\":"<<tick[1]<<",\"gpu_us_diagnostic\":"<<us<<"}\n";log.flush();units++;
        if(stage==3&&start==N-128){
            check(c.vk().getQueryPoolResults(query,2,2,sizeof tick,tick,8,VK_QUERY_RESULT_64_BIT));
            std::ofstream envelope(out/("envelope-seed-"+std::to_string(seed_index)+".json"));
            envelope<<std::setprecision(17)<<"{\"timestamp_begin\":"<<tick[0]<<",\"timestamp_end\":"<<tick[1]<<",\"gpu_us_including_fences_pauses\":"<<double((tick[1]-tick[0])&mask)*properties.limits.timestampPeriod/1000.<<",\"accepted_timing\":false}\n";
            need(bool(envelope),"037 envelope write");
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    void save(u32 seed_index){
        Ledger::instance().phase("completed-image-readback");auto folder=out/("seed-"+std::to_string(seed_index));need(fs::create_directory(folder),"037 seed output exists");
        const std::array<const char*,11> names{"original.f32","original-hits.u32","original-source.f32","observed.f32","observed-hits.u32","observed-source.f32","witnesses.bin","candidates.bin","reservoirs.bin","sdk-output.f32","params.bin"};
        for(u32 j=0;j<11;j++){
            auto* ptr=static_cast<const unsigned char*>(buffers[j].mapped);
            for(u32 k=0;k<256;k++)need(ptr[sizes[j]+k]==0xa7,"037 trailing guard corrupted");
            binary(folder/names[j],ptr,std::size_t(sizes[j]));binary(folder/(std::string(names[j])+".guard"),ptr+sizes[j],256);
        }
        pfm(folder/"sdk-unpacked-total.pfm",static_cast<const float*>(buffers[9].mapped),24,8);
        pfm(folder/"sdk-packed-total.pfm",static_cast<const float*>(buffers[9].mapped),24,20);
    }
    void device(){
        std::ofstream f(out/"device.json");f<<std::setprecision(17)<<"{\"name\":"<<std::quoted(properties.deviceName)<<",\"driver_name\":"<<std::quoted(driver.driverName)<<",\"driver_info\":"<<std::quoted(driver.driverInfo)<<",\"vendor_id\":"<<properties.vendorID<<",\"device_id\":"<<properties.deviceID<<",\"timestamp_valid_bits\":"<<bits<<",\"timestamp_period_ns\":"<<properties.limits.timestampPeriod<<",\"queue_family\":"<<c.queue_family()<<"}\n";need(bool(f),"037 device receipt");
    }
};
int main(int argc,char** argv){fs::path output;
    try{
        need(argc==10,"037 usage --cpu-check|--gpu --state DIR --out NEWDIR --vertices 2|8 --shaders DIR");
        std::string mode=argv[1];need(mode=="--cpu-check"||mode=="--gpu","037 mode");std::map<std::string,std::string> args;
        for(int j=2;j<argc;j+=2)need(args.emplace(argv[j],argv[j+1]).second,"037 duplicate option");
        need(args.size()==4&&args.contains("--state")&&args.contains("--out")&&args.contains("--vertices")&&args.contains("--shaders"),"037 options");
        need(args["--vertices"]=="2"||args["--vertices"]=="8","037 depth");u32 vertices=args["--vertices"]=="2"?2:8;
        State state=load_state(args["--state"]);for(const char* name:{"original_producer.spv","physical_producer.spv","physical_make.spv","physical_load.spv"})shader(fs::path(args["--shaders"])/name);
        fs::path target=args["--out"];need(!fs::exists(target)&&fs::is_directory(target.parent_path())&&fs::create_directory(target),"037 exclusive output");
        output=target;safety_output=output;safety_started=Clock::now();
        for(const char* name:{"geometry-state.bin","frame-state.bin"})fs::copy_file(fs::path(args["--state"])/name,output/name);
        if(mode=="--cpu-check"){
            std::ofstream f(output/"complete.json");f<<"{\"complete\":true,\"gpu_initialized\":false,\"triangles\":"<<state.triangles.size()<<",\"vertices\":"<<vertices<<"}\n";return 0;
        }
        double setup_us{},frame_us{},readback_us{},active_us{};u32 units{};
        {
            auto start=Clock::now();Ledger::instance().phase("context-upload-as-pipelines");b::B002VulkanContext context(false,b::kB002TargetDeviceName,true);
            b::B002HwrtTraversal hwrt(context,state.triangles,"",false);Runtime run(context,output);run.allocate(state,hwrt,args["--shaders"],vertices);run.device();
            setup_us=std::chrono::duration<double,std::micro>(Clock::now()-start).count();auto stats=hwrt.setup_stats();
            std::ofstream setup(output/"setup.json");setup<<std::setprecision(17)<<"{\"setup_wall_us\":"<<setup_us<<",\"vertex_upload_wall_us\":"<<stats.vertex_upload_us<<",\"metadata_upload_wall_us\":"<<stats.metadata_upload_us<<",\"blas_build_gpu_us\":"<<stats.blas_build_us<<",\"tlas_build_gpu_us\":"<<stats.tlas_build_us<<",\"accepted_timing\":false}\n";
            for(u32 s=0;s<4;s++){
                auto frame=Clock::now();for(u32 stage=0;stage<4;stage++)for(u32 p=0;p<N;p+=128)run.unit(s,stage,p,vertices);
                frame_us+=std::chrono::duration<double,std::micro>(Clock::now()-frame).count();
                auto readback=Clock::now();run.save(s);readback_us+=std::chrono::duration<double,std::micro>(Clock::now()-readback).count();
            }
            active_us=run.active_us;units=run.units;need(units==7200,"037 incomplete units");Ledger::instance().phase("teardown");
        }
        Ledger::instance().save(output/"allocation-ledger.json");need(reserved_bytes==0,"037 ownership teardown");
        std::ofstream f(output/"complete.json");f<<std::setprecision(17)<<"{\"complete\":true,\"gpu_initialized\":true,\"units\":"<<units<<",\"vertices\":"<<vertices<<",\"paths_per_role\":230400,\"roles\":2,\"completed_images_read_back\":4,\"input_images_uploaded\":0,\"input_candidates_uploaded\":0,\"intermediate_readbacks\":0,\"aggregate_reserved_peak\":"<<reserved_peak<<",\"aggregate_reserved_at_teardown\":"<<reserved_bytes<<",\"setup_wall_us\":"<<setup_us<<",\"frame_wall_us_including_fences_pauses\":"<<frame_us<<",\"readback_wall_us\":"<<readback_us<<",\"active_gpu_us_diagnostic\":"<<active_us<<",\"quality_admitted\":false,\"accepted_timing\":false}\n";
        need(bool(f),"037 completion receipt");return 0;
    }catch(const std::exception& e){if(!output.empty()){Ledger::instance().save(output/"allocation-ledger.json");std::ofstream(output/"failure.txt")<<e.what()<<'\n';}std::cerr<<e.what()<<'\n';return 2;}
}

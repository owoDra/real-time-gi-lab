//019 isolated Vulkan replay host. No Renderer/default-build integration.
#define main m001_q019_cpu_main
#include "surface_quadratic_scalar.cpp"
#undef main
#include "allocation_ledger.hpp"
#include <chrono>
#include <cstring>
#include <iomanip>
#include <thread>
using Ledger=phos::gi::research::n010::AllocationLedger;
using Clock=std::chrono::steady_clock;
static void vkcheck(VkResult r){require(r==VK_SUCCESS,"Vulkan operation failed");}
struct Q019Buffer{VkBuffer buffer{};VkDeviceMemory memory{};void* mapped{};VkDeviceSize bytes{};};
struct Q019Context {
    VkInstance instance{};VkPhysicalDevice physical{};VkDevice device{};VkQueue queue{};q::uint family{},bits{};
    VkPhysicalDeviceProperties properties{};VkPhysicalDeviceMemoryProperties memories{};VkPhysicalDeviceDriverProperties driver{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES};
    VkCommandPool pool{};VkCommandBuffer command{};VkFence fence{};VkQueryPool query{};
    VkDescriptorSetLayout set_layout{};VkPipelineLayout layout{};VkDescriptorPool descriptor_pool{};VkDescriptorSet set{};VkShaderModule module{};VkPipeline pipeline{};
    std::array<Q019Buffer,8> buffers{};std::uint64_t owned{};q::uint units{};fs::path out;std::ofstream journal;Clock::time_point started=Clock::now();
    ~Q019Context(){
        if(device){
            if(pipeline)vkDestroyPipeline(device,pipeline,nullptr);if(module)vkDestroyShaderModule(device,module,nullptr);
            if(descriptor_pool)vkDestroyDescriptorPool(device,descriptor_pool,nullptr);if(layout)vkDestroyPipelineLayout(device,layout,nullptr);if(set_layout)vkDestroyDescriptorSetLayout(device,set_layout,nullptr);
            for(auto b:buffers){if(b.mapped)vkUnmapMemory(device,b.memory);if(b.buffer)vkDestroyBuffer(device,b.buffer,nullptr);if(b.memory){Ledger::instance().release(device,b.memory);vkFreeMemory(device,b.memory,nullptr);}}
            if(query)vkDestroyQueryPool(device,query,nullptr);if(fence)vkDestroyFence(device,fence,nullptr);if(pool)vkDestroyCommandPool(device,pool,nullptr);vkDestroyDevice(device,nullptr);
        }
        if(instance)vkDestroyInstance(instance,nullptr);
    }
    void init(const fs::path& output,const std::vector<q::uint>& shader){
        out=output;journal.open(out/"dispatches.jsonl");require(bool(journal),"journal open failed");
        VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};app.pApplicationName="M001 quadratic019 isolated correctness";app.apiVersion=VK_API_VERSION_1_3;
        VkInstanceCreateInfo ic{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};ic.pApplicationInfo=&app;vkcheck(vkCreateInstance(&ic,nullptr,&instance));
        q::uint count=0;vkcheck(vkEnumeratePhysicalDevices(instance,&count,nullptr));std::vector<VkPhysicalDevice> devices(count);vkcheck(vkEnumeratePhysicalDevices(instance,&count,devices.data()));
        for(auto d:devices){VkPhysicalDeviceProperties p{};vkGetPhysicalDeviceProperties(d,&p);if(std::string(p.deviceName)=="AMD Radeon 8060S Graphics (RADV STRIX_HALO)"){require(!physical,"ambiguous target device");physical=d;}}
        require(physical,"required exact target device unavailable");VkPhysicalDeviceProperties2 p2{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};p2.pNext=&driver;vkGetPhysicalDeviceProperties2(physical,&p2);properties=p2.properties;
        require(properties.apiVersion>=VK_API_VERSION_1_3 && properties.limits.maxPerStageDescriptorStorageBuffers>=8 && properties.limits.maxComputeWorkGroupInvocations>=32,"device compute limits unsupported");
        vkGetPhysicalDeviceMemoryProperties(physical,&memories);count=0;vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,nullptr);std::vector<VkQueueFamilyProperties> queues(count);vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,queues.data());
        family=UINT32_MAX;for(q::uint j=0;j<count;j++)if((queues[j].queueFlags&VK_QUEUE_COMPUTE_BIT)&&queues[j].timestampValidBits){family=j;bits=queues[j].timestampValidBits;break;}
        require(family!=UINT32_MAX && bits<=64,"compute queue/timestamp unavailable");float priority=1;
        VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};qi.queueFamilyIndex=family;qi.queueCount=1;qi.pQueuePriorities=&priority;
        VkDeviceCreateInfo di{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};di.queueCreateInfoCount=1;di.pQueueCreateInfos=&qi;vkcheck(vkCreateDevice(physical,&di,nullptr,&device));vkGetDeviceQueue(device,family,0,&queue);
        VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=family;pi.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;vkcheck(vkCreateCommandPool(device,&pi,nullptr,&pool));
        VkCommandBufferAllocateInfo ca{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ca.commandPool=pool;ca.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ca.commandBufferCount=1;vkcheck(vkAllocateCommandBuffers(device,&ca,&command));
        VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};vkcheck(vkCreateFence(device,&fi,nullptr,&fence));VkQueryPoolCreateInfo qc{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};qc.queryType=VK_QUERY_TYPE_TIMESTAMP;qc.queryCount=2;vkcheck(vkCreateQueryPool(device,&qc,nullptr,&query));
        std::array<VkDescriptorSetLayoutBinding,8> bindings{};for(q::uint j=0;j<8;j++)bindings[j]={j,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,1,VK_SHADER_STAGE_COMPUTE_BIT,nullptr};
        VkDescriptorSetLayoutCreateInfo si{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};si.bindingCount=8;si.pBindings=bindings.data();vkcheck(vkCreateDescriptorSetLayout(device,&si,nullptr,&set_layout));
        VkPushConstantRange pc{VK_SHADER_STAGE_COMPUTE_BIT,0,16};VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};li.setLayoutCount=1;li.pSetLayouts=&set_layout;li.pushConstantRangeCount=1;li.pPushConstantRanges=&pc;vkcheck(vkCreatePipelineLayout(device,&li,nullptr,&layout));
        VkDescriptorPoolSize ds{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,8};VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};dp.maxSets=1;dp.poolSizeCount=1;dp.pPoolSizes=&ds;vkcheck(vkCreateDescriptorPool(device,&dp,nullptr,&descriptor_pool));
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};da.descriptorPool=descriptor_pool;da.descriptorSetCount=1;da.pSetLayouts=&set_layout;vkcheck(vkAllocateDescriptorSets(device,&da,&set));
        VkShaderModuleCreateInfo sm{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};sm.codeSize=shader.size()*4;sm.pCode=shader.data();vkcheck(vkCreateShaderModule(device,&sm,nullptr,&module));
        VkComputePipelineCreateInfo cp{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};cp.layout=layout;cp.stage.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;cp.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;cp.stage.module=module;cp.stage.pName="main";vkcheck(vkCreateComputePipelines(device,VK_NULL_HANDLE,1,&cp,nullptr,&pipeline));
    }
    void allocate(q::uint j,VkDeviceSize bytes,const void* data){
        auto& b=buffers[j];b.bytes=bytes;require(bytes>0&&bytes<=properties.limits.maxStorageBufferRange,"storage range unsupported");
        VkBufferCreateInfo bc{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};bc.size=bytes;bc.usage=VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;bc.sharingMode=VK_SHARING_MODE_EXCLUSIVE;vkcheck(vkCreateBuffer(device,&bc,nullptr,&b.buffer));
        VkMemoryRequirements req{};vkGetBufferMemoryRequirements(device,b.buffer,&req);q::uint type=UINT32_MAX;
        constexpr auto flags=VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
        for(q::uint k=0;k<memories.memoryTypeCount;k++)if((req.memoryTypeBits&(1u<<k))&&(memories.memoryTypes[k].propertyFlags&flags)==flags){type=k;break;}
        require(type!=UINT32_MAX,"host coherent memory unavailable");owned+=req.size;require(owned<=8ull*1024*1024*1024,"owned allocation cap");
        VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};ai.allocationSize=req.size;ai.memoryTypeIndex=type;vkcheck(vkAllocateMemory(device,&ai,nullptr,&b.memory));Ledger::instance().allocate(device,b.memory,req.size,type,flags,bc.usage);
        vkcheck(vkBindBufferMemory(device,b.buffer,b.memory,0));vkcheck(vkMapMemory(device,b.memory,0,VK_WHOLE_SIZE,0,&b.mapped));
        if(data)std::memcpy(b.mapped,data,std::size_t(bytes));else std::memset(b.mapped,0,std::size_t(bytes));
        VkDescriptorBufferInfo info{b.buffer,0,bytes};VkWriteDescriptorSet write{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};write.dstSet=set;write.dstBinding=j;write.descriptorCount=1;write.descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;write.pBufferInfo=&info;vkUpdateDescriptorSets(device,1,&write,0,nullptr);
    }
    void dispatch(q::uint mode,q::uint stage,q::uint start,q::uint count){
        require(std::chrono::duration<double>(Clock::now()-started).count()<180,"native wall guard");
        auto label=std::string(mode==0?"geometry":mode==1?"fit":"filter")+"-s"+std::to_string(stage)+"-p"+std::to_string(start);
        Ledger::instance().phase(label);journal<<"{\"event\":\"begin\",\"unit\":"<<units<<",\"label\":"<<std::quoted(label)<<",\"mode\":"<<mode<<",\"stage\":"<<stage<<",\"start\":"<<start<<",\"count\":"<<count<<"}\n";journal.flush();
        vkcheck(vkResetFences(device,1,&fence));vkcheck(vkResetCommandBuffer(command,0));VkCommandBufferBeginInfo cb{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};cb.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;vkcheck(vkBeginCommandBuffer(command,&cb));
        VkMemoryBarrier before{VK_STRUCTURE_TYPE_MEMORY_BARRIER};before.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT|VK_ACCESS_SHADER_WRITE_BIT;before.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;
        vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&before,0,nullptr,0,nullptr);
        vkCmdResetQueryPool(command,query,0,2);vkCmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);
        vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline);vkCmdBindDescriptorSets(command,VK_PIPELINE_BIND_POINT_COMPUTE,layout,0,1,&set,0,nullptr);
        std::array<q::uint,4> push{mode,stage,start,count};vkCmdPushConstants(command,layout,VK_SHADER_STAGE_COMPUTE_BIT,0,16,push.data());vkCmdDispatch(command,(count+31)/32,1,1);
        VkMemoryBarrier after{VK_STRUCTURE_TYPE_MEMORY_BARRIER};after.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;after.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
        vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&after,0,nullptr,0,nullptr);
        vkCmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,1);vkcheck(vkEndCommandBuffer(command));VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};submit.commandBufferCount=1;submit.pCommandBuffers=&command;vkcheck(vkQueueSubmit(queue,1,&submit,fence));
        VkResult wait=vkWaitForFences(device,1,&fence,VK_TRUE,250000000ull);
        if(wait!=VK_SUCCESS){journal<<"{\"event\":\"incomplete\",\"unit\":"<<units<<",\"wait_result\":"<<int(wait)<<"}\n";journal.flush();Ledger::instance().save(out/"allocation-ledger.json");std::ofstream(out/"failure.txt")<<"bounded fence incomplete; no teardown claim\n";std::_Exit(3);}
        std::uint64_t ticks[2]{};vkcheck(vkGetQueryPoolResults(device,query,0,2,sizeof ticks,ticks,8,VK_QUERY_RESULT_64_BIT));
        auto mask=bits==64?UINT64_MAX:((std::uint64_t(1)<<bits)-1);double us=double((ticks[1]-ticks[0])&mask)*properties.limits.timestampPeriod/1000.;
        journal<<std::setprecision(17)<<"{\"event\":\"complete\",\"unit\":"<<units<<",\"timestamp_begin\":"<<ticks[0]<<",\"timestamp_end\":"<<ticks[1]<<",\"gpu_us_diagnostic\":"<<us<<"}\n";journal.flush();++units;
        require(std::isfinite(us)&&us<=250000,"GPU unit duration guard");std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
};
static int replay_geometry(int argc,char** argv){
    require(argc==6&&std::string(argv[2])=="--input"&&std::string(argv[4])=="--out","CPU geometry replay usage");
    auto s=load(argv[3]);s.geometry=read<float>(fs::path(argv[3])/"geometry.f32",s.size()*8);
    for(q::uint p=0;p<s.size();p++){float norm2=0;for(q::uint a=0;a<8;a++){float x=s.geometry[p*8+a];require(std::isfinite(x),"geometry nonfinite");if(!s.hits[p*8+7])require(x==0,"nonzero miss geometry");if(a>=4&&a<=6)norm2+=x*x;}
        if(s.hits[p*8+7])require(std::abs(std::sqrt(norm2)-1)<=1e-4f,"geometry normal not unit");}
    fs::path out=argv[5];require(!fs::exists(out)&&fs::create_directory(out),"output exists or parent missing");q::active=&s;
    for(q::uint stage=0;stage<3;stage++)for(q::uint p=0;p<s.size();p++)q::q_fit(p,1u<<stage,stage);
    for(q::uint stage=0;stage<3;stage++)for(q::uint p=0;p<s.size();p++)q::q_apply(p,1u<<stage,stage);
    for(const auto* v:{&s.coefficients,&s.stages,&s.unclipped})for(float x:*v)require(std::isfinite(x),"nonfinite geometry replay");
    write(out/"geometry.f32",s.geometry);write(out/"coefficients.f32",s.coefficients);write(out/"maps.u32",s.maps);write(out/"stages.f32",s.stages);write(out/"unclipped.f32",s.unclipped);
    std::ofstream(out/"complete.json")<<"{\"schema\":\"m001-q019-native-geometry-cpu/1\",\"complete\":true,\"gpu_initialized\":false}\n";return 0;
}
int main(int argc,char** argv){
    if(argc>1&&std::string(argv[1])=="--cpu-check")return m001_q019_cpu_main(argc,argv);
    fs::path out;
    try{
        if(argc>1&&std::string(argv[1])=="--cpu-replay-geometry")return replay_geometry(argc,argv);
        require(argc==8&&std::string(argv[1])=="--gpu"&&std::string(argv[2])=="--input"&&std::string(argv[4])=="--out"&&std::string(argv[6])=="--shader","usage: --gpu --input INPUT --out NEW_OUTPUT --shader SPIRV");
        auto s=load(argv[3]);fs::path shaderpath=argv[7];require(fs::is_regular_file(shaderpath)&&fs::file_size(shaderpath)>=20&&fs::file_size(shaderpath)%4==0,"invalid SPIR-V size/path");
        auto shader=read<q::uint>(shaderpath,fs::file_size(shaderpath)/4);require(shader[0]==0x07230203,"invalid SPIR-V magic");
        fs::path candidate=argv[5];require(!fs::exists(candidate),"output exists");require(fs::create_directory(candidate),"output parent missing");out=candidate;
        q::uint units=0;{
            Q019Context c;Ledger::instance().phase("startup");c.init(out,shader);
            c.allocate(0,s.hits.size()*4,s.hits.data());c.allocate(1,80,s.camera.data());c.allocate(2,s.geometry.size()*4,nullptr);c.allocate(3,s.coefficients.size()*4,nullptr);
            c.allocate(4,s.maps.size()*4,nullptr);c.allocate(5,s.sources.size()*4,s.sources.data());c.allocate(6,s.stages.size()*4,nullptr);c.allocate(7,s.unclipped.size()*4,nullptr);
            c.dispatch(0,0,0,s.size());for(q::uint stage=0;stage<3;stage++)for(q::uint p=0;p<s.size();p+=128)c.dispatch(1,stage,p,std::min(128u,s.size()-p));
            for(q::uint stage=0;stage<3;stage++)c.dispatch(2,stage,0,s.size());units=c.units;
            std::memcpy(s.geometry.data(),c.buffers[2].mapped,s.geometry.size()*4);std::memcpy(s.coefficients.data(),c.buffers[3].mapped,s.coefficients.size()*4);std::memcpy(s.maps.data(),c.buffers[4].mapped,s.maps.size()*4);
            std::memcpy(s.stages.data(),c.buffers[6].mapped,s.stages.size()*4);std::memcpy(s.unclipped.data(),c.buffers[7].mapped,s.unclipped.size()*4);
            std::ofstream(out/"device.json")<<std::setprecision(17)<<"{\"name\":"<<std::quoted(c.properties.deviceName)<<",\"driver_name\":"<<std::quoted(c.driver.driverName)<<",\"driver_info\":"<<std::quoted(c.driver.driverInfo)<<",\"vendor_id\":"<<c.properties.vendorID<<",\"device_id\":"<<c.properties.deviceID<<",\"driver_version\":"<<c.properties.driverVersion<<",\"api_version\":"<<c.properties.apiVersion<<",\"queue_family\":"<<c.family<<",\"timestamp_valid_bits\":"<<c.bits<<",\"timestamp_period_ns\":"<<c.properties.limits.timestampPeriod<<",\"owned_bytes\":"<<c.owned<<"}\n";
        }
        Ledger::instance().save(out/"allocation-ledger.json");
        write(out/"geometry.f32",s.geometry);write(out/"coefficients.f32",s.coefficients);write(out/"maps.u32",s.maps);write(out/"stages.f32",s.stages);write(out/"unclipped.f32",s.unclipped);
        std::ofstream(out/"complete.json")<<"{\"schema\":\"m001-q019-native-gpu/1\",\"complete\":true,\"units\":"<<units<<",\"new_primary_paths\":0,\"new_pt_paths\":0,\"quality_admitted\":false,\"accepted_timing\":false}\n";std::cout<<"GPU replay complete; independent admission required\n";return 0;
    }catch(const std::exception& e){if(!out.empty()&&fs::is_directory(out)){Ledger::instance().save(out/"allocation-ledger.json");std::ofstream(out/"failure.txt")<<e.what()<<'\n';}std::cerr<<e.what()<<'\n';return 2;}
}

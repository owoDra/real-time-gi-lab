// Dormant standalone M001 host. No Renderer/default CMake linkage.
// SDK resource helpers derive from the retained N010 ddgi_volume_bringup.cpp;
// that diagnostic and the SDK are unchanged. This adapter needs its own admission.
#include "ddgi_contract.hpp"
#include "b002_hwrt.hpp"
#include "allocation_ledger.hpp"
#include <rtxgi/ddgi/gfx/DDGIVolume_VK.h>
#include <rtxgi/VulkanExtensions.h>
#include <chrono>
#include <cstring>
#include <functional>
#include <iomanip>
#include <iostream>
#include <thread>

namespace fs=std::filesystem;
namespace D=rtxgi::vulkan;
namespace b=phos::gi::research::lane_b;
using Ledger=phos::gi::research::n010::AllocationLedger;
using Clock=std::chrono::steady_clock;
static void check(VkResult r){m001::require(r==VK_SUCCESS,"Vulkan operation failed");}
static void sdk_check(rtxgi::ERTXGIStatus r){m001::require(r==rtxgi::ERTXGIStatus::OK,"SDK operation failed");}
struct Buffer { VkBuffer handle{}; VkDeviceMemory memory{}; void* mapped{}; VkDeviceSize bytes{}; };
struct Image { VkImage handle{}; VkDeviceMemory memory{}; VkImageView view{}; uint32_t w{},h{},layers{},channels{}; };
struct Kernel { VkShaderModule module{}; VkPipeline pipeline{}; };
struct Context {
    VkPhysicalDevice physical{};VkDevice device{};VkQueue queue{};uint32_t family{},subgroup{},valid_bits{};
    VkPhysicalDeviceMemoryProperties memory{};VkPhysicalDeviceProperties properties{};
    VkDescriptorSetLayout sdk_set_layout{},adapter_set_layout{};VkPipelineLayout sdk_layout{},adapter_layout{};
    VkDescriptorPool descriptors{};VkSampler sampler{};VkCommandPool pool{};VkCommandBuffer command{};
    VkFence fence{};VkQueryPool query{};uint64_t owned_bytes{};fs::path out;
    std::vector<Buffer> buffers;std::vector<Image> images;std::vector<Kernel> kernels;
    std::ofstream journal;Clock::time_point started=Clock::now();
    Context(b::B002VulkanContext& base,const fs::path& output):physical(base.physical_device()),device(base.device()),
      queue(base.queue()),family(base.queue_family()),out(output),journal(output/"dispatches.jsonl") {
        buffers.reserve(32);images.reserve(12);kernels.reserve(10);
        vkGetPhysicalDeviceMemoryProperties(physical,&memory);vkGetPhysicalDeviceProperties(physical,&properties);
        VkPhysicalDeviceSubgroupProperties sg{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SUBGROUP_PROPERTIES};
        VkPhysicalDeviceProperties2 p{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};p.pNext=&sg;vkGetPhysicalDeviceProperties2(physical,&p);
        subgroup=sg.subgroupSize;m001::require(subgroup==32 || subgroup==64,"unsupported subgroup width");
        m001::require((sg.supportedStages&VK_SHADER_STAGE_COMPUTE_BIT) && (sg.supportedOperations&VK_SUBGROUP_FEATURE_ARITHMETIC_BIT),"subgroup arithmetic required");
        uint32_t n=0;vkGetPhysicalDeviceQueueFamilyProperties(physical,&n,nullptr);std::vector<VkQueueFamilyProperties> q(n);
        vkGetPhysicalDeviceQueueFamilyProperties(physical,&n,q.data());valid_bits=q.at(family).timestampValidBits;
        m001::require(valid_bits>0 && valid_bits<=64,"timestamp bits");
        rtxgi::SetInsertPerfMarkers(false);D::LoadExtensions(device);
        VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=family;pi.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        check(vkCreateCommandPool(device,&pi,nullptr,&pool));VkCommandBufferAllocateInfo ci{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
        ci.commandPool=pool;ci.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ci.commandBufferCount=1;check(vkAllocateCommandBuffers(device,&ci,&command));
        VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};check(vkCreateFence(device,&fi,nullptr,&fence));
        VkQueryPoolCreateInfo qi{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};qi.queryType=VK_QUERY_TYPE_TIMESTAMP;qi.queryCount=2;check(vkCreateQueryPool(device,&qi,nullptr,&query));
    }
    ~Context() {
        // Every submitted unit completed its bounded fence, except timeout paths which _Exit.
        for(auto k:kernels){if(k.pipeline)vkDestroyPipeline(device,k.pipeline,nullptr);if(k.module)vkDestroyShaderModule(device,k.module,nullptr);}
        if(descriptors)vkDestroyDescriptorPool(device,descriptors,nullptr);
        if(sampler)vkDestroySampler(device,sampler,nullptr);
        for(auto l:{sdk_layout,adapter_layout})if(l)vkDestroyPipelineLayout(device,l,nullptr);
        for(auto l:{sdk_set_layout,adapter_set_layout})if(l)vkDestroyDescriptorSetLayout(device,l,nullptr);
        for(auto i:images){if(i.view)vkDestroyImageView(device,i.view,nullptr);if(i.handle)vkDestroyImage(device,i.handle,nullptr);if(i.memory){Ledger::instance().release(device,i.memory);vkFreeMemory(device,i.memory,nullptr);}}
        for(auto b:buffers){if(b.mapped)vkUnmapMemory(device,b.memory);if(b.handle)vkDestroyBuffer(device,b.handle,nullptr);if(b.memory){Ledger::instance().release(device,b.memory);vkFreeMemory(device,b.memory,nullptr);}}
        if(query)vkDestroyQueryPool(device,query,nullptr);if(fence)vkDestroyFence(device,fence,nullptr);if(pool)vkDestroyCommandPool(device,pool,nullptr);
    }
    void dispatch(const std::string& label,const std::function<void()>& record) {
        m001::require(std::chrono::duration<double>(Clock::now()-started).count()<180,"host wall guard reached before next unit");
        Ledger::instance().phase(label);journal<<"{\"event\":\"begin\",\"unit\":\""<<label<<"\"}\n";journal.flush();
        check(vkResetFences(device,1,&fence));check(vkResetCommandBuffer(command,0));
        VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;check(vkBeginCommandBuffer(command,&bi));
        vkCmdResetQueryPool(command,query,0,2);vkCmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);
        record();vkCmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,1);check(vkEndCommandBuffer(command));
        VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&command;check(vkQueueSubmit(queue,1,&si,fence));
        VkResult wait=vkWaitForFences(device,1,&fence,VK_TRUE,250000000ull);
        if(wait!=VK_SUCCESS){journal<<"{\"event\":\"incomplete\",\"wait_result\":"<<int(wait)<<"}\n";journal.flush();
            Ledger::instance().save(out/"allocation-ledger.json");std::ofstream(out/"failure.txt")<<"bounded fence failed; no completion/teardown claim\n";
            std::_Exit(3);}
        uint64_t ts[2]{};check(vkGetQueryPoolResults(device,query,0,2,sizeof ts,ts,8,VK_QUERY_RESULT_64_BIT));
        uint64_t mask=valid_bits==64?UINT64_MAX:(uint64_t(1)<<valid_bits)-1;
        double us=double((ts[1]-ts[0])&mask)*properties.limits.timestampPeriod/1000;
        journal<<std::setprecision(17)<<"{\"event\":\"complete\",\"unit\":\""<<label<<"\",\"timestamp_begin\":"<<ts[0]<<",\"timestamp_end\":"<<ts[1]<<",\"gpu_us_diagnostic\":"<<us<<"}\n";journal.flush();
        m001::require(us<=250000,"GPU unit duration guard; stop after completed unit");
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    void memory_barrier(VkAccessFlags src,VkAccessFlags dst,VkPipelineStageFlags a,VkPipelineStageFlags z) {
        VkMemoryBarrier mb{VK_STRUCTURE_TYPE_MEMORY_BARRIER};mb.srcAccessMask=src;mb.dstAccessMask=dst;
        vkCmdPipelineBarrier(command,a,z,0,1,&mb,0,nullptr,0,nullptr);
    }
    // Resource creation helpers follow below.
    void allocate(const VkMemoryRequirements& req,VkMemoryPropertyFlags flags,VkDeviceMemory& output,uint32_t usage) {
        uint32_t type=UINT32_MAX;for(uint32_t j=0;j<memory.memoryTypeCount;++j)if((req.memoryTypeBits&(1u<<j))&&(memory.memoryTypes[j].propertyFlags&flags)==flags){type=j;break;}
        if(type==UINT32_MAX)throw std::runtime_error("required memory type unavailable");
        VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};ai.allocationSize=req.size;owned_bytes+=req.size;m001::require(owned_bytes<=7ull*1024*1024*1024,"adapter allocation cap");ai.memoryTypeIndex=type;check(vkAllocateMemory(device,&ai,nullptr,&output));
        Ledger::instance().allocate(device,output,req.size,type,flags,usage);
    }
    Buffer& buffer(VkDeviceSize bytes,VkBufferUsageFlags usage) {
        buffers.emplace_back();auto& b=buffers.back();b.bytes=bytes;
        VkBufferCreateInfo bi{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};bi.size=bytes;bi.usage=usage;bi.sharingMode=VK_SHARING_MODE_EXCLUSIVE;check(vkCreateBuffer(device,&bi,nullptr,&b.handle));
        VkMemoryRequirements req{};vkGetBufferMemoryRequirements(device,b.handle,&req);allocate(req,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,b.memory,usage);
        check(vkBindBufferMemory(device,b.handle,b.memory,0));check(vkMapMemory(device,b.memory,0,VK_WHOLE_SIZE,0,&b.mapped));return b;
    }
    Image& image(const rtxgi::DDGIVolumeDesc& desc,rtxgi::EDDGIVolumeTextureType type,rtxgi::EDDGIVolumeTextureFormat format,uint32_t channels) {
        images.emplace_back();auto& i=images.back();i.channels=channels;rtxgi::GetDDGIVolumeTextureDimensions(desc,type,i.w,i.h,i.layers);
        auto vkformat=D::GetDDGIVolumeTextureFormat(type,format);VkFormatProperties fp{};vkGetPhysicalDeviceFormatProperties(physical,vkformat,&fp);
        if((fp.optimalTilingFeatures & (VK_FORMAT_FEATURE_STORAGE_IMAGE_BIT|VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT|VK_FORMAT_FEATURE_SAMPLED_IMAGE_FILTER_LINEAR_BIT)) != (VK_FORMAT_FEATURE_STORAGE_IMAGE_BIT|VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT|VK_FORMAT_FEATURE_SAMPLED_IMAGE_FILTER_LINEAR_BIT))throw std::runtime_error("unsupported storage image format");
        VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};ii.imageType=VK_IMAGE_TYPE_2D;ii.extent={i.w,i.h,1};ii.mipLevels=1;ii.arrayLayers=i.layers;ii.format=vkformat;ii.tiling=VK_IMAGE_TILING_OPTIMAL;ii.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED;ii.samples=VK_SAMPLE_COUNT_1_BIT;ii.sharingMode=VK_SHARING_MODE_EXCLUSIVE;ii.usage=VK_IMAGE_USAGE_STORAGE_BIT|VK_IMAGE_USAGE_SAMPLED_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
        check(vkCreateImage(device,&ii,nullptr,&i.handle));VkMemoryRequirements req{};vkGetImageMemoryRequirements(device,i.handle,&req);allocate(req,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,i.memory,ii.usage);check(vkBindImageMemory(device,i.handle,i.memory,0));
        VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};vi.image=i.handle;vi.viewType=VK_IMAGE_VIEW_TYPE_2D_ARRAY;vi.format=vkformat;vi.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,i.layers};check(vkCreateImageView(device,&vi,nullptr,&i.view));return i;
    }
    Kernel kernel(const fs::path& path,const char* entry,VkPipelineLayout pipeline_layout) {
        kernels.emplace_back();auto& k=kernels.back();std::ifstream in(path,std::ios::binary|std::ios::ate);if(!in)throw std::runtime_error("missing SPIR-V: "+path.string());auto bytes=in.tellg();if(bytes<=0 || size_t(bytes)%4)throw std::runtime_error("invalid SPIR-V size");std::vector<uint32_t> words(size_t(bytes)/4);in.seekg(0);in.read(reinterpret_cast<char*>(words.data()),bytes);if(!in || words[0]!=0x07230203)throw std::runtime_error("bad SPIR-V");
        VkShaderModuleCreateInfo mi{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};mi.codeSize=size_t(bytes);mi.pCode=words.data();check(vkCreateShaderModule(device,&mi,nullptr,&k.module));
        VkComputePipelineCreateInfo pi{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};pi.layout=pipeline_layout;pi.stage.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;pi.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;pi.stage.module=k.module;pi.stage.pName=entry;check(vkCreateComputePipelines(device,VK_NULL_HANDLE,1,&pi,nullptr,&k.pipeline));return k;
    }
    void barrier(Image i,VkImageLayout from,VkImageLayout to,VkAccessFlags src,VkAccessFlags dst,VkPipelineStageFlags a,VkPipelineStageFlags b) {
        VkImageMemoryBarrier bi{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};bi.oldLayout=from;bi.newLayout=to;bi.srcAccessMask=src;bi.dstAccessMask=dst;bi.srcQueueFamilyIndex=bi.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;bi.image=i.handle;bi.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,i.layers};vkCmdPipelineBarrier(command,a,b,0,0,nullptr,0,nullptr,1,&bi);
    }
    void clear(Image i,bool initial,float radiance=0,float distance=0) {
        barrier(i,initial?VK_IMAGE_LAYOUT_UNDEFINED:VK_IMAGE_LAYOUT_GENERAL,VK_IMAGE_LAYOUT_GENERAL,
            initial?0:VK_ACCESS_MEMORY_READ_BIT|VK_ACCESS_MEMORY_WRITE_BIT,VK_ACCESS_TRANSFER_WRITE_BIT,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT);
        VkClearColorValue v{};v.float32[0]=v.float32[1]=v.float32[2]=radiance;v.float32[3]=distance;
        VkImageSubresourceRange range{VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,i.layers};vkCmdClearColorImage(command,i.handle,VK_IMAGE_LAYOUT_GENERAL,&v,1,&range);
        barrier(i,VK_IMAGE_LAYOUT_GENERAL,VK_IMAGE_LAYOUT_GENERAL,VK_ACCESS_TRANSFER_WRITE_BIT,VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT);
    }
    void capture(Image image,Buffer& staging,const std::string& name) {
        VkDeviceSize bytes=VkDeviceSize(image.w)*image.h*image.layers*image.channels*4;
        m001::require(bytes<=staging.bytes,"capture staging range");
        dispatch("readback-"+name,[&]{
            barrier(image,VK_IMAGE_LAYOUT_GENERAL,VK_IMAGE_LAYOUT_GENERAL,VK_ACCESS_MEMORY_WRITE_BIT|VK_ACCESS_MEMORY_READ_BIT,VK_ACCESS_TRANSFER_READ_BIT,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT);
            VkBufferImageCopy copy{};copy.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,image.layers};copy.imageExtent={image.w,image.h,1};
            vkCmdCopyImageToBuffer(command,image.handle,VK_IMAGE_LAYOUT_GENERAL,staging.handle,1,&copy);
            memory_barrier(VK_ACCESS_TRANSFER_WRITE_BIT,VK_ACCESS_HOST_READ_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT);
        });
        std::ofstream f(out/(name+".f32"),std::ios::binary);f.write(static_cast<const char*>(staging.mapped),std::streamsize(bytes));m001::require(bool(f),"capture write");
    }
};

static void layouts(Context& c) {
    VkDescriptorSetLayoutCreateInfo sl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};VkPushConstantRange pc{};
    VkPipelineLayoutCreateInfo pl{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};std::array<VkDescriptorSetLayoutBinding,7> sdk{};
    D::GetDDGIVolumeLayoutDescs(sl,pc,pl,sdk.data());check(vkCreateDescriptorSetLayout(c.device,&sl,nullptr,&c.sdk_set_layout));
    pl.pSetLayouts=&c.sdk_set_layout;check(vkCreatePipelineLayout(c.device,&pl,nullptr,&c.sdk_layout));
    std::vector<VkDescriptorSetLayoutBinding> adapter;
    for(auto [binding,type]:std::array<std::pair<uint32_t,VkDescriptorType>,10>{{
        {0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER},{1,VK_DESCRIPTOR_TYPE_STORAGE_IMAGE},{7,VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR},
        {8,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER},{9,VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER},{10,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER},
        {11,VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE},{12,VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE},{13,VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE},{14,VK_DESCRIPTOR_TYPE_SAMPLER}}})
        adapter.push_back({binding,type,1,VK_SHADER_STAGE_COMPUTE_BIT,nullptr});
    sl.bindingCount=uint32_t(adapter.size());sl.pBindings=adapter.data();check(vkCreateDescriptorSetLayout(c.device,&sl,nullptr,&c.adapter_set_layout));
    pc={VK_SHADER_STAGE_COMPUTE_BIT,0,sizeof(m001::Push)};pl.pSetLayouts=&c.adapter_set_layout;pl.pPushConstantRanges=&pc;check(vkCreatePipelineLayout(c.device,&pl,nullptr,&c.adapter_layout));
    std::array<VkDescriptorPoolSize,7> sizes{{{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,14},{VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,16},
        {VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,4},{VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,4},{VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE,12},{VK_DESCRIPTOR_TYPE_SAMPLER,4},{VK_DESCRIPTOR_TYPE_UNIFORM_TEXEL_BUFFER,1}}};
    VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};dp.maxSets=6;dp.poolSizeCount=uint32_t(sizes.size());dp.pPoolSizes=sizes.data();check(vkCreateDescriptorPool(c.device,&dp,nullptr,&c.descriptors));
    VkSamplerCreateInfo si{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};si.magFilter=si.minFilter=VK_FILTER_LINEAR;si.mipmapMode=VK_SAMPLER_MIPMAP_MODE_NEAREST;
    si.addressModeU=si.addressModeV=si.addressModeW=VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;si.maxLod=0;check(vkCreateSampler(c.device,&si,nullptr,&c.sampler));
}
static VkDescriptorSet descriptor(Context& c,VkDescriptorSetLayout layout) {
    VkDescriptorSetAllocateInfo ai{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};ai.descriptorPool=c.descriptors;ai.descriptorSetCount=1;ai.pSetLayouts=&layout;
    VkDescriptorSet set{};check(vkAllocateDescriptorSets(c.device,&ai,&set));return set;
}
struct Atlas { std::array<Image,6> images;Buffer constants,variability;VkDescriptorSet sdk_set{},trace_set{},gather_set{}; };
static void sdk_descriptor(Context& c,Atlas& a) {
    a.sdk_set=descriptor(c,c.sdk_set_layout);VkDescriptorBufferInfo cb{a.constants.handle,0,a.constants.bytes};
    std::array<VkDescriptorImageInfo,6> views{};std::array<VkWriteDescriptorSet,7> writes{};
    for(uint32_t j=0;j<7;++j){auto& w=writes[j];w.sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;w.dstSet=a.sdk_set;w.dstBinding=j;w.descriptorCount=1;
        w.descriptorType=j?VK_DESCRIPTOR_TYPE_STORAGE_IMAGE:VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        if(!j)w.pBufferInfo=&cb;else{views[j-1]={VK_NULL_HANDLE,a.images[j-1].view,VK_IMAGE_LAYOUT_GENERAL};w.pImageInfo=&views[j-1];}}
    vkUpdateDescriptorSets(c.device,uint32_t(writes.size()),writes.data(),0,nullptr);
}
static VkDescriptorSet adapter_descriptor(Context& c,const Atlas& current,const Atlas& previous,
    const b::B002HwrtTraversal& hwrt,const Buffer& frame,const Buffer& pixels) {
    VkDescriptorSet set=descriptor(c,c.adapter_set_layout);std::vector<VkWriteDescriptorSet> writes;
    std::array<VkDescriptorBufferInfo,4> bufs{{{current.constants.handle,0,current.constants.bytes},
        {hwrt.triangle_buffer().buffer,0,hwrt.triangle_buffer().size},{frame.handle,0,frame.bytes},{pixels.handle,0,pixels.bytes}}};
    std::array<uint32_t,4> numbers{0,8,9,10};
    for(size_t j=0;j<4;++j){VkWriteDescriptorSet w{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};w.dstSet=set;w.dstBinding=numbers[j];w.descriptorCount=1;
        w.descriptorType=j==2?VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER:VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;w.pBufferInfo=&bufs[j];writes.push_back(w);}
    std::array<VkDescriptorImageInfo,5> images{{{VK_NULL_HANDLE,current.images[0].view,VK_IMAGE_LAYOUT_GENERAL},
        {VK_NULL_HANDLE,previous.images[1].view,VK_IMAGE_LAYOUT_GENERAL},{VK_NULL_HANDLE,previous.images[2].view,VK_IMAGE_LAYOUT_GENERAL},
        {VK_NULL_HANDLE,previous.images[3].view,VK_IMAGE_LAYOUT_GENERAL},{c.sampler,VK_NULL_HANDLE,VK_IMAGE_LAYOUT_UNDEFINED}}};
    std::array<uint32_t,5> inum{1,11,12,13,14};
    for(size_t j=0;j<5;++j){VkWriteDescriptorSet w{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};w.dstSet=set;w.dstBinding=inum[j];w.descriptorCount=1;
        w.descriptorType=j==0?VK_DESCRIPTOR_TYPE_STORAGE_IMAGE:(j==4?VK_DESCRIPTOR_TYPE_SAMPLER:VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE);w.pImageInfo=&images[j];writes.push_back(w);}
    auto as=hwrt.top_level();VkWriteDescriptorSetAccelerationStructureKHR acc{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET_ACCELERATION_STRUCTURE_KHR};acc.accelerationStructureCount=1;acc.pAccelerationStructures=&as;
    VkWriteDescriptorSet w{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};w.pNext=&acc;w.dstSet=set;w.dstBinding=7;w.descriptorCount=1;w.descriptorType=VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR;writes.push_back(w);
    vkUpdateDescriptorSets(c.device,uint32_t(writes.size()),writes.data(),0,nullptr);return set;
}
static void attach(D::DDGIVolume& volume,const rtxgi::DDGIVolumeDesc& desc,const Atlas& a,const Context& c,const std::array<Kernel,8>& k) {
    D::DDGIVolumeResources r{};r.unmanaged.enabled=true;r.constantsBuffer=a.constants.handle;auto& u=r.unmanaged;u.pipelineLayout=c.sdk_layout;u.descriptorSet=a.sdk_set;
    u.probeRayData=a.images[0].handle;u.probeIrradiance=a.images[1].handle;u.probeDistance=a.images[2].handle;u.probeData=a.images[3].handle;u.probeVariability=a.images[4].handle;u.probeVariabilityAverage=a.images[5].handle;
    u.probeRayDataMemory=a.images[0].memory;u.probeIrradianceMemory=a.images[1].memory;u.probeDistanceMemory=a.images[2].memory;u.probeDataMemory=a.images[3].memory;u.probeVariabilityMemory=a.images[4].memory;u.probeVariabilityAverageMemory=a.images[5].memory;
    u.probeRayDataView=a.images[0].view;u.probeIrradianceView=a.images[1].view;u.probeDistanceView=a.images[2].view;u.probeDataView=a.images[3].view;u.probeVariabilityView=a.images[4].view;u.probeVariabilityAverageView=a.images[5].view;
    u.probeVariabilityReadback=a.variability.handle;u.probeVariabilityReadbackMemory=a.variability.memory;
    u.probeBlendingIrradianceModule=k[0].module;u.probeBlendingIrradiancePipeline=k[0].pipeline;u.probeBlendingDistanceModule=k[1].module;u.probeBlendingDistancePipeline=k[1].pipeline;
    u.probeRelocation={k[2].module,k[3].module,k[2].pipeline,k[3].pipeline};u.probeClassification={k[4].module,k[5].module,k[4].pipeline,k[5].pipeline};u.probeVariabilityPipelines={k[6].module,k[7].module,k[6].pipeline,k[7].pipeline};
    sdk_check(volume.Create(desc,r));volume.Update();auto packed=volume.GetDescGPUPacked();static_assert(sizeof(packed)==128);std::memcpy(a.constants.mapped,&packed,sizeof packed);
}
static void bind_adapter(Context& c,Kernel k,VkDescriptorSet set,m001::Push push,uint32_t x,uint32_t y=1) {
    vkCmdBindPipeline(c.command,VK_PIPELINE_BIND_POINT_COMPUTE,k.pipeline);vkCmdBindDescriptorSets(c.command,VK_PIPELINE_BIND_POINT_COMPUTE,c.adapter_layout,0,1,&set,0,nullptr);
    vkCmdPushConstants(c.command,c.adapter_layout,VK_SHADER_STAGE_COMPUTE_BIT,0,sizeof push,&push);vkCmdDispatch(c.command,x,y,1);
    c.memory_barrier(VK_ACCESS_SHADER_WRITE_BIT,VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT);
}
static void binary(const fs::path& path,const void* data,size_t size) {std::ofstream f(path,std::ios::binary);f.write(static_cast<const char*>(data),std::streamsize(size));m001::require(bool(f),"binary write");}
static void pfm(const fs::path& path,const m001::State& s,const float* pixels,uint32_t channel) {
    std::ofstream f(path,std::ios::binary);f<<"PF\n"<<s.width<<' '<<s.height<<"\n-1.0\n";
    for(uint32_t y=s.height;y-->0;)for(uint32_t x=0;x<s.width;++x){float v=pixels[4*(size_t(y)*s.width+x)+channel];float rgb[]{v,v,v};f.write(reinterpret_cast<const char*>(rgb),sizeof rgb);}
    m001::require(bool(f),"PFM write");
}
struct Options {
    fs::path state,out,shaders,reduction,adapter;
    uint32_t side=2,rays=128,vertices=2;
    std::string mode="scene";bool cpu=false;
};
static uint32_t number(const std::string& text) {
    m001::require(!text.empty() && text.find_first_not_of("0123456789")==std::string::npos,"unsigned decimal option required");
    auto n=std::stoull(text);m001::require(n<=UINT32_MAX,"integer option overflow");return uint32_t(n);
}
static Options options(int argc,char** argv) {
    Options o;std::vector<std::string> seen;
    for(int k=1;k<argc;++k){std::string arg=argv[k];m001::require(std::find(seen.begin(),seen.end(),arg)==seen.end(),"duplicate option");seen.push_back(arg);
        if(arg=="--cpu-check"){o.cpu=true;continue;}m001::require(k+1<argc,"missing option value");std::string v=argv[++k];
        if(arg=="--state")o.state=v;else if(arg=="--out")o.out=v;else if(arg=="--sdk-shaders")o.shaders=v;
        else if(arg=="--reduction-shaders")o.reduction=v;else if(arg=="--adapter-shaders")o.adapter=v;
        else if(arg=="--grid-side")o.side=number(v);else if(arg=="--rays")o.rays=number(v);else if(arg=="--vertices")o.vertices=number(v);
        else if(arg=="--mode")o.mode=v;else throw std::runtime_error("unknown option");}
    m001::require(!o.state.empty() && !o.out.empty(),"state and new output required");
    m001::require(o.mode=="scene" || o.mode=="direct" || o.mode=="constant0" || o.mode=="constant1" || o.mode=="constant8","unsupported mode");
    m001::require(o.mode=="direct" ? o.vertices==1 : (o.vertices==2 || o.vertices==8),"mode/depth mismatch");
    if(!o.cpu)m001::require(!o.shaders.empty() && !o.reduction.empty() && !o.adapter.empty(),"three shader directories required");
    return o;
}
static void run(const Options& o,const m001::State& state,const m001::Grid& grid) {
    auto setup_start=Clock::now();b::B002VulkanContext base(false,b::kB002TargetDeviceName,true);
    std::vector<b::Triangle> triangles;
    for(const auto& t:state.triangles)triangles.push_back({{t.v0[0],t.v0[1],t.v0[2]},{t.v1[0],t.v1[1],t.v1[2]},
        {t.v2[0],t.v2[1],t.v2[2]},t.primitive,t.material,t.instance,true});
    b::B002HwrtTraversal hwrt(base,triangles,"",false);Context c(base,o.out);layouts(c);
    auto frame=c.buffer(sizeof(m001::Frame),VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT);std::memcpy(frame.mapped,&state.frame,sizeof state.frame);
    auto pixels=c.buffer(VkDeviceSize(state.width)*state.height*16,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    std::memset(pixels.mapped,0,size_t(pixels.bytes));
    rtxgi::DDGIVolumeDesc desc{};char name[]="M001 finite static adapter";desc.name=name;desc.rngSeed=305419896;
    desc.probeCounts={int(o.side),int(o.side),int(o.side)};desc.origin={grid.origin[0],grid.origin[1],grid.origin[2]};
    desc.probeSpacing={grid.spacing[0],grid.spacing[1],grid.spacing[2]};desc.probeNumRays=int(o.rays);
    desc.probeNumIrradianceTexels=8;desc.probeNumIrradianceInteriorTexels=6;desc.probeNumDistanceTexels=16;desc.probeNumDistanceInteriorTexels=14;
    desc.probeMaxRayDistance=state.frame.camera_forward_far[3];desc.probeHysteresis=0;desc.probeIrradianceEncodingGamma=1;
    desc.probeIrradianceThreshold=desc.probeBrightnessThreshold=1e6f;desc.probeDistanceExponent=50;
    desc.probeNormalBias=desc.probeViewBias=.01f*std::min({grid.spacing[0],grid.spacing[1],grid.spacing[2]});
    desc.probeRelocationEnabled=desc.probeClassificationEnabled=desc.probeVariabilityEnabled=false;
    desc.probeRayDataFormat=desc.probeIrradianceFormat=desc.probeDataFormat=rtxgi::EDDGIVolumeTextureFormat::F32x4;
    desc.probeDistanceFormat=rtxgi::EDDGIVolumeTextureFormat::F32x2;desc.probeVariabilityFormat=rtxgi::EDDGIVolumeTextureFormat::F32;
    std::array<Atlas,2> atlas;
    for(auto& a:atlas){a.constants=c.buffer(sizeof(rtxgi::DDGIVolumeDescGPUPacked),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);a.variability=c.buffer(8,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
        for(int j=0;j<6;++j){auto f=j==2 || j==5?rtxgi::EDDGIVolumeTextureFormat::F32x2:(j==4?rtxgi::EDDGIVolumeTextureFormat::F32:rtxgi::EDDGIVolumeTextureFormat::F32x4);
            a.images[j]=c.image(desc,rtxgi::EDDGIVolumeTextureType(j),f,j==2 || j==5?2:(j==4?1:4));}sdk_descriptor(c,a);}
    std::string blend="blend-"+std::to_string(o.rays);std::string wave=std::to_string(c.subgroup);
    std::array<Kernel,8> k{c.kernel(o.shaders/(blend+"-irradiance.spv"),"DDGIProbeBlendingCS",c.sdk_layout),c.kernel(o.shaders/(blend+"-distance.spv"),"DDGIProbeBlendingCS",c.sdk_layout),
        c.kernel(o.shaders/"relocation.spv","DDGIProbeRelocationCS",c.sdk_layout),c.kernel(o.shaders/"relocation-reset.spv","DDGIProbeRelocationResetCS",c.sdk_layout),
        c.kernel(o.shaders/"classification.spv","DDGIProbeClassificationCS",c.sdk_layout),c.kernel(o.shaders/"classification-reset.spv","DDGIProbeClassificationResetCS",c.sdk_layout),
        c.kernel(o.reduction/("reduction-wave"+wave+".spv"),"DDGIReductionCS",c.sdk_layout),c.kernel(o.reduction/("extra-reduction-wave"+wave+".spv"),"DDGIExtraReductionCS",c.sdk_layout)};
    auto trace=c.kernel(o.adapter/"TraceProbes.spv","TraceProbes",c.adapter_layout),gather=c.kernel(o.adapter/"GatherPixels.spv","GatherPixels",c.adapter_layout);
    std::array<D::DDGIVolume,2> volumes;
    for(int j=0;j<2;++j){attach(volumes[j],desc,atlas[j],c,k);atlas[j].trace_set=adapter_descriptor(c,atlas[j],atlas[1-j],hwrt,frame,pixels);
        atlas[j].gather_set=adapter_descriptor(c,atlas[j],atlas[j],hwrt,frame,pixels);binary(o.out/("constants-"+std::to_string(j)+".bin"),atlas[j].constants.mapped,size_t(atlas[j].constants.bytes));}
    m001::require(std::memcmp(atlas[0].constants.mapped,atlas[1].constants.mapped,128)==0,"ping-pong packed descriptors/rotation differ");
    VkDeviceSize max_bytes=0;for(auto image:atlas[0].images)max_bytes=std::max(max_bytes,VkDeviceSize(image.w)*image.h*image.layers*image.channels*4);
    auto& staging=c.buffer(max_bytes,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    std::ofstream metadata(o.out/"configuration.json");metadata<<std::setprecision(17)<<"{\"schema\":\"m001-ddgi-native/1\",\"mode\":\""<<o.mode<<"\",\"grid_side\":"<<o.side<<",\"rays\":"<<o.rays<<",\"vertices\":"<<o.vertices
        <<",\"seed\":305419896,\"rotation_updates_per_volume\":1,\"hysteresis\":0,\"gamma\":1,\"normal_view_bias\":"<<desc.probeNormalBias<<",\"brightness_threshold\":1000000,\"distance_exponent\":50,\"ray_max\":"<<desc.probeMaxRayDistance
        <<",\"origin\":["<<grid.origin[0]<<','<<grid.origin[1]<<','<<grid.origin[2]<<"],\"spacing\":["<<grid.spacing[0]<<','<<grid.spacing[1]<<','<<grid.spacing[2]<<"],\"subgroup\":"<<c.subgroup<<",\"timestamp_valid_bits\":"<<c.valid_bits
        <<",\"timestamp_period_ns\":"<<c.properties.limits.timestampPeriod<<",\"device\":\""<<base.device_name()<<"\",\"driver_name\":\""<<base.driver_name()<<"\",\"driver_info\":\""<<base.driver_info()<<"\",\"api_version\":"<<base.api_version()
        <<",\"timing_classification\":\"DIAGNOSTIC_UNCALIBRATED\",\"setup_wall_us\":"<<std::chrono::duration<double,std::micro>(Clock::now()-setup_start).count()<<",\"images\":[";
    for(int j=0;j<6;++j){auto i=atlas[0].images[j];metadata<<(j?",":"")<<"{\"type\":"<<j<<",\"w\":"<<i.w<<",\"h\":"<<i.h<<",\"layers\":"<<i.layers<<",\"channels\":"<<i.channels<<'}';}
    metadata<<"]}\n";metadata.close();m001::require(bool(metadata),"configuration write");
    c.dispatch("fresh-zero-initialize",[&]{for(auto& a:atlas)for(auto image:a.images)c.clear(image,true);});
    auto stage_plan=m001::stages(o.vertices);auto ray_tiles=m001::tiles(o.side*o.side*o.side*o.rays);
    for(auto stage:stage_plan){auto& current=atlas[stage.write];auto& previous=atlas[stage.read];
        std::string prefix="stage-"+std::to_string(stage.ordinal);
        c.dispatch(prefix+"-clear-destination",[&]{for(auto image:current.images)c.clear(image,false);});
        if(o.mode=="scene")for(auto tile:ray_tiles)c.dispatch(prefix+"-trace-"+std::to_string(tile.begin),[&]{
            bind_adapter(c,trace,current.trace_set,{stage.previous_ready,tile.begin,tile.count,0},(tile.count+63)/64);});
        else {float radiance=o.mode=="constant8"?8.f:(o.mode=="constant1"?1.f:0.f);
            c.dispatch(prefix+"-constant-ray-data",[&]{c.clear(current.images[0],false,radiance,1);});}
        c.dispatch(prefix+"-sdk-blend",[&]{auto ptr=&volumes[stage.write];sdk_check(D::UpdateDDGIVolumeProbes(c.command,1,&ptr));
            // The SDK's internal image barrier covers layer0; this whole-memory barrier covers every array layer.
            c.memory_barrier(VK_ACCESS_SHADER_WRITE_BIT,VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT);});
        for(int j=0;j<4;++j)c.capture(current.images[j],staging,prefix+"-current-"+std::to_string(j));
        for(int j=1;j<4;++j)c.capture(previous.images[j],staging,prefix+"-previous-"+std::to_string(j));
    }
    uint32_t final=stage_plan.empty()?0:stage_plan.back().write;
    c.dispatch("primary-direct-gather",[&]{bind_adapter(c,gather,atlas[final].gather_set,{o.vertices==1?0u:1u,0,0,0},(state.width+7)/8,(state.height+7)/8);
        c.memory_barrier(VK_ACCESS_SHADER_WRITE_BIT,VK_ACCESS_HOST_READ_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT);});
    const float* data=static_cast<const float*>(pixels.mapped);for(size_t j=0;j<size_t(state.width)*state.height*4;++j)m001::require(std::isfinite(data[j]),"nonfinite HDR pixel");
    binary(o.out/"pixels.f32",data,size_t(pixels.bytes));pfm(o.out/"direct.pfm",state,data,0);pfm(o.out/"indirect.pfm",state,data,1);pfm(o.out/"total.pfm",state,data,2);
    for(auto& volume:volumes)volume.Destroy();
}
int main(int argc,char** argv) {
    fs::path out;
    try {auto o=options(argc,argv);auto state=m001::load_state(o.state);auto g=m001::grid(state,o.side,o.rays);
        auto stages=m001::stages(o.vertices);auto tiles=m001::tiles(o.side*o.side*o.side*o.rays);
        m001::create_output(o.out);out=o.out;
        for(auto name:{"geometry-state.bin","frame-state.bin"})fs::copy_file(o.state/name,out/name);
        std::ofstream plan(out/"cpu-contract.json");plan<<"{\"gpu_initialized\":false,\"stage_count\":"<<stages.size()<<",\"tile_count_per_stage\":"<<tiles.size()<<",\"total_rays_per_stage\":"<<o.side*o.side*o.side*o.rays<<",\"frame_bytes\":128,\"triangle_stride\":64,\"push_bytes\":16}\n";plan.close();
        if(o.cpu){std::cout<<"CPU contract PASS; Vulkan NOT initialized\n";return 0;}
        Ledger::instance().phase("startup");run(o,state,g);Ledger::instance().save(out/"allocation-ledger.json");
        std::ofstream(out/"complete.json")<<"{\"capture_complete\":true,\"semantic_admission\":false,\"quality_admission\":false,\"speed_admission\":false}\n";
        std::cout<<"capture complete; independent admission required\n";return 0;
    }catch(const std::exception& error){if(!out.empty()){Ledger::instance().save(out/"allocation-ledger.json");std::ofstream(out/"failure.txt")<<error.what()<<'\n';}
        std::cerr<<error.what()<<'\n';return 2;}
}

// Isolated SDK resource/dispatch diagnostic; no scene or Renderer linkage.
#include <rtxgi/ddgi/gfx/DDGIVolume_VK.h>
#include <rtxgi/VulkanExtensions.h>
#include "allocation_ledger.hpp"
#include <array>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <stdexcept>
#include <vector>

namespace fs = std::filesystem;
namespace D = rtxgi::vulkan;
using Ledger = phos::gi::research::n010::AllocationLedger;
static void check(VkResult result) {
    if (result != VK_SUCCESS) throw std::runtime_error("Vulkan result "+std::to_string(result));
}
static void sdk_check(rtxgi::ERTXGIStatus result) {
    if (result != rtxgi::ERTXGIStatus::OK) throw std::runtime_error("RTXGI status "+std::to_string(int(result)));
}
struct Buffer { VkBuffer handle{}; VkDeviceMemory memory{}; void* mapped{}; VkDeviceSize bytes{}; };
struct Image { VkImage handle{}; VkDeviceMemory memory{}; VkImageView view{}; uint32_t w{},h{},layers{},channels{}; };
struct Kernel { VkShaderModule module{}; VkPipeline pipeline{}; };
struct Context {
    VkInstance instance{}; VkPhysicalDevice physical{}; VkDevice device{}; VkQueue queue{};
    uint32_t family{},subgroup{}; VkPhysicalDeviceMemoryProperties memory{};
    VkPhysicalDeviceProperties properties{};
    VkDescriptorSetLayout set_layout{}; VkPipelineLayout layout{}; VkDescriptorPool descriptors{};
    VkDescriptorSet set{}; VkCommandPool pool{}; VkCommandBuffer command{};
    std::vector<Buffer> buffers; std::vector<Image> images; std::vector<Kernel> kernels;
    Context() { buffers.reserve(8); images.reserve(6); kernels.reserve(8); }
    ~Context() {
        if (device) {
            vkDeviceWaitIdle(device);
            for (auto k:kernels) { if(k.pipeline)vkDestroyPipeline(device,k.pipeline,nullptr); if(k.module)vkDestroyShaderModule(device,k.module,nullptr); }
            if (descriptors) vkDestroyDescriptorPool(device,descriptors,nullptr);
            if (layout) vkDestroyPipelineLayout(device,layout,nullptr);
            if (set_layout) vkDestroyDescriptorSetLayout(device,set_layout,nullptr);
            for (auto i:images) { if(i.view)vkDestroyImageView(device,i.view,nullptr); if(i.handle)vkDestroyImage(device,i.handle,nullptr); if(i.memory){Ledger::instance().release(device,i.memory);vkFreeMemory(device,i.memory,nullptr);} }
            for (auto b:buffers) { if(b.mapped)vkUnmapMemory(device,b.memory); if(b.handle)vkDestroyBuffer(device,b.handle,nullptr); if(b.memory){Ledger::instance().release(device,b.memory);vkFreeMemory(device,b.memory,nullptr);} }
            if (pool) vkDestroyCommandPool(device,pool,nullptr);
            vkDestroyDevice(device,nullptr);
        }
        if(instance)vkDestroyInstance(instance,nullptr);
    }
    void init() {
        VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO}; app.pApplicationName="N010 DDGI bringup";app.apiVersion=VK_API_VERSION_1_2;
        VkInstanceCreateInfo info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};info.pApplicationInfo=&app;
        check(vkCreateInstance(&info,nullptr,&instance));
        uint32_t count=0;check(vkEnumeratePhysicalDevices(instance,&count,nullptr));std::vector<VkPhysicalDevice> devices(count);
        check(vkEnumeratePhysicalDevices(instance,&count,devices.data()));
        for(auto p:devices) { VkPhysicalDeviceProperties prop{};vkGetPhysicalDeviceProperties(p,&prop);if(prop.vendorID==0x1002 && prop.deviceType!=VK_PHYSICAL_DEVICE_TYPE_CPU){physical=p;properties=prop;break;} }
        if(!physical)throw std::runtime_error("AMD physical GPU unavailable; no software fallback");
        VkPhysicalDeviceSubgroupProperties sg{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SUBGROUP_PROPERTIES};
        VkPhysicalDeviceProperties2 prop2{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};prop2.pNext=&sg;vkGetPhysicalDeviceProperties2(physical,&prop2);
        subgroup=sg.subgroupSize;
        if((subgroup!=32 && subgroup!=64) || !(sg.supportedStages&VK_SHADER_STAGE_COMPUTE_BIT) || !(sg.supportedOperations&VK_SUBGROUP_FEATURE_ARITHMETIC_BIT))throw std::runtime_error("unsupported subgroup configuration");
        VkPhysicalDeviceFeatures features{};vkGetPhysicalDeviceFeatures(physical,&features);
        if(!features.shaderStorageImageReadWithoutFormat || !features.shaderStorageImageWriteWithoutFormat || !features.shaderStorageImageExtendedFormats)throw std::runtime_error("required storage image features unavailable");
        VkPhysicalDeviceFeatures enabled{};enabled.shaderStorageImageReadWithoutFormat=VK_TRUE;enabled.shaderStorageImageWriteWithoutFormat=VK_TRUE;enabled.shaderStorageImageExtendedFormats=VK_TRUE;
        uint32_t n=0;vkGetPhysicalDeviceQueueFamilyProperties(physical,&n,nullptr);std::vector<VkQueueFamilyProperties> families(n);vkGetPhysicalDeviceQueueFamilyProperties(physical,&n,families.data());
        bool found=false;for(uint32_t j=0;j<n;++j)if(families[j].queueFlags&VK_QUEUE_COMPUTE_BIT){family=j;found=true;break;}
        if(!found)throw std::runtime_error("compute queue unavailable");
        float priority=1;VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};qi.queueFamilyIndex=family;qi.queueCount=1;qi.pQueuePriorities=&priority;
        VkDeviceCreateInfo di{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};di.queueCreateInfoCount=1;di.pQueueCreateInfos=&qi;di.pEnabledFeatures=&enabled;
        check(vkCreateDevice(physical,&di,nullptr,&device));vkGetDeviceQueue(device,family,0,&queue);vkGetPhysicalDeviceMemoryProperties(physical,&memory);
        rtxgi::SetInsertPerfMarkers(false);D::LoadExtensions(device);
        VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=family;pi.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;check(vkCreateCommandPool(device,&pi,nullptr,&pool));
        VkCommandBufferAllocateInfo ci{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ci.commandPool=pool;ci.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ci.commandBufferCount=1;check(vkAllocateCommandBuffers(device,&ci,&command));
    }
    void allocate(const VkMemoryRequirements& req,VkMemoryPropertyFlags flags,VkDeviceMemory& output,uint32_t usage) {
        uint32_t type=UINT32_MAX;for(uint32_t j=0;j<memory.memoryTypeCount;++j)if((req.memoryTypeBits&(1u<<j))&&(memory.memoryTypes[j].propertyFlags&flags)==flags){type=j;break;}
        if(type==UINT32_MAX)throw std::runtime_error("required memory type unavailable");
        VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};ai.allocationSize=req.size;ai.memoryTypeIndex=type;check(vkAllocateMemory(device,&ai,nullptr,&output));
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
        if(!(fp.optimalTilingFeatures&VK_FORMAT_FEATURE_STORAGE_IMAGE_BIT))throw std::runtime_error("unsupported storage image format");
        VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};ii.imageType=VK_IMAGE_TYPE_2D;ii.extent={i.w,i.h,1};ii.mipLevels=1;ii.arrayLayers=i.layers;ii.format=vkformat;ii.tiling=VK_IMAGE_TILING_OPTIMAL;ii.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED;ii.samples=VK_SAMPLE_COUNT_1_BIT;ii.sharingMode=VK_SHARING_MODE_EXCLUSIVE;ii.usage=VK_IMAGE_USAGE_STORAGE_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
        check(vkCreateImage(device,&ii,nullptr,&i.handle));VkMemoryRequirements req{};vkGetImageMemoryRequirements(device,i.handle,&req);allocate(req,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,i.memory,ii.usage);check(vkBindImageMemory(device,i.handle,i.memory,0));
        VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};vi.image=i.handle;vi.viewType=VK_IMAGE_VIEW_TYPE_2D_ARRAY;vi.format=vkformat;vi.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,i.layers};check(vkCreateImageView(device,&vi,nullptr,&i.view));return i;
    }
    Kernel kernel(const fs::path& path,const char* entry) {
        kernels.emplace_back();auto& k=kernels.back();std::ifstream in(path,std::ios::binary|std::ios::ate);if(!in)throw std::runtime_error("missing SPIR-V: "+path.string());auto bytes=in.tellg();if(bytes<=0 || size_t(bytes)%4)throw std::runtime_error("invalid SPIR-V size");std::vector<uint32_t> words(size_t(bytes)/4);in.seekg(0);in.read(reinterpret_cast<char*>(words.data()),bytes);if(!in || words[0]!=0x07230203)throw std::runtime_error("bad SPIR-V");
        VkShaderModuleCreateInfo mi{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};mi.codeSize=size_t(bytes);mi.pCode=words.data();check(vkCreateShaderModule(device,&mi,nullptr,&k.module));
        VkComputePipelineCreateInfo pi{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};pi.layout=layout;pi.stage.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;pi.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;pi.stage.module=k.module;pi.stage.pName=entry;check(vkCreateComputePipelines(device,VK_NULL_HANDLE,1,&pi,nullptr,&k.pipeline));return k;
    }
    void barrier(Image i,VkImageLayout from,VkImageLayout to,VkAccessFlags src,VkAccessFlags dst,VkPipelineStageFlags a,VkPipelineStageFlags b) {
        VkImageMemoryBarrier bi{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};bi.oldLayout=from;bi.newLayout=to;bi.srcAccessMask=src;bi.dstAccessMask=dst;bi.srcQueueFamilyIndex=bi.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;bi.image=i.handle;bi.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,i.layers};vkCmdPipelineBarrier(command,a,b,0,0,nullptr,0,nullptr,1,&bi);
    }
};
static void run(const fs::path& shaders,const fs::path& reduction,const fs::path& out) {
    Context c;c.init();
    rtxgi::DDGIVolumeDesc desc{};char name[]="N010 constant diagnostic";desc.name=name;desc.rngSeed=305419896;desc.probeCounts={2,2,2};desc.probeSpacing={1,1,1};desc.probeNumRays=128;desc.probeNumIrradianceTexels=8;desc.probeNumIrradianceInteriorTexels=6;desc.probeNumDistanceTexels=16;desc.probeNumDistanceInteriorTexels=14;desc.probeIrradianceEncodingGamma=1;desc.probeHysteresis=0;desc.probeBrightnessThreshold=1e6;
    desc.probeRayDataFormat=desc.probeIrradianceFormat=desc.probeDataFormat=rtxgi::EDDGIVolumeTextureFormat::F32x4;desc.probeDistanceFormat=rtxgi::EDDGIVolumeTextureFormat::F32x2;desc.probeVariabilityFormat=rtxgi::EDDGIVolumeTextureFormat::F32;
    auto& constants=c.buffer(sizeof(rtxgi::DDGIVolumeDescGPUPacked),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto& variability_read=c.buffer(8,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    for(int j=0;j<6;++j) {auto type=rtxgi::EDDGIVolumeTextureType(j);auto format=j==2 || j==5?rtxgi::EDDGIVolumeTextureFormat::F32x2:(j==4?rtxgi::EDDGIVolumeTextureFormat::F32:rtxgi::EDDGIVolumeTextureFormat::F32x4);c.image(desc,type,format,j==2 || j==5?2:(j==4?1:4));}
    VkDescriptorSetLayoutCreateInfo sl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};VkPushConstantRange pc{};VkPipelineLayoutCreateInfo pl{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};std::array<VkDescriptorSetLayoutBinding,7> bindings{};D::GetDDGIVolumeLayoutDescs(sl,pc,pl,bindings.data());check(vkCreateDescriptorSetLayout(c.device,&sl,nullptr,&c.set_layout));pl.pSetLayouts=&c.set_layout;check(vkCreatePipelineLayout(c.device,&pl,nullptr,&c.layout));
    std::array<VkDescriptorPoolSize,2> sizes{{{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,1},{VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,6}}};VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};dp.maxSets=1;dp.poolSizeCount=2;dp.pPoolSizes=sizes.data();check(vkCreateDescriptorPool(c.device,&dp,nullptr,&c.descriptors));VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};da.descriptorPool=c.descriptors;da.descriptorSetCount=1;da.pSetLayouts=&c.set_layout;check(vkAllocateDescriptorSets(c.device,&da,&c.set));
    VkDescriptorBufferInfo cb{constants.handle,0,constants.bytes};std::array<VkDescriptorImageInfo,6> views{};std::array<VkWriteDescriptorSet,7> writes{};
    for(uint32_t j=0;j<7;++j) {auto& w=writes[j];w.sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;w.dstSet=c.set;w.dstBinding=j;w.descriptorCount=1;w.descriptorType=j==0?VK_DESCRIPTOR_TYPE_STORAGE_BUFFER:VK_DESCRIPTOR_TYPE_STORAGE_IMAGE;if(j==0)w.pBufferInfo=&cb;else{views[j-1].imageView=c.images[j-1].view;views[j-1].imageLayout=VK_IMAGE_LAYOUT_GENERAL;w.pImageInfo=&views[j-1];}}
    vkUpdateDescriptorSets(c.device,7,writes.data(),0,nullptr);
    std::array<Kernel,8> kernels{c.kernel(shaders/"blend-128-irradiance.spv","DDGIProbeBlendingCS"),c.kernel(shaders/"blend-128-distance.spv","DDGIProbeBlendingCS"),c.kernel(shaders/"relocation.spv","DDGIProbeRelocationCS"),c.kernel(shaders/"relocation-reset.spv","DDGIProbeRelocationResetCS"),c.kernel(shaders/"classification.spv","DDGIProbeClassificationCS"),c.kernel(shaders/"classification-reset.spv","DDGIProbeClassificationResetCS"),c.kernel(reduction/("reduction-wave"+std::to_string(c.subgroup)+".spv"),"DDGIReductionCS"),c.kernel(reduction/("extra-reduction-wave"+std::to_string(c.subgroup)+".spv"),"DDGIExtraReductionCS")};
    D::DDGIVolumeResources res{};res.unmanaged.enabled=true;res.constantsBuffer=constants.handle;auto& u=res.unmanaged;u.pipelineLayout=c.layout;u.descriptorSet=c.set;
    u.probeRayData=c.images[0].handle;u.probeIrradiance=c.images[1].handle;u.probeDistance=c.images[2].handle;u.probeData=c.images[3].handle;u.probeVariability=c.images[4].handle;u.probeVariabilityAverage=c.images[5].handle;
    u.probeRayDataMemory=c.images[0].memory;u.probeIrradianceMemory=c.images[1].memory;u.probeDistanceMemory=c.images[2].memory;u.probeDataMemory=c.images[3].memory;u.probeVariabilityMemory=c.images[4].memory;u.probeVariabilityAverageMemory=c.images[5].memory;
    u.probeRayDataView=c.images[0].view;u.probeIrradianceView=c.images[1].view;u.probeDistanceView=c.images[2].view;u.probeDataView=c.images[3].view;u.probeVariabilityView=c.images[4].view;u.probeVariabilityAverageView=c.images[5].view;u.probeVariabilityReadback=variability_read.handle;u.probeVariabilityReadbackMemory=variability_read.memory;
    u.probeBlendingIrradianceModule=kernels[0].module;u.probeBlendingIrradiancePipeline=kernels[0].pipeline;u.probeBlendingDistanceModule=kernels[1].module;u.probeBlendingDistancePipeline=kernels[1].pipeline;
    u.probeRelocation={kernels[2].module,kernels[3].module,kernels[2].pipeline,kernels[3].pipeline};u.probeClassification={kernels[4].module,kernels[5].module,kernels[4].pipeline,kernels[5].pipeline};u.probeVariabilityPipelines={kernels[6].module,kernels[7].module,kernels[6].pipeline,kernels[7].pipeline};
    D::DDGIVolume volume;sdk_check(volume.Create(desc,res));volume.Update();auto packed=volume.GetDescGPUPacked();std::memcpy(constants.mapped,&packed,sizeof packed);
    auto& irr_read=c.buffer(VkDeviceSize(c.images[1].w)*c.images[1].h*c.images[1].layers*16,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    auto& dist_read=c.buffer(VkDeviceSize(c.images[2].w)*c.images[2].h*c.images[2].layers*8,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    std::ofstream metadata(out/"measurements.json");metadata<<std::setprecision(17)<<"{\"device\":\""<<c.properties.deviceName<<"\",\"subgroup_width\":"<<c.subgroup<<",\"validation_layer_run\":false,\"image_layouts\":[";
    for(size_t j=0;j<c.images.size();++j){auto image=c.images[j];metadata<<(j?",":"")<<"{\"type\":"<<j<<",\"width\":"<<image.w<<",\"height\":"<<image.h<<",\"layers\":"<<image.layers<<",\"float32_channels\":"<<image.channels<<"}";}
    metadata<<"],\"rows\":[";
    bool all=true;
    for(int control=0;control<2;++control) {
        Ledger::instance().phase(control?"constant-positive":"constant-zero");check(vkResetCommandBuffer(c.command,0));VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};check(vkBeginCommandBuffer(c.command,&bi));
        for(auto image:c.images) {c.barrier(image,control?VK_IMAGE_LAYOUT_GENERAL:VK_IMAGE_LAYOUT_UNDEFINED,VK_IMAGE_LAYOUT_GENERAL,control?VK_ACCESS_TRANSFER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT:0,VK_ACCESS_TRANSFER_WRITE_BIT,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT);VkClearColorValue value{};if(image.handle==c.images[0].handle){value.float32[0]=value.float32[1]=value.float32[2]=float(control);value.float32[3]=1;}VkImageSubresourceRange range{VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,image.layers};vkCmdClearColorImage(c.command,image.handle,VK_IMAGE_LAYOUT_GENERAL,&value,1,&range);c.barrier(image,VK_IMAGE_LAYOUT_GENERAL,VK_IMAGE_LAYOUT_GENERAL,VK_ACCESS_TRANSFER_WRITE_BIT,VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT);}
        auto ptr=&volume;sdk_check(D::UpdateDDGIVolumeProbes(c.command,1,&ptr));
        for(int j=1;j<=2;++j) {auto image=c.images[j];c.barrier(image,VK_IMAGE_LAYOUT_GENERAL,VK_IMAGE_LAYOUT_GENERAL,VK_ACCESS_SHADER_WRITE_BIT,VK_ACCESS_TRANSFER_READ_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT);VkBufferImageCopy copy{};copy.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,image.layers};copy.imageExtent={image.w,image.h,1};vkCmdCopyImageToBuffer(c.command,image.handle,VK_IMAGE_LAYOUT_GENERAL,j==1?irr_read.handle:dist_read.handle,1,&copy);}
        VkMemoryBarrier host{VK_STRUCTURE_TYPE_MEMORY_BARRIER};host.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;host.dstAccessMask=VK_ACCESS_HOST_READ_BIT;vkCmdPipelineBarrier(c.command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&host,0,nullptr,0,nullptr);check(vkEndCommandBuffer(c.command));VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};submit.commandBufferCount=1;submit.pCommandBuffers=&c.command;check(vkQueueSubmit(c.queue,1,&submit,VK_NULL_HANDLE));check(vkQueueWaitIdle(c.queue));
        double ierr=0,derr=0;bool finite=true;
        for(int kind=1;kind<=2;++kind) {auto image=c.images[kind];auto& buf=kind==1?irr_read:dist_read;auto values=static_cast<float*>(buf.mapped);auto n=size_t(image.w)*image.h*image.layers;std::ofstream raw(out/("control"+std::to_string(control)+(kind==1?".irradiance.f32":".distance.f32")),std::ios::binary);raw.write(static_cast<const char*>(buf.mapped),std::streamsize(buf.bytes));if(!raw)throw std::runtime_error("readback file write failed");for(size_t j=0;j<n;++j)for(uint32_t channel=0;channel<image.channels;++channel) {double value=values[j*image.channels+channel];finite=finite&&std::isfinite(value);if((kind==1 && channel<3)||kind==2){auto error=std::abs(value-(kind==1?0.5*control:0.5));if(kind==1)ierr=std::max(ierr,error);else derr=std::max(derr,error);}}}
        bool pass=finite && ierr<=1e-5 && derr<=1e-5;all=all&&pass;metadata<<(control?",":"")<<"{\"radiance\":"<<control<<",\"irradiance_max_abs_error\":"<<ierr<<",\"distance_max_abs_error\":"<<derr<<",\"all_finite\":"<<(finite?"true":"false")<<",\"pass\":"<<(pass?"true":"false")<<"}";
    }
    metadata<<"],\"all_pass\":"<<(all?"true":"false")<<"}\n";metadata.close();volume.Destroy();
    if(!all)throw std::runtime_error("constant-field diagnostic failed; retain output without retry");
}
int main(int argc,char** argv) {
    if(argc!=4){std::cerr<<"usage: ddgi-volume-bringup SHADERS REDUCTION_SHADERS NEW_OUTPUT\n";return 1;}
    fs::path out=argv[3];if(fs::exists(out)){std::cerr<<"refuse existing output\n";return 1;}fs::create_directories(out);
    try {Ledger::instance().phase("startup");run(argv[1],argv[2],out);Ledger::instance().save(out/"allocation-ledger.json");std::cout<<"constant-field SDK diagnostic PASS\n";return 0;}
    catch(const std::exception& e) {Ledger::instance().save(out/"allocation-ledger.json");std::ofstream(out/"failure.txt")<<e.what()<<'\n';std::cerr<<e.what()<<'\n';return 2;}
}

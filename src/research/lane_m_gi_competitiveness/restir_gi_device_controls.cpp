// 034 isolated analytic GPU control host. Uses exact033 SPIR-V; no Renderer build.
#include <vulkan/vulkan.h>
#include <Rtxdi/GI/ReSTIRGI.h>
#include "allocation_ledger.hpp"
#include <array>
#include <chrono>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <vector>
namespace fs=std::filesystem;
using u32=std::uint32_t;using u64=std::uint64_t;using Bytes=std::vector<std::uint8_t>;
using Ledger=phos::gi::research::n010::AllocationLedger;using Clock=std::chrono::steady_clock;
static constexpr u64 guard=256,cap=256ull*1024*1024;
static constexpr std::array<const char*,6> names{"make","spatial-basic","spatial-ray","temporal-basic","temporal-ray","fused-ray"};
static void need(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
static void vkcheck(VkResult r){need(r==VK_SUCCESS,"034 Vulkan operation failed");}
static Bytes read(const fs::path& p,u64 expected=0){need(fs::is_regular_file(p),"034 input file missing");auto n=fs::file_size(p);need(n>0&&(!expected||n==expected),"034 input file size");Bytes b(n);std::ifstream f(p,std::ios::binary);f.read(reinterpret_cast<char*>(b.data()),n);need(bool(f),"034 input read");return b;}
static void write(const fs::path& p,const void* data,u64 n){need(!fs::exists(p),"034 output overwrite");std::ofstream f(p,std::ios::binary);f.write(static_cast<const char*>(data),n);need(bool(f),"034 output write");}
static u32 word(const Bytes& b,u64 offset){u32 n;std::memcpy(&n,b.data()+offset,4);return n;}
static void setword(void* p,u64 offset,u32 n){std::memcpy(static_cast<std::uint8_t*>(p)+offset,&n,4);}
struct Inputs {
 u32 w{},h{},pixels{},pitch{};std::array<u64,10> sizes{};std::array<std::array<Bytes,10>,8> fixtures;std::array<Bytes,6> shaders;
 Inputs(const fs::path& source,const fs::path& shader){auto meta=read(source/"meta.u32",8);w=word(meta,0);h=word(meta,4);need((w==17&&h==9)||(w==320&&h==180),"034 unregistered viewport");pixels=w*h;
  auto p=rtxdi::CalculateReservoirBufferParameters(w,h,rtxdi::CheckerboardMode::Off);pitch=p.reservoirArrayPitch;
  sizes={u64(pitch)*64,u64(pixels)*48,u64(pixels)*48,u64(pixels)*48,8192*2,u64(pixels*2+64)*16,32,32,48,80};
  for(u32 c=0;c<8;++c)for(u32 j=0;j<10;++j){auto& b=fixtures[c][j];b=read(source/("fixture-"+std::to_string(c))/("binding-"+std::to_string(j)+".bin"),sizes[j]);}
  for(u32 i=0;i<6;++i){shaders[i]=read(shader/(std::string(names[i])+".spv"));need(shaders[i].size()%4==0&&word(shaders[i],0)==0x07230203,"034 exact SPIR-V malformed");}
  for(u32 c=0;c<8;++c){auto& b=fixtures[c];need(word(b[9],0)==w&&word(b[9],4)==h&&word(b[9],16)==8191&&word(b[9],20)==0&&word(b[9],32)==p.reservoirBlockRowPitch&&word(b[9],36)==pitch,"034 Controls layout/values");
   for(u32 i=0;i<pixels;++i){need(word(b[1],i*48+32)==1&&word(b[1],i*48+28)==0xffffffffu,"034 current surface contract");for(u32 a=0;a<3;++a){float f;std::memcpy(&f,b[3].data()+i*48+32+a*4,4);need(std::isfinite(f)&&f>=0,"034 physical fixture radiance");}}
   need(word(b[6],8)==2&&word(b[7],8)==8&&word(b[8],12)==2,"034 SDK parameters");
  }
 }
};
struct Buffer {VkBuffer buffer{};VkDeviceMemory memory{};VkBufferView view{};void* mapped{};u64 size{},reserved{};};
struct Runtime {
 fs::path out;Inputs& input;Clock::time_point started=Clock::now();std::ofstream journal;bool pending=false;
 VkInstance instance{};VkPhysicalDevice physical{};VkDevice device{};VkQueue queue{};u32 family{},bits{},units{},dispatches{},copies{};
 VkPhysicalDeviceProperties properties{};VkPhysicalDeviceMemoryProperties memoryProperties{};
 VkCommandPool pool{};VkCommandBuffer command{};VkFence fence{};VkQueryPool query{};
 VkDescriptorSetLayout setLayout{};VkPipelineLayout pipelineLayout{};VkDescriptorPool descriptorPool{};VkDescriptorSet set{};
 std::array<VkShaderModule,6> modules{};std::array<VkPipeline,6> pipelines{};std::array<Buffer,10> buffers{};u64 owned=0;Bytes expectedControls;
 Runtime(Inputs& in,fs::path dir):out(std::move(dir)),input(in){journal.open(out/"units.jsonl");need(bool(journal),"034 journal");}
 [[noreturn]] void incomplete(const char* why){Ledger::instance().save(out/"allocation-ledger.json");std::ofstream(out/"failure.json")<<"{\"complete\":false,\"reason\":"<<std::quoted(why)<<",\"gpu_completion_proven\":false,\"teardown_claim\":false}\n";std::_Exit(3);}
 ~Runtime(){if(pending)incomplete("pending GPU submission during exception");if(device){
  for(u32 i=0;i<6;++i){if(pipelines[i])vkDestroyPipeline(device,pipelines[i],nullptr);if(modules[i])vkDestroyShaderModule(device,modules[i],nullptr);}
  if(descriptorPool)vkDestroyDescriptorPool(device,descriptorPool,nullptr);if(pipelineLayout)vkDestroyPipelineLayout(device,pipelineLayout,nullptr);if(setLayout)vkDestroyDescriptorSetLayout(device,setLayout,nullptr);
  for(auto& b:buffers){if(b.view)vkDestroyBufferView(device,b.view,nullptr);if(b.mapped)vkUnmapMemory(device,b.memory);if(b.buffer)vkDestroyBuffer(device,b.buffer,nullptr);if(b.memory){Ledger::instance().release(device,b.memory);vkFreeMemory(device,b.memory,nullptr);}}
  if(query)vkDestroyQueryPool(device,query,nullptr);if(fence)vkDestroyFence(device,fence,nullptr);if(pool)vkDestroyCommandPool(device,pool,nullptr);vkDestroyDevice(device,nullptr);}
  if(instance)vkDestroyInstance(instance,nullptr);
 }
 void init(){VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};app.pApplicationName="M001 ReSTIR034 analytic controls";app.apiVersion=VK_API_VERSION_1_2;
  VkInstanceCreateInfo ic{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};ic.pApplicationInfo=&app;vkcheck(vkCreateInstance(&ic,nullptr,&instance));u32 count=0;vkcheck(vkEnumeratePhysicalDevices(instance,&count,nullptr));std::vector<VkPhysicalDevice> devices(count);vkcheck(vkEnumeratePhysicalDevices(instance,&count,devices.data()));
  for(auto p:devices){VkPhysicalDeviceProperties d{};vkGetPhysicalDeviceProperties(p,&d);if(std::string(d.deviceName)=="AMD Radeon 8060S Graphics (RADV STRIX_HALO)"){need(!physical,"034 ambiguous target device");physical=p;}}
  need(physical,"034 exact target device unavailable");VkPhysicalDeviceDriverProperties driver{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES};VkPhysicalDeviceIDProperties id{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES};id.pNext=&driver;VkPhysicalDeviceProperties2 p2{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};p2.pNext=&id;vkGetPhysicalDeviceProperties2(physical,&p2);properties=p2.properties;
  need(properties.apiVersion>=VK_API_VERSION_1_2&&properties.limits.maxPerStageDescriptorStorageBuffers>=8&&properties.limits.maxComputeWorkGroupInvocations>=64,"034 device limits");
  need(guard%properties.limits.minStorageBufferOffsetAlignment==0&&guard%properties.limits.minUniformBufferOffsetAlignment==0&&guard%properties.limits.minTexelBufferOffsetAlignment==0,"034 descriptor guard alignment");
  VkPhysicalDeviceFeatures supported{};vkGetPhysicalDeviceFeatures(physical,&supported);need(supported.robustBufferAccess&&supported.shaderStorageImageExtendedFormats,"034 required supported features");
  VkFormatProperties format{};vkGetPhysicalDeviceFormatProperties(physical,VK_FORMAT_R8G8_SNORM,&format);need(format.bufferFeatures&VK_FORMAT_FEATURE_UNIFORM_TEXEL_BUFFER_BIT,"034 SNORM neighbor view");
  vkGetPhysicalDeviceMemoryProperties(physical,&memoryProperties);count=0;vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,nullptr);std::vector<VkQueueFamilyProperties> qs(count);vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,qs.data());family=UINT32_MAX;
  for(u32 k=0;k<count;++k)if((qs[k].queueFlags&VK_QUEUE_COMPUTE_BIT)&&qs[k].timestampValidBits){family=k;bits=qs[k].timestampValidBits;break;}
  need(family!=UINT32_MAX&&bits<=64,"034 compute queue");float priority=1;VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};qi.queueFamilyIndex=family;qi.queueCount=1;qi.pQueuePriorities=&priority;
  VkPhysicalDeviceFeatures features{};features.robustBufferAccess=VK_TRUE;features.shaderStorageImageExtendedFormats=VK_TRUE;VkDeviceCreateInfo dc{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};dc.queueCreateInfoCount=1;dc.pQueueCreateInfos=&qi;dc.pEnabledFeatures=&features;vkcheck(vkCreateDevice(physical,&dc,nullptr,&device));vkGetDeviceQueue(device,family,0,&queue);
  VkCommandPoolCreateInfo pc{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pc.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;pc.queueFamilyIndex=family;vkcheck(vkCreateCommandPool(device,&pc,nullptr,&pool));VkCommandBufferAllocateInfo ca{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ca.commandPool=pool;ca.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ca.commandBufferCount=1;vkcheck(vkAllocateCommandBuffers(device,&ca,&command));
  VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};vkcheck(vkCreateFence(device,&fi,nullptr,&fence));VkQueryPoolCreateInfo qc{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};qc.queryType=VK_QUERY_TYPE_TIMESTAMP;qc.queryCount=2;vkcheck(vkCreateQueryPool(device,&qc,nullptr,&query));
  std::array<VkDescriptorSetLayoutBinding,10> bindings{};for(u32 j=0;j<10;++j)bindings[j]={j,type(j),1,VK_SHADER_STAGE_COMPUTE_BIT,nullptr};VkDescriptorSetLayoutCreateInfo sl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};sl.bindingCount=10;sl.pBindings=bindings.data();vkcheck(vkCreateDescriptorSetLayout(device,&sl,nullptr,&setLayout));VkPipelineLayoutCreateInfo pl{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};pl.setLayoutCount=1;pl.pSetLayouts=&setLayout;vkcheck(vkCreatePipelineLayout(device,&pl,nullptr,&pipelineLayout));
  std::array<VkDescriptorPoolSize,3> sizes{{{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,8},{VK_DESCRIPTOR_TYPE_UNIFORM_TEXEL_BUFFER,1},{VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,1}}};VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};dp.maxSets=1;dp.poolSizeCount=3;dp.pPoolSizes=sizes.data();vkcheck(vkCreateDescriptorPool(device,&dp,nullptr,&descriptorPool));VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};da.descriptorPool=descriptorPool;da.descriptorSetCount=1;da.pSetLayouts=&setLayout;vkcheck(vkAllocateDescriptorSets(device,&da,&set));
  for(u32 k=0;k<6;++k){VkShaderModuleCreateInfo sm{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};sm.codeSize=input.shaders[k].size();sm.pCode=reinterpret_cast<const u32*>(input.shaders[k].data());vkcheck(vkCreateShaderModule(device,&sm,nullptr,&modules[k]));VkComputePipelineCreateInfo cp{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};cp.layout=pipelineLayout;cp.stage.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;cp.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;cp.stage.module=modules[k];cp.stage.pName="main";vkcheck(vkCreateComputePipelines(device,VK_NULL_HANDLE,1,&cp,nullptr,&pipelines[k]));}
  for(u32 j=0;j<10;++j)allocate(j);
  std::ofstream f(out/"device.json");f<<"{\"name\":"<<std::quoted(properties.deviceName)<<",\"driver\":"<<std::quoted(driver.driverName)<<",\"driver_info\":"<<std::quoted(driver.driverInfo)<<",\"vendor_id\":"<<properties.vendorID<<",\"device_id\":"<<properties.deviceID<<",\"api_version\":"<<properties.apiVersion<<",\"queue_family\":"<<family<<",\"timestamp_bits\":"<<bits<<",\"timestamp_period_ns\":"<<properties.limits.timestampPeriod<<",\"robust_buffer_access\":true,\"validation_layers\":false,\"device_uuid\":\"";
  for(auto b:id.deviceUUID)f<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(b);f<<"\",\"accepted_timing\":false}\n";need(bool(f),"034 device receipt");
 }
 static VkDescriptorType type(u32 j){return j==4?VK_DESCRIPTOR_TYPE_UNIFORM_TEXEL_BUFFER:j==9?VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER:VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;}
 std::uint8_t* data(u32 j){return static_cast<std::uint8_t*>(buffers[j].mapped)+guard;}
 void allocate(u32 j){auto& b=buffers[j];b.size=input.sizes[j];VkBufferCreateInfo bc{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};bc.size=b.size+2*guard;bc.sharingMode=VK_SHARING_MODE_EXCLUSIVE;bc.usage=VK_BUFFER_USAGE_TRANSFER_SRC_BIT|VK_BUFFER_USAGE_TRANSFER_DST_BIT|(j==4?VK_BUFFER_USAGE_UNIFORM_TEXEL_BUFFER_BIT:j==9?VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT:VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);vkcheck(vkCreateBuffer(device,&bc,nullptr,&b.buffer));VkMemoryRequirements mr{};vkGetBufferMemoryRequirements(device,b.buffer,&mr);u32 t=UINT32_MAX;const auto flags=VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
  for(u32 i=0;i<memoryProperties.memoryTypeCount;++i)if((mr.memoryTypeBits&(1u<<i))&&(memoryProperties.memoryTypes[i].propertyFlags&flags)==flags){t=i;break;}need(t!=UINT32_MAX&&owned+mr.size<=cap,"034 owned memory/type cap");owned+=mr.size;b.reserved=mr.size;VkMemoryAllocateInfo ma{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};ma.allocationSize=mr.size;ma.memoryTypeIndex=t;vkcheck(vkAllocateMemory(device,&ma,nullptr,&b.memory));Ledger::instance().allocate(device,b.memory,mr.size,t,flags,bc.usage);vkcheck(vkBindBufferMemory(device,b.buffer,b.memory,0));vkcheck(vkMapMemory(device,b.memory,0,VK_WHOLE_SIZE,0,&b.mapped));
  VkDescriptorBufferInfo bi{b.buffer,guard,b.size};VkWriteDescriptorSet d{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};d.dstSet=set;d.dstBinding=j;d.descriptorCount=1;d.descriptorType=type(j);d.pBufferInfo=&bi;
  if(j==4){VkBufferViewCreateInfo vi{VK_STRUCTURE_TYPE_BUFFER_VIEW_CREATE_INFO};vi.buffer=b.buffer;vi.offset=guard;vi.range=b.size;vi.format=VK_FORMAT_R8G8_SNORM;vkcheck(vkCreateBufferView(device,&vi,nullptr,&b.view));d.pBufferInfo=nullptr;d.pTexelBufferView=&b.view;}vkUpdateDescriptorSets(device,1,&d,0,nullptr);
 }
 void restore(u32 fixture){for(u32 j=0;j<10;++j){auto& b=buffers[j];std::memset(b.mapped,0x5a,b.size+2*guard);std::memcpy(data(j),input.fixtures[fixture][j].data(),b.size);}}
 void controls(u32 frame,u32 output){setword(data(9),8,frame);setword(data(9),12,0);setword(data(9),24,frame);setword(data(9),76,output);expectedControls.assign(data(9),data(9)+80);}
 void check(u32 fixture){for(u32 j=0;j<10;++j){auto& b=buffers[j];auto* bytes=static_cast<std::uint8_t*>(b.mapped);for(u64 k=0;k<guard;++k)need(bytes[k]==0x5a&&bytes[guard+b.size+k]==0x5a,"034 buffer canary changed");if(j!=0&&j!=5&&j!=9)need(std::memcmp(data(j),input.fixtures[fixture][j].data(),b.size)==0,"034 immutable input changed");}need(std::memcmp(data(9),expectedControls.data(),80)==0,"034 uniform input changed");for(u64 i=u64(input.pixels)*32;i<buffers[5].size;++i)need(data(5)[i]==0,"034 unwritten output padding changed");}
 void begin(const std::string& label){need(std::chrono::duration<double>(Clock::now()-started).count()<180,"034 native wall guard");Ledger::instance().phase(label);journal<<"{\"event\":\"begin\",\"unit\":"<<units<<",\"label\":"<<std::quoted(label)<<"}\n";journal.flush();vkcheck(vkResetFences(device,1,&fence));vkcheck(vkResetCommandBuffer(command,0));VkCommandBufferBeginInfo b{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};b.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;vkcheck(vkBeginCommandBuffer(command,&b));VkMemoryBarrier before{VK_STRUCTURE_TYPE_MEMORY_BARRIER};before.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT|VK_ACCESS_SHADER_WRITE_BIT|VK_ACCESS_TRANSFER_WRITE_BIT;before.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT|VK_ACCESS_UNIFORM_READ_BIT|VK_ACCESS_TRANSFER_READ_BIT|VK_ACCESS_TRANSFER_WRITE_BIT;vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT|VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT|VK_PIPELINE_STAGE_TRANSFER_BIT,0,1,&before,0,nullptr,0,nullptr);vkCmdResetQueryPool(command,query,0,2);vkCmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);}
 void end(){VkMemoryBarrier after{VK_STRUCTURE_TYPE_MEMORY_BARRIER};after.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT|VK_ACCESS_TRANSFER_WRITE_BIT;after.dstAccessMask=VK_ACCESS_HOST_READ_BIT|VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_TRANSFER_READ_BIT;vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT|VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT|VK_PIPELINE_STAGE_TRANSFER_BIT,0,1,&after,0,nullptr,0,nullptr);vkCmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,1);vkcheck(vkEndCommandBuffer(command));VkSubmitInfo s{VK_STRUCTURE_TYPE_SUBMIT_INFO};s.commandBufferCount=1;s.pCommandBuffers=&command;vkcheck(vkQueueSubmit(queue,1,&s,fence));pending=true;auto waited=vkWaitForFences(device,1,&fence,VK_TRUE,250000000ull);if(waited!=VK_SUCCESS)incomplete("034 bounded fence incomplete");pending=false;u64 tick[2]{};vkcheck(vkGetQueryPoolResults(device,query,0,2,sizeof(tick),tick,8,VK_QUERY_RESULT_64_BIT));auto mask=bits==64?UINT64_MAX:((u64(1)<<bits)-1);double us=double((tick[1]-tick[0])&mask)*properties.limits.timestampPeriod/1000.;need(std::isfinite(us)&&us<=250000,"034 GPU unit duration");journal<<std::setprecision(17)<<"{\"event\":\"complete\",\"unit\":"<<units++<<",\"begin\":"<<tick[0]<<",\"end\":"<<tick[1]<<",\"gpu_us_diagnostic\":"<<us<<"}\n";journal.flush();std::this_thread::sleep_for(std::chrono::milliseconds(2));}
 void dispatch(u32 variant,const std::string& label){bool preserve=word(expectedControls,76)==1;Bytes source;if(preserve)source.assign(data(0),data(0)+u64(input.pitch)*32);begin(label);vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipelines[variant]);vkCmdBindDescriptorSets(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipelineLayout,0,1,&set,0,nullptr);vkCmdDispatch(command,(input.w+7)/8,(input.h+7)/8,1);end();if(preserve)need(std::memcmp(source.data(),data(0),source.size())==0,"034 source reservoir array changed");++dispatches;}
 void history(const std::string& label){begin(label);VkBufferCopy c{guard+u64(input.pitch)*32,guard,u64(input.pitch)*32};vkCmdCopyBuffer(command,buffers[0].buffer,buffers[0].buffer,1,&c);end();++copies;need(std::memcmp(data(0),data(0)+u64(input.pitch)*32,u64(input.pitch)*32)==0,"034 device history copy mismatch");}
 Bytes snapshot(const fs::path& path,u32 binding){auto& b=buffers[binding];Bytes bytes(b.size+2*guard);std::memcpy(bytes.data(),b.mapped,bytes.size());write(path,bytes.data(),bytes.size());return bytes;}
 void run(){for(u32 fixture=0;fixture<8;++fixture)for(u32 variant=0;variant<6;++variant){auto stem="f"+std::to_string(fixture)+"-p"+std::to_string(variant);auto dir=out/stem;need(fs::create_directory(dir),"034 fixture output exists");restore(fixture);controls(0,0);dispatch(0,stem+"-seed");check(fixture);snapshot(dir/"seed-reservoirs.bin",0);snapshot(dir/"seed-results.bin",5);
   std::memset(data(5),0,buffers[5].size);controls(0,1);dispatch(variant,stem+"-cold");check(fixture);auto cold0=snapshot(dir/"cold-reservoirs.bin",0);auto cold5=snapshot(dir/"cold-results.bin",5);
   history(stem+"-history-copy");std::memset(data(5),0,buffers[5].size);controls(1,1);dispatch(variant,stem+"-warm");check(fixture);snapshot(dir/"warm-reservoirs.bin",0);snapshot(dir/"warm-results.bin",5);
   restore(fixture);controls(0,0);dispatch(0,stem+"-reset-seed");check(fixture);std::memset(data(5),0,buffers[5].size);controls(0,1);dispatch(variant,stem+"-reset");check(fixture);auto reset0=snapshot(dir/"reset-reservoirs.bin",0);auto reset5=snapshot(dir/"reset-results.bin",5);need(cold0==reset0&&cold5==reset5,"034 cold/reset not byte-exact");
   std::ofstream f(dir/"complete.json");f<<"{\"complete\":true,\"fixture\":"<<fixture<<",\"variant\":"<<variant<<",\"dispatches\":5,\"copies\":1,\"cold_reset_exact\":true,\"canaries_and_readonly_pass\":true}\n";need(bool(f),"034 fixture receipt");std::cout<<stem<<" PASS\n"<<std::flush;
  }need(dispatches==240&&copies==48&&units==288,"034 fixed complete unit boundary");}
};
int main(int argc,char** argv){fs::path out;bool created=false;
 try{need(argc==8,"034 usage --cpu-check|--gpu --input DIR --out NEW --shaders DIR");std::string mode=argv[1];need(mode=="--cpu-check"||mode=="--gpu","034 unknown mode");need(std::string(argv[2])=="--input"&&std::string(argv[4])=="--out"&&std::string(argv[6])=="--shaders","034 exact options/order");Inputs input(argv[3],argv[7]);out=argv[5];need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"034 exclusive output/parent");need(fs::create_directory(out),"034 output creation");created=true;
  if(mode=="--cpu-check"){std::ofstream f(out/"complete.json");f<<"{\"complete\":true,\"gpu_initialized\":false,\"width\":"<<input.w<<",\"height\":"<<input.h<<",\"reservoir_array_pitch\":"<<input.pitch<<",\"fixtures\":8,\"variants\":6,\"controls_bytes\":80}\n";need(bool(f),"034 CPU receipt");return 0;}
  u32 dispatches,copies,units;{Ledger::instance().phase("034-startup");Runtime run(input,out);run.init();run.run();dispatches=run.dispatches;copies=run.copies;units=run.units;Ledger::instance().phase("034-teardown");}
  Ledger::instance().save(out/"allocation-ledger.json");std::ofstream f(out/"complete.json");f<<"{\"schema\":\"m001-restir034-native-analytic-controls/1\",\"complete\":true,\"gpu_initialized\":true,\"width\":"<<input.w<<",\"height\":"<<input.h<<",\"dispatches\":"<<dispatches<<",\"copies\":"<<copies<<",\"units\":"<<units<<",\"configurations\":48,\"quality_admitted\":false,\"accepted_timing\":false}\n";need(bool(f),"034 terminal native receipt");return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(created){std::ofstream f(out/"native-error.json");f<<"{\"complete\":false,\"error\":"<<std::quoted(e.what())<<"}\n";}return 2;}
}

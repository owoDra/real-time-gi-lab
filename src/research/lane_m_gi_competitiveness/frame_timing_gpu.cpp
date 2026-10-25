//044 calibrated AB/BA GPU timing of complete M001 frame roles and a neutral calibration workload.
// Reuses exact 022/041/042 SPIR-V; one Vulkan context per process; GPU timestamps are primary.
#include "integrated_state.hpp"
#include "i001_compute.hpp"
#include <charconv>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <thread>
using namespace m022;
namespace i=phos::gi::research::integration;
using u32=std::uint32_t;
constexpr u32 W=320,H=180,N=W*H,BLOCK_ROW=((W+15)/16)*256,PITCH=BLOCK_ROW*((H+15)/16),WARMUP=4,MEASURED=12;
static void check(VkResult value){need(value==VK_SUCCESS,"044 Vulkan operation");}
static u32 integer(const std::string& s){u32 v=0;auto r=std::from_chars(s.data(),s.data()+s.size(),v);need(r.ec==std::errc{}&&r.ptr==s.data()+s.size(),"044 unsigned option");return v;}
static u32 jenkins(u32 a){
    a=(a+0x7ed55d16u)+(a<<12);a=(a^0xc761c23cu)^(a>>19);a=(a+0x165667b1u)+(a<<5);
    a=(a+0xd3a2646cu)^(a<<9);a=(a+0xfd7046c5u)+(a<<3);return (a^0xb55a4f09u)^(a>>16);
}
struct Controls {
    float camera[3];float epsilon;float forward[3];u32 width;
    u32 height,pixels,unit,pad0;
    u32 runtime[4];u32 reservoir[4];
    float t_depth,t_normal;u32 t_history,t_fallback,t_bias,t_age,t_permutation,t_uniform;
    float s_depth,s_normal;u32 s_samples;float s_radius;u32 s_bias,s_pad[3];
};
static_assert(sizeof(Controls)==144);
enum Buffer:u32 {HITS,CAMERA,GEOMETRY,COEFF,MAPS,SOURCES,STAGES,UNCLIPPED,RAWPT,FINAL,PARAMS,ACC,
                 WITNESSES,CANDIDATES,LOCAL,RESERVOIRS,OWNERS,SURFACES,OFFSETS,SHADING,FRAME,CONTROLS,DIAGNOSTICS,COUNTERS,NEUTRAL,COUNT};
static const char* NAMES[COUNT]={"hits","camera","geometry","coefficients","maps","sources","stages","unclipped","raw-pt","final","params","accumulated",
    "witnesses","candidates","local-endpoints","reservoirs","owners","surfaces","neighbor-offsets","shading","frame","controls","diagnostics","counters","neutral"};
struct Role {std::string name;std::vector<Buffer> buffers;};
struct Runtime {
    b::B002VulkanContext& c;fs::path out;std::ofstream log;u32 vertices{};
    std::array<b::B002Buffer,COUNT> buffers{};std::array<std::uint64_t,COUNT> sizes{};
    std::unique_ptr<i::I001ComputeStage> producer,quadratic,compose,physical,accumulate,copy,neutral;std::array<std::unique_ptr<i::I001ComputeStage>,5> reuse;
    VkCommandPool pool{};VkCommandBuffer command{};VkFence fence{};VkQueryPool query{};
    VkPhysicalDeviceProperties properties{};VkPhysicalDeviceDriverProperties driver{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES};
    u32 bits{},submits{},samples{},frame_index{};
    Runtime(b::B002VulkanContext& context,const fs::path& output):c(context),out(output),log(out/"samples.jsonl"){
        need(bool(log),"044 journal");log<<std::setprecision(17);
        VkPhysicalDeviceProperties2 p{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};p.pNext=&driver;
        vkGetPhysicalDeviceProperties2(c.physical_device(),&p);properties=p.properties;
        u32 count=0;vkGetPhysicalDeviceQueueFamilyProperties(c.physical_device(),&count,nullptr);
        std::vector<VkQueueFamilyProperties> families(count);vkGetPhysicalDeviceQueueFamilyProperties(c.physical_device(),&count,families.data());
        need(c.queue_family()<count,"044 queue family");bits=families[c.queue_family()].timestampValidBits;
        need(bits>0&&bits<=64&&properties.limits.maxPerStageDescriptorStorageBuffers>=12,"044 device limits");
        VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=c.queue_family();pi.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        check(c.vk().createCommandPool(&pi,nullptr,&pool));
        VkCommandBufferAllocateInfo ai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ai.commandPool=pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;
        check(c.vk().allocateCommandBuffers(&ai,&command));
        VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};check(c.vk().createFence(&fi,nullptr,&fence));
        VkQueryPoolCreateInfo qi{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};qi.queryType=VK_QUERY_TYPE_TIMESTAMP;qi.queryCount=2;
        check(c.vk().createQueryPool(&qi,nullptr,&query));
    }
    ~Runtime(){producer.reset();quadratic.reset();compose.reset();physical.reset();accumulate.reset();copy.reset();neutral.reset();for(auto& s:reuse)s.reset();
        for(auto& buf:buffers)c.destroy_buffer(buf);if(query)c.vk().destroyQueryPool(query,nullptr);if(fence)c.vk().destroyFence(fence,nullptr);if(pool)c.vk().destroyCommandPool(pool,nullptr);}
    template<class T=unsigned char> T* map(Buffer j){return static_cast<T*>(buffers[j].mapped);}
    void allocate(const State* state,b::B002HwrtTraversal* hwrt,const fs::path& shaders,const fs::path& offsets,u32 depth){
        vertices=depth;
        sizes={32ull*N,80,32ull*N,300ull*N,24ull*N,4ull*N,12ull*N,12ull*N,16ull*N,16ull*N,128,16ull*N,
               80ull*N*std::max(depth,1u),128ull*N,16ull*N,32ull*PITCH*6,16ull*PITCH*6,96ull*N,8ull*8192,64ull*N,16ull*N,sizeof(Controls),24ull*N,32,4ull*N};
        for(u32 j=0;j<COUNT;j++){
            need(sizes[j]<=properties.limits.maxStorageBufferRange,"044 descriptor range");
            buffers[j]=c.create_host_buffer(sizes[j],j==PARAMS?VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT:VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            need(buffers[j].mapped,"044 coherent mapping");std::memset(buffers[j].mapped,0,std::size_t(sizes[j]));
        }
        auto stage=[&](std::unique_ptr<i::I001ComputeStage>& s,const char* name,std::vector<i::I001Binding> bind,std::size_t push){s=std::make_unique<i::I001ComputeStage>(c,(shaders/name).string(),bind,push);};
        stage(neutral,"timing_neutral.spv",{{0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[NEUTRAL]}},16);
        if(!state)return;
        std::memcpy(map(CAMERA),state->camera.data(),80);std::memcpy(map(PARAMS),&state->params,sizeof(state->params));
        need(fs::file_size(offsets)==16384,"044 neighbor offsets");std::ifstream o(offsets,std::ios::binary);std::array<signed char,16384> raw{};
        o.read(reinterpret_cast<char*>(raw.data()),16384);need(bool(o),"044 offset read");
        auto* offset=map<float>(OFFSETS);for(u32 j=0;j<16384;j++)offset[j]=std::max(float(raw[j])/127.0f,-1.0f);
        Controls k{};const auto& p=state->params;
        for(int a=0;a<3;a++){k.camera[a]=p.camera_pos_near[a];k.forward[a]=p.camera_forward_far[a];}
        k.epsilon=state->camera[16];k.width=W;k.height=H;k.pixels=N;k.unit=64;k.runtime[0]=8191;k.reservoir[0]=BLOCK_ROW;k.reservoir[1]=PITCH;
        k.t_depth=.1f;k.t_normal=.6f;k.t_history=8;k.t_fallback=1;k.t_bias=3;k.t_age=30;k.s_depth=.1f;k.s_normal=.6f;k.s_samples=2;k.s_radius=32.f;k.s_bias=3;
        std::memcpy(map(CONTROLS),&k,sizeof k);
        const VkDescriptorType S=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,A=VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR;
        stage(producer,"integrated_producer.spv",{{0,S,&buffers[RAWPT]},{1,A,nullptr,hwrt->top_level()},{2,S,&hwrt->triangle_buffer()},{3,VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,&buffers[PARAMS]},{4,S,&buffers[HITS]},{5,S,&buffers[SOURCES]}},16);
        std::vector<i::I001Binding> qb;for(u32 j=0;j<8;j++)qb.push_back({j,S,&buffers[j]});stage(quadratic,"surface_quadratic_device.spv",qb,16);
        stage(compose,"integrated_composite.spv",{{0,S,&buffers[RAWPT]},{1,S,&buffers[STAGES]},{2,S,&buffers[FINAL]}},0);
        stage(physical,"physical_producer.spv",{{0,S,&buffers[RAWPT]},{1,A,nullptr,hwrt->top_level()},{2,S,&hwrt->triangle_buffer()},{3,VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,&buffers[PARAMS]},{4,S,&buffers[HITS]},{5,S,&buffers[SOURCES]},
            {6,S,&buffers[WITNESSES]},{7,S,&buffers[CANDIDATES]},{8,S,&buffers[LOCAL]}},16);
        std::vector<i::I001Binding> rb{{0,S,&buffers[RESERVOIRS]},{1,S,&buffers[OWNERS]},{2,S,&buffers[CANDIDATES]},{3,S,&buffers[LOCAL]},{4,S,&buffers[SURFACES]},{5,S,&buffers[OFFSETS]},
            {6,A,nullptr,hwrt->top_level()},{7,S,&buffers[SHADING]},{8,S,&buffers[FRAME]},{9,S,&buffers[RAWPT]},{10,S,&buffers[CONTROLS]},{11,S,&buffers[DIAGNOSTICS]},{12,S,&buffers[COUNTERS]}};
        for(u32 s=0;s<5;s++)stage(reuse[s],("reuse_s"+std::to_string(s)+".spv").c_str(),rb,16);
        stage(accumulate,"timing_accumulate.spv",{{0,S,&buffers[RAWPT]},{1,S,&buffers[ACC]}},16);
        stage(copy,"timing_copy.spv",{{0,S,&buffers[FRAME]},{1,S,&buffers[SOURCES]}},16);
    }
    void barrier(){
        VkMemoryBarrier m{VK_STRUCTURE_TYPE_MEMORY_BARRIER};m.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT|VK_ACCESS_HOST_WRITE_BIT;m.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT|VK_ACCESS_HOST_READ_BIT;
        c.vk().cmdPipelineBarrier(command,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&m,0,nullptr,0,nullptr);
    }
    template<class F> double submit(F&& body){
        wall_guard();check(c.vk().resetFences(1,&fence));check(c.vk().resetCommandPool(pool,0));
        VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        check(c.vk().beginCommandBuffer(command,&bi));c.vk().cmdResetQueryPool(command,query,0,2);barrier();
        c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);body();barrier();
        c.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,1);check(c.vk().endCommandBuffer(command));
        VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&command;
        check(c.vk().queueSubmit(c.queue(),1,&si,fence));
        if(c.vk().waitForFences(1,&fence,VK_TRUE,250000000ull)!=VK_SUCCESS)incomplete_fence("044-submit");
        std::uint64_t tick[2]{};check(c.vk().getQueryPoolResults(query,0,2,sizeof tick,tick,8,VK_QUERY_RESULT_64_BIT));
        auto mask=bits==64?UINT64_MAX:((std::uint64_t(1)<<bits)-1);double us=double((tick[1]-tick[0])&mask)*properties.limits.timestampPeriod/1000.;
        need(std::isfinite(us)&&us>0&&us<=250000,"044 timestamp guard");submits++;
        log<<"{\"event\":\"submit\",\"submit\":"<<submits-1<<",\"timestamp_begin\":"<<tick[0]<<",\"timestamp_end\":"<<tick[1]<<",\"gpu_us\":"<<us<<"}\n";
        return us;
    }
    void dispatch_producer(std::unique_ptr<i::I001ComputeStage>& s,u32 spp,u32 seed){for(u32 p=0;p<N;p+=128){std::array<u32,4> push{spp,vertices,seed,p};s->record(command,4,1,1,push.data(),16);}}
    void reconstruction(){
        std::array<u32,4> push{0,0,0,N};quadratic->record(command,(N+31)/32,1,1,push.data(),16);barrier();
        for(u32 s=0;s<3;s++){for(u32 p=0;p<N;p+=128){push={1,s,p,128};quadratic->record(command,4,1,1,push.data(),16);}barrier();}
        for(u32 s=0;s<3;s++){push={2,s,0,N};quadratic->record(command,(N+31)/32,1,1,push.data(),16);barrier();}
        compose->record(command,(N+31)/32);
    }
    void reuse_stage(u32 stage,u32 index){std::array<u32,4> push{0,index,jenkins(index),0};reuse[stage]->record(command,(W+7)/8,(H+7)/8,1,push.data(),16);}
    double sample(const std::string& role,u32 parameter){
        u32 seed=jenkins(0x0a440000u+samples);double us=0;std::vector<double> parts;
        auto add=[&](double x){us+=x;parts.push_back(x);};
        if(role=="neutral"){u32 count=parameter>>16,iterations=parameter&0xffff;for(u32 k=0;k<count;k++)add(submit([&]{std::array<u32,4> push{iterations*64,N,seed+k,0};neutral->record(command,N/64,1,1,push.data(),16);}));}
        else if(role=="PT_REF"){u32 chunks=parameter/64;need(parameter%64==0&&chunks>0,"044 reference chunks");
            for(u32 k=0;k<chunks;k++)add(submit([&]{dispatch_producer(producer,64,seed^jenkins(k));barrier();std::array<u32,4> push{k==0?0u:1u,N,chunks,0};accumulate->record(command,N/64,1,1,push.data(),16);}));}
        else if(role=="PTR")add(submit([&]{dispatch_producer(producer,parameter,seed);barrier();reconstruction();}));
        else if(role=="RSR"){
            u32 index=frame_index++;
            add(submit([&]{dispatch_producer(physical,1,seed);barrier();reuse_stage(0,index);barrier();for(u32 s=1;s<4;s++){reuse_stage(s,index);barrier();}reuse_stage(4,index);barrier();
                std::array<u32,4> push{N,0,0,0};copy->record(command,N/64,1,1,push.data(),16);barrier();reconstruction();}));
            need(map<u32>(COUNTERS)[0]==0,"044 ReSTIR shader error flag");std::memset(map(COUNTERS),0,32);
        }
        else need(false,"044 unknown role");
        samples++;
        log<<"{\"event\":\"sample\",\"sample\":"<<samples-1<<",\"role\":"<<std::quoted(role)<<",\"parameter\":"<<parameter<<",\"submits\":"<<parts.size()<<",\"gpu_us\":"<<us<<"}\n";log.flush();
        return us;
    }
    void device(){
        std::ofstream f(out/"device.json");f<<std::setprecision(17)<<"{\"name\":"<<std::quoted(properties.deviceName)<<",\"driver_name\":"<<std::quoted(driver.driverName)<<",\"driver_info\":"<<std::quoted(driver.driverInfo)<<",\"vendor_id\":"<<properties.vendorID<<",\"device_id\":"<<properties.deviceID<<",\"driver_version\":"<<properties.driverVersion<<",\"api_version\":"<<properties.apiVersion<<",\"timestamp_valid_bits\":"<<bits<<",\"timestamp_period_ns\":"<<properties.limits.timestampPeriod<<",\"queue_family\":"<<c.queue_family()<<"}\n";need(bool(f),"044 device receipt");
        std::ofstream b(out/"buffers.json");b<<"{";for(u32 j=0;j<COUNT;j++)b<<(j?",":"")<<std::quoted(NAMES[j])<<":"<<sizes[j];b<<"}\n";need(bool(b),"044 buffer receipt");
    }
};
struct Comparison {std::string name;std::string a;u32 pa;std::string b;u32 pb;};
static void campaign(Runtime& run,const std::vector<Comparison>& list,u32 process){
    std::ofstream f(run.out/"pairs.jsonl");f<<std::setprecision(17);need(bool(f),"044 pair journal");
    std::this_thread::sleep_for(std::chrono::seconds(1));
    for(u32 pair=0;pair<WARMUP+MEASURED;pair++)for(u32 j=0;j<list.size();j++){
        const Comparison& k=list[(pair+j)%list.size()];bool ab=((pair+j+process)%2)==0;double ta=0,tb=0;
        Ledger::instance().phase(k.name+"-pair"+std::to_string(pair));
        if(ab){ta=run.sample(k.a,k.pa);tb=run.sample(k.b,k.pb);}else{tb=run.sample(k.b,k.pb);ta=run.sample(k.a,k.pa);}
        f<<"{\"comparison\":"<<std::quoted(k.name)<<",\"pair\":"<<pair<<",\"warmup\":"<<(pair<WARMUP?"true":"false")<<",\"order\":\""<<(ab?"AB":"BA")<<"\",\"position\":"<<j<<",\"a_us\":"<<ta<<",\"b_us\":"<<tb<<",\"log_b_over_a\":"<<std::log(tb/ta)<<"}\n";f.flush();
    }
}
int main(int argc,char** argv){fs::path output;
    try{
        need(argc>=2,"044 usage --calibration|--target ...");std::string mode=argv[1];need(mode=="--calibration"||mode=="--target"||mode=="--cpu-check","044 mode");std::map<std::string,std::string> args;
        for(int j=2;j<argc;j+=2){need(j+1<argc&&args.emplace(argv[j],argv[j+1]).second,"044 duplicate/missing option");}
        auto has=[&](std::initializer_list<const char*> keys){for(auto k:keys)if(!args.contains(k))return false;return args.size()==keys.size();};
        bool calibration=mode=="--calibration";
        need(calibration?has({"--out","--shaders","--process","--tiny","--short","--multi"}):has({"--state","--out","--vertices","--shaders","--offsets","--process","--reference-spp","--recon-spp"}),"044 options");
        fs::path target=args["--out"];need(!fs::exists(target)&&fs::is_directory(target.parent_path()),"044 exclusive output");
        u32 process=integer(args["--process"]);need(process<8,"044 process index");std::optional<State> state;u32 vertices=0;
        if(!calibration){state=load_state(args["--state"]);vertices=integer(args["--vertices"]);need(vertices==2||vertices==8,"044 depth");
            for(const char* name:{"integrated_producer.spv","surface_quadratic_device.spv","integrated_composite.spv","physical_producer.spv","reuse_s0.spv","reuse_s1.spv","reuse_s2.spv","reuse_s3.spv","reuse_s4.spv","timing_accumulate.spv","timing_copy.spv"})shader(fs::path(args["--shaders"])/name);}
        shader(fs::path(args["--shaders"])/"timing_neutral.spv");
        need(fs::create_directory(target),"044 output creation");output=target;safety_output=output;safety_started=Clock::now();
        if(state)for(const char* name:{"geometry-state.bin","frame-state.bin"})fs::copy_file(fs::path(args["--state"])/name,output/name);
        if(mode=="--cpu-check"){std::ofstream(output/"complete.json")<<"{\"complete\":true,\"gpu_initialized\":false}\n";return 0;}
        std::vector<Comparison> list;
        if(calibration){u32 t=integer(args["--tiny"]),s=integer(args["--short"]),l=integer(args["--multi"]);need(t>0&&s>0&&l>0&&t%100==0&&s%100==0&&l%100==0&&s*12/10<=0xffff,"044 calibration iterations");
            for(auto [size,count,base]:{std::tuple{"tiny",1u,t},std::tuple{"short",1u,s},std::tuple{"multi",16u,l}})for(u32 delta:{0u,5u,10u,20u})
                list.push_back({std::string(size)+"-plus"+std::to_string(delta),"neutral",(count<<16)|base,"neutral",(count<<16)|(base*(100+delta)/100)});}
        else{u32 ref=integer(args["--reference-spp"]),recon=integer(args["--recon-spp"]);need((ref==256||ref==1024)&&(recon==16||recon==64),"044 registered rungs");
            list={{"T1","PT_REF",ref,"PTR",recon},{"T2","PTR",1,"RSR",0},{"T3","PTR",4,"RSR",0},{"T4","PTR",16,"RSR",0}};}
        double setup_us=0;u32 samples=0,submits=0;
        {
            auto start=Clock::now();Ledger::instance().phase("context-upload-as-pipelines");b::B002VulkanContext context(false,b::kB002TargetDeviceName,true);
            std::unique_ptr<b::B002HwrtTraversal> hwrt;if(state)hwrt=std::make_unique<b::B002HwrtTraversal>(context,state->triangles,"",false);
            Runtime run(context,output);run.allocate(state?&*state:nullptr,hwrt.get(),args["--shaders"],state?fs::path(args["--offsets"]):fs::path(),vertices);run.device();
            setup_us=std::chrono::duration<double,std::micro>(Clock::now()-start).count();
            campaign(run,list,process);samples=run.samples;submits=run.submits;Ledger::instance().phase("teardown");
        }
        Ledger::instance().save(output/"allocation-ledger.json");need(reserved_bytes==0,"044 ownership teardown");
        std::ofstream f(output/"complete.json");f<<std::setprecision(17)<<"{\"complete\":true,\"gpu_initialized\":true,\"mode\":"<<std::quoted(mode)<<",\"process\":"<<process<<",\"comparisons\":"<<list.size()<<",\"pairs_per_comparison\":"<<WARMUP+MEASURED<<",\"warmup_pairs\":"<<WARMUP<<",\"samples\":"<<samples<<",\"submits\":"<<submits<<",\"aggregate_reserved_peak\":"<<reserved_peak<<",\"aggregate_reserved_at_teardown\":"<<reserved_bytes<<",\"setup_wall_us\":"<<setup_us<<",\"accepted_timing_requires_analysis\":true}\n";
        need(bool(f),"044 completion receipt");return 0;
    }catch(const std::exception& e){if(!output.empty()){Ledger::instance().save(output/"allocation-ledger.json");std::ofstream(output/"failure.txt")<<e.what()<<'\n';}std::cerr<<e.what()<<'\n';return 2;}
}

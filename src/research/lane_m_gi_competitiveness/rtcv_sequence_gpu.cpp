//049 sequence harness: raw PT / reprojected accumulation (PTA) / RTCV over a frame sequence.
// Ping-pong retained BLAS/TLAS (current and previous scene), AS refit per frame, GPU timestamps.
#include "integrated_safety.hpp"
#include "b002_hwrt.hpp"
#include "a001_runtime.hpp"
#include "i001_compute.hpp"
#include <array>
#include <charconv>
#include <cmath>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <vector>
using namespace m022;
namespace b=phos::gi::research::lane_b;
namespace a=phos::gi::lane_a;
namespace i=phos::gi::research::integration;
namespace fs=std::filesystem;
using u32=std::uint32_t;
constexpr u32 W=320,H=180,N=W*H,CHUNK=128,TX=(W+15)/16,TY=(H+15)/16,TILES=TX*TY,STRATA=((W+2)/3)*((H+2)/3);
constexpr u32 MAX_TRIANGLES=4u*1024u*1024u;
static void check(VkResult v){need(v==VK_SUCCESS,"049 Vulkan operation");}
static u32 integer(const std::string& s){u32 v=0;auto r=std::from_chars(s.data(),s.data()+s.size(),v);need(r.ec==std::errc{}&&r.ptr==s.data()+s.size(),"049 unsigned option");return v;}
static u32 jenkins(u32 x){
    x=(x+0x7ed55d16u)+(x<<12);x=(x^0xc761c23cu)^(x>>19);x=(x+0x165667b1u)+(x<<5);
    x=(x+0xd3a2646cu)^(x<<9);x=(x+0xfd7046c5u)+(x<<3);return (x^0xb55a4f09u)^(x>>16);
}
struct Frame {std::vector<b::Triangle> triangles;a::A001ParamsGpu params{};};
template<class T>static T read(std::ifstream& f){T x{};f.read(reinterpret_cast<char*>(&x),sizeof(x));need(bool(f),"049 truncated state");return x;}
// Private copy of the 022 loader without the 2048-triangle cap.
static Frame load(const fs::path& path){
    Frame s;auto gp=path/"geometry-state.bin",fp=path/"frame-state.bin";
    need(fs::is_regular_file(gp)&&fs::is_regular_file(fp),"049 state files missing");
    std::ifstream g(gp,std::ios::binary);need(read<u32>(g)==1,"049 geometry version");auto count=read<u32>(g);
    need(count>0&&count<=MAX_TRIANGLES&&fs::file_size(gp)==8+52ull*count,"049 geometry shape/range");s.triangles.reserve(count);
    for(u32 j=0;j<count;j++){
        b::Triangle t;t.v0=read<b::Vec3>(g);t.v1=read<b::Vec3>(g);t.v2=read<b::Vec3>(g);
        t.primitive_id=read<u32>(g);t.material_id=read<u32>(g);t.instance_id=read<u32>(g);auto two=read<u32>(g);t.two_sided=two==1;
        need(two==1&&t.primitive_id!=0xffffffffu&&t.instance_id!=0xffffffffu,"049 geometry metadata");
        for(auto v:{t.v0,t.v1,t.v2})need(std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z),"049 nonfinite vertex");
        s.triangles.push_back(t);
    }
    std::ifstream f(fp,std::ios::binary);char magic[12]{};f.read(magic,12);need(std::memcmp(magic,"N007-STATE1\0",12)==0&&fs::file_size(fp)==148,"049 frame magic/shape");
    auto width=read<u32>(f),height=read<u32>(f);s.params=read<a::A001ParamsGpu>(f);auto& p=s.params;
    need(width==W&&height==H&&p.counts[0]==count&&p.counts[1]==W&&p.counts[2]==H,"049 viewport/counts");
    for(auto axis:{p.camera_forward_far,p.camera_right_tan_x,p.camera_up_tan_y}){float n=(axis[0]*axis[0]+axis[1]*axis[1])+axis[2]*axis[2];need(std::abs(n-1)<=1e-4f,"049 camera basis not unit");}
    need(p.camera_forward_far[3]>=1e-4f&&p.camera_right_tan_x[3]>0&&p.camera_up_tan_y[3]>0&&p.light_pos_interval[3]>0,"049 camera/light range");
    return s;
}
static bool same_vertex(const b::Vec3& x,const b::Vec3& y){return x.x==y.x&&x.y==y.y&&x.z==y.z;}
static std::vector<u32> moved(const Frame& from,const Frame& to){
    need(from.triangles.size()==to.triangles.size(),"049 stable topology");std::vector<u32> list;
    for(u32 j=0;j<to.triangles.size();j++){const auto &x=from.triangles[j],&y=to.triangles[j];
        need(x.primitive_id==y.primitive_id&&x.instance_id==y.instance_id&&x.material_id==y.material_id,"049 stable primitive identity");
        if(!same_vertex(x.v0,y.v0)||!same_vertex(x.v1,y.v1)||!same_vertex(x.v2,y.v2))list.push_back(j);}
    return list;
}
static bool same_light(const a::A001ParamsGpu& x,const a::A001ParamsGpu& y){return std::memcmp(x.light_pos_interval,y.light_pos_interval,16)==0;}
static bool same_camera(const a::A001ParamsGpu& x,const a::A001ParamsGpu& y){return std::memcmp(&x,&y,64)==0;}
struct Push {u32 mode,seed,start,k,k_new,vertices,flags,n_max,ratio_bits;};
static u32 role_id(const std::string& r){
    static const std::map<std::string,u32> ids{{"PT",0},{"PTA",1},{"RTCV",2},{"PTG",3},{"RTCVF",4},{"PTR",5}};
    need(ids.contains(r),"049 role");return ids.at(r);
}
struct Config {std::string role;u32 k{},k_new{},n_max{},vertices{},seed{};};
// One role's complete per-frame state: its own BLAS/TLAS (ping-pong current/previous for
// history roles), history/anchor buffers and command resources. Every GPU cost of a frame
// (AS refit, primary, paths, filtering, reductions, PTR operator) is timestamped.
struct RoleRun {
    struct Result {double render_us{},as_us{},upload_wall_us{};u32 flags{};std::size_t moved{};};
    b::B002VulkanContext& context;const std::vector<Frame>& seq;Config c;u32 id;bool pingpong,ptr;
    std::array<std::unique_ptr<b::B002HwrtTraversal>,2> trav;std::array<u32,2> held{0,0};VkPhysicalDeviceProperties props{};
    std::array<b::B002Buffer,2> params,anchor,hist;b::B002Buffer image{},tiles{},grad{},scratch{};std::array<b::B002Buffer,8> q{};
    std::array<std::unique_ptr<i::I001ComputeStage>,2> stage;std::unique_ptr<i::I001ComputeStage> quadratic;
    VkCommandPool pool{};VkCommandBuffer cmd{};VkFence fence{};VkQueryPool query{};std::uint64_t owned{};
    b::B002Buffer host(std::uint64_t bytes,VkBufferUsageFlags usage){auto x=context.create_host_buffer(bytes,usage);std::memset(x.mapped,0,bytes);owned+=bytes;return x;}
    RoleRun(b::B002VulkanContext& ctx,const std::vector<Frame>& s,Config cfg,const fs::path& shaders):context(ctx),seq(s),c(std::move(cfg)),id(role_id(c.role)){
        pingpong=c.role!="PT"&&c.role!="PTR";ptr=id==5;
        trav[0]=std::make_unique<b::B002HwrtTraversal>(context,seq[0].triangles,"",false);
        if(pingpong)trav[1]=std::make_unique<b::B002HwrtTraversal>(context,seq[0].triangles,"",false);
        vkGetPhysicalDeviceProperties(context.physical_device(),&props);
        const VkBufferUsageFlags SB=VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
        for(u32 j=0;j<2;j++){params[j]=host(sizeof(a::A001ParamsGpu),VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT);anchor[j]=host(48ull*N,SB);hist[j]=host(32ull*N,SB);}
        image=host(16ull*N,SB);tiles=host(4ull*TILES,SB);grad=host(id==3?4ull*STRATA:16,SB);scratch=host(id==4?16ull*N:16,SB);
        const std::array<std::uint64_t,8> qsize{32ull*N,80,32ull*N,300ull*N,24ull*N,4ull*N,12ull*N,12ull*N};
        for(u32 j=0;j<8;j++)q[j]=host(ptr?qsize[j]:16,SB);
        for(u32 t=0;t<TILES;t++)static_cast<float*>(tiles.mapped)[t]=1.0f;
        const VkDescriptorType S=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,A=VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,U=VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        fs::path spv=shaders/("rtcv_role"+std::to_string(id)+".spv");need(fs::is_regular_file(spv),"049 shader");
        for(u32 j=0;j<2;j++){auto& cur=*trav[pingpong?j:0];auto& prev=*trav[pingpong?1-j:0];
            std::vector<i::I001Binding> bind{{0,S,&image},{1,A,nullptr,cur.top_level()},{2,S,&cur.triangle_buffer()},{3,U,&params[j]},{4,A,nullptr,prev.top_level()},{5,S,&prev.triangle_buffer()},{6,U,&params[1-j]},
                {7,S,&anchor[j]},{8,S,&anchor[1-j]},{9,S,&hist[j]},{10,S,&hist[1-j]},{11,S,&tiles},{12,S,&grad},{13,S,&scratch},{14,S,&q[0]},{15,S,&q[5]},{16,S,&q[6]}};
            stage[j]=std::make_unique<i::I001ComputeStage>(context,spv.string(),bind,sizeof(Push));}
        if(ptr){std::vector<i::I001Binding> qb;for(u32 j=0;j<8;j++)qb.push_back({j,S,&q[j]});quadratic=std::make_unique<i::I001ComputeStage>(context,(shaders/"surface_quadratic_device.spv").string(),qb,16);}
        VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=context.queue_family();pi.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;check(context.vk().createCommandPool(&pi,nullptr,&pool));
        VkCommandBufferAllocateInfo ai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ai.commandPool=pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;check(context.vk().allocateCommandBuffers(&ai,&cmd));
        VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};check(context.vk().createFence(&fi,nullptr,&fence));
        VkQueryPoolCreateInfo qi{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};qi.queryType=VK_QUERY_TYPE_TIMESTAMP;qi.queryCount=2;check(context.vk().createQueryPool(&qi,nullptr,&query));
    }
    ~RoleRun(){
        if(query)context.vk().destroyQueryPool(query,nullptr);if(fence)context.vk().destroyFence(fence,nullptr);if(pool)context.vk().destroyCommandPool(pool,nullptr);
        for(auto& st:stage)st.reset();quadratic.reset();
        for(u32 j=0;j<2;j++){context.destroy_buffer(params[j]);context.destroy_buffer(anchor[j]);context.destroy_buffer(hist[j]);}
        context.destroy_buffer(image);context.destroy_buffer(tiles);context.destroy_buffer(grad);context.destroy_buffer(scratch);for(auto& x:q)context.destroy_buffer(x);
        for(auto& t:trav)t.reset();
    }
    void barrier(){VkMemoryBarrier m{VK_STRUCTURE_TYPE_MEMORY_BARRIER};m.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT|VK_ACCESS_HOST_WRITE_BIT;m.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT|VK_ACCESS_HOST_READ_BIT;
        context.vk().cmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT|VK_PIPELINE_STAGE_ACCELERATION_STRUCTURE_BUILD_BIT_KHR,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&m,0,nullptr,0,nullptr);}
    void record(u32 mode,u32 count,const Push& base){for(u32 p=0;p<count;p+=CHUNK){Push push=base;push.mode=mode;push.start=p;stage[cur_slot]->record(cmd,CHUNK/32,1,1,&push,sizeof push);}barrier();}
    u32 cur_slot{};
    Result frame(u32 f,u32 k_override=0){
        wall_guard();Result r;const u32 s=pingpong?f%2:0;cur_slot=s;auto& cur=*trav[pingpong?s:0];
        const Frame& now=seq[f];const Frame& before=seq[f?f-1:0];
        // Bring this traversal from the state it holds to frame f (refit, GPU-timestamped).
        auto list=moved(seq[held[pingpong?s:0]],now);r.moved=list.size();
        if(!list.empty()){auto st=cur.update_geometry(now.triangles,list);r.as_us=st.blas_update_us+st.tlas_update_us;r.upload_wall_us=st.geometry_upload_us;}
        held[pingpong?s:0]=f;
        std::memcpy(params[s].mapped,&now.params,sizeof(a::A001ParamsGpu));if(!pingpong)std::memcpy(params[1].mapped,&now.params,sizeof(a::A001ParamsGpu));
        u32 flags=0;if(f==0)flags|=8u;
        if(!moved(before,now).empty())flags|=1u;if(!same_light(before.params,now.params))flags|=2u;if(!same_camera(before.params,now.params))flags|=4u;r.flags=flags;
        if(ptr){float* cam=static_cast<float*>(q[1].mapped);const auto& pp=now.params;
            for(int a=0;a<4;a++){cam[a]=pp.camera_pos_near[a];cam[4+a]=pp.camera_forward_far[a];cam[8+a]=pp.camera_right_tan_x[a];cam[12+a]=pp.camera_up_tan_y[a];}
            float lo[3]{INFINITY,INFINITY,INFINITY},hi[3]{-INFINITY,-INFINITY,-INFINITY};
            for(const auto& t:now.triangles)for(auto v:{t.v0,t.v1,t.v2}){float x[3]{v.x,v.y,v.z};for(int a=0;a<3;a++){lo[a]=std::min(lo[a],x[a]);hi[a]=std::max(hi[a],x[a]);}}
            float dx=hi[0]-lo[0],dy=hi[1]-lo[1],dz=hi[2]-lo[2];cam[16]=float(1e-5*std::max(1.,double(std::sqrt((dx*dx+dy*dy)+dz*dz))));cam[17]=1;cam[18]=W;cam[19]=H;}
        check(context.vk().resetFences(1,&fence));check(context.vk().resetCommandPool(pool,0));
        VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;check(context.vk().beginCommandBuffer(cmd,&bi));
        context.vk().cmdResetQueryPool(cmd,query,0,2);barrier();context.vk().cmdWriteTimestamp(cmd,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);
        Push base{0,jenkins(c.seed*0x9e3779b9u+f),0,k_override?k_override:c.k,c.k_new,c.vertices,flags,c.n_max,0};
        record(0,N,base);
        if(id==3){record(1,STRATA,base);record(2,N,base);}
        else if(id==4){record(1,N,base);record(2,N,base);record(3,TILES,base);}
        else if(id==2){record(1,N,base);record(2,TILES,base);}
        else if(id==5){record(1,N,base);std::array<u32,4> qp{0,0,0,N};quadratic->record(cmd,(N+31)/32,1,1,qp.data(),16);barrier();
            for(u32 st=0;st<3;st++){for(u32 p=0;p<N;p+=CHUNK){qp={1,st,p,CHUNK};quadratic->record(cmd,CHUNK/32,1,1,qp.data(),16);}barrier();}
            for(u32 st=0;st<3;st++){qp={2,st,0,N};quadratic->record(cmd,(N+31)/32,1,1,qp.data(),16);barrier();}
            record(2,N,base);}
        else record(1,N,base);
        context.vk().cmdWriteTimestamp(cmd,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,1);check(context.vk().endCommandBuffer(cmd));
        VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&cmd;check(context.vk().queueSubmit(context.queue(),1,&si,fence));
        if(context.vk().waitForFences(1,&fence,VK_TRUE,2000000000ull)!=VK_SUCCESS)incomplete_fence("049-frame");
        std::uint64_t tick[2]{};check(context.vk().getQueryPoolResults(query,0,2,sizeof tick,tick,8,VK_QUERY_RESULT_64_BIT));
        r.render_us=double(tick[1]-tick[0])*props.limits.timestampPeriod/1000.;need(std::isfinite(r.render_us)&&r.render_us>0,"049 timestamp");
        return r;
    }
    void save(const fs::path& path){const float* px=static_cast<const float*>(image.mapped);std::vector<float> out(2ull*N);for(u32 j=0;j<N;j++){out[2*j]=px[4*j];out[2*j+1]=px[4*j+1];}
        std::ofstream img(path,std::ios::binary);img.write(reinterpret_cast<const char*>(out.data()),std::streamsize(out.size()*4));need(bool(img),"049 image write");}
    double history_sum(u32 f,u32 slot)const{const float* h=static_cast<const float*>(hist[pingpong?f%2:0].mapped);double x=0;for(u32 j=0;j<N;j++)x+=h[8*j+slot];return x;}
};
static Config config(std::map<std::string,std::string>& args,const std::string& suffix){
    Config c;c.role=args["--role"+suffix];role_id(c.role);c.k=integer(args["--k"+suffix]);c.k_new=integer(args["--k-new"]);c.n_max=integer(args["--n-max"+suffix]);
    c.vertices=integer(args["--vertices"]);c.seed=integer(args["--seed"]);
    need(c.vertices>=2&&c.vertices<=8&&c.k>0&&c.k<=65536&&c.k_new>0&&c.k_new<=256&&c.n_max>=1&&c.n_max<=4096,"049 parameter range");return c;
}
int main(int argc,char** argv){fs::path output;
    try{
        need(argc>=2,"049 usage: --capture|--timing options");const std::string mode=argv[1];need(mode=="--capture"||mode=="--timing","049 mode");
        std::map<std::string,std::string> args;for(int j=2;j<argc;j+=2){need(j+1<argc&&args.emplace(argv[j],argv[j+1]).second,"049 duplicate/missing option");}
        const bool timing=mode=="--timing";
        const std::vector<std::string> keys=timing?std::vector<std::string>{"--sequence","--out","--vertices","--shaders","--k-new","--seed","--role-a","--k-a","--n-max-a","--role-b","--k-b","--n-max-b","--settle","--measured","--process"}
                                                :std::vector<std::string>{"--sequence","--frames","--out","--vertices","--shaders","--role","--k","--k-new","--n-max","--capture","--seed","--ref-spp"};
        for(const auto& key:keys)need(args.contains(key),"049 options");need(args.size()==keys.size(),"049 unknown option");
        fs::path target=args["--out"];need(!fs::exists(target)&&fs::is_directory(target.parent_path()),"049 exclusive output");
        constexpr u32 WARMUP=4;u32 frames=0,settle=0,measured=0,process=0;
        if(timing){settle=integer(args["--settle"]);measured=integer(args["--measured"]);process=integer(args["--process"]);need(measured==32&&process<8,"045 measured pairs/process");frames=settle+WARMUP+measured;}
        else frames=integer(args["--frames"]);
        need(frames>0&&frames<=4096,"049 frames");
        std::vector<Frame> seq;for(u32 f=0;f<frames;f++){std::ostringstream name;name<<std::setw(4)<<std::setfill('0')<<f;seq.push_back(load(fs::path(args["--sequence"])/name.str()));}
        need(fs::create_directory(target),"049 output creation");output=target;safety_output=output;safety_started=Clock::now();
        std::ofstream log(output/(timing?"pairs.jsonl":"frames.jsonl"));log<<std::setprecision(17);need(bool(log),"049 journal");
        std::uint64_t owned_a=0,owned_b=0;
        {
            Ledger::instance().phase("context-as-pipelines");b::B002VulkanContext context(false,b::kB002TargetDeviceName,true);
            if(!timing){
                Config c=config(args,"");const u32 ref_spp=integer(args["--ref-spp"]);need(ref_spp==0||c.role=="PT","049 reference spp only for PT");
                std::set<u32> capture;{std::stringstream ss(args["--capture"]);std::string item;while(std::getline(ss,item,','))if(!item.empty()){u32 x=integer(item);need(x<frames,"049 capture frame");capture.insert(x);}}
                RoleRun run(context,seq,c,args["--shaders"]);owned_a=run.owned;Ledger::instance().phase("frames");
                for(u32 f=0;f<frames;f++){const bool cap=capture.contains(f);auto r=run.frame(f,(ref_spp&&cap)?ref_spp:0);
                    log<<"{\"frame\":"<<f<<",\"flags\":"<<r.flags<<",\"moved\":"<<r.moved<<",\"as_gpu_us\":"<<r.as_us<<",\"as_upload_wall_us\":"<<r.upload_wall_us<<",\"render_gpu_us\":"<<r.render_us
                       <<",\"replays\":"<<run.history_sum(f,7)<<",\"captured\":"<<(cap?"true":"false")<<"}\n";log.flush();
                    if(cap){std::ostringstream name;name<<"frame-"<<std::setw(4)<<std::setfill('0')<<f<<".f32";run.save(output/name.str());}}
                Ledger::instance().phase("teardown");
            }else{
                // 045 AB/BA protocol over a sequence: each pair renders the same frame index once per
                // role (independent states); AB iff (pair+process) is even. Settle frames precede the
                // 4 warm-up and 32 measured pairs so that history roles are in steady state.
                Config ca=config(args,"-a"),cb=config(args,"-b");RoleRun ra(context,seq,ca,args["--shaders"]),rb(context,seq,cb,args["--shaders"]);owned_a=ra.owned;owned_b=rb.owned;
                Ledger::instance().phase("settle");for(u32 f=0;f<settle;f++){if((f+process)%2==0){ra.frame(f);rb.frame(f);}else{rb.frame(f);ra.frame(f);}}
                Ledger::instance().phase("pairs");
                for(u32 pair=0;pair<WARMUP+measured;pair++){const u32 f=settle+pair;const bool ab=((pair+process)%2)==0;RoleRun::Result x,y;
                    if(ab){x=ra.frame(f);y=rb.frame(f);}else{y=rb.frame(f);x=ra.frame(f);}
                    const double ta=x.render_us+x.as_us,tb=y.render_us+y.as_us;
                    log<<"{\"comparison\":\"T1\",\"pair\":"<<pair<<",\"frame\":"<<f<<",\"warmup\":"<<(pair<WARMUP?"true":"false")<<",\"order\":\""<<(ab?"AB":"BA")<<"\",\"position\":0,\"a_us\":"<<ta<<",\"b_us\":"<<tb
                       <<",\"a_as_us\":"<<x.as_us<<",\"b_as_us\":"<<y.as_us<<",\"log_b_over_a\":"<<std::log(tb/ta)<<"}\n";log.flush();}
                Ledger::instance().phase("teardown");
            }
        }
        Ledger::instance().save(output/"allocation-ledger.json");need(reserved_bytes==0,"049 ownership teardown");
        std::ofstream(output/"complete.json")<<"{\"complete\":true,\"mode\":\""<<(timing?"timing":"capture")<<"\",\"frames\":"<<frames<<",\"measured_pairs\":"<<measured<<",\"role_owned_host_buffer_bytes_a\":"<<owned_a<<",\"role_owned_host_buffer_bytes_b\":"<<owned_b
            <<",\"aggregate_reserved_peak\":"<<reserved_peak<<",\"aggregate_reserved_at_teardown\":"<<reserved_bytes<<"}\n";
        return 0;
    }catch(const std::exception& e){if(!output.empty()){Ledger::instance().save(output/"allocation-ledger.json");std::ofstream(output/"failure.txt")<<e.what()<<'\n';}std::cerr<<e.what()<<'\n';return 2;}
}

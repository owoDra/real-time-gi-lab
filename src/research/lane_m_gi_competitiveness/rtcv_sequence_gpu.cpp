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
int main(int argc,char** argv){fs::path output;
    try{
        std::map<std::string,std::string> args;for(int j=1;j<argc;j+=2){need(j+1<argc&&args.emplace(argv[j],argv[j+1]).second,"049 duplicate/missing option");}
        for(auto key:{"--sequence","--frames","--out","--vertices","--shaders","--role","--k","--k-new","--n-max","--capture","--seed","--ref-spp"})need(args.contains(key),"049 options");
        need(args.size()==12,"049 unknown option");
        const std::string role=args["--role"];need(role=="PT"||role=="PTA"||role=="RTCV"||role=="PTG"||role=="RTCVF","049 role");const u32 role_id=role=="PT"?0:role=="PTA"?1:role=="RTCV"?2:role=="PTG"?3:4;
        const u32 frames=integer(args["--frames"]),vertices=integer(args["--vertices"]),k=integer(args["--k"]),k_new=integer(args["--k-new"]),n_max=integer(args["--n-max"]),seed=integer(args["--seed"]),ref_spp=integer(args["--ref-spp"]);
        need(frames>0&&frames<=4096&&vertices>=2&&vertices<=8&&k>0&&k<=65536&&k_new>0&&k_new<=256&&n_max>=1&&n_max<=4096,"049 parameter range");
        std::set<u32> capture;{std::stringstream ss(args["--capture"]);std::string item;while(std::getline(ss,item,','))if(!item.empty()){u32 c=integer(item);need(c<frames,"049 capture frame");capture.insert(c);}}
        need(ref_spp==0||role=="PT","049 reference spp only for PT");
        fs::path target=args["--out"];need(!fs::exists(target)&&fs::is_directory(target.parent_path()),"049 exclusive output");
        std::vector<Frame> seq;for(u32 f=0;f<frames;f++){std::ostringstream name;name<<std::setw(4)<<std::setfill('0')<<f;seq.push_back(load(fs::path(args["--sequence"])/name.str()));}
        fs::path spv=fs::path(args["--shaders"])/("rtcv_role"+std::to_string(role_id)+".spv");need(fs::is_regular_file(spv),"049 shader");
        need(fs::create_directory(target),"049 output creation");output=target;safety_output=output;safety_started=Clock::now();
        std::ofstream log(output/"frames.jsonl");log<<std::setprecision(17);
        {
            Ledger::instance().phase("context-as-pipelines");b::B002VulkanContext context(false,b::kB002TargetDeviceName,true);
            const bool pingpong=role!="PT";
            std::array<std::unique_ptr<b::B002HwrtTraversal>,2> trav;std::array<u32,2> held{0,0};
            trav[0]=std::make_unique<b::B002HwrtTraversal>(context,seq[0].triangles,"",false);
            if(pingpong)trav[1]=std::make_unique<b::B002HwrtTraversal>(context,seq[0].triangles,"",false);
            VkPhysicalDeviceProperties props{};vkGetPhysicalDeviceProperties(context.physical_device(),&props);
            std::array<b::B002Buffer,2> params,anchor,hist;b::B002Buffer image,tiles,grad,scratch;
            for(u32 s=0;s<2;s++){params[s]=context.create_host_buffer(sizeof(a::A001ParamsGpu),VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT);
                anchor[s]=context.create_host_buffer(48ull*N,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);hist[s]=context.create_host_buffer(32ull*N,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                std::memset(anchor[s].mapped,0,48ull*N);std::memset(hist[s].mapped,0,32ull*N);}
            image=context.create_host_buffer(16ull*N,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);tiles=context.create_host_buffer(4ull*TILES,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);grad=context.create_host_buffer(4ull*STRATA,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);scratch=context.create_host_buffer(16ull*N,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            for(u32 t=0;t<TILES;t++)static_cast<float*>(tiles.mapped)[t]=1.0f;
            const VkDescriptorType S=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,A=VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,U=VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
            std::array<std::unique_ptr<i::I001ComputeStage>,2> stage;
            for(u32 s=0;s<2;s++){auto& cur=*trav[pingpong?s:0];auto& prev=*trav[pingpong?1-s:0];
                std::vector<i::I001Binding> bind{{0,S,&image},{1,A,nullptr,cur.top_level()},{2,S,&cur.triangle_buffer()},{3,U,&params[s]},{4,A,nullptr,prev.top_level()},{5,S,&prev.triangle_buffer()},{6,U,&params[1-s]},
                    {7,S,&anchor[s]},{8,S,&anchor[1-s]},{9,S,&hist[s]},{10,S,&hist[1-s]},{11,S,&tiles},{12,S,&grad},{13,S,&scratch}};
                stage[s]=std::make_unique<i::I001ComputeStage>(context,spv.string(),bind,sizeof(Push));}
            VkCommandPool pool{};VkCommandBuffer cmd{};VkFence fence{};VkQueryPool query{};
            VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=context.queue_family();pi.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;check(context.vk().createCommandPool(&pi,nullptr,&pool));
            VkCommandBufferAllocateInfo ai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ai.commandPool=pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;check(context.vk().allocateCommandBuffers(&ai,&cmd));
            VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};check(context.vk().createFence(&fi,nullptr,&fence));
            VkQueryPoolCreateInfo qi{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};qi.queryType=VK_QUERY_TYPE_TIMESTAMP;qi.queryCount=2;check(context.vk().createQueryPool(&qi,nullptr,&query));
            auto barrier=[&]{VkMemoryBarrier m{VK_STRUCTURE_TYPE_MEMORY_BARRIER};m.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT|VK_ACCESS_HOST_WRITE_BIT;m.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT|VK_ACCESS_HOST_READ_BIT;
                context.vk().cmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT|VK_PIPELINE_STAGE_ACCELERATION_STRUCTURE_BUILD_BIT_KHR,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&m,0,nullptr,0,nullptr);};
            Ledger::instance().phase("frames");
            float ratio=1.0f;const double scale=std::getenv("RTCV_DEV_RATIO_SCALE")?std::atof(std::getenv("RTCV_DEV_RATIO_SCALE")):1.0;  // dev-only knob  // frame-global replay-difference/sample variance ratio from the previous frame
            for(u32 f=0;f<frames;f++){
                wall_guard();const u32 s=pingpong?f%2:0;auto& cur=*trav[pingpong?s:0];
                const Frame& now=seq[f];const Frame& before=seq[f?f-1:0];
                // Bring this traversal from the state it holds to frame f (refit, GPU-timestamped).
                auto list=moved(seq[held[pingpong?s:0]],now);double as_gpu_us=0,upload_us=0;
                if(!list.empty()){auto st=cur.update_geometry(now.triangles,list);as_gpu_us=st.blas_update_us+st.tlas_update_us;upload_us=st.geometry_upload_us;}
                held[pingpong?s:0]=f;
                std::memcpy(params[s].mapped,&now.params,sizeof(a::A001ParamsGpu));
                if(!pingpong)std::memcpy(params[1].mapped,&now.params,sizeof(a::A001ParamsGpu));
                u32 flags=0;if(f==0)flags|=8u;
                if(!moved(before,now).empty())flags|=1u;if(!same_light(before.params,now.params))flags|=2u;if(!same_camera(before.params,now.params))flags|=4u;
                const bool cap=capture.contains(f);const u32 kk=(ref_spp&&cap)?ref_spp:k;
                const u32 fseed=jenkins(seed*0x9e3779b9u+f);
                check(context.vk().resetFences(1,&fence));check(context.vk().resetCommandPool(pool,0));
                VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;check(context.vk().beginCommandBuffer(cmd,&bi));
                context.vk().cmdResetQueryPool(cmd,query,0,2);barrier();context.vk().cmdWriteTimestamp(cmd,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);
                const u32 modes=role_id>=3?3:2;
                for(u32 mode=0;mode<modes;mode++){const u32 count=(role_id==3&&mode==1)?STRATA:N;for(u32 p=0;p<count;p+=CHUNK){u32 rb;std::memcpy(&rb,&ratio,4);Push push{mode,fseed,p,kk,k_new,vertices,flags,n_max,rb};stage[s]->record(cmd,CHUNK/32,1,1,&push,sizeof push);}barrier();}
                context.vk().cmdWriteTimestamp(cmd,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,1);check(context.vk().endCommandBuffer(cmd));
                VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&cmd;check(context.vk().queueSubmit(context.queue(),1,&si,fence));
                if(context.vk().waitForFences(1,&fence,VK_TRUE,2000000000ull)!=VK_SUCCESS)incomplete_fence("049-frame");
                std::uint64_t tick[2]{};check(context.vk().getQueryPoolResults(query,0,2,sizeof tick,tick,8,VK_QUERY_RESULT_64_BIT));
                double render_us=double(tick[1]-tick[0])*props.limits.timestampPeriod/1000.;need(std::isfinite(render_us)&&render_us>0,"049 timestamp");
                const float* hst=static_cast<const float*>(hist[s].mapped);double replays=0,valid=0,sd=0,sv=0;for(u32 j=0;j<N;j++){replays+=hst[8*j+7];valid+=hst[8*j+6];if(hst[8*j+7]>0){sd+=hst[8*j+4];sv+=std::max(0.f,hst[8*j+3]-hst[8*j+2]*hst[8*j+2]);}}
                const float used=ratio;if(sv>0)ratio=float(std::min(sd/sv,2.0));
                {std::vector<double> td(TILES,0),tv(TILES,0),tn(TILES,0);for(u32 j=0;j<N;j++)if(hst[8*j+7]>0){u32 t=(j/W/16)*TX+(j%W)/16;td[t]+=hst[8*j+4];tv[t]+=std::max(0.f,hst[8*j+3]-hst[8*j+2]*hst[8*j+2]);tn[t]+=1;}
                 float* tr=static_cast<float*>(tiles.mapped);if(replays>0)for(u32 t=0;t<TILES;t++)tr[t]=tn[t]>=16&&tv[t]>0?float(std::min(scale*td[t]/tv[t],2.0)):ratio;}
                log<<"{\"frame\":"<<f<<",\"flags\":"<<flags<<",\"moved\":"<<list.size()<<",\"as_gpu_us\":"<<as_gpu_us<<",\"as_upload_wall_us\":"<<upload_us<<",\"render_gpu_us\":"<<render_us<<",\"k\":"<<kk<<",\"replays\":"<<replays<<",\"ratio_used\":"<<used<<",\"history_pixels\":"<<valid<<",\"captured\":"<<(cap?"true":"false")<<"}\n";log.flush();
                if(cap){const float* px=static_cast<const float*>(image.mapped);std::vector<float> out(2ull*N);for(u32 j=0;j<N;j++){out[2*j]=px[4*j];out[2*j+1]=px[4*j+1];}
                    std::ostringstream name;name<<"frame-"<<std::setw(4)<<std::setfill('0')<<f<<".f32";std::ofstream img(output/name.str(),std::ios::binary);img.write(reinterpret_cast<const char*>(out.data()),std::streamsize(out.size()*4));need(bool(img),"049 image write");}
            }
            Ledger::instance().phase("teardown");
            context.vk().destroyQueryPool(query,nullptr);context.vk().destroyFence(fence,nullptr);context.vk().destroyCommandPool(pool,nullptr);
            for(auto& st:stage)st.reset();
            for(u32 s=0;s<2;s++){context.destroy_buffer(params[s]);context.destroy_buffer(anchor[s]);context.destroy_buffer(hist[s]);}context.destroy_buffer(image);context.destroy_buffer(tiles);context.destroy_buffer(grad);context.destroy_buffer(scratch);
            for(auto& t:trav)t.reset();
        }
        Ledger::instance().save(output/"allocation-ledger.json");need(reserved_bytes==0,"049 ownership teardown");
        std::ofstream(output/"complete.json")<<"{\"complete\":true,\"role\":\""<<role<<"\",\"frames\":"<<frames<<",\"aggregate_reserved_peak\":"<<reserved_peak<<",\"aggregate_reserved_at_teardown\":"<<reserved_bytes<<"}\n";
        return 0;
    }catch(const std::exception& e){if(!output.empty()){Ledger::instance().save(output/"allocation-ledger.json");std::ofstream(output/"failure.txt")<<e.what()<<'\n';}std::cerr<<e.what()<<'\n';return 2;}
}

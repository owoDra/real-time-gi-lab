// Experimental oracle execution port; no reference eligibility by build/run.
#include "n010_reference_snapshot.hpp"
#include "n010_reference_context.hpp"
#include <chrono>
namespace N = phos::gi::research::n008;
struct alignas(32) D4 { double v[4]{}; };
struct alignas(32) GNode { D4 lo,hi; };
struct alignas(32) GTriangle { D4 a,b,c,rho,emit,normal; };
struct alignas(32) GPoint { D4 position,intensity; };
struct alignas(32) GPrimary { D4 origin,normal,rho,direct,emit; uint64_t counters[4]{}; };
struct alignas(32) GStats { D4 sum[4],sum2[4]; uint64_t counters[4]{}; };
struct alignas(32) Params { D4 physical; uint32_t sizes[4]{},interval[4]{},seed[4]{}; };
static_assert(sizeof(GNode)==64 && sizeof(GTriangle)==192 && sizeof(GPrimary)==192 && sizeof(GStats)==288 && sizeof(Params)==96);
static D4 d4(N::V3 v,double w=0) { return {{v.x,v.y,v.z,w}}; }
static D4 d4(N::Rgb v,double w=0) { return {{v[0],v[1],v[2],w}}; }
struct NoDraw { double uniform(){throw std::runtime_error("unexpected host RNG use");} };
static void sidecar(const fs::path& path,const N::Scene& scene,uint64_t seed,uint32_t spp,const GStats* stats) {
    std::ofstream file(path,std::ios::binary);file.write("N008F64\0",8);uint32_t shape[3]={scene.width,scene.height,spp};file.write(reinterpret_cast<char*>(shape),12);file.write(reinterpret_cast<char*>(&seed),8);
    for(size_t p=0;p<size_t(scene.width)*scene.height;++p){double values[24]{};for(int k=0;k<4;++k)for(int channel=0;channel<3;++channel){values[k*3+channel]=stats[p].sum[k].v[channel]/spp;values[12+k*3+channel]=stats[p].sum2[k].v[channel]/spp;}file.write(reinterpret_cast<char*>(values),sizeof values);}
    if(!file)throw std::runtime_error("sidecar write failed");
}
static void execute(const N::Scene& scene,const fs::path& net,const fs::path& shader,uint64_t seed,uint32_t spp,uint32_t batch,const fs::path& out) {
    if(scene.sampling!=N::Sampling::Center || scene.max_bounces<1 || scene.max_bounces>8)throw std::runtime_error("unsupported sampling/depth");
    for(auto m:scene.materials)for(double e:m.emit)if(e!=0)throw std::runtime_error("emissive scenes unsupported in this port");
    N::N010NetRng::load(net.string());N::Oracle oracle(scene);
    std::vector<GNode> nodes;std::vector<GTriangle> triangles;std::vector<GPoint> lights;
    for(auto node:oracle.bvh().n010_nodes())nodes.push_back({d4(node.box.lo,node.count?node.first:node.right),d4(node.box.hi,node.count)});
    for(auto tri:scene.triangles){auto m=scene.materials[tri.material];auto ng=N::cross(tri.v1-tri.v0,tri.v2-tri.v0);if(N::dot(ng,ng)>0)ng=N::normalize(ng);triangles.push_back({d4(tri.v0),d4(tri.v1),d4(tri.v2),d4(m.rho,m.two_sided?1:0),d4(m.emit),d4(ng)});}
    for(auto p:scene.points)lights.push_back({d4(p.position),d4(p.intensity)});
    const size_t pixels=size_t(scene.width)*scene.height;std::vector<GPrimary> primary(pixels);std::vector<N::PrimaryRecord> hits(pixels);
    for(uint32_t y=0;y<scene.height;++y)for(uint32_t x=0;x<scene.width;++x){
        size_t index=size_t(y)*scene.width+x;auto& p=primary[index];auto ray=oracle.primary_ray(x,y,.5,.5);auto hit=oracle.bvh().closest(ray,scene.camera.near,scene.camera.far,UINT32_MAX);
        if(!hit.hit())continue;p.counters[0]=1;auto tri=scene.triangles[hit.tri];auto m=scene.materials[tri.material];auto ng=N::normalize(N::cross(tri.v1-tri.v0,tri.v2-tri.v0));bool front=N::dot(ng,ray.dir)<0;hits[index]={hit.t,hit.tri,front?1u:0u};if(front)p.emit=d4(m.emit);
        if(!front && !m.two_sided){p.counters[3]=1;continue;}auto n=front?ng:ng*-1.;auto position=oracle.nudge_inside(tri,ray.origin+ray.dir*hit.t);auto origin=position+n*oracle.offset();
        auto f=m.rho;for(auto& channel:f)channel/=N::kPi;
        if(f[0]==0 && f[1]==0 && f[2]==0)continue;
        NoDraw unused;N::RenderCounters counters{};auto e=oracle.direct(origin,n,hit.tri,unused,counters);
        N::Rgb radiance{};for(int channel=0;channel<3;++channel)radiance[channel]=f[channel]*e[channel];
        p.origin=d4(origin,1);p.normal=d4(n,hit.tri);p.rho=d4(m.rho);p.direct=d4(radiance);p.counters[1]=counters.shadow_tests;p.counters[2]=counters.shadow_blocked;
    }
    Context c;c.init();
    auto upload=[&](const void* data,size_t bytes){size_t index=c.buffers.size();auto& buf=c.buffer(std::max<size_t>(bytes,32),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);std::memset(buf.mapped,0,size_t(buf.bytes));if(bytes)std::memcpy(buf.mapped,data,bytes);return index;};
    upload(triangles.data(),triangles.size()*sizeof(GTriangle));upload(nodes.data(),nodes.size()*sizeof(GNode));auto& order=oracle.bvh().n010_order();upload(order.data(),order.size()*sizeof(uint32_t));upload(lights.data(),lights.size()*sizeof(GPoint));upload(N::N010NetRng::net.data(),N::N010NetRng::net.size()*sizeof(uint32_t));upload(primary.data(),primary.size()*sizeof(GPrimary));
    std::vector<GStats> empty(pixels);upload(empty.data(),empty.size()*sizeof(GStats));
    Params params{};params.physical={{oracle.offset(),oracle.n010_edge_inset(),scene.soft_scale,scene.secondary_far_camera?scene.camera.far:N::kInf}};params.sizes[0]=uint32_t(pixels);params.sizes[1]=uint32_t(nodes.size());params.sizes[2]=uint32_t(lights.size());params.sizes[3]=scene.max_bounces;params.seed[0]=uint32_t(seed);params.seed[1]=uint32_t(seed>>32);params.seed[2]=scene.falloff==N::Falloff::N001Soft?1:0;upload(&params,sizeof params);uint32_t fault=0;upload(&fault,sizeof fault);
    std::array<VkDescriptorSetLayoutBinding,9> bindings{};for(uint32_t j=0;j<9;++j)bindings[j]={j,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,1,VK_SHADER_STAGE_COMPUTE_BIT,nullptr};
    VkDescriptorSetLayoutCreateInfo sl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};sl.bindingCount=uint32_t(bindings.size());sl.pBindings=bindings.data();check(vkCreateDescriptorSetLayout(c.device,&sl,nullptr,&c.set_layout));VkPipelineLayoutCreateInfo pl{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};pl.setLayoutCount=1;pl.pSetLayouts=&c.set_layout;check(vkCreatePipelineLayout(c.device,&pl,nullptr,&c.layout));
    VkDescriptorPoolSize poolsize{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,9};VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};dp.maxSets=1;dp.poolSizeCount=1;dp.pPoolSizes=&poolsize;check(vkCreateDescriptorPool(c.device,&dp,nullptr,&c.descriptors));VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};da.descriptorPool=c.descriptors;da.descriptorSetCount=1;da.pSetLayouts=&c.set_layout;check(vkAllocateDescriptorSets(c.device,&da,&c.set));
    std::array<VkDescriptorBufferInfo,9> bufferinfos{};std::array<VkWriteDescriptorSet,9> writes{};
    for(uint32_t j=0;j<9;++j){bufferinfos[j]={c.buffers[j].handle,0,c.buffers[j].bytes};writes[j].sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;writes[j].dstSet=c.set;writes[j].dstBinding=j;writes[j].descriptorCount=1;writes[j].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;writes[j].pBufferInfo=&bufferinfos[j];}vkUpdateDescriptorSets(c.device,9,writes.data(),0,nullptr);
    auto kernel=c.kernel(shader,"main");
    Ledger::instance().phase("reference-acquisition-diagnostic");auto started=std::chrono::steady_clock::now();
    for(uint32_t begin=0;begin<spp;begin+=batch){
        params.interval[0]=begin;params.interval[1]=std::min(spp,begin+batch);std::memcpy(c.buffers[7].mapped,&params,sizeof params);
        check(vkResetCommandBuffer(c.command,0));VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};check(vkBeginCommandBuffer(c.command,&bi));
        VkMemoryBarrier barrier{VK_STRUCTURE_TYPE_MEMORY_BARRIER};barrier.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT|VK_ACCESS_SHADER_WRITE_BIT;barrier.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;
        vkCmdPipelineBarrier(c.command,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&barrier,0,nullptr,0,nullptr);
        vkCmdBindPipeline(c.command,VK_PIPELINE_BIND_POINT_COMPUTE,kernel.pipeline);vkCmdBindDescriptorSets(c.command,VK_PIPELINE_BIND_POINT_COMPUTE,c.layout,0,1,&c.set,0,nullptr);vkCmdDispatch(c.command,uint32_t((pixels+63)/64),1,1);
        barrier.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;barrier.dstAccessMask=VK_ACCESS_HOST_READ_BIT;vkCmdPipelineBarrier(c.command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&barrier,0,nullptr,0,nullptr);check(vkEndCommandBuffer(c.command));VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&c.command;check(vkQueueSubmit(c.queue,1,&si,VK_NULL_HANDLE));check(vkQueueWaitIdle(c.queue));
    }
    auto values=static_cast<const GStats*>(c.buffers[6].mapped);auto flags=*static_cast<const uint32_t*>(c.buffers[8].mapped);
    sidecar(out/"o.f64",scene,seed,spp,values);static const char* names[]={"emission","direct","indirect","total"};
    bool finite=true;uint64_t counters[4]{};
    for(int k=0;k<4;++k){std::vector<float> rgb(pixels*3);for(size_t p=0;p<pixels;++p)for(int channel=0;channel<3;++channel){double mean=values[p].sum[k].v[channel]/spp;finite=finite && std::isfinite(mean) && std::isfinite(values[p].sum2[k].v[channel]);rgb[p*3+channel]=float(mean);}N::write_pfm((out/(std::string("o.")+names[k]+".pfm")).string(),scene.width,scene.height,rgb);}
    for(size_t p=0;p<pixels;++p)for(int k=0;k<4;++k)counters[k]+=values[p].counters[k];
    std::ofstream raw(out/"o.hits",std::ios::binary);raw.write("N008HIT\0",8);uint32_t shape[2]={scene.width,scene.height};raw.write(reinterpret_cast<const char*>(shape),8);for(auto hit:hits){raw.write(reinterpret_cast<const char*>(&hit.t),8);raw.write(reinterpret_cast<const char*>(&hit.tri),4);raw.write(reinterpret_cast<const char*>(&hit.front),4);}if(!raw)throw std::runtime_error("hit file write failed");
    double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    std::ofstream meta(out/"gpu.json");meta<<std::setprecision(17)<<"{\"schema\":\"n010-gpu-reference-diagnostic/1\",\"device\":\""<<c.properties.deviceName<<"\",\"spp\":"<<spp<<",\"seed\":"<<seed<<",\"width\":"<<scene.width<<",\"height\":"<<scene.height<<",\"vertices\":"<<scene.max_bounces<<",\"geometry_sha256\":\""<<N::geometry_sha256(scene)<<"\",\"fault_flags\":"<<flags<<",\"all_finite\":"<<(finite?"true":"false")<<",\"primary_hits\":"<<counters[0]<<",\"shadow_tests\":"<<counters[1]<<",\"shadow_blocked\":"<<counters[2]<<",\"backface_absorbed\":"<<counters[3]<<",\"gpu_acquisition_wall_seconds_diagnostic\":"<<elapsed<<",\"eligible_for_references\":false}\n";
    if(flags || !finite)throw std::runtime_error("GPU oracle fault/nonfinite output; retained without eligibility");
}
int main(int argc,char** argv) {
    if(argc!=8){std::cerr<<"usage: SCENE NET SHADER SEED SPP BATCH NEW_OUTPUT\n";return 1;}
    fs::path out=argv[7];if(fs::exists(out)){std::cerr<<"refuse existing output\n";return 1;}fs::create_directories(out);
    try {uint64_t seed=std::stoull(argv[4]);uint32_t spp=uint32_t(std::stoul(argv[5])),batch=uint32_t(std::stoul(argv[6]));if(!spp || spp>262144 || !batch || batch>1024)throw std::runtime_error("invalid sample/batch range");std::ifstream file(argv[1]);if(!file)throw std::runtime_error("missing scene");auto scene=N::parse_scene(file);Ledger::instance().phase("startup");execute(scene,argv[2],argv[3],seed,spp,batch,out);Ledger::instance().save(out/"allocation-ledger.json");return 0;}
    catch(const std::exception& e){Ledger::instance().save(out/"allocation-ledger.json");std::ofstream(out/"failure.txt")<<e.what()<<'\n';std::cerr<<e.what()<<'\n';return 2;}
}

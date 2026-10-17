// Plan112 isolated host template. Builder inserts pinned352 physical sections.
// Not linked into Renderer; no reference admission from successful execution.
// @N010_COMMON@
#include <cstddef>
#include <iterator>
#include <numeric>
static constexpr char backendId[]="@N010_BACKEND_ID@";
struct alignas(32) GPart {D4 contribution;uint64_t counts[4]{},proposal[4]{};D4 maxima;};
struct AuditState {uint64_t counts[4]{};double maxima[4]{};};
static_assert(sizeof(GPart)==128 && sizeof(AuditState)==64 && offsetof(Params,control)==80);

static std::string file_sha(const fs::path& path) {
    std::ifstream in(path,std::ios::binary);if(!in)throw std::runtime_error("missing hash input");
    N::Sha256 hash;std::array<char,65536> bytes;
    while(in){in.read(bytes.data(),bytes.size());if(in.gcount())hash.update(bytes.data(),size_t(in.gcount()));}
    if(!in.eof())throw std::runtime_error("hash input read failed");return hash.hex();
}
static void write_bytes(const fs::path& path,const void* data,size_t bytes) {
    std::ofstream out(path,std::ios::binary);if(bytes)out.write(static_cast<const char*>(data),bytes);
    if(!out)throw std::runtime_error("binary evidence write failed: "+path.string());
}
static void read_bytes(const fs::path& path,void* data,size_t bytes) {
    std::ifstream in(path,std::ios::binary);if(bytes)in.read(static_cast<char*>(data),bytes);
    if(!in || in.peek()!=std::char_traits<char>::eof())throw std::runtime_error("prefix binary length/read differs");
}
static std::vector<uint32_t> select_pixels(const N::Scene& scene,const std::string& mode) {
    if(mode=="diagnostic8") {
        if(scene.width!=320 || scene.height!=180 || scene.max_bounces!=8)
            throw std::runtime_error("diagnostic8 requires original C1 shape/depth");
        return {9640,9720,9800,9880,48040,48120,48200,48280};
    }
    if(mode!="full")throw std::runtime_error("unknown selection mode");
    std::vector<uint32_t> out(size_t(scene.width)*scene.height);std::iota(out.begin(),out.end(),0u);return out;
}
static AuditState audit_merge(AuditState a,const AuditState& b) {
    for(int k=0;k<4;++k){a.counts[k]+=b.counts[k];a.maxima[k]=std::max(a.maxima[k],b.maxima[k]);}return a;
}
static AuditState cpu_audit(const N::Oracle& oracle) {
    const auto& a=oracle.renderer_audit_;AuditState out;
    out.counts[0]=a.bvh_queries;out.counts[1]=a.component_attempts;
    out.counts[2]=a.component_nulls;out.counts[3]=a.own_checks;
    out.maxima[0]=a.max_own_log_error;out.maxima[1]=a.max_target_error_fraction;
    out.maxima[2]=a.max_unconditioned_target_error_fraction;out.maxima[3]=a.max_weight;return out;
}
static std::string stamp(const std::string& sceneSha,const std::string& netSha,uint64_t seed,
                         const N::Scene& scene,uint32_t spp,const std::string& mode,uint32_t batch,uint32_t tile) {
    std::ostringstream s;s<<"N010-TILED-PREFIX-1\n"<<backendId<<'\n'<<sceneSha<<'\n'<<netSha<<'\n'
        <<seed<<' '<<scene.width<<' '<<scene.height<<' '<<spp<<' '<<mode<<' '<<batch<<' '<<tile<<'\n';return s.str();
}
static void execute(const N::Scene& scene,const fs::path& scenePath,const fs::path& net,const fs::path& shader,
                    uint64_t seed,uint32_t spp,uint32_t batch,uint32_t tileCapacity,const std::string& mode,
                    uint32_t beginSpp,const fs::path& prefix,const fs::path& out) {
// @N010_PHYSICAL@
    std::array<std::array<double,2>,1> trig{};
    std::vector<GStats> corrected(pixels);
    std::vector<uint32_t> completed(pixels);
    std::vector<N::Oracle::PrimaryCache> cpuCaches(pixels);
    AuditState prefixAudit,gpuAudit;
    const auto sceneSha=file_sha(scenePath),netSha=file_sha(net);
    if(beginSpp) {
        std::ifstream in(prefix/"prefix.stamp",std::ios::binary);
        const std::string got((std::istreambuf_iterator<char>(in)),{});
        if(got!=stamp(sceneSha,netSha,seed,scene,beginSpp,mode,batch,tileCapacity))
            throw std::runtime_error("prefix source/scene/net/seed/shape/count/mode/layout differs");
        read_bytes(prefix/"gpu.stats",corrected.data(),corrected.size()*sizeof(GStats));
        read_bytes(prefix/"audit.bin",&prefixAudit,sizeof prefixAudit);
        for(const auto& value:corrected)for(int k=0;k<4;++k)for(int c=0;c<4;++c)
            for(double v:{value.sum[k].v[c],value.sum2[k].v[c]})
                if(!std::isfinite(v)||v<0||(v!=0&&std::fpclassify(v)==FP_SUBNORMAL))
                    throw std::runtime_error("invalid/subnormal prefix sums");
        for(double v:prefixAudit.maxima)if(!std::isfinite(v)||v<0)throw std::runtime_error("invalid prefix audit");
        for(auto pixel:selected)completed[pixel]=beginSpp;
    }
    std::vector<GPrimary> selectedPrimary;for(auto pixel:selected)selectedPrimary.push_back(primary[pixel]);
    write_bytes(out/"primary-records.bin",selectedPrimary.data(),selectedPrimary.size()*sizeof(GPrimary));
    std::ofstream hitsFile(out/"o.hits",std::ios::binary);hitsFile.write("N008HIT\0",8);
    uint32_t shape[]={scene.width,scene.height};hitsFile.write(reinterpret_cast<const char*>(shape),8);
    for(auto hit:hits){hitsFile.write(reinterpret_cast<const char*>(&hit.t),8);hitsFile.write(reinterpret_cast<const char*>(&hit.tri),4);hitsFile.write(reinterpret_cast<const char*>(&hit.front),4);}
    hitsFile.close();if(!hitsFile)throw std::runtime_error("primary hit write failed");
    std::ofstream scope(out/"scope.json");scope<<"{\"schema\":\"n010-tiled-whole-scope/1\",\"mode\":\""<<mode
        <<"\",\"selected_pixels\":[";for(size_t i=0;i<selected.size();++i){if(i)scope<<',';scope<<selected[i];}
    scope<<"],\"spp\":"<<spp<<",\"begin_spp\":"<<beginSpp<<",\"seed\":"<<seed
        <<",\"batch\":"<<batch<<",\"tile_capacity\":"<<tileCapacity<<",\"raw_path_record_bytes\":160,\"part_record_bytes\":128,\"primary_record_bytes\":192,\"reference_admission\":false}\n";
    scope.close();if(!scope)throw std::runtime_error("scope write failed");
    Context c;c.init();
    auto upload=[&](const void* data,size_t bytes){auto& b=c.buffer(std::max<size_t>(bytes,32),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        std::memset(b.mapped,0,size_t(b.bytes));if(data&&bytes)std::memcpy(b.mapped,data,bytes);};
    upload(triangles.data(),triangles.size()*sizeof(GTriangle));upload(nodes.data(),nodes.size()*sizeof(GNode));
    const auto& order=oracle.bvh().n010_order();upload(order.data(),order.size()*sizeof(uint32_t));
    upload(lights.data(),lights.size()*sizeof(GPoint));upload(N::N010NetRng::net.data(),N::N010NetRng::net.size()*4);
    upload(primary.data(),primary.size()*sizeof(GPrimary));upload(nullptr,32); // unused retained stats binding
    Params params{};params.physical={{oracle.offset(),oracle.n010_edge_inset(),scene.soft_scale,
        scene.secondary_far_camera?scene.camera.far:N::kInf}};
    params.sizes[0]=uint32_t(pixels);params.sizes[1]=uint32_t(nodes.size());params.sizes[2]=uint32_t(lights.size());params.sizes[3]=scene.max_bounces;
    params.seed[0]=uint32_t(seed);params.seed[1]=uint32_t(seed>>32);params.seed[2]=scene.falloff==N::Falloff::N001Soft?1:0;
    params.interval[2]=batch;upload(&params,sizeof params);upload(nullptr,4);
    upload(nullptr,tileCapacity*4);upload(trig.data(),sizeof trig);
    const size_t capacity=size_t(tileCapacity)*batch;
    upload(nullptr,capacity*sizeof(GPart));upload(nullptr,capacity*4);
// @N010_PIPELINE@
    auto kernel=c.kernel(shader,"main");Ledger::instance().phase("tiled-reference-diagnostic");
    const auto started=std::chrono::steady_clock::now();
    std::ofstream dispatches(out/"dispatches.jsonl"),batches(out/"batches.jsonl");
    std::ofstream rawSamples,correctedSamples,routingFlags,partSamples;
    if(mode=="diagnostic8") {
        rawSamples.open(out/"gpu-paths.bin",std::ios::binary);correctedSamples.open(out/"corrected-paths.bin",std::ios::binary);
        routingFlags.open(out/"routing-flags.bin",std::ios::binary);partSamples.open(out/"gpu-parts.bin",std::ios::binary);
        if(!rawSamples||!correctedSamples||!routingFlags||!partSamples)throw std::runtime_error("diagnostic stream open failed");
    }
    if(!dispatches||!batches)throw std::runtime_error("batch log open failed");
    std::vector<GPart> parts(7*capacity);std::vector<uint32_t> flags(capacity),depthFlags(capacity);
    uint64_t fallbackTotal=0,reasonCounts[6]{},totalPaths=0;double maxDispatchWall=0;
    uint32_t activeBegin=beginSpp,activeEnd=beginSpp,activeDepth=0;size_t activeTile=0,activeCount=0;
    auto save_partial=[&]() {
        write_bytes(out/"partial.stats",corrected.data(),corrected.size()*sizeof(GStats));
        write_bytes(out/"partial-counts.bin",completed.data(),completed.size()*4);
        const auto a=audit_merge(prefixAudit,audit_merge(gpuAudit,cpu_audit(oracle)));write_bytes(out/"partial-audit.bin",&a,sizeof a);
        write_bytes(out/"active-parts.bin",parts.data(),parts.size()*sizeof(GPart));
        write_bytes(out/"active-routing.bin",flags.data(),flags.size()*4);
        std::ofstream f(out/"partial.json");f<<"{\"complete\":false,\"begin\":"<<activeBegin<<",\"end\":"<<activeEnd
            <<",\"tile_begin\":"<<activeTile<<",\"tile_count\":"<<activeCount<<",\"last_submitted_depth\":"<<activeDepth
            <<",\"completed_scored_paths\":"<<totalPaths<<",\"reference_admission\":false}\n";
    };
    try {
        for(uint32_t begin=beginSpp;begin<spp;begin+=batch) {
            const uint32_t end=std::min(spp,begin+batch);activeBegin=begin;activeEnd=end;
            for(size_t tileBegin=0;tileBegin<selected.size();tileBegin+=tileCapacity) {
                const size_t count=std::min<size_t>(tileCapacity,selected.size()-tileBegin);
                activeTile=tileBegin;activeCount=count;activeDepth=0;
                std::fill(parts.begin(),parts.end(),GPart{});std::fill(flags.begin(),flags.end(),0u);
                params.interval[0]=begin;params.interval[1]=end;params.interval[3]=uint32_t(count);
                std::memcpy(c.buffers[9].mapped,selected.data()+tileBegin,count*4);
                double batchMaxWall=0;
                for(uint32_t depth=1;depth<scene.max_bounces;++depth) {
                    activeDepth=depth;params.control[0]=depth;std::memcpy(c.buffers[7].mapped,&params,sizeof params);
                    const auto tick=std::chrono::steady_clock::now();
                    check(vkResetCommandBuffer(c.command,0));VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};check(vkBeginCommandBuffer(c.command,&bi));
                    VkMemoryBarrier barrier{VK_STRUCTURE_TYPE_MEMORY_BARRIER};barrier.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT|VK_ACCESS_SHADER_WRITE_BIT;barrier.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;
                    vkCmdPipelineBarrier(c.command,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&barrier,0,nullptr,0,nullptr);
                    vkCmdBindPipeline(c.command,VK_PIPELINE_BIND_POINT_COMPUTE,kernel.pipeline);vkCmdBindDescriptorSets(c.command,VK_PIPELINE_BIND_POINT_COMPUTE,c.layout,0,1,&c.set,0,nullptr);
                    vkCmdDispatch(c.command,uint32_t((count*batch+63)/64),1,1);
                    barrier.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;barrier.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
                    vkCmdPipelineBarrier(c.command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&barrier,0,nullptr,0,nullptr);
                    check(vkEndCommandBuffer(c.command));VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&c.command;
                    check(vkQueueSubmit(c.queue,1,&si,VK_NULL_HANDLE));check(vkQueueWaitIdle(c.queue));
                    const double wall=std::chrono::duration<double>(std::chrono::steady_clock::now()-tick).count();
                    batchMaxWall=std::max(batchMaxWall,wall);maxDispatchWall=std::max(maxDispatchWall,wall);
                    std::memcpy(parts.data()+(depth-1)*capacity,c.buffers[11].mapped,count*batch*sizeof(GPart));
                    std::memcpy(depthFlags.data(),c.buffers[12].mapped,count*batch*4);
                    for(size_t j=0;j<count*batch;++j)flags[j]|=depthFlags[j];
                    dispatches<<std::setprecision(17)<<"{\"begin\":"<<begin<<",\"end\":"<<end<<",\"tile_begin\":"<<tileBegin
                        <<",\"tile_count\":"<<count<<",\"depth\":"<<depth<<",\"submit_wait_wall_seconds_diagnostic\":"<<wall<<"}\n";
                    dispatches.flush();if(!dispatches)throw std::runtime_error("dispatch evidence write failed");
                    if(*static_cast<const uint32_t*>(c.buffers[8].mapped))throw std::runtime_error("GPU_FAULT; retain partial evidence");
                    if(wall>.250)throw std::runtime_error("OPERATIONAL_SUBMIT_WAIT_GUARD; retain partial evidence");
                    // A fixed pause gives the desktop a scheduling opportunity between depths.
                    std::this_thread::sleep_for(std::chrono::milliseconds(2));
                }
                uint64_t tileFallback=0,tileReasons[6]{};
                for(size_t slot=0;slot<count;++slot) {
                    const auto pixel=selected[tileBegin+slot];auto& dst=corrected[pixel];auto& cache=cpuCaches[pixel];
                    for(uint32_t sample=begin;sample<end;++sample) {
                        const size_t index=slot*batch+sample-begin;GPath raw{};AuditState pathAudit;
                        raw.components[0]=primary[pixel].emit;raw.components[1]=primary[pixel].direct;
                        for(int k=0;k<4;++k)raw.counters[k]=primary[pixel].counters[k];
                        for(uint32_t depth=1;depth<scene.max_bounces;++depth) {
                            const auto& part=parts[(depth-1)*capacity+index];
                            for(int ch=0;ch<3;++ch)raw.components[2].v[ch]+=part.contribution.v[ch];
                            raw.counters[1]+=part.counts[0];raw.counters[2]+=part.counts[1];
                            pathAudit.counts[0]+=part.proposal[0];pathAudit.counts[1]+=part.counts[2];
                            pathAudit.counts[2]+=part.counts[3];pathAudit.counts[3]+=part.proposal[1];
                            const double delta=part.maxima.v[0];
                            const double logBound=std::isfinite(delta)&&delta>=0&&delta<1?-std::log1p(-delta):N::kInf;
                            pathAudit.maxima[0]=std::max(pathAudit.maxima[0],logBound);
                            for(int k=1;k<4;++k)pathAudit.maxima[k]=std::max(pathAudit.maxima[k],part.maxima.v[k]);
                            if(mode=="diagnostic8")partSamples.write(reinterpret_cast<const char*>(&part),sizeof part);
                        }
                        for(int ch=0;ch<3;++ch)raw.components[3].v[ch]=(raw.components[0].v[ch]+raw.components[1].v[ch])+raw.components[2].v[ch];
                        GPath value=raw;
                        if(flags[index]) {
                            ++fallbackTotal;++tileFallback;for(int bit=0;bit<6;++bit)if(flags[index]&(1u<<bit)){++reasonCounts[bit];++tileReasons[bit];}
                            N::N010NetRng rng(seed,pixel,sample);N::Rgb comp[N::kComponents]{};N::RenderCounters cnt{};
                            oracle.sample_all_split(uint32_t(pixel%scene.width),uint32_t(pixel/scene.width),rng,comp,cnt,nullptr,&cache);
                            for(int k=0;k<3;++k)value.components[k]=d4(comp[k]);
                            for(int ch=0;ch<3;++ch)value.components[3].v[ch]=(comp[0][ch]+comp[1][ch])+comp[2][ch];
                            value.counters[0]=cnt.primary_hits;value.counters[1]=cnt.shadow_tests;value.counters[2]=cnt.shadow_blocked;value.counters[3]=cnt.backface_absorbed;
                        } else gpuAudit=audit_merge(gpuAudit,pathAudit);
                        if(mode=="diagnostic8") {
                            rawSamples.write(reinterpret_cast<const char*>(&raw),sizeof raw);correctedSamples.write(reinterpret_cast<const char*>(&value),sizeof value);
                            routingFlags.write(reinterpret_cast<const char*>(&flags[index]),4);
                        }
                        for(int k=0;k<4;++k)for(int ch=0;ch<3;++ch){double x=value.components[k].v[ch];
                            if(!std::isfinite(x)||x<0)throw std::runtime_error("invalid corrected contribution");
                            dst.sum[k].v[ch]+=x;dst.sum2[k].v[ch]+=x*x;
                        }
                        for(int k=0;k<4;++k)dst.counters[k]+=value.counters[k];
                        ++completed[pixel];++totalPaths;
                    }
                }
                batches<<std::setprecision(17)<<"{\"begin\":"<<begin<<",\"end\":"<<end<<",\"tile_begin\":"<<tileBegin
                    <<",\"selected_count\":"<<count<<",\"complete\":true,\"cpu_fallback_paths\":"<<tileFallback<<",\"reason_counts\":[";
                for(int k=0;k<6;++k){if(k)batches<<',';batches<<tileReasons[k];}
                batches<<"],\"max_depth_submit_wait_wall_seconds_diagnostic\":"<<batchMaxWall<<"}\n";batches.flush();
                if(mode=="diagnostic8") {rawSamples.flush();correctedSamples.flush();routingFlags.flush();partSamples.flush();
                    if(!rawSamples||!correctedSamples||!routingFlags||!partSamples)throw std::runtime_error("diagnostic stream write failed");}
                if(!batches)throw std::runtime_error("batch evidence write failed");
            }
        }
    } catch(...) {save_partial();throw;}
    const auto audit=audit_merge(prefixAudit,audit_merge(gpuAudit,cpu_audit(oracle)));
    for(auto pixel:selected)if(completed[pixel]!=spp)throw std::runtime_error("incomplete scored pixel");
    for(const auto& value:corrected)for(int k=0;k<4;++k)for(int ch=0;ch<4;++ch)
        if(!std::isfinite(value.sum[k].v[ch])||!std::isfinite(value.sum2[k].v[ch]))throw std::runtime_error("invalid accumulated moment");
    write_bytes(out/"gpu.stats",corrected.data(),corrected.size()*sizeof(GStats));write_bytes(out/"audit.bin",&audit,sizeof audit);
    write_bytes(out/"sample-counts.bin",completed.data(),completed.size()*4);
    sidecar(out/"o.f64",scene,seed,spp,corrected.data());static const char* names[]={"emission","direct","indirect","total"};
    for(int k=0;k<4;++k){std::vector<float> rgb(pixels*3);for(size_t p=0;p<pixels;++p)for(int ch=0;ch<3;++ch){rgb[p*3+ch]=float(corrected[p].sum[k].v[ch]/spp);
            if(!std::isfinite(rgb[p*3+ch]))throw std::runtime_error("invalid PFM mean");}
        N::write_pfm((out/(std::string("o.")+names[k]+".pfm")).string(),scene.width,scene.height,rgb);}
    const uint32_t faults=*static_cast<const uint32_t*>(c.buffers[8].mapped);if(faults)throw std::runtime_error("GPU fault flags; no completed prefix");
    uint64_t counters[4]{};for(const auto& value:corrected)for(int k=0;k<4;++k)counters[k]+=value.counters[k];
    std::ofstream meta(out/"gpu.json");meta<<std::setprecision(17)<<"{\"schema\":\"n010-tiled-depth-split-whole-hybrid/1\",\"backend_id\":\""<<backendId
        <<"\",\"scene_sha256\":\""<<sceneSha<<"\",\"net_sha256\":\""<<netSha<<"\",\"geometry_sha256\":\""<<N::geometry_sha256(scene)
        <<"\",\"device\":\""<<c.properties.deviceName<<"\",\"mode\":\""<<mode<<"\",\"width\":"<<scene.width<<",\"height\":"<<scene.height
        <<",\"vertices\":"<<scene.max_bounces<<",\"seed\":"<<seed<<",\"spp\":"<<spp<<",\"begin_spp\":"<<beginSpp<<",\"batch\":"<<batch
        <<",\"tile_capacity\":"<<tileCapacity<<",\"selected_count\":"<<selected.size()<<",\"new_scored_paths\":"<<totalPaths
        <<",\"cpu_fallback_paths_new_interval\":"<<fallbackTotal<<",\"routing_reason_counts\":[";
    for(int k=0;k<6;++k){if(k)meta<<',';meta<<reasonCounts[k];}
    meta<<"],\"primary_hits\":"<<counters[0]<<",\"shadow_tests\":"<<counters[1]<<",\"shadow_blocked\":"<<counters[2]
        <<",\"backface_absorbed\":"<<counters[3]<<",\"max_depth_submit_wait_wall_seconds_diagnostic\":"<<maxDispatchWall
        <<",\"acquisition_wall_seconds_diagnostic\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()
        <<",\"auxiliary_primary_primes_new_interval\":"<<oracle.primary_prime_samples_
        <<",\"all_split\":{\"proposal_bvh_queries\":"<<audit.counts[0]<<",\"component_attempts\":"<<audit.counts[1]
        <<",\"component_nulls\":"<<audit.counts[2]<<",\"own_checks\":"<<audit.counts[3]
        <<",\"max_own_log_error_bound\":"<<audit.maxima[0]<<",\"max_conditioned_error_fraction\":"<<audit.maxima[1]
        <<",\"max_unconditioned_error_fraction\":"<<audit.maxima[2]<<",\"max_weight\":"<<audit.maxima[3]
        <<"},\"fault_flags\":0,\"all_finite\":true,\"reference_admission\":false,\"accepted_timing\":false}\n";
    meta.close();if(!meta)throw std::runtime_error("metadata write failed");
    const auto proof=stamp(sceneSha,netSha,seed,scene,spp,mode,batch,tileCapacity);
    write_bytes(out/"prefix.stamp",proof.data(),proof.size());
}
int main(int argc,char** argv) {
    if(argc!=13){std::cerr<<"usage: SCENE NET SHADER SEED SPP BATCH TILE MODE BEGIN PREFIX NEW_OUT WORKERS\n";return 1;}
    const fs::path out=argv[11];if(fs::exists(out)){std::cerr<<"refuse existing output\n";return 1;}fs::create_directories(out);
    try {
        const auto seed=std::stoull(argv[4]);const uint32_t spp=uint32_t(std::stoul(argv[5])),batch=uint32_t(std::stoul(argv[6])),
            tile=uint32_t(std::stoul(argv[7])),begin=uint32_t(std::stoul(argv[9]));
        const std::string mode=argv[8];const fs::path prefix=argv[10];
        if(!spp||spp>262144||(spp&(spp-1))||!batch||batch>16||!tile||tile>512||std::string(argv[12])!="1"||
           (begin&&(spp!=2*begin||(begin&(begin-1))||prefix=="-"))||(!begin&&prefix!="-"))
            throw std::runtime_error("invalid count/layout/one-worker/dyadic-prefix request");
        std::ifstream in(argv[1]);if(!in)throw std::runtime_error("missing scene");const auto scene=N::parse_scene(in);
        Ledger::instance().phase("startup");execute(scene,argv[1],argv[2],argv[3],seed,spp,batch,tile,mode,begin,prefix,out);
        Ledger::instance().save(out/"allocation-ledger.json");return 0;
    } catch(const std::exception& e) {
        Ledger::instance().save(out/"allocation-ledger.json");std::ofstream(out/"failure.txt")<<e.what()<<'\n';std::cerr<<e.what()<<'\n';return 2;
    }
}

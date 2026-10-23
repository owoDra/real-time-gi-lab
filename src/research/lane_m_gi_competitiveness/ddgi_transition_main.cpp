// Isolated persistent-resource dynamic reset adapter. Original static core is unchanged.
#define main m001_retained_static_main
#include "ddgi_scene_main.cpp"
#undef main
#include "ddgi_transition_contract.hpp"

static void run_transition(const Options& initial,const m001::State& source,const m001::State& target) {
    Options o=initial;auto state=source;auto grid=m001::grid(state,o.side,o.rays);
    const auto schedule=m001_dynamic::plan(source,target);
    const std::array<const m001::State*,2> states{&source,&target};
    const fs::path root=initial.out;
    std::ofstream sequence(root/"sequence.jsonl");
    auto initial_clock=Clock::now();
    auto setup_start=Clock::now();b::B002VulkanContext base(false,b::kB002TargetDeviceName,true);
    std::vector<b::Triangle> triangles;
    for(const auto& t:state.triangles)triangles.push_back({{t.v0[0],t.v0[1],t.v0[2]},{t.v1[0],t.v1[1],t.v1[2]},
        {t.v2[0],t.v2[1],t.v2[2]},t.primitive,t.material,t.instance,true});
    b::B002HwrtTraversal hwrt(base,triangles,"",false);Context c(base,o.out/"frames/0");layouts(c);
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
        atlas[j].gather_set=adapter_descriptor(c,atlas[j],atlas[j],hwrt,frame,pixels);}
    m001::require(std::memcmp(atlas[0].constants.mapped,atlas[1].constants.mapped,128)==0,"ping-pong packed descriptors/rotation differ");
    VkDeviceSize max_bytes=0;for(auto image:atlas[0].images)max_bytes=std::max(max_bytes,VkDeviceSize(image.w)*image.h*image.layers*image.channels*4);
    auto& staging=c.buffer(max_bytes,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    double initial_setup_wall=std::chrono::duration<double,std::micro>(Clock::now()-setup_start).count();
    auto previous=source;
    for(auto step:schedule){
        auto frame_start=Clock::now();state=*states[step.state_index];grid=m001::grid(state,o.side,o.rays);
        o.out=root/"frames"/std::to_string(step.ordinal);c.out=o.out;
        if(step.ordinal){c.journal.close();c.journal.open(o.out/"dispatches.jsonl");}
        Ledger::instance().phase("frame-"+std::to_string(step.ordinal)+"-update");
        auto changed=m001_dynamic::moved(previous,state);b::HwrtUpdateStats updates{};
        if(!changed.empty()){
            triangles.clear();for(const auto& t:state.triangles)triangles.push_back({{t.v0[0],t.v0[1],t.v0[2]},{t.v1[0],t.v1[1],t.v1[2]},
                {t.v2[0],t.v2[1],t.v2[2]},t.primitive,t.material,t.instance,true});
            updates=hwrt.update_geometry(triangles,changed);
        }
        m001::require(changed.size()==step.moved_primitives,"native changed geometry differs from schedule");
        std::memcpy(frame.mapped,&state.frame,sizeof state.frame);
        desc.origin={grid.origin[0],grid.origin[1],grid.origin[2]};desc.probeSpacing={grid.spacing[0],grid.spacing[1],grid.spacing[2]};
        desc.probeMaxRayDistance=state.frame.camera_forward_far[3];
        desc.probeNormalBias=desc.probeViewBias=.01f*std::min({grid.spacing[0],grid.spacing[1],grid.spacing[2]});
        for(int j=0;j<2;++j){auto& volume=volumes[j];volume.SetOrigin(desc.origin);volume.SetProbeSpacing(desc.probeSpacing);
            volume.SetProbeMaxRayDistance(desc.probeMaxRayDistance);volume.SetProbeNormalBias(desc.probeNormalBias);volume.SetProbeViewBias(desc.probeViewBias);
            auto packed=volume.GetDescGPUPacked();std::memcpy(atlas[j].constants.mapped,&packed,sizeof packed);
            binary(o.out/("constants-"+std::to_string(j)+".bin"),atlas[j].constants.mapped,sizeof packed);}
        m001::require(std::memcmp(atlas[0].constants.mapped,atlas[1].constants.mapped,128)==0,"updated descriptor pairs differ");
        double update_wall=std::chrono::duration<double,std::micro>(Clock::now()-frame_start).count();
    std::ofstream metadata(o.out/"configuration.json");metadata<<std::setprecision(17)<<"{\"schema\":\"m001-ddgi-native/1\",\"mode\":\""<<o.mode<<"\",\"grid_side\":"<<o.side<<",\"rays\":"<<o.rays<<",\"vertices\":"<<o.vertices
        <<",\"seed\":305419896,\"rotation_updates_per_volume\":1,\"hysteresis\":0,\"gamma\":1,\"normal_view_bias\":"<<desc.probeNormalBias<<",\"brightness_threshold\":1000000,\"distance_exponent\":50,\"ray_max\":"<<desc.probeMaxRayDistance
        <<",\"origin\":["<<grid.origin[0]<<','<<grid.origin[1]<<','<<grid.origin[2]<<"],\"spacing\":["<<grid.spacing[0]<<','<<grid.spacing[1]<<','<<grid.spacing[2]<<"],\"subgroup\":"<<c.subgroup<<",\"timestamp_valid_bits\":"<<c.valid_bits
        <<",\"timestamp_period_ns\":"<<c.properties.limits.timestampPeriod<<",\"device\":\""<<base.device_name()<<"\",\"driver_name\":\""<<base.driver_name()<<"\",\"driver_info\":\""<<base.driver_info()<<"\",\"api_version\":"<<base.api_version()
        <<",\"timing_classification\":\"DIAGNOSTIC_UNCALIBRATED\",\"setup_wall_us\":"<<(step.ordinal==0?initial_setup_wall:0.)<<",\"images\":[";
    for(int j=0;j<6;++j){auto i=atlas[0].images[j];metadata<<(j?",":"")<<"{\"type\":"<<j<<",\"w\":"<<i.w<<",\"h\":"<<i.h<<",\"layers\":"<<i.layers<<",\"channels\":"<<i.channels<<'}';}
    metadata<<"]}\n";metadata.close();m001::require(bool(metadata),"configuration write");
    c.dispatch("fresh-zero-initialize",[&]{for(auto& a:atlas)for(auto image:a.images)c.clear(image,step.ordinal==0);
        c.memory_barrier(VK_ACCESS_HOST_WRITE_BIT,VK_ACCESS_SHADER_READ_BIT,VK_PIPELINE_STAGE_HOST_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT);});
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
        sequence<<std::setprecision(17)<<"{\"frame\":"<<step.ordinal<<",\"state_index\":"<<step.state_index<<",\"reset_both_atlases\":true,\"moved_primitives\":"<<updates.moved_primitives
            <<",\"geometry_upload_gpu_us_diagnostic\":"<<updates.geometry_upload_gpu_us<<",\"geometry_upload_wall_us\":"<<updates.geometry_upload_us
            <<",\"blas_update_wall_us\":"<<updates.blas_update_us<<",\"tlas_update_wall_us\":"<<updates.tlas_update_us
            <<",\"frame_setup_update_wall_us\":"<<update_wall<<",\"frame_complete_wall_us\":"<<std::chrono::duration<double,std::micro>(Clock::now()-frame_start).count()<<"}\n";sequence.flush();
        previous=state;
    }
    std::ofstream(root/"sequence-duration.json")<<std::setprecision(17)<<"{\"whole_sequence_setup_and_frames_wall_us_diagnostic\":"<<std::chrono::duration<double,std::micro>(Clock::now()-initial_clock).count()<<",\"accepted_timing\":false}\n";
    for(auto& volume:volumes)volume.Destroy();
}

int main(int argc,char** argv) {
    fs::path out;
    try {
        std::vector<char*> ordinary{argv[0]};fs::path target_path;std::string policy;bool saw_target=false,saw_policy=false;
        for(int k=1;k<argc;++k){std::string arg=argv[k];
            if(arg=="--target-state" || arg=="--history-policy"){
                m001::require(k+1<argc,"missing transition option value");std::string value=argv[++k];
                if(arg=="--target-state"){m001::require(!saw_target,"duplicate target state");saw_target=true;target_path=value;}
                else{m001::require(!saw_policy,"duplicate history policy");saw_policy=true;policy=value;}
            }else ordinary.push_back(argv[k]);
        }
        if(!saw_target){m001::require(!saw_policy,"history policy without target");return m001_retained_static_main(int(ordinary.size()),ordinary.data());}
        m001::require(!target_path.empty() && saw_policy && policy=="reset-all","explicit reset-all policy required");
        auto o=options(int(ordinary.size()),ordinary.data());
        m001::require(o.mode=="scene" && (o.vertices==2 || o.vertices==8),"transition supports scene B2/B8 only");
        auto source=m001::load_state(o.state),target=m001::load_state(target_path);
        auto schedule=m001_dynamic::plan(source,target);
        (void)m001::grid(source,o.side,o.rays);(void)m001::grid(target,o.side,o.rays);
        m001::create_output(o.out);out=o.out;
        std::ofstream contract(out/"transition-contract.json");contract<<"{\"schema\":\"m001-ddgi-reset-schedule/1\",\"history_policy\":\"reset-all\",\"cpu_checked\":true,\"frames\":[";
        for(auto step:schedule){auto frame=out/"frames"/std::to_string(step.ordinal);fs::create_directories(frame);
            for(auto name:{"geometry-state.bin","frame-state.bin"})fs::copy_file((step.state_index?target_path:o.state)/name,frame/name);
            contract<<(step.ordinal?",":"")<<"{\"index\":"<<step.ordinal<<",\"state_index\":"<<step.state_index<<",\"moved_primitives\":"<<step.moved_primitives<<",\"reset_both_atlases\":true,\"finite_stages\":"<<o.vertices-1<<'}';}
        contract<<"]}\n";contract.close();m001::require(bool(contract),"transition contract write");
        if(o.cpu){std::cout<<"CPU transition contract PASS; Vulkan NOT initialized\n";return 0;}
        auto started=Clock::now();Ledger::instance().phase("startup");run_transition(o,source,target);
        Ledger::instance().save(out/"allocation-ledger.json");
        std::ofstream(out/"complete.json")<<std::setprecision(17)<<"{\"capture_complete\":true,\"history_policy\":\"reset-all\",\"frames\":4,\"whole_pipeline_lifetime_wall_us_diagnostic\":"
            <<std::chrono::duration<double,std::micro>(Clock::now()-started).count()<<",\"semantic_admission\":false,\"quality_admission\":false,\"speed_admission\":false}\n";
        std::cout<<"dynamic capture complete; independent admission required\n";return 0;
    }catch(const std::exception& error){if(!out.empty()){Ledger::instance().save(out/"allocation-ledger.json");std::ofstream(out/"failure.txt")<<error.what()<<'\n';}
        std::cerr<<error.what()<<'\n';return 2;}
}

// 015 bounded observed-data CPU pilot, not an oracle or GPU benchmark.
#include "guided_transport.hpp"
#include <filesystem>
#include <iomanip>
#include <iostream>
namespace fs=std::filesystem;
namespace g=phos::gi::research::m001guide;
namespace o=phos::gi::research::n008;
template<class T>void save(const fs::path& p,const T* ptr,std::size_t n) {
    std::ofstream f(p,std::ios::binary);if(!f)throw std::runtime_error("pilot output open failed");
    f.write(reinterpret_cast<const char*>(ptr),std::streamsize(n*sizeof(T)));
    if(!f)throw std::runtime_error("pilot output write failed");
}
int main(int argc,char** argv) {
 try {
    g::require(argc==5&&std::string(argv[1])=="--scene"&&std::string(argv[3])=="--out","015 requires --scene FILE --out NEW_DIR");
    const fs::path scene_path=argv[2],out=argv[4];
    g::require(!fs::exists(out),"015 output exists; no overwrite");
    std::ifstream input(scene_path);g::require(bool(input),"015 scene unavailable");const auto scene=o::parse_scene(input);
    g::Transport transport(scene);g::require(fs::create_directory(out),"015 output creation failed");
    std::vector<o::PrimaryRecord> primary(320*180);std::vector<unsigned> hits;g::Counts scan;
    for(unsigned id=0;id<primary.size();++id) {
        g::Surface surface;
        if(transport.trace(transport.oracle.primary_ray(id%320,id/320,.5,.5),scene.camera.near,
                           scene.camera.far,~0u,surface,scan,&primary[id]))hits.push_back(id);
    }
    g::require(hits.size()>=16,"015 fewer than16primary hits");
    std::array<unsigned,16> selected{};
    for(unsigned k=0;k<16;++k)selected[k]=hits[((2*k+1)*hits.size())/32];
    save(out/"all-primary.bin",primary.data(),primary.size());save(out/"selected-pixels.u32",selected.data(),selected.size());
    g::Field field(scene);field.train(transport);
    save(out/"training-weights.f64",field.weights.data(),field.weights.size());
    save(out/"guide-cdf.u32",field.cdf.data(),field.cdf.size());
    constexpr std::array<std::uint64_t,4> seeds{305419896ULL,2596069104ULL,81985529216486895ULL,18364758544493064720ULL};
    std::ofstream report(out/"capture.json");report<<std::setprecision(17);
    report<<"{\"schema\":\"m001-all-bounce-guide-cpu-native/1\",\"primary_scan_queries\":"<<scan.closest
          <<",\"primary_hit_pixels\":"<<hits.size()<<",\"training_paths\":65536,\"training_closest_queries\":"<<field.training.closest
          <<",\"training_shadow_queries\":"<<field.training.shadow<<",\"grid\":8,\"bins\":64,\"spp\":1024,\"seeds\":[";
    for(unsigned i=0;i<4;++i)report<<(i?",":"")<<seeds[i];
    report<<"],\"guide_lo\":["<<field.lo.x<<','<<field.lo.y<<','<<field.lo.z<<"],\"guide_extent\":["<<field.extent.x<<','<<field.extent.y<<','<<field.extent.z<<"],\"rows\":[";
    bool comma=false;
    for(unsigned depth:{2u,8u})for(bool guided:{false,true}) {
        g::Counts counts;std::vector<double> samples,direct;
        samples.reserve(4*16*1024);direct.reserve(4*16);
        for(auto seed:seeds)for(unsigned id:selected) {
            g::Surface first;o::PrimaryRecord record;
            g::require(transport.trace(transport.oracle.primary_ray(id%320,id/320,.5,.5),scene.camera.near,
                       scene.camera.far,~0u,first,counts,&record),"015 selected primary disappeared");
            g::require(record.tri==primary[id].tri&&record.t==primary[id].t,"015 primary replay differs");
            o::Xoshiro256 drng(seed,id,~0ULL);direct.push_back(transport.direct(first,drng,counts));
            for(unsigned sample=0;sample<1024;++sample) {
                o::Xoshiro256 rng(seed,id,sample);
                samples.push_back(g::render_indirect(transport,field,first,depth,guided,rng,counts));
            }
        }
        const auto name="b"+std::to_string(depth)+(guided?"-guided":"-cosine");
        save(out/(name+".samples.f64"),samples.data(),samples.size());save(out/(name+".direct.f64"),direct.data(),direct.size());
        report<<(comma?",":"")<<"{\"depth\":"<<depth<<",\"guided\":"<<(guided?"true":"false")
              <<",\"sample_file\":\""<<name<<".samples.f64\",\"direct_file\":\""<<name<<".direct.f64\",\"closest_queries\":"<<counts.closest
              <<",\"shadow_queries\":"<<counts.shadow<<",\"null_samples\":"<<counts.nulls<<"}";comma=true;
        std::cout<<name<<" CPU samples retained\n"<<std::flush;
    }
    report<<"],\"gpu_executed\":false,\"candidate_is_independent_reference\":false}\n";
    g::require(bool(report),"015 native report write failed");return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}

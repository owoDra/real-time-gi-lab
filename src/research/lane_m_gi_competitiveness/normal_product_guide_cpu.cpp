// 016 CPU candidate-only acquisition; no training/control resampling or GPU.
#include "normal_product_guide.hpp"
#include <filesystem>
#include <iomanip>
#include <iostream>
namespace fs=std::filesystem;
namespace p=phos::gi::research::m001product;
namespace g=phos::gi::research::m001guide;
namespace o=phos::gi::research::n008;
template<class T>void save(const fs::path& path,const T* ptr,std::size_t n) {
    std::ofstream f(path,std::ios::binary);g::require(bool(f),"016 output open failed");
    f.write(reinterpret_cast<const char*>(ptr),std::streamsize(n*sizeof(T)));
    g::require(bool(f),"016 output write failed");
}
int main(int argc,char** argv){try{
    g::require(argc==7&&std::string(argv[1])=="--scene"&&std::string(argv[3])=="--weights"&&std::string(argv[5])=="--out",
               "016 requires --scene FILE --weights OLD_FILE --out NEW_DIR");
    const fs::path out=argv[6];g::require(!fs::exists(out),"016 no overwrite");
    std::ifstream input(argv[2]);g::require(bool(input),"016 scene unavailable");const auto scene=o::parse_scene(input);
    g::Transport transport(scene);g::Field field(scene);
    std::ifstream weights(argv[4],std::ios::binary);g::require(bool(weights),"016 frozen weights unavailable");
    weights.read(reinterpret_cast<char*>(field.weights.data()),std::streamsize(field.weights.size()*sizeof(g::Weights)));
    g::require(bool(weights)&&weights.peek()==std::char_traits<char>::eof(),"016 weight shape differs");
    for(const auto& row:field.weights)g::validate(g::quantize(row));
    g::require(fs::create_directory(out),"016 output creation failed");
    std::vector<o::PrimaryRecord> primary(57600);std::vector<unsigned> hits;g::Counts scan;
    for(unsigned id=0;id<primary.size();++id){g::Surface surface;
        if(transport.trace(transport.oracle.primary_ray(id%320,id/320,.5,.5),scene.camera.near,scene.camera.far,~0u,surface,scan,&primary[id]))hits.push_back(id);
    }
    g::require(hits.size()>=16,"016 insufficient primary support");std::array<unsigned,16> selected{};
    for(unsigned k=0;k<16;++k)selected[k]=hits[((2*k+1)*hits.size())/32];
    save(out/"all-primary.bin",primary.data(),primary.size());save(out/"selected-pixels.u32",selected.data(),selected.size());
    constexpr std::array<std::uint64_t,4> seeds{305419896ULL,2596069104ULL,81985529216486895ULL,18364758544493064720ULL};
    std::ofstream report(out/"capture.json");report<<std::setprecision(17);
    report<<"{\"schema\":\"m001-normal-product-guide-cpu-native/1\",\"primary_scan_queries\":"<<scan.closest
          <<",\"primary_hit_pixels\":"<<hits.size()<<",\"new_training_paths\":0,\"grid\":8,\"bins\":64,\"spp\":1024,\"seeds\":[";
    for(unsigned i=0;i<4;++i)report<<(i?",":"")<<seeds[i];
    report<<"],\"guide_lo\":["<<field.lo.x<<','<<field.lo.y<<','<<field.lo.z<<"],\"guide_extent\":["<<field.extent.x<<','<<field.extent.y<<','<<field.extent.z<<"],\"rows\":[";
    bool comma=false;
    for(unsigned depth:{2u,8u}){
        g::Counts counts;std::vector<double> samples,direct;samples.reserve(65536);direct.reserve(64);
        for(auto seed:seeds)for(unsigned id:selected){g::Surface first;o::PrimaryRecord record;
            g::require(transport.trace(transport.oracle.primary_ray(id%320,id/320,.5,.5),scene.camera.near,scene.camera.far,~0u,first,counts,&record),"016 selected primary disappeared");
            g::require(record.tri==primary[id].tri&&record.t==primary[id].t,"016 primary replay differs");
            o::Xoshiro256 drng(seed,id,~0ULL);direct.push_back(transport.direct(first,drng,counts));
            for(unsigned sample=0;sample<1024;++sample){o::Xoshiro256 rng(seed,id,sample);samples.push_back(p::render(transport,field,first,depth,rng,counts));}
        }
        const auto name="b"+std::to_string(depth)+"-product";
        save(out/(name+".samples.f64"),samples.data(),samples.size());save(out/(name+".direct.f64"),direct.data(),direct.size());
        report<<(comma?",":"")<<"{\"depth\":"<<depth<<",\"sample_file\":\""<<name<<".samples.f64\",\"direct_file\":\""<<name
              <<".direct.f64\",\"closest_queries\":"<<counts.closest<<",\"shadow_queries\":"<<counts.shadow<<",\"null_samples\":"<<counts.nulls<<"}";comma=true;
        std::cout<<name<<" CPU samples retained\n"<<std::flush;
    }
    report<<"],\"gpu_executed\":false,\"candidate_is_independent_reference\":false}\n";
    g::require(bool(report),"016 report write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

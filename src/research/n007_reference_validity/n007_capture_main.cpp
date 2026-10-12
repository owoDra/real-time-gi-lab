// N007-only matched-frame CPU/GPU capture; historical renderer unchanged.
#include "n007_cpu_components.hpp"
#include "n001_runtime.hpp"
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;
namespace n=phos::gi::research::n007;
namespace r=phos::gi::research::integration;
namespace {
void pfm(const fs::path& file,std::uint32_t w,std::uint32_t h,const std::vector<float>& values) {
    static_assert(std::endian::native==std::endian::little);
    if(values.size()!=std::size_t(w)*h)throw std::runtime_error("PFM shape mismatch");
    fs::create_directories(file.parent_path());
    std::ofstream out(file,std::ios::binary);
    if(!out)throw std::runtime_error("PFM output open failed");
    out<<"PF\n"<<w<<' '<<h<<"\n-1.0\n";
    for(auto y=h;y-->0;)for(std::uint32_t x=0;x<w;++x) {
        const float v=values[std::size_t(y)*w+x];
        const float pixel[3]{v,v,v};
        out.write(reinterpret_cast<const char*>(pixel),sizeof(pixel));
    }
    if(!out)throw std::runtime_error("PFM output write failed");
}
template<class T>void raw(std::ofstream& out,const T& item) {
    out.write(reinterpret_cast<const char*>(&item),sizeof(item));
}
void capture_state(const fs::path& out,const r::I001RendererReadback& f) {
    std::ofstream geometry(out/"geometry-state.bin",std::ios::binary);
    std::ofstream frame(out/"frame-state.bin",std::ios::binary);
    if(!geometry||!frame)throw std::runtime_error("state output failed");
    const std::uint32_t version=1,ntri=std::uint32_t(f.triangles.size());
    raw(geometry,version);raw(geometry,ntri);
    for(const auto& t:f.triangles) {
        for(const auto& v:{t.v0,t.v1,t.v2}) {
            raw(geometry,v.x);raw(geometry,v.y);raw(geometry,v.z);
        }
        raw(geometry,t.primitive_id);raw(geometry,t.material_id);raw(geometry,t.instance_id);
        const std::uint32_t sided=t.two_sided?1U:0U;raw(geometry,sided);
    }
    const char magic[12]={'N','0','0','7','-','S','T','A','T','E','1','\0'};
    frame.write(magic,sizeof(magic));raw(frame,f.width);raw(frame,f.height);raw(frame,f.params);
    if(!geometry||!frame)throw std::runtime_error("state serialization failed");
}
void write_hits(const fs::path& path,const std::vector<n::PrimaryHit>& hits) {
    std::ofstream out(path,std::ios::binary);
    if(!out)throw std::runtime_error("CPU primary hit output failed");
    out.write(reinterpret_cast<const char*>(hits.data()),
              std::streamsize(hits.size()*sizeof(hits[0])));
    if(!out)throw std::runtime_error("CPU primary hit write failed");
}
std::string arg_value(int argc,char** argv,int& i) {
    if(i+1>=argc)throw std::invalid_argument("missing N007 argument value");
    return argv[++i];
}
}
int main(int argc,char** argv) {
    try {
        fs::path out,scene;
        std::string scenario,backend;
        bool target=false;
        std::uint32_t spp=512;
        for(int i=1;i<argc;++i) {
            const std::string arg=argv[i];
            if(arg=="--out")out=arg_value(argc,argv,i);
            else if(arg=="--scene")scene=arg_value(argc,argv,i);
            else if(arg=="--scenario")scenario=arg_value(argc,argv,i);
            else if(arg=="--backend")backend=arg_value(argc,argv,i);
            else if(arg=="--spp")spp=std::uint32_t(std::stoul(arg_value(argc,argv,i)));
            else if(arg=="--target-state")target=true;
            else throw std::invalid_argument("unknown N007 option: "+arg);
        }
        if(out.empty()||scene.empty()||scenario.empty()||
           (backend!="software"&&backend!="hwrt")||
           (spp!=512&&spp!=1024&&spp!=2048&&spp!=4096&&spp!=8192))
            throw std::invalid_argument(
                "required: --out DIR --scene GLTF --scenario NAME --backend software|hwrt "
                "[--spp 512|1024|2048|4096|8192] [--target-state]");
        fs::create_directories(out/"gpu");fs::create_directories(out/"cpu");
        r::I001Options opt{};
        opt.scene=scene;
        opt.scenario=r::i001_parse_scenario(scenario);
        opt.variant=backend=="software"?
            r::I001Variant::LaneEFinalSoftware:r::I001Variant::LaneEFinalHwrt;
        r::I001Runtime runtime(opt);
        (void)runtime.run_frame(false);
        if(target)(void)runtime.run_frame(true);
        const auto path=fs::absolute(out/"gpu/hits.bin").string();
        if(setenv("PHOS_N007_GPU_HITS",path.c_str(),1)!=0)
            throw std::runtime_error("could not set GPU hit capture path");
        const auto frame=runtime.renderer_readback();
        if(frame.width!=320||frame.height!=180)
            throw std::runtime_error("N007 preregistered 320x180 dimensions mismatch");
        capture_state(out,frame);
        std::ofstream metadata(out/"capture.json");
        if(!metadata)throw std::runtime_error("capture metadata open failed");
        metadata<<"{\"schema_version\":1,\"scenario\":\""<<scenario
                <<"\",\"backend\":\""<<backend
                <<"\",\"target_state\":"<<(target?"true":"false")
                <<",\"frame_id\":"<<(target?2:1)
                <<",\"spp\":"<<spp
                <<",\"width\":"<<frame.width<<",\"height\":"<<frame.height
                <<",\"triangles\":"<<frame.triangles.size()<<"}\n";
        if(!metadata)throw std::runtime_error("capture metadata write failed");
        const auto npx=std::size_t(frame.width)*frame.height;
        if(frame.image_rgba.size()!=npx*4)
            throw std::runtime_error("GPU packed output shape mismatch");
        std::vector<float> gpu_d,gpu_i,gpu_t;
        gpu_d.reserve(npx);gpu_i.reserve(npx);gpu_t.reserve(npx);
        for(std::size_t k=0;k<npx;++k) {
            gpu_d.push_back(frame.image_rgba[4*k]);
            gpu_i.push_back(frame.image_rgba[4*k+1]);
            gpu_t.push_back(frame.image_rgba[4*k+2]);
        }
        pfm(out/"gpu/direct.pfm",frame.width,frame.height,gpu_d);
        pfm(out/"gpu/indirect.pfm",frame.width,frame.height,gpu_i);
        pfm(out/"gpu/total.pfm",frame.width,frame.height,gpu_t);
        n::FrameParams p{};
        for(std::size_t i=0;i<4;++i) {
            p.camera_pos_near[i]=frame.params.camera_pos_near[i];
            p.camera_right_tan_x[i]=frame.params.camera_right_tan_x[i];
            p.camera_up_tan_y[i]=frame.params.camera_up_tan_y[i];
            p.camera_forward_far[i]=frame.params.camera_forward_far[i];
            p.light_pos_interval[i]=frame.params.light_pos_interval[i];
        }
        constexpr std::uint64_t seeds[]{
            305419896ULL,2596069104ULL,81985529216486895ULL,18364758544493064720ULL};
        std::vector<float> cpu_d(npx),cpu_i(npx),cpu_t(npx);
        n::ShadowStats counts{};
        for(std::size_t i=0;i<4;++i) {
            const auto sample=n::capture_cpu(frame.triangles,p,frame.width,frame.height,spp,seeds[i]);
            const auto dir=out/"cpu"/("seed-"+std::to_string(i));
            fs::create_directories(dir);
            pfm(dir/"direct.pfm",frame.width,frame.height,sample.direct);
            pfm(dir/"indirect.pfm",frame.width,frame.height,sample.indirect);
            pfm(dir/"total.pfm",frame.width,frame.height,sample.total);
            if(i==0)write_hits(out/"cpu/hits.bin",sample.primary);
            counts+=sample.counts;
            for(std::size_t k=0;k<npx;++k) {
                cpu_d[k]+=sample.direct[k]*.25F;
                cpu_i[k]+=sample.indirect[k]*.25F;
                cpu_t[k]+=sample.total[k]*.25F;
            }
        }
        pfm(out/"cpu/direct.pfm",frame.width,frame.height,cpu_d);
        pfm(out/"cpu/indirect.pfm",frame.width,frame.height,cpu_i);
        pfm(out/"cpu/total.pfm",frame.width,frame.height,cpu_t);
        std::ofstream stats(out/"cpu/counts.json");
        stats<<"{\"primary_hits\":"<<counts.primary_hits
             <<",\"secondary_hits\":"<<counts.secondary_hits
             <<",\"shadow_tested\":"<<counts.shadow_tested
             <<",\"shadow_blocked\":"<<counts.shadow_blocked
             <<",\"shadow_clear\":"<<counts.shadow_clear
             <<",\"positive_samples\":"<<counts.positive_samples<<"}\n";
        if(!stats)throw std::runtime_error("N007 shadow counter output failed");
        std::cout<<"N007 component capture saved; historical causation not proven.\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"N007: "<<e.what()<<'\n';return 1;
    }
}

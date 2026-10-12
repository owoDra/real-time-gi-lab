// N007-only CPU reference acquisition from frozen post-motion state snapshots.
// No Vulkan initialization. Writes four fixed-seed PFMs for one frozen SPP level.
// This is reference *sampling*, not physical truth or a statistical PASS.
#include "n007_cpu_components.hpp"
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

namespace fs=std::filesystem;
namespace n=phos::gi::research::n007;
namespace b=phos::gi::research::lane_b;
namespace {
template<typename T>void read(std::ifstream& in,T& value){
    static_assert(std::is_trivially_copyable_v<T>);
    if(!in.read(reinterpret_cast<char*>(&value),sizeof(value)))
        throw std::runtime_error("N007 frozen state read truncated");
}
struct alignas(16) Params {
    std::array<float,4> camera_pos_near{},camera_right_tan_x{},
        camera_up_tan_y{},camera_forward_far{},scene_origin_spacing{},
        light_pos_interval{};
    std::array<std::uint32_t,4> counts{},limits{};
};
static_assert(sizeof(Params)==128);
n::FrameParams params(const fs::path& path){
    if(!fs::is_regular_file(path)||fs::file_size(path)!=148)
        throw std::runtime_error("N007 frozen frame-state must be 148 bytes");
    std::ifstream in(path,std::ios::binary);
    std::array<char,12> marker{};read(in,marker);
    constexpr std::array<char,12> expected{'N','0','0','7','-','S','T','A','T','E','1','\0'};
    if(marker!=expected)throw std::runtime_error("N007 frozen frame-state magic");
    std::uint32_t w{},h{};read(in,w);read(in,h);
    if(w!=320||h!=180)throw std::runtime_error("N007 fixed 320x180 frame required");
    Params in_params{};read(in,in_params);
    if(in_params.counts[1]!=320||in_params.counts[2]!=180)
        throw std::runtime_error("N007 camera viewport diverges from frame-state");
    n::FrameParams out{};
    out.camera_pos_near=in_params.camera_pos_near;
    out.camera_right_tan_x=in_params.camera_right_tan_x;
    out.camera_up_tan_y=in_params.camera_up_tan_y;
    out.camera_forward_far=in_params.camera_forward_far;
    out.light_pos_interval=in_params.light_pos_interval;
    return out;
}
std::vector<b::Triangle> triangles(const fs::path& path){
    if(!fs::is_regular_file(path)||fs::file_size(path)<8)
        throw std::runtime_error("N007 geometry state missing");
    std::ifstream in(path,std::ios::binary);
    std::uint32_t version{},count{};read(in,version);read(in,count);
    if(version!=1||count==0||count>100000000U||
       fs::file_size(path)!=8ULL+std::uint64_t(count)*52ULL)
        throw std::runtime_error("N007 geometry state layout mismatch");
    std::vector<b::Triangle> out;out.reserve(count);
    for(std::uint32_t i=0;i<count;++i){
        std::array<float,9> v{};
        std::array<std::uint32_t,4> meta{};
        read(in,v);read(in,meta);
        if(meta[0]!=i||meta[3]>1U)throw std::runtime_error("N007 geometry primitive identity/order");
        for(const auto val:v)if(!std::isfinite(val))
            throw std::runtime_error("N007 geometry nonfinite value");
        out.push_back({{v[0],v[1],v[2]},{v[3],v[4],v[5]},
                       {v[6],v[7],v[8]},meta[0],meta[1],meta[2],meta[3]!=0});
    }
    return out;
}
void pfm(const fs::path& path,const std::vector<float>& values){
    if(values.size()!=320U*180U)throw std::runtime_error("N007 PFM shape mismatch");
    std::ofstream out(path,std::ios::binary);
    if(!out)throw std::runtime_error("N007 PFM open failed");
    out<<"PF\n320 180\n-1.0\n";
    for(int y=179;y>=0;--y)for(int x=0;x<320;++x){
        const float v=values[std::size_t(y)*320+x];
        const float pixel[]{v,v,v};
        out.write(reinterpret_cast<const char*>(pixel),sizeof(pixel));
    }
    if(!out)throw std::runtime_error("N007 PFM write failed");
}
}
int main(int argc,char** argv){
    try{
        static_assert(std::endian::native==std::endian::little);
        fs::path capture,out;
        std::uint32_t spp=0;
        for(int i=1;i<argc;++i){
            const std::string arg=argv[i];
            if(i+1==argc)throw std::invalid_argument("N007 CPU reference argument missing");
            if(arg=="--capture")capture=argv[++i];
            else if(arg=="--out")out=argv[++i];
            else if(arg=="--spp")spp=std::uint32_t(std::stoul(argv[++i]));
            else throw std::invalid_argument("unknown N007 CPU reference option");
        }
        if(capture.empty()||out.empty()||(
           spp!=512&&spp!=1024&&spp!=2048&&spp!=4096&&spp!=8192))
            throw std::invalid_argument("required: --capture DIR --out DIR --spp 512|1024|2048|4096|8192");
        if(fs::exists(out))throw std::runtime_error("N007 SPP level already exists; no overwrite");
        const auto p=params(capture/"frame-state.bin");
        const auto geometry=triangles(capture/"geometry-state.bin");
        const auto partial=fs::path(out.string()+".partial");
        if(fs::exists(partial))throw std::runtime_error("N007 incomplete SPP level already exists");
        fs::create_directories(partial);
        constexpr std::array<std::uint64_t,4> seeds{
            305419896ULL,2596069104ULL,
            81985529216486895ULL,18364758544493064720ULL};
        for(std::size_t i=0;i<seeds.size();++i){
            const auto result=n::capture_cpu(geometry,p,320,180,spp,seeds[i]);
            const auto sub=partial/("seed-"+std::to_string(i));
            fs::create_directories(sub);
            pfm(sub/"direct.pfm",result.direct);
            pfm(sub/"indirect.pfm",result.indirect);
            pfm(sub/"total.pfm",result.total);
            std::cout<<"N007 CPU SPP "<<spp<<" seed "<<i
                     <<" positive_samples="<<result.counts.positive_samples
                     <<" shadow_blocked="<<result.counts.shadow_blocked
                     <<" shadow_clear="<<result.counts.shadow_clear<<std::endl;
        }
        fs::rename(partial,out);
        std::cout<<"N007 CPU reference level saved: "<<out<<"\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"N007 CPU reference: "<<e.what()<<'\n';return 1;
    }
}

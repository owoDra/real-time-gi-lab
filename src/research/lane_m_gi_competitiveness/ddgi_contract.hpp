#pragma once
// Standalone DDGI input/stage contract; this header never initializes Vulkan.
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace m001 {
inline void require(bool ok, const char* why) {
    if (!ok) throw std::runtime_error(why);
}
struct alignas(16) Frame {
    float camera_pos_near[4], camera_right_tan_x[4], camera_up_tan_y[4], camera_forward_far[4];
    float scene_origin_spacing[4], light_pos_interval[4];
    uint32_t counts[4], limits[4];
};
struct alignas(16) GpuTriangle { float v0[4],v1[4],v2[4]; uint32_t metadata[4]; };
struct Push { uint32_t previous_ready, begin, count, reserved; };
static_assert(sizeof(Frame)==128 && offsetof(Frame,counts)==96 && offsetof(Frame,limits)==112);
static_assert(sizeof(GpuTriangle)==64 && offsetof(GpuTriangle,metadata)==48 && sizeof(Push)==16);
struct Triangle { std::array<float,3> v0,v1,v2; uint32_t primitive,material,instance,two_sided; };
struct State { Frame frame{}; uint32_t width{},height{}; std::vector<Triangle> triangles; };
template<class T> T read(std::ifstream& f) {
    T v{}; f.read(reinterpret_cast<char*>(&v),sizeof(v)); require(bool(f),"truncated state"); return v;
}
inline State load_state(const std::filesystem::path& root) {
    require(std::endian::native==std::endian::little,"little endian required");
    State s;
    auto geometry=root/"geometry-state.bin", frame=root/"frame-state.bin";
    std::ifstream g(geometry,std::ios::binary);
    require(read<uint32_t>(g)==1,"geometry version");
    uint32_t n=read<uint32_t>(g);
    require(n>0 && n<=1000000 && std::filesystem::file_size(geometry)==8+uint64_t(n)*52,"geometry shape");
    for (uint32_t j=0;j<n;++j) {
        Triangle t{read<std::array<float,3>>(g),read<std::array<float,3>>(g),read<std::array<float,3>>(g),
                   read<uint32_t>(g),read<uint32_t>(g),read<uint32_t>(g),read<uint32_t>(g)};
        require(t.two_sided==1 && t.primitive==j,"BF-P two-sided contiguous primitive slots required");
        for(auto v:{t.v0,t.v1,t.v2})for(float x:v) require(std::isfinite(x),"nonfinite geometry");
        double u[3],v[3];for(int k=0;k<3;++k){u[k]=double(t.v1[k])-t.v0[k];v[k]=double(t.v2[k])-t.v0[k];}
        double area=0;for(int k=0;k<3;++k){double c=u[(k+1)%3]*v[(k+2)%3]-u[(k+2)%3]*v[(k+1)%3];area+=c*c;}
        require(area>0 && std::isfinite(area),"degenerate geometry"); s.triangles.push_back(t);
    }
    std::ifstream f(frame,std::ios::binary); auto magic=read<std::array<char,12>>(f);
    require(magic==std::array<char,12>{'N','0','0','7','-','S','T','A','T','E','1',0}
            && std::filesystem::file_size(frame)==148,"frame magic/shape");
    s.width=read<uint32_t>(f);s.height=read<uint32_t>(f);s.frame=read<Frame>(f);
    require(s.width>0 && s.height>0 && s.width<=4096 && s.height<=4096 && uint64_t(s.width)*s.height<=16777216
        && s.width==s.frame.counts[1] && s.height==s.frame.counts[2],"frame dimensions");
    // Only the first six float4s are floating point; counts/limits are integers.
    auto floats=std::bit_cast<std::array<float,32>>(s.frame);
    for(int k=0;k<24;++k) require(std::isfinite(floats[k]),"nonfinite frame");
    require(s.frame.camera_forward_far[3]>0 && s.frame.light_pos_interval[3]>0
            && s.frame.camera_right_tan_x[3]>0 && s.frame.camera_up_tan_y[3]>0,"physical frame range");
    auto dot=[](const float* a,const float* b){double r=0;for(int k=0;k<3;++k)r+=double(a[k])*b[k];return r;};
    auto r=s.frame.camera_right_tan_x,u=s.frame.camera_up_tan_y,w=s.frame.camera_forward_far;
    require(std::abs(dot(r,r)-1)<1e-5 && std::abs(dot(u,u)-1)<1e-5 && std::abs(dot(w,w)-1)<1e-5
        && std::abs(dot(r,u))<1e-5 && std::abs(dot(r,w))<1e-5 && std::abs(dot(u,w))<1e-5,"camera basis");
    return s;
}
struct Stage { uint32_t ordinal,write,read,previous_ready; };
inline std::vector<Stage> stages(uint32_t vertices) {
    require(vertices==1 || vertices==2 || vertices==8,"unsupported transport depth");
    std::vector<Stage> out;
    for(uint32_t k=0;k+1<vertices;++k)out.push_back({k,k%2,1-k%2,k?1u:0u});
    return out;
}
struct Tile { uint32_t begin,count; };
inline std::vector<Tile> tiles(uint32_t total,uint32_t limit=4096) {
    require(total>0 && total<=24u*24u*24u*512u && limit>0 && limit<=4096,"invalid bounded ray tiling");
    std::vector<Tile> out;
    for(uint32_t j=0;j<total;){uint32_t n=std::min(limit,total-j);out.push_back({j,n});j+=n;}
    return out;
}
struct Grid { std::array<float,3> origin,spacing; uint32_t side,rays; };
inline Grid grid(const State& s,uint32_t side,uint32_t rays) {
    require(side>=2 && side<=24 && (rays==128 || rays==256 || rays==512),"unsupported DDGI budget");
    Grid out{{},{},side,rays};
    std::array<double,3> lo{INFINITY,INFINITY,INFINITY},hi{-INFINITY,-INFINITY,-INFINITY};
    for(const auto& t:s.triangles) for(auto p:{t.v0,t.v1,t.v2})for(int k=0;k<3;++k){lo[k]=std::min(lo[k],double(p[k]));hi[k]=std::max(hi[k],double(p[k]));}
    // Geometry-only AABB plus one nominal cell on either side. No image-dependent placement.
    for(int k=0;k<3;++k){double extent=hi[k]-lo[k];require(extent>0,"zero AABB extent");double pad=extent/(side-1);
        out.origin[k]=float((hi[k]+lo[k])*.5);out.spacing[k]=float((extent+2*pad)/(side-1));
        require(std::isfinite(out.origin[k]) && std::isfinite(out.spacing[k]) && out.spacing[k]>0,"grid range");}
    return out;
}
inline void create_output(const std::filesystem::path& p) {
    // Atomic final directory creation; existing output (including a symlink) is never accepted.
    require(!p.empty(),"output path required");
    if(!p.parent_path().empty())std::filesystem::create_directories(p.parent_path());
    require(std::filesystem::create_directory(p),"refuse existing output");
}
}

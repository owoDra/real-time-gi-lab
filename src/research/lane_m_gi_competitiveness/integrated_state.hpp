#pragma once
#include "b002_hwrt.hpp"
#include "a001_runtime.hpp"
#include "integrated_safety.hpp"
#include <array>
#include <cmath>
#include <cstring>
#include <fstream>
#include <set>
#include <vector>
namespace m022 {
namespace b=phos::gi::research::lane_b;
namespace a=phos::gi::lane_a;
namespace fs=std::filesystem;
struct State {std::vector<b::Triangle> triangles;a::A001ParamsGpu params{};std::array<float,20> camera{};};
template<class T>inline T read(std::ifstream& f){T x{};f.read(reinterpret_cast<char*>(&x),sizeof(x));need(bool(f),"022 truncated state");return x;}
inline State load_state(const fs::path& path){
    State s;auto gp=path/"geometry-state.bin",fp=path/"frame-state.bin";
    need(fs::is_regular_file(gp)&&fs::is_regular_file(fp),"022 state files missing");
    std::ifstream g(gp,std::ios::binary);need(read<std::uint32_t>(g)==1,"022 geometry version");auto count=read<std::uint32_t>(g);
    need(count>0 && count<=2048 && fs::file_size(gp)==8+52ull*count,"022 geometry shape/range");
    std::set<std::uint32_t> keys;std::array<float,3> lo{INFINITY,INFINITY,INFINITY},hi{-INFINITY,-INFINITY,-INFINITY};
    for(std::uint32_t j=0;j<count;j++){
        b::Triangle t;t.v0=read<b::Vec3>(g);t.v1=read<b::Vec3>(g);t.v2=read<b::Vec3>(g);
        t.primitive_id=read<std::uint32_t>(g);t.material_id=read<std::uint32_t>(g);t.instance_id=read<std::uint32_t>(g);auto two=read<std::uint32_t>(g);t.two_sided=two==1;
        need(two==1 && t.primitive_id!=0xffffffffu && t.instance_id!=0xffffffffu && keys.insert(t.primitive_id).second,"022 geometry metadata");
        for(auto v:{t.v0,t.v1,t.v2}){std::array<float,3> value{v.x,v.y,v.z};for(int k=0;k<3;k++){need(std::isfinite(value[k]),"022 nonfinite vertex");lo[k]=std::min(lo[k],value[k]);hi[k]=std::max(hi[k],value[k]);}}
        float x1=t.v1.x-t.v0.x,y1=t.v1.y-t.v0.y,z1=t.v1.z-t.v0.z,x2=t.v2.x-t.v0.x,y2=t.v2.y-t.v0.y,z2=t.v2.z-t.v0.z;
        float nx=y1*z2-z1*y2,ny=z1*x2-x1*z2,nz=x1*y2-y1*x2;
        need(std::isfinite(nx)&&std::isfinite(ny)&&std::isfinite(nz)&&(nx!=0||ny!=0||nz!=0),"022 degenerate triangle");s.triangles.push_back(t);
    }
    std::ifstream f(fp,std::ios::binary);char magic[12]{};f.read(magic,12);need(std::memcmp(magic,"N007-STATE1\0",12)==0 && fs::file_size(fp)==148,"022 frame magic/shape");
    auto width=read<std::uint32_t>(f),height=read<std::uint32_t>(f);s.params=read<a::A001ParamsGpu>(f);auto& p=s.params;
    need(width==320 && height==180 && p.counts[0]==count && p.counts[1]==width && p.counts[2]==height,"022 viewport/counts");
    std::array<float,24> floats;std::memcpy(floats.data(),&p,96);for(float value:floats)need(std::isfinite(value),"022 nonfinite frame");
    for(auto axis:{p.camera_forward_far,p.camera_right_tan_x,p.camera_up_tan_y}){float norm=(axis[0]*axis[0]+axis[1]*axis[1])+axis[2]*axis[2];need(std::abs(norm-1)<=1e-4f,"022 camera basis not unit");}
    for(auto pair:{std::pair{p.camera_forward_far,p.camera_right_tan_x},std::pair{p.camera_forward_far,p.camera_up_tan_y},std::pair{p.camera_right_tan_x,p.camera_up_tan_y}}){float dot=(pair.first[0]*pair.second[0]+pair.first[1]*pair.second[1])+pair.first[2]*pair.second[2];need(std::abs(dot)<=1e-4f,"022 camera basis not orthogonal");}
    need(p.camera_forward_far[3]>=1e-4f && p.camera_right_tan_x[3]>0 && p.camera_up_tan_y[3]>0 && p.light_pos_interval[3]>0,"022 camera/light range");
    for(int k=0;k<4;k++){s.camera[k]=p.camera_pos_near[k];s.camera[4+k]=p.camera_forward_far[k];s.camera[8+k]=p.camera_right_tan_x[k];s.camera[12+k]=p.camera_up_tan_y[k];}
    float dx=hi[0]-lo[0],dy=hi[1]-lo[1],dz=hi[2]-lo[2];float diagonal=std::sqrt((dx*dx+dy*dy)+dz*dz);
    need(std::isfinite(diagonal),"022 geometry diagonal");s.camera[16]=float(1e-5*std::max(1.,double(diagonal)));s.camera[17]=1;s.camera[18]=320;s.camera[19]=180;return s;
}
inline void budget(std::uint32_t spp,std::uint32_t vertices,std::uint32_t seed){need((spp==16||spp==64)&&(vertices==2||vertices==8)&&seed==305419896u,"022 unregistered budget/seed");}
inline std::vector<std::uint32_t> shader(const fs::path& p){need(fs::is_regular_file(p)&&fs::file_size(p)>=20&&fs::file_size(p)%4==0,"022 shader shape/path");std::vector<std::uint32_t> words(fs::file_size(p)/4);std::ifstream f(p,std::ios::binary);f.read(reinterpret_cast<char*>(words.data()),std::streamsize(words.size()*4));need(bool(f)&&words[0]==0x07230203,"022 shader read/magic");return words;}
}

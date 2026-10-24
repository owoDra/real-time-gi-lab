#pragma once
//019 storage shim for the ACTUAL GLSL scalar kernel. No Vulkan calls in here.
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <vector>
namespace m001_q019 {
using uint=std::uint32_t;
struct Storage {
    std::array<float,20> camera{};
    std::vector<uint> hits,maps;
    std::vector<float> geometry,coefficients,sources,stages,unclipped;
    uint size() const{return uint(camera[18])*uint(camera[19]);}
    uint images() const{return uint(camera[17]);}
    void allocate(){uint n=size();geometry.assign(n*8,0);coefficients.assign(n*75,0);maps.assign(n*6,0);
        stages.assign(n*images()*3,0);unclipped.assign(n*images()*3,0);}
};
inline thread_local Storage* active=nullptr;
inline uint q_width(){return uint(active->camera[18]);}inline uint q_height(){return uint(active->camera[19]);}
inline uint q_size(){return active->size();}inline uint q_images(){return active->images();}
inline uint q_hit(uint p,uint w){return active->hits.at(p*8+w);}inline float q_camera(uint a){return active->camera.at(a);}
inline float q_fbits(uint x){return std::bit_cast<float>(x);}inline float q_sqrt(float x){return std::sqrt(x);}
inline float q_abs(float x){return std::abs(x);}inline float q_floor(float x){return std::floor(x);}
inline float q_max(float x,float y){return std::max(x,y);}inline int q_iabs(int x){return std::abs(x);}inline int q_imax(int x,int y){return std::max(x,y);}
inline float q_getgeo(uint p,uint a){return active->geometry.at(p*8+a);}inline void q_setgeo(uint p,uint a,float v){active->geometry.at(p*8+a)=v;}
inline float q_getcoeff(uint s,uint j,uint p){return active->coefficients.at((s*25+j)*q_size()+p);}
inline void q_setcoeff(uint s,uint j,uint p,float v){active->coefficients.at((s*25+j)*q_size()+p)=v;}
inline void q_setmask(uint s,uint p,uint v){active->maps.at(s*q_size()+p)=v;}
inline void q_setselector(uint s,uint p,uint v){active->maps.at((3+s)*q_size()+p)=v;}
inline float q_source(uint i,uint p){return active->sources.at(i*q_size()+p);}
inline float q_readstage(uint i,uint s,uint p){return active->stages.at((i*3+s)*q_size()+p);}
inline void q_writestage(uint i,uint s,uint p,float r,float v){uint o=(i*3+s)*q_size()+p;active->unclipped.at(o)=r;active->stages.at(o)=v;}
#define precise
#define Q_OUT
#include "surface_quadratic_shared.glslinc"
#undef Q_OUT
#undef precise
inline void execute(Storage& s){active=&s;for(uint p=0;p<s.size();p++)q_geometry(p);
    for(uint stage=0;stage<3;stage++)for(uint p=0;p<s.size();p++)q_fit(p,1u<<stage,stage);
    for(uint stage=0;stage<3;stage++)for(uint p=0;p<s.size();p++)q_apply(p,1u<<stage,stage);active=nullptr;}
}

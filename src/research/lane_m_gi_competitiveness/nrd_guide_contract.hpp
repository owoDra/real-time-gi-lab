#pragma once
//023 native API/guide metadata contract; no graphics calls.
#include "NRD.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <utility>
namespace m023 {
inline void need(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
using Camera=std::array<float,20>;
inline double dot(const float* a,const float* b){return double(a[0])*b[0]+double(a[1])*b[1]+double(a[2])*b[2];}
inline void validate(const Camera& c){
    for(float v:c)need(std::isfinite(v),"023 nonfinite camera");
    need(c[3]>0&&c[7]>c[3]&&c[11]>0&&c[15]>0&&c[18]>=1&&c[19]>=1&&c[18]<=4096&&c[19]<=4096&&std::floor(c[18])==c[18]&&std::floor(c[19])==c[19],"023 camera range/viewport");
    for(int a:{4,8,12})need(std::abs(dot(&c[a],&c[a])-1)<=1e-4,"023 camera basis unit");
    for(auto p:{std::pair{4,8},std::pair{4,12},std::pair{8,12}})need(std::abs(dot(&c[p.first],&c[p.second]))<=1e-4,"023 camera basis orthogonal");
}
inline nrd::CommonSettings common(const Camera& c,std::uint32_t frame,bool clear){
    validate(c);nrd::CommonSettings s{};float near=c[3],far=c[7];
    s.viewToClipMatrix[0]=1/c[11];s.viewToClipMatrix[5]=1/c[15];s.viewToClipMatrix[10]=far/(far-near);s.viewToClipMatrix[11]=1;s.viewToClipMatrix[14]=-near*(far/(far-near));
    for(int row=0;row<3;row++){int axis=row==0?8:row==1?12:4;for(int col=0;col<3;col++)s.worldToViewMatrix[col*4+row]=c[axis+col];s.worldToViewMatrix[12+row]=-float(dot(&c[axis],c.data()));}s.worldToViewMatrix[15]=1;
    std::copy_n(s.viewToClipMatrix,16,s.viewToClipMatrixPrev);std::copy_n(s.worldToViewMatrix,16,s.worldToViewMatrixPrev);
    for(int a=0;a<2;a++){auto n=std::uint16_t(c[18+a]);s.resourceSize[a]=s.resourceSizePrev[a]=s.rectSize[a]=s.rectSizePrev[a]=n;}
    s.timeDeltaBetweenFrames=1000.f/60.f;s.denoisingRange=far;s.frameIndex=frame;s.accumulationMode=clear?nrd::AccumulationMode::CLEAR_AND_RESTART:nrd::AccumulationMode::CONTINUE;return s;
}
struct HitDistance {float sum{};std::uint32_t count{};
    void add(float first_secondary_distance){need(std::isfinite(first_secondary_distance)&&first_secondary_distance>=0,"023 invalid first-secondary distance");need(count<16384,"023 distance sample cap");sum+=std::min(first_secondary_distance,65504.f);count++;}
    float mean()const{need(count>0&&std::isfinite(sum),"023 empty/nonfinite distance sum");return sum/float(count);}
};
inline float view_z(float t,const std::array<float,3>& ray,const Camera& c){need(std::isfinite(t)&&t>=0,"023 primary distance");double norm=dot(ray.data(),ray.data());need(std::abs(norm-1)<=1e-4,"023 primary ray unit");float z=t*float(dot(ray.data(),&c[4]));need(std::isfinite(z)&&z>0,"023 viewZ not positive");return z;}
inline std::array<float,4> normal_oct(const std::array<float,3>& n){
    need(std::isfinite(n[0])&&std::isfinite(n[1])&&std::isfinite(n[2])&&std::abs(dot(n.data(),n.data())-1)<=1e-4,"023 normal not finite/unit");
    float length=std::abs(n[0])+std::abs(n[1])+std::abs(n[2]);float x=n[0]/length,y=n[1]/length,z=n[2]/length;
    // Upstream _NRD_EncodeNormalRoughness101010, roughness=1, material=0.
    float py=y*.5f+.5f,px=x*.5f+py;py-=x*.5f;return {px,py,z<0?0.f:1.f,0.f};
}
}

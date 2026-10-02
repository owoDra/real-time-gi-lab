#pragma once
#include "traversal_contract.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <optional>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace phos::gi::research::lane_b {

struct Aabb {
    Vec3 min{INFINITY, INFINITY, INFINITY};
    Vec3 max{-INFINITY, -INFINITY, -INFINITY};
};

inline Aabb triangle_bounds(const Triangle& t) noexcept {
    Aabb a{};
    for (Vec3 v : {t.v0, t.v1, t.v2}) {
        a.min.x=std::min(a.min.x,v.x); a.min.y=std::min(a.min.y,v.y); a.min.z=std::min(a.min.z,v.z);
        a.max.x=std::max(a.max.x,v.x); a.max.y=std::max(a.max.y,v.y); a.max.z=std::max(a.max.z,v.z);
    }
    return a;
}
inline Aabb merge(Aabb a,const Aabb& b) noexcept {
    a.min.x=std::min(a.min.x,b.min.x); a.min.y=std::min(a.min.y,b.min.y); a.min.z=std::min(a.min.z,b.min.z);
    a.max.x=std::max(a.max.x,b.max.x); a.max.y=std::max(a.max.y,b.max.y); a.max.z=std::max(a.max.z,b.max.z); return a;
}
inline Vec3 center(const Aabb& a) noexcept { return (a.min+a.max)*0.5F; }
inline bool normalize_ray(Ray& r) noexcept {
    const float len=length(r.direction);
    if(!std::isfinite(len)||len<=1e-8F||!std::isfinite(r.t_max)||r.t_max<=kRayTMin) return false;
    r.direction=r.direction/len; return true;
}
inline bool ray_aabb(const Ray& r,const Aabb& a,float tmax) noexcept {
    float lo=kRayTMin, hi=tmax;
    const float o[3]{r.origin.x,r.origin.y,r.origin.z}, d[3]{r.direction.x,r.direction.y,r.direction.z};
    const float mn[3]{a.min.x,a.min.y,a.min.z}, mx[3]{a.max.x,a.max.y,a.max.z};
    for(int i=0;i<3;++i){
        if(std::abs(d[i])<1e-8F){ if(o[i]<mn[i]||o[i]>mx[i]) return false; continue; }
        float t0=(mn[i]-o[i])/d[i], t1=(mx[i]-o[i])/d[i]; if(t0>t1) std::swap(t0,t1);
        lo=std::max(lo,t0); hi=std::min(hi,t1); if(lo>hi) return false;
    }
    return true;
}
inline std::optional<Hit> intersect_triangle(const Triangle& tri,const Ray& r,float best) noexcept {
    const Vec3 e1=tri.v1-tri.v0,e2=tri.v2-tri.v0,p=cross(r.direction,e2); const float det=dot(e1,p);
    if(tri.two_sided?std::abs(det)<1e-8F:det<=1e-8F) return std::nullopt;
    const float inv=1.0F/det; const Vec3 tv=r.origin-tri.v0; const float u=dot(tv,p)*inv;
    if(u<0||u>1) return std::nullopt;
    const Vec3 q=cross(tv,e1);
    const float v=dot(r.direction,q)*inv;
    if(v<0||u+v>1) return std::nullopt;
    const float t=dot(e2,q)*inv;
    const float tol=std::max(kHitDistanceAbsTolerance,std::abs(best)*kHitDistanceRelTolerance);
    if(t<kRayTMin||t>r.t_max||t>best+tol) return std::nullopt;
    return Hit{true,t,normalize(cross(e1,e2)),tri.primitive_id,tri.material_id,tri.instance_id};
}
inline bool prefer_hit(const Hit& h,const Hit& cur) noexcept {
    if(!h.hit) return false;
    if(!cur.hit) return true;
    const float tol=std::max(kHitDistanceAbsTolerance,std::abs(cur.t)*kHitDistanceRelTolerance);
    return h.t<cur.t-tol || (std::abs(h.t-cur.t)<=tol && h.primitive_id<cur.primitive_id);
}
inline Hit trace_reference(std::span<const Triangle> tris,Ray r) {
    if(!normalize_ray(r)) return {};
    Hit best{};
    for(const auto& t:tris) if(auto h=intersect_triangle(t,r,best.hit?best.t:r.t_max);h&&prefer_hit(*h,best)) best=*h;
    return best;
}
inline bool equivalent_hit(const Hit& a,const Hit& b) noexcept {
    if(a.hit!=b.hit) return false;
    if(!a.hit) return std::isinf(b.t)&&b.primitive_id==kInvalidId&&b.material_id==kInvalidId&&b.instance_id==kInvalidId;
    const float tol=std::max(kHitDistanceAbsTolerance,std::abs(a.t)*kHitDistanceRelTolerance);
    return std::abs(a.t-b.t)<=tol&&a.primitive_id==b.primitive_id&&a.material_id==b.material_id&&a.instance_id==b.instance_id&&dot(normalize(a.normal),normalize(b.normal))>0.9999F;
}

struct Scene { std::string name; std::vector<Triangle> triangles; std::vector<std::uint32_t> moving; };
inline void add_quad(std::vector<Triangle>& t,Vec3 a,Vec3 b,Vec3 c,Vec3 d,std::uint32_t mat,std::uint32_t inst){
    const auto id=std::uint32_t(t.size()); t.push_back({a,b,c,id,mat,inst,true}); t.push_back({a,c,d,id+1,mat,inst,true});
}
inline void add_box(std::vector<Triangle>& t,Vec3 c,Vec3 h,std::uint32_t mat,std::uint32_t inst){
    Vec3 a{c.x-h.x,c.y-h.y,c.z-h.z},b{c.x+h.x,c.y-h.y,c.z-h.z},cc{c.x+h.x,c.y+h.y,c.z-h.z},d{c.x-h.x,c.y+h.y,c.z-h.z};
    Vec3 e{c.x-h.x,c.y-h.y,c.z+h.z},f{c.x+h.x,c.y-h.y,c.z+h.z},g{c.x+h.x,c.y+h.y,c.z+h.z},hh{c.x-h.x,c.y+h.y,c.z+h.z};
    add_quad(t,a,b,cc,d,mat,inst); add_quad(t,f,e,hh,g,mat,inst); add_quad(t,e,a,d,hh,mat,inst);
    add_quad(t,b,f,g,cc,mat,inst); add_quad(t,d,cc,g,hh,mat,inst); add_quad(t,e,f,b,a,mat,inst);
}
inline Scene make_scene(std::string_view kind){
    Scene s{std::string(kind), {}, {}};
    std::uint32_t inst=0;
    auto mark=[&]{const auto first=std::uint32_t(s.triangles.size()-12);for(std::uint32_t p=first;p<first+12;++p)s.moving.push_back(p);};
    if(kind=="sparse") for(int z=-3;z<=3;++z)for(int x=-3;x<=3;++x){if(((x*17+z*13)&3)!=0)continue;add_box(s.triangles,{float(x*18),2,float(z*18)},{1.5F,2,1.5F},inst%7,inst);if(inst%4==0)mark();++inst;}
    else if(kind=="dense") for(int z=-5;z<=5;++z)for(int x=-5;x<=5;++x){float h=1+float((x*x+z*z)%5);add_box(s.triangles,{float(x*4),h,float(z*4)},{1.25F,h,1.25F},inst%11,inst);if(((x+z)&3)==0)mark();++inst;}
    else if(kind=="vertical") for(int l=0;l<14;++l)for(int x=-3;x<=3;++x){add_box(s.triangles,{float(x*6),float(l*6)+1.5F,0},{1,1.5F,10},inst%9,inst);if(l%3==0&&x%2==0)mark();++inst;}
    else throw std::runtime_error("unknown scene");
    return s;
}
inline void translate(std::vector<Triangle>& t,std::span<const std::uint32_t> ids,Vec3 d){for(auto id:ids){auto& q=t.at(id);q.v0=q.v0+d;q.v1=q.v1+d;q.v2=q.v2+d;}}
inline std::vector<Ray> make_rays(std::string_view scene,std::size_t n,float tmax,bool shifted){
    std::vector<Ray> out;out.reserve(n);Vec3 base=scene=="vertical"?Vec3{0,38,-28}:Vec3{0,6,-34};if(shifted)base=base+Vec3{7.5F,3,5};constexpr float golden=2.39996323F;
    for(std::size_t i=0;i<n;++i){float u=(float(i)+.5F)/float(n),y=1-2*u,r=std::sqrt(std::max(0.0F,1-y*y)),a=golden*float(i);Vec3 d=normalize(Vec3{std::cos(a)*r,y,std::sin(a)*r}+Vec3{0,scene=="vertical"?.15F:.05F,1.15F});float j=float((i*2654435761ULL)&1023ULL)/1023-.5F;out.push_back({base+Vec3{j*3,j*1.5F,0},d,tmax});}
    return out;
}

} // namespace phos::gi::research::lane_b

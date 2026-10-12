#pragma once
// N007-only CPU stage instrumentation. This source does not replace N001.
#include "../lane_n_end_to_end_renderer/imported/lane_b_traversal/software_bvh.hpp"
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <thread>
#include <vector>

namespace phos::gi::research::n007 {
namespace b = phos::gi::research::lane_b;

struct FrameParams {
    std::array<float,4> camera_pos_near{};
    std::array<float,4> camera_right_tan_x{};
    std::array<float,4> camera_up_tan_y{};
    std::array<float,4> camera_forward_far{};
    std::array<float,4> light_pos_interval{};
};
struct alignas(16) PrimaryHit {
    std::array<float,4> normal_t{0,0,0,std::numeric_limits<float>::infinity()};
    std::array<std::uint32_t,4> metadata{b::kInvalidId,b::kInvalidId,b::kInvalidId,0};
};
static_assert(sizeof(PrimaryHit)==32);

struct ShadowStats {
    std::uint64_t primary_hits{},secondary_hits{},shadow_tested{},
                  shadow_blocked{},shadow_clear{},positive_samples{};
    ShadowStats& operator+=(const ShadowStats& v) {
        primary_hits+=v.primary_hits;secondary_hits+=v.secondary_hits;
        shadow_tested+=v.shadow_tested;shadow_blocked+=v.shadow_blocked;
        shadow_clear+=v.shadow_clear;positive_samples+=v.positive_samples;
        return *this;
    }
};
struct Capture {
    std::uint32_t width{},height{},spp{};
    std::uint64_t seed{};
    std::vector<PrimaryHit> primary;
    // Linear single-channel values; PFM exporter repeats each into RGB.
    std::vector<float> direct,indirect,total;
    ShadowStats counts{};
};
inline std::uint64_t splitmix64(std::uint64_t& state) noexcept {
    state+=0x9e3779b97f4a7c15ULL;
    auto value=state;
    value=(value^(value>>30U))*0xbf58476d1ce4e5b9ULL;
    value=(value^(value>>27U))*0x94d049bb133111ebULL;
    return value^(value>>31U);
}
inline double random01(std::uint64_t& state) noexcept {
    return double(splitmix64(state)>>11U)*(1.0/9007199254740992.0);
}
inline b::Vec3 vec(const std::array<float,4>& p) noexcept {
    return {p[0],p[1],p[2]};
}
inline b::Vec3 forward(b::Vec3 normal,b::Vec3 incoming) noexcept {
    normal=b::normalize(normal);
    return b::dot(normal,incoming*-1.0F)<0.0F?normal*-1.0F:normal;
}
inline b::Vec3 camera_ray(const FrameParams& p,std::uint32_t x,std::uint32_t y,
                          std::uint32_t w,std::uint32_t h) noexcept {
    const float nx=2.0F*(float(x)+0.5F)/float(w)-1.0F;
    const float ny=1.0F-2.0F*(float(y)+0.5F)/float(h);
    return b::normalize(vec(p.camera_forward_far)+
        vec(p.camera_right_tan_x)*(nx*p.camera_right_tan_x[3])+
        vec(p.camera_up_tan_y)*(ny*p.camera_up_tan_y[3]));
}
inline b::Vec3 bounce_ray(b::Vec3 normal,double u1,double u2) noexcept {
    constexpr double pi=3.1415926535897932384626433832795;
    const float radius=std::sqrt(float(u1));
    const float phi=float(2.0*pi*u2);
    const float x=radius*std::cos(phi),y=radius*std::sin(phi);
    const float z=std::sqrt(std::max(0.0F,1.0F-radius*radius));
    const b::Vec3 helper=std::abs(normal.z)<0.999F?
        b::Vec3{0,0,1}:b::Vec3{1,0,0};
    const auto tangent=b::normalize(b::cross(helper,normal));
    return b::normalize(tangent*x+b::cross(normal,tangent)*y+normal*z);
}
inline double lambert(const b::SoftwareBvh& bvh,const FrameParams& p,
                      b::Vec3 position,b::Vec3 normal,ShadowStats& counts) {
    constexpr double pi=3.1415926535897932384626433832795;
    const auto to_light=vec(p.light_pos_interval)-position;
    const float d2=b::dot(to_light,to_light);
    if(!std::isfinite(d2)||d2<=1.e-12F)return 0;
    const float d=std::sqrt(d2);
    const auto direction=to_light/d;
    const float cosine=std::max(0.0F,b::dot(normal,direction));
    if(cosine<=0)return 0;
    const float epsilon=std::max(b::kRayTMin*8.0F,p.camera_pos_near[3]*0.02F);
    const float tmax=d-std::max(b::kRayTMin*16.0F,p.camera_pos_near[3]*0.04F);
    if(tmax>b::kRayTMin) {
        ++counts.shadow_tested;
        if(bvh.trace({position+normal*epsilon,direction,tmax}).hit) {
            ++counts.shadow_blocked;
            return 0;
        }
        ++counts.shadow_clear;
    }
    const float scale=std::max(p.light_pos_interval[3],1.e-6F);
    const float attenuation=(scale*scale)/(scale*scale+d2);
    return double(cosine*attenuation)/pi;
}
inline Capture capture_cpu(const std::vector<b::Triangle>& triangles,
                           const FrameParams& p,std::uint32_t width,
                           std::uint32_t height,std::uint32_t spp,
                           std::uint64_t seed,std::uint32_t max_bounces=8) {
    if(!width||!height||!spp||!max_bounces||
       std::uint64_t(width)*height>100'000'000ULL)
        throw std::invalid_argument("invalid N007 capture dimensions/spp/bounces");
    const auto n=std::size_t(width)*height;
    Capture out{};out.width=width;out.height=height;out.spp=spp;out.seed=seed;
    out.primary.resize(n);out.direct.resize(n);out.indirect.resize(n);out.total.resize(n);
    const b::SoftwareBvh bvh(triangles);
    std::atomic<std::uint32_t> row{0};
    const auto worker_count=std::max(1U,std::thread::hardware_concurrency());
    std::vector<ShadowStats> worker_stats(worker_count);
    std::vector<std::thread> workers;
    workers.reserve(worker_count);
    for(std::uint32_t worker=0;worker<worker_count;++worker) {
        workers.emplace_back([&,worker] {
            auto& counters=worker_stats[worker];
            for(;;) {
                const auto y=row.fetch_add(1);
                if(y>=height)return;
                for(std::uint32_t x=0;x<width;++x) {
                    const auto pixel=std::size_t(y)*width+x;
                    const auto direction=camera_ray(p,x,y,width,height);
                    const auto origin=vec(p.camera_pos_near);
                    const auto first=bvh.trace({origin,direction,p.camera_forward_far[3]});
                    if(!first.hit)continue;
                    out.primary[pixel].normal_t={
                        first.normal.x,first.normal.y,first.normal.z,first.t};
                    out.primary[pixel].metadata={
                        first.primitive_id,first.material_id,first.instance_id,1};
                    counters.primary_hits+=spp;
                    const auto position=origin+direction*first.t;
                    const auto normal=forward(first.normal,direction);
                    double sum_direct=0,sum_indirect=0;
                    for(std::uint32_t sample=0;sample<spp;++sample) {
                        std::uint64_t rng=seed ^
                            (std::uint64_t(pixel)+1ULL)*0xd6e8feb86659fd93ULL ^
                            (std::uint64_t(sample)+1ULL)*0xa5a3564e27f8862bULL;
                        const auto direct=lambert(bvh,p,position,normal,counters);
                        double indirect=0;
                        auto pos=position;
                        auto nrm=normal;
                        for(std::uint32_t bounce=1;bounce<max_bounces;++bounce) {
                            const auto ray=bounce_ray(nrm,random01(rng),random01(rng));
                            const float epsilon=std::max(
                                b::kRayTMin*8.0F,p.camera_pos_near[3]*0.02F);
                            const auto ray_origin=pos+nrm*epsilon;
                            const auto hit=bvh.trace({
                                ray_origin,ray,p.camera_forward_far[3]});
                            if(!hit.hit)break;
                            ++counters.secondary_hits;
                            pos=ray_origin+ray*hit.t;
                            nrm=forward(hit.normal,ray);
                            indirect+=lambert(bvh,p,pos,nrm,counters);
                        }
                        sum_direct+=direct;
                        sum_indirect+=indirect;
                        if(direct+indirect>0)++counters.positive_samples;
                    }
                    out.direct[pixel]=float(sum_direct/double(spp));
                    out.indirect[pixel]=float(sum_indirect/double(spp));
                    out.total[pixel]=float((sum_direct+sum_indirect)/double(spp));
                }
            }
        });
    }
    for(auto& worker:workers)worker.join();
    for(const auto& item:worker_stats)out.counts+=item;
    return out;
}
} // namespace phos::gi::research::n007

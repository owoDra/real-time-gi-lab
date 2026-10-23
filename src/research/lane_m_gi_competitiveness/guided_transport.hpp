// 015 CPU candidate kernel. Standalone; never linked into the Renderer.
#pragma once
#include "n008_oracle.hpp"
#include <numeric>

namespace phos::gi::research::m001guide {
namespace o = phos::gi::research::n008;
using o::V3;
constexpr unsigned kBins=64, kGrid=8, kCells=512, kDepths=7;
constexpr std::uint32_t kMass=1u<<24;
constexpr double kArea=4*o::kPi/kBins;
using Weights=std::array<double,kBins>;
using Cdf=std::array<std::uint32_t,kBins>;
inline void require(bool ok,const char* msg) {if(!ok)throw std::runtime_error(msg);}
inline void valid_unit(V3 w) {
    require(std::isfinite(w.x)&&std::isfinite(w.y)&&std::isfinite(w.z)
            &&std::abs(o::dot(w,w)-1)<1e-10,"guide invalid unit vector");
}
inline Cdf quantize(const Weights& weights) {
    double largest=0;
    for(double v:weights) {require(std::isfinite(v)&&v>=0,"invalid guide weight");largest=std::max(largest,v);}
    Cdf result{};
    if(largest==0) {for(unsigned b=0;b<kBins;++b)result[b]=(b+1)*(kMass/kBins);return result;}
    long double sum=0;for(double v:weights)sum+=static_cast<long double>(v)/largest;
    std::array<long double,kBins> frac{};
    std::array<unsigned,kBins> order{};std::iota(order.begin(),order.end(),0);
    std::uint64_t used=0;
    for(unsigned b=0;b<kBins;++b) {
        const long double raw=(static_cast<long double>(weights[b])/largest)*kMass/sum;
        result[b]=std::uint32_t(std::floor(raw));frac[b]=raw-result[b];used+=result[b];
    }
    require(used<=kMass && kMass-used<=kBins,"guide apportionment overflow");
    std::stable_sort(order.begin(),order.end(),[&](unsigned a,unsigned b){return frac[a]>frac[b];});
    for(unsigned i=0;i<kMass-used;++i)++result[order[i]];
    for(unsigned b=1;b<kBins;++b)result[b]+=result[b-1];
    require(result.back()==kMass,"guide CDF mass mismatch");return result;
}
inline void validate(const Cdf& cdf) {
    require(cdf.back()==kMass&&std::is_sorted(cdf.begin(),cdf.end()),"invalid guide CDF");
}
inline std::uint32_t mass(const Cdf& cdf,unsigned b) {
    require(b<kBins,"invalid guide bin");return cdf[b]-(b?cdf[b-1]:0);
}
inline unsigned choose(const Cdf& cdf,std::uint32_t u24) {
    require(u24<kMass,"invalid guide categorical draw");
    const auto at=unsigned(std::upper_bound(cdf.begin(),cdf.end(),u24)-cdf.begin());
    require(at<kBins&&mass(cdf,at)>0,"empty guide bin selected");return at;
}
inline V3 bin_direction(unsigned bin,double u,double v) {
    require(bin<kBins&&u>0&&u<1&&v>0&&v<1,"invalid within-bin draw");
    const double z=-1+2*((bin/8)+u)/8, phi=2*o::kPi*((bin%8)+v)/8;
    const double r=std::sqrt(std::max(0.0,1-z*z));return {r*std::cos(phi),r*std::sin(phi),z};
}
inline unsigned direction_bin(V3 w) {
    valid_unit(w);double phi=std::atan2(w.y,w.x);if(phi<0)phi+=2*o::kPi;
    const unsigned iz=std::min(7u,unsigned(std::max(0.0,std::floor((w.z+1)*4))));
    const unsigned ip=std::min(7u,unsigned(phi*4/o::kPi));return iz*8+ip;
}
inline double density(const Cdf& cdf,V3 w) {return double(mass(cdf,direction_bin(w)))/(kMass*kArea);}
inline double mixed_density(const Cdf& cdf,V3 n,V3 w) {
    valid_unit(n);return .5*std::max(0.0,o::dot(n,w))/o::kPi+.5*density(cdf,w);
}
struct Draw {V3 direction;double pdf{},weight{};bool null{};};
inline Draw draw(const Cdf& cdf,V3 n,bool guided,std::uint32_t category,double u,double v) {
    valid_unit(n);
    const V3 w=guided?bin_direction(choose(cdf,category),u,v):o::Oracle::cosine_sample(n,u,v);
    const double cosine=std::max(0.0,o::dot(n,w));
    const double q=mixed_density(cdf,n,w);
    require(std::isfinite(q)&&q>0,"invalid sampled mixture density");
    const double weight=cosine/(o::kPi*q);
    require(std::isfinite(weight)&&weight>=0&&weight<=2+1e-12,"invalid mixture throughput");
    return {w,q,weight,cosine==0};
}
// Open midpoint draws with23bits: even float32 cannot round the maximum to1.
inline double open23(std::uint64_t word) {return (double(word>>41)+.5)/(1u<<23);}

struct Counts {std::uint64_t closest{},shadow{},nulls{};};
struct Surface {V3 origin,normal;std::uint32_t primitive{};};
class Transport {
public:
    const o::Scene& scene;
    o::Oracle oracle;
    o::Bvh bvh;
    explicit Transport(const o::Scene& s):scene(s),oracle(s),bvh(s.triangles) {
        require(s.width==320&&s.height==180&&s.max_bounces==8&&s.sampling==o::Sampling::Center
                &&s.falloff==o::Falloff::N001Soft&&!s.secondary_far_camera&&!s.points.empty(),"015 physical scene unsupported");
        for(const auto& m:s.materials)require(m.two_sided&&m.rho==o::Rgb{1,1,1}&&m.emit==o::Rgb{0,0,0},"015 BF-P material differs");
    }
    bool trace(o::Ray ray,double near,double far,std::uint32_t ignore,Surface& surface,Counts& count,
               o::PrimaryRecord* record=nullptr) const {
        ++count.closest;const auto hit=bvh.closest(ray,near,far,ignore);if(!hit.hit())return false;
        const auto& t=scene.triangles[hit.tri];V3 n=o::normalize(o::cross(t.v1-t.v0,t.v2-t.v0));
        const bool front=o::dot(n,ray.dir)<0;
        if(record)*record={hit.t,hit.tri,front?1u:0u};
        if(!front)n=n*-1;
        const V3 pos=oracle.nudge_inside(t,ray.origin+ray.dir*hit.t);
        surface={pos+n*oracle.offset(),n,hit.tri};return true;
    }
    double direct(const Surface& s,o::Xoshiro256& rng,Counts& count) const {
        o::RenderCounters cnt{};const auto value=oracle.direct(s.origin,s.normal,s.primitive,rng,cnt);
        count.shadow+=cnt.shadow_tests;
        require(value[0]==value[1]&&value[0]==value[2]&&std::isfinite(value[0])&&value[0]>=0,"invalid grey direct");
        return value[0]/o::kPi;
    }
};

class Field {
public:
    V3 lo,extent;
    std::vector<Weights> weights;
    std::vector<Cdf> cdf;
    Counts training;
    explicit Field(const o::Scene& scene):weights(kCells*kDepths),cdf(kCells*kDepths) {
        require(!scene.triangles.empty(),"empty guide scene");
        o::Aabb box;for(const auto& t:scene.triangles){box.grow(t.v0);box.grow(t.v1);box.grow(t.v2);}
        lo=box.lo;extent=box.hi-box.lo;const double eps=1e-9*std::max(1.0,o::length(extent));
        if(extent.x==0)extent.x=eps;if(extent.y==0)extent.y=eps;if(extent.z==0)extent.z=eps;
    }
    V3 center(unsigned cell) const {
        return lo+V3{extent.x*((cell%8)+.5)/8,extent.y*(((cell/8)%8)+.5)/8,extent.z*((cell/64)+.5)/8};
    }
    unsigned cell(V3 p) const {
        const auto axis=[](double x,double low,double e){return unsigned(std::clamp(std::floor((x-low)*8/e),0.0,7.0));};
        require(std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z),"nonfinite guide position");
        return axis(p.x,lo.x,extent.x)+8*axis(p.y,lo.y,extent.y)+64*axis(p.z,lo.z,extent.z);
    }
    const Cdf& lookup(V3 p,unsigned remaining) const {
        require(remaining>=1&&remaining<=kDepths,"invalid guide remaining depth");return cdf[cell(p)*kDepths+remaining-1];
    }
    void train(const Transport& transport) {
        constexpr std::uint64_t seed=0x475549444531ULL;
        for(unsigned c=0;c<kCells;++c)for(unsigned b=0;b<kBins;++b)for(unsigned j=0;j<2;++j) {
            o::Xoshiro256 rng(seed,c,b*2+j);
            const double u=open23(rng.next()),v=open23(rng.next());
            o::Ray ray{center(c),bin_direction(b,u,v)};unsigned self=~0u;double value=0;
            for(unsigned d=0;d<kDepths;++d) {
                Surface hit;
                if(transport.trace(ray,0,o::kInf,self,hit,training)) {
                    value+=transport.direct(hit,rng,training);self=hit.primitive;
                    const double a=open23(rng.next()),z=open23(rng.next());
                    ray={hit.origin,o::Oracle::cosine_sample(hit.normal,a,z)};
                } else {
                    for(unsigned tail=d;tail<kDepths;++tail)weights[c*kDepths+tail][b]+=value*.5;
                    break;
                }
                weights[c*kDepths+d][b]+=value*.5;
            }
        }
        for(unsigned at=0;at<cdf.size();++at){cdf[at]=quantize(weights[at]);validate(cdf[at]);}
    }
};

inline double render_indirect(const Transport& transport,const Field& field,Surface current,
                              unsigned depth,bool guided,o::Xoshiro256& rng,Counts& counts) {
    require(depth==2||depth==8,"invalid015depth");double value=0,throughput=1;
    for(unsigned vertex=1;vertex<depth;++vertex) {
        V3 wi;
        if(guided) {
            const auto branch=rng.next(),category=rng.next();
            const double u=open23(rng.next()),v=open23(rng.next());
            const auto d=draw(field.lookup(current.origin,depth-vertex),current.normal,
                              (branch&1)!=0,std::uint32_t(category>>40),u,v);
            if(d.null){++counts.nulls;break;}wi=d.direction;throughput*=d.weight;
        } else {const double u=open23(rng.next()),v=open23(rng.next());wi=o::Oracle::cosine_sample(current.normal,u,v);}
        Surface next;
        if(!transport.trace({current.origin,wi},0,o::kInf,current.primitive,next,counts))break;
        value+=throughput*transport.direct(next,rng,counts);current=next;
    }
    require(std::isfinite(value)&&value>=0,"invalid015path radiance");return value;
}
} // namespace

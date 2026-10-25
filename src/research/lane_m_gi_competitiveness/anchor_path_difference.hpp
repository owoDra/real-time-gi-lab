// 031 standalone physical paired paths. Not part of the Renderer build.
#pragma once
#include "anchor_counted_oracle.hpp"
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <numeric>

namespace phos::gi::research::m001anchor {
namespace p=phos::gi::research::m001anchor_physical;
namespace fs=std::filesystem;
static_assert(sizeof(p::PrimaryRecord)==16&&sizeof(p::V3)==24&&sizeof(double)==8);
constexpr unsigned kPairs=16,kAbsolute=1024;
constexpr std::uint64_t kBankDomain=0xa031a031a031a031ULL;
constexpr std::array<std::uint64_t,4> kSeeds{305419896ULL,2596069104ULL,81985529216486895ULL,18364758544493064720ULL};
inline void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
struct Sample {double direct{},indirect{};std::uint64_t closest{},shadow{};p::PrimaryRecord primary;};
inline Sample sample(const p::Oracle& oracle,unsigned width,unsigned pixel,p::Xoshiro256& rng) {
    p::Rgb values[p::kComponents];p::RenderCounters counts;Sample result;
    oracle.sample(pixel%width,pixel/width,rng,values,counts,&result.primary);
    for(unsigned k=0;k<p::kComponents;++k){
        require(values[k][0]==values[k][1]&&values[k][0]==values[k][2]&&
                std::isfinite(values[k][0])&&values[k][0]>=0,"031 invalid grey physical path");
    }
    require(values[p::kEmission][0]==0,"031 emission unsupported");
    result.direct=values[p::kDirect][0];result.indirect=values[p::kIndirect][0];
    result.closest=counts.closest_queries;result.shadow=counts.shadow_tests;return result;
}
inline std::array<Sample,2> pair(const p::Oracle& oracle,unsigned width,unsigned pixel,unsigned anchor,
                                std::uint64_t seed,unsigned index) {
    p::Xoshiro256 rng(seed,pixel,index);auto local_rng=rng,anchor_rng=rng;
    return {sample(oracle,width,pixel,local_rng),sample(oracle,width,anchor,anchor_rng)};
}
inline double estimate(const std::vector<double>& absolute,const std::vector<double>& local,
                       const std::vector<double>& paired) {
    require(absolute.size()==kAbsolute&&local.size()==kPairs&&paired.size()==kPairs,"031 split mismatch");
    double bank=0,residual=0;
    for(double v:absolute){require(std::isfinite(v)&&v>=0,"031 invalid absolute sample");bank+=v;}
    for(unsigned j=0;j<kPairs;++j){
        require(std::isfinite(local[j])&&std::isfinite(paired[j])&&local[j]>=0&&paired[j]>=0,
                "031 invalid paired physical sample");residual+=local[j]-paired[j];
    }
    return bank/kAbsolute+residual/kPairs;
}
inline void validate_scene(const p::Scene& scene) {
    require(scene.width==320&&scene.height==180&&(scene.max_bounces==2||scene.max_bounces==8)
            &&scene.sampling==p::Sampling::Center&&scene.falloff==p::Falloff::N001Soft
            &&!scene.secondary_far_camera&&!scene.points.empty(),"031 unsupported physical boundary");
    for(const auto& m:scene.materials)require(m.two_sided&&m.rho==p::Rgb{1,1,1}&&m.emit==p::Rgb{0,0,0},
                                          "031 unsupported material");
    for(const auto& light:scene.points)require(light.intensity[0]==light.intensity[1]&&light.intensity[0]==light.intensity[2],
                                              "031 unsupported colored light");
}
template<class T>void save(const fs::path& path,const std::vector<T>& values) {
    require(!fs::exists(path),"031 payload exists");std::ofstream stream(path,std::ios::binary);
    require(bool(stream),"031 payload open");stream.write(reinterpret_cast<const char*>(values.data()),values.size()*sizeof(T));
    require(bool(stream),"031 payload write");
}
template<class T>std::vector<T> load(const fs::path& path,std::size_t count) {
    require(fs::file_size(path)==count*sizeof(T),"031 input payload size");std::vector<T> values(count);
    std::ifstream stream(path,std::ios::binary);stream.read(reinterpret_cast<char*>(values.data()),values.size()*sizeof(T));
    require(bool(stream),"031 input payload read");return values;
}
inline void geometry(const p::Scene& scene,const fs::path& out) {
    p::Oracle oracle(scene);p::Bvh bvh(scene.triangles);const unsigned size=scene.width*scene.height;
    std::vector<p::PrimaryRecord> primary(size);std::vector<p::V3> origins(size),normals(size,p::V3{0,0,1}),vertices;
    for(unsigned id=0;id<size;++id){
        const auto ray=oracle.primary_ray(id%scene.width,id/scene.width,.5,.5);
        const auto hit=bvh.closest(ray,scene.camera.near,scene.camera.far,~0u);if(!hit.hit())continue;
        const auto& triangle=scene.triangles[hit.tri];auto normal=p::normalize(p::cross(triangle.v1-triangle.v0,triangle.v2-triangle.v0));
        const bool front=p::dot(normal,ray.dir)<0;if(!front)normal=normal*-1;
        primary[id]={hit.t,hit.tri,front?1u:0u};normals[id]=normal;
        origins[id]=oracle.nudge_inside(triangle,ray.origin+ray.dir*hit.t)+normal*oracle.offset();
    }
    for(const auto& t:scene.triangles){vertices.push_back(t.v0);vertices.push_back(t.v1);vertices.push_back(t.v2);}
    save(out/"primary.bin",primary);save(out/"origins.f64",origins);save(out/"normals.f64",normals);save(out/"vertices.f64",vertices);
    std::ofstream report(out/"geometry.json");report<<"{\"complete\":true,\"pixels\":"<<size<<",\"closest_queries\":"<<size
        <<",\"gpu_executed\":false,\"radiance_sampled\":false}\n";require(bool(report),"031 geometry receipt write");
}
inline void paths(const p::Scene& scene,const fs::path& geo,const fs::path& out) {
    p::Oracle oracle(scene);const unsigned size=scene.width*scene.height;
    const auto groups=load<std::int64_t>(geo/"groups.i64",size);
    const auto primary=load<p::PrimaryRecord>(geo/"primary.bin",size);
    const auto count=fs::file_size(geo/"anchors.u32")/sizeof(std::uint32_t);
    require(count>0&&count<=size,"031 anchor count");const auto anchors=load<std::uint32_t>(geo/"anchors.u32",count);
    std::vector<std::vector<unsigned>> members(count);unsigned active=0;
    for(unsigned id=0;id<size;++id){
        require(groups[id]>=-1&&groups[id]<std::int64_t(count),"031 group index");
        require((groups[id]>=0)==(primary[id].tri!=0xffffffffu),"031 sky/group mismatch");
        if(groups[id]>=0){members[groups[id]].push_back(id);++active;}
    }
    for(unsigned g=0;g<count;++g)require(!members[g].empty()&&anchors[g]==members[g][members[g].size()/2],"031 nonmedian anchor");
    std::ofstream report(out/"paths.json");report<<std::setprecision(17)<<"{\"complete\":true,\"gpu_executed\":false,\"pixels\":"<<size
        <<",\"active_pixels\":"<<active<<",\"groups\":"<<count<<",\"pairs\":16,\"absolute\":1024,\"rows\":[";
    for(unsigned replicate=0;replicate<4;++replicate){
        const auto seed=kSeeds[replicate];const auto dir=out/("seed-"+std::to_string(replicate));require(fs::create_directory(dir),"031 seed directory exists");
        std::vector<double> absolute(count*kAbsolute),local(size*kPairs),paired(size*kPairs),extra(size*kPairs),direct(size);
        std::vector<std::uint64_t> queries(size*6),bank_queries(count*2);
        for(unsigned g=0;g<count;++g)for(unsigned j=0;j<kAbsolute;++j){
            p::Xoshiro256 rng(seed^kBankDomain,anchors[g],j);const auto value=sample(oracle,scene.width,anchors[g],rng);
            require(value.primary.tri==primary[anchors[g]].tri&&value.primary.t==primary[anchors[g]].t,"031 anchor primary drift");
            absolute[g*kAbsolute+j]=value.indirect;bank_queries[g*2]+=value.closest;bank_queries[g*2+1]+=value.shadow;
        }
        save(dir/"anchor-absolute.f64",absolute);save(dir/"bank-query-counts.u64",bank_queries);
        for(unsigned id=0;id<size;++id){
            if(groups[id]<0)continue;
            for(unsigned j=0;j<kPairs;++j){
                const auto values=pair(oracle,scene.width,id,anchors[groups[id]],seed,j);
                p::Xoshiro256 rng(seed,id,j+kPairs);const auto control=sample(oracle,scene.width,id,rng);
                require(values[0].primary.tri==primary[id].tri&&values[0].primary.t==primary[id].t&&
                        control.primary.tri==primary[id].tri&&control.primary.t==primary[id].t,"031 local primary drift");
                require(values[1].primary.tri==primary[anchors[groups[id]]].tri&&
                        values[1].primary.t==primary[anchors[groups[id]]].t,"031 paired anchor primary drift");
                if(j==0)direct[id]=values[0].direct;
                require(values[0].direct==direct[id]&&control.direct==direct[id],"031 nondeterministic direct");
                local[id*kPairs+j]=values[0].indirect;paired[id*kPairs+j]=values[1].indirect;extra[id*kPairs+j]=control.indirect;
                for(unsigned c=0;c<2;++c){queries[id*6+c]+=c?values[0].shadow:values[0].closest;
                    queries[id*6+2+c]+=c?values[1].shadow:values[1].closest;queries[id*6+4+c]+=c?control.shadow:control.closest;}
            }
            if(id%4096==0)std::cout<<"031 seed "<<replicate<<" pixel "<<id<<"\n"<<std::flush;
        }
        save(dir/"local.f64",local);save(dir/"paired-anchor.f64",paired);save(dir/"extra-local.f64",extra);
        save(dir/"direct.f64",direct);save(dir/"query-counts.u64",queries);
        std::uint64_t local_c=0,local_s=0,paired_c=0,paired_s=0,extra_c=0,extra_s=0,bank_c=0,bank_s=0;
        for(unsigned id=0;id<size;++id){local_c+=queries[id*6];local_s+=queries[id*6+1];paired_c+=queries[id*6+2];paired_s+=queries[id*6+3];extra_c+=queries[id*6+4];extra_s+=queries[id*6+5];}
        for(unsigned g=0;g<count;++g){bank_c+=bank_queries[g*2];bank_s+=bank_queries[g*2+1];}
        report<<(replicate?",":"")<<"{\"seed\":"<<seed<<",\"local_closest\":"<<local_c<<",\"local_shadow\":"<<local_s
            <<",\"paired_closest\":"<<paired_c<<",\"paired_shadow\":"<<paired_s<<",\"extra_closest\":"<<extra_c<<",\"extra_shadow\":"<<extra_s
            <<",\"bank_closest\":"<<bank_c<<",\"bank_shadow\":"<<bank_s<<"}"<<std::flush;
        std::cout<<"031 seed "<<replicate<<" complete\n"<<std::flush;
    }
    report<<"]}\n";require(bool(report),"031 paths receipt write");
}
} // namespace

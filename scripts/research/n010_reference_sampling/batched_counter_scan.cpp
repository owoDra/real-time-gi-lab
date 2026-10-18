// Post-hoc CPU-only localization; original CPU header is copied byte for byte.
#include "n010_rqmc_oracle.hpp"
#include <iomanip>
#include <iostream>
using namespace phos::gi::research::n008;
struct alignas(32) Four {double v[4]{};};
struct alignas(32) GStats {Four sum[4],sum2[4];uint64_t counters[4]{};};
static_assert(sizeof(GStats)==288);
struct Sample {double values[12]{};uint64_t counters[4]{},queries{},nulls{},own{};};
static void array(std::ostream& out,const uint64_t* values,size_t count) {
    out<<'[';for(size_t i=0;i<count;++i){if(i)out<<',';out<<values[i];}out<<']';
}
int main(int argc,char** argv) {try {
    if(argc!=6)return 1;
    N010NetRng::load(argv[1]);std::ifstream in(argv[2]);const Scene scene=parse_scene(in);
    if(scene.width!=320||scene.height!=180||scene.max_bounces!=8)return 2;
    const Oracle oracle(scene);constexpr uint32_t spp=16;constexpr uint64_t seed=305419896;
    const size_t pixels=size_t(scene.width)*scene.height;
    std::vector<GStats> gpu(pixels);std::ifstream g(argv[3],std::ios::binary);
    g.read(reinterpret_cast<char*>(gpu.data()),gpu.size()*sizeof(GStats));if(!g||g.peek()!=EOF)return 3;
    std::vector<std::array<double,24>> baseline(pixels);std::ifstream cpu(argv[4],std::ios::binary);
    cpu.seekg(28);cpu.read(reinterpret_cast<char*>(baseline.data()),baseline.size()*sizeof(baseline[0]));if(!cpu||cpu.peek()!=EOF)return 4;
    std::ofstream out(argv[5]);out<<std::setprecision(17)<<"{\"schema\":\"n010-cpu-counter-scan/1\",\"seed\":"<<seed<<",\"spp\":16,\"rows\":[";
    size_t differences=0;uint64_t global[4]{},gpuGlobal[4]{};
    for(uint32_t pixel=0;pixel<pixels;++pixel) {
        Oracle::PrimaryCache cache;GStats stats;std::array<Sample,16> samples;
        for(uint32_t s=0;s<spp;++s) {
            auto& detail=samples[s];const auto q=oracle.renderer_audit_.bvh_queries;
            const auto n=oracle.renderer_audit_.component_nulls,o=oracle.renderer_audit_.own_checks;
            N010NetRng rng(seed,pixel,s);Rgb comp[kComponents];RenderCounters cnt{};
            oracle.sample_all_split(pixel%320,pixel/320,rng,comp,cnt,nullptr,&cache);
            detail.counters[0]=cnt.primary_hits;detail.counters[1]=cnt.shadow_tests;
            detail.counters[2]=cnt.shadow_blocked;detail.counters[3]=cnt.backface_absorbed;
            detail.queries=oracle.renderer_audit_.bvh_queries-q;detail.nulls=oracle.renderer_audit_.component_nulls-n;
            detail.own=oracle.renderer_audit_.own_checks-o;
            for(int c=0;c<3;++c){double total=0;for(int k=0;k<3;++k){detail.values[k*3+c]=comp[k][c];total+=comp[k][c];}detail.values[9+c]=total;}
            for(int k=0;k<4;++k)for(int c=0;c<3;++c){const double value=detail.values[k*3+c];stats.sum[k].v[c]+=value;stats.sum2[k].v[c]+=value*value;}
            for(int k=0;k<4;++k)stats.counters[k]+=detail.counters[k];
        }
        for(int k=0;k<4;++k)for(int c=0;c<3;++c){const double mean=stats.sum[k].v[c]/spp,m2=stats.sum2[k].v[c]/spp;
            if(std::memcmp(&mean,&baseline[pixel][k*3+c],8)||std::memcmp(&m2,&baseline[pixel][12+k*3+c],8))
                throw std::runtime_error("original CPU baseline mean/moment bits differ");}
        for(int k=0;k<4;++k){global[k]+=stats.counters[k];gpuGlobal[k]+=gpu[pixel].counters[k];}
        if(std::memcmp(stats.counters,gpu[pixel].counters,sizeof stats.counters)) {
            if(differences++)out<<',';out<<"{\"pixel\":"<<pixel<<",\"x\":"<<pixel%320<<",\"y\":"<<pixel/320<<",\"cpu_counters\":";
            array(out,stats.counters,4);out<<",\"gpu_counters\":";array(out,gpu[pixel].counters,4);out<<",\"cpu_samples\":[";
            for(uint32_t s=0;s<spp;++s){if(s)out<<',';const auto& detail=samples[s];out<<"{\"sample\":"<<s<<",\"counters\":";
                array(out,detail.counters,4);out<<",\"queries\":"<<detail.queries<<",\"nulls\":"<<detail.nulls<<",\"own\":"<<detail.own<<",\"components\":[";
                for(int k=0;k<12;++k){if(k)out<<',';out<<detail.values[k];}out<<"]}";}out<<"]}";
        }
    }
    const auto& audit=oracle.renderer_audit_;
    out<<"],\"complete\":true,\"all_cpu_mean_moment_bits_exact\":true,\"pixel_count\":"<<pixels<<",\"differing_pixels\":"<<differences
       <<",\"cpu_counters\":";array(out,global,4);out<<",\"gpu_counters\":";array(out,gpuGlobal,4);
    out<<",\"cpu_audit\":{\"proposal_bvh_queries\":"<<audit.bvh_queries<<",\"component_attempts\":"<<audit.component_attempts
       <<",\"component_nulls\":"<<audit.component_nulls<<",\"own_checks\":"<<audit.own_checks<<"}}\n";
    if(!out)throw std::runtime_error("diagnostic output write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}

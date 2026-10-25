#include "anchor_path_difference.hpp"
#include "n008_oracle.hpp"
namespace a=phos::gi::research::m001anchor;
namespace original=phos::gi::research::n008;
int main(){
 try{
    const std::string text="n008scene 1\nresolution 4 4\ncamera 0 0 1 0 0 -1 0 1 0 .4 .4 0 10\nsampling center\nmax_bounces 8\nfalloff n001_soft 1\nsecondary_far inf\nmaterial s 1 1 1 0 0 0 1\npoint 0 0 1 1 1 1\ntri s -2 -2 0 2 -2 0 2 2 0\ntri s -2 -2 0 2 2 0 -2 2 0\ntri s 2 -2 0 2 -2 3 2 2 3\ntri s 2 -2 0 2 2 3 2 2 0\n";
    std::istringstream input(text),old_input(text);auto scene=a::p::parse_scene(input);auto old_scene=original::parse_scene(old_input);
    unsigned tested=0;bool saw_indirect=false;
    for(unsigned depth:{2u,8u}){
        scene.max_bounces=old_scene.max_bounces=depth;a::p::Oracle oracle(scene);original::Oracle reference(old_scene);
        for(unsigned pixel=0;pixel<16;++pixel)for(unsigned j=0;j<64;++j){
            a::p::Xoshiro256 rng(305419896,pixel,j);original::Xoshiro256 old_rng(305419896,pixel,j);
            const auto value=a::sample(oracle,4,pixel,rng);original::Rgb physical[original::kComponents];original::RenderCounters counts;original::PrimaryRecord primary;
            reference.sample(pixel%4,pixel/4,old_rng,physical,counts,&primary);
            a::require(value.direct==physical[original::kDirect][0]&&value.indirect==physical[original::kIndirect][0],"031 original/count radiance differs");
            a::require(value.primary.t==primary.t&&value.primary.tri==primary.tri&&value.primary.front==primary.front,"031 original/count primary differs");
            a::require(value.shadow==counts.shadow_tests&&value.closest>=1&&value.closest<=depth&&value.shadow<=value.closest,"031 physical counters differ");
            if(depth==2)a::require(value.closest==2,"031 finite two-vertex closest count");
            saw_indirect=saw_indirect||value.indirect>0;++tested;
        }
        for(unsigned j=0;j<128;++j){
            const auto same=a::pair(oracle,4,5,5,1234567,j);
            a::require(same[0].indirect==same[1].indirect&&same[0].closest==same[1].closest&&same[0].shadow==same[1].shadow,"031 identical receiver cancellation");
            const auto shifted=a::pair(oracle,4,5,10,1234567,j);
            a::p::Xoshiro256 local_rng(1234567,5,j),anchor_rng(1234567,5,j);
            const auto local=a::sample(oracle,4,5,local_rng),anchor=a::sample(oracle,4,10,anchor_rng);
            a::require(shifted[0].indirect==local.indirect&&shifted[1].indirect==anchor.indirect&&
                       shifted[0].direct==local.direct&&shifted[1].direct==anchor.direct,"031 coupled marginal mismatch");
        }
    }
    a::require(saw_indirect,"031 physical fixture lacked indirect signal");
    std::vector<double> absolute(a::kAbsolute,2),local(a::kPairs,3),paired(a::kPairs,3);
    a::require(a::estimate(absolute,local,paired)==2,"031 constant/cancellation estimator");
    std::fill(absolute.begin(),absolute.end(),0);std::fill(local.begin(),local.end(),0);std::fill(paired.begin(),paired.end(),1);
    a::require(a::estimate(absolute,local,paired)==-1,"031 signed difference clipped");
    bool rejected=false;local[0]=-1;try{a::estimate(absolute,local,paired);}catch(...){rejected=true;}
    a::require(rejected,"031 negative physical samples accepted");
    rejected=false;local[0]=0;local.pop_back();try{a::estimate(absolute,local,paired);}catch(...){rejected=true;}
    a::require(rejected,"031 malformed split accepted");
    scene.triangles.clear();a::p::Oracle empty(scene);a::p::Xoshiro256 rng(1,0,0);const auto miss=a::sample(empty,4,0,rng);
    a::require(miss.indirect==0&&miss.direct==0&&miss.closest==1&&miss.shadow==0,"031 empty-scene miss/count");
    std::cout<<"{\"all_pass\":true,\"original_counted_path_comparisons\":"<<tested
             <<",\"identical_receiver_pairs\":256,\"shifted_marginal_pairs\":256,\"physical_bounce_boundaries\":[2,8],\"gpu_executed\":false}\n";
    return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}

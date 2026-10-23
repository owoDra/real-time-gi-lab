// Executable mathematical contract tests, CPU only; no Vulkan headers/linkage.
#include "ddgi_contract.hpp"
#include <iostream>

int main() {
    using m001::require;
    // Verify exact ownership of every ray for non-divisible and upper-bound grids.
    for(uint32_t total:{1u,63u,64u,4095u,4096u,4097u,23u*23u*23u*512u,24u*24u*24u*512u}) {
        auto tiles=m001::tiles(total);std::vector<uint8_t> visits(total);uint32_t launched=0;
        for(auto t:tiles){require(t.begin==launched && t.count>0 && t.count<=4096,"tile hole/overlap");
            for(uint32_t thread=0;thread<((t.count+63)/64)*64;++thread)if(thread<t.count){require(++visits.at(t.begin+thread)==1,"duplicate ray write");}
            launched+=t.count;}
        require(launched==total && std::all_of(visits.begin(),visits.end(),[](auto n){return n==1;}),"incomplete ray coverage");
    }
    // Model a transport recurrence with a distinct symbolic path-degree per bounce.
    // Reading a stale atlas, aliasing the write target or skipping a depth must fail.
    for(uint32_t depth:{1u,2u,8u}) {
        std::array<std::vector<uint32_t>,2> atlas;uint32_t completed=0;
        auto plan=m001::stages(depth);
        for(auto s:plan){require(s.write!=s.read && s.previous_ready==(s.ordinal>0),"feedback alias/read-before-ready");
            auto previous=atlas[s.read];auto& target=atlas[s.write];target.clear();target.push_back(1);
            if(s.previous_ready)for(auto degree:previous)target.push_back(degree+1);
            require(atlas[s.read]==previous,"previous atlas mutation");
            require(target.size()==s.ordinal+1,"stale/incorrect-depth transport");
            for(uint32_t k=0;k<target.size();++k)require(target[k]==k+1,"missing/duplicated transport order");++completed;
        }
        require(completed==depth-1,"finite stage count");
    }
    for(uint32_t bad:{0u,3u,7u,9u,UINT32_MAX}){bool rejected=false;try{(void)m001::stages(bad);}catch(...){rejected=true;}require(rejected,"unsupported depth accepted");}
    std::cout<<"CPU ray ownership, finite symbolic transport and refusal PASS; GPU NOT RUN\n";
}

#pragma once
#include "ddgi_contract.hpp"
#include <cstring>

namespace m001_dynamic {
inline std::vector<uint32_t> moved(const m001::State& a,const m001::State& z) {
    m001::require(a.width==z.width && a.height==z.height && a.triangles.size()==z.triangles.size(),"stable viewport/topology required");
    std::vector<uint32_t> out;
    for(size_t j=0;j<a.triangles.size();++j){const auto& x=a.triangles[j];const auto& y=z.triangles[j];
        m001::require(x.primitive==y.primitive && x.material==y.material && x.instance==y.instance && x.two_sided==y.two_sided,"dynamic metadata/topology unsupported");
        if(x.v0!=y.v0 || x.v1!=y.v1 || x.v2!=y.v2)out.push_back(uint32_t(j));}
    return out;
}
struct Step {uint32_t ordinal,state_index,moved_primitives;bool reset_both_atlases;};
inline std::array<Step,4> plan(const m001::State& source,const m001::State& target) {
    auto changed=moved(source,target);
    m001::require(!changed.empty() || std::memcmp(&source.frame,&target.frame,sizeof source.frame)!=0,"no-op transition refused");
    return {{{0,0,0,true},{1,1,uint32_t(changed.size()),true},{2,1,0,true},{3,0,uint32_t(changed.size()),true}}};
}
}

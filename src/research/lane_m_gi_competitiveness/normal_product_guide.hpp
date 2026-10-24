// 016 standalone CPU proposal. The immutable015 kernel supplies transport/PDF.
#pragma once
#include "guided_transport.hpp"
namespace phos::gi::research::m001product {
namespace g=phos::gi::research::m001guide;
namespace o=phos::gi::research::n008;
inline g::Cdf product(const g::Weights& incoming,o::V3 normal) {
    g::valid_unit(normal);g::Weights weights{};
    for(unsigned b=0;b<g::kBins;++b) {
        g::require(std::isfinite(incoming[b])&&incoming[b]>=0,"016 invalid incoming weight");
        weights[b]=incoming[b]*std::max(0.0,o::dot(normal,g::bin_direction(b,.5,.5)));
    }
    return g::quantize(weights);
}
inline g::Cdf lookup(const g::Field& field,o::V3 p,o::V3 normal,unsigned remaining) {
    g::require(remaining>=1&&remaining<=g::kDepths,"016 invalid remaining depth");
    return product(field.weights[field.cell(p)*g::kDepths+remaining-1],normal);
}
inline double render(const g::Transport& transport,const g::Field& field,g::Surface current,
                     unsigned depth,o::Xoshiro256& rng,g::Counts& counts) {
    g::require(depth==2||depth==8,"016 invalid depth");double value=0,throughput=1;
    for(unsigned vertex=1;vertex<depth;++vertex) {
        const auto cdf=lookup(field,current.origin,current.normal,depth-vertex);
        const auto branch=rng.next(),category=rng.next();
        const double u=g::open23(rng.next()),v=g::open23(rng.next());
        const auto d=g::draw(cdf,current.normal,(branch&1)!=0,std::uint32_t(category>>40),u,v);
        if(d.null){++counts.nulls;break;}
        throughput*=d.weight;g::Surface next;
        if(!transport.trace({current.origin,d.direction},0,o::kInf,current.primitive,next,counts))break;
        value+=throughput*transport.direct(next,rng,counts);current=next;
    }
    g::require(std::isfinite(value)&&value>=0,"016 invalid radiance");return value;
}
} // namespace

// Tests of the actual015kernel, including analytic mixture expectations.
#include "guided_transport.hpp"
#include <iostream>
namespace g=phos::gi::research::m001guide;
namespace o=phos::gi::research::n008;
unsigned tests=0;
void expect(bool condition,const char* label){g::require(condition,label);++tests;}
template<class F>bool rejects(F f){try{f();return false;}catch(const std::exception&){return true;}}
int main(){try{
    g::Weights zeros{};auto uniform=g::quantize(zeros);g::validate(uniform);
    expect(uniform.back()==g::kMass,"uniform total");
    bool ok=true;for(unsigned b=0;b<64;++b)ok&=g::mass(uniform,b)==g::kMass/64;
    expect(ok,"uniform masses");
    g::Weights concentrated{};concentrated[17]=1;const auto point=g::quantize(concentrated);
    expect(g::choose(point,0)==17&&g::choose(point,g::kMass-1)==17,"categorical empty bins/boundaries");
    for(unsigned i=0;i<64;++i)concentrated[i]=double(i%7);
    const auto arbitrary=g::quantize(concentrated);g::validate(arbitrary);
    std::array<std::uint32_t,64> observed{};
    for(std::uint32_t u=0;u<g::kMass;++u)++observed[g::choose(arbitrary,u)];
    ok=true;for(unsigned b=0;b<64;++b)ok&=observed[b]==g::mass(arbitrary,b);
    expect(ok,"exhaustive2^24categorical draws equal actual PDF masses");
    auto bad=concentrated;bad[0]=-1;expect(rejects([&]{g::quantize(bad);}),"negative weight rejected");
    bad[0]=o::kInf;expect(rejects([&]{g::quantize(bad);}),"nonfinite weight rejected");
    bad[0]=std::numeric_limits<double>::quiet_NaN();expect(rejects([&]{g::quantize(bad);}),"NaN weight rejected");
    bad.fill(std::numeric_limits<double>::max());expect(g::quantize(bad)==uniform,"huge finite weights avoid sum overflow");
    auto broken=uniform;broken[3]=0;expect(rejects([&]{g::validate(broken);}),"nonmonotone CDF rejected");
    broken=uniform;--broken.back();expect(rejects([&]{g::validate(broken);}),"wrong total rejected");
    expect(rejects([&]{g::choose(uniform,g::kMass);}),"out-of-range categorical rejected");
    ok=true;for(unsigned b=0;b<64;++b)for(double u:{.0001,.5,.9999})for(double v:{.0001,.5,.9999}) {
        const auto w=g::bin_direction(b,u,v);ok&=g::direction_bin(w)==b&&std::abs(g::density(uniform,w)-1/(4*o::kPi))<1e-15;
    }expect(ok,"sphere bin partition and uniform density");
    expect(rejects([&]{g::bin_direction(0,0,.5);})&&rejects([&]{g::bin_direction(64,.5,.5);}),"invalid bin/endpoints rejected");
    expect(rejects([&]{g::density(uniform,{0,0,2});}),"nonunit PDF input rejected");
    expect(double(float(g::open23(0)))>0&&float(g::open23(~0ULL))<1,"open23 float32 endpoints");
    // Independent midpoint solid-angle integration. Integrand is cos(theta)/pi,
    // proposal density includes BOTH mixture branches even for cosine draws.
    for(const auto& cdf:{uniform,point,arbitrary}) {
        double norm=0,constant=0,linear=0,max_weight=0;unsigned nulls=0;
        constexpr unsigned nz=256,np=256;
        for(unsigned z=0;z<nz;++z)for(unsigned a=0;a<np;++a){
            const double zz=-1+2*(z+.5)/nz,phi=2*o::kPi*(a+.5)/np;
            const o::V3 w{std::sqrt(1-zz*zz)*std::cos(phi),std::sqrt(1-zz*zz)*std::sin(phi),zz},n{0,0,1};
            const double q=g::mixed_density(cdf,n,w),f=std::max(0.0,zz)/o::kPi;
            norm+=q*4*o::kPi/(nz*np);
            if(q>0){constant+=(f/q)*q*4*o::kPi/(nz*np);linear+=(f*(1+zz)/q)*q*4*o::kPi/(nz*np);}
        }
        expect(std::abs(norm-1)<1e-11,"mixture normalization including null sphere mass");
        expect(std::abs(constant-1)<1e-11&&std::abs(linear-5.0/3)<3e-5,"independent single transition expectation");
        o::Xoshiro256 rng(1234,0,0);
        for(unsigned i=0;i<32768;++i){const auto branch=rng.next(),cat=rng.next();const double u=g::open23(rng.next()),v=g::open23(rng.next());
            const auto d=g::draw(cdf,{0,0,1},branch&1,std::uint32_t(cat>>40),u,v);max_weight=std::max(max_weight,d.weight);nulls+=d.null;
            g::require(std::abs(d.pdf-g::mixed_density(cdf,{0,0,1},d.direction))<1e-15,"sample/evaluate PDF disagree");
        }
        expect(max_weight<=2+1e-12&&nulls>0,"throughput bound and actual retained null events");
    }
    // Two transitions: independently integrate g(w1)=1+z1, g(w2)=1+z2 under
    // cosine measure; product expectation (5/3)^2. Sample the actual kernel.
    double sum=0,sum2=0;o::Xoshiro256 rng(0x12345678,0,0);constexpr unsigned samples=262144;
    for(unsigned i=0;i<samples;++i){double value=1;for(unsigned d=0;d<2;++d){
        const auto branch=rng.next(),cat=rng.next();const double u=g::open23(rng.next()),v=g::open23(rng.next());
        const auto hit=g::draw(arbitrary,{0,0,1},branch&1,std::uint32_t(cat>>40),u,v);
        value*=hit.weight*(1+hit.direction.z);if(hit.null){value=0;break;}
    }sum+=value;sum2+=value*value;}
    const double mean=sum/samples,variance=(sum2-sum*sum/samples)/(samples-1),se=std::sqrt(variance/samples);
    expect(std::abs(mean-25.0/9)<6*se,"actual two-transition estimator analytic expectation within frozen6SE health guard");
    std::cout<<"{\"actual_contract_checks\":"<<tests<<",\"categorical_draws_exhausted\":16777216,\"two_transition_samples\":"<<samples
             <<",\"two_transition_mean\":"<<mean<<",\"two_transition_se\":"<<se<<",\"pass\":true}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

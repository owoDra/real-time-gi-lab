// Actual016 proposal tests; no015 test-suite rerun.
#include "normal_product_guide.hpp"
#include <iomanip>
#include <iostream>
namespace p=phos::gi::research::m001product;
namespace g=phos::gi::research::m001guide;
namespace o=phos::gi::research::n008;
unsigned checks=0;
void expect(bool x,const char* label){g::require(x,label);++checks;}
template<class F>bool rejects(F f){try{f();return false;}catch(const std::exception&){return true;}}
int main(){try{
    g::Weights zero{},flat{},incoming{};flat.fill(1);
    for(unsigned b=0;b<64;++b)incoming[b]=double(1+b%7);
    expect(p::product(zero,{0,0,1})==g::quantize(zero),"016 zero-product fallback");
    const auto front=p::product(flat,{0,0,1}),back=p::product(flat,{0,0,-1});
    bool good=true;for(unsigned b=0;b<64;++b)good&=(g::mass(front,b)>0)==(b>=32)&&(g::mass(back,b)>0)==(b<32);
    expect(good&&front!=back,"016 actual normal reverses product support");
    auto bad=incoming;bad[0]=-1;expect(rejects([&]{p::product(bad,{0,0,1});}),"016 negative incoming rejected");
    bad[0]=o::kInf;expect(rejects([&]{p::product(bad,{0,0,1});}),"016 nonfinite incoming rejected");
    bad[0]=std::numeric_limits<double>::quiet_NaN();expect(rejects([&]{p::product(bad,{0,0,1});}),"016 NaN incoming rejected");
    expect(rejects([&]{p::product(incoming,{0,0,2});}),"016 nonunit normal rejected");
    // Actual field indexing: unique rows at cell0/depth1 and cell511/depth7.
    o::Scene scene;scene.triangles.push_back({{0,0,0},{1,0,1},{0,1,0},0});g::Field field(scene);
    field.weights[0]=flat;field.weights[511*7+6]=incoming;
    expect(p::lookup(field,{-1,-1,-1},{0,0,1},1)==front,"016 clamped cell/remaining1 lookup");
    expect(p::lookup(field,{2,2,2},{0,0,-1},7)==p::product(incoming,{0,0,-1}),"016 clamped cell/remaining7 lookup");
    expect(rejects([&]{p::lookup(field,{0,0,0},{0,0,1},0);})&&rejects([&]{p::lookup(field,{0,0,0},{0,0,1},8);}),"016 invalid depth rejected");
    const std::array<o::V3,3> normals{{{0,0,1},o::normalize({.3,.4,.5}),o::normalize({-.6,.2,-.3})}};
    const o::V3 axis{.3,-.4,.5};bool found_null=false;
    for(const auto n:normals){
        const auto cdf=p::product(incoming,n);g::validate(cdf);g::Weights independent{};
        long double total=0;for(unsigned b=0;b<64;++b){
            const double z=-1+2*((b/8)+.5)/8,phi=2*o::kPi*((b%8)+.5)/8,r=std::sqrt(1-z*z);
            independent[b]=incoming[b]*std::max(0.0,n.x*r*std::cos(phi)+n.y*r*std::sin(phi)+n.z*z);total+=independent[b];
        }
        good=true;for(unsigned b=0;b<64;++b)good&=std::abs(g::mass(cdf,b)-independent[b]/total*g::kMass)<=1+1e-8;
        expect(good,"016 independently computed normal product quantized masses");
        // Independent sphere quadrature, including both branches and null mass.
        constexpr unsigned nz=256,np=256;double norm=0,constant=0,linear=0;
        for(unsigned z=0;z<nz;++z)for(unsigned a=0;a<np;++a){
            const double zz=-1+2*(z+.5)/nz,phi=2*o::kPi*(a+.5)/np,r=std::sqrt(1-zz*zz);
            const o::V3 w{r*std::cos(phi),r*std::sin(phi),zz};
            const double f=std::max(0.0,o::dot(n,w))/o::kPi,q=g::mixed_density(cdf,n,w),da=4*o::kPi/(nz*np);
            const unsigned b=(z/(nz/8))*8+a/(np/8);
            g::require(std::abs(q-(.5*f+.5*double(g::mass(cdf,b))/(g::kMass*g::kArea)))<1e-12,"016 full PDF evaluation differs");
            norm+=q*da;if(q>0){constant+=(f/q)*q*da;linear+=(f*(1+o::dot(w,axis))/q)*q*da;}
        }
        expect(std::abs(norm-1)<1e-4,"016 arbitrary-normal mixture normalization");
        expect(std::abs(constant-1)<1e-4&&std::abs(linear-(1+2*o::dot(n,axis)/3))<1e-4,"016 independent continuous expectation");
        // Every positive-cosine direction has support even in zero guide bins.
        good=true;for(unsigned b=0;b<64;++b){const auto w=g::bin_direction(b,.5,.5);if(o::dot(n,w)>0)good&=g::mixed_density(cdf,n,w)>0;
            if(g::mass(cdf,b)>0)for(double u:{.001,.999})for(double v:{.001,.999}){
                const auto d=g::draw(cdf,n,true,b?cdf[b-1]:0,u,v);
                if(d.null){found_null=true;g::require(d.weight==0&&d.pdf>0,"016 null was discarded or renormalized");}
            }
        }expect(good,"016 cosine mixture keeps complete support");
        o::Xoshiro256 rng(0x160016,0,0);double max_weight=0;good=true;
        for(unsigned i=0;i<32768;++i){const auto branch=rng.next(),cat=rng.next();const double u=g::open23(rng.next()),v=g::open23(rng.next());
            const auto d=g::draw(cdf,n,branch&1,std::uint32_t(cat>>40),u,v);max_weight=std::max(max_weight,d.weight);
            good&=std::abs(d.pdf-g::mixed_density(cdf,n,d.direction))<1e-15;
        }expect(good&&max_weight<=2+1e-12,"016 actual sample/evaluate PDF and throughput bound");
    }
    expect(found_null,"016 tangent-crossing bins retain actual null events");
    // Recompute product at both distinct normals; independent analytic target.
    double sum=0,sum2=0;o::Xoshiro256 rng(0x1600abcd,0,0);constexpr unsigned samples=262144;
    for(unsigned i=0;i<samples;++i){double value=1;for(unsigned step=1;step<=2;++step){
        const auto n=normals[step];const auto cdf=p::product(incoming,n);
        const auto branch=rng.next(),cat=rng.next();const double u=g::open23(rng.next()),v=g::open23(rng.next());
        const auto d=g::draw(cdf,n,branch&1,std::uint32_t(cat>>40),u,v);
        value*=d.weight*(1+o::dot(d.direction,axis));if(d.null){value=0;break;}
    }sum+=value;sum2+=value*value;}
    const double mean=sum/samples,var=(sum2-sum*sum/samples)/(samples-1),se=std::sqrt(var/samples);
    const double exact=(1+2*o::dot(normals[1],axis)/3)*(1+2*o::dot(normals[2],axis)/3);
    expect(std::abs(mean-exact)<6*se,"016 actual two-transition analytic6SE health guard");
    std::cout<<std::setprecision(17)<<"{\"actual_contract_checks\":"<<checks<<",\"pass\":true,\"two_transition_samples\":"<<samples
             <<",\"two_transition_mean\":"<<mean<<",\"two_transition_exact\":"<<exact<<",\"two_transition_se\":"<<se<<"}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

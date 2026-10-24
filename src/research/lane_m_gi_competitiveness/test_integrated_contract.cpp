#include "integrated_safety.hpp"
#include "surface_quadratic_scalar.hpp"
#include <iostream>
namespace q=m001_q019;
int main(int argc,char** argv){
    using namespace m022;
    if(argc==3 && std::string(argv[1])=="--incomplete"){safety_output=argv[2];need(std::filesystem::create_directory(safety_output),"existing synthetic failure");incomplete_fence("synthetic-cpu-contract");}
    unsigned checks=0;
    auto rejects=[&](auto f){bool threw=false;try{f();}catch(const std::exception&){threw=true;}need(threw,"contract expected rejection");checks++;};
    rejects([]{reserve(0);});reserve(cap);checks++;rejects([]{reserve(1);});release(cap);checks++;
    rejects([]{release(1);});rejects([]{reserve(cap+1);});safety_started=Clock::now()-std::chrono::seconds(181);rejects([]{wall_guard();});safety_started=Clock::now();
    q::Storage one;one.camera={0,0,0,1e-4f,0,0,1,100,1,0,0,1,0,1,0,1,1e-4f,1,11,11};auto n=one.size();one.hits.resize(n*8);one.sources.resize(n);
    for(unsigned p=0;p<n;p++){
        float x=2*((float(p%11)+.5f)/11)-1,y=1-2*((float(p/11)+.5f)/11);float t=5*std::sqrt((x*x+y*y)+1);
        one.hits[p*8+2]=std::bit_cast<q::uint>(1.f);one.hits[p*8+3]=std::bit_cast<q::uint>(t);one.hits[p*8+4]=p;one.hits[p*8+5]=0xffffffffu;one.hits[p*8+6]=0;one.hits[p*8+7]=1;
        one.sources[p]=float((p*17)%29)*.03125f;
    }
    auto five=one;five.camera[17]=5;five.sources.clear();for(int image=0;image<5;image++)five.sources.insert(five.sources.end(),one.sources.begin(),one.sources.end());
    one.allocate();five.allocate();q::execute(one);q::execute(five);
    need(one.geometry==five.geometry && one.coefficients==five.coefficients && one.maps==five.maps,"single/five geometry or math differs");checks++;
    for(int image=0;image<5;image++)for(unsigned p=0;p<3*n;p++)need(one.stages[p]==five.stages[image*3*n+p]&&one.unclipped[p]==five.unclipped[image*3*n+p],"single/five image stage differs");checks++;
    std::cout<<"{\"complete\":true,\"actual_new_contracts\":"<<checks<<",\"pixels\":"<<n<<",\"stage_comparisons\":"<<n*3*5*2<<",\"gpu_executed\":false}\n";
}

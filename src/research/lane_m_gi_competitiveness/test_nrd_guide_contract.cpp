#include "nrd_guide_contract.hpp"
#include <iostream>
#include <limits>
using namespace m023;
int main(){unsigned checks=0;auto check=[&](bool x){need(x,"023 C++ contract assertion");checks++;};auto reject=[&](auto f){bool threw=false;try{f();}catch(const std::exception&){threw=true;}check(threw);};
    Camera c{1,2,3,.01f,0,0,1,100,1,0,0,1.2f,0,1,0,.7f,.0001f,1,320,180};auto s=common(c,0,true);
    check(s.resourceSize[0]==320&&s.rectSize[1]==180&&s.accumulationMode==nrd::AccumulationMode::CLEAR_AND_RESTART&&s.denoisingRange==100&&s.timeDeltaBetweenFrames==1000.f/60.f);
    check(common(c,63,false).frameIndex==63&&common(c,63,false).accumulationMode==nrd::AccumulationMode::CONTINUE);
    check(s.worldToViewMatrix[12]==-1&&s.worldToViewMatrix[13]==-2&&s.worldToViewMatrix[14]==-3&&s.viewToClipMatrix[11]==1);
    for(unsigned y:{0u,73u,179u})for(unsigned x:{0u,156u,319u}){
        double nx=2*(double(x)+.5)/320-1,ny=1-2*(double(y)+.5)/180;double vz=7.;double world[]{1+nx*c[11]*vz,2+ny*c[15]*vz,3+vz,1};double v[4]{},clip[4]{};
        for(int r=0;r<4;r++)for(int k=0;k<4;k++)v[r]+=s.worldToViewMatrix[k*4+r]*world[k];for(int r=0;r<4;r++)for(int k=0;k<4;k++)clip[r]+=s.viewToClipMatrix[k*4+r]*v[k];
        check(std::abs((clip[0]/clip[3]*.5+.5)-(double(x)+.5)/320)<1e-7&&std::abs((.5-clip[1]/clip[3]*.5)-(double(y)+.5)/180)<1e-7);
    }
    for(auto change:{std::pair{3,0.f},std::pair{7,.001f},std::pair{11,0.f},std::pair{18,320.5f},std::pair{19,0.f},std::pair{18,4097.f},std::pair{0,std::numeric_limits<float>::infinity()},std::pair{4,1.f}}){auto invalid=c;invalid[change.first]=change.second;reject([&]{common(invalid,0,true);});}
    HitDistance d;reject([&]{d.mean();});d.add(2);d.add(4);check(d.sum==6&&d.mean()==3);d.add(65504);check(d.sum==65510&&d.mean()==65510.f/3);d.add(1e6f);check(d.sum==131014&&d.mean()==131014.f/4);
    reject([&]{d.add(-1);});reject([&]{d.add(std::numeric_limits<float>::quiet_NaN());});d.count=16384;reject([&]{d.add(1);});
    check(view_z(7,{0,0,1},c)==7);reject([&]{view_z(7,{0,0,2},c);});reject([&]{view_z(-1,{0,0,1},c);});reject([&]{view_z(1,{0,0,-1},c);});
    for(auto n:{std::array<float,3>{1,0,0},std::array<float,3>{0,-1,0},std::array<float,3>{0,0,-1},std::array<float,3>{.6f,0,-.8f},std::array<float,3>{.48f,.64f,.6f}}){auto packed=normal_oct(n);double l=std::abs(double(n[0]))+std::abs(double(n[1]))+std::abs(double(n[2]));check(std::abs(packed[0]-(.5+(double(n[0])+n[1])/(2*l)))<=1e-7&&std::abs(packed[1]-(.5+(double(n[1])-n[0])/(2*l)))<=1e-7&&packed[2]==(n[2]<0?0:1)&&packed[3]==0);}
    reject([&]{normal_oct({0,0,0});});reject([&]{normal_oct({0,0,std::numeric_limits<float>::infinity()});});
    std::cout<<"{\"complete\":true,\"actual_cpp_checks\":"<<checks<<",\"gpu_initialized\":false}\n";
}

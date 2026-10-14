// Post-hoc N009 direct-light diagnosis. Independent double N008 geometry;
// this is not a float GPU emulator and does not establish a repaired GPU PASS.
#include "n008_oracle.hpp"
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <map>
#include <vector>
namespace o=phos::gi::research::n008;
namespace fs=std::filesystem;
struct GHit {float n[3],t; std::uint32_t prim,mat,inst,flag;};
struct Params {float cam[4],right[4],up[4],fwd[4],origin[4],light[4];std::uint32_t counts[4],limits[4];};
static_assert(sizeof(GHit)==32 && sizeof(Params)==128);
std::vector<char> read(const fs::path& p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("open: "+p.string());return {std::istreambuf_iterator<char>(f),{}};}
template<class T>T at(const std::vector<char>& b,std::size_t off){if(off+sizeof(T)>b.size())throw std::runtime_error("short input");T v;std::memcpy(&v,b.data()+off,sizeof(T));return v;}
o::V3 v3(const float* v){return {v[0],v[1],v[2]};}
void vec(o::V3 p){std::cout<<'['<<p.x<<','<<p.y<<','<<p.z<<']';}
int main(int argc,char** argv){try{
 if(argc!=3)throw std::runtime_error("usage: direct_diagnostic CAPTURE PIXEL_TSV (id oracle_t oracle_triangle gpu_direct ref_direct)");
 fs::path cap=argv[1];auto g=read(cap/"geometry-state.bin"),f=read(cap/"frame-state.bin"),h=read(cap/"gpu/hits.bin");
 auto p=at<Params>(f,20);auto w=at<std::uint32_t>(f,12),ht=at<std::uint32_t>(f,16),nt=at<std::uint32_t>(g,4);
 if(f.size()!=148||g.size()!=8+52*std::size_t(nt)||h.size()!=32*std::size_t(w)*ht)throw std::runtime_error("state size mismatch");
 std::vector<o::Triangle> tris;std::map<std::uint32_t,std::uint32_t> ids;o::Aabb box;
 for(std::uint32_t i=0;i<nt;++i){float a[9];std::memcpy(a,g.data()+8+52*std::size_t(i),36);o::Triangle t{v3(a),v3(a+3),v3(a+6),0};tris.push_back(t);box.grow(t.v0);box.grow(t.v1);box.grow(t.v2);ids.emplace(at<std::uint32_t>(g,44+52*std::size_t(i)),i);}
 o::Bvh bvh(tris);double diag=o::length(box.hi-box.lo);const auto invalid=0xffffffffU;
 std::ifstream in(argv[2]);if(!in)throw std::runtime_error("pixel TSV open");std::uint32_t id,oi;double ot,gd,rd;bool first=true;
 std::cout<<std::setprecision(17)<<"{\"schema\":\"n010-direct-ray-diagnostic/1\",\"independent_double_geometry\":true,\"diagonal\":"<<diag<<",\"pixels\":[";
 while(in>>id>>ot>>oi>>gd>>rd){if(id>=w*ht||oi>=nt)throw std::runtime_error("bad pixel/triangle");auto hit=at<GHit>(h,id*32);auto self=ids.at(hit.prim);auto x=id%w,y=id/w;
  float nx=2.0f*(float(x)+0.5f)/float(w)-1.0f,ny=1.0f-2.0f*(float(y)+0.5f)/float(ht),d[3];
  for(int a=0;a<3;++a)d[a]=p.fwd[a]+p.right[a]*(nx*p.right[3])+p.up[a]*(ny*p.up[3]);
  float len=std::sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]),pos[3];for(int a=0;a<3;++a){d[a]/=len;pos[a]=p.cam[a]+d[a]*hit.t;}
  o::V3 gpu_pos=v3(pos),gpu_n=o::normalize(v3(hit.n)),cam=v3(p.cam),light=v3(p.light);
  if(o::dot(gpu_n,v3(d))>0)gpu_n=gpu_n*-1;
  double dx=2.0*(double(x)+0.5)/w-1.0,dy=1.0-2.0*(double(y)+0.5)/ht;
  auto fwd=o::normalize(v3(p.fwd)),right=o::normalize(o::cross(fwd,v3(p.up))),up=o::cross(right,fwd);
  auto od=o::normalize(fwd+right*(dx*p.right[3])+up*(dy*p.up[3]));
  auto oracle_pos=cam+od*ot,oracle_n=o::normalize(o::cross(tris[oi].v1-tris[oi].v0,tris[oi].v2-tris[oi].v0));if(o::dot(oracle_n,od)>0)oracle_n=oracle_n*-1;
  std::cout<<(first?"":",")<<"{\"id\":"<<id<<",\"x\":"<<x<<",\"y\":"<<y<<",\"gpu_primary_primitive\":"<<hit.prim<<",\"oracle_triangle\":"<<oi<<",\"gpu_direct\":"<<gd<<",\"reference_direct\":"<<rd<<",\"gpu_position\":";vec(gpu_pos);std::cout<<",\"oracle_position\":";vec(oracle_pos);std::cout<<",\"position_distance\":"<<o::length(gpu_pos-oracle_pos)<<",\"rays\":[";
  bool rf=true;
  for(int source=0;source<2;++source){auto pos0=source?oracle_pos:gpu_pos,n=source?oracle_n:gpu_n;auto lv=light-pos0;double dist=o::length(lv);auto wi=lv*(1/dist);
   for(int mode=0;mode<4;++mode){double eps=mode==0?std::max(8e-4,double(p.cam[3])*0.02):mode==1?diag*1e-12:0.0;
    auto org=pos0+n*eps;double tmax=dist-(mode==0?std::max(16e-4,double(p.cam[3])*0.04):eps);
    auto blocker=bvh.closest({org,wi},mode==0?1e-4:0.0,tmax,mode==3?invalid:self);
    double cosine=std::max(0.0,o::dot(n,wi)),sc=double(p.light[3]);
    std::cout<<(rf?"":",")<<"{\"source\":\""<<(source?"oracle":"gpu_float_reconstructed")<<"\",\"mode\":\""<<(mode==0?"shader_offset_ignore_self":mode==1?"oracle_offset_ignore_self":mode==2?"zero_offset_ignore_self":"zero_offset_include_self")<<"\",\"origin\":";vec(org);std::cout<<",\"direction\":";vec(wi);std::cout<<",\"offset\":"<<eps<<",\"tmax\":"<<tmax<<",\"blocked\":"<<(blocker.hit()?"true":"false")<<",\"blocker_triangle\":"<<(blocker.hit()?std::int64_t(blocker.tri):-1)<<",\"blocker_t\":"<<(blocker.hit()?blocker.t:-1)<<",\"predicted_direct\":"<<(blocker.hit()?0:cosine*sc*sc/(sc*sc+dist*dist)/o::kPi)<<'}';rf=false;
   }
  }
  std::cout<<"]}";first=false;
 }
 if(!in.eof())throw std::runtime_error("malformed TSV");std::cout<<"]}\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

//042 independent brute-force float64 visibility for the CPU replay (no BVH, no GPU).
// Each query reports nominal, strict and loose occlusion under the 042a boundary perturbations.
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;
struct Query {double origin[3];double direction[3];double tmax;std::uint32_t ignore;std::uint32_t pad;};
static_assert(sizeof(Query)==64);
struct Triangle {double v0[3],e1[3],e2[3];};
static void need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
static std::vector<char> bytes(const fs::path& p){
    std::ifstream f(p,std::ios::binary);need(bool(f),"042 visibility input");
    return std::vector<char>((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());
}
int main(int argc,char** argv){
    try{
        need(argc==7&&std::string(argv[1])=="--triangles"&&std::string(argv[3])=="--queries"&&std::string(argv[5])=="--out","042 usage --triangles G --queries Q --out R");
        auto g=bytes(argv[2]);need(g.size()>=8,"042 geometry header");std::uint32_t version,count;
        std::memcpy(&version,g.data(),4);std::memcpy(&count,g.data()+4,4);
        need(version==1&&count>0&&count<=2048&&g.size()==8+52ull*count,"042 geometry ABI");
        std::vector<Triangle> triangles(count);
        for(std::uint32_t j=0;j<count;j++){
            float v[9];std::memcpy(v,g.data()+8+52ull*j,36);
            for(int k=0;k<3;k++){triangles[j].v0[k]=v[k];triangles[j].e1[k]=double(v[3+k])-v[k];triangles[j].e2[k]=double(v[6+k])-v[k];}
        }
        auto q=bytes(argv[4]);need(q.size()%sizeof(Query)==0,"042 query ABI");std::size_t n=q.size()/sizeof(Query);
        std::vector<Query> queries(n);std::memcpy(queries.data(),q.data(),q.size());
        std::vector<std::uint8_t> result(n);constexpr double margin=1e-6,relative=1e-4;
        for(std::size_t r=0;r<n;r++){
            const Query& x=queries[r];
            for(int k=0;k<3;k++)need(std::isfinite(x.origin[k])&&std::isfinite(x.direction[k]),"042 finite query");
            need(std::isfinite(x.tmax)&&x.tmax>0,"042 query tmax");
            const double strict_t=x.tmax*(1-relative),loose_t=x.tmax*(1+relative);bool strict=false,loose=false,nominal=false;
            for(std::uint32_t j=0;j<count&&!(strict&&loose&&nominal);j++){
                if(j==x.ignore)continue;
                const Triangle& t=triangles[j];const double* d=x.direction;
                double p[3]={d[1]*t.e2[2]-d[2]*t.e2[1],d[2]*t.e2[0]-d[0]*t.e2[2],d[0]*t.e2[1]-d[1]*t.e2[0]};
                double det=t.e1[0]*p[0]+t.e1[1]*p[1]+t.e1[2]*p[2];
                if(!(std::abs(det)>1e-300))continue;
                double inv=1/det;
                double s[3]={x.origin[0]-t.v0[0],x.origin[1]-t.v0[1],x.origin[2]-t.v0[2]};
                double u=(s[0]*p[0]+s[1]*p[1]+s[2]*p[2])*inv;
                double c[3]={s[1]*t.e1[2]-s[2]*t.e1[1],s[2]*t.e1[0]-s[0]*t.e1[2],s[0]*t.e1[1]-s[1]*t.e1[0]};
                double v=(d[0]*c[0]+d[1]*c[1]+d[2]*c[2])*inv,h=(t.e2[0]*c[0]+t.e2[1]*c[1]+t.e2[2]*c[2])*inv;
                if(!(h>0))continue;
                if(u>=margin&&v>=margin&&u+v<=1-margin&&h<strict_t)strict=true;
                if(u>=-margin&&v>=-margin&&u+v<=1+margin&&h<loose_t)loose=true;
                if(u>=0&&v>=0&&u+v<=1&&h<x.tmax)nominal=true;
            }
            result[r]=std::uint8_t((strict?1:0)|(loose?2:0)|(nominal?4:0));
        }
        need(!fs::exists(argv[6]),"042 exclusive visibility output");std::ofstream o(argv[6],std::ios::binary);
        o.write(reinterpret_cast<const char*>(result.data()),std::streamsize(n));need(bool(o),"042 visibility output");
        std::cout<<"{\"queries\":"<<n<<",\"triangles\":"<<count<<"}\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}

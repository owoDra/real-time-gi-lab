#include "surface_quadratic_scalar.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
namespace q=m001_q019;namespace fs=std::filesystem;
static void require(bool b,const char* m){if(!b)throw std::runtime_error(m);}
static bool close(float a,float b){return std::abs(a-b)<=2e-4f+2e-5f*std::abs(b);}
static q::Storage fixture(q::uint w=11,q::uint h=11){
    q::Storage s;s.camera={0,0,0,1e-4f,0,0,1,100,1,0,0,1,0,1,0,1,1e-5f,1,float(w),float(h)};
    s.hits.assign(w*h*8,0);s.sources.assign(w*h,0);s.allocate();
    for(q::uint y=0;y<h;y++)for(q::uint x=0;x<w;x++){
        auto p=y*w+x;s.hits[p*8+2]=std::bit_cast<q::uint>(1.f);s.hits[p*8+3]=std::bit_cast<q::uint>(2.f);s.hits[p*8+7]=1;
        s.geometry[p*8]=float(x);s.geometry[p*8+1]=float(y);s.geometry[p*8+6]=1;
    }return s;
}
static void fit(q::Storage& s){q::active=&s;for(q::uint stage=0;stage<3;stage++)for(q::uint p=0;p<s.size();p++)q::q_fit(p,1u<<stage,stage);}
static void apply(q::Storage& s){q::active=&s;for(q::uint stage=0;stage<3;stage++)for(q::uint p=0;p<s.size();p++)q::q_apply(p,1u<<stage,stage);}
static void check_coeff(const q::Storage& s){
    for(q::uint stage=0;stage<3;stage++)for(q::uint p=0;p<s.size();p++){
        float sum=0,l1=0;auto mask=s.maps[stage*s.size()+p];
        for(q::uint j=0;j<25;j++){float c=s.coefficients[(stage*25+j)*s.size()+p];require(std::isfinite(c),"finite coefficient");sum+=c;l1+=std::abs(c);if(!(mask&(1u<<j)))require(c==0,"rejected coefficient nonzero");}
        require(l1<=4.0002f,"L1 health");require(std::abs(sum-(s.hits[p*8+7]?1.f:0.f))<=2e-4f,"normalization health");
    }
}
template<class T>static void write(const fs::path& p,const std::vector<T>& v){std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char*>(v.data()),std::streamsize(v.size()*sizeof(T)));require(bool(f),"fixture write");}
static void dump(const fs::path& root,const std::string& name,const q::Storage& s,bool camera=false){
    auto p=root/name;require(!fs::exists(p)&&fs::create_directory(p),"fixture output exists");
    write(p/"camera.f32",std::vector<float>(s.camera.begin(),s.camera.end()));write(p/"hits.u32",s.hits);write(p/"geometry.f32",s.geometry);
    write(p/"coefficients.f32",s.coefficients);write(p/"maps.u32",s.maps);write(p/"sources.f32",s.sources);write(p/"stages.f32",s.stages);write(p/"unclipped.f32",s.unclipped);
    std::ofstream(p/"fixture.json")<<"{\"name\":\""<<name<<"\",\"width\":"<<int(s.camera[18])<<",\"height\":"<<int(s.camera[19])<<",\"images\":1,\"geometry_from_camera\":"<<(camera?"true":"false")<<"}\n";
}
int main(int argc,char** argv){try{
    require(argc==2,"new fixture output root required");fs::path root=argv[1];require(!fs::exists(root)&&fs::create_directory(root),"test output exists");std::vector<std::string> names;
    for(const std::string name:{"zero","constant","affine","quadratic","horizontal","vertical","single"}){
        auto s=name=="horizontal"?fixture(11,1):name=="vertical"?fixture(1,11):name=="single"?fixture(1,1):fixture();
        for(q::uint p=0;p<s.size();p++){
            float x=s.geometry[p*8],y=s.geometry[p*8+1];
            s.sources[p]=name=="zero"?0:name=="constant"||name=="single"?7:name=="affine"?10+.2f*x+.3f*y:2+.2f*x+.3f*y+.01f*x*x+.02f*x*y+.03f*y*y;
        }
        fit(s);apply(s);check_coeff(s);
        for(q::uint stage=0;stage<3;stage++)for(q::uint p=0;p<s.size();p++)require(close(s.stages[stage*s.size()+p],s.sources[p]),"analytic polynomial reproduction");
        if(name=="single")for(q::uint stage=0;stage<3;stage++)require(s.maps[(3+stage)*s.size()]>>8==257,"single rank");
        dump(root,name,s);names.push_back(name);
    }
    {auto s=fixture();for(q::uint p=0;p<s.size();p++){s.hits[p*8+7]=0;for(q::uint a=0;a<8;a++)s.geometry[p*8+a]=0;s.sources[p]=7;}
        fit(s);apply(s);check_coeff(s);for(float x:s.stages)require(x==0,"miss stage nonzero");for(q::uint p=0;p<s.size()*3;p++)require(s.maps[3*s.size()+p]==255,"miss selector");dump(root,"miss",s);names.push_back("miss");}
    for(const std::string barrier:{"material","normal","plane","thin-miss"}){
        auto s=fixture();for(q::uint y=0;y<11;y++){auto p=y*11+5;if(barrier=="material")s.hits[p*8+5]=1;
            if(barrier=="normal"){s.geometry[p*8+6]=0;s.geometry[p*8+5]=1;}
            if(barrier=="plane")s.geometry[p*8+2]=.01f;
            if(barrier=="thin-miss"){s.hits[p*8+7]=0;for(q::uint a=0;a<8;a++)s.geometry[p*8+a]=0;}}
        fit(s);check_coeff(s);q::active=&s;require(!q::q_accept(4*11+4,0,1,1),"adjacent barrier skipped");
        require(!q::q_accept(4*11+4,0,2,2),"thin intervening barrier skipped");
        apply(s);dump(root,barrier,s);names.push_back(barrier);
    }
    {auto s=fixture();fit(s);q::active=&s;require(!q::q_accept(0,-1,0,4)&&!q::q_accept(0,0,-1,4)&&q::q_accept(0,0,0,4),"viewport/center");
        apply(s);dump(root,"viewport",s);names.push_back("viewport");}
    {auto s=fixture();fit(s);auto center=5*11+5;int selected=-1;for(int j=0;j<25;j++)if(s.coefficients[j*s.size()+center]<-1e-5f){selected=j;break;}
        require(selected>=0,"expected signed coefficient");int y=5+selected/5-2,x=5+selected%5-2;s.sources[y*11+x]=1;apply(s);check_coeff(s);
        require(s.unclipped[center]<0 && s.stages[center]==0,"preclip/clip");dump(root,"signed-clipping",s);names.push_back("signed-clipping");}
    {q::active=nullptr;float a[25]{},b[25]{};a[0]=5;a[1]=-4;b[0]=2;b[1]=-1;require(q::q_l1_model(a,b)==1,"affine L1 fallback");names.push_back("affine-fallback");
        require(q::q_l1_model(a,a)==2,"constant L1 fallback");names.push_back("constant-fallback");a[0]=3;a[1]=-1;require(q::q_l1_model(a,b)==0,"inclusive L1");names.push_back("inclusive-L1");}
    {auto s=fixture(1,1);s.camera[0]=1;s.camera[1]=2;s.camera[2]=3;q::active=&s;q::q_geometry(0);
        require(s.geometry[0]==1&&s.geometry[1]==2&&s.geometry[2]==5&&s.geometry[6]==-1,"camera position/normal orientation");
        fit(s);apply(s);dump(root,"camera",s,true);names.push_back("camera");}
    {auto s=fixture(9,7);s.camera[0]=1;s.camera[1]=2;s.camera[2]=3;q::active=&s;for(q::uint p=0;p<s.size();p++)q::q_geometry(p);
        fit(s);apply(s);check_coeff(s);dump(root,"camera-grid",s,true);names.push_back("camera-grid");}
    std::cout<<"{\"actual_shared_float32_contract_tests\":"<<names.size()<<",\"pass_\":true,\"tests\":[";
    for(std::size_t i=0;i<names.size();i++)std::cout<<(i?",":"")<<'"'<<names[i]<<'"';std::cout<<"]}\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}

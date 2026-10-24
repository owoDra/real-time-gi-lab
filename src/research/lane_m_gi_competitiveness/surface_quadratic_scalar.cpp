//019 CPU execution/readback oracle for the actual float32 shader include.
#include "surface_quadratic_scalar.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
namespace fs=std::filesystem;
namespace q=m001_q019;
static void require(bool b,const char* m){if(!b)throw std::runtime_error(m);}
template<class T>static std::vector<T> read(const fs::path& p,std::size_t count){
    require(fs::is_regular_file(p)&&fs::file_size(p)==count*sizeof(T),"input shape/size differs");
    std::vector<T> v(count);std::ifstream f(p,std::ios::binary);f.read(reinterpret_cast<char*>(v.data()),std::streamsize(count*sizeof(T)));require(bool(f),"input read failed");return v;
}
template<class T>static void write(const fs::path& p,const std::vector<T>& v){
    require(!fs::exists(p),"output exists");std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char*>(v.data()),std::streamsize(v.size()*sizeof(T)));require(bool(f),"output write failed");
}
static q::Storage load(const fs::path& input){
    q::Storage s;auto camera=read<float>(input/"camera.f32",20);std::copy(camera.begin(),camera.end(),s.camera.begin());
    for(float x:camera)require(std::isfinite(x),"nonfinite camera");
    require(camera[18]==320 && camera[19]==180 && camera[17]==5 && camera[16]>0,"unregistered dimensions/images/epsilon");
    float forward2=0;for(int k=4;k<7;k++)forward2+=camera[k]*camera[k];require(forward2>0,"zero camera direction");
    require(camera[11]>0 && camera[15]>0 && camera[7]>=1e-4f,"camera range differs");
    for(int a:{4,8,12}){float norm2=0;for(int k=0;k<3;k++)norm2+=camera[a+k]*camera[a+k];require(std::abs(norm2-1)<=1e-4f,"camera basis not unit");}
    for(auto axes:{std::pair{4,8},std::pair{4,12},std::pair{8,12}}){float dot=0;for(int k=0;k<3;k++)dot+=camera[axes.first+k]*camera[axes.second+k];require(std::abs(dot)<=1e-4f,"camera basis not orthogonal");}
    s.hits=read<q::uint>(input/"hits.u32",s.size()*8);s.sources=read<float>(input/"sources.f32",s.size()*s.images());
    for(q::uint p=0;p<s.size();p++) {
        auto flag=s.hits[p*8+7];require(flag<=1,"primary flag invalid");
        if(flag){float n2=0;for(q::uint a=0;a<3;a++){float x=q::q_fbits(s.hits[p*8+a]);require(std::isfinite(x),"primary normal nonfinite");n2+=x*x;}
            float t=q::q_fbits(s.hits[p*8+3]);require(std::abs(std::sqrt(n2)-1)<=1e-4f && std::isfinite(t) && t>=1e-4f && t<=camera[7],"primary normal/depth range differs");
            for(q::uint a=4;a<7;a++)require(s.hits[p*8+a]!=0xffffffffu,"hit metadata invalid");
        }else{for(q::uint a=0;a<3;a++)require(q::q_fbits(s.hits[p*8+a])==0,"miss normal invalid");
            require(q::q_fbits(s.hits[p*8+3])==INFINITY,"miss t invalid");for(q::uint a=4;a<7;a++)require(s.hits[p*8+a]==0xffffffffu,"miss metadata invalid");}
    }
    for(float x:s.sources)require(std::isfinite(x)&&x>=0,"source nonfinite/negative");
    s.allocate();return s;
}
int main(int argc,char** argv){
    fs::path out;
    try{
        require(argc==6 && std::string(argv[1])=="--cpu-check" && std::string(argv[2])=="--input" && std::string(argv[4])=="--out","usage: --cpu-check --input NEW_INPUT --out NEW_OUTPUT");
        auto s=load(argv[3]);out=argv[5];require(!fs::exists(out),"output exists");require(fs::create_directory(out),"output create failed");
        q::execute(s);
        for(const auto* v:{&s.geometry,&s.coefficients,&s.stages,&s.unclipped})for(float x:*v)require(std::isfinite(x),"nonfinite reconstruction");
        write(out/"geometry.f32",s.geometry);write(out/"coefficients.f32",s.coefficients);write(out/"maps.u32",s.maps);
        write(out/"stages.f32",s.stages);write(out/"unclipped.f32",s.unclipped);
        std::ofstream(out/"complete.json")<<"{\"schema\":\"m001-q019-native-cpu/1\",\"complete\":true,\"gpu_initialized\":false,\"pixels\":57600,\"images\":5}\n";
        std::cout<<"{\"complete\":true,\"gpu_initialized\":false}\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}

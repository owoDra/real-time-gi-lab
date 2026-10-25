#include "anchor_path_difference.hpp"
namespace a=phos::gi::research::m001anchor;
int main(int argc,char** argv){
    try{
        const bool geo=argc==6&&std::string(argv[1])=="geometry"&&std::string(argv[2])=="--scene"&&std::string(argv[4])=="--out";
        const bool render=argc==8&&std::string(argv[1])=="paths"&&std::string(argv[2])=="--scene"&&std::string(argv[4])=="--geometry"&&std::string(argv[6])=="--out";
        a::require(geo||render,"031 requires geometry --scene S --out NEW or paths --scene S --geometry G --out NEW");
        const a::fs::path out=argv[geo?5:7];a::require(!a::fs::exists(out),"031 output exists; no overwrite");
        std::ifstream input(argv[3]);a::require(bool(input),"031 scene unavailable");const auto scene=a::p::parse_scene(input);a::validate_scene(scene);
        a::require(a::fs::create_directory(out),"031 output creation failed");
        if(geo)a::geometry(scene,out);else a::paths(scene,argv[5],out);return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}

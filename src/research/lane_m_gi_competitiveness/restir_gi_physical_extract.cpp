//035 isolated CPU physical extraction; original N008 and private observer side by side.
#include "n008_oracle.hpp"
#include "restir035_observed.hpp"
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <type_traits>
namespace o=phos::gi::research::n008;namespace v=phos::gi::research::restir035;
namespace fs=std::filesystem;
using u32=std::uint32_t;using u64=std::uint64_t;
constexpr std::array<u64,4> seeds{305419896ULL^0xa035a035a035a035ULL,2596069104ULL^0xa035a035a035a035ULL,81985529216486895ULL^0xa035a035a035a035ULL,18364758544493064720ULL^0xa035a035a035a035ULL};
static void need(bool yes,const char* text){if(!yes)throw std::runtime_error(text);}
template<class T>static bool equal(const T& a,const T& b){static_assert(std::is_trivially_copyable_v<T>);return std::memcmp(&a,&b,sizeof(T))==0;}
template<class T>static void save(const fs::path& p,const std::vector<T>& a){need(!fs::exists(p),"035 output exists");std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char*>(a.data()),a.size()*sizeof(T));need(bool(f),"035 write");}
struct Packet {v::V3 receiver{},normal{},endpoint{},endpoint_normal{},radiance{};double pdf{};u32 status{},sdk_m{},trials{1},padding{};};
static_assert(sizeof(Packet)==144&&sizeof(o::Xoshiro256)==32&&sizeof(v::Xoshiro256)==32&&sizeof(o::RenderCounters)==32&&sizeof(o::PrimaryRecord)==16);
struct Result {std::array<double,9> components{};o::PrimaryRecord primary;std::array<u64,4> counts{},rng{};};
static_assert(sizeof(Result)==152);
static Packet extract(const v::PathVertex* records,u32 depth){Packet p;
 if(records[0].kind!=2)return p;p.receiver=records[0].spawn;p.normal=records[0].normal;p.status=1;
 if(records[1].kind!=2)return p;p.status=2;p.sdk_m=1;p.endpoint=records[1].hit_position;p.endpoint_normal=records[1].normal;
 p.pdf=v::dot(p.normal,records[1].direction)/v::kPi;need(p.pdf>0&&std::isfinite(p.pdf),"035 source PDF");
 for(u32 i=1;i<depth;++i)p.radiance=p.radiance+records[i].reflected;
 return p;
}
static void validate(const o::Scene& s,bool full){need(s.sampling==o::Sampling::Center&&!s.secondary_far_camera&&(s.max_bounces==2||s.max_bounces==8)&&s.falloff==o::Falloff::N001Soft,"035 scene semantics");if(full)need(s.width==320&&s.height==180&&!s.points.empty(),"035 full scene dimensions/lights");
 for(const auto& m:s.materials)need(m.rho==o::Rgb{1,1,1}&&m.emit==o::Rgb{0,0,0}&&m.two_sided,"035 unit-grey two-sided material");}
static u64 run(const std::string& raw,const fs::path& out,bool contracts){std::istringstream ia(raw),ib(raw);auto scene=o::parse_scene(ia);auto observed_scene=v::parse_scene(ib);validate(scene,!contracts);o::Oracle original(scene);v::Oracle observed(observed_scene);u32 pixels=scene.width*scene.height,depth=scene.max_bounces;u64 count=0;
 for(u32 seed=0;seed<(contracts?1u:4u);++seed){auto dir=out/("seed-"+std::to_string(seed));if(!contracts)need(fs::create_directory(dir),"035 seed exists");u32 repetitions=contracts?16:1;std::vector<Result> baseline(pixels*repetitions),instrumented(baseline.size());std::vector<v::PathVertex> vertices(baseline.size()*depth);std::vector<Packet> packets(baseline.size());
  auto flush=[&](){if(!contracts){save(dir/"original.bin",baseline);save(dir/"observed.bin",instrumented);save(dir/"vertices.bin",vertices);save(dir/"packets.bin",packets);}};
  for(u32 id=0;id<pixels;++id)for(u32 sample=0;sample<repetitions;++sample){auto index=id*repetitions+sample;auto& a=baseline[index];auto& b=instrumented[index];o::Xoshiro256 ra(seeds[seed],id,sample);v::Xoshiro256 rb(seeds[seed],id,sample);o::RenderCounters ca;v::RenderCounters cb;o::Rgb values[o::kComponents];v::Rgb reflected[v::kComponents];v::PrimaryRecord primary;
   original.sample(id%scene.width,id/scene.width,ra,values,ca,&a.primary);observed.sample(id%scene.width,id/scene.width,rb,reflected,cb,&primary,vertices.data()+index*depth);
   std::memcpy(a.components.data(),values,72);std::memcpy(b.components.data(),reflected,72);std::memcpy(&b.primary,&primary,16);std::memcpy(a.counts.data(),&ca,32);std::memcpy(b.counts.data(),&cb,32);std::memcpy(a.rng.data(),&ra,32);std::memcpy(b.rng.data(),&rb,32);
   packets[index]=extract(vertices.data()+index*depth,depth);if(!equal(a,b)){flush();throw std::runtime_error("035 original/observed bit parity failure");}
   const auto& p=packets[index];auto li=p.radiance;for(unsigned c=0;c<3;++c)need(li[c]==a.components[6+c],"035 suffix exact original recovery");
   if(p.status==2){const auto d=v::normalize(p.endpoint-p.receiver);const double scale=v::dot(p.normal,d)/(v::kPi*p.pdf);need(std::abs(scale-1)<=1e-10+1e-12,"035 source direction/PDF recovery");need(v::dot(p.endpoint_normal,p.receiver-p.endpoint)>0,"035 oriented secondary support");}
   ++count;
  }flush();if(!contracts)std::cout<<"035 seed "<<seed<<" complete\n"<<std::flush;
 }
 if(!contracts){std::ofstream f(out/"complete.json");f<<"{\"complete\":true,\"gpu_executed\":false,\"paths_per_role\":"<<count<<",\"original_and_observed_runs\":2,\"width\":"<<scene.width<<",\"height\":"<<scene.height<<",\"vertices\":"<<depth<<",\"vertex_stride\":192,\"packet_stride\":144,\"result_stride\":152,\"bit_exact_original_observed\":true,\"offset\":"<<std::setprecision(17)<<original.offset()<<",\"seeds\":[";for(unsigned i=0;i<4;++i)f<<(i?",":"")<<seeds[i];f<<"]}\n";need(bool(f),"035 completion write");}return count;
}
int main(int argc,char** argv){try{
 if(argc==2&&std::string(argv[1])=="--contracts"){u64 count=0;for(u32 depth:{2,8})for(u32 fixture=0;fixture<4;++fixture){std::ostringstream s;s<<"n008scene 1\nresolution 1 1\ncamera 0 0 .5 0 0 -1 0 1 0 .1 .1 .001 10\nsampling center\nmax_bounces "<<depth<<"\nfalloff n001_soft 1\nsecondary_far inf\nmaterial m 1 1 1 0 0 0 1\npoint 0 0 .5 "<<(fixture==3?0:1)<<" "<<(fixture==3?0:1)<<" "<<(fixture==3?0:1)<<"\n";
   if(fixture==0)s<<"tri m 100 100 0 101 100 0 100 101 0\n";else{s<<"tri m -100 -100 0 100 -100 0 100 100 0\ntri m -100 -100 0 100 100 0 -100 100 0\n";if(fixture>=2)s<<"tri m -100 -100 1 100 -100 1 100 100 1\ntri m -100 -100 1 100 100 1 -100 100 1\n";}count+=run(s.str(),{},true);}
  std::cout<<"{\"complete\":true,\"all_pass\":true,\"gpu_executed\":false,\"new_native_cases\":8,\"new_path_pairs\":"<<count<<"}\n";return 0;}
 need(argc==5&&std::string(argv[1])=="--scene"&&std::string(argv[3])=="--out","035 usage --scene S --out NEW | --contracts");fs::path source=argv[2],out=argv[4];need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"035 exclusive output");std::ifstream f(source);need(bool(f),"035 scene read");std::ostringstream raw;raw<<f.rdbuf();need(fs::create_directory(out),"035 output creation");run(raw.str(),out,false);return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}

#include "software_bvh.hpp"
#include "sparse_grid.hpp"
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <optional>
#include <string_view>

namespace lane = phos::gi::research::lane_b;
using Clock=std::chrono::steady_clock;

namespace {
struct Row{std::string scene,dynamic,camera,candidate;float tmax{};std::size_t triangles{},rays{},mismatches{},persistent{},scratch{};double build{},refit{},rebuild{},update{},trace{};};
struct Args{std::size_t rays{2048};int repeats{3};};

double us(Clock::time_point t){return std::chrono::duration<double,std::micro>(Clock::now()-t).count();}
double median(std::vector<double> v){std::sort(v.begin(),v.end());auto m=v.size()/2;return v.size()%2?v[m]:(v[m-1]+v[m])*.5;}
template<class F>double measure(int n,F&& f){std::vector<double> v;for(int i=0;i<n;++i){auto t=Clock::now();f();v.push_back(us(t));}return median(std::move(v));}
void consume(const lane::Hit& h){static volatile std::uint64_t sink=0;sink=sink^std::uint64_t(h.primitive_id)^std::uint64_t(h.hit);}
template<class A>std::size_t validate(const std::vector<lane::Triangle>& t,const A& a,std::span<const lane::Ray> rays){std::size_t bad=0;for(auto r:rays)if(!lane::equivalent_hit(lane::trace_reference(t,r),a.trace(r)))++bad;return bad;}
template<class A>double trace_time(const A& a,std::span<const lane::Ray> rays,int n){return measure(n,[&]{for(auto r:rays)consume(a.trace(r));});}

Row run_bvh(const lane::Scene& src,std::span<const lane::Ray> rays,bool dyn,bool cam,float tmax,int repeats){
    auto t=src.triangles;std::optional<lane::SoftwareBvh> tmp;double build=measure(repeats,[&]{tmp.emplace(t);});lane::SoftwareBvh bvh(t);double update=0,refit=0;
    if(dyn){update=measure(repeats,[&]{auto moved=src.triangles;lane::translate(moved,src.moving,{1.25F,.65F,-.8F});volatile auto n=moved.size();(void)n;});lane::translate(t,src.moving,{1.25F,.65F,-.8F});refit=measure(repeats,[&]{bvh.refit(t);});bvh.refit(t);}
    double rebuild=measure(repeats,[&]{lane::SoftwareBvh x(t);if(!rays.empty())consume(x.trace(rays.front()));});
    return {src.name,dyn?"moving":"static",cam?"shifted":"static","software-bvh",tmax,t.size(),rays.size(),validate(t,bvh,rays),bvh.persistent_bytes(),bvh.scratch_bytes(),build,refit,rebuild,update,trace_time(bvh,rays,repeats)};
}
Row run_grid(const lane::Scene& src,std::span<const lane::Ray> rays,bool dyn,bool cam,float tmax,int repeats){
    auto t=src.triangles;std::optional<lane::SparseGrid> tmp;double build=measure(repeats,[&]{tmp.emplace(t);});lane::SparseGrid grid(t);double update=0;
    if(dyn){lane::translate(t,src.moving,{1.25F,.65F,-.8F});update=measure(repeats,[&]{lane::SparseGrid x(src.triangles);auto moved=src.triangles;lane::translate(moved,src.moving,{1.25F,.65F,-.8F});x.update(moved,src.moving);});grid.update(t,src.moving);}
    double rebuild=measure(repeats,[&]{lane::SparseGrid x(t);if(!rays.empty())consume(x.trace(rays.front()));});
    return {src.name,dyn?"moving":"static",cam?"shifted":"static","stratabrick-grid-control",tmax,t.size(),rays.size(),validate(t,grid,rays),grid.persistent_bytes(),grid.scratch_bytes(),build,0,rebuild,update,trace_time(grid,rays,repeats)};
}
void csv(std::ostream& o,const std::vector<Row>& rows){
    o<<"scene,dynamic,camera,t_max,candidate,triangles,rays,mismatches,build_us,refit_us,rebuild_us,dynamic_update_us,trace_us,persistent_bytes,scratch_bytes\n"<<std::fixed<<std::setprecision(3);
    for(auto&r:rows)o<<r.scene<<','<<r.dynamic<<','<<r.camera<<','<<r.tmax<<','<<r.candidate<<','<<r.triangles<<','<<r.rays<<','<<r.mismatches<<','<<r.build<<','<<r.refit<<','<<r.rebuild<<','<<r.update<<','<<r.trace<<','<<r.persistent<<','<<r.scratch<<'\n';
}
Args args(int argc,char**argv){Args a;for(int i=1;i<argc;++i){std::string_view s=argv[i];if(++i>=argc)throw std::runtime_error("option requires value");if(s=="--rays")a.rays=std::stoull(argv[i]);else if(s=="--repeats")a.repeats=std::stoi(argv[i]);else throw std::runtime_error("unknown option");}if(!a.rays||a.repeats<=0)throw std::runtime_error("rays/repeats must be positive");return a;}
}

int main(int argc,char**argv){try{
    auto a=args(argc,argv);std::vector<Row> rows;
    for(std::string_view name:{"sparse","dense","vertical"}){auto scene=lane::make_scene(name);for(bool dyn:{false,true})for(bool cam:{false,true})for(float t:{50.F,200.F}){auto rays=lane::make_rays(name,a.rays,t,cam);rows.push_back(run_bvh(scene,rays,dyn,cam,t,a.repeats));rows.push_back(run_grid(scene,rays,dyn,cam,t,a.repeats));}}
    csv(std::cout,rows);if(const char*d=std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");d&&*d){std::ofstream f(std::string(d)+"/b001-controls.csv");if(!f)throw std::runtime_error("artifact open failed");csv(f,rows);}auto bad=std::accumulate(rows.begin(),rows.end(),std::size_t{},[](auto n,const Row&r){return n+r.mismatches;});if(bad){std::cerr<<"correctness mismatches: "<<bad<<'\n';return 2;}std::cerr<<"B001 correctness: PASS ("<<rows.size()<<" candidate rows)\n";return 0;
}catch(const std::exception&e){std::cerr<<"B001 error: "<<e.what()<<'\n';return 1;}}

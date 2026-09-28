#include "a001_analysis.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace phos::gi::lane_a {
namespace {

constexpr std::uint32_t INVALID=0xffffffffu;
struct V3{float x{},y{},z{};};
V3 sub(V3 a,V3 b){return{a.x-b.x,a.y-b.y,a.z-b.z};}
float dot(V3 a,V3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
float length(V3 v){return std::sqrt(dot(v,v));}
V3 normalize(V3 v){
    const float l=length(v);
    return l>1e-12f?V3{v.x/l,v.y/l,v.z/l}:V3{};
}
V3 surface_pos(const SurfaceSampleGpu&s){
    return{s.position[0],s.position[1],s.position[2]};
}

bool project(V3 position,const A001ParamsGpu&p,std::uint32_t&tile,float&depth){
    const V3 rel=sub(position,{p.camera_pos_near[0],p.camera_pos_near[1],p.camera_pos_near[2]});
    depth=dot(rel,{p.camera_forward_far[0],p.camera_forward_far[1],p.camera_forward_far[2]});
    if(depth<p.camera_pos_near[3]||depth>p.camera_forward_far[3]) return false;

    const float nx=dot(rel,{p.camera_right_tan_x[0],p.camera_right_tan_x[1],p.camera_right_tan_x[2]})/
        (depth*p.camera_right_tan_x[3]);
    const float ny=dot(rel,{p.camera_up_tan_y[0],p.camera_up_tan_y[1],p.camera_up_tan_y[2]})/
        (depth*p.camera_up_tan_y[3]);
    if(std::abs(nx)>1.0f||std::abs(ny)>1.0f) return false;

    const auto x=std::min(
        p.counts[1]-1u,
        std::uint32_t(std::max(0.0f,(nx*0.5f+0.5f)*float(p.counts[1]))));
    const auto y=std::min(
        p.counts[2]-1u,
        std::uint32_t(std::max(0.0f,(ny*0.5f+0.5f)*float(p.counts[2]))));
    tile=y*p.counts[1]+x;
    return true;
}

V3 ray_direction(std::uint32_t ray){
    constexpr float v=0.5773502691896258f;
    return{(ray&1u)?v:-v,(ray&2u)?v:-v,(ray&4u)?v:-v};
}

std::uint32_t quantized_contribution(const SplitRcWorkItemV1&i,const A001ParamsGpu&p){
    const V3 to=normalize({
        p.light_pos_interval[0]-i.probe_px,
        p.light_pos_interval[1]-i.probe_py,
        p.light_pos_interval[2]-i.probe_pz,
    });
    const float a=std::max(0.0f,i.dir_x*to.x+i.dir_y*to.y+i.dir_z*to.z);
    const float value=std::clamp(a/float(1u<<i.cascade),0.0f,1.0f);
    return static_cast<std::uint32_t>(std::round(value*65535.0f));
}

std::uint64_t fnv1a(const void*data,std::size_t bytes){
    const auto*p=static_cast<const unsigned char*>(data);
    std::uint64_t hash=1469598103934665603ull;
    for(std::size_t i=0;i<bytes;++i){
        hash^=p[i];
        hash*=1099511628211ull;
    }
    return hash;
}

std::string json_escape(const std::string&s){
    std::ostringstream out;
    for(char c:s){
        switch(c){
        case '\\': out<<"\\\\"; break;
        case '"': out<<"\\\""; break;
        case '\n': out<<"\\n"; break;
        case '\r': out<<"\\r"; break;
        case '\t': out<<"\\t"; break;
        default: out<<c;
        }
    }
    return out.str();
}

double ratio(std::uint64_t n,std::uint64_t d){
    return d?double(n)/double(d):0.0;
}

bool within_float_ulps(float actual,float expected,int ulps){
    if(!std::isfinite(actual)||!std::isfinite(expected)) return actual==expected;
    float lo=expected;
    float hi=expected;
    for(int i=0;i<ulps;++i){
        lo=std::nextafter(lo,-std::numeric_limits<float>::infinity());
        hi=std::nextafter(hi, std::numeric_limits<float>::infinity());
    }
    return actual>=lo&&actual<=hi;
}

} // namespace

A001Analysis analyze_a001(
    const SceneSurfaceSet&scene,
    const A001Settings&settings,
    const A001ParamsGpu&p,
    const A001Readback&r){
    A001Analysis a;
    a.locality.items_per_cascade.assign(settings.cascade_count,0);

    const std::uint32_t tiles=settings.tile_width*settings.tile_height;
    std::vector<float>cpu_depth(tiles,std::numeric_limits<float>::infinity());

    for(const auto&s:scene.samples){
        std::uint32_t tile{};
        float depth{};
        if(project(surface_pos(s),p,tile,depth))
            cpu_depth[tile]=std::min(cpu_depth[tile],depth);
    }

    std::uint64_t cpu_visible=0;
    for(float depth:cpu_depth)
        if(std::isfinite(depth)) ++cpu_visible;

    for(std::uint32_t tile=0;tile<tiles;++tile){
        const auto sid=r.tile_owner.at(tile);
        if(sid==INVALID) continue;
        ++a.visible_probe_count;

        if(sid>=scene.samples.size()){
            a.visibility_correct=false;
            a.errors.push_back("visibility owner out of range");
            continue;
        }

        std::uint32_t projected{};
        float depth{};
        const float tolerance=std::max(1e-5f,p.camera_forward_far[3]*1e-6f);
        if(!project(surface_pos(scene.samples[sid]),p,projected,depth) ||
           projected!=tile ||
           depth>cpu_depth[tile]+tolerance){
            a.visibility_correct=false;
            a.errors.push_back("GPU visibility owner is not a nearest projected surface");
        }
    }

    if(a.visible_probe_count!=cpu_visible){
        a.visibility_correct=false;
        a.errors.push_back("GPU/CPU visible tile counts differ");
    }

    const std::uint64_t expected_work=
        a.visible_probe_count*settings.cascade_count*settings.rays_per_probe;
    const std::uint64_t expected_outputs=
        a.visible_probe_count*settings.cascade_count;

    if(r.counters[0]!=expected_work ||
       r.counters[1]!=expected_outputs ||
       r.counters[2]!=0u ||
       r.counters[3]!=a.visible_probe_count){
        a.producer_correct=false;
        a.errors.push_back("producer counters do not match visible work");
    }

    const std::uint32_t block=settings.cascade_count*settings.rays_per_probe;
    if(block==0 || r.work_items.size()%block!=0){
        a.producer_correct=false;
        a.errors.push_back("producer work is not block aligned");
    }

    std::vector<bool>seen_tile(tiles,false);
    std::vector<bool>seen_output(r.resolved.size(),false);
    std::uint64_t semantic_checks=0;
    std::uint64_t semantic_failures=0;

    for(std::size_t base=0;base+block<=r.work_items.size();base+=block){
        const auto&first=r.work_items[base];
        const auto sid=first.surface_id;
        const auto tile=first.tile_id;
        const auto output_base=first.output_id;

        if(tile>=tiles ||
           sid>=scene.samples.size() ||
           r.tile_owner[tile]!=sid ||
           seen_tile[tile]){
            a.producer_correct=false;
            a.errors.push_back("producer emitted invalid/duplicate visible surface block");
            continue;
        }
        seen_tile[tile]=true;
        const V3 position=surface_pos(scene.samples[sid]);

        for(std::uint32_t cascade=0;cascade<settings.cascade_count;++cascade){
            const float spacing=p.scene_origin_spacing[3]*float(1u<<cascade);
            const std::int32_t px=std::int32_t(std::floor((position.x-p.scene_origin_spacing[0])/spacing));
            const std::int32_t py=std::int32_t(std::floor((position.y-p.scene_origin_spacing[1])/spacing));
            const std::int32_t pz=std::int32_t(std::floor((position.z-p.scene_origin_spacing[2])/spacing));
            const float ppx=p.scene_origin_spacing[0]+(float(px)+0.5f)*spacing;
            const float ppy=p.scene_origin_spacing[1]+(float(py)+0.5f)*spacing;
            const float ppz=p.scene_origin_spacing[2]+(float(pz)+0.5f)*spacing;
            const float interval_max=p.light_pos_interval[3]*float(1u<<cascade);
            const float interval_min=cascade
                ? p.light_pos_interval[3]*float(1u<<(cascade-1u))
                : 0.0f;

            for(std::uint32_t ray=0;ray<settings.rays_per_probe;++ray){
                const auto&i=r.work_items[base+cascade*settings.rays_per_probe+ray];
                const auto rd=ray_direction(ray);
                ++a.locality.items_per_cascade[cascade];

                const bool ok=
                    i.surface_id==sid &&
                    i.tile_id==tile &&
                    i.cascade==cascade &&
                    i.ray_index==ray &&
                    i.output_id==output_base+cascade &&
                    i.probe_x==px &&
                    i.probe_y==py &&
                    i.probe_z==pz &&
                    std::abs(i.interval_min-interval_min)<1e-5f &&
                    std::abs(i.interval_max-interval_max)<1e-5f &&
                    std::abs(i.dir_x-rd.x)<1e-6f &&
                    std::abs(i.dir_y-rd.y)<1e-6f &&
                    std::abs(i.dir_z-rd.z)<1e-6f &&
                    within_float_ulps(i.probe_px,ppx,2) &&
                    within_float_ulps(i.probe_py,ppy,2) &&
                    within_float_ulps(i.probe_pz,ppz,2);
                ++semantic_checks;
                if(!ok){
                    a.producer_correct=false;
                    ++semantic_failures;
                    if(semantic_failures<=4){
                        std::ostringstream detail;
                        detail<<std::setprecision(9)
                            <<"producer semantic mismatch item="
                            <<(base+cascade*settings.rays_per_probe+ray)
                            <<" actual={sid:"<<i.surface_id
                            <<",tile:"<<i.tile_id
                            <<",cascade:"<<i.cascade
                            <<",ray:"<<i.ray_index
                            <<",output:"<<i.output_id
                            <<",probe:["<<i.probe_x<<","<<i.probe_y<<","<<i.probe_z<<"]"
                            <<",interval:["<<i.interval_min<<","<<i.interval_max<<"]"
                            <<",dir:["<<i.dir_x<<","<<i.dir_y<<","<<i.dir_z<<"]"
                            <<",pos:["<<i.probe_px<<","<<i.probe_py<<","<<i.probe_pz<<"]}"
                            <<" expected={sid:"<<sid
                            <<",tile:"<<tile
                            <<",cascade:"<<cascade
                            <<",ray:"<<ray
                            <<",output:"<<(output_base+cascade)
                            <<",probe:["<<px<<","<<py<<","<<pz<<"]"
                            <<",interval:["<<interval_min<<","<<interval_max<<"]"
                            <<",dir:["<<rd.x<<","<<rd.y<<","<<rd.z<<"]"
                            <<",pos:["<<ppx<<","<<ppy<<","<<ppz<<"]}";
                        a.errors.push_back(detail.str());
                    }
                }
            }

            const auto output_id=output_base+cascade;
            if(output_id>=seen_output.size() || seen_output[output_id]){
                a.producer_correct=false;
                a.errors.push_back("output identity is out of range or duplicated");
            }else{
                seen_output[output_id]=true;
            }
        }
    }

    if(semantic_failures){
        a.errors.push_back(
            "producer semantic reference mismatches: "+
            std::to_string(semantic_failures)+"/"+
            std::to_string(semantic_checks));
    }

    for(std::uint32_t tile=0;tile<tiles;++tile){
        if(r.tile_owner[tile]!=INVALID && !seen_tile[tile]){
            a.producer_correct=false;
            a.errors.push_back("visible tile did not emit a producer block");
            break;
        }
    }

    if(std::find(seen_output.begin(),seen_output.end(),false)!=seen_output.end()){
        a.producer_correct=false;
        a.errors.push_back("producer output identity space has holes");
    }

    std::vector<std::uint64_t>sums(r.resolved.size());
    std::vector<std::uint32_t>counts(r.resolved.size());
    for(const auto&i:r.work_items){
        if(i.output_id<r.resolved.size()){
            sums[i.output_id]+=quantized_contribution(i,p);
            ++counts[i.output_id];
        }
    }

    for(std::size_t i=0;i<r.resolved.size();++i){
        const float expected=counts[i]
            ? float(sums[i])/(float(counts[i])*65535.0f)
            : 0.0f;
        const float error=std::abs(r.resolved[i]-expected);
        a.max_resolve_abs_error=std::max(a.max_resolve_abs_error,error);
        if(error>2e-6f){
            a.resolve_correct=false;
            a.errors.push_back("resolve output differs from CPU reference");
            break;
        }
    }

    for(std::size_t i=0;i<r.work_items.size();++i){
        if(i==0){
            a.locality.probe_runs=1;
            continue;
        }
        const auto&x=r.work_items[i];
        const auto&previous=r.work_items[i-1];
        ++a.locality.adjacent_pairs;

        const bool same_probe=
            x.cascade==previous.cascade &&
            x.probe_x==previous.probe_x &&
            x.probe_y==previous.probe_y &&
            x.probe_z==previous.probe_z;
        if(same_probe) ++a.locality.same_probe_pairs;
        else ++a.locality.probe_runs;

        if(x.cascade==previous.cascade)
            ++a.locality.same_cascade_pairs;

        if(x.cascade==previous.cascade &&
           std::max({
               std::abs(x.probe_x-previous.probe_x),
               std::abs(x.probe_y-previous.probe_y),
               std::abs(x.probe_z-previous.probe_z)})<=1)
            ++a.locality.neighboring_probe_pairs;

        const auto ax=x.tile_id%settings.tile_width;
        const auto ay=x.tile_id/settings.tile_width;
        const auto bx=previous.tile_id%settings.tile_width;
        const auto by=previous.tile_id/settings.tile_width;
        if((ax>bx?ax-bx:bx-ax)+(ay>by?ay-by:by-ay)<=1)
            ++a.locality.neighboring_tile_pairs;
    }

    return a;
}

void write_a001_artifacts(
    const std::filesystem::path&dir,
    const SceneSurfaceSet&,
    const A001Settings&s,
    const A001ParamsGpu&,
    const A001Timings&t,
    const A001Memory&mem,
    const A001Readback&r,
    const A001Analysis&a,
    const std::string&gpu,
    const std::string&commit){
    std::filesystem::create_directories(dir);

    std::ofstream metrics(dir/"metrics.json");
    metrics<<std::setprecision(10)
     <<"{\n"
     <<"  \"case\": \""<<case_name(s.case_id)<<"\",\n"
     <<"  \"gpu\": \""<<json_escape(gpu)<<"\",\n"
     <<"  \"git_commit\": \""<<json_escape(commit)<<"\",\n"
     <<"  \"visible_probe_count\": "<<a.visible_probe_count<<",\n"
     <<"  \"work_item_count\": "<<r.work_items.size()<<",\n"
     <<"  \"output_count\": "<<r.resolved.size()<<",\n"
     <<"  \"correctness\": {"
     <<"\"visibility\": "<<(a.visibility_correct?"true":"false")<<", "
     <<"\"producer\": "<<(a.producer_correct?"true":"false")<<", "
     <<"\"resolve\": "<<(a.resolve_correct?"true":"false")<<", "
     <<"\"max_resolve_abs_error\": "<<a.max_resolve_abs_error<<"},\n"
     <<"  \"locality\": {"
     <<"\"same_probe_adjacent_ratio\": "<<ratio(a.locality.same_probe_pairs,a.locality.adjacent_pairs)<<", "
     <<"\"same_cascade_adjacent_ratio\": "<<ratio(a.locality.same_cascade_pairs,a.locality.adjacent_pairs)<<", "
     <<"\"neighboring_probe_adjacent_ratio\": "<<ratio(a.locality.neighboring_probe_pairs,a.locality.adjacent_pairs)<<", "
     <<"\"neighboring_tile_adjacent_ratio\": "<<ratio(a.locality.neighboring_tile_pairs,a.locality.adjacent_pairs)<<", "
     <<"\"mean_probe_run\": "<<(a.locality.probe_runs?double(r.work_items.size())/double(a.locality.probe_runs):0.0)<<"},\n"
     <<"  \"memory\": {"
     <<"\"persistent_bytes\": "<<mem.persistent_bytes<<", "
     <<"\"transient_bytes\": "<<mem.transient_bytes<<", "
     <<"\"resident_bytes\": "<<mem.resident_bytes<<", "
     <<"\"max_stream_bytes\": "<<mem.max_stream_bytes<<"},\n"
     <<"  \"timings_us\": {"
     <<"\"visibility_depth\": "<<t.visibility_depth_us<<", "
     <<"\"visibility_owner\": "<<t.visibility_owner_us<<", "
     <<"\"producer_emit\": "<<t.producer_emit_us<<", "
     <<"\"finalize\": "<<t.finalize_us<<", "
     <<"\"producer_total\": "<<t.producer_total_us<<", "
     <<"\"gather\": "<<t.gather_us<<", "
     <<"\"merge\": "<<t.merge_us<<", "
     <<"\"resolve\": "<<t.resolve_us<<", "
     <<"\"end_to_end\": "<<t.end_to_end_us<<"},\n"
     <<"  \"items_per_cascade\": [";
    for(std::size_t i=0;i<a.locality.items_per_cascade.size();++i){
        if(i) metrics<<", ";
        metrics<<a.locality.items_per_cascade[i];
    }
    metrics<<"],\n  \"errors\": [";
    for(std::size_t i=0;i<a.errors.size();++i){
        if(i) metrics<<", ";
        metrics<<"\""<<json_escape(a.errors[i])<<"\"";
    }
    metrics<<"]\n}\n";

    if(!a.correct()) return;

    if constexpr(std::endian::native!=std::endian::little)
        throw std::runtime_error("A001 stream v1 exporter requires little-endian host");

    SplitRcStreamHeaderV1 header{};
    header.item_bytes=sizeof(SplitRcWorkItemV1);
    header.frame_id=s.frame_id;
    header.item_count=static_cast<std::uint32_t>(r.work_items.size());
    header.output_count=static_cast<std::uint32_t>(r.resolved.size());
    header.cascade_count=s.cascade_count;
    header.rays_per_probe=s.rays_per_probe;
    header.tile_width=s.tile_width;
    header.tile_height=s.tile_height;
    header.workload_id=fnv1a(
        r.work_items.data(),
        r.work_items.size()*sizeof(SplitRcWorkItemV1));

    std::ofstream binary(dir/"stream-v1.bin",std::ios::binary|std::ios::trunc);
    binary.write(reinterpret_cast<const char*>(&header),sizeof(header));
    binary.write(
        reinterpret_cast<const char*>(r.work_items.data()),
        std::streamsize(r.work_items.size()*sizeof(SplitRcWorkItemV1)));
    if(!binary) throw std::runtime_error("Could not write A001 stream");

    std::ofstream manifest(dir/"stream-v1.json");
    manifest<<"{\n"
     <<"  \"schema_version\": 1,\n"
     <<"  \"header_bytes\": 64,\n"
     <<"  \"item_bytes\": 64,\n"
     <<"  \"item_count\": "<<header.item_count<<",\n"
     <<"  \"output_count\": "<<header.output_count<<",\n"
     <<"  \"workload_id\": "<<header.workload_id<<",\n"
     <<"  \"case\": \""<<case_name(s.case_id)<<"\",\n"
     <<"  \"git_commit\": \""<<json_escape(commit)<<"\"\n"
     <<"}\n";
}

} // namespace phos::gi::lane_a

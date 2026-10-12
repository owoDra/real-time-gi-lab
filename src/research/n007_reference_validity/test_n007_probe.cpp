#include "n007_probe_audit.hpp"
#include <cassert>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

namespace n=phos::gi::research::n007;
namespace b=phos::gi::research::lane_b;
namespace fs=std::filesystem;
template<class T>void dump(const fs::path& path,const T& item) {
    std::ofstream f(path,std::ios::binary);
    assert(f);
    f.write(reinterpret_cast<const char*>(&item),sizeof(item));
    assert(f);
}
int main() {
    // Probe hits z=3; offset shadow ray to the light intersects occluder z=2.
    const std::vector<b::Triangle> triangles{
        {{-1,-1,3},{1,-1,3},{0,1,3},7,2,3,true},
        {{.35F,-1,2},{.9F,-1,2},{.6F,1,2},8,2,3,true}
    };
    n::FrameParams p{};
    p.camera_pos_near={0,0,0,.01F};
    p.camera_forward_far={0,0,1,10};
    p.light_pos_interval={2,0,0,.5F};
    b::LaneAWorkItemV1 work{};
    work.output_id=9;
    work.interval_min=0;work.interval_max=10;
    work.dir_z=1;work.probe_pz=0;
    b::GpuHit gpu{};
    gpu.normal_t[0]=0;gpu.normal_t[1]=0;gpu.normal_t[2]=1;gpu.normal_t[3]=3;
    gpu.metadata[0]=7;gpu.metadata[1]=2;gpu.metadata[2]=3;gpu.metadata[3]=1;
    const float distance2=13.0F;
    const float cos=3.0F/std::sqrt(distance2);
    const float unshadowed=cos*(.25F/(.25F+distance2))/3.14159265358979323846F;
    const std::array<std::uint32_t,2> fixed{
        9,std::uint32_t(std::lround(unshadowed*65535.0F))};
    assert(fixed[1]>0);
    const auto path=fs::temp_directory_path()/"n007-probe-cpu-unit";
    fs::create_directories(path);
    dump(path/"probe-work.bin",work);
    dump(path/"probe-hits.bin",gpu);
    dump(path/"probe-contributions.bin",fixed);
    std::vector<std::uint8_t> labels;
    const auto outcome=n::audit_gpu_probe_transport(path,triangles,p,1,&labels);
    assert(labels.size()==1&&labels[0]==1U);
    assert(outcome.work_items==1);
    assert(outcome.gpu_hit_items==1);
    assert(outcome.gpu_traversal_mismatches==0);
    assert(outcome.gpu_positive_contributions==1);
    assert(outcome.gpu_positive_matched_traversal==1);
    assert(outcome.gpu_positive_shadow_blocked==1);
    assert(outcome.gpu_positive_shadow_clear==0);
    assert(outcome.gpu_positive_replay_candidate==1);
    assert(outcome.gpu_positive_fixed_prediction_mismatches==0);
    fs::remove_all(path);
    std::cout<<"N007 controlled GPU-probe shadow replay test PASS\n";
}

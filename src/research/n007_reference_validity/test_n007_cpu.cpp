#include "n007_cpu_components.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace phos::gi::research;
int main() {
    n007::FrameParams p{};
    p.camera_pos_near={0,0,0,0.01F};
    p.camera_forward_far={0,0,1,10};
    p.camera_right_tan_x={1,0,0,0};
    p.camera_up_tan_y={0,1,0,0};
    p.light_pos_interval={0,0,0,0.5F};
    std::vector<lane_b::Triangle> triangles{
        {{-2,-2,3},{2,-2,3},{0,2,3},7,2,3,true}};
    const auto sample=n007::capture_cpu(triangles,p,1,1,4,305419896,2);
    assert(sample.primary[0].metadata[0]==7);
    assert(sample.primary[0].metadata[3]==1);
    assert(std::abs(sample.primary[0].normal_t[3]-3.0F)<1e-5F);
    assert(sample.counts.primary_hits==4);
    assert(sample.counts.shadow_tested==
           sample.counts.shadow_blocked+sample.counts.shadow_clear);
    assert(std::abs(sample.direct[0]+sample.indirect[0]-sample.total[0])<1e-6F);
    p.camera_forward_far={0,0,-1,10};
    const auto miss=n007::capture_cpu(triangles,p,1,1,2,305419896,2);
    assert(miss.primary[0].metadata[0]==lane_b::kInvalidId);
    assert(std::isinf(miss.primary[0].normal_t[3]));
    assert(miss.total[0]==0);
    bool threw=false;
    try {(void)n007::capture_cpu(triangles,p,0,1,1,1);}
    catch(const std::invalid_argument&) {threw=true;}
    assert(threw);
    std::cout<<"N007 CPU controlled hit/miss/transport/counter tests PASS\n";
}

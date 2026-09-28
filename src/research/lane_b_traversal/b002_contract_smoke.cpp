#include "hierarchical_stratabrick.hpp"
#include "lane_a_stream_v1.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
using namespace phos::gi::research::lane_b;
int main(){
 std::vector<Triangle> t;
 auto add=[&](float x,float z,std::uint32_t id){t.push_back({{x-1,-1,z},{x+1,-1,z},{x,1,z},id,id+10,id+20,true});};
 add(0,5,0);add(9,12,1);add(-8,18,2);
 HierarchicalStrataBrick h(t,8.0F);
 std::vector<Ray> rays{{{0,0,0},{0,0,1},30},{{9,0,0},{0,0,1},30},{{-8,0,0},{0,0,1},30},{{0,5,0},{0,1,0},30}};
 for(auto r:rays){auto a=trace_reference(t,r),b=h.trace(r);if(!equivalent_hit(a,b)){std::cerr << "hierarchical static mismatch\n"; return 2;}}
 auto moved=t;moved[0].v0.x+=9;moved[0].v1.x+=9;moved[0].v2.x+=9;std::uint32_t m=0;auto s=h.update(moved,std::span<const std::uint32_t>(&m,1));
 for(auto r:rays){auto a=trace_reference(moved,r),b=h.trace(r);if(!equivalent_hit(a,b)){std::cerr << "hierarchical update mismatch\n"; return 3;}}
 LaneAReplayStreamV1 stream;stream.header.item_bytes=64;stream.header.item_count=1;stream.header.output_count=1;stream.header.cascade_count=1;stream.header.rays_per_probe=1;stream.header.tile_width=1;stream.header.tile_height=1;stream.items.resize(1);auto&i=stream.items[0];i.interval_min=2;i.interval_max=10;i.dir_z=1;i.probe_px=3;i.probe_py=4;i.probe_pz=5;stream.header.workload_id=lane_a_workload_id(stream.items.data(),64);
 auto p=std::filesystem::temp_directory_path()/"phos-b002-smoke-stream.bin";{std::ofstream o(p,std::ios::binary);o.write((char*)&stream.header,64);o.write((char*)stream.items.data(),64);}auto loaded=load_lane_a_stream_v1(p);auto rr=lane_a_item_to_ray(loaded.items[0]);std::filesystem::remove(p);if(rr.origin.z!=7||rr.t_max!=8)return 4;
 std::cout << "B002 contract smoke: PASS segments=" << h.segment_count() << " membership_changes=" << s.membership_changes << "\n"; return 0;
}

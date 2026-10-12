// N007 CPU-only replay from captured state and actual GPU secondary payloads.
// Existing original capture files remain immutable. Writes only a derived mask.
#include "n007_probe_audit.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs=std::filesystem;
namespace n=phos::gi::research::n007;
namespace b=phos::gi::research::lane_b;
namespace {
template<class T> void read(std::ifstream& stream,T& value) {
    static_assert(std::is_trivially_copyable_v<T>);
    if(!stream.read(reinterpret_cast<char*>(&value),sizeof(value)))
        throw std::runtime_error("N007 capture unexpectedly truncated");
}
struct alignas(16) Params {
    std::array<float,4> camera_pos_near{},camera_right_tan_x{},
        camera_up_tan_y{},camera_forward_far{},scene_origin_spacing{},
        light_pos_interval{};
    std::array<std::uint32_t,4> counts{},limits{};
};
static_assert(sizeof(Params)==128);
n::FrameParams load_params(const fs::path& path) {
    if(!fs::is_regular_file(path)||fs::file_size(path)!=148)
        throw std::runtime_error("N007 frame-state.bin must be 148 bytes");
    std::ifstream in(path,std::ios::binary);
    std::array<char,12> marker{};
    read(in,marker);
    constexpr std::array<char,12> valid{'N','0','0','7','-','S','T','A','T','E','1','\0'};
    if(marker!=valid)throw std::runtime_error("N007 frame-state magic mismatch");
    std::uint32_t width{},height{};
    read(in,width);read(in,height);
    if(width!=320||height!=180)
        throw std::runtime_error("N007 frame state dimensions do not match frozen 320x180");
    Params source{};read(in,source);
    n::FrameParams out{};
    out.camera_pos_near=source.camera_pos_near;
    out.camera_right_tan_x=source.camera_right_tan_x;
    out.camera_up_tan_y=source.camera_up_tan_y;
    out.camera_forward_far=source.camera_forward_far;
    out.light_pos_interval=source.light_pos_interval;
    return out;
}
std::vector<b::Triangle> load_triangles(const fs::path& path) {
    if(!fs::is_regular_file(path)||fs::file_size(path)<8)
        throw std::runtime_error("N007 geometry-state.bin missing/short");
    std::ifstream in(path,std::ios::binary);
    std::uint32_t version{},count{};
    read(in,version);read(in,count);
    if(version!=1||count==0||count>100000000U||
        fs::file_size(path)!=8ULL+std::uint64_t(count)*52ULL)
        throw std::runtime_error("N007 CPU geometry-state record length mismatch");
    std::vector<b::Triangle> tris;tris.reserve(count);
    for(std::uint32_t k=0;k<count;++k) {
        std::array<float,9> coords{};
        std::array<std::uint32_t,4> ids{};
        read(in,coords);read(in,ids);
        if(ids[0]!=k||ids[3]>1U)
            throw std::runtime_error("N007 CPU geometry primitive ordering/side flag invalid");
        for(auto v:coords)if(!std::isfinite(v))
            throw std::runtime_error("N007 CPU geometry contains nonfinite coordinates");
        tris.push_back({{coords[0],coords[1],coords[2]},
                       {coords[3],coords[4],coords[5]},
                       {coords[6],coords[7],coords[8]},
                       ids[0],ids[1],ids[2],ids[3]!=0U});
    }
    return tris;
}
}
int main(int argc,char** argv) {
    try {
        if(argc!=3||std::string(argv[1])!="--capture")
            throw std::invalid_argument("usage: phos-n007-probe-offline --capture CAPTURE_DIR");
        static_assert(std::endian::native==std::endian::little);
        const fs::path root=argv[2],gpu=root/"gpu";
        const auto p=load_params(root/"frame-state.bin");
        auto geometry=load_triangles(root/"geometry-state.bin");
        const auto work=gpu/"probe-work.bin";
        if(!fs::is_regular_file(work)||fs::file_size(work)%sizeof(b::LaneAWorkItemV1))
            throw std::runtime_error("N007 GPU work stream missing/misaligned");
        const auto count=std::size_t(fs::file_size(work)/sizeof(b::LaneAWorkItemV1));
        if(count>100000000ULL)
            throw std::runtime_error("N007 GPU work stream unreasonable");
        std::vector<std::uint8_t> labels;
        const auto audit=n::audit_gpu_probe_transport(gpu,geometry,p,count,&labels);
        if(audit.gpu_traversal_mismatches||audit.invalid_gpu_hit_flags||
           audit.invalid_contribution_ids||audit.gpu_positive_fixed_prediction_mismatches)
            throw std::runtime_error("N007 probe replay failed; shadow counterfactual prohibited");
        const auto output=gpu/"probe-shadow-flags.bin";
        if(fs::exists(output))
            throw std::runtime_error("N007 derived shadow flag file already exists; refusing overwrite");
        std::ofstream out(output,std::ios::binary);
        if(!out||!out.write(reinterpret_cast<const char*>(labels.data()),
                           std::streamsize(labels.size())))
            throw std::runtime_error("N007 shadow flag output write failed");
        out.close();
        if(!out)throw std::runtime_error("N007 shadow flag close failed");
        std::cout<<"{\"classification\":\"diagnostic-only\","
                 <<"\"work_items\":"<<count
                 <<",\"shadow_blocked_positive\":"<<audit.gpu_positive_shadow_blocked
                 <<",\"shadow_clear_positive\":"<<audit.gpu_positive_shadow_clear
                 <<",\"gpu_positive_contributions\":"<<audit.gpu_positive_contributions
                 <<",\"source_payload_replay_mismatches\":0,"
                 <<"\"output\":\""<<output.string()<<"\"}\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"N007 offline probe: "<<e.what()<<'\n';
        return 1;
    }
}

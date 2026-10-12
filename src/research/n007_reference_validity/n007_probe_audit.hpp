#pragma once
// N007-only CPU replay of the actual GPU probe work/hit/contribution payloads.
// Does NOT alter the historical GPU renderer or its transport assumptions.
#include "n007_cpu_components.hpp"
#include "../lane_n_end_to_end_renderer/imported/lane_b_traversal/lane_a_stream_v1.hpp"
#include "../lane_n_end_to_end_renderer/imported/lane_b_traversal/b002_gpu_layout.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace phos::gi::research::n007 {
namespace fs=std::filesystem;
template <class T>
std::vector<T> read_gpu_probe_bytes(const fs::path& file,std::size_t n) {
    if(!fs::is_regular_file(file) || fs::file_size(file)!=n*sizeof(T))
        throw std::runtime_error("N007 GPU probe payload length mismatch: "+file.string());
    std::vector<T> values(n);
    std::ifstream input(file,std::ios::binary);
    if(!input)throw std::runtime_error("N007 GPU probe payload read open failed");
    if(n)input.read(reinterpret_cast<char*>(values.data()),
                    std::streamsize(n*sizeof(T)));
    if(!input && n)throw std::runtime_error("N007 GPU probe payload read failed");
    return values;
}
struct ProbeAudit {
    std::uint64_t work_items{}, gpu_hit_items{}, gpu_positive_contributions{};
    std::uint64_t gpu_traversal_mismatches{},gpu_positive_traversal_mismatches{};
    std::uint64_t gpu_positive_matched_traversal{},gpu_positive_shadow_blocked{};
    std::uint64_t gpu_positive_shadow_clear{},gpu_positive_other_zero{};
    std::uint64_t gpu_positive_fixed_prediction_mismatches{};
    std::uint64_t gpu_positive_replay_candidate{};
    std::uint64_t zero_gpu_but_positive_unshadowed{};
    std::uint64_t invalid_gpu_hit_flags{},invalid_contribution_ids{};
};
// Audit is diagnostic: GPU producer traces only eight discrete directions per
// cascade; N001 CPU reference traces cosine rays. No equivalence claim follows.
inline ProbeAudit audit_gpu_probe_transport(
    const fs::path& gpu_dir,const std::vector<b::Triangle>& triangles,
    const FrameParams& p,std::size_t work_count) {
    using Work=b::LaneAWorkItemV1;
    using Hit=b::GpuHit;
    using Fixed=std::array<std::uint32_t,2>;
    static_assert(sizeof(Work)==64&&sizeof(Hit)==32&&sizeof(Fixed)==8);
    const auto work=read_gpu_probe_bytes<Work>(gpu_dir/"probe-work.bin",work_count);
    const auto hits=read_gpu_probe_bytes<Hit>(gpu_dir/"probe-hits.bin",work_count);
    const auto fixed=read_gpu_probe_bytes<Fixed>(gpu_dir/"probe-contributions.bin",work_count);
    const b::SoftwareBvh bvh(triangles);
    ProbeAudit out{};
    out.work_items=work_count;
    constexpr float pi=3.14159265358979323846F;
    for(std::size_t k=0;k<work_count;++k) {
        const auto& item=work[k];
        const auto& g=hits[k];
        const bool gpu_positive=fixed[k][1]!=0U;
        if(fixed[k][0]!=item.output_id || fixed[k][1]>65535U)
            ++out.invalid_contribution_ids;
        if(g.metadata[3]>1U) {++out.invalid_gpu_hit_flags;continue;}
        if(g.metadata[3]==1U)++out.gpu_hit_items;
        if(gpu_positive)++out.gpu_positive_contributions;
        // Reconstruct exact GPU ray generation from its actual work item.
        const auto ray=b::lane_a_item_to_ray(item);
        const auto cpu_hit=bvh.trace(ray);
        const auto gpu_hit=b::from_gpu_hit(g);
        const bool traversal_match=b::equivalent_hit(cpu_hit,gpu_hit);
        if(!traversal_match) {
            ++out.gpu_traversal_mismatches;
            if(gpu_positive)++out.gpu_positive_traversal_mismatches;
            continue;
        }
        if(!gpu_hit.hit)continue;
        const auto incoming=ray.direction;
        const b::Vec3 pos=vec({item.probe_px,item.probe_py,item.probe_pz,0})+
            incoming*(item.interval_min+g.normal_t[3]);
        const auto normal=forward({g.normal_t[0],g.normal_t[1],g.normal_t[2]},incoming);
        const auto light=vec(p.light_pos_interval)-pos;
        const float d2=b::dot(light,light);
        float unshadowed=0.0F;
        if(std::isfinite(d2)&&d2>1.e-12F) {
            const float cosine=std::max(0.0F,b::dot(normal,light/std::sqrt(d2)));
            const float scale=std::max(p.light_pos_interval[3],1.e-6F);
            unshadowed=cosine*((scale*scale)/(scale*scale+d2))/pi;
        }
        const auto predicted=std::uint32_t(std::lround(
            std::clamp(unshadowed,0.0F,1.0F)*65535.0F));
        if(gpu_positive) {
            ++out.gpu_positive_matched_traversal;
            if(std::abs(std::int64_t(predicted)-std::int64_t(fixed[k][1]))>1)
                ++out.gpu_positive_fixed_prediction_mismatches;
            ShadowStats visibility{};
            const auto shadowed=lambert(bvh,p,pos,normal,visibility);
            if(visibility.shadow_blocked)++out.gpu_positive_shadow_blocked;
            else if(shadowed>0)++out.gpu_positive_shadow_clear;
            else ++out.gpu_positive_other_zero;
            if(visibility.shadow_blocked&&predicted>0U)
                ++out.gpu_positive_replay_candidate;
        } else if(predicted>0U) {
            ++out.zero_gpu_but_positive_unshadowed;
        }
    }
    return out;
}
} // namespace phos::gi::research::n007

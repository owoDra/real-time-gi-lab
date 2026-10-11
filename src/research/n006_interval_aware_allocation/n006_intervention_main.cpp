#include "n006_runtime.hpp"
#include "../lane_n_end_to_end_renderer/n001_reference.hpp"

#include <algorithm>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace fs = std::filesystem;
namespace lane_n = phos::gi::research::integration;

namespace {

[[nodiscard]] std::vector<float> rgb_from_rgba(
    const lane_n::I001RendererReadback& frame) {
    const auto pixels = std::size_t(frame.width) * frame.height;
    if (frame.image_rgba.size() != pixels * 4U) {
        throw std::runtime_error("N006 RGBA payload size mismatch");
    }
    std::vector<float> rgb(pixels * 3U);
    for (std::size_t pixel = 0; pixel < pixels; ++pixel) {
        for (std::size_t channel = 0; channel < 3U; ++channel) {
            rgb[pixel * 3U + channel] = frame.image_rgba[pixel * 4U + channel];
        }
    }
    return rgb;
}

void write_pfm(
    const fs::path& path,
    std::uint32_t width,
    std::uint32_t height,
    const std::vector<float>& rgb) {
    static_assert(std::endian::native == std::endian::little);
    if (rgb.size() != std::size_t(width) * height * 3U) {
        throw std::runtime_error("N006 PFM payload size mismatch");
    }
    fs::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("could not open N006 PFM");
    out << "PF\n" << width << ' ' << height << "\n-1.0\n";
    const auto row_floats = std::size_t(width) * 3U;
    for (std::uint32_t y = height; y-- > 0U;) {
        const auto* row = rgb.data() + std::size_t(y) * row_floats;
        out.write(
            reinterpret_cast<const char*>(row),
            std::streamsize(row_floats * sizeof(float)));
    }
    if (!out) throw std::runtime_error("N006 PFM write failed");
}

[[nodiscard]] std::string indexed_path(
    const char* prefix,
    std::uint32_t index) {
    std::ostringstream out;
    out << "frames/" << prefix << '-' << std::setw(3) << std::setfill('0')
        << index << ".pfm";
    return out.str();
}

template <typename T>
[[nodiscard]] std::vector<T> parse_csv(const std::string& raw) {
    std::vector<T> values;
    std::stringstream stream(raw);
    std::string token;
    while (std::getline(stream, token, ',')) {
        if (token.empty()) {
            throw std::runtime_error("N006 CSV contains an empty item");
        }
        if constexpr (std::is_same_v<T, float>) {
            values.push_back(std::stof(token));
        } else {
            values.push_back(static_cast<T>(std::stoul(token)));
        }
    }
    return values;
}

[[nodiscard]] lane_n::N006ExtraMode parse_mode(std::string_view value) {
    if (value == "current") return lane_n::N006ExtraMode::Current;
    if (value == "uniform-extra-rays") return lane_n::N006ExtraMode::Uniform;
    if (value == "targeted-extra-rays") return lane_n::N006ExtraMode::Targeted;
    throw std::runtime_error("unknown N006 mode");
}

[[nodiscard]] const char* mode_name(lane_n::N006ExtraMode value) noexcept {
    switch (value) {
    case lane_n::N006ExtraMode::Current: return "current";
    case lane_n::N006ExtraMode::Uniform: return "uniform-extra-rays";
    case lane_n::N006ExtraMode::Targeted: return "targeted-extra-rays";
    }
    return "unknown";
}

struct ReferenceMeta {
    std::string path;
    std::uint32_t spp{};
    double p99_abs{};
    double p99_relative{};
};

[[nodiscard]] ReferenceMeta render_reference(
    const lane_n::I001RendererReadback& readback,
    const fs::path& artifact_dir,
    const std::string& relative_path,
    const lane_n::N001ReferenceSettings& settings = {}) {
    const auto result = lane_n::n001_render_reference(readback, settings);
    if (!result.converged) {
        throw std::runtime_error("N006 reference did not converge");
    }
    write_pfm(
        artifact_dir / relative_path,
        readback.width,
        readback.height,
        result.rgb);
    return {
        relative_path,
        result.spp,
        result.replicate_p99_abs_luminance,
        result.replicate_p99_relative_luminance,
    };
}

void write_reference(
    std::ostream& out,
    const ReferenceMeta& reference) {
    out << std::setprecision(17)
        << "{\"path\":\"" << reference.path << "\","
        << "\"spp\":" << reference.spp << ','
        << "\"converged\":true,"
        << "\"replicate_p99_abs_luminance\":" << reference.p99_abs << ','
        << "\"replicate_p99_relative_luminance\":" << reference.p99_relative
        << '}';
}

void write_timing(
    std::ostream& out,
    const lane_n::I001FrameTimings& t,
    double extra_producer_gpu_us) {
    out << std::setprecision(17)
        << "{\"complete_gi_gpu\":" << t.complete_gpu_us << ','
        << "\"complete_renderer_gpu\":" << t.complete_renderer_gpu_us << ','
        << "\"extra_producer_gpu\":" << extra_producer_gpu_us << ','
        << "\"primary_visibility_gpu\":" << t.primary_visibility_us << ','
        << "\"renderer_depth_gpu\":" << t.renderer_depth_us << ','
        << "\"frame_init_gpu\":" << t.frame_init_us << ','
        << "\"visibility_reuse_gpu\":" << t.visibility_reuse_us << ','
        << "\"traversal_maintenance_gpu\":" << t.traversal_maintenance_gpu_us << ','
        << "\"invalidation_gpu\":" << t.invalidation_us << ','
        << "\"composite_gpu\":" << t.composite_us << ','
        << "\"producer_gpu\":" << t.producer_us << ','
        << "\"ray_prepare_gpu\":" << t.ray_prepare_us << ','
        << "\"traversal_gpu\":" << t.traversal_us << ','
        << "\"radiance_gpu\":" << t.radiance_us << ','
        << "\"merge_gpu\":" << t.merge_us << ','
        << "\"storage_update_gpu\":" << t.storage_update_us << ','
        << "\"resolve_gpu\":" << t.resolve_us << ','
        << "\"dynamic_update_wall\":" << t.dynamic_update_wall_us << ','
        << "\"geometry_transfer_gpu\":" << t.geometry_transfer_gpu_us << ','
        << "\"instance_transfer_gpu\":" << t.instance_transfer_gpu_us << ','
        << "\"blas_update_gpu\":" << t.blas_update_us << ','
        << "\"tlas_update_gpu\":" << t.tlas_update_us
        << '}';
}

void write_stats(
    std::ostream& out,
    const lane_n::I001FrameStats& s) {
    out << "{\"work_items\":" << s.work_items << ','
        << "\"outputs\":" << s.outputs << ','
        << "\"overflow\":" << s.overflow << ','
        << "\"visible_owners\":" << s.visible_owners << ','
        << "\"moved_primitives\":" << s.moved_primitives << ','
        << "\"topology_mutations\":" << s.topology_mutations << ','
        << "\"topology_replaced_primitives\":" << s.topology_replaced_primitives << ','
        << "\"backend_rebuilds\":" << s.backend_rebuilds << ','
        << "\"storage_allocations\":" << s.storage_allocations << ','
        << "\"storage_updates\":" << s.storage_updates << ','
        << "\"storage_invalidations\":" << s.storage_invalidations << ','
        << "\"storage_failures\":" << s.storage_failures
        << '}';
}

void write_memory(
    std::ostream& out,
    const lane_n::I001Memory& m) {
    out << "{\"persistent\":" << m.persistent_bytes << ','
        << "\"transient\":" << m.transient_bytes << ','
        << "\"scratch\":" << m.scratch_bytes << ','
        << "\"old_new_overlap\":" << m.old_new_overlap_bytes << ','
        << "\"true_lifetime_peak\":" << m.peak_resident_bytes << ','
        << "\"radiance_storage_persistent\":" << m.storage_capacity_bytes << ','
        << "\"producer_stream_capacity\":" << m.stream_capacity_bytes << ','
        << "\"image_transient\":" << m.image_bytes
        << '}';
}

void write_extra(
    std::ostream& out,
    const lane_n::N006ExtraStats& e) {
    out << std::setprecision(17)
        << "{\"base_traced_rays\":" << e.base_traced_rays << ','
        << "\"extra_rays_requested\":" << e.extra_rays_requested << ','
        << "\"extra_rays_traced\":" << e.extra_rays_traced << ','
        << "\"extra_work_items\":" << e.extra_work_items << ','
        << "\"eligible_owner_count\":" << e.eligible_owner_count << ','
        << "\"selected_owner_count\":" << e.selected_owner_count << ','
        << "\"eligible_probe_count\":" << e.eligible_probe_count << ','
        << "\"extra_probe_count\":" << e.extra_probe_count << ','
        << "\"extra_probe_fraction\":" << e.extra_probe_fraction << ','
        << "\"extra_producer_gpu_us\":" << e.extra_producer_gpu_us << ','
        << "\"base_prefix_correct\":" << (e.base_prefix_correct ? "true" : "false") << ','
        << "\"extra_work_correct\":" << (e.extra_work_correct ? "true" : "false")
        << ",\"influence_trace\":{"
        << "\"available\":" << (e.influence_trace.available ? "true" : "false");
    if (e.influence_trace.available) {
        const auto& trace = e.influence_trace;
        out << ",\"tile_id\":" << trace.tile_id
            << ",\"cascade\":" << trace.cascade
            << ",\"output_id\":" << trace.output_id
            << ",\"probe_x\":" << trace.probe_x
            << ",\"probe_y\":" << trace.probe_y
            << ",\"probe_z\":" << trace.probe_z
            << ",\"base_ray_count\":" << trace.base_ray_count
            << ",\"extra_ray_count\":" << trace.extra_ray_count
            << ",\"base_radiance_sum16\":" << trace.base_radiance_sum16
            << ",\"extra_radiance_sum16\":" << trace.extra_radiance_sum16
            << ",\"base_zero_rays\":" << trace.base_zero_rays
            << ",\"extra_zero_rays\":" << trace.extra_zero_rays
            << ",\"base_output_mean16\":" << trace.base_output_mean16
            << ",\"target_output_mean16\":" << trace.target_output_mean16
            << ",\"shared_probe_outputs\":" << trace.shared_probe_outputs
            << ",\"before_storage_sum16\":" << trace.before_storage_sum16
            << ",\"after_storage_sum16\":" << trace.after_storage_sum16
            << ",\"before_storage_mean16\":" << trace.before_storage_mean16
            << ",\"after_storage_mean16\":" << trace.after_storage_mean16
            << ",\"observed_storage_sum16\":" << trace.observed_storage_sum16
            << ",\"observed_storage_outputs\":" << trace.observed_storage_outputs;
    }
    out << "},\"gpu_hash_probe\":{"
        << "\"executed\":" << (e.gpu_hash_probe.executed ? "true" : "false");
    if (e.gpu_hash_probe.executed) {
        const auto& audit = e.gpu_hash_probe;
        out << ",\"hash_slots\":" << audit.hash_slots
            << ",\"scratch_bytes\":" << audit.scratch_bytes
            << ",\"unique_keys\":" << audit.unique_keys
            << ",\"duplicate_outputs\":" << audit.duplicate_outputs
            << ",\"invalid_keys\":" << audit.invalid_keys
            << ",\"failed_inserts\":" << audit.failed_inserts
            << ",\"collision_steps\":" << audit.collision_steps
            << ",\"complete_hash_gpu_us\":" << audit.complete_hash_gpu_us
            << ",\"unique_by_cascade\":[";
        for (std::size_t i = 0; i < audit.unique_by_cascade.size(); ++i) {
            if (i != 0U) out << ',';
            out << audit.unique_by_cascade[i];
        }
        out << "],\"duplicate_by_cascade\":[";
        for (std::size_t i = 0; i < audit.duplicate_by_cascade.size(); ++i) {
            if (i != 0U) out << ',';
            out << audit.duplicate_by_cascade[i];
        }
        out << ']';
    }
    out << "},\"canonical\":{"
        << "\"executed\":" << (e.canonical.executed ? "true" : "false");
    if (e.canonical.executed) {
        const auto& a = e.canonical;
        out << ",\"copyback_executed\":"
            << (a.copyback_executed ? "true" : "false")
            << ",\"hash_slots\":" << a.hash_slots
            << ",\"original_work_items\":" << a.original_work_items
            << ",\"original_outputs\":" << a.original_outputs
            << ",\"canonical_work_items\":" << a.canonical_work_items
            << ",\"canonical_outputs\":" << a.canonical_outputs
            << ",\"duplicates\":" << a.duplicates
            << ",\"invalid_keys\":" << a.invalid_keys
            << ",\"failed_inserts\":" << a.failed_inserts
            << ",\"index_overflows\":" << a.index_overflows
            << ",\"collision_steps\":" << a.collision_steps
            << ",\"scratch_bytes\":" << a.scratch_bytes
            << ",\"total_canonical_gpu_us\":" << a.total_canonical_gpu_us
            << ",\"owner_weight_storage_gpu_us\":" << a.owner_weight_storage_gpu_us
            << ",\"owner_weight_errors\":" << a.owner_weight_errors
            << ",\"weighted_owner_total\":" << a.weighted_owner_total
            << ",\"unique_by_cascade\":[";
        for (std::size_t i = 0; i < a.unique_by_cascade.size(); ++i) {
            if (i != 0U) out << ',';
            out << a.unique_by_cascade[i];
        }
        out << ']';
    }
    const auto& m1 = e.canonical_m1;
    out << "},\"canonical_m1\":{\"executed\":"
        << (m1.executed ? "true" : "false");
    if (m1.executed) {
        out << ",\"selected_token\":" << m1.selected_token
            << ",\"output_id\":" << m1.output_id
            << ",\"base_ray_count\":" << m1.base_ray_count
            << ",\"extra_ray_count\":" << m1.extra_ray_count
            << ",\"base_radiance_sum16\":" << m1.base_radiance_sum16
            << ",\"extra_radiance_sum16\":" << m1.extra_radiance_sum16
            << ",\"baseline_mean16\":" << m1.baseline_mean16
            << ",\"candidate_mean16\":" << m1.candidate_mean16
            << ",\"merged_sample_count\":" << m1.merged_sample_count
            << ",\"base_hit_count\":" << m1.base_hit_count
            << ",\"extra_hit_count\":" << m1.extra_hit_count
            << ",\"extra_miss_count\":" << m1.extra_miss_count
            << ",\"base_positive_radiance_rays\":" << m1.base_positive_radiance_rays
            << ",\"extra_positive_radiance_rays\":" << m1.extra_positive_radiance_rays
            << ",\"extra_hit_zero_radiance_rays\":" << m1.extra_hit_zero_radiance_rays
            << ",\"extra_injection_gpu_us\":" << m1.extra_injection_gpu_us;
    }
    out << "}}";
}

void write_hit(
    std::ostream& out,
    const lane_n::I001N004HitDiagnostics& d) {
    out << "{\"strict_mismatches\":" << d.strict_mismatches << ','
        << "\"surface_tie_equivalent_mismatches\":"
        << d.surface_tie_equivalent_mismatches << ','
        << "\"substantive_mismatches\":" << d.substantive_mismatches
        << '}';
}

void write_p1l_b0_profile(
    std::ostream& out, const lane_n::N006P1lB0Profile& profile) {
    static constexpr std::array<std::string_view, 4> kPrimary{
        "node_pops", "triangle_tests", "hit", "stack_overflow"};
    static constexpr std::array<std::string_view, 8> kShadow{
        "shadow_queries", "node_pops", "triangle_tests", "blockers",
        "valid_pixels", "positive_cosine", "stack_overflow", "storage_lookups"};
    static constexpr std::array<std::string_view, 8> kSecondary{
        "instance_tests", "dda_cells", "hash_probes", "quant_node_pops",
        "child_aabb_tests", "triangle_tests", "leaf_visits", "overflow"};
    const auto write_group = [&](auto labels, const auto& values) {
        out << '{';
        for (std::size_t i = 0; i < values.size(); ++i) {
            if (i) out << ',';
            const auto& v = values[i];
            out << '"' << labels[i] << "\":{\"sum\":" << v.total
                << ",\"mean\":" << v.mean
                << ",\"p50\":" << v.p50
                << ",\"p90\":" << v.p90
                << ",\"p99\":" << v.p99
                << ",\"max\":" << v.maximum
                << ",\"nonzero\":" << v.nonzero << '}';
        }
        out << '}';
    };
    out << "{\"diagnostic_only\":true,\"uninstrumented_gpu_timing\":true"
        << ",\"output_byte_identical\":true,\"pixels\":" << profile.pixels
        << ",\"secondary_rays\":" << profile.secondary_rays
        << ",\"primary\":";
    write_group(kPrimary, profile.primary);
    out << ",\"shadow\":";
    write_group(kShadow, profile.shadow);
    out << ",\"secondary\":";
    write_group(kSecondary, profile.secondary);
    out << '}';
}


void write_p1l_b1b_profile(
    std::ostream& out, const lane_n::N006P1lB1bProfile& profile) {
    static constexpr std::array<std::string_view, 4> names{
        "node_pops", "triangle_tests", "hit", "stack_overflow"};
    const auto group = [&](const auto& metrics) {
        out << '{';
        for (std::size_t i = 0; i < metrics.size(); ++i) {
            if (i) out << ',';
            const auto& v = metrics[i];
            out << '"' << names[i] << "\":{\"sum\":" << v.total
                << ",\"mean\":" << v.mean
                << ",\"p50\":" << v.p50
                << ",\"p90\":" << v.p90
                << ",\"p99\":" << v.p99
                << ",\"max\":" << v.maximum
                << ",\"nonzero\":" << v.nonzero << '}';
        }
        out << '}';
    };
    const auto delta = [&](const lane_n::N006P1lB1bDifference& v) {
        out << "{\"signed_total\":" << v.signed_total
            << ",\"mean\":" << v.mean
            << ",\"p50\":" << v.p50
            << ",\"p90\":" << v.p90
            << ",\"p99\":" << v.p99
            << ",\"min\":" << v.minimum
            << ",\"max\":" << v.maximum
            << ",\"fewer\":" << v.fewer
            << ",\"equal\":" << v.equal
            << ",\"more\":" << v.more << '}';
    };
    out << "{\"diagnostic_only\":true,\"uninstrumented_gpu_timing\":true,"
           "\"original_hit_byte_exact\":true,\"near_first_hit_byte_exact\":true,"
           "\"pixels\":" << profile.pixels << ",\"original\":";
    group(profile.original);
    out << ",\"near_first\":";
    group(profile.near_first);
    out << ",\"delta\":{\"node_pops\":";
    delta(profile.delta[0]);
    out << ",\"triangle_tests\":";
    delta(profile.delta[1]);
    out << "}}";
}


void write_p1m0_coverage(
    std::ostream& out,
    const lane_n::N006P1m0Coverage& data) {
    out << "{\"diagnostic_only\":true,\"hash_capacity\":" << data.hash_capacity
        << ",\"pretrace_executed\":" << (data.pretrace_executed ? "true" : "false")
        << ",\"pretrace_slot_byte_equal\":" << (data.pretrace_slot_byte_equal ? "true" : "false")
        << ",\"pretrace_stats_byte_equal\":" << (data.pretrace_stats_byte_equal ? "true" : "false")
        << ",\"pretrace_clear_and_count_gpu_us\":" << data.pretrace_clear_and_count_gpu_us
        << ",\"pretrace_scratch_bytes\":" << data.pretrace_scratch_bytes
        << ",\"valid_primary_pixels\":" << data.valid_primary_pixels
        << ",\"lookup_attempts\":" << data.lookup_attempts
        << ",\"matched_lookups\":" << data.matched_lookups
        << ",\"absent_keys\":" << data.absent_keys
        << ",\"invalid_keys\":" << data.invalid_keys
        << ",\"probe_exhaustions\":" << data.probe_exhaustions
        << ",\"uint32_overflows\":" << data.uint32_overflows
        << ",\"invalid_launch\":" << data.invalid_launch
        << ",\"canonical_keys\":" << data.canonical_keys
        << ",\"keys_with_consumers\":" << data.keys_with_consumers
        << ",\"max_consumer_pixels\":" << data.max_consumer_pixels
        << ",\"consumer_lookups_by_cascade\":[";
    for (std::size_t i = 0; i < 4U; ++i) {
        if (i) out << ',';
        out << data.consumer_lookups_by_cascade[i];
    }
    out << "],\"keys_with_consumers_by_cascade\":[";
    for (std::size_t i = 0; i < 4U; ++i) {
        if (i) out << ',';
        out << data.keys_with_consumers_by_cascade[i];
    }
    out << "],\"key_rows\":[";
    for (std::size_t i = 0; i < data.key_rows.size(); ++i) {
        const auto& row = data.key_rows[i];
        if (i) out << ',';
        out << "{\"token\":" << row.token
            << ",\"consumer_pixels\":" << row.consumer_pixels
            << ",\"producer_owner_outputs\":" << row.producer_owner_outputs
            << '}';
    }
    out << "]}";
}

struct FrameEvidence {
    lane_n::N006FrameResult result;
    lane_n::I001N004HitDiagnostics hits;
    lane_n::I001RendererReadback readback;
    std::string image_path;
    float motion_fraction{};
    std::uint32_t owner_budget{};
    bool internal_correctness{};
    bool hit_diagnostics_executed{true};
    std::optional<lane_n::N006P1lB0Profile> p1l_b0_profile;
    std::optional<lane_n::N006P1lB1bProfile> p1l_b1b_profile;
    int p1l_b1_arm{-1};
    bool p1l_b1_primary_exact{};
    std::optional<lane_n::N006P1m0Coverage> p1m0_coverage;
};

[[nodiscard]] bool frame_core_correct(
    const lane_n::N006FrameResult& result) noexcept {
    return result.extra.base_prefix_correct &&
        result.extra.extra_work_correct &&
        result.frame.stats.overflow == 0U &&
        result.frame.stats.storage_failures == 0U;
}

[[nodiscard]] bool frame_correct(
    const lane_n::N006FrameResult& result,
    const lane_n::I001N004HitDiagnostics& hits) noexcept {
    return frame_core_correct(result) && hits.substantive_mismatches == 0U;
}

} // namespace

int main(int argc, char** argv) {
    fs::path scene;
    fs::path artifact_dir;
    std::string scenario_name = "static";
    std::string mode_text = "current";
    std::string variant_name = "lane-e-final-hwrt";
    std::string motion_fraction_text;
    std::string owner_budget_text;
    std::uint32_t source_warmup_frames = 32U;
    std::uint32_t target_frames = 1U;
    float depth_threshold = 0.01F;
    std::uint32_t extra_rays_per_probe = 4U;
    std::uint32_t selected_tile_id = 0xffffffffU;
    std::uint32_t selected_cascade = 0xffffffffU;
    bool topology = false;
    bool skip_reference = false;
    bool capture_visible_tiles = false;
    bool capture_probe_multiplicity = false;
    bool capture_probe_equivalence = false;
    bool canonical_probe_pilot = false;
    bool canonical_matrix_case = false;
    bool canonical_lean_hash = false;
    bool canonical_zero_copy = false;
    bool p1l_stage_probe = false;
    bool p1l_stage_fast = false;
    bool p1l_b0_counts = false;
    bool p1l_b1b_counts = false;
    bool p1l_b1c_axis_proxy = false;
    bool p1m0_coverage = false;
    bool p1m0_pretrace_coverage = false;
    std::uint32_t p1m1_canonical_token = 0U;
    bool p1m2_tetra_octant_directions = false;
    bool p1m2b_independent_state = false;
    bool p1m3_fractional_storage = false;
    bool p1m3b_holdout_quality = false;
    std::string p1l_b1_pattern;
    bool capture_gpu_unique_hash = false;
    // P1h: frozen canonical/current balanced schedule after target-state warmup.
    std::string canonical_frame_pattern;
    // P1k frozen balanced order: 0=current, 1=lean copyback, 2=direct compact.
    std::string three_arm_pattern;
    std::uint32_t target_state_warmup_frames = 0U;
    // P1e diagnostic only: exact per-target-frame hash flag schedule.
    std::string hash_frame_pattern;

    for (int index = 1; index < argc; ++index) {
        const std::string_view arg = argv[index];
        if (arg == "--scene" && index + 1 < argc) scene = argv[++index];
        else if (arg == "--artifact-dir" && index + 1 < argc) artifact_dir = argv[++index];
        else if (arg == "--scenario" && index + 1 < argc) scenario_name = argv[++index];
        else if (arg == "--mode" && index + 1 < argc) mode_text = argv[++index];
        else if (arg == "--source-warmup-frames" && index + 1 < argc) {
            source_warmup_frames = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--target-frames" && index + 1 < argc) {
            target_frames = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--motion-fractions" && index + 1 < argc) {
            motion_fraction_text = argv[++index];
        } else if (arg == "--owner-budgets" && index + 1 < argc) {
            owner_budget_text = argv[++index];
        } else if (arg == "--depth-threshold" && index + 1 < argc) {
            depth_threshold = std::stof(argv[++index]);
        } else if (arg == "--extra-rays-per-probe" && index + 1 < argc) {
            extra_rays_per_probe = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--selected-tile-id" && index + 1 < argc) {
            selected_tile_id = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--selected-cascade" && index + 1 < argc) {
            selected_cascade = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--topology") topology = true;
        else if (arg == "--skip-reference") skip_reference = true;
        else if (arg == "--capture-visible-tiles") capture_visible_tiles = true;
        else if (arg == "--capture-probe-multiplicity") capture_probe_multiplicity = true;
        else if (arg == "--capture-probe-equivalence") capture_probe_equivalence = true;
        else if (arg == "--canonical-probe-pilot") canonical_probe_pilot = true;
        else if (arg == "--canonical-matrix-case") canonical_matrix_case = true;
        else if (arg == "--canonical-lean-hash") canonical_lean_hash = true;
        else if (arg == "--canonical-zero-copy") canonical_zero_copy = true;
        else if (arg == "--p1l-stage-probe") p1l_stage_probe = true;
        else if (arg == "--p1l-stage-fast") p1l_stage_fast = true;
        else if (arg == "--p1l-b0-counts") p1l_b0_counts = true;
        else if (arg == "--p1l-b1b-counts") p1l_b1b_counts = true;
        else if (arg == "--p1l-b1c-axis-proxy") p1l_b1c_axis_proxy = true;
        else if (arg == "--p1m0-consumer-coverage") p1m0_coverage = true;
        else if (arg == "--p1m0-pretrace-coverage") p1m0_pretrace_coverage = true;
        else if (arg == "--p1m1-canonical-token" && index + 1 < argc) {
            p1m1_canonical_token = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        }
        else if (arg == "--p1m2-tetra-octant-directions") {
            p1m2_tetra_octant_directions = true;
        }
        else if (arg == "--p1m2b-independent-state") {
            p1m2b_independent_state = true;
        }
        else if (arg == "--p1m3-fractional-storage") {
            p1m3_fractional_storage = true;
        }
        else if (arg == "--p1m3b-holdout-quality") {
            p1m3b_holdout_quality = true;
        }
        else if (arg == "--p1l-b1-pattern" && index + 1 < argc)
            p1l_b1_pattern = argv[++index];
        else if (arg == "--three-arm-pattern" && index + 1 < argc)
            three_arm_pattern = argv[++index];
        else if (arg == "--variant" && index + 1 < argc) variant_name = argv[++index];
        else if (arg == "--canonical-frame-pattern" && index + 1 < argc) {
            canonical_frame_pattern = argv[++index];
        } else if (arg == "--target-state-warmup-frames" && index + 1 < argc) {
            target_state_warmup_frames =
                static_cast<std::uint32_t>(std::stoul(argv[++index]));
        }
        else if (arg == "--capture-gpu-unique-hash") capture_gpu_unique_hash = true;
        else if (arg == "--hash-frame-pattern" && index + 1 < argc) {
            hash_frame_pattern = argv[++index];
        }
        else {
            std::cerr
                << "usage: phos-n006-candidate --artifact-dir PATH --scene PATH "
                   "--scenario NAME --mode current|targeted-extra-rays "
                   "--owner-budgets CSV [--motion-fractions CSV] [--topology] "
                   "[--source-warmup-frames N] [--target-frames N] "
                   "[--depth-threshold F] [--extra-rays-per-probe N] "
                   "[--selected-tile-id N --selected-cascade N] [--skip-reference]\n";
            return 2;
        }
    }

    try {
        if (artifact_dir.empty() || scene.empty() || source_warmup_frames == 0U ||
            target_frames == 0U) {
            throw std::runtime_error("invalid N006 candidate arguments");
        }
        if (p1m2_tetra_octant_directions && p1m1_canonical_token == 0U) {
            throw std::runtime_error(
                "P1m2a directions require a frozen P1m1 canonical token");
        }
        // P1m3b moving-rigid is a distinct prospective Q8 quality holdout.
        // References can be rendered in a baseline control only.
        if (p1m3b_holdout_quality &&
            (!p1m3_fractional_storage || !p1m2b_independent_state ||
             scenario_name != "moving-rigid" ||
             p1m2_tetra_octant_directions ||
             (!skip_reference && p1m1_canonical_token != 0U))) {
            throw std::runtime_error(
                "P1m3b requires moving-rigid SW Q8; "
                "CPU references are control-only");
        }
        // P1m3a is an independently frozen alternative STORAGE REPRESENTATION.
        // Historical M1a/M2a/M2b storage semantics must remain byte-identical.
        if (p1m3_fractional_storage) {
            const bool valid_calibration_key = p1m1_canonical_token == 0U ||
                (scenario_name == "camera-motion" &&
                 (p1m1_canonical_token == 1084233745U ||
                  p1m1_canonical_token == 3223324678U ||
                  p1m1_canonical_token == 2152730633U)) ||
                (scenario_name == "light-motion" &&
                 p1m1_canonical_token == 3223324678U);
            if (!p1m2b_independent_state ||
                (!p1m3b_holdout_quality && !valid_calibration_key) ||
                p1m2_tetra_octant_directions) {
                throw std::runtime_error(
                    "P1m3a Q8 requires independent-state camera/light "
                    "frozen original-direction calibration only");
            }
        }
        // P1m2b is a NEW, explicit bounded study; it cannot weaken the
        // original M1a/M2a frozen static/C3 token whitelist.
        if (p1m2b_independent_state &&
            (!p1m0_coverage || p1m0_pretrace_coverage ||
             (scenario_name != "camera-motion" && scenario_name != "light-motion" &&
               !(p1m3b_holdout_quality && scenario_name == "moving-rigid")) ||
             variant_name != "lane-e-final-software" ||
             !canonical_lean_hash || canonical_zero_copy || (!skip_reference && !(p1m3b_holdout_quality && p1m1_canonical_token == 0U)) ||
             topology || mode_text != "current" ||
             source_warmup_frames != 32U ||
             target_state_warmup_frames != 8U || target_frames != 1U ||
             capture_visible_tiles || capture_probe_multiplicity ||
             capture_probe_equivalence || capture_gpu_unique_hash ||
             !hash_frame_pattern.empty() || !three_arm_pattern.empty() ||
             !canonical_frame_pattern.empty() || canonical_probe_pilot)) {
            throw std::runtime_error(
                "P1m2b requires separate camera/light SW + M0, 32+8 "
                "warmups, one target and no reference/other capture");
        }
        // M1a first prospective pilot: only three unchanged calibration
        // tokens from static cascade-3; no post-hoc scene/token tuning.
        if (p1m1_canonical_token != 0U) {
            const bool accepted_token =
                p1m1_canonical_token == 3221225474U ||
                p1m1_canonical_token == 3223322625U ||
                p1m1_canonical_token == 3223324678U;
            if ((!p1m2b_independent_state && !accepted_token) ||
                (!p1m2b_independent_state && scenario_name != "static") ||
                !p1m0_coverage || p1m0_pretrace_coverage ||
                variant_name != "lane-e-final-software" ||
                !canonical_lean_hash || canonical_zero_copy ||
                (!skip_reference && !(p1m3b_holdout_quality && p1m1_canonical_token == 0U)) || topology ||
                mode_text != "current" || source_warmup_frames != 32U ||
                target_state_warmup_frames != 8U || target_frames != 1U ||
                capture_visible_tiles || capture_probe_multiplicity ||
                capture_probe_equivalence || capture_gpu_unique_hash ||
                !hash_frame_pattern.empty() || !three_arm_pattern.empty() ||
                !canonical_frame_pattern.empty() || canonical_probe_pilot) {
                throw std::runtime_error(
                    "P1m1a requires frozen static C3 zero/low/high token, "
                    "N006 SW lean-copyback, 32+8 warmups, one target, "
                    "postframe M0 parity and zero reference");
            }
        }
        if (p1m0_pretrace_coverage && !p1m0_coverage) {
            throw std::runtime_error(
                "P1m0b pretrace requires --p1m0-consumer-coverage for exact postframe parity");
        }
        const bool p1l_b1 = !p1l_b1_pattern.empty();
        if (p1l_b1c_axis_proxy && !p1l_b1)
            throw std::runtime_error("N006 P1l-B1c requires frozen --p1l-b1-pattern");
        const bool p1l_stage_any =
            p1l_stage_probe || p1l_stage_fast || p1l_b0_counts ||
            p1l_b1 || p1l_b1b_counts;
        // M0 retains the N004 sampled oracle on the one target frame, but
        // must not re-run the CPU hit oracle on all eight warmup frames.
        // Use the same sampled-fast correctness protocol as P1l-B0.
        const bool p1l_sampled_hit =
            p1l_stage_fast || p1l_b0_counts || p1l_b1 || p1l_b1b_counts ||
            p1m0_coverage;
        if (int(p1l_stage_probe) + int(p1l_stage_fast) +
            int(p1l_b0_counts) + int(p1l_b1) + int(p1l_b1b_counts) > 1) {
            throw std::runtime_error(
                "N006 P1l legacy-full and sampled-fast modes are mutually exclusive");
        }
        const auto mode = parse_mode(mode_text);
        auto fractions = motion_fraction_text.empty()
            ? std::vector<float>(target_frames, 1.0F)
            : parse_csv<float>(motion_fraction_text);
        auto budgets = owner_budget_text.empty()
            ? std::vector<std::uint32_t>(target_frames, 0U)
            : parse_csv<std::uint32_t>(owner_budget_text);
        if (fractions.size() != target_frames || budgets.size() != target_frames) {
            throw std::runtime_error("N006 schedule length must match target frames");
        }
        if (mode == lane_n::N006ExtraMode::Targeted &&
            (selected_tile_id >= 320U * 180U || selected_cascade >= 4U ||
             !std::all_of(budgets.begin(), budgets.end(),
                 [](auto value) { return value == 1U; }))) {
            throw std::runtime_error("N006 targeted mode requires tile 0..57599, cascade 0..3 and owner budget 1 per frame");
        }
        for (const auto fraction : fractions) {
            if (!(fraction >= 0.0F && fraction <= 1.0F)) {
                throw std::runtime_error("N006 motion fraction outside [0,1]");
            }
        }
        if (mode == lane_n::N006ExtraMode::Current &&
            std::any_of(budgets.begin(), budgets.end(), [](auto value) { return value != 0U; })) {
            throw std::runtime_error("N006 current mode must use zero owner budgets");
        }
        // P1j-A is a distinct run of the frozen correctness matrix. The
        // accepted P1i behavior and allocations remain the default.
        if (canonical_lean_hash &&
            !((canonical_matrix_case && canonical_probe_pilot) ||
              !three_arm_pattern.empty() || p1l_stage_any ||
              p1m0_coverage)) {
            throw std::runtime_error(
                "N006 P1j-A lean hash requires canonical matrix correctness pilot");
        }
        if (canonical_zero_copy &&
            (!canonical_lean_hash ||
             !((canonical_matrix_case && canonical_probe_pilot) ||
               !three_arm_pattern.empty()))) {
            throw std::runtime_error(
                "N006 P1j-B direct work requires lean-hash matrix canonical pilot");
        }
        if (canonical_matrix_case) {
            const bool accepted_variant =
                variant_name == "lane-e-final-hwrt" ||
                variant_name == "lane-e-final-software";
            const bool accepted_scenario =
                scenario_name == "static" ||
                scenario_name == "camera-motion" ||
                scenario_name == "light-motion" ||
                scenario_name == "moving-rigid" ||
                scenario_name == "deforming-control";
            if (!canonical_probe_pilot || !accepted_variant || !accepted_scenario ||
                topology || !skip_reference ||
                !hash_frame_pattern.empty() || !canonical_frame_pattern.empty() ||
                target_state_warmup_frames != 0U ||
                !three_arm_pattern.empty() ||
                capture_gpu_unique_hash || capture_probe_equivalence ||
                capture_probe_multiplicity || capture_visible_tiles ||
                mode != lane_n::N006ExtraMode::Current ||
                source_warmup_frames != 32U || target_frames != 2U ||
                !std::all_of(fractions.begin(), fractions.end(),
                    [](float value) { return value == 1.0F; })) {
                throw std::runtime_error(
                    "N006 P1i matrix supports only fixed two-frame current/canonical "
                    "LaneEFinal HWRT/software five-scenario protocol");
            }
        } else if (variant_name != "lane-e-final-hwrt" &&
                   three_arm_pattern.empty() && !p1l_stage_any &&
                   !p1m0_coverage) {
            throw std::runtime_error(
                "N006 variant override is reserved for P1i matrix study");
        }
        if (canonical_probe_pilot &&
            (mode != lane_n::N006ExtraMode::Current ||
             !skip_reference ||
             capture_gpu_unique_hash ||
             capture_probe_multiplicity ||
             capture_probe_equivalence ||
             !hash_frame_pattern.empty() ||
             !canonical_frame_pattern.empty() ||
             target_state_warmup_frames != 0U ||
             (scenario_name != "deforming-control" && !canonical_matrix_case) ||
             source_warmup_frames != 32U ||
             target_frames != 2U ||
             !std::all_of(fractions.begin(), fractions.end(),
                  [](float fraction) { return fraction == 1.0F; }))) {
            throw std::runtime_error(
                "N006 P1g requires 32 warmups, two fixed current/canonical "
                "target frames, deforming-control and skipped reference");
        }
        if (!canonical_frame_pattern.empty()) {
            if (canonical_frame_pattern != "011001100110" ||
                target_state_warmup_frames != 8U ||
                source_warmup_frames != 32U ||
                target_frames != 12U ||
                canonical_probe_pilot || capture_gpu_unique_hash ||
                capture_probe_multiplicity || capture_probe_equivalence ||
                capture_visible_tiles ||
                !hash_frame_pattern.empty() ||
                mode != lane_n::N006ExtraMode::Current ||
                scenario_name != "deforming-control" ||
                !skip_reference || topology ||
                !std::all_of(fractions.begin(), fractions.end(),
                    [](float value) { return value == 1.0F; })) {
                throw std::runtime_error(
                    "N006 P1h requires fixed 011001100110, 8 target-state "
                    "warmups, 32 source warmups, 12 motion=1 current targets, "
                    "no hash/extra/reference/topology");
            }
        } else if (target_state_warmup_frames != 0U &&
                   three_arm_pattern.empty() && !p1l_stage_any &&
                   !p1m0_coverage) {
            throw std::runtime_error(
                "N006 target-state warmup only valid with a frozen P1h/P1k pattern");
        }

        if (!three_arm_pattern.empty()) {
            // All 6 permutations of (current, lean copyback, lean direct)
            // in one process; each arm appears twice in every triplet position.
            if (three_arm_pattern != "012120201021102210" ||
                canonical_frame_pattern.size() != 0U ||
                canonical_matrix_case || canonical_probe_pilot ||
                !canonical_lean_hash || !canonical_zero_copy ||
                !skip_reference || topology ||
                mode != lane_n::N006ExtraMode::Current ||
                scenario_name != "deforming-control" ||
                (variant_name != "lane-e-final-hwrt" &&
                 variant_name != "lane-e-final-software") ||
                source_warmup_frames != 32U ||
                target_state_warmup_frames != 8U ||
                target_frames != 18U ||
                capture_gpu_unique_hash || capture_probe_equivalence ||
                capture_probe_multiplicity || capture_visible_tiles ||
                !hash_frame_pattern.empty() ||
                !std::all_of(fractions.begin(), fractions.end(),
                    [](float value) { return value == 1.0F; })) {
                throw std::runtime_error(
                    "N006 P1k requires frozen balanced 18-frame pattern, 32 source/8 "
                    "target warmups, 2 supported backends, lean+zero-copy and no reference");
            }
        }

        // P1l-A1 uses existing N006-only disjoint GPU timestamps, without
        // modifying historical shader stages or the three-arm P1k protocol.
        if (p1l_stage_probe || p1l_stage_fast) {
            const bool supported_variant =
                variant_name == "lane-e-final-hwrt" ||
                variant_name == "lane-e-final-software";
            const bool supported_scenario =
                scenario_name == "static" ||
                scenario_name == "camera-motion" ||
                scenario_name == "light-motion" ||
                scenario_name == "moving-rigid" ||
                scenario_name == "deforming-control";
            if (!supported_variant || !supported_scenario ||
                !canonical_lean_hash || canonical_zero_copy ||
                canonical_probe_pilot || canonical_matrix_case ||
                !canonical_frame_pattern.empty() || !three_arm_pattern.empty() ||
                topology || !skip_reference ||
                mode != lane_n::N006ExtraMode::Current ||
                source_warmup_frames != 32U ||
                target_state_warmup_frames != 8U || target_frames != 12U ||
                capture_gpu_unique_hash || capture_probe_equivalence ||
                capture_probe_multiplicity || capture_visible_tiles ||
                !hash_frame_pattern.empty() ||
                !std::all_of(fractions.begin(), fractions.end(),
                    [](float value) { return value == 1.0F; }) ||
                !std::all_of(budgets.begin(), budgets.end(),
                    [](std::uint32_t value) { return value == 0U; })) {
                throw std::runtime_error(
                    "N006 P1l-A1 requires fixed 5 scenarios x 2 backends, "
                    "lean-copyback canonical, 32 source/8 target warmups, "
                    "12 motion=1 frames and skipped reference");
            }
        }

        if (p1l_b0_counts || p1l_b1b_counts) {
            const bool supported_scenario =
                scenario_name == "static" || scenario_name == "camera-motion" ||
                scenario_name == "light-motion" || scenario_name == "moving-rigid" ||
                scenario_name == "deforming-control";
            if (variant_name != "lane-e-final-software" || !supported_scenario ||
                !canonical_lean_hash || canonical_zero_copy ||
                canonical_probe_pilot || canonical_matrix_case ||
                !canonical_frame_pattern.empty() || !three_arm_pattern.empty() ||
                topology || !skip_reference ||
                mode != lane_n::N006ExtraMode::Current ||
                source_warmup_frames != 32U ||
                target_state_warmup_frames != 8U || target_frames != 1U ||
                capture_gpu_unique_hash || capture_probe_equivalence ||
                capture_probe_multiplicity || capture_visible_tiles ||
                !hash_frame_pattern.empty() ||
                fractions[0] != 1.0F || budgets[0] != 0U) {
                throw std::runtime_error(
                    "N006 P1l-B0/B1b requires software, one canonical target, "
                    "32 source/8 target warmups, lean-copyback, no reference");
            }
        }
        if (p1m0_coverage) {
            const bool supported_scenario =
                scenario_name == "static" || scenario_name == "camera-motion" ||
                scenario_name == "light-motion" || scenario_name == "moving-rigid" ||
                scenario_name == "deforming-control";
            if (variant_name != "lane-e-final-software" || !supported_scenario ||
                !canonical_lean_hash || canonical_zero_copy || p1l_stage_any ||
                canonical_probe_pilot || canonical_matrix_case ||
                !canonical_frame_pattern.empty() || !three_arm_pattern.empty() ||
                topology || (!skip_reference && !(p1m3b_holdout_quality && p1m1_canonical_token == 0U)) || capture_gpu_unique_hash ||
                capture_probe_equivalence || capture_probe_multiplicity ||
                capture_visible_tiles || !hash_frame_pattern.empty() ||
                mode != lane_n::N006ExtraMode::Current ||
                source_warmup_frames != 32U ||
                target_state_warmup_frames != 8U || target_frames != 1U ||
                fractions[0] != 1.0F || budgets[0] != 0U) {
                throw std::runtime_error(
                    "P1m0 requires software, canonical lean hash, 32+8 warmups, "
                    "one current target, no reference/other probes");
            }
        }
        if (p1l_b1) {
            const bool supported_scenario =
                scenario_name == "static" || scenario_name == "camera-motion" ||
                scenario_name == "light-motion" || scenario_name == "moving-rigid" ||
                scenario_name == "deforming-control";
            if (variant_name != "lane-e-final-software" || !supported_scenario ||
                !canonical_lean_hash || canonical_zero_copy ||
                canonical_probe_pilot || canonical_matrix_case ||
                !canonical_frame_pattern.empty() || !three_arm_pattern.empty() ||
                topology || !skip_reference ||
                mode != lane_n::N006ExtraMode::Current ||
                source_warmup_frames != 32U ||
                target_state_warmup_frames != 8U ||
                capture_gpu_unique_hash || capture_probe_equivalence ||
                capture_probe_multiplicity || capture_visible_tiles ||
                !hash_frame_pattern.empty() ||
                !std::all_of(fractions.begin(), fractions.end(),
                    [](float v) { return v == 1.0F; }) ||
                !std::all_of(budgets.begin(), budgets.end(),
                    [](std::uint32_t v) { return v == 0U; }) ||
                p1l_b1_pattern.size() != target_frames ||
                !(p1l_b1_pattern == "01" ||
                  p1l_b1_pattern == "011001100110011001100110")) {
                throw std::runtime_error(
                    "N006 P1l-B1 requires software canonical copyback, "
                    "32+8 warmups and frozen 01 preflight or 24-frame ABBA pattern");
            }
        }
        std::vector<std::uint32_t> hash_schedule(
            target_frames, capture_gpu_unique_hash ? 1U : 0U);
        if (!hash_frame_pattern.empty()) {
            if (capture_gpu_unique_hash ||
                mode != lane_n::N006ExtraMode::Current ||
                !skip_reference ||
                target_frames != 12U ||
                source_warmup_frames != 32U ||
                scenario_name != "deforming-control" ||
                !std::all_of(fractions.begin(), fractions.end(),
                    [](float value) { return value == 1.0F; })) {
                throw std::runtime_error(
                    "N006 P1e hash-frame schedule requires 32 warmups, 12 fixed "
                    "deforming-control target frames, current/no-reference only");
            }
            if (hash_frame_pattern != "011001100110") {
                throw std::runtime_error("N006 P1e hash-frame schedule differs from frozen plan");
            }
            for (std::uint32_t index = 0U; index < target_frames; ++index) {
                hash_schedule[index] = (hash_frame_pattern[index] == '1') ? 1U : 0U;
            }
        }

        lane_n::I001Options options{};
        options.scene = scene;
        options.variant = lane_n::i001_parse_variant(variant_name);
        options.scenario = lane_n::i001_parse_scenario(scenario_name);
        options.validation = true;
        // M0 diagnostic stage markers are flushed directly to the runner's
        // stderr log, including when Vulkan/CPU work does not return.
        const auto trace_p1m0 = [&](const char* stage) {
            if (p1m0_coverage) {
                std::cerr << "[P1m0-stage] " << stage << std::endl;
            }
        };
        trace_p1m0("runtime construction begin");
        lane_n::N006Runtime runtime(
            options, canonical_lean_hash, canonical_zero_copy, p1l_b1,
            p1l_b1c_axis_proxy, p1m0_pretrace_coverage,
            p1m1_canonical_token != 0U, p1m2_tetra_octant_directions,
            p1m3_fractional_storage);
        trace_p1m0("runtime construction complete");

        const lane_n::N006ExtraRequest current_request{};
        trace_p1m0("initial source frame begin");
        auto source = runtime.run_frame(false, current_request);
        trace_p1m0("initial source frame complete");
        const auto source_hits = p1l_sampled_hit
            ? lane_n::I001N004HitDiagnostics{}
            : runtime.n004_hit_diagnostics();
        const bool source_correct = p1l_sampled_hit
            ? frame_core_correct(source)
            : frame_correct(source, source_hits);
        bool source_warmups_correct = source_correct;
        for (std::uint32_t index = 1; index < source_warmup_frames; ++index) {
            if (p1m0_coverage && (index == 1U || index == 16U ||
                                  index + 1U == source_warmup_frames))
                std::cerr << "[P1m0-stage] source warmup "
                          << (index + 1U) << "/" << source_warmup_frames
                          << " begin" << std::endl;
            const auto warm_source = runtime.run_frame(false, current_request);
            const bool warm_correct =
                p1l_sampled_hit ? frame_core_correct(warm_source)
                : p1l_stage_probe
                    ? frame_correct(warm_source, runtime.n004_hit_diagnostics())
                    : true;
            if (!warm_correct) {
                source_warmups_correct = false;
                throw std::runtime_error("N006 P1l source warmup invalid");
            }
        }

        // P1h: force traversal maintenance / dynamic transition before the
        // FIRST timed target. Warmup samples are not pair statistics.
        // P1m0 spans five frozen scenes, not P1h's one hardcoded scene.
        // Freeze per-target-state stable counts before measuring each case.
        const bool scenario_counted_target = p1l_stage_any || p1m0_coverage;
        trace_p1m0("source warmup complete");
        bool target_warmup_correct = true;
        double last_target_warmup_maintenance_us = 0.0;
        std::uint32_t last_target_warmup_owners = 0U;
        std::uint32_t last_target_warmup_work = 0U;
        std::uint32_t first_target_warmup_owners = 0U;
        std::uint32_t first_target_warmup_outputs = 0U;
        std::uint32_t first_target_warmup_work = 0U;
        std::vector<double> target_warmup_maintenance_samples;
        if (target_state_warmup_frames != 0U) {
            runtime.set_motion_fraction(1.0F);
            for (std::uint32_t warm = 0; warm < target_state_warmup_frames; ++warm) {
                if (p1m0_coverage)
                    std::cerr << "[P1m0-stage] target warmup "
                              << (warm + 1U) << "/" << target_state_warmup_frames
                              << " begin" << std::endl;
                const auto warm_frame = runtime.run_frame(true, current_request);
                const auto warm_hits = p1l_sampled_hit
                    ? lane_n::I001N004HitDiagnostics{}
                    : runtime.n004_hit_diagnostics();
                const auto& stats = warm_frame.frame.stats;
                const double maintenance =
                    warm_frame.frame.timings.traversal_maintenance_gpu_us;
                target_warmup_maintenance_samples.push_back(maintenance);
                if (warm == 0U) {
                    first_target_warmup_owners = stats.visible_owners;
                    first_target_warmup_outputs = stats.outputs;
                    first_target_warmup_work = stats.work_items;
                }
                const bool expected_counts = scenario_counted_target
                    ? (first_target_warmup_owners != 0U &&
                       stats.visible_owners == first_target_warmup_owners &&
                       stats.outputs == first_target_warmup_owners * 4U &&
                       stats.outputs == first_target_warmup_outputs &&
                       stats.work_items == stats.outputs * 8U &&
                       stats.work_items == first_target_warmup_work)
                    : (stats.visible_owners == 4172U &&
                       stats.work_items == 133504U &&
                       stats.outputs == 16688U);
                if (!(p1l_sampled_hit
                      ? frame_core_correct(warm_frame)
                      : frame_correct(warm_frame, warm_hits)) ||
                    !expected_counts || (warm != 0U && maintenance != 0.0)) {
                    target_warmup_correct = false;
                    throw std::runtime_error(
                        "N006 P1h/P1k/P1l target warmup "
                        "frame/count/maintenance invalid");
                }
                last_target_warmup_maintenance_us = maintenance;
                last_target_warmup_owners = stats.visible_owners;
                last_target_warmup_work = stats.work_items;
                if (p1m0_coverage)
                    std::cerr << "[P1m0-stage] target warmup "
                              << (warm + 1U) << " complete" << std::endl;
            }
            if (last_target_warmup_maintenance_us != 0.0 ||
                (scenario_counted_target
                    ? (last_target_warmup_owners != first_target_warmup_owners ||
                       last_target_warmup_work != first_target_warmup_work)
                    : (last_target_warmup_owners != 4172U ||
                       last_target_warmup_work != 133504U))) {
                throw std::runtime_error(
                    "N006 P1h/P1k/P1l target-state warmup failed to stabilize");
            }
        }
        std::ostringstream warmup_maintenance_json;
        warmup_maintenance_json << '[' << std::setprecision(17);
        for (std::size_t idx = 0; idx < target_warmup_maintenance_samples.size(); ++idx) {
            if (idx != 0U) warmup_maintenance_json << ',';
            warmup_maintenance_json << target_warmup_maintenance_samples[idx];
        }
        warmup_maintenance_json << ']';

        trace_p1m0("all warmups complete");
        fs::create_directories(artifact_dir / "frames");
        std::vector<FrameEvidence> frames;
        frames.reserve(target_frames);
        std::vector<std::uint8_t> b1_baseline_hits;
        for (std::uint32_t index = 0; index < target_frames; ++index) {
            runtime.set_motion_fraction(fractions[index]);
            const lane_n::N006ExtraRequest request{
                mode,
                budgets[index],
                depth_threshold,
                extra_rays_per_probe,
                selected_tile_id,
                selected_cascade,
                hash_schedule[index] != 0U,
                (canonical_probe_pilot && index == 1U) ||
                    (!canonical_frame_pattern.empty() &&
                     canonical_frame_pattern[index] == '1') ||
                    (!three_arm_pattern.empty() &&
                     three_arm_pattern[index] != '0') ||
                    p1l_stage_any || p1m0_coverage,
                (canonical_probe_pilot && canonical_zero_copy && index == 1U) ||
                    (!three_arm_pattern.empty() &&
                     three_arm_pattern[index] == '2'),
                p1l_b1 && p1l_b1_pattern[index] == '1',
                p1m0_pretrace_coverage && index == 0U,
                p1m1_canonical_token != 0U && index == 0U,
                p1m1_canonical_token,
                p1m2_tetra_octant_directions && index == 0U,
            };
            trace_p1m0("canonical target render begin");
            lane_n::N006FrameResult result =
                (index == 0U && topology)
                ? runtime.run_topology_churn_frame(request)
                : runtime.run_frame(true, request);
            trace_p1m0("canonical target render complete");
            const bool hit_executed =
                p1l_b1 ? index == 1U : (!p1l_sampled_hit || index == 0U);
            trace_p1m0("target N004 sampled hit oracle begin");
            const auto hits = hit_executed
                ? runtime.n004_hit_diagnostics()
                : lane_n::I001N004HitDiagnostics{};
            trace_p1m0("target N004 sampled hit oracle complete");
            auto readback = runtime.renderer_readback();
            trace_p1m0("target HDR readback complete");
            const auto image_path = indexed_path("candidate", index);
            write_pfm(
                artifact_dir / image_path,
                readback.width,
                readback.height,
                rgb_from_rgba(readback));
            trace_p1m0("target PFM written");
            bool b1_primary_exact = false;
            if (p1l_b1) {
                const auto hit_bytes = runtime.p1l_b1_primary_hit_bytes();
                if (index == 0U) {
                    if (p1l_b1_pattern[index] != '0') {
                        throw std::runtime_error("N006 P1l-B1 must start with baseline");
                    }
                    b1_baseline_hits = hit_bytes;
                }
                b1_primary_exact = hit_bytes == b1_baseline_hits;
                if (!b1_primary_exact) {
                    throw std::runtime_error(
                        "N006 P1l-B1 primary GPU hit bytes diverged between arms");
                }
            }
            std::optional<lane_n::N006P1lB0Profile> b0_profile;
            std::optional<lane_n::N006P1lB1bProfile> b1b_profile;
            if (p1l_b1b_counts) {
                // Frozen B1b: both diagnostic shaders use same accepted
                // input, AFTER frame timestamps; byte parity is mandatory.
                b1b_profile = runtime.p1l_b1b_work_counts();
            }
            if (p1l_b0_counts) {
                // This separate command runs AFTER the normal renderer and
                // image readback; no diagnostic work enters accepted GPU timers.
                b0_profile = runtime.p1l_b0_work_counts();
            }
            std::optional<lane_n::N006P1m0Coverage> consumer_profile;
            if (p1m0_coverage) {
                // Postframe diagnostic, after accepted render and CPU oracle.
                trace_p1m0("consumer GPU diagnostic begin");
                consumer_profile = runtime.p1m0_consumer_coverage();
                trace_p1m0("consumer GPU diagnostic complete");
            }
            frames.push_back({
                result,
                hits,
                std::move(readback),
                image_path,
                fractions[index],
                budgets[index],
                (hit_executed ? frame_correct(result, hits)
                              : frame_core_correct(result)),
                hit_executed,
                std::move(b0_profile),
                std::move(b1b_profile),
                p1l_b1 ? int(p1l_b1_pattern[index] - '0') : -1,
                b1_primary_exact,
                std::move(consumer_profile),
            });
        }

        if (capture_gpu_unique_hash &&
            (mode != lane_n::N006ExtraMode::Current ||
             target_frames != 1U || !skip_reference)) {
            throw std::runtime_error(
                "N006 GPU hash capture requires current, one target frame, no reference");
        }
        if (capture_probe_equivalence) {
            if (mode != lane_n::N006ExtraMode::Current ||
                target_frames != 1U || !skip_reference ||
                capture_gpu_unique_hash || !hash_frame_pattern.empty()) {
                throw std::runtime_error(
                    "N006 probe equivalence requires current, one target, no hash/reference");
            }
            const auto audit = runtime.probe_output_equivalence_audit();
            std::ofstream out(artifact_dir / "n006-probe-equivalence.json");
            if (!out) {
                throw std::runtime_error("N006 P1f equivalence output creation failed");
            }
            out << "{\"schema_version\":1,\"protocol_version\":\"n006-p1f-owner-equivalence-v1\","
                << "\"base_work_items\":" << audit.base_work_items
                << ",\"owner_outputs\":" << audit.owner_outputs
                << ",\"visible_owners\":" << audit.visible_owners
                << ",\"rays_per_probe\":" << audit.rays_per_probe
                << ",\"cascade_count\":" << audit.cascade_count
                << ",\"all_gpu_storage_slots_reconstructed\":"
                << (audit.all_gpu_storage_slots_reconstructed ? "true" : "false")
                << ",\"cascades\":[";
            for (std::size_t j = 0; j < audit.cascades.size(); ++j) {
                const auto& row = audit.cascades[j];
                if (j != 0U) out << ',';
                out << "{\"cascade\":" << row.cascade
                    << ",\"unique_probe_keys\":" << row.unique_probe_keys
                    << ",\"owner_outputs\":" << row.owner_outputs
                    << ",\"shared_keys\":" << row.shared_keys
                    << ",\"divergent_merged_keys\":" << row.divergent_merged_keys
                    << ",\"divergent_owner_outputs\":" << row.divergent_owner_outputs
                    << ",\"divergent_rounded_mean_keys\":"
                    << row.divergent_rounded_mean_keys
                    << ",\"zero_sample_outputs\":" << row.zero_sample_outputs
                    << ",\"missing_or_bad_gpu_storage_keys\":"
                    << row.missing_or_bad_gpu_storage_keys << '}';
            }
            out << "]}\n";
            if (!out) {
                throw std::runtime_error("N006 P1f equivalence output write failed");
            }
        }

        if (capture_probe_multiplicity) {
            if (mode != lane_n::N006ExtraMode::Current ||
                target_frames != 1U || !skip_reference) {
                throw std::runtime_error(
                    "N006 multiplicity capture requires current, one frame, no reference");
            }
            const auto audit = runtime.probe_multiplicity_audit();
            std::ofstream output(artifact_dir / "n006-probe-multiplicity.json");
            if (!output) {
                throw std::runtime_error("N006 multiplicity output creation failed");
            }
            output << "{\"schema_version\":1,\"protocol_version\":"
                      "\"n006-probe-multiplicity-v1\","
                   << "\"base_work_items\":" << audit.base_work_items << ','
                   << "\"visible_owners\":" << audit.visible_owners << ','
                   << "\"rays_per_probe\":" << audit.rays_per_probe << ','
                   << "\"cascade_count\":" << audit.cascade_count << ','
                   << "\"cascades\":[";
            for (std::size_t index = 0; index < audit.cascades.size(); ++index) {
                const auto& row = audit.cascades[index];
                if (index != 0U) output << ',';
                output << "{\"cascade\":" << row.cascade
                       << ",\"owner_outputs\":" << row.owner_outputs
                       << ",\"unique_probe_keys\":" << row.unique_probe_keys
                       << ",\"max_owner_outputs_per_key\":"
                       << row.max_owner_outputs_per_key
                       << ",\"shared_keys\":" << row.shared_keys
                       << ",\"duplicated_ray_inputs\":" << row.duplicated_ray_inputs
                       << ",\"same_probe_ray_inputs_identical\":"
                       << (row.same_probe_ray_inputs_identical ? "true" : "false")
                       << '}';
            }
            output << "]}\n";
            if (!output) {
                throw std::runtime_error("N006 multiplicity capture write failed");
            }
        }

        if (capture_visible_tiles) {
            const auto tiles = runtime.visible_tile_ids();
            std::ofstream visible_file(artifact_dir / "n006-visible-tiles.json");
            if (!visible_file) throw std::runtime_error("N006 visible tile capture file open failed");
            visible_file << "{\"schema_version\":1,\"width\":320,\"height\":180,\"tile_ids\":[";
            for (std::size_t i = 0; i < tiles.size(); ++i) {
                if (i != 0U) visible_file << ',';
                visible_file << tiles[i];
            }
            visible_file << "]}\n";
            if (!visible_file) throw std::runtime_error("N006 visible tile capture write failed");
        }

        const bool varying_state = !std::all_of(
            fractions.begin(),
            fractions.end(),
            [&](float value) { return value == fractions.front(); });
        std::vector<ReferenceMeta> references;
        std::vector<ReferenceMeta> independent_references;
        if (!skip_reference) {
            references.reserve(frames.size());
            if (varying_state) {
                for (std::uint32_t index = 0; index < frames.size(); ++index) {
                    references.push_back(render_reference(
                        frames[index].readback,
                        artifact_dir,
                        indexed_path("reference-8bounce", index)));
                }
            } else {
                const auto shared = render_reference(
                    frames.front().readback,
                    artifact_dir,
                    "frames/reference-8bounce.pfm");
                references.assign(frames.size(), shared);
                if (p1m3b_holdout_quality) {
                    // Distinct seeds from default reference, same source
                    // state, 8 diffuse bounces and original convergence.
                    lane_n::N001ReferenceSettings independent_settings{};
                    independent_settings.seed_a = 0x517cc1b727220a95ULL;
                    independent_settings.seed_b = 0x8b8b8b8b4f1bbcddULL;
                    const auto independent = render_reference(
                        frames.front().readback, artifact_dir,
                        "frames/reference-8bounce-independent.pfm",
                        independent_settings);
                    independent_references.assign(frames.size(), independent);
                }
            }
        }

        std::ofstream out(artifact_dir / "n006-candidate-evidence.json");
        if (!out) throw std::runtime_error("could not open N006 evidence JSON");
        out << std::setprecision(17)
            << "{\n"
            << "  \"schema_version\":1,\n"
            << "  \"protocol_version\":\"n006-p1-intervention-v1\",\n"
            << "  \"mode\":\"" << mode_name(mode) << "\",\n"
            << "  \"scenario\":\"" << scenario_name << "\",\n"
            << "  \"topology\":" << (topology ? "true" : "false") << ",\n"
            << "  \"variant\":\"" << variant_name << "\",\n"
            << "  \"source_warmup_frames\":" << source_warmup_frames << ",\n"
            << "  \"source_warmups_correct\":"
            << (source_warmups_correct ? "true" : "false") << ",\n"
            << "  \"p1l_stage_probe\":"
            << (p1l_stage_probe ? "true" : "false") << ",\n"
            << "  \"p1l_stage_fast\":"
            << (p1l_stage_fast ? "true" : "false") << ",\n"
            << "  \"p1l_b0_counts\":"
            << (p1l_b0_counts ? "true" : "false") << ",\n"
            << "  \"p1l_b1b_counts\":"
            << (p1l_b1b_counts ? "true" : "false") << ",\n"
            << "  \"p1l_b1_pattern\":\"" << p1l_b1_pattern << "\",\n"
            << "  \"p1l_b1c_axis_proxy\":" << (p1l_b1c_axis_proxy ? "true" : "false") << ",\n"
            << "  \"p1m0_consumer_coverage\":" << (p1m0_coverage ? "true" : "false") << ",\n"
            << "  \"p1m0_pretrace_coverage\":" << (p1m0_pretrace_coverage ? "true" : "false") << ",\n"
            << "  \"p1m1_canonical_token\":" << p1m1_canonical_token << ",\n"
            << "  \"p1m2_tetra_octant_directions\":"
            << (p1m2_tetra_octant_directions ? "true" : "false") << ",\n"
            << "  \"p1m2b_independent_state\":"
            << (p1m2b_independent_state ? "true" : "false") << ",\n"
            << "  \"p1m3_fractional_storage\":"
            << (p1m3_fractional_storage ? "true" : "false") << ",\n"
            << "  \"p1m3b_holdout_quality\":"
            << (p1m3b_holdout_quality ? "true" : "false") << ",\n"
            << "  \"p1l_b1c_axis_pack_cpu_us\":" << runtime.p1l_b1c_pack_cpu_us() << ",\n"
            << "  \"p1l_b1c_axis_packed_nodes\":" << runtime.p1l_b1c_packed_nodes() << ",\n"
            << "  \"p1l_hit_diagnostic_frame\":"
            << (p1l_b1 ? "1" : (p1l_sampled_hit ? "0" : "-1"))
            << ",\n"
            << "  \"three_arm_pattern\":\"" << three_arm_pattern << "\",\n"
            << "  \"target_state_warmup\":{\"frames\":"
            << target_state_warmup_frames
            << ",\"correct\":" << (target_warmup_correct ? "true" : "false")
            << ",\"last_traversal_maintenance_gpu\":"
            << last_target_warmup_maintenance_us
            << ",\"last_visible_owners\":" << last_target_warmup_owners
            << ",\"last_work_items\":" << last_target_warmup_work
            << ",\"maintenance_gpu_us\":" << warmup_maintenance_json.str()
            << "},\n"
            << "  \"depth_threshold\":" << depth_threshold << ",\n"
            << "  \"extra_rays_per_probe\":" << extra_rays_per_probe << ",\n"
            << "  \"selected_tile_id\":" << selected_tile_id << ",\n"
            << "  \"selected_cascade\":" << selected_cascade << ",\n"
            << "  \"reference_generation\":\""
            << (skip_reference ? "skipped" : "rendered") << "\",\n"
            << "  \"source\":{\"internal_correctness\":"
            << (source_correct ? "true" : "false") << ",\"extra\":";
        write_extra(out, source.extra);
        out << ",\"hit_diagnostics\":";
        if (p1l_sampled_hit) out << "null";
        else write_hit(out, source_hits);
        out << "},\n"
            << "  \"device\":{\"name\":\"" << runtime.device_name()
            << "\",\"driver_name\":\"" << runtime.driver_name()
            << "\",\"driver_info\":\"" << runtime.driver_info()
            << "\",\"api_version\":" << runtime.api_version()
            << ",\"timestamp_period_ns\":" << runtime.timestamp_period_ns()
            << "},\n"
            << "  \"frames\":[\n";
        for (std::size_t index = 0; index < frames.size(); ++index) {
            const auto& frame = frames[index];
            out << "    {\"index\":" << index
                << ",\"motion_fraction\":" << frame.motion_fraction
                << ",\"owner_budget\":" << frame.owner_budget
                << ",\"internal_correctness\":"
                << (frame.internal_correctness ? "true" : "false")
                << ",\"image\":\"" << frame.image_path << "\",\"reference\":";
            if (skip_reference) out << "null";
            else write_reference(out, references[index]);
            out << ",\"reference_independent\":";
            if (skip_reference || !p1m3b_holdout_quality) out << "null";
            else write_reference(out, independent_references[index]);
            out << ",\"hit_diagnostics\":";
            if (frame.hit_diagnostics_executed) write_hit(out, frame.hits);
            else out << "null";
            out << ",\"p1l_b1_arm\":";
            if (p1l_b1) out << frame.p1l_b1_arm;
            else out << "null";
            out << ",\"p1l_b1_primary_exact\":";
            if (p1l_b1) out << (frame.p1l_b1_primary_exact ? "true" : "false");
            else out << "null";
            out << ",\"p1l_b1b_counts\":";
            if (frame.p1l_b1b_profile) {
                write_p1l_b1b_profile(out, *frame.p1l_b1b_profile);
            } else {
                out << "null";
            }
            out << ",\"p1m0_consumer_coverage\":";
            if (frame.p1m0_coverage) {
                write_p1m0_coverage(out, *frame.p1m0_coverage);
            } else {
                out << "null";
            }
            out << ",\"p1l_b0_counts\":";
            if (frame.p1l_b0_profile) {
                write_p1l_b0_profile(out, *frame.p1l_b0_profile);
            } else {
                out << "null";
            }
            out << ",\"timing_us\":";
            write_timing(
                out,
                frame.result.frame.timings,
                frame.result.extra.extra_producer_gpu_us);
            out << ",\"stats\":";
            write_stats(out, frame.result.frame.stats);
            out << ",\"memory_bytes\":";
            write_memory(out, frame.result.frame.memory);
            out << ",\"extra\":";
            write_extra(out, frame.result.extra);
            out << '}';
            if (index + 1U != frames.size()) out << ',';
            out << '\n';
        }
        out << "  ]\n}\n";
        if (!out) throw std::runtime_error("N006 evidence write failed");

        const bool all_correct = source_correct && std::all_of(
            frames.begin(), frames.end(),
            [](const auto& frame) { return frame.internal_correctness; });
        std::cout << "N006 P2 candidate evidence: " << artifact_dir << '\n'
                  << "mode=" << mode_name(mode)
                  << " scenario=" << scenario_name
                  << " correctness=" << (all_correct ? "pass" : "FAIL")
                  << '\n';
        return all_correct ? 0 : 3;
    } catch (const std::exception& error) {
        std::cerr << "N006 candidate failure: " << error.what() << '\n';
        return 1;
    }
}
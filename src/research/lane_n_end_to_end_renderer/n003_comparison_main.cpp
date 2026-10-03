#include "n001_runtime.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace fs = std::filesystem;
namespace lane_n = phos::gi::research::integration;

namespace {

struct ScenarioSpec {
    const char* name;
    lane_n::I001Scenario scenario;
    bool topology;
};

constexpr std::array<ScenarioSpec, 6> kScenarios{{
    {"static", lane_n::I001Scenario::Static, false},
    {"camera-motion", lane_n::I001Scenario::CameraMotion, false},
    {"light-motion", lane_n::I001Scenario::LightMotion, false},
    {"moving-rigid", lane_n::I001Scenario::MovingRigid, false},
    {"stable-topology-deforming", lane_n::I001Scenario::DeformingControl, false},
    {"topology-changing-high-churn", lane_n::I001Scenario::DeformingControl, true},
}};

enum class Role { Current, Vanilla };

struct FrozenTiming {
    double renderer_prerequisite{};
    double frame_init_visibility{};
    double producer{};
    double ray_prepare{};
    double geometry_prepare_upload{};
    double acceleration_structure_maintenance{};
    double traversal{};
    double gather{};
    double radiance_storage{};
    double merge_resolve{};
    double synchronization{};
    double complete_gi{};
    double complete_renderer{};
};

[[nodiscard]] FrozenTiming freeze_timing(const lane_n::I001FrameTimings& t) {
    FrozenTiming out{};
    out.renderer_prerequisite = t.primary_visibility_us;
    out.frame_init_visibility =
        t.renderer_depth_us + t.frame_init_us + t.visibility_reuse_us;
    out.producer = t.producer_us;
    out.ray_prepare = t.ray_prepare_us;
    out.geometry_prepare_upload =
        t.surface_update_gpu_us + t.geometry_transfer_gpu_us +
        t.instance_transfer_gpu_us;
    out.acceleration_structure_maintenance =
        t.blas_update_us + t.tlas_update_us + t.hierarchy_upload_gpu_us;
    out.traversal = t.traversal_us;
    out.gather = t.radiance_us;
    out.radiance_storage = t.storage_update_us + t.invalidation_us;
    out.merge_resolve = t.merge_us + t.resolve_us;
    out.complete_gi = t.complete_gpu_us;
    out.complete_renderer = t.complete_renderer_gpu_us;
    const double accounted =
        out.renderer_prerequisite + out.frame_init_visibility + out.producer +
        out.ray_prepare + out.geometry_prepare_upload +
        out.acceleration_structure_maintenance + out.traversal + out.gather +
        out.radiance_storage + out.merge_resolve;
    const double remainder = out.complete_gi - accounted;
    if (remainder < -2.0) {
        throw std::runtime_error(
            "N003 comparison timing buckets exceed complete GI boundary");
    }
    out.synchronization = std::max(0.0, remainder);
    return out;
}

[[nodiscard]] lane_n::I001Options options_for(
    const fs::path& scene,
    const ScenarioSpec& spec) {
    lane_n::I001Options options{};
    options.scene = scene;
    options.variant = lane_n::I001Variant::LaneEFinalHwrt;
    options.scenario = spec.scenario;
    options.validation = true;
    return options;
}

struct Sample {
    FrozenTiming timing;
    lane_n::I001FrameStats stats;
    lane_n::I001Memory memory;
    lane_n::I001Quality quality;
    std::string device_name;
    std::string driver_name;
    std::string driver_info;
    std::uint32_t api_version{};
    float timestamp_period_ns{};
};

[[nodiscard]] Sample run_role(
    const fs::path& scene,
    const ScenarioSpec& spec,
    Role role,
    std::uint32_t source_warmup_frames) {
    lane_n::I001Runtime runtime(options_for(scene, spec));
    if (role == Role::Vanilla) {
        runtime.configure_n003_vanilla_software_baseline();
    }

    (void)runtime.run_frame(false);
    const auto source_quality = runtime.validate_last_frame();
    if (!source_quality.passed) {
        throw std::runtime_error(
            std::string("N003 comparison source correctness failed for ") +
            spec.name);
    }
    for (std::uint32_t index = 1; index < source_warmup_frames; ++index) {
        (void)runtime.run_frame(false);
    }

    lane_n::I001FrameResult measured{};
    if (spec.topology) {
        measured = role == Role::Current
            ? runtime.run_topology_churn_frame()
            : runtime.run_n003_vanilla_topology_churn_frame();
        if (measured.stats.topology_mutations != 1U ||
            measured.stats.backend_rebuilds != 1U ||
            measured.stats.topology_replaced_primitives == 0U) {
            throw std::runtime_error(
                "N003 comparison topology transition contract failed");
        }
    } else {
        measured = runtime.run_frame(true);
    }

    const auto quality = runtime.validate_last_frame();
    if (!quality.passed || measured.stats.storage_failures != 0U) {
        throw std::runtime_error(
            std::string("N003 comparison measured correctness failed for ") +
            spec.name);
    }

    return {
        freeze_timing(measured.timings),
        measured.stats,
        measured.memory,
        quality,
        runtime.device_name(),
        runtime.driver_name(),
        runtime.driver_info(),
        runtime.api_version(),
        runtime.timestamp_period_ns(),
    };
}

void require_same_device(const Sample& a, const Sample& b) {
    if (a.device_name != b.device_name || a.driver_name != b.driver_name ||
        a.driver_info != b.driver_info || a.api_version != b.api_version ||
        a.timestamp_period_ns != b.timestamp_period_ns) {
        throw std::runtime_error("N003 comparison device provenance mismatch");
    }
}

void require_same_workload(
    const ScenarioSpec& spec,
    const Sample& current,
    const Sample& vanilla) {
    const auto& a = current.stats;
    const auto& b = vanilla.stats;
    if (a.work_items != b.work_items ||
        a.outputs != b.outputs ||
        a.requested_work_items != b.requested_work_items ||
        a.requested_outputs != b.requested_outputs ||
        a.overflow != b.overflow ||
        a.visible_owners != b.visible_owners) {
        throw std::runtime_error(
            std::string("N003 comparison producer workload mismatch for ") +
            spec.name);
    }
    if (spec.topology &&
        (a.moved_primitives != b.moved_primitives ||
         a.topology_mutations != b.topology_mutations ||
         a.topology_replaced_primitives != b.topology_replaced_primitives ||
         a.backend_rebuilds != b.backend_rebuilds)) {
        throw std::runtime_error(
            "N003 comparison topology workload identity mismatch");
    }
}

void write_timing(std::ostream& out, const FrozenTiming& t, int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << std::setprecision(17)
        << pad << "{\n"
        << pad << "  \"complete_gi_gpu\": " << t.complete_gi << ",\n"
        << pad << "  \"complete_renderer_gpu\": " << t.complete_renderer << ",\n"
        << pad << "  \"stages\": {\n"
        << pad << "    \"renderer_prerequisite_attributable_to_gi\": " << t.renderer_prerequisite << ",\n"
        << pad << "    \"frame_init_visibility\": " << t.frame_init_visibility << ",\n"
        << pad << "    \"producer\": " << t.producer << ",\n"
        << pad << "    \"ray_prepare\": " << t.ray_prepare << ",\n"
        << pad << "    \"geometry_prepare_upload\": " << t.geometry_prepare_upload << ",\n"
        << pad << "    \"acceleration_structure_maintenance\": " << t.acceleration_structure_maintenance << ",\n"
        << pad << "    \"traversal\": " << t.traversal << ",\n"
        << pad << "    \"gather\": " << t.gather << ",\n"
        << pad << "    \"radiance_storage\": " << t.radiance_storage << ",\n"
        << pad << "    \"merge_resolve\": " << t.merge_resolve << ",\n"
        << pad << "    \"synchronization\": " << t.synchronization << "\n"
        << pad << "  }\n"
        << pad << "}";
}

void write_stats(std::ostream& out, const lane_n::I001FrameStats& s, int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << pad << "{\n"
        << pad << "  \"work_items\": " << s.work_items << ",\n"
        << pad << "  \"outputs\": " << s.outputs << ",\n"
        << pad << "  \"requested_work_items\": " << s.requested_work_items << ",\n"
        << pad << "  \"requested_outputs\": " << s.requested_outputs << ",\n"
        << pad << "  \"overflow\": " << s.overflow << ",\n"
        << pad << "  \"visible_owners\": " << s.visible_owners << ",\n"
        << pad << "  \"moved_primitives\": " << s.moved_primitives << ",\n"
        << pad << "  \"topology_mutations\": " << s.topology_mutations << ",\n"
        << pad << "  \"topology_replaced_primitives\": " << s.topology_replaced_primitives << ",\n"
        << pad << "  \"backend_rebuilds\": " << s.backend_rebuilds << ",\n"
        << pad << "  \"storage_allocations\": " << s.storage_allocations << ",\n"
        << pad << "  \"storage_updates\": " << s.storage_updates << ",\n"
        << pad << "  \"storage_invalidations\": " << s.storage_invalidations << ",\n"
        << pad << "  \"storage_failures\": " << s.storage_failures << "\n"
        << pad << "}";
}

void write_memory(std::ostream& out, const lane_n::I001Memory& m, int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << pad << "{\n"
        << pad << "  \"persistent\": " << m.persistent_bytes << ",\n"
        << pad << "  \"transient\": " << m.transient_bytes << ",\n"
        << pad << "  \"scratch\": " << m.scratch_bytes << ",\n"
        << pad << "  \"old_new_overlap\": " << m.old_new_overlap_bytes << ",\n"
        << pad << "  \"true_lifetime_peak\": " << m.peak_resident_bytes << ",\n"
        << pad << "  \"radiance_storage_persistent\": " << m.storage_capacity_bytes << ",\n"
        << pad << "  \"producer_stream_capacity\": " << m.stream_capacity_bytes << ",\n"
        << pad << "  \"image_transient\": " << m.image_bytes << "\n"
        << pad << "}";
}

void write_quality(std::ostream& out, const lane_n::I001Quality& q, int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << std::setprecision(17)
        << pad << "{\n"
        << pad << "  \"passed\": " << (q.passed ? "true" : "false") << ",\n"
        << pad << "  \"visibility_mismatches\": " << q.visibility_mismatches << ",\n"
        << pad << "  \"producer_semantic_errors\": " << q.producer_semantic_errors << ",\n"
        << pad << "  \"hit_mismatches\": " << q.hit_mismatches << ",\n"
        << pad << "  \"traversal_runtime_errors\": " << q.traversal_runtime_errors << ",\n"
        << pad << "  \"missing_probes\": " << q.missing_probes << ",\n"
        << pad << "  \"leaked_probes\": " << q.leaked_probes << ",\n"
        << pad << "  \"stale_storage_slots\": " << q.stale_storage_slots << ",\n"
        << pad << "  \"resolved_output_mismatches\": " << q.resolved_output_mismatches << ",\n"
        << pad << "  \"radiance_rms_error\": " << q.radiance_rms_error << ",\n"
        << pad << "  \"radiance_max_abs_error\": " << q.radiance_max_abs_error << "\n"
        << pad << "}";
}

void write_sample(std::ostream& out, const Sample& sample, int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << pad << "{\n" << pad << "  \"timing_us\": ";
    write_timing(out, sample.timing, indent + 2);
    out << ",\n" << pad << "  \"stats\": ";
    write_stats(out, sample.stats, indent + 2);
    out << ",\n" << pad << "  \"memory_bytes\": ";
    write_memory(out, sample.memory, indent + 2);
    out << ",\n" << pad << "  \"correctness\": ";
    write_quality(out, sample.quality, indent + 2);
    out << "\n" << pad << "}";
}

} // namespace

int main(int argc, char** argv) {
    fs::path scene =
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf";
    fs::path artifact_dir;
    std::uint32_t source_warmup_frames = 32U;
    std::string start_order = "AB";

    for (int index = 1; index < argc; ++index) {
        const std::string_view arg = argv[index];
        if (arg == "--scene" && index + 1 < argc) {
            scene = argv[++index];
        } else if (arg == "--artifact-dir" && index + 1 < argc) {
            artifact_dir = argv[++index];
        } else if (arg == "--source-warmup-frames" && index + 1 < argc) {
            source_warmup_frames =
                static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--start-order" && index + 1 < argc) {
            start_order = argv[++index];
        } else {
            std::cerr << "usage: phos-n003-comparison --artifact-dir PATH "
                         "[--scene PATH] [--source-warmup-frames N] "
                         "[--start-order AB|BA]\n";
            return 2;
        }
    }
    if (artifact_dir.empty() || source_warmup_frames == 0U ||
        (start_order != "AB" && start_order != "BA")) {
        std::cerr << "invalid N003 comparison arguments\n";
        return 2;
    }

    try {
        fs::create_directories(artifact_dir);
        struct PairResult {
            const ScenarioSpec* spec{};
            Sample current;
            Sample vanilla;
        };
        std::vector<PairResult> results;
        results.reserve(kScenarios.size());

        for (const auto& spec : kScenarios) {
            Sample current{};
            Sample vanilla{};
            if (start_order == "AB") {
                current = run_role(scene, spec, Role::Current, source_warmup_frames);
                vanilla = run_role(scene, spec, Role::Vanilla, source_warmup_frames);
            } else {
                vanilla = run_role(scene, spec, Role::Vanilla, source_warmup_frames);
                current = run_role(scene, spec, Role::Current, source_warmup_frames);
            }
            require_same_device(current, vanilla);
            require_same_workload(spec, current, vanilla);
            std::cout << "N003 comparison " << spec.name
                      << ": current=" << current.timing.complete_renderer
                      << "us vanilla=" << vanilla.timing.complete_renderer << "us\n";
            results.push_back({&spec, std::move(current), std::move(vanilla)});
        }

        const auto& device = results.front().current;
        for (const auto& result : results) {
            require_same_device(device, result.current);
            require_same_device(device, result.vanilla);
        }

        std::ofstream out(artifact_dir / "n003-comparison-pair.json");
        if (!out) {
            throw std::runtime_error("could not open N003 comparison artifact");
        }
        out << std::setprecision(17)
            << "{\n"
            << "  \"schema_version\": 1,\n"
            << "  \"protocol_version\": \"current-vs-vanilla-v1\",\n"
            << "  \"roles\": {\"A\": \"current-lane-e-final-hwrt\", "
               "\"B\": \"vanilla-software-bvh\"},\n"
            << "  \"execution_start_order\": \"" << start_order << "\",\n"
            << "  \"source_warmup_frames\": " << source_warmup_frames << ",\n"
            << "  \"device\": {\n"
            << "    \"name\": \"" << device.device_name << "\",\n"
            << "    \"driver_name\": \"" << device.driver_name << "\",\n"
            << "    \"driver_info\": \"" << device.driver_info << "\",\n"
            << "    \"api_version\": " << device.api_version << ",\n"
            << "    \"timestamp_period_ns\": " << device.timestamp_period_ns << "\n"
            << "  },\n"
            << "  \"scenarios\": {\n";
        for (std::size_t index = 0; index < results.size(); ++index) {
            const auto& result = results[index];
            out << "    \"" << result.spec->name << "\": {\n"
                << "      \"A\": ";
            write_sample(out, result.current, 6);
            out << ",\n      \"B\": ";
            write_sample(out, result.vanilla, 6);
            out << "\n    }";
            if (index + 1U != results.size()) out << ',';
            out << '\n';
        }
        out << "  }\n}\n";
        if (!out) {
            throw std::runtime_error("N003 comparison artifact write failed");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "N003 comparison failure: " << error.what() << '\n';
        return 1;
    }
}

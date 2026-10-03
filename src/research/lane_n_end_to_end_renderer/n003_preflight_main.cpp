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
    out.synchronization = std::max(0.0, out.complete_gi - accounted);
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
    std::string device_name;
    std::string driver_name;
    std::string driver_info;
    std::uint32_t api_version{};
    float timestamp_period_ns{};
};

[[nodiscard]] Sample run_role(
    const fs::path& scene,
    const ScenarioSpec& spec,
    std::uint32_t source_warmup_frames) {
    lane_n::I001Runtime runtime(options_for(scene, spec));

    // Validate the source state early, then leave the final warm-up frame
    // immediately adjacent to the measured target transition. v3 validated
    // after all warm-up frames, and that validation path performs independent
    // reference GPU work and buffer traffic; it broke the intended hot-start
    // boundary before the measured frame.
    (void)runtime.run_frame(false);
    const auto source_quality = runtime.validate_last_frame();
    if (!source_quality.passed) {
        throw std::runtime_error(
            std::string("N003 preflight source correctness failed for ") +
            spec.name);
    }
    for (std::uint32_t index = 1; index < source_warmup_frames; ++index) {
        (void)runtime.run_frame(false);
    }

    lane_n::I001FrameResult measured{};
    if (spec.topology) {
        measured = runtime.run_topology_churn_frame();
        if (measured.stats.topology_mutations != 1U ||
            measured.stats.backend_rebuilds != 1U ||
            measured.stats.topology_replaced_primitives == 0U) {
            throw std::runtime_error(
                "N003 preflight topology transition was not exercised exactly once");
        }
    } else {
        measured = runtime.run_frame(true);
    }

    const auto quality = runtime.validate_last_frame();
    if (!quality.passed) {
        throw std::runtime_error(
            std::string("N003 preflight measured correctness failed for ") +
            spec.name);
    }

    return {
        freeze_timing(measured.timings),
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
        throw std::runtime_error("N003 preflight A/B device provenance mismatch");
    }
}

void write_timing(std::ostream& out, const FrozenTiming& timing, int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << std::setprecision(17)
        << pad << "{\n"
        << pad << "  \"complete_gi_gpu\": " << timing.complete_gi << ",\n"
        << pad << "  \"complete_renderer_gpu\": " << timing.complete_renderer << ",\n"
        << pad << "  \"stages\": {\n"
        << pad << "    \"renderer_prerequisite_attributable_to_gi\": " << timing.renderer_prerequisite << ",\n"
        << pad << "    \"frame_init_visibility\": " << timing.frame_init_visibility << ",\n"
        << pad << "    \"producer\": " << timing.producer << ",\n"
        << pad << "    \"ray_prepare\": " << timing.ray_prepare << ",\n"
        << pad << "    \"geometry_prepare_upload\": " << timing.geometry_prepare_upload << ",\n"
        << pad << "    \"acceleration_structure_maintenance\": " << timing.acceleration_structure_maintenance << ",\n"
        << pad << "    \"traversal\": " << timing.traversal << ",\n"
        << pad << "    \"gather\": " << timing.gather << ",\n"
        << pad << "    \"radiance_storage\": " << timing.radiance_storage << ",\n"
        << pad << "    \"merge_resolve\": " << timing.merge_resolve << ",\n"
        << pad << "    \"synchronization\": " << timing.synchronization << "\n"
        << pad << "  }\n"
        << pad << "}";
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
            std::cerr << "usage: phos-n003-preflight --artifact-dir PATH "
                         "[--scene PATH] [--source-warmup-frames N] "
                         "[--start-order AB|BA]\n";
            return 2;
        }
    }
    if (artifact_dir.empty() || source_warmup_frames == 0U ||
        (start_order != "AB" && start_order != "BA")) {
        std::cerr << "invalid N003 preflight arguments\n";
        return 2;
    }

    try {
        fs::create_directories(artifact_dir);
        struct PairResult {
            const ScenarioSpec* spec{};
            Sample a;
            Sample b;
        };
        std::vector<PairResult> results;
        results.reserve(kScenarios.size());

        for (const auto& spec : kScenarios) {
            Sample a{};
            Sample b{};
            if (start_order == "AB") {
                a = run_role(scene, spec, source_warmup_frames);
                b = run_role(scene, spec, source_warmup_frames);
            } else {
                b = run_role(scene, spec, source_warmup_frames);
                a = run_role(scene, spec, source_warmup_frames);
            }
            require_same_device(a, b);
            std::cout << "N003 paired control " << spec.name
                      << ": A=" << a.timing.complete_renderer
                      << "us B=" << b.timing.complete_renderer << "us\n";
            results.push_back({&spec, std::move(a), std::move(b)});
        }

        const auto& device = results.front().a;
        for (const auto& result : results) {
            require_same_device(device, result.a);
            require_same_device(device, result.b);
        }

        std::ofstream out(artifact_dir / "n003-timing-pair.json");
        if (!out) {
            throw std::runtime_error("could not open N003 timing pair artifact");
        }
        out << std::setprecision(17)
            << "{\n"
            << "  \"schema_version\": 1,\n"
            << "  \"protocol_version\": \"paired-control-v4\",\n"
            << "  \"source_warmup_frames\": " << source_warmup_frames << ",\n"
            << "  \"warmup_validation_position\": \"after-first-source-frame\",\n"
            << "  \"start_order\": \"" << start_order << "\",\n"
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
            write_timing(out, result.a.timing, 6);
            out << ",\n      \"B\": ";
            write_timing(out, result.b.timing, 6);
            out << "\n    }";
            if (index + 1U != results.size()) out << ',';
            out << '\n';
        }
        out << "  }\n}\n";
        if (!out) {
            throw std::runtime_error("N003 timing pair artifact write failed");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "N003 preflight failure: " << error.what() << '\n';
        return 1;
    }
}

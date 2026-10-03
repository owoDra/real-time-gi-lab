#include "n001_runtime.hpp"

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

namespace fs = std::filesystem;
namespace lane_n = phos::gi::research::integration;

namespace {

struct RoleSample {
    lane_n::I001FrameStats source_stats{};
    lane_n::I001FrameStats target_stats{};
    double complete_gi_gpu_us{};
    double complete_renderer_gpu_us{};
    std::string device_name;
    std::string driver_name;
    std::string driver_info;
    std::uint32_t api_version{};
    float timestamp_period_ns{};
};

[[nodiscard]] lane_n::I001Options options_for(const fs::path& scene) {
    lane_n::I001Options options{};
    options.scene = scene;
    options.variant = lane_n::I001Variant::LaneEFinalHwrt;
    options.scenario = lane_n::I001Scenario::MovingRigid;
    options.validation = true;
    return options;
}

[[nodiscard]] RoleSample run_role(
    const fs::path& scene,
    std::uint32_t source_warmup_frames) {
    lane_n::I001Runtime runtime(options_for(scene));

    auto source = runtime.run_frame(false);
    const auto source_quality = runtime.validate_last_frame();
    if (!source_quality.passed) {
        throw std::runtime_error("N003 moving diagnostic source correctness failed");
    }
    for (std::uint32_t index = 1; index < source_warmup_frames; ++index) {
        source = runtime.run_frame(false);
    }

    const auto measured = runtime.run_frame(true);
    const auto target_quality = runtime.validate_last_frame();
    if (!target_quality.passed) {
        throw std::runtime_error("N003 moving diagnostic target correctness failed");
    }

    return {
        source.stats,
        measured.stats,
        measured.timings.complete_gpu_us,
        measured.timings.complete_renderer_gpu_us,
        runtime.device_name(),
        runtime.driver_name(),
        runtime.driver_info(),
        runtime.api_version(),
        runtime.timestamp_period_ns(),
    };
}

void require_same_device(const RoleSample& a, const RoleSample& b) {
    if (a.device_name != b.device_name || a.driver_name != b.driver_name ||
        a.driver_info != b.driver_info || a.api_version != b.api_version ||
        a.timestamp_period_ns != b.timestamp_period_ns) {
        throw std::runtime_error("N003 moving diagnostic A/B device provenance mismatch");
    }
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
        << pad << "  \"segment_membership_changes\": " << s.segment_membership_changes << ",\n"
        << pad << "  \"hierarchy_refit_segments\": " << s.hierarchy_refit_segments << ",\n"
        << pad << "  \"hierarchy_rebuilt_segments\": " << s.hierarchy_rebuilt_segments << ",\n"
        << pad << "  \"topology_mutations\": " << s.topology_mutations << ",\n"
        << pad << "  \"topology_replaced_primitives\": " << s.topology_replaced_primitives << ",\n"
        << pad << "  \"backend_rebuilds\": " << s.backend_rebuilds << ",\n"
        << pad << "  \"storage_allocations\": " << s.storage_allocations << ",\n"
        << pad << "  \"storage_updates\": " << s.storage_updates << ",\n"
        << pad << "  \"storage_invalidations\": " << s.storage_invalidations << ",\n"
        << pad << "  \"storage_failures\": " << s.storage_failures << "\n"
        << pad << "}";
}

void write_role(std::ostream& out, const RoleSample& sample, int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << std::setprecision(17)
        << pad << "{\n"
        << pad << "  \"source_stats\": ";
    write_stats(out, sample.source_stats, indent + 2);
    out << ",\n" << pad << "  \"target_stats\": ";
    write_stats(out, sample.target_stats, indent + 2);
    out << ",\n"
        << pad << "  \"complete_gi_gpu_us\": " << sample.complete_gi_gpu_us << ",\n"
        << pad << "  \"complete_renderer_gpu_us\": " << sample.complete_renderer_gpu_us << "\n"
        << pad << "}";
}

} // namespace

int main(int argc, char** argv) {
    fs::path scene = "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf";
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
            source_warmup_frames = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--start-order" && index + 1 < argc) {
            start_order = argv[++index];
        } else {
            std::cerr << "usage: phos-n003-workload-diagnostic --artifact-dir PATH "
                         "[--scene PATH] [--source-warmup-frames N] [--start-order AB|BA]\n";
            return 2;
        }
    }
    if (artifact_dir.empty() || source_warmup_frames == 0U ||
        (start_order != "AB" && start_order != "BA")) {
        std::cerr << "invalid N003 moving diagnostic arguments\n";
        return 2;
    }

    try {
        fs::create_directories(artifact_dir);
        RoleSample a{};
        RoleSample b{};
        if (start_order == "AB") {
            a = run_role(scene, source_warmup_frames);
            b = run_role(scene, source_warmup_frames);
        } else {
            b = run_role(scene, source_warmup_frames);
            a = run_role(scene, source_warmup_frames);
        }
        require_same_device(a, b);

        std::ofstream out(artifact_dir / "n003-moving-workload-pair.json");
        if (!out) {
            throw std::runtime_error("could not open N003 moving diagnostic artifact");
        }
        out << std::setprecision(17)
            << "{\n"
            << "  \"schema_version\": 1,\n"
            << "  \"protocol_version\": \"moving-rigid-workload-invariance-v1\",\n"
            << "  \"source_warmup_frames\": " << source_warmup_frames << ",\n"
            << "  \"start_order\": \"" << start_order << "\",\n"
            << "  \"device\": {\n"
            << "    \"name\": \"" << a.device_name << "\",\n"
            << "    \"driver_name\": \"" << a.driver_name << "\",\n"
            << "    \"driver_info\": \"" << a.driver_info << "\",\n"
            << "    \"api_version\": " << a.api_version << ",\n"
            << "    \"timestamp_period_ns\": " << a.timestamp_period_ns << "\n"
            << "  },\n"
            << "  \"A\": ";
        write_role(out, a, 2);
        out << ",\n  \"B\": ";
        write_role(out, b, 2);
        out << "\n}\n";
        if (!out) {
            throw std::runtime_error("N003 moving diagnostic artifact write failed");
        }

        std::cout << "N003 moving workload diagnostic: A=" << a.complete_renderer_gpu_us
                  << "us B=" << b.complete_renderer_gpu_us << "us\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "N003 moving workload diagnostic failure: " << error.what() << '\n';
        return 1;
    }
}

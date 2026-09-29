#include "i001_runtime.hpp"

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace integration = phos::gi::research::integration;

namespace {

struct Cli {
    integration::I001Options options;
    std::uint32_t warmup_frames{1};
    std::uint32_t measured_frames{1};
};

[[nodiscard]] bool dynamic_scenario(integration::I001Scenario value) noexcept {
    using S = integration::I001Scenario;
    return value == S::MovingRigid ||
           value == S::SparseMovingStress ||
           value == S::DenseMovingStress ||
           value == S::LargeWorldMovingStress ||
           value == S::VerticalWorldMovingStress;
}

Cli parse_cli(int argc, char** argv) {
    Cli cli;
    cli.options.variant = integration::I001Variant::TransientLbvh;
    cli.options.scenario = integration::I001Scenario::Static;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        const auto value = [&](const char* option) -> std::string {
            if (i + 1 >= argc) {
                throw std::runtime_error(std::string(option) + " requires a value");
            }
            return argv[++i];
        };
        if (arg == "--scene") {
            cli.options.scene = value("--scene");
        } else if (arg == "--variant") {
            cli.options.variant = integration::i001_parse_variant(value("--variant"));
            if (cli.options.variant != integration::I001Variant::VanillaSoftware &&
                cli.options.variant != integration::I001Variant::CombinedHwrt &&
                cli.options.variant != integration::I001Variant::CombinedSoftware &&
                cli.options.variant != integration::I001Variant::TransientLbvh) {
                throw std::runtime_error("G002 variant is outside the frozen diagnostic set");
            }
        } else if (arg == "--scenario") {
            cli.options.scenario = integration::i001_parse_scenario(value("--scenario"));
        } else if (arg == "--warmup-frames") {
            cli.warmup_frames = static_cast<std::uint32_t>(std::stoul(value("--warmup-frames")));
        } else if (arg == "--measured-frames") {
            cli.measured_frames = static_cast<std::uint32_t>(std::stoul(value("--measured-frames")));
            if (cli.measured_frames == 0U) {
                throw std::runtime_error("G002 measured frames must be positive");
            }
        } else if (arg == "--validation") {
            cli.options.validation = true;
        } else if (arg == "--help") {
            std::cout
                << "phos-lane-g-g002 [--scene path] "
                   "[--variant vanilla-software|combined-hwrt|combined-software|transient-lbvh] "
                   "[--scenario <I001 scenario>] [--warmup-frames N] "
                   "[--measured-frames N] [--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error("unknown G002 argument: " + arg);
        }
    }
    return cli;
}

std::filesystem::path artifact_root() {
    if (const char* value = std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");
        value != nullptr && *value != '\0') {
        return value;
    }
    return "out/research/lane-g-transient-lbvh-hardening/"
           "002-timing-repeatability-diagnosis/manual";
}

void write_header(std::ostream& out) {
    out
        << "variant,scenario,device,warmup_frames,measured_frames,measured_index,"
           "frame_kind,setup_wall_us,complete_frame_wall_us,"
           "renderer_depth_us,frame_init_us,visibility_reuse_us,producer_us,"
           "ray_prepare_us,traversal_maintenance_gpu_us,dynamic_update_wall_us,"
           "dynamic_builder_reset_us,dynamic_builder_input_us,dynamic_builder_aabb_us,"
           "dynamic_builder_morton_us,dynamic_builder_sort_us,dynamic_builder_topology_us,"
           "dynamic_builder_bounds_us,dynamic_builder_us,static_traversal_us,"
           "dynamic_traversal_us,cross_structure_merge_us,traversal_us,radiance_us,"
           "merge_us,storage_update_us,invalidation_us,resolve_us,complete_gpu_us,"
           "incremental_gi_us,moved_primitives,segment_membership_changes,"
           "peak_resident_bytes\n";
}

void write_row(
    std::ostream& out,
    const Cli& cli,
    const integration::I001Runtime& runtime,
    const integration::I001FrameResult& result,
    std::uint32_t index,
    double setup_wall_us,
    double complete_frame_wall_us) {
    const bool transition = dynamic_scenario(cli.options.scenario) && index == 0U;
    const auto& t = result.timings;
    out << std::fixed << std::setprecision(6)
        << integration::i001_variant_name(cli.options.variant) << ','
        << integration::i001_scenario_name(cli.options.scenario) << ','
        << '"' << runtime.device_name() << '"' << ','
        << cli.warmup_frames << ',' << cli.measured_frames << ',' << index << ','
        << (transition ? "transition" : "steady-target") << ','
        << setup_wall_us << ',' << complete_frame_wall_us << ','
        << t.renderer_depth_us << ',' << t.frame_init_us << ','
        << t.visibility_reuse_us << ',' << t.producer_us << ','
        << t.ray_prepare_us << ',' << t.traversal_maintenance_gpu_us << ','
        << t.dynamic_update_wall_us << ','
        << t.dynamic_builder_reset_us << ',' << t.dynamic_builder_input_us << ','
        << t.dynamic_builder_aabb_us << ',' << t.dynamic_builder_morton_us << ','
        << t.dynamic_builder_sort_us << ',' << t.dynamic_builder_topology_us << ','
        << t.dynamic_builder_bounds_us << ',' << t.dynamic_builder_us << ','
        << t.static_traversal_us << ',' << t.dynamic_traversal_us << ','
        << t.cross_structure_merge_us << ',' << t.traversal_us << ','
        << t.radiance_us << ',' << t.merge_us << ',' << t.storage_update_us << ','
        << t.invalidation_us << ',' << t.resolve_us << ',' << t.complete_gpu_us << ','
        << t.incremental_gi_us << ',' << result.stats.moved_primitives << ','
        << result.stats.segment_membership_changes << ','
        << result.memory.peak_resident_bytes << '\n';
}

void write_device(
    const std::filesystem::path& path,
    const Cli& cli,
    const integration::I001Runtime& runtime) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot create G002 device metadata");
    out
        << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"plan_version\": \"lane-g-g002-v1\",\n"
        << "  \"variant\": \"" << integration::i001_variant_name(cli.options.variant) << "\",\n"
        << "  \"scenario\": \"" << integration::i001_scenario_name(cli.options.scenario) << "\",\n"
        << "  \"device\": \"" << runtime.device_name() << "\",\n"
        << "  \"driver_name\": \"" << runtime.driver_name() << "\",\n"
        << "  \"driver_info\": \"" << runtime.driver_info() << "\",\n"
        << "  \"api_version\": " << runtime.api_version() << ",\n"
        << "  \"validation\": " << (cli.options.validation ? "true" : "false") << "\n"
        << "}\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto cli = parse_cli(argc, argv);
        const auto setup_start = std::chrono::steady_clock::now();
        integration::I001Runtime runtime(cli.options);
        const double setup_wall_us =
            std::chrono::duration<double, std::micro>(
                std::chrono::steady_clock::now() - setup_start).count();

        for (std::uint32_t i = 0; i < cli.warmup_frames; ++i) {
            (void)runtime.run_frame(false);
        }

        const auto root = artifact_root();
        std::filesystem::create_directories(root);
        std::ofstream csv(root / "g002-frames.csv");
        if (!csv) throw std::runtime_error("cannot create G002 frame CSV");
        write_header(csv);

        for (std::uint32_t i = 0; i < cli.measured_frames; ++i) {
            const auto start = std::chrono::steady_clock::now();
            const auto result = runtime.run_frame(true);
            const double wall_us =
                std::chrono::duration<double, std::micro>(
                    std::chrono::steady_clock::now() - start).count();
            write_row(csv, cli, runtime, result, i, setup_wall_us, wall_us);
        }
        write_device(root / "g002-device.json", cli, runtime);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "G002 error: " << error.what() << '\n';
        return 1;
    }
}

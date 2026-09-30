#include "i001_runtime.hpp"

#include <chrono>
#include <cstdlib>
#include <cstdint>
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
    std::uint32_t warmup_frames{16};
    std::uint32_t measured_frames{16};
};

[[nodiscard]] bool allowed_variant(integration::I001Variant value) noexcept {
    using V = integration::I001Variant;
    return value == V::HardenedTransientLbvh ||
           value == V::TransientLbvh ||
           value == V::CombinedHwrt ||
           value == V::VanillaSoftware;
}

[[nodiscard]] bool dynamic_case(integration::I001Scenario value) noexcept {
    using S = integration::I001Scenario;
    return value == S::MovingRigid ||
           value == S::SparseMovingStress ||
           value == S::DenseMovingStress ||
           value == S::LargeWorldMovingStress ||
           value == S::VerticalWorldMovingStress;
}

[[nodiscard]] bool target_state(
    integration::I001Scenario scenario,
    std::uint32_t absolute_frame_index) noexcept {
    if (!dynamic_case(scenario)) {
        return true;
    }
    // Warmup frame zero is source-state false. Alternation continues through the
    // measured phase, so every measured dynamic frame crosses the update boundary.
    return (absolute_frame_index & 1U) != 0U;
}

Cli parse_cli(int argc, char** argv) {
    Cli cli;
    cli.options.variant = integration::I001Variant::HardenedTransientLbvh;
    cli.options.scenario = integration::I001Scenario::Static;
    cli.options.geometry_class = integration::I001GeometryClass::RepresentativeRigid;

    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        const auto value = [&](const char* option) -> std::string {
            if (index + 1 >= argc) {
                throw std::runtime_error(std::string(option) + " requires a value");
            }
            return argv[++index];
        };
        if (argument == "--scene") {
            cli.options.scene = value("--scene");
        } else if (argument == "--variant") {
            cli.options.variant = integration::i001_parse_variant(value("--variant"));
            if (!allowed_variant(cli.options.variant)) {
                throw std::runtime_error("H001 variant outside frozen set");
            }
        } else if (argument == "--scenario") {
            cli.options.scenario = integration::i001_parse_scenario(value("--scenario"));
        } else if (argument == "--geometry-class") {
            cli.options.geometry_class =
                integration::i001_parse_geometry_class(value("--geometry-class"));
        } else if (argument == "--warmup-frames") {
            cli.warmup_frames = static_cast<std::uint32_t>(
                std::stoul(value("--warmup-frames")));
        } else if (argument == "--measured-frames") {
            cli.measured_frames = static_cast<std::uint32_t>(
                std::stoul(value("--measured-frames")));
            if (cli.measured_frames == 0U) {
                throw std::runtime_error("H001 measured frames must be positive");
            }
        } else if (argument == "--validation") {
            cli.options.validation = true;
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-h-h001 [--scene path] [--variant name] "
                   "[--scenario name] [--geometry-class name] "
                   "[--warmup-frames N] [--measured-frames N] [--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error("unknown H001 argument: " + argument);
        }
    }
    return cli;
}

std::filesystem::path artifact_root() {
    if (const char* value = std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");
        value != nullptr && *value != '\0') {
        return value;
    }
    return "out/research/lane-h-topology-rebuild-crossover/"
           "001-safe-timing-methodology/manual";
}

void write_header(std::ostream& out) {
    out
        << "variant,scenario,geometry_class,device,phase,frame_index,absolute_frame_index,"
           "target_state,setup_wall_us,complete_frame_wall_us,complete_gpu_us,"
           "dynamic_update_wall_us,traversal_maintenance_gpu_us,dynamic_builder_us,"
           "traversal_us,moved_primitives,segment_membership_changes,"
           "topology_replaced_primitives,persistent_bytes,transient_bytes,scratch_bytes,"
           "peak_resident_bytes\n";
}

void write_row(
    std::ostream& out,
    const Cli& cli,
    const integration::I001Runtime& runtime,
    const integration::I001FrameResult& result,
    const char* phase,
    std::uint32_t phase_index,
    std::uint32_t absolute_index,
    bool state,
    double setup_wall_us,
    double complete_frame_wall_us) {
    const auto& t = result.timings;
    const auto& s = result.stats;
    const auto& m = result.memory;
    out << std::fixed << std::setprecision(6)
        << integration::i001_variant_name(cli.options.variant) << ','
        << integration::i001_scenario_name(cli.options.scenario) << ','
        << integration::i001_geometry_class_name(cli.options.geometry_class) << ','
        << '"' << runtime.device_name() << '"' << ','
        << phase << ',' << phase_index << ',' << absolute_index << ','
        << (state ? 1 : 0) << ',' << setup_wall_us << ',' << complete_frame_wall_us << ','
        << t.complete_gpu_us << ',' << t.dynamic_update_wall_us << ','
        << t.traversal_maintenance_gpu_us << ',' << t.dynamic_builder_us << ','
        << t.traversal_us << ',' << s.moved_primitives << ','
        << s.segment_membership_changes << ',' << s.topology_replaced_primitives << ','
        << m.persistent_bytes << ',' << m.transient_bytes << ',' << m.scratch_bytes << ','
        << m.peak_resident_bytes << '\n';
}

void write_device(
    const std::filesystem::path& path,
    const Cli& cli,
    const integration::I001Runtime& runtime) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("cannot create H001 device metadata");
    }
    out
        << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"plan_version\": \"lane-h-h001-safe-timing-v1\",\n"
        << "  \"variant\": \"" << integration::i001_variant_name(cli.options.variant) << "\",\n"
        << "  \"scenario\": \"" << integration::i001_scenario_name(cli.options.scenario) << "\",\n"
        << "  \"geometry_class\": \""
        << integration::i001_geometry_class_name(cli.options.geometry_class) << "\",\n"
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
        std::cout << "GPU: " << runtime.device_name() << '\\n';
        const double setup_wall_us = std::chrono::duration<double, std::micro>(
            std::chrono::steady_clock::now() - setup_start).count();

        const auto root = artifact_root();
        std::filesystem::create_directories(root);
        std::ofstream csv(root / "h001-frames.csv");
        if (!csv) {
            throw std::runtime_error("cannot create H001 frame CSV");
        }
        write_header(csv);

        std::uint32_t absolute_index = 0;
        for (std::uint32_t index = 0; index < cli.warmup_frames; ++index, ++absolute_index) {
            const bool state = target_state(cli.options.scenario, absolute_index);
            const auto start = std::chrono::steady_clock::now();
            const auto result = runtime.run_frame(state);
            const double wall_us = std::chrono::duration<double, std::micro>(
                std::chrono::steady_clock::now() - start).count();
            write_row(
                csv, cli, runtime, result, "warmup", index, absolute_index,
                state, setup_wall_us, wall_us);
        }

        for (std::uint32_t index = 0; index < cli.measured_frames; ++index, ++absolute_index) {
            const bool state = target_state(cli.options.scenario, absolute_index);
            const auto start = std::chrono::steady_clock::now();
            const auto result = runtime.run_frame(state);
            const double wall_us = std::chrono::duration<double, std::micro>(
                std::chrono::steady_clock::now() - start).count();
            write_row(
                csv, cli, runtime, result, "measured", index, absolute_index,
                state, setup_wall_us, wall_us);
        }

        write_device(root / "h001-device.json", cli, runtime);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "H001 error: " << error.what() << '\n';
        return 1;
    }
}

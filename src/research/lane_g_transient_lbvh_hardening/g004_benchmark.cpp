#include "i001_runtime.hpp"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace integration = phos::gi::research::integration;

namespace {

struct Cli {
    integration::I001Options options;
};

Cli parse_cli(int argc, char** argv) {
    Cli cli;
    cli.options.variant = integration::I001Variant::HardenedTransientLbvh;
    cli.options.scenario = integration::I001Scenario::Static;
    cli.options.geometry_class =
        integration::I001GeometryClass::RepresentativeRigid;

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
        } else if (argument == "--scenario") {
            cli.options.scenario =
                integration::i001_parse_scenario(value("--scenario"));
        } else if (argument == "--geometry-class") {
            cli.options.geometry_class =
                integration::i001_parse_geometry_class(
                    value("--geometry-class"));
        } else if (argument == "--validation") {
            cli.options.validation = true;
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-g-g004 [--scene path] "
                   "[--scenario name] [--geometry-class name] "
                   "[--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error(
                "unknown G004 argument: " + argument);
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
           "004-integration-hardening/manual";
}

void write_device(
    const std::filesystem::path& path,
    const Cli& cli,
    const integration::I001Runtime& runtime) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("cannot create G004 device metadata");
    }
    out
        << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"plan_version\": \"lane-g-g004-v1\",\n"
        << "  \"variant\": \"hardened-transient-lbvh\",\n"
        << "  \"scenario\": \""
        << integration::i001_scenario_name(cli.options.scenario)
        << "\",\n"
        << "  \"geometry_class\": \""
        << integration::i001_geometry_class_name(
               cli.options.geometry_class)
        << "\",\n"
        << "  \"device\": \"" << runtime.device_name() << "\",\n"
        << "  \"driver_name\": \"" << runtime.driver_name() << "\",\n"
        << "  \"driver_info\": \"" << runtime.driver_info() << "\",\n"
        << "  \"api_version\": " << runtime.api_version() << ",\n"
        << "  \"validation\": "
        << (cli.options.validation ? "true" : "false") << "\n"
        << "}\n";
}

void write_frame(
    const std::filesystem::path& path,
    const Cli& cli,
    const integration::I001Runtime& runtime,
    const integration::I001FrameResult& result) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("cannot create G004 frame CSV");
    }
    const auto& q = result.quality;
    const auto& s = result.stats;
    const auto& m = result.memory;
    const auto& t = result.timings;

    out
        << "variant,scenario,geometry_class,device,quality_passed,"
           "visibility_mismatches,producer_semantic_errors,hit_mismatches,"
           "traversal_runtime_errors,missing_probes,leaked_probes,"
           "stale_storage_slots,resolved_output_mismatches,"
           "radiance_rms_error,radiance_max_abs_error,temporal_rms_error,"
           "temporal_max_abs_error,storage_failures,overflow,work_items,"
           "outputs,moved_primitives,dynamic_groups,deformed_primitives,"
           "topology_replaced_primitives,runtime_resident_bytes,"
           "setup_peak_bytes,peak_resident_bytes,complete_gpu_us,"
           "dynamic_update_wall_us\n";

    out
        << "hardened-transient-lbvh,"
        << integration::i001_scenario_name(cli.options.scenario) << ','
        << integration::i001_geometry_class_name(
               cli.options.geometry_class) << ','
        << '"' << runtime.device_name() << '"' << ','
        << (q.passed ? 1 : 0) << ','
        << q.visibility_mismatches << ','
        << q.producer_semantic_errors << ','
        << q.hit_mismatches << ','
        << q.traversal_runtime_errors << ','
        << q.missing_probes << ','
        << q.leaked_probes << ','
        << q.stale_storage_slots << ','
        << q.resolved_output_mismatches << ','
        << q.radiance_rms_error << ','
        << q.radiance_max_abs_error << ','
        << q.temporal_rms_error << ','
        << q.temporal_max_abs_error << ','
        << s.storage_failures << ','
        << s.overflow << ','
        << s.work_items << ','
        << s.outputs << ','
        << s.moved_primitives << ','
        << s.dynamic_groups << ','
        << s.deformed_primitives << ','
        << s.topology_replaced_primitives << ','
        << m.runtime_resident_bytes << ','
        << m.setup_peak_bytes << ','
        << m.peak_resident_bytes << ','
        << t.complete_gpu_us << ','
        << t.dynamic_update_wall_us << '\n';
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto cli = parse_cli(argc, argv);
        integration::I001Runtime runtime(cli.options);
        std::cout << "GPU: " << runtime.device_name() << '\n';

        auto warmup = runtime.run_frame(false);
        warmup.quality = runtime.validate_last_frame();
        if (!warmup.quality.passed ||
            warmup.stats.storage_failures != 0U ||
            warmup.stats.overflow != 0U) {
            std::cerr << "G004 warmup correctness failed\n";
            return 2;
        }

        auto result = runtime.run_frame(true);
        result.quality = runtime.validate_last_frame();
        if (!result.quality.passed ||
            result.stats.storage_failures != 0U ||
            result.stats.overflow != 0U) {
            std::cerr << "G004 measured correctness failed\n";
            return 2;
        }

        const auto root = artifact_root();
        std::filesystem::create_directories(root);
        write_frame(root / "g004-frame.csv", cli, runtime, result);
        write_device(root / "g004-device.json", cli, runtime);

        std::cerr << "G004 correctness/quality: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "G004 error: " << error.what() << '\n';
        return 1;
    }
}

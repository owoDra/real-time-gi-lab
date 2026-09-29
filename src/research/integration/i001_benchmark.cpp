#include "i001_runtime.hpp"

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
    bool quality{true};
};

Cli parse_cli(int argc, char** argv) {
    Cli cli;
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
        } else if (argument == "--scenario") {
            cli.options.scenario = integration::i001_parse_scenario(value("--scenario"));
        } else if (argument == "--bounded-owner-capacity") {
            cli.options.bounded_owner_capacity =
                static_cast<std::uint32_t>(std::stoul(value("--bounded-owner-capacity")));
        } else if (argument == "--validation") {
            cli.options.validation = true;
        } else if (argument == "--no-quality") {
            cli.quality = false;
        } else if (argument == "--help") {
            std::cout
                << "phos-i001 [--scene path] "
                   "[--variant vanilla-software|combined-hwrt|combined-software|depth-reuse-hwrt|bounded-hwrt] "
                   "[--scenario static|camera-motion|light-motion|moving-rigid|sparse-stress|dense-stress|large-world-stress|vertical-world-stress] "
                   "[--bounded-owner-capacity N] [--validation] [--no-quality]\n";
            std::exit(0);
        } else {
            throw std::runtime_error("unknown I001 argument: " + argument);
        }
    }
    return cli;
}

std::filesystem::path artifact_root() {
    if (const char* value = std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");
        value != nullptr && *value != '\0') {
        return value;
    }
    return "out/research/integration-gate/001-dynamic-end-to-end/manual";
}

void write_csv(
    std::ostream& output,
    const Cli& cli,
    const integration::I001Runtime& runtime,
    const integration::I001FrameResult& result) {
    output
        << "variant,scenario,device,validation,bounded_owner_capacity,"
           "renderer_depth_us,frame_init_us,visibility_reuse_us,"
           "producer_us,ray_prepare_us,traversal_maintenance_gpu_us,dynamic_update_wall_us,"
           "traversal_us,radiance_us,"
           "merge_us,storage_update_us,invalidation_us,resolve_us,"
           "complete_gpu_us,incremental_gi_us,"
           "work_items,outputs,requested_work_items,requested_outputs,"
           "overflow,visible_owners,storage_allocations,storage_updates,"
           "storage_invalidations,storage_failures,"
           "persistent_bytes,transient_bytes,scratch_bytes,peak_resident_bytes,"
           "stream_capacity_bytes,storage_capacity_bytes,"
           "visibility_mismatches,producer_semantic_errors,"
           "hit_mismatches,traversal_runtime_errors,missing_probes,leaked_probes,"
           "stale_storage_slots,resolved_output_mismatches,"
           "radiance_rms_error,radiance_max_abs_error,quality_passed\n";

    output << std::fixed << std::setprecision(6)
        << integration::i001_variant_name(cli.options.variant) << ','
        << integration::i001_scenario_name(cli.options.scenario) << ','
        << '"' << runtime.device_name() << '"' << ','
        << (cli.options.validation ? 1 : 0) << ','
        << cli.options.bounded_owner_capacity << ','
        << result.timings.renderer_depth_us << ','
        << result.timings.frame_init_us << ','
        << result.timings.visibility_reuse_us << ','
        << result.timings.producer_us << ','
        << result.timings.ray_prepare_us << ','
        << result.timings.traversal_maintenance_gpu_us << ','
        << result.timings.dynamic_update_wall_us << ','
        << result.timings.traversal_us << ','
        << result.timings.radiance_us << ','
        << result.timings.merge_us << ','
        << result.timings.storage_update_us << ','
        << result.timings.invalidation_us << ','
        << result.timings.resolve_us << ','
        << result.timings.complete_gpu_us << ','
        << result.timings.incremental_gi_us << ','
        << result.stats.work_items << ','
        << result.stats.outputs << ','
        << result.stats.requested_work_items << ','
        << result.stats.requested_outputs << ','
        << result.stats.overflow << ','
        << result.stats.visible_owners << ','
        << result.stats.storage_allocations << ','
        << result.stats.storage_updates << ','
        << result.stats.storage_invalidations << ','
        << result.stats.storage_failures << ','
        << result.memory.persistent_bytes << ','
        << result.memory.transient_bytes << ','
        << result.memory.scratch_bytes << ','
        << result.memory.peak_resident_bytes << ','
        << result.memory.stream_capacity_bytes << ','
        << result.memory.storage_capacity_bytes << ','
        << result.quality.visibility_mismatches << ','
        << result.quality.producer_semantic_errors << ','
        << result.quality.hit_mismatches << ','
        << result.quality.traversal_runtime_errors << ','
        << result.quality.missing_probes << ','
        << result.quality.leaked_probes << ','
        << result.quality.stale_storage_slots << ','
        << result.quality.resolved_output_mismatches << ','
        << result.quality.radiance_rms_error << ','
        << result.quality.radiance_max_abs_error << ','
        << (result.quality.passed ? 1 : 0) << '\n';
}

void write_metadata(
    const std::filesystem::path& path,
    const Cli& cli,
    const integration::I001Runtime& runtime,
    const integration::I001FrameResult& result) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot create I001 metadata");
    output << std::fixed << std::setprecision(6)
        << "{\n"
        << "  \"variant\": \"" << integration::i001_variant_name(cli.options.variant) << "\",\n"
        << "  \"scenario\": \"" << integration::i001_scenario_name(cli.options.scenario) << "\",\n"
        << "  \"device\": \"" << runtime.device_name() << "\",\n"
        << "  \"driver_name\": \"" << runtime.driver_name() << "\",\n"
        << "  \"driver_info\": \"" << runtime.driver_info() << "\",\n"
        << "  \"api_version\": " << runtime.api_version() << ",\n"
        << "  \"validation\": " << (cli.options.validation ? "true" : "false") << ",\n"
        << "  \"bounded_owner_capacity\": "
        << cli.options.bounded_owner_capacity << ",\n"
        << "  \"quality_passed\": " << (result.quality.passed ? "true" : "false") << ",\n"
        << "  \"overflow\": " << result.stats.overflow << ",\n"
        << "  \"traversal_maintenance_gpu_us\": "
        << result.timings.traversal_maintenance_gpu_us << ",\n"
        << "  \"dynamic_update_wall_us\": "
        << result.timings.dynamic_update_wall_us << ",\n"
        << "  \"complete_gpu_us\": " << result.timings.complete_gpu_us << "\n"
        << "}\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto cli = parse_cli(argc, argv);
        integration::I001Runtime runtime(cli.options);
        std::cout << "GPU: " << runtime.device_name() << '\n';

        (void)runtime.run_frame(false);
        auto result = runtime.run_frame(true);
        if (cli.quality) {
            result.quality = runtime.validate_last_frame();
        } else {
            result.quality.passed = true;
        }

        const auto root = artifact_root();
        std::filesystem::create_directories(root);
        {
            std::ofstream csv(root / "i001-frame.csv");
            if (!csv) throw std::runtime_error("cannot create I001 CSV artifact");
            write_csv(csv, cli, runtime, result);
        }
        write_metadata(root / "i001-device.json", cli, runtime, result);
        write_csv(std::cout, cli, runtime, result);

        if (!result.quality.passed) {
            std::cerr << "I001 correctness/quality gate failed\n";
            return 2;
        }
        if (result.stats.storage_failures != 0U) {
            std::cerr << "I001 storage probe failures: "
                      << result.stats.storage_failures << '\n';
            return 3;
        }
        std::cerr << "I001 correctness/quality: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "I001 error: " << error.what() << '\n';
        return 1;
    }
}

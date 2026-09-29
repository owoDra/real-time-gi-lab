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
    cli.options.variant = integration::I001Variant::TransientLbvh;
    cli.options.scenario = integration::I001Scenario::Static;
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
            if (cli.options.variant != integration::I001Variant::TransientLbvh &&
                cli.options.variant != integration::I001Variant::VanillaSoftware &&
                cli.options.variant != integration::I001Variant::CombinedHwrt &&
                cli.options.variant != integration::I001Variant::CombinedSoftware) {
                throw std::runtime_error("G001 variant is outside the frozen memory census");
            }
        } else if (argument == "--scenario") {
            cli.options.scenario = integration::i001_parse_scenario(value("--scenario"));
            if (cli.options.scenario != integration::I001Scenario::Static &&
                cli.options.scenario != integration::I001Scenario::MovingRigid &&
                cli.options.scenario != integration::I001Scenario::SparseStress &&
                cli.options.scenario != integration::I001Scenario::SparseMovingStress &&
                cli.options.scenario != integration::I001Scenario::DenseMovingStress) {
                throw std::runtime_error("G001 scenario is outside the frozen memory census");
            }
        } else if (argument == "--validation") {
            cli.options.validation = true;
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-g-g001 [--scene path] "
                   "[--variant transient-lbvh|vanilla-software|combined-hwrt|combined-software] "
                   "[--scenario static|moving-rigid|sparse-stress|sparse-moving|dense-moving] "
                   "[--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error("unknown G001 argument: " + argument);
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
           "001-memory-ownership-lifetime-census/manual";
}

void write_device(
    const std::filesystem::path& path,
    const Cli& cli,
    const integration::I001Runtime& runtime) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot create G001 device metadata");
    out
        << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"plan_version\": \"lane-g-g001-v1\",\n"
        << "  \"variant\": \"" << integration::i001_variant_name(cli.options.variant) << "\",\n"
        << "  \"scenario\": \"" << integration::i001_scenario_name(cli.options.scenario) << "\",\n"
        << "  \"device\": \"" << runtime.device_name() << "\",\n"
        << "  \"driver_name\": \"" << runtime.driver_name() << "\",\n"
        << "  \"driver_info\": \"" << runtime.driver_info() << "\",\n"
        << "  \"api_version\": " << runtime.api_version() << ",\n"
        << "  \"validation\": " << (cli.options.validation ? "true" : "false") << "\n"
        << "}\n";
}

void write_frame(
    const std::filesystem::path& path,
    const Cli& cli,
    const integration::I001Runtime& runtime,
    const integration::I001FrameResult& result) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot create G001 frame CSV");
    const auto& m = result.memory;
    out
        << "variant,scenario,device,quality_passed,storage_failures,"
           "persistent_bytes,transient_bytes,scratch_bytes,peak_resident_bytes,"
           "stream_capacity_bytes,storage_capacity_bytes,shared_persistent_bytes,"
           "static_hwrt_persistent_bytes,dynamic_candidate_persistent_bytes,"
           "dynamic_candidate_transient_bytes,dynamic_candidate_scratch_bytes,"
           "current_frame_geometry_bytes,host_persistent_bytes,host_transient_bytes\n";
    out
        << integration::i001_variant_name(cli.options.variant) << ','
        << integration::i001_scenario_name(cli.options.scenario) << ','
        << '"' << runtime.device_name() << '"' << ','
        << (result.quality.passed ? 1 : 0) << ','
        << result.stats.storage_failures << ','
        << m.persistent_bytes << ','
        << m.transient_bytes << ','
        << m.scratch_bytes << ','
        << m.peak_resident_bytes << ','
        << m.stream_capacity_bytes << ','
        << m.storage_capacity_bytes << ','
        << m.shared_persistent_bytes << ','
        << m.static_hwrt_persistent_bytes << ','
        << m.dynamic_candidate_persistent_bytes << ','
        << m.dynamic_candidate_transient_bytes << ','
        << m.dynamic_candidate_scratch_bytes << ','
        << m.current_frame_geometry_bytes << ','
        << m.host_persistent_bytes << ','
        << m.host_transient_bytes << '\n';
}

void write_allocations(
    const std::filesystem::path& path,
    const Cli& cli,
    const integration::I001Runtime& runtime) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot create G001 allocation CSV");
    out
        << "variant,scenario,name,owner,role,capacity_kind,"
           "allocation_lifetime,use_lifetime,logical_bytes,allocation_bytes,"
           "logical_size_known,vulkan_allocation,counted_in_f007_peak\n";
    for (const auto& row : runtime.allocation_census()) {
        out
            << integration::i001_variant_name(cli.options.variant) << ','
            << integration::i001_scenario_name(cli.options.scenario) << ','
            << row.name << ','
            << row.owner << ','
            << row.role << ','
            << row.capacity_kind << ','
            << row.allocation_lifetime << ','
            << row.use_lifetime << ','
            << row.logical_bytes << ','
            << row.allocation_bytes << ','
            << (row.logical_size_known ? 1 : 0) << ','
            << (row.vulkan_allocation ? 1 : 0) << ','
            << (row.counted_in_f007_peak ? 1 : 0) << '\n';
    }
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto cli = parse_cli(argc, argv);
        integration::I001Runtime runtime(cli.options);
        std::cout << "GPU: " << runtime.device_name() << '\n';

        auto warmup = runtime.run_frame(false);
        warmup.quality = runtime.validate_last_frame();
        if (!warmup.quality.passed || warmup.stats.storage_failures != 0U) {
            std::cerr << "G001 warmup correctness failed\n";
            return 2;
        }

        auto result = runtime.run_frame(true);
        result.quality = runtime.validate_last_frame();
        if (!result.quality.passed || result.stats.storage_failures != 0U) {
            std::cerr << "G001 measured correctness failed\n";
            return 2;
        }

        const auto root = artifact_root();
        std::filesystem::create_directories(root);
        write_frame(root / "g001-frame.csv", cli, runtime, result);
        write_allocations(root / "g001-allocations.csv", cli, runtime);
        write_device(root / "g001-device.json", cli, runtime);

        std::cerr << "G001 correctness/quality: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "G001 error: " << error.what() << '\n';
        return 1;
    }
}

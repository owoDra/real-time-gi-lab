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

bool allowed_variant(integration::I001Variant value) {
    using V = integration::I001Variant;
    return value == V::TransientLbvh ||
           value == V::HardenedTransientLbvh ||
           value == V::VanillaSoftware ||
           value == V::CombinedHwrt ||
           value == V::CombinedSoftware;
}

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
        } else if (argument == "--variant") {
            cli.options.variant =
                integration::i001_parse_variant(value("--variant"));
            if (!allowed_variant(cli.options.variant)) {
                throw std::runtime_error("G005 variant outside frozen set");
            }
        } else if (argument == "--scenario") {
            cli.options.scenario =
                integration::i001_parse_scenario(value("--scenario"));
        } else if (argument == "--validation") {
            cli.options.validation = true;
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-g-g005 [--scene path] [--variant name] "
                   "[--scenario name] [--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error("unknown G005 argument: " + argument);
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
           "005-final-deterministic-replay/manual";
}

void write_device(
    const std::filesystem::path& path,
    const Cli& cli,
    const integration::I001Runtime& runtime) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot create G005 device metadata");
    out
        << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"plan_version\": \"lane-g-g005-deterministic-v1\",\n"
        << "  \"variant\": \""
        << integration::i001_variant_name(cli.options.variant) << "\",\n"
        << "  \"scenario\": \""
        << integration::i001_scenario_name(cli.options.scenario) << "\",\n"
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
    if (!out) throw std::runtime_error("cannot create G005 frame CSV");

    const auto& q = result.quality;
    const auto& s = result.stats;
    const auto& m = result.memory;
    const auto& t = result.timings;

    out
        << "variant,scenario,device,quality_passed,"
           "visibility_mismatches,producer_semantic_errors,hit_mismatches,"
           "traversal_runtime_errors,missing_probes,leaked_probes,"
           "stale_storage_slots,resolved_output_mismatches,"
           "storage_failures,overflow,work_items,outputs,"
           "requested_work_items,requested_outputs,visible_owners,"
           "moved_primitives,segment_membership_changes,dynamic_groups,"
           "runtime_resident_bytes,setup_peak_bytes,peak_resident_bytes,"
           "persistent_bytes,transient_bytes,scratch_bytes,"
           "complete_gpu_us,dynamic_update_wall_us\n";

    out
        << integration::i001_variant_name(cli.options.variant) << ','
        << integration::i001_scenario_name(cli.options.scenario) << ','
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
        << s.storage_failures << ','
        << s.overflow << ','
        << s.work_items << ','
        << s.outputs << ','
        << s.requested_work_items << ','
        << s.requested_outputs << ','
        << s.visible_owners << ','
        << s.moved_primitives << ','
        << s.segment_membership_changes << ','
        << s.dynamic_groups << ','
        << m.runtime_resident_bytes << ','
        << m.setup_peak_bytes << ','
        << m.peak_resident_bytes << ','
        << m.persistent_bytes << ','
        << m.transient_bytes << ','
        << m.scratch_bytes << ','
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
            std::cerr << "G005 warmup correctness failed\n";
            return 2;
        }

        auto result = runtime.run_frame(true);
        result.quality = runtime.validate_last_frame();
        if (!result.quality.passed ||
            result.stats.storage_failures != 0U ||
            result.stats.overflow != 0U) {
            std::cerr << "G005 measured correctness failed\n";
            return 2;
        }

        const auto root = artifact_root();
        std::filesystem::create_directories(root);
        write_frame(root / "g005-frame.csv", cli, runtime, result);
        write_device(root / "g005-device.json", cli, runtime);

        std::cerr << "G005 correctness/quality: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "G005 error: " << error.what() << '\n';
        return 1;
    }
}

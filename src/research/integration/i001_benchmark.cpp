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
                   "[--variant vanilla-software|combined-hwrt|rigid-instance-hwrt-update|rigid-instance-hwrt-build|rigid-instance-software-binary|rigid-instance-software-quantized|deforming-local-hwrt|deforming-local-software-quantized|combined-software|depth-reuse-hwrt|bounded-hwrt] "
                   "[--scenario static|camera-motion|light-motion|moving-rigid|deforming-control|sparse-stress|dense-stress|large-world-stress|vertical-world-stress] "
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


void print_quality_diagnostics(
    const char* phase,
    const integration::I001FrameResult& result) {
    const auto& q = result.quality;
    std::cerr
        << "I001 quality diagnostics [" << phase << "]: "
        << "visibility_mismatches=" << q.visibility_mismatches
        << ", producer_semantic_errors=" << q.producer_semantic_errors
        << ", hit_mismatches=" << q.hit_mismatches
        << ", traversal_runtime_errors=" << q.traversal_runtime_errors
        << ", missing_probes=" << q.missing_probes
        << ", leaked_probes=" << q.leaked_probes
        << ", stale_storage_slots=" << q.stale_storage_slots
        << ", resolved_output_mismatches=" << q.resolved_output_mismatches
        << ", radiance_rms_error=" << q.radiance_rms_error
        << ", radiance_max_abs_error=" << q.radiance_max_abs_error
        << ", temporal_rms_error=" << q.temporal_rms_error
        << ", temporal_max_abs_error=" << q.temporal_max_abs_error
        << ", storage_failures=" << result.stats.storage_failures
        << ", work_items=" << result.stats.work_items
        << ", outputs=" << result.stats.outputs
        << ", requested_work_items=" << result.stats.requested_work_items
        << ", requested_outputs=" << result.stats.requested_outputs
        << ", overflow=" << result.stats.overflow
        << '\n';
}

void write_csv(
    std::ostream& output,
    const Cli& cli,
    const integration::I001Runtime& runtime,
    const integration::I001FrameResult& result,
    double setup_wall_us) {
    output
        << "variant,scenario,device,validation,bounded_owner_capacity,"
           "warmup_frames,measured_frames,setup_wall_us,"
           "renderer_depth_us,frame_init_us,visibility_reuse_us,"
           "producer_us,ray_prepare_us,traversal_maintenance_gpu_us,dynamic_update_wall_us,"
           "geometry_prepare_cpu_us,surface_update_gpu_us,"
           "geometry_transfer_wall_us,geometry_transfer_gpu_us,"
           "instance_transfer_wall_us,instance_transfer_gpu_us,"
           "blas_update_us,tlas_update_us,membership_update_cpu_us,"
           "hierarchy_refit_cpu_us,hierarchy_rebuild_cpu_us,hierarchy_occupancy_cpu_us,"
           "packing_cpu_us,hierarchy_upload_gpu_us,software_bvh_rebuild_cpu_us,"
           "traversal_us,radiance_us,"
           "merge_us,storage_update_us,invalidation_us,resolve_us,"
           "complete_gpu_us,incremental_gi_us,"
           "work_items,outputs,requested_work_items,requested_outputs,"
           "overflow,visible_owners,moved_primitives,segment_membership_changes,"
           "hierarchy_refit_segments,hierarchy_rebuilt_segments,"
           "storage_allocations,storage_updates,"
           "storage_invalidations,storage_failures,"
           "persistent_bytes,transient_bytes,scratch_bytes,peak_resident_bytes,"
           "stream_capacity_bytes,storage_capacity_bytes,"
           "visibility_mismatches,producer_semantic_errors,"
           "hit_mismatches,traversal_runtime_errors,missing_probes,leaked_probes,"
           "stale_storage_slots,resolved_output_mismatches,"
           "radiance_rms_error,radiance_max_abs_error,"
           "temporal_rms_error,temporal_max_abs_error,quality_passed\n";

    output << std::fixed << std::setprecision(6)
        << integration::i001_variant_name(cli.options.variant) << ','
        << integration::i001_scenario_name(cli.options.scenario) << ','
        << '"' << runtime.device_name() << '"' << ','
        << (cli.options.validation ? 1 : 0) << ','
        << cli.options.bounded_owner_capacity << ','
        << 1 << ','
        << 1 << ','
        << setup_wall_us << ','
        << result.timings.renderer_depth_us << ','
        << result.timings.frame_init_us << ','
        << result.timings.visibility_reuse_us << ','
        << result.timings.producer_us << ','
        << result.timings.ray_prepare_us << ','
        << result.timings.traversal_maintenance_gpu_us << ','
        << result.timings.dynamic_update_wall_us << ','
        << result.timings.geometry_prepare_cpu_us << ','
        << result.timings.surface_update_gpu_us << ','
        << result.timings.geometry_transfer_wall_us << ','
        << result.timings.geometry_transfer_gpu_us << ','
        << result.timings.instance_transfer_wall_us << ','
        << result.timings.instance_transfer_gpu_us << ','
        << result.timings.blas_update_us << ','
        << result.timings.tlas_update_us << ','
        << result.timings.membership_update_cpu_us << ','
        << result.timings.hierarchy_refit_cpu_us << ','
        << result.timings.hierarchy_rebuild_cpu_us << ','
        << result.timings.hierarchy_occupancy_cpu_us << ','
        << result.timings.packing_cpu_us << ','
        << result.timings.hierarchy_upload_gpu_us << ','
        << result.timings.software_bvh_rebuild_cpu_us << ','
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
        << result.stats.moved_primitives << ','
        << result.stats.segment_membership_changes << ','
        << result.stats.hierarchy_refit_segments << ','
        << result.stats.hierarchy_rebuilt_segments << ','
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
        << result.quality.temporal_rms_error << ','
        << result.quality.temporal_max_abs_error << ','
        << (result.quality.passed ? 1 : 0) << '\n';
}

void write_metadata(
    const std::filesystem::path& path,
    const Cli& cli,
    const integration::I001Runtime& runtime,
    const integration::I001FrameResult& result,
    double setup_wall_us) {
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
        << "  \"warmup_frames\": 1,\n"
        << "  \"measured_frames\": 1,\n"
        << "  \"setup_wall_us\": " << setup_wall_us << ",\n"
        << "  \"quality_passed\": " << (result.quality.passed ? "true" : "false") << ",\n"
        << "  \"overflow\": " << result.stats.overflow << ",\n"
        << "  \"traversal_maintenance_gpu_us\": "
        << result.timings.traversal_maintenance_gpu_us << ",\n"
        << "  \"dynamic_update_wall_us\": "
        << result.timings.dynamic_update_wall_us << ",\n"
        << "  \"geometry_prepare_cpu_us\": "
        << result.timings.geometry_prepare_cpu_us << ",\n"
        << "  \"surface_update_gpu_us\": "
        << result.timings.surface_update_gpu_us << ",\n"
        << "  \"geometry_transfer_wall_us\": "
        << result.timings.geometry_transfer_wall_us << ",\n"
        << "  \"geometry_transfer_gpu_us\": "
        << result.timings.geometry_transfer_gpu_us << ",\n"
        << "  \"instance_transfer_wall_us\": "
        << result.timings.instance_transfer_wall_us << ",\n"
        << "  \"instance_transfer_gpu_us\": "
        << result.timings.instance_transfer_gpu_us << ",\n"
        << "  \"blas_update_us\": "
        << result.timings.blas_update_us << ",\n"
        << "  \"tlas_update_us\": "
        << result.timings.tlas_update_us << ",\n"
        << "  \"membership_update_cpu_us\": "
        << result.timings.membership_update_cpu_us << ",\n"
        << "  \"hierarchy_refit_cpu_us\": "
        << result.timings.hierarchy_refit_cpu_us << ",\n"
        << "  \"hierarchy_rebuild_cpu_us\": "
        << result.timings.hierarchy_rebuild_cpu_us << ",\n"
        << "  \"hierarchy_occupancy_cpu_us\": "
        << result.timings.hierarchy_occupancy_cpu_us << ",\n"
        << "  \"packing_cpu_us\": "
        << result.timings.packing_cpu_us << ",\n"
        << "  \"hierarchy_upload_gpu_us\": "
        << result.timings.hierarchy_upload_gpu_us << ",\n"
        << "  \"software_bvh_rebuild_cpu_us\": "
        << result.timings.software_bvh_rebuild_cpu_us << ",\n"
        << "  \"complete_gpu_us\": " << result.timings.complete_gpu_us << "\n"
        << "}\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto cli = parse_cli(argc, argv);
        const auto setup_start = std::chrono::steady_clock::now();
        integration::I001Runtime runtime(cli.options);
        const auto setup_wall_us =
            std::chrono::duration<double, std::micro>(
                std::chrono::steady_clock::now() - setup_start).count();
        std::cout << "GPU: " << runtime.device_name() << '\n';

        auto warmup = runtime.run_frame(false);
        if (cli.quality) {
            warmup.quality = runtime.validate_last_frame();
            if (!warmup.quality.passed) {
                print_quality_diagnostics("warmup", warmup);
                std::cerr << "I001 warmup correctness/quality gate failed\n";
                return 2;
            }
        }

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
            write_csv(csv, cli, runtime, result, setup_wall_us);
        }
        write_metadata(
            root / "i001-device.json",
            cli,
            runtime,
            result,
            setup_wall_us);
        write_csv(
            std::cout,
            cli,
            runtime,
            result,
            setup_wall_us);

        if (!result.quality.passed) {
            print_quality_diagnostics("measured", result);
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

#include "../integration/i001_runtime.hpp"

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
};

Cli parse_cli(int argc, char** argv) {
    Cli cli;
    cli.options.variant = integration::I001Variant::TransientLbvh;
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
        } else if (argument == "--validation") {
            cli.options.validation = true;
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-f-f003 [--scene path] "
                   "[--scenario static|camera-motion|light-motion|moving-rigid|"
                   "sparse-stress|dense-stress|large-world-stress|vertical-world-stress] "
                   "[--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error("unknown F003 argument: " + argument);
        }
    }
    return cli;
}

std::filesystem::path artifact_root() {
    if (const char* value = std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");
        value != nullptr && *value != '\0') {
        return value;
    }
    return "out/research/lane-f-dynamic-geometry-alternatives/"
           "003-end-to-end-transient-lbvh/manual-candidate";
}

void print_quality(
    const char* phase,
    const integration::I001FrameResult& result) {
    const auto& q = result.quality;
    std::cerr
        << "F003 quality [" << phase << "]: "
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
        << '\n';
}

void write_csv(
    std::ostream& out,
    const Cli& cli,
    const integration::I001Runtime& runtime,
    const integration::I001FrameResult& result,
    double setup_wall_us,
    double complete_frame_wall_us) {
    out
        << "variant,scenario,device,validation,warmup_frames,measured_frames,"
           "setup_wall_us,complete_frame_wall_us,"
           "renderer_depth_us,frame_init_us,visibility_reuse_us,producer_us,"
           "ray_prepare_us,traversal_maintenance_gpu_us,dynamic_update_wall_us,"
           "dynamic_builder_reset_us,dynamic_builder_input_us,"
           "dynamic_builder_aabb_us,dynamic_builder_morton_us,"
           "dynamic_builder_sort_us,dynamic_builder_topology_us,"
           "dynamic_builder_bounds_us,dynamic_builder_us,"
           "static_traversal_us,dynamic_traversal_us,cross_structure_merge_us,"
           "traversal_us,radiance_us,merge_us,storage_update_us,invalidation_us,"
           "resolve_us,complete_gpu_us,incremental_gi_us,"
           "work_items,outputs,requested_work_items,requested_outputs,overflow,"
           "visible_owners,moved_primitives,segment_membership_changes,"
           "storage_allocations,storage_updates,storage_invalidations,storage_failures,"
           "persistent_bytes,transient_bytes,scratch_bytes,peak_resident_bytes,"
           "stream_capacity_bytes,storage_capacity_bytes,"
           "shared_persistent_bytes,static_hwrt_persistent_bytes,"
           "dynamic_candidate_persistent_bytes,dynamic_candidate_transient_bytes,"
           "dynamic_candidate_scratch_bytes,current_frame_geometry_bytes,"
           "host_persistent_bytes,host_transient_bytes,"
           "visibility_mismatches,producer_semantic_errors,hit_mismatches,"
           "traversal_runtime_errors,missing_probes,leaked_probes,stale_storage_slots,"
           "resolved_output_mismatches,radiance_rms_error,radiance_max_abs_error,"
           "temporal_rms_error,temporal_max_abs_error,quality_passed\n";

    const auto& t = result.timings;
    const auto& m = result.memory;
    const auto& q = result.quality;
    out << std::fixed << std::setprecision(6)
        << integration::i001_variant_name(cli.options.variant) << ','
        << integration::i001_scenario_name(cli.options.scenario) << ','
        << '"' << runtime.device_name() << '"' << ','
        << (cli.options.validation ? 1 : 0) << ','
        << 1 << ',' << 1 << ','
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
        << t.incremental_gi_us << ','
        << result.stats.work_items << ',' << result.stats.outputs << ','
        << result.stats.requested_work_items << ',' << result.stats.requested_outputs << ','
        << result.stats.overflow << ',' << result.stats.visible_owners << ','
        << result.stats.moved_primitives << ','
        << result.stats.segment_membership_changes << ','
        << result.stats.storage_allocations << ',' << result.stats.storage_updates << ','
        << result.stats.storage_invalidations << ',' << result.stats.storage_failures << ','
        << m.persistent_bytes << ',' << m.transient_bytes << ',' << m.scratch_bytes << ','
        << m.peak_resident_bytes << ',' << m.stream_capacity_bytes << ','
        << m.storage_capacity_bytes << ',' << m.shared_persistent_bytes << ','
        << m.static_hwrt_persistent_bytes << ',' << m.dynamic_candidate_persistent_bytes << ','
        << m.dynamic_candidate_transient_bytes << ',' << m.dynamic_candidate_scratch_bytes << ','
        << m.current_frame_geometry_bytes << ',' << m.host_persistent_bytes << ','
        << m.host_transient_bytes << ','
        << q.visibility_mismatches << ',' << q.producer_semantic_errors << ','
        << q.hit_mismatches << ',' << q.traversal_runtime_errors << ','
        << q.missing_probes << ',' << q.leaked_probes << ','
        << q.stale_storage_slots << ',' << q.resolved_output_mismatches << ','
        << q.radiance_rms_error << ',' << q.radiance_max_abs_error << ','
        << q.temporal_rms_error << ',' << q.temporal_max_abs_error << ','
        << (q.passed ? 1 : 0) << '\n';
}

void write_device(
    const std::filesystem::path& path,
    const Cli& cli,
    const integration::I001Runtime& runtime) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot create F003 device metadata");
    out
        << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"plan_version\": \"lane-f-plan-v1\",\n"
        << "  \"variant\": \"transient-lbvh\",\n"
        << "  \"scenario\": \""
        << integration::i001_scenario_name(cli.options.scenario) << "\",\n"
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
        const auto setup_wall_us =
            std::chrono::duration<double, std::micro>(
                std::chrono::steady_clock::now() - setup_start).count();
        std::cout << "GPU: " << runtime.device_name() << '\n';

        auto warmup = runtime.run_frame(false);
        warmup.quality = runtime.validate_last_frame();
        if (!warmup.quality.passed || warmup.stats.storage_failures != 0U) {
            print_quality("warmup", warmup);
            return 2;
        }

        const auto frame_start = std::chrono::steady_clock::now();
        auto result = runtime.run_frame(true);
        const auto complete_frame_wall_us =
            std::chrono::duration<double, std::micro>(
                std::chrono::steady_clock::now() - frame_start).count();
        result.quality = runtime.validate_last_frame();

        const auto root = artifact_root();
        std::filesystem::create_directories(root);
        {
            std::ofstream csv(root / "f003-candidate-frame.csv");
            if (!csv) throw std::runtime_error("cannot create F003 candidate CSV");
            write_csv(csv, cli, runtime, result, setup_wall_us, complete_frame_wall_us);
        }
        write_device(root / "f003-candidate-device.json", cli, runtime);
        write_csv(std::cout, cli, runtime, result, setup_wall_us, complete_frame_wall_us);

        if (!result.quality.passed || result.stats.storage_failures != 0U) {
            print_quality("measured", result);
            return 2;
        }
        std::cerr << "F003 candidate correctness/quality: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "F003 candidate error: " << error.what() << '\n';
        return 1;
    }
}

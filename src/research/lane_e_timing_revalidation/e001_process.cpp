#include "../integration/i001_runtime.hpp"

#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace integration = phos::gi::research::integration;

namespace {

struct Cli {
    std::filesystem::path scene;
    std::filesystem::path output;
    std::string scenario;
    std::string track;
    std::string comparison;
    std::string start_order;
    std::uint32_t block{};
    std::uint32_t warmup_pairs{4};
    std::uint32_t measured_pairs{12};
    std::uint32_t transitions{16};
    std::uint32_t settle_seconds{1};
    bool validation{};
};

[[noreturn]] void fail(const std::string& message) {
    throw std::runtime_error(message);
}

Cli parse_cli(int argc, char** argv) {
    Cli cli;
    auto value = [&](int& index, const char* name) -> std::string {
        if (index + 1 >= argc) fail(std::string("missing value for ") + name);
        return argv[++index];
    };
    for (int index = 1; index < argc; ++index) {
        const std::string arg = argv[index];
        if (arg == "--scene") cli.scene = value(index, "--scene");
        else if (arg == "--output") cli.output = value(index, "--output");
        else if (arg == "--scenario") cli.scenario = value(index, "--scenario");
        else if (arg == "--track") cli.track = value(index, "--track");
        else if (arg == "--comparison") cli.comparison = value(index, "--comparison");
        else if (arg == "--start-order") cli.start_order = value(index, "--start-order");
        else if (arg == "--block") cli.block = std::stoul(value(index, "--block"));
        else if (arg == "--warmup-pairs") cli.warmup_pairs = std::stoul(value(index, "--warmup-pairs"));
        else if (arg == "--measured-pairs") cli.measured_pairs = std::stoul(value(index, "--measured-pairs"));
        else if (arg == "--transitions") cli.transitions = std::stoul(value(index, "--transitions"));
        else if (arg == "--settle-seconds") cli.settle_seconds = std::stoul(value(index, "--settle-seconds"));
        else if (arg == "--validation") cli.validation = true;
        else fail("unknown argument: " + arg);
    }

    if (cli.scene.empty() || cli.output.empty() || cli.scenario.empty() ||
        cli.track.empty() || cli.comparison.empty()) {
        fail("scene/output/scenario/track/comparison are required");
    }
    if (cli.track != "hwrt" && cli.track != "software") {
        fail("track must be hwrt or software");
    }
    if (cli.comparison != "control" && cli.comparison != "candidate") {
        fail("comparison must be control or candidate");
    }
    if (!cli.validation && cli.start_order != "AB" && cli.start_order != "BA") {
        fail("timing requires start-order AB or BA");
    }
    if (!cli.validation &&
        (cli.warmup_pairs != 4 || cli.measured_pairs != 12 ||
         cli.transitions != 16)) {
        fail("accepted timing shape must remain 4+12 pairs and 16 transitions");
    }
    return cli;
}

integration::I001Variant control_variant(const std::string& track) {
    return track == "hwrt"
        ? integration::I001Variant::CombinedHwrt
        : integration::I001Variant::CombinedSoftware;
}

integration::I001Variant candidate_variant(const std::string& track) {
    return track == "hwrt"
        ? integration::I001Variant::LaneEFinalHwrt
        : integration::I001Variant::LaneEFinalSoftware;
}

integration::I001Scenario scenario_value(const std::string& value) {
    if (value == "static") return integration::I001Scenario::Static;
    if (value == "camera-motion") return integration::I001Scenario::CameraMotion;
    if (value == "light-motion") return integration::I001Scenario::LightMotion;
    if (value == "moving-rigid") return integration::I001Scenario::MovingRigid;
    if (value == "stable-topology-deforming")
        return integration::I001Scenario::DeformingControl;
    fail("unsupported E001 scenario: " + value);
}

integration::I001Options options_for(
    const Cli& cli,
    integration::I001Variant variant,
    bool validation) {
    integration::I001Options options;
    options.scene = cli.scene;
    options.variant = variant;
    options.scenario = scenario_value(cli.scenario);
    options.validation = validation;
    return options;
}

std::string csv_string(const std::string& value) {
    std::string out = "\"";
    for (const char ch : value) {
        if (ch == '"') out += "\"\"";
        else out += ch;
    }
    out += '"';
    return out;
}

struct Batch {
    double complete_gpu_us{};
    double complete_wall_us{};
    double geometry_prepare_cpu_us{};
    double dynamic_update_wall_us{};
    double surface_update_gpu_us{};
    double geometry_transfer_gpu_us{};
    double instance_transfer_gpu_us{};
    double blas_update_us{};
    double tlas_update_us{};
    double membership_update_cpu_us{};
    double hierarchy_refit_cpu_us{};
    double hierarchy_rebuild_cpu_us{};
    double packing_cpu_us{};
    double hierarchy_upload_gpu_us{};
    double software_bvh_rebuild_cpu_us{};
    double traversal_us{};
    double merge_us{};
    double storage_update_us{};
    double invalidation_us{};
    double resolve_us{};
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t scratch_bytes{};
    std::size_t true_peak_bytes{};
    std::size_t old_new_overlap_bytes{};
    std::size_t allocation_count{};
    std::size_t free_count{};
    std::size_t live_allocations{};
    bool allocation_lifetime_complete{};
};

Batch run_batch(integration::I001Runtime& runtime, std::uint32_t transitions) {
    runtime.reset_allocation_epoch();
    const auto before = runtime.allocation_stats();
    Batch out;
    const auto start = std::chrono::steady_clock::now();
    integration::I001FrameResult last{};
    for (std::uint32_t index = 0; index < transitions; ++index) {
        const bool target = (index % 2U) == 0U;
        const auto result = runtime.run_frame(target);
        last = result;
        out.complete_gpu_us += result.timings.complete_gpu_us;
        out.geometry_prepare_cpu_us += result.timings.geometry_prepare_cpu_us;
        out.dynamic_update_wall_us += result.timings.dynamic_update_wall_us;
        out.surface_update_gpu_us += result.timings.surface_update_gpu_us;
        out.geometry_transfer_gpu_us += result.timings.geometry_transfer_gpu_us;
        out.instance_transfer_gpu_us += result.timings.instance_transfer_gpu_us;
        out.blas_update_us += result.timings.blas_update_us;
        out.tlas_update_us += result.timings.tlas_update_us;
        out.membership_update_cpu_us += result.timings.membership_update_cpu_us;
        out.hierarchy_refit_cpu_us += result.timings.hierarchy_refit_cpu_us;
        out.hierarchy_rebuild_cpu_us += result.timings.hierarchy_rebuild_cpu_us;
        out.packing_cpu_us += result.timings.packing_cpu_us;
        out.hierarchy_upload_gpu_us += result.timings.hierarchy_upload_gpu_us;
        out.software_bvh_rebuild_cpu_us += result.timings.software_bvh_rebuild_cpu_us;
        out.traversal_us += result.timings.traversal_us;
        out.merge_us += result.timings.merge_us;
        out.storage_update_us += result.timings.storage_update_us;
        out.invalidation_us += result.timings.invalidation_us;
        out.resolve_us += result.timings.resolve_us;
        out.old_new_overlap_bytes = std::max(
            out.old_new_overlap_bytes,
            result.memory.old_new_overlap_bytes);
    }
    out.complete_wall_us =
        std::chrono::duration<double, std::micro>(
            std::chrono::steady_clock::now() - start).count();

    const auto after = runtime.allocation_stats();
    out.persistent_bytes = last.memory.persistent_bytes;
    out.transient_bytes = last.memory.transient_bytes;
    out.scratch_bytes = last.memory.scratch_bytes;
    out.true_peak_bytes = after.peak_bytes;
    out.allocation_count = after.allocation_count;
    out.free_count = after.free_count;
    out.live_allocations = after.live_allocations;
    out.allocation_lifetime_complete =
        after.allocation_count == after.free_count &&
        after.live_allocations == before.live_allocations;
    return out;
}

void write_timing_header(std::ofstream& output) {
    output
        << "phase,pair_index,role,order,block,scenario,track,comparison,"
        << "gpu_us,wall_us,geometry_prepare_cpu_us,dynamic_update_wall_us,"
        << "surface_update_gpu_us,geometry_transfer_gpu_us,instance_transfer_gpu_us,"
        << "blas_update_us,tlas_update_us,membership_update_cpu_us,"
        << "hierarchy_refit_cpu_us,hierarchy_rebuild_cpu_us,packing_cpu_us,"
        << "hierarchy_upload_gpu_us,software_bvh_rebuild_cpu_us,traversal_us,"
        << "merge_us,storage_update_us,invalidation_us,resolve_us,"
        << "persistent_bytes,transient_bytes,scratch_bytes,old_new_overlap_bytes,"
        << "true_peak_bytes,allocation_count,free_count,live_allocations,"
        << "allocation_lifetime_complete,"
        << "device_name,driver_name,driver_info,api_version,timestamp_period_ns\n";
}

void write_timing_row(
    std::ofstream& output,
    const Cli& cli,
    const char* phase,
    std::uint32_t pair,
    const char* role,
    const std::string& order,
    const Batch& batch,
    const integration::I001Runtime& runtime) {
    output
        << phase << ',' << pair << ',' << role << ',' << order << ','
        << cli.block << ',' << cli.scenario << ',' << cli.track << ','
        << cli.comparison << ','
        << std::setprecision(17)
        << batch.complete_gpu_us << ',' << batch.complete_wall_us << ','
        << batch.geometry_prepare_cpu_us << ',' << batch.dynamic_update_wall_us << ','
        << batch.surface_update_gpu_us << ',' << batch.geometry_transfer_gpu_us << ','
        << batch.instance_transfer_gpu_us << ',' << batch.blas_update_us << ','
        << batch.tlas_update_us << ',' << batch.membership_update_cpu_us << ','
        << batch.hierarchy_refit_cpu_us << ',' << batch.hierarchy_rebuild_cpu_us << ','
        << batch.packing_cpu_us << ',' << batch.hierarchy_upload_gpu_us << ','
        << batch.software_bvh_rebuild_cpu_us << ',' << batch.traversal_us << ','
        << batch.merge_us << ',' << batch.storage_update_us << ','
        << batch.invalidation_us << ',' << batch.resolve_us << ','
        << batch.persistent_bytes << ',' << batch.transient_bytes << ','
        << batch.scratch_bytes << ',' << batch.old_new_overlap_bytes << ','
        << batch.true_peak_bytes << ',' << batch.allocation_count << ','
        << batch.free_count << ',' << batch.live_allocations << ','
        << (batch.allocation_lifetime_complete ? 1 : 0) << ','
        << csv_string(runtime.device_name()) << ','
        << csv_string(runtime.driver_name()) << ','
        << csv_string(runtime.driver_info()) << ','
        << runtime.api_version() << ','
        << runtime.timestamp_period_ns() << '\n';
}

void write_validation_header(std::ofstream& output) {
    output
        << "role,state,scenario,track,comparison,quality_passed,"
        << "hit_mismatch,nearest_hit_tie_mismatch,visibility_mismatch,"
        << "producer_semantic_error,traversal_runtime_error,storage_failure,"
        << "static_owner_mutation,unrelated_owner_mutation,"
        << "workload_digest,resolved_output_digest,geometry_input_digest,"
        << "persistent_bytes,transient_bytes,scratch_bytes,old_new_overlap_bytes,"
        << "current_bytes,true_peak_bytes,allocation_count,free_count,live_allocations,"
        << "allocation_lifetime_complete,"
        << "device_name,driver_name,driver_info,api_version,timestamp_period_ns\n";
}

void write_validation_row(
    std::ofstream& output,
    const Cli& cli,
    const char* role,
    const char* state,
    const integration::I001FrameResult& result,
    const integration::I001Quality& quality,
    const integration::I001AllocationStats& allocations,
    bool allocation_lifetime_complete,
    const integration::I001Runtime& runtime) {
    output
        << role << ',' << state << ',' << cli.scenario << ',' << cli.track << ','
        << cli.comparison << ',' << (quality.passed ? 1 : 0) << ','
        << quality.hit_mismatches << ',' << quality.nearest_hit_tie_mismatches << ','
        << quality.visibility_mismatches << ',' << quality.producer_semantic_errors << ','
        << quality.traversal_runtime_errors << ',' << result.stats.storage_failures << ','
        << quality.static_owner_mutations << ',' << quality.unrelated_owner_mutations << ','
        << quality.workload_digest << ',' << quality.resolved_output_digest << ','
        << quality.geometry_input_digest << ','
        << result.memory.persistent_bytes << ',' << result.memory.transient_bytes << ','
        << result.memory.scratch_bytes << ',' << result.memory.old_new_overlap_bytes << ','
        << allocations.current_bytes << ',' << allocations.peak_bytes << ','
        << allocations.allocation_count << ',' << allocations.free_count << ','
        << allocations.live_allocations << ','
        << (allocation_lifetime_complete ? 1 : 0) << ','
        << csv_string(runtime.device_name()) << ','
        << csv_string(runtime.driver_name()) << ','
        << csv_string(runtime.driver_info()) << ','
        << runtime.api_version() << ',' << runtime.timestamp_period_ns() << '\n';
}

int run_validation(const Cli& cli) {
    const auto control = control_variant(cli.track);
    const auto b_variant =
        cli.comparison == "control" ? control : candidate_variant(cli.track);

    integration::I001Runtime runtime_a(options_for(cli, control, true));
    integration::I001Runtime runtime_b(options_for(cli, b_variant, true));

    std::ofstream output(cli.output);
    if (!output) fail("cannot create validation output");
    write_validation_header(output);

    for (const auto [state_name, target] :
         std::vector<std::pair<const char*, bool>>{{"target", true}, {"base", false}}) {
        runtime_a.reset_allocation_epoch();
        const auto before_a = runtime_a.allocation_stats();
        const auto frame_a = runtime_a.run_frame(target);
        const auto allocations_a = runtime_a.allocation_stats();
        const bool lifetime_a =
            allocations_a.allocation_count == allocations_a.free_count &&
            allocations_a.live_allocations == before_a.live_allocations;
        const auto quality_a = runtime_a.validate_last_frame();

        runtime_b.reset_allocation_epoch();
        const auto before_b = runtime_b.allocation_stats();
        const auto frame_b = runtime_b.run_frame(target);
        const auto allocations_b = runtime_b.allocation_stats();
        const bool lifetime_b =
            allocations_b.allocation_count == allocations_b.free_count &&
            allocations_b.live_allocations == before_b.live_allocations;
        const auto quality_b = runtime_b.validate_last_frame();

        write_validation_row(
            output, cli, "A", state_name, frame_a, quality_a,
            allocations_a, lifetime_a, runtime_a);
        write_validation_row(
            output, cli, "B", state_name, frame_b, quality_b,
            allocations_b, lifetime_b, runtime_b);

        if (!lifetime_a || !lifetime_b ||
            !quality_a.passed || !quality_b.passed ||
            quality_a.workload_digest != quality_b.workload_digest ||
            quality_a.resolved_output_digest != quality_b.resolved_output_digest ||
            quality_a.geometry_input_digest != quality_b.geometry_input_digest) {
            fail("E001 validation identity/correctness gate failed");
        }
        if (runtime_a.device_name() != runtime_b.device_name() ||
            runtime_a.driver_name() != runtime_b.driver_name() ||
            runtime_a.driver_info() != runtime_b.driver_info() ||
            runtime_a.api_version() != runtime_b.api_version() ||
            runtime_a.timestamp_period_ns() != runtime_b.timestamp_period_ns()) {
            fail("E001 validation provenance mismatch");
        }
    }
    return 0;
}

int run_timing(const Cli& cli) {
    const auto control = control_variant(cli.track);
    const auto b_variant =
        cli.comparison == "control" ? control : candidate_variant(cli.track);

    integration::I001Runtime runtime_a(options_for(cli, control, false));
    integration::I001Runtime runtime_b(options_for(cli, b_variant, false));

    if (runtime_a.device_name() != runtime_b.device_name() ||
        runtime_a.driver_name() != runtime_b.driver_name() ||
        runtime_a.driver_info() != runtime_b.driver_info() ||
        runtime_a.api_version() != runtime_b.api_version() ||
        runtime_a.timestamp_period_ns() != runtime_b.timestamp_period_ns()) {
        fail("E001 timing provenance mismatch");
    }

    std::this_thread::sleep_for(std::chrono::seconds(cli.settle_seconds));

    std::ofstream output(cli.output);
    if (!output) fail("cannot create timing output");
    write_timing_header(output);

    const auto total_pairs = cli.warmup_pairs + cli.measured_pairs;
    for (std::uint32_t pair = 0; pair < total_pairs; ++pair) {
        const bool start_ab = cli.start_order == "AB";
        const bool ab = (pair % 2U) == 0U ? start_ab : !start_ab;
        const std::string order = ab ? "AB" : "BA";
        const char* phase = pair < cli.warmup_pairs ? "warmup" : "measured";

        auto run_role = [&](const char* role) {
            if (std::string(role) == "A") {
                const auto batch = run_batch(runtime_a, cli.transitions);
                write_timing_row(output, cli, phase, pair, role, order, batch, runtime_a);
            } else {
                const auto batch = run_batch(runtime_b, cli.transitions);
                write_timing_row(output, cli, phase, pair, role, order, batch, runtime_b);
            }
        };

        if (ab) {
            run_role("A");
            run_role("B");
        } else {
            run_role("B");
            run_role("A");
        }
        output.flush();
    }
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto cli = parse_cli(argc, argv);
        if (cli.validation) return run_validation(cli);
        return run_timing(cli);
    } catch (const std::exception& error) {
        std::cerr << "E001 error: " << error.what() << '\n';
        return 1;
    }
}

// L001 reuses the frozen J004 runtime implementation directly so the heavy
// recurring boundary, B001 tie semantics, and control-family work cannot drift.
#define main phos_lane_j_j004_embedded_main
#include "../lane_j_topology_backend_alternatives/formal_runtime/j004_formal_process.cpp"
#undef main

namespace {

enum class L001Environment {
    DualContext,
    SingleContextIndependentRuntime,
};

struct L001Args {
    L001Environment environment{L001Environment::DualContext};
    std::vector<char*> forwarded;
};

[[nodiscard]] const char* environment_name(
    L001Environment environment) noexcept {
    return environment == L001Environment::DualContext
        ? "dual-context"
        : "single-context-independent-runtime";
}

[[nodiscard]] L001Environment parse_environment(
    const std::string& value) {
    if (value == "dual-context") {
        return L001Environment::DualContext;
    }
    if (value == "single-context-independent-runtime") {
        return L001Environment::SingleContextIndependentRuntime;
    }
    fail("unknown L001 measurement environment: " + value);
}

[[nodiscard]] L001Args split_l001_args(int argc, char** argv) {
    L001Args parsed;
    parsed.forwarded.push_back(argv[0]);
    bool found_environment = false;
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        if (argument == "--environment") {
            if (found_environment || index + 1 >= argc) {
                fail("L001 requires exactly one --environment value");
            }
            parsed.environment = parse_environment(argv[++index]);
            found_environment = true;
            continue;
        }
        parsed.forwarded.push_back(argv[index]);
    }
    if (!found_environment) {
        fail("L001 requires --environment");
    }
    return parsed;
}

[[nodiscard]] bool same_provenance(
    const B002VulkanContext& a,
    const B002VulkanContext& b) noexcept {
    return
        a.device_name() == b.device_name() &&
        a.driver_name() == b.driver_name() &&
        a.driver_info() == b.driver_info() &&
        a.api_version() == b.api_version() &&
        a.driver_version() == b.driver_version() &&
        a.vendor_id() == b.vendor_id() &&
        a.device_id() == b.device_id() &&
        a.timestamp_period_ns() == b.timestamp_period_ns();
}

void write_l001_device(
    const std::filesystem::path& root,
    const B002VulkanContext& context,
    L001Environment environment) {
    std::ofstream out(root / "l001-device.json");
    if (!out) {
        fail("cannot create L001 device file");
    }
    out
        << "{\n"
        << "  \"environment\": \"" << environment_name(environment) << "\",\n"
        << "  \"device\": \"" << context.device_name() << "\",\n"
        << "  \"driver_name\": \"" << context.driver_name() << "\",\n"
        << "  \"driver_info\": \"" << context.driver_info() << "\",\n"
        << "  \"api_version\": " << context.api_version() << ",\n"
        << "  \"driver_version\": " << context.driver_version() << ",\n"
        << "  \"vendor_id\": " << context.vendor_id() << ",\n"
        << "  \"device_id\": " << context.device_id() << ",\n"
        << "  \"timestamp_period_ns\": " << context.timestamp_period_ns() << "\n"
        << "}\n";
}

[[nodiscard]] bool validation_zero(const ValidationResult& value) noexcept {
    return
        value.hit_mismatches == 0U &&
        value.nearest_hit_tie_mismatches == 0U &&
        value.traversal_runtime_errors == 0U &&
        value.storage_failures == 0U &&
        value.immutable_owner_mutations == 0U;
}

void write_validation_role(
    std::ofstream& out,
    const char* role,
    const ValidationResult& value,
    bool trailing_comma) {
    out
        << "    \"" << role << "\": {\n"
        << "      \"visibility_mismatch_count\": 0,\n"
        << "      \"producer_semantic_error_count\": 0,\n"
        << "      \"hit_mismatch_count\": " << value.hit_mismatches << ",\n"
        << "      \"nearest_hit_tie_mismatch_count\": "
        << value.nearest_hit_tie_mismatches << ",\n"
        << "      \"static_hit_mismatch_count\": "
        << value.static_hit_mismatches << ",\n"
        << "      \"static_nearest_hit_tie_mismatch_count\": "
        << value.static_nearest_hit_tie_mismatches << ",\n"
        << "      \"dynamic_hit_mismatch_count\": "
        << value.dynamic_hit_mismatches << ",\n"
        << "      \"dynamic_nearest_hit_tie_mismatch_count\": "
        << value.dynamic_nearest_hit_tie_mismatches << ",\n"
        << "      \"merge_only_hit_mismatch_count\": "
        << value.merge_only_hit_mismatches << ",\n"
        << "      \"merge_only_nearest_hit_tie_mismatch_count\": "
        << value.merge_only_nearest_hit_tie_mismatches << ",\n"
        << "      \"traversal_runtime_error_count\": "
        << value.traversal_runtime_errors << ",\n"
        << "      \"storage_failure_count\": "
        << value.storage_failures << ",\n"
        << "      \"immutable_owner_mutation_count\": "
        << value.immutable_owner_mutations << ",\n"
        << "      \"workload_identity_match\": true,\n"
        << "      \"resolved_digest\": " << value.resolved_digest << "\n"
        << "    }" << (trailing_comma ? "," : "") << "\n";
}

void write_l001_validation(
    const std::filesystem::path& root,
    const Options& options,
    L001Environment environment,
    const ValidationResult& a,
    const ValidationResult& b,
    std::size_t baseline_a,
    std::size_t after_a,
    std::size_t baseline_b,
    std::size_t after_b,
    std::size_t after_b_destroy,
    std::size_t after_a_destroy,
    bool allocation_lifetime_consistent) {
    const bool resolved_identity =
        a.resolved_digest == b.resolved_digest;
    const bool passed =
        validation_zero(a) &&
        validation_zero(b) &&
        resolved_identity &&
        allocation_lifetime_consistent;

    std::ofstream out(root / "l001-validation.json");
    if (!out) {
        fail("cannot create L001 validation file");
    }
    out
        << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"environment\": \"" << environment_name(environment) << "\",\n"
        << "  \"track\": \"" << track_name(options.track) << "\",\n"
        << "  \"variant\": \"" << kind_name(control_kind(options.track)) << "\",\n"
        << "  \"validation_ray_prefix_count\": " << options.validation_rays << ",\n"
        << "  \"roles\": {\n";
    write_validation_role(out, "A", a, true);
    write_validation_role(out, "B", b, false);
    out
        << "  },\n"
        << "  \"resolved_output_identity\": "
        << (resolved_identity ? "true" : "false") << ",\n"
        << "  \"allocation_lifetime\": {\n"
        << "    \"baseline_a_live_bytes\": " << baseline_a << ",\n"
        << "    \"after_a_create_live_bytes\": " << after_a << ",\n"
        << "    \"baseline_b_live_bytes\": " << baseline_b << ",\n"
        << "    \"after_b_create_live_bytes\": " << after_b << ",\n"
        << "    \"after_b_destroy_live_bytes\": " << after_b_destroy << ",\n"
        << "    \"after_a_destroy_live_bytes\": " << after_a_destroy << ",\n"
        << "    \"consistent\": "
        << (allocation_lifetime_consistent ? "true" : "false") << "\n"
        << "  },\n"
        << "  \"timed_memory_decision_use\": \"diagnostic-only\",\n"
        << "  \"passed\": " << (passed ? "true" : "false") << "\n"
        << "}\n";
}

[[nodiscard]] int run_validation_pair(
    const std::filesystem::path& root,
    const Options& options,
    L001Environment environment) {
    const auto kind = control_kind(options.track);
    ValidationResult a{};
    ValidationResult b{};
    std::size_t baseline_a = 0U;
    std::size_t after_a = 0U;
    std::size_t baseline_b = 0U;
    std::size_t after_b = 0U;
    std::size_t after_b_destroy = 0U;
    std::size_t after_a_destroy = 0U;
    bool lifetime_ok = false;

    if (environment == L001Environment::DualContext) {
        B002VulkanContext context_a(
            options.validation,
            lane_b::kB002TargetDeviceName,
            true);
        B002VulkanContext context_b(
            options.validation,
            lane_b::kB002TargetDeviceName,
            true);
        if (!same_provenance(context_a, context_b)) {
            fail("L001 dual contexts have inconsistent device provenance");
        }
        write_l001_device(root, context_a, environment);

        baseline_a = context_a.live_allocation_bytes();
        baseline_b = context_b.live_allocation_bytes();
        {
            FormalRuntime runtime_a(context_a, options, kind);
            after_a = context_a.live_allocation_bytes();
            {
                FormalRuntime runtime_b(context_b, options, kind);
                after_b = context_b.live_allocation_bytes();
                a = runtime_a.validate_cycle(options.validation_rays);
                b = runtime_b.validate_cycle(options.validation_rays);
            }
            after_b_destroy = context_b.live_allocation_bytes();
        }
        after_a_destroy = context_a.live_allocation_bytes();
        lifetime_ok =
            after_a > baseline_a &&
            after_b > baseline_b &&
            after_b_destroy == baseline_b &&
            after_a_destroy == baseline_a;
    } else {
        B002VulkanContext context(
            options.validation,
            lane_b::kB002TargetDeviceName,
            true);
        write_l001_device(root, context, environment);

        baseline_a = context.live_allocation_bytes();
        baseline_b = baseline_a;
        {
            FormalRuntime runtime_a(context, options, kind);
            after_a = context.live_allocation_bytes();
            {
                FormalRuntime runtime_b(context, options, kind);
                after_b = context.live_allocation_bytes();
                a = runtime_a.validate_cycle(options.validation_rays);
                b = runtime_b.validate_cycle(options.validation_rays);
            }
            after_b_destroy = context.live_allocation_bytes();
        }
        after_a_destroy = context.live_allocation_bytes();
        lifetime_ok =
            after_a > baseline_a &&
            after_b > after_a &&
            after_b_destroy == after_a &&
            after_a_destroy == baseline_a;
        baseline_b = after_a;
    }

    write_l001_validation(
        root,
        options,
        environment,
        a,
        b,
        baseline_a,
        after_a,
        baseline_b,
        after_b,
        after_b_destroy,
        after_a_destroy,
        lifetime_ok);

    return
        validation_zero(a) &&
        validation_zero(b) &&
        a.resolved_digest == b.resolved_digest &&
        lifetime_ok
            ? 0
            : 2;
}

void write_sample_header(std::ofstream& samples) {
    samples
        << "phase,pair_index,order,role,variant,"
           "geometry_prepare_wall_us,"
           "allocation_reallocation_wall_us,"
           "geometry_upload_gpu_us,"
           "candidate_preprocess_gpu_us,"
           "build_rebuild_gpu_us,"
           "refit_gpu_us,compaction_gpu_us,"
           "instance_tlas_update_gpu_us,"
           "traversal_gpu_us,synchronization_wall_us,"
           "merge_gpu_us,storage_gpu_us,resolve_gpu_us,"
           "complete_gpu_us,gpu_us,"
           "complete_update_wall_us,complete_wall_us,"
           "persistent_bytes,transient_bytes,scratch_bytes,"
           "old_new_overlap_bytes,true_peak_resident_bytes,"
           "max_resident_bytes,max_true_peak_resident_bytes,"
           "storage_failures\n";
}

void execute_pairs(
    std::ofstream& samples,
    FormalRuntime& runtime_a,
    FormalRuntime& runtime_b,
    const Options& options,
    DynamicKind kind) {
    const auto total_pairs =
        options.warmup_pairs + options.measured_pairs;
    for (std::uint32_t pair = 0U; pair < total_pairs; ++pair) {
        const bool base_ab = options.start_order == "AB";
        const bool pair_ab =
            (pair % 2U == 0U) ? base_ab : !base_ab;
        const char* order = pair_ab ? "AB" : "BA";
        const char* phase =
            pair < options.warmup_pairs ? "warmup" : "measured";
        const auto pair_index =
            pair < options.warmup_pairs
                ? pair
                : pair - options.warmup_pairs;

        const auto run = [&](const char* role, FormalRuntime& runtime) {
            const auto result =
                runtime.run_batch(options.batch_transitions);
            if (result.storage_failures != 0U) {
                fail(std::string("L001 role ") + role + " storage failure");
            }
            write_sample_row(
                samples,
                phase,
                pair_index,
                order,
                role,
                kind,
                result);
        };

        if (pair_ab) {
            run("A", runtime_a);
            run("B", runtime_b);
        } else {
            run("B", runtime_b);
            run("A", runtime_a);
        }
        samples.flush();
    }
}

[[nodiscard]] int run_timing(
    const std::filesystem::path& root,
    const Options& options,
    L001Environment environment) {
    if (options.comparison != "control") {
        fail("L001 timing permits same-variant control only");
    }
    const auto kind = control_kind(options.track);

    std::ofstream samples(root / "l001-samples.csv");
    if (!samples) {
        fail("cannot create L001 sample CSV");
    }
    write_sample_header(samples);

    if (environment == L001Environment::DualContext) {
        B002VulkanContext context_a(
            false,
            lane_b::kB002TargetDeviceName,
            true);
        B002VulkanContext context_b(
            false,
            lane_b::kB002TargetDeviceName,
            true);
        if (!same_provenance(context_a, context_b)) {
            fail("L001 dual contexts have inconsistent device provenance");
        }
        write_l001_device(root, context_a, environment);
        FormalRuntime runtime_a(context_a, options, kind);
        FormalRuntime runtime_b(context_b, options, kind);
        execute_pairs(samples, runtime_a, runtime_b, options, kind);
    } else {
        B002VulkanContext context(
            false,
            lane_b::kB002TargetDeviceName,
            true);
        write_l001_device(root, context, environment);
        FormalRuntime runtime_a(context, options, kind);
        FormalRuntime runtime_b(context, options, kind);
        execute_pairs(samples, runtime_a, runtime_b, options, kind);
    }

    std::cout
        << "L001 process complete: "
        << environment_name(environment)
        << "/" << track_name(options.track)
        << "/" << kind_name(kind)
        << "\n";
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        auto parsed = split_l001_args(argc, argv);
        auto options = parse_options(
            static_cast<int>(parsed.forwarded.size()),
            parsed.forwarded.data());
        const auto root = artifact_root();
        std::filesystem::create_directories(root);

        if (options.validation_only) {
            if (options.validation_variant != "control" ||
                options.comparison != "control") {
                fail("L001 validation permits control/control only");
            }
            return run_validation_pair(root, options, parsed.environment);
        }
        return run_timing(root, options, parsed.environment);
    } catch (const std::exception& error) {
        std::cerr << "L001 fatal: " << error.what() << "\n";
        return 1;
    }
}

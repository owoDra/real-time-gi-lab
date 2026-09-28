#include "d001_runtime.hpp"

#include "../lane_a_split_rc/a001_analysis.hpp"
#include "../lane_a_split_rc/a001_scene.hpp"
#include "../lane_a_split_rc/a001_runtime.hpp"
#include "vk_context.hpp"

#include <array>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace phos::gi::lane_d {
namespace {

constexpr std::uint32_t kBoundedOwnerCapacity = 1280u;
constexpr std::uint32_t kForcedOverflowCapacity = 512u;

struct Cli {
    std::filesystem::path scene{
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"};
    std::filesystem::path output_dir{};
    lane_a::A001Settings settings{};
    std::uint32_t iterations{50};
    bool validation{};
    bool synthetic{};
};

struct BaselineSummary {
    lane_a::A001Timings timings{};
    lane_a::A001Memory memory{};
    lane_a::A001Analysis analysis{};
    std::array<std::uint32_t, 4> counters{};
    std::size_t work_item_count{};
    std::size_t output_count{};
    std::uint64_t owner_hash{};
};

struct VariantSummary {
    const char* name{};
    D001Mode mode{};
    std::uint32_t owner_capacity{};
    D001StageTimings timings{};
    D001Memory memory{};
    lane_a::A001Readback readback{};
    lane_a::A001Analysis analysis{};
    std::uint64_t owner_hash{};
};

struct OverflowSummary {
    std::uint32_t owner_capacity{};
    D001StageTimings timings{};
    D001Memory memory{};
    lane_a::A001Readback readback{};
    std::uint64_t owner_hash{};
};

lane_a::A001Case parse_case(const std::string& value) {
    if (value == "static") return lane_a::A001Case::Static;
    if (value == "camera-motion") return lane_a::A001Case::CameraMotion;
    if (value == "light-motion") return lane_a::A001Case::LightMotion;
    throw std::runtime_error("Unknown D005 case: " + value);
}

Cli parse(int argc, char** argv) {
    Cli cli;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        const auto value = [&](const char* flag) {
            if (i + 1 >= argc) {
                throw std::runtime_error(
                    std::string(flag) + " needs a value");
            }
            return std::string(argv[++i]);
        };

        if (arg == "--scene") {
            cli.scene = value("--scene");
        } else if (arg == "--output-dir") {
            cli.output_dir = value("--output-dir");
        } else if (arg == "--case") {
            cli.settings.case_id = parse_case(value("--case"));
        } else if (arg == "--iterations") {
            cli.iterations = static_cast<std::uint32_t>(
                std::stoul(value("--iterations")));
        } else if (arg == "--validation") {
            cli.validation = true;
        } else if (arg == "--synthetic") {
            cli.synthetic = true;
        } else if (arg == "--help") {
            std::cout
                << "phos-lane-d-d005 "
                   "--case static|camera-motion|light-motion "
                   "[--scene path] [--iterations N] "
                   "[--output-dir path] [--validation] [--synthetic]\n";
            std::exit(0);
        } else {
            throw std::runtime_error("Unknown argument: " + arg);
        }
    }

    cli.settings.frame_id =
        cli.settings.case_id == lane_a::A001Case::Static
            ? 0u
            : (cli.settings.case_id ==
                       lane_a::A001Case::CameraMotion
                   ? 1u
                   : 2u);

    if (cli.iterations == 0) {
        throw std::runtime_error("D005 iterations must be positive");
    }

    if (cli.output_dir.empty()) {
        cli.output_dir =
            std::filesystem::path(
                "out/research/lane-d-producer-optimization/"
                "005-stream-capacity-overflow/manual") /
            lane_a::case_name(cli.settings.case_id);
    }
    return cli;
}

std::uint64_t fnv1a(const void* data, std::size_t bytes) {
    constexpr std::uint64_t offset = 14695981039346656037ull;
    constexpr std::uint64_t prime = 1099511628211ull;
    auto hash = offset;
    const auto* input = static_cast<const unsigned char*>(data);
    for (std::size_t i = 0; i < bytes; ++i) {
        hash ^= std::uint64_t(input[i]);
        hash *= prime;
    }
    return hash;
}

template <class T>
std::uint64_t hash_vector(const std::vector<T>& values) {
    return fnv1a(values.data(), values.size() * sizeof(T));
}

std::string json_escape(const std::string& value) {
    std::string output;
    for (const char c : value) {
        switch (c) {
        case '\\': output += "\\\\"; break;
        case '"': output += "\\\""; break;
        case '\n': output += "\\n"; break;
        case '\r': output += "\\r"; break;
        case '\t': output += "\\t"; break;
        default: output += c; break;
        }
    }
    return output;
}

double full_producer(const VariantSummary& v) {
    return v.timings.visibility_owner_prerequisite_us() +
           v.timings.producer_reset_us +
           v.timings.producer_emit_us +
           v.timings.finalize_us;
}

double full_e2e(const VariantSummary& v) {
    return full_producer(v) +
           v.timings.gather_us +
           v.timings.merge_us +
           v.timings.resolve_us;
}

double depth_reuse_standalone_producer(
    const VariantSummary& full,
    const VariantSummary& reuse) {
    return full.timings.visibility_depth_prerequisite_us() +
           reuse.timings.incremental_producer_us();
}

double depth_reuse_standalone_e2e(
    const VariantSummary& full,
    const VariantSummary& reuse) {
    return full.timings.visibility_depth_prerequisite_us() +
           reuse.timings.incremental_end_to_end_us();
}

double overflow_attempt_e2e(const OverflowSummary& v) {
    return v.timings.visibility_owner_prerequisite_us() +
           v.timings.producer_reset_us +
           v.timings.producer_emit_us +
           v.timings.finalize_us +
           v.timings.gather_us +
           v.timings.merge_us +
           v.timings.resolve_us;
}

BaselineSummary run_baseline(
    VulkanContext& vk,
    const lane_a::SceneSurfaceSet& scene,
    const lane_a::A001Settings& settings,
    const lane_a::A001ParamsGpu& params,
    std::uint32_t iterations) {
    lane_a::A001Runtime runtime(vk, scene, params);
    const auto timings = runtime.measure(iterations);
    const auto readback = runtime.readback();
    return {
        timings,
        runtime.memory(),
        lane_a::analyze_a001(scene, settings, params, readback),
        readback.counters,
        readback.work_items.size(),
        readback.resolved.size(),
        hash_vector(readback.tile_owner),
    };
}

VariantSummary run_variant(
    VulkanContext& vk,
    const lane_a::SceneSurfaceSet& scene,
    const lane_a::A001Settings& settings,
    const lane_a::A001ParamsGpu& params,
    const char* name,
    D001Mode mode,
    std::uint32_t owner_capacity,
    std::uint32_t iterations) {
    D001Runtime runtime(
        vk,
        scene,
        params,
        mode,
        ProducerEmissionDomain::SurfaceScan,
        ProducerAllocationMode::OwnerSlotBounded,
        owner_capacity);
    const auto timings = runtime.measure(iterations);
    auto readback = runtime.readback();
    auto analysis =
        lane_a::analyze_a001(scene, settings, params, readback);
    return {
        name,
        mode,
        owner_capacity,
        timings,
        runtime.memory(),
        std::move(readback),
        std::move(analysis),
        0,
    };
}

OverflowSummary run_overflow(
    VulkanContext& vk,
    const lane_a::SceneSurfaceSet& scene,
    const lane_a::A001ParamsGpu& params,
    std::uint32_t owner_capacity,
    std::uint32_t iterations) {
    D001Runtime runtime(
        vk,
        scene,
        params,
        D001Mode::Full,
        ProducerEmissionDomain::SurfaceScan,
        ProducerAllocationMode::OwnerSlotBounded,
        owner_capacity);
    const auto timings = runtime.measure(iterations);
    auto readback = runtime.readback();
    return {
        owner_capacity,
        timings,
        runtime.memory(),
        std::move(readback),
        0,
    };
}

bool same_normal_semantics(
    const BaselineSummary& baseline,
    const VariantSummary& variant) {
    return variant.analysis.correct() &&
           variant.readback.counters[2] == 0u &&
           variant.analysis.visible_probe_count ==
               baseline.analysis.visible_probe_count &&
           variant.readback.work_items.size() ==
               baseline.work_item_count &&
           variant.readback.resolved.size() ==
               baseline.output_count &&
           hash_vector(variant.readback.tile_owner) ==
               baseline.owner_hash;
}

bool safe_overflow(
    const BaselineSummary& baseline,
    const OverflowSummary& overflow,
    const lane_a::A001Settings& settings) {
    const std::uint32_t expected_outputs =
        overflow.owner_capacity * settings.cascade_count;
    const std::uint32_t expected_work =
        expected_outputs * settings.rays_per_probe;

    return overflow.readback.counters[2] == 1u &&
           overflow.readback.counters[3] ==
               baseline.analysis.visible_probe_count &&
           overflow.readback.counters[0] == expected_work &&
           overflow.readback.counters[1] == expected_outputs &&
           overflow.readback.work_items.size() == expected_work &&
           overflow.readback.resolved.size() == expected_outputs &&
           hash_vector(overflow.readback.tile_owner) ==
               baseline.owner_hash;
}

void write_memory(
    std::ostream& out,
    const D001Memory& m,
    std::uint32_t owner_capacity,
    const lane_a::A001Settings& settings,
    std::size_t actual_stream_bytes) {
    const auto output_capacity =
        std::uint64_t(owner_capacity) * settings.cascade_count;
    const auto work_capacity =
        output_capacity * settings.rays_per_probe;
    out
        << "{"
        << "\"persistent_bytes\": " << m.gi_owned_persistent_bytes
        << ", \"transient_bytes\": " << m.gi_owned_transient_bytes
        << ", \"resident_bytes\": "
        << (m.gi_owned_persistent_bytes + m.gi_owned_transient_bytes)
        << ", \"stream_capacity_bytes\": " << m.stream_capacity_bytes
        << ", \"contribution_capacity_bytes\": "
        << work_capacity * 2u * sizeof(std::uint32_t)
        << ", \"output_capacity\": " << output_capacity
        << ", \"work_capacity\": " << work_capacity
        << ", \"actual_stream_bytes\": " << actual_stream_bytes
        << ", \"reused_visibility_bytes\": " << m.reused_visibility_bytes
        << "}";
}

void write_variant(
    std::ostream& out,
    const BaselineSummary& baseline,
    const VariantSummary& full_for_capacity,
    const VariantSummary& variant,
    const lane_a::A001Settings& settings) {
    const bool correct = same_normal_semantics(baseline, variant);
    const double producer =
        variant.mode == D001Mode::Full
            ? full_producer(variant)
            : depth_reuse_standalone_producer(
                  full_for_capacity, variant);
    const double e2e =
        variant.mode == D001Mode::Full
            ? full_e2e(variant)
            : depth_reuse_standalone_e2e(
                  full_for_capacity, variant);

    out
        << "{\n"
        << "      \"correct\": " << (correct ? "true" : "false") << ",\n"
        << "      \"visibility_mode\": \"" << mode_name(variant.mode) << "\",\n"
        << "      \"owner_capacity\": " << variant.owner_capacity << ",\n"
        << "      \"visible_owner_count\": "
        << variant.readback.counters[3] << ",\n"
        << "      \"overflow_flag\": "
        << variant.readback.counters[2] << ",\n"
        << "      \"work_item_count\": "
        << variant.readback.work_items.size() << ",\n"
        << "      \"output_count\": "
        << variant.readback.resolved.size() << ",\n"
        << "      \"timings_us\": {"
        << "\"producer_emit\": " << variant.timings.producer_emit_us
        << ", \"producer_total\": " << producer
        << ", \"end_to_end\": " << e2e
        << "},\n"
        << "      \"memory\": ";
    write_memory(
        out,
        variant.memory,
        variant.owner_capacity,
        settings,
        variant.readback.work_items.size() *
            sizeof(lane_a::SplitRcWorkItemV1));
    out << "\n    }";
}

void write_metrics(
    const std::filesystem::path& path,
    const Cli& cli,
    const std::string& gpu,
    const std::string& commit,
    const BaselineSummary& baseline,
    const VariantSummary& slot_full,
    const VariantSummary& bounded,
    const VariantSummary& bounded_depth,
    const OverflowSummary& overflow,
    const VariantSummary& fallback) {
    const bool normal_correct =
        baseline.analysis.correct() &&
        same_normal_semantics(baseline, slot_full) &&
        same_normal_semantics(baseline, bounded) &&
        same_normal_semantics(baseline, bounded_depth);
    const bool overflow_safe =
        safe_overflow(baseline, overflow, cli.settings);
    const bool fallback_correct =
        same_normal_semantics(baseline, fallback);

    std::filesystem::create_directories(path.parent_path());
    std::ofstream out(path);
    out << std::setprecision(10);

    out
        << "{\n"
        << "  \"experiment\": \"005-stream-capacity-overflow\",\n"
        << "  \"case\": \"" << lane_a::case_name(cli.settings.case_id)
        << "\",\n"
        << "  \"gpu\": \"" << json_escape(gpu) << "\",\n"
        << "  \"git_commit\": \"" << json_escape(commit) << "\",\n"
        << "  \"iterations\": " << cli.iterations << ",\n"
        << "  \"validation\": "
        << (cli.validation ? "true" : "false") << ",\n"
        << "  \"normal_correct\": "
        << (normal_correct ? "true" : "false") << ",\n"
        << "  \"overflow_safe\": "
        << (overflow_safe ? "true" : "false") << ",\n"
        << "  \"fallback_correct\": "
        << (fallback_correct ? "true" : "false") << ",\n"
        << "  \"baseline_a001\": {"
        << "\"correct\": "
        << (baseline.analysis.correct() ? "true" : "false")
        << ", \"visible_owner_count\": "
        << baseline.analysis.visible_probe_count
        << ", \"work_item_count\": " << baseline.work_item_count
        << ", \"output_count\": " << baseline.output_count
        << ", \"overflow_flag\": " << baseline.counters[2]
        << ", \"timings_us\": {"
        << "\"producer_total\": " << baseline.timings.producer_total_us
        << ", \"producer_emit\": " << baseline.timings.producer_emit_us
        << ", \"end_to_end\": " << baseline.timings.end_to_end_us
        << "}, \"memory\": {"
        << "\"persistent_bytes\": " << baseline.memory.persistent_bytes
        << ", \"transient_bytes\": " << baseline.memory.transient_bytes
        << ", \"resident_bytes\": " << baseline.memory.resident_bytes
        << ", \"stream_capacity_bytes\": " << baseline.memory.max_stream_bytes
        << "}},\n";

    out << "  \"owner-slot-full\": ";
    write_variant(
        out, baseline, slot_full, slot_full, cli.settings);
    out << ",\n  \"owner-slot-bounded\": ";
    write_variant(
        out, baseline, bounded, bounded, cli.settings);
    out << ",\n  \"owner-slot-bounded-depth-reuse\": ";
    write_variant(
        out, baseline, bounded, bounded_depth, cli.settings);
    out << ",\n  \"forced-overflow\": {\n"
        << "    \"safe\": " << (overflow_safe ? "true" : "false") << ",\n"
        << "    \"owner_capacity\": " << overflow.owner_capacity << ",\n"
        << "    \"attempted_visible_owners\": "
        << overflow.readback.counters[3] << ",\n"
        << "    \"overflow_flag\": "
        << overflow.readback.counters[2] << ",\n"
        << "    \"clamped_work_items\": "
        << overflow.readback.counters[0] << ",\n"
        << "    \"clamped_outputs\": "
        << overflow.readback.counters[1] << ",\n"
        << "    \"attempt_end_to_end_us\": "
        << overflow_attempt_e2e(overflow) << ",\n"
        << "    \"memory\": ";
    write_memory(
        out,
        overflow.memory,
        overflow.owner_capacity,
        cli.settings,
        overflow.readback.work_items.size() *
            sizeof(lane_a::SplitRcWorkItemV1));
    out << "\n  },\n"
        << "  \"fallback-full\": ";
    write_variant(
        out, baseline, fallback, fallback, cli.settings);
    out << ",\n"
        << "  \"fallback_gpu_retry_total_us\": "
        << overflow_attempt_e2e(overflow) + full_e2e(fallback)
        << "\n}\n";
}

} // namespace
} // namespace phos::gi::lane_d

int main(int argc, char** argv) {
    using namespace phos::gi;
    using namespace phos::gi::lane_a;
    using namespace phos::gi::lane_d;

    try {
        const auto cli = parse(argc, argv);
        SceneSurfaceSet scene;
        if (cli.synthetic) {
            std::cerr << "D005: synthetic bring-up workload "
                         "(not architectural evidence)\n";
            scene = make_synthetic_surface_samples(262144);
        } else {
            if (!std::filesystem::exists(cli.scene)) {
                throw std::runtime_error(
                    "Scene not found: " + cli.scene.string());
            }
            scene = load_scene_surface_samples(cli.scene);
        }

        const auto params = build_a001_params(scene, cli.settings);
        const auto full_capacity =
            cli.settings.tile_width * cli.settings.tile_height;
        if (kBoundedOwnerCapacity >= full_capacity ||
            kForcedOverflowCapacity >= kBoundedOwnerCapacity) {
            throw std::runtime_error("D005 capacity constants invalid");
        }

        VulkanContext vk(cli.validation);
        std::cerr << "GPU: " << vk.device_name() << '\n';

        const auto baseline =
            run_baseline(
                vk, scene, cli.settings, params, cli.iterations);
        auto slot_full =
            run_variant(
                vk, scene, cli.settings, params,
                "owner-slot-full", D001Mode::Full,
                full_capacity, cli.iterations);
        auto bounded =
            run_variant(
                vk, scene, cli.settings, params,
                "owner-slot-bounded", D001Mode::Full,
                kBoundedOwnerCapacity, cli.iterations);
        auto bounded_depth =
            run_variant(
                vk, scene, cli.settings, params,
                "owner-slot-bounded-depth-reuse",
                D001Mode::DepthReuse,
                kBoundedOwnerCapacity, cli.iterations);
        auto overflow =
            run_overflow(
                vk, scene, params,
                kForcedOverflowCapacity, cli.iterations);
        auto fallback =
            run_variant(
                vk, scene, cli.settings, params,
                "fallback-full", D001Mode::Full,
                full_capacity, cli.iterations);

        const bool normal_correct =
            baseline.analysis.correct() &&
            same_normal_semantics(baseline, slot_full) &&
            same_normal_semantics(baseline, bounded) &&
            same_normal_semantics(baseline, bounded_depth);
        const bool overflow_ok =
            safe_overflow(baseline, overflow, cli.settings);
        const bool fallback_ok =
            same_normal_semantics(baseline, fallback);

        const char* commit_env =
            std::getenv("PHOS_RESEARCH_GIT_COMMIT");
        const std::string commit =
            commit_env ? commit_env : "unknown";

        std::filesystem::create_directories(cli.output_dir);
        write_metrics(
            cli.output_dir / "metrics.json",
            cli,
            vk.device_name(),
            commit,
            baseline,
            slot_full,
            bounded,
            bounded_depth,
            overflow,
            fallback);

        std::cout
            << std::fixed << std::setprecision(3)
            << "case=" << case_name(cli.settings.case_id)
            << " gpu=\"" << vk.device_name() << "\""
            << " visible=" << baseline.analysis.visible_probe_count
            << " bounded_capacity=" << kBoundedOwnerCapacity
            << " stream_bytes=" << bounded.memory.stream_capacity_bytes
            << " full_stream_bytes=" << slot_full.memory.stream_capacity_bytes
            << " overflow_probe="
            << (overflow_ok ? "safe" : "FAIL")
            << " fallback="
            << (fallback_ok ? "pass" : "FAIL")
            << " correctness="
            << (normal_correct ? "pass" : "FAIL")
            << '\n';

        if (!normal_correct || !overflow_ok || !fallback_ok) {
            std::cerr << "D005 gate failed before timing acceptance\n";
            return 2;
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "fatal: " << error.what() << '\n';
        return 1;
    }
}

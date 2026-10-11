#include "d001_runtime.hpp"
#include "d003_runtime.hpp"

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
    std::uint64_t workload_id{};
};

struct TwoPassSummary {
    D001StageTimings timings{};
    D001Memory memory{};
    lane_a::A001Analysis analysis{};
    std::array<std::uint32_t, 4> counters{};
    std::size_t work_item_count{};
    std::size_t output_count{};
    std::uint64_t owner_hash{};
    std::uint64_t workload_id{};
};

struct PackedSummary {
    D003Timings timings{};
    D003Memory memory{};
    lane_a::A001Analysis analysis{};
    std::array<std::uint32_t, 4> counters{};
    std::size_t work_item_count{};
    std::size_t output_count{};
    std::uint64_t owner_hash{};
    std::uint64_t workload_id{};
};

lane_a::A001Case parse_case(const std::string& value) {
    if (value == "static") {
        return lane_a::A001Case::Static;
    }
    if (value == "camera-motion") {
        return lane_a::A001Case::CameraMotion;
    }
    if (value == "light-motion") {
        return lane_a::A001Case::LightMotion;
    }
    throw std::runtime_error("Unknown D003 case: " + value);
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
        } else if (arg == "--width") {
            cli.settings.tile_width = static_cast<std::uint32_t>(
                std::stoul(value("--width")));
        } else if (arg == "--height") {
            cli.settings.tile_height = static_cast<std::uint32_t>(
                std::stoul(value("--height")));
        } else if (arg == "--cascades") {
            cli.settings.cascade_count =
                static_cast<std::uint32_t>(
                    std::stoul(value("--cascades")));
        } else if (arg == "--rays-per-probe") {
            cli.settings.rays_per_probe =
                static_cast<std::uint32_t>(
                    std::stoul(value("--rays-per-probe")));
        } else if (arg == "--validation") {
            cli.validation = true;
        } else if (arg == "--synthetic") {
            cli.synthetic = true;
        } else if (arg == "--help") {
            std::cout
                << "phos-lane-d-d003 "
                   "--case static|camera-motion|light-motion "
                   "[--scene path] [--iterations N] "
                   "[--output-dir path] [--validation] [--synthetic]\n";
            std::exit(0);
        } else {
            throw std::runtime_error(
                "Unknown argument: " + arg);
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
        throw std::runtime_error(
            "D003 iterations must be positive");
    }

    if (cli.output_dir.empty()) {
        cli.output_dir =
            std::filesystem::path(
                "out/research/lane-d-producer-optimization/"
                "003-one-pass-owner-selection/manual") /
            lane_a::case_name(cli.settings.case_id);
    }
    return cli;
}

std::uint64_t fnv1a(const void* data, std::size_t bytes) {
    constexpr std::uint64_t offset = 14695981039346656037ull;
    constexpr std::uint64_t prime = 1099511628211ull;
    auto hash = offset;
    const auto* input =
        static_cast<const unsigned char*>(data);
    for (std::size_t i = 0; i < bytes; ++i) {
        hash ^= std::uint64_t(input[i]);
        hash *= prime;
    }
    return hash;
}

template <class T>
std::uint64_t hash_vector(const std::vector<T>& values) {
    return fnv1a(
        values.data(),
        values.size() * sizeof(T));
}

double ratio(
    std::uint64_t numerator,
    std::uint64_t denominator) {
    return denominator
        ? double(numerator) / double(denominator)
        : 0.0;
}

std::string json_escape(const std::string& value) {
    std::string output;
    output.reserve(value.size());
    for (const char c : value) {
        switch (c) {
        case '\\':
            output += "\\\\";
            break;
        case '"':
            output += "\\\"";
            break;
        case '\n':
            output += "\\n";
            break;
        case '\r':
            output += "\\r";
            break;
        case '\t':
            output += "\\t";
            break;
        default:
            output += c;
            break;
        }
    }
    return output;
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
    const auto analysis =
        lane_a::analyze_a001(
            scene,
            settings,
            params,
            readback);

    return {
        timings,
        runtime.memory(),
        analysis,
        readback.counters,
        readback.work_items.size(),
        readback.resolved.size(),
        hash_vector(readback.tile_owner),
        hash_vector(readback.work_items),
    };
}

TwoPassSummary run_two_pass(
    VulkanContext& vk,
    const lane_a::SceneSurfaceSet& scene,
    const lane_a::A001Settings& settings,
    const lane_a::A001ParamsGpu& params,
    std::uint32_t iterations) {
    D001Runtime runtime(
        vk,
        scene,
        params,
        D001Mode::Full,
        ProducerEmissionDomain::SurfaceScan);
    const auto timings = runtime.measure(iterations);
    const auto readback = runtime.readback();
    const auto analysis =
        lane_a::analyze_a001(
            scene,
            settings,
            params,
            readback);

    return {
        timings,
        runtime.memory(),
        analysis,
        readback.counters,
        readback.work_items.size(),
        readback.resolved.size(),
        hash_vector(readback.tile_owner),
        hash_vector(readback.work_items),
    };
}

PackedSummary run_packed(
    VulkanContext& vk,
    const lane_a::SceneSurfaceSet& scene,
    const lane_a::A001Settings& settings,
    const lane_a::A001ParamsGpu& params,
    std::uint32_t iterations) {
    D003Runtime runtime(vk, scene, params);
    const auto timings = runtime.measure(iterations);
    const auto readback = runtime.readback();
    const auto analysis =
        lane_a::analyze_a001(
            scene,
            settings,
            params,
            readback);

    return {
        timings,
        runtime.memory(),
        analysis,
        readback.counters,
        readback.work_items.size(),
        readback.resolved.size(),
        hash_vector(readback.tile_owner),
        hash_vector(readback.work_items),
    };
}

template <class Summary>
bool same_semantics(
    const BaselineSummary& baseline,
    const Summary& candidate) {
    return candidate.analysis.correct() &&
           baseline.analysis.visible_probe_count ==
               candidate.analysis.visible_probe_count &&
           baseline.work_item_count ==
               candidate.work_item_count &&
           baseline.output_count ==
               candidate.output_count &&
           baseline.owner_hash == candidate.owner_hash &&
           candidate.counters[2] == 0u;
}

double two_pass_producer_total(
    const TwoPassSummary& summary) {
    return summary.timings.visibility_owner_prerequisite_us() +
           summary.timings.producer_reset_us +
           summary.timings.producer_emit_us +
           summary.timings.finalize_us;
}

double two_pass_e2e(
    const TwoPassSummary& summary) {
    return two_pass_producer_total(summary) +
           summary.timings.gather_us +
           summary.timings.merge_us +
           summary.timings.resolve_us;
}

void write_locality(
    std::ostream& output,
    const lane_a::A001Analysis& analysis,
    std::size_t work_item_count) {
    const auto pairs = analysis.locality.adjacent_pairs;
    output
        << "{"
        << "\"same_probe_adjacent_ratio\": "
        << ratio(analysis.locality.same_probe_pairs, pairs)
        << ", \"same_cascade_adjacent_ratio\": "
        << ratio(analysis.locality.same_cascade_pairs, pairs)
        << ", \"neighboring_probe_adjacent_ratio\": "
        << ratio(analysis.locality.neighboring_probe_pairs, pairs)
        << ", \"neighboring_tile_adjacent_ratio\": "
        << ratio(analysis.locality.neighboring_tile_pairs, pairs)
        << ", \"mean_probe_run\": "
        << (analysis.locality.probe_runs
                ? double(work_item_count) /
                      double(analysis.locality.probe_runs)
                : 0.0)
        << "}";
}

void write_two_pass(
    std::ostream& output,
    const BaselineSummary& baseline,
    const TwoPassSummary& summary) {
    const bool correct = same_semantics(baseline, summary);
    const auto& t = summary.timings;
    const auto& m = summary.memory;

    output
        << "{\n"
        << "      \"correct\": "
        << (correct ? "true" : "false") << ",\n"
        << "      \"visible_probe_count\": "
        << summary.analysis.visible_probe_count << ",\n"
        << "      \"work_item_count\": "
        << summary.work_item_count << ",\n"
        << "      \"output_count\": "
        << summary.output_count << ",\n"
        << "      \"overflow_flag\": "
        << summary.counters[2] << ",\n"
        << "      \"workload_id\": "
        << summary.workload_id << ",\n"
        << "      \"locality\": ";
    write_locality(
        output,
        summary.analysis,
        summary.work_item_count);
    output
        << ",\n"
        << "      \"timings_us\": {\n"
        << "        \"visibility_reset\": "
        << t.visibility_reset_us << ",\n"
        << "        \"visibility_depth\": "
        << t.visibility_depth_us << ",\n"
        << "        \"owner_reset\": "
        << t.owner_reset_us << ",\n"
        << "        \"visibility_owner\": "
        << t.visibility_owner_us << ",\n"
        << "        \"producer_reset\": "
        << t.producer_reset_us << ",\n"
        << "        \"producer_emit\": "
        << t.producer_emit_us << ",\n"
        << "        \"finalize\": "
        << t.finalize_us << ",\n"
        << "        \"producer_total\": "
        << two_pass_producer_total(summary) << ",\n"
        << "        \"gather\": "
        << t.gather_us << ",\n"
        << "        \"merge\": "
        << t.merge_us << ",\n"
        << "        \"resolve\": "
        << t.resolve_us << ",\n"
        << "        \"end_to_end\": "
        << two_pass_e2e(summary) << "\n"
        << "      },\n"
        << "      \"memory\": {\n"
        << "        \"persistent_bytes\": "
        << m.gi_owned_persistent_bytes << ",\n"
        << "        \"transient_bytes\": "
        << m.gi_owned_transient_bytes << ",\n"
        << "        \"visibility_bytes\": "
        << m.prerequisite_visibility_bytes << ",\n"
        << "        \"producer_scratch_bytes\": "
        << m.producer_scratch_bytes << ",\n"
        << "        \"stream_capacity_bytes\": "
        << m.stream_capacity_bytes << ",\n"
        << "        \"actual_stream_bytes\": "
        << summary.work_item_count *
               sizeof(lane_a::SplitRcWorkItemV1) << "\n"
        << "      }\n"
        << "    }";
}

void write_packed(
    std::ostream& output,
    const BaselineSummary& baseline,
    const PackedSummary& summary) {
    const bool correct = same_semantics(baseline, summary);
    const auto& t = summary.timings;
    const auto& m = summary.memory;

    output
        << "{\n"
        << "      \"correct\": "
        << (correct ? "true" : "false") << ",\n"
        << "      \"visible_probe_count\": "
        << summary.analysis.visible_probe_count << ",\n"
        << "      \"work_item_count\": "
        << summary.work_item_count << ",\n"
        << "      \"output_count\": "
        << summary.output_count << ",\n"
        << "      \"overflow_flag\": "
        << summary.counters[2] << ",\n"
        << "      \"workload_id\": "
        << summary.workload_id << ",\n"
        << "      \"locality\": ";
    write_locality(
        output,
        summary.analysis,
        summary.work_item_count);
    output
        << ",\n"
        << "      \"timings_us\": {\n"
        << "        \"visibility_reset\": "
        << t.visibility_reset_us << ",\n"
        << "        \"visibility_select\": "
        << t.visibility_select_us << ",\n"
        << "        \"producer_reset\": "
        << t.producer_reset_us << ",\n"
        << "        \"producer_emit\": "
        << t.producer_emit_us << ",\n"
        << "        \"finalize\": "
        << t.finalize_us << ",\n"
        << "        \"producer_total\": "
        << t.producer_total_us() << ",\n"
        << "        \"gather\": "
        << t.gather_us << ",\n"
        << "        \"merge\": "
        << t.merge_us << ",\n"
        << "        \"resolve\": "
        << t.resolve_us << ",\n"
        << "        \"end_to_end\": "
        << t.end_to_end_us() << "\n"
        << "      },\n"
        << "      \"memory\": {\n"
        << "        \"persistent_bytes\": "
        << m.persistent_bytes << ",\n"
        << "        \"transient_bytes\": "
        << m.transient_bytes << ",\n"
        << "        \"visibility_bytes\": "
        << m.packed_visibility_bytes << ",\n"
        << "        \"producer_scratch_bytes\": "
        << m.producer_scratch_bytes << ",\n"
        << "        \"stream_capacity_bytes\": "
        << m.stream_capacity_bytes << ",\n"
        << "        \"actual_stream_bytes\": "
        << summary.work_item_count *
               sizeof(lane_a::SplitRcWorkItemV1) << "\n"
        << "      }\n"
        << "    }";
}

void write_metrics(
    const std::filesystem::path& path,
    const Cli& cli,
    const std::string& gpu,
    const std::string& commit,
    const BaselineSummary& baseline,
    const TwoPassSummary& two_pass,
    const PackedSummary& packed) {
    const bool cross_correct =
        baseline.analysis.correct() &&
        same_semantics(baseline, two_pass) &&
        same_semantics(baseline, packed);

    std::filesystem::create_directories(path.parent_path());
    std::ofstream output(path);
    output << std::setprecision(10);

    output
        << "{\n"
        << "  \"experiment\": \"003-one-pass-owner-selection\",\n"
        << "  \"case\": \""
        << lane_a::case_name(cli.settings.case_id) << "\",\n"
        << "  \"gpu\": \"" << json_escape(gpu) << "\",\n"
        << "  \"git_commit\": \"" << json_escape(commit) << "\",\n"
        << "  \"iterations\": " << cli.iterations << ",\n"
        << "  \"validation\": "
        << (cli.validation ? "true" : "false") << ",\n"
        << "  \"required_features\": "
           "[\"shaderInt64\", \"shaderBufferInt64Atomics\"],\n"
        << "  \"cross_variant_correct\": "
        << (cross_correct ? "true" : "false") << ",\n"
        << "  \"baseline_a001\": {\n"
        << "    \"correct\": "
        << (baseline.analysis.correct() ? "true" : "false") << ",\n"
        << "    \"visible_probe_count\": "
        << baseline.analysis.visible_probe_count << ",\n"
        << "    \"work_item_count\": "
        << baseline.work_item_count << ",\n"
        << "    \"output_count\": "
        << baseline.output_count << ",\n"
        << "    \"overflow_flag\": "
        << baseline.counters[2] << ",\n"
        << "    \"workload_id\": "
        << baseline.workload_id << ",\n"
        << "    \"timings_us\": {"
        << "\"producer_total\": "
        << baseline.timings.producer_total_us
        << ", \"producer_emit\": "
        << baseline.timings.producer_emit_us
        << ", \"end_to_end\": "
        << baseline.timings.end_to_end_us
        << "},\n"
        << "    \"memory\": {"
        << "\"persistent_bytes\": "
        << baseline.memory.persistent_bytes
        << ", \"transient_bytes\": "
        << baseline.memory.transient_bytes
        << ", \"visibility_bytes\": "
        << 2 * cli.settings.tile_width *
               cli.settings.tile_height *
               sizeof(std::uint32_t)
        << ", \"stream_capacity_bytes\": "
        << baseline.memory.max_stream_bytes
        << "}\n"
        << "  },\n"
        << "  \"two-pass-staged\": ";
    write_two_pass(output, baseline, two_pass);
    output << ",\n  \"packed-one-pass\": ";
    write_packed(output, baseline, packed);
    output << "\n}\n";
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
            std::cerr
                << "D003: synthetic bring-up workload "
                   "(not architectural evidence)\n";
            scene = make_synthetic_surface_samples(262144);
        } else {
            if (!std::filesystem::exists(cli.scene)) {
                throw std::runtime_error(
                    "Scene not found: " + cli.scene.string());
            }
            scene = load_scene_surface_samples(cli.scene);
        }

        const auto params =
            build_a001_params(scene, cli.settings);

        VulkanContext vk(VulkanContextOptions{
            cli.validation,
            true,
        });
        std::cerr << "GPU: " << vk.device_name() << '\n';

        const auto baseline =
            run_baseline(
                vk,
                scene,
                cli.settings,
                params,
                cli.iterations);
        const auto two_pass =
            run_two_pass(
                vk,
                scene,
                cli.settings,
                params,
                cli.iterations);
        const auto packed =
            run_packed(
                vk,
                scene,
                cli.settings,
                params,
                cli.iterations);

        const bool correct =
            baseline.analysis.correct() &&
            same_semantics(baseline, two_pass) &&
            same_semantics(baseline, packed);

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
            two_pass,
            packed);

        std::cout
            << std::fixed
            << std::setprecision(3)
            << "case=" << case_name(cli.settings.case_id)
            << " gpu=\"" << vk.device_name() << "\""
            << " surfaces=" << scene.samples.size()
            << " visible_probes="
            << baseline.analysis.visible_probe_count
            << " work_items=" << baseline.work_item_count
            << " a001_producer_us="
            << baseline.timings.producer_total_us
            << " two_pass_us="
            << two_pass_producer_total(two_pass)
            << " packed_us="
            << packed.timings.producer_total_us()
            << " correctness="
            << (correct ? "pass" : "FAIL")
            << '\n';

        if (!correct) {
            std::cerr
                << "D003 semantic/cross-variant correctness "
                   "gate failed\n";
            return 2;
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "fatal: " << error.what() << '\n';
        return 1;
    }
}

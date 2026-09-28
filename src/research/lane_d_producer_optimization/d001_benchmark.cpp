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

struct VariantSummary {
    D001Mode mode{};
    D001StageTimings timings{};
    D001Memory memory{};
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
    throw std::runtime_error("Unknown D001 case: " + value);
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
                << "phos-lane-d-producer-optimization "
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
            "D001 iterations must be positive");
    }

    if (cli.output_dir.empty()) {
        cli.output_dir =
            std::filesystem::path(
                "out/research/lane-d-producer-optimization/"
                "001-visibility-reuse/manual") /
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

double mean_probe_run(
    const lane_a::A001Analysis& analysis,
    std::size_t work_item_count) {
    return analysis.locality.probe_runs
        ? double(work_item_count) /
              double(analysis.locality.probe_runs)
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

VariantSummary run_variant(
    VulkanContext& vk,
    const lane_a::SceneSurfaceSet& scene,
    const lane_a::A001Settings& settings,
    const lane_a::A001ParamsGpu& params,
    D001Mode mode,
    std::uint32_t iterations) {
    D001Runtime runtime(vk, scene, params, mode);
    const auto timings = runtime.measure(iterations);
    const auto readback = runtime.readback();
    const auto analysis =
        lane_a::analyze_a001(
            scene,
            settings,
            params,
            readback);

    return {
        mode,
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

bool same_counts(
    const BaselineSummary& baseline,
    const VariantSummary& variant) {
    return baseline.analysis.visible_probe_count ==
               variant.analysis.visible_probe_count &&
           baseline.work_item_count ==
               variant.work_item_count &&
           baseline.output_count ==
               variant.output_count &&
           variant.counters[2] == 0u;
}

double full_visibility_prerequisite(
    const VariantSummary& full) {
    return full.timings.visibility_owner_prerequisite_us();
}

double depth_visibility_prerequisite(
    const VariantSummary& full) {
    return full.timings.visibility_depth_prerequisite_us();
}

double incremental_producer(
    const VariantSummary& variant) {
    return variant.timings.incremental_producer_us();
}

double incremental_end_to_end(
    const VariantSummary& variant) {
    return variant.timings.incremental_end_to_end_us();
}

double standalone_producer(
    const VariantSummary& full,
    const VariantSummary& variant) {
    if (variant.mode == D001Mode::Full) {
        return full_visibility_prerequisite(full) +
               full.timings.producer_reset_us +
               full.timings.producer_emit_us +
               full.timings.finalize_us;
    }
    if (variant.mode == D001Mode::DepthReuse) {
        return depth_visibility_prerequisite(full) +
               incremental_producer(variant);
    }
    return full_visibility_prerequisite(full) +
           incremental_producer(variant);
}

double standalone_end_to_end(
    const VariantSummary& full,
    const VariantSummary& variant) {
    if (variant.mode == D001Mode::Full) {
        return standalone_producer(full, variant) +
               full.timings.gather_us +
               full.timings.merge_us +
               full.timings.resolve_us;
    }

    const double prerequisite =
        variant.mode == D001Mode::DepthReuse
            ? depth_visibility_prerequisite(full)
            : full_visibility_prerequisite(full);
    return prerequisite +
           incremental_end_to_end(variant);
}

void write_locality(
    std::ostream& output,
    const lane_a::A001Analysis& analysis,
    std::size_t work_item_count) {
    output
        << "{"
        << "\"same_probe_adjacent_ratio\": "
        << ratio(
               analysis.locality.same_probe_pairs,
               analysis.locality.adjacent_pairs)
        << ", \"same_cascade_adjacent_ratio\": "
        << ratio(
               analysis.locality.same_cascade_pairs,
               analysis.locality.adjacent_pairs)
        << ", \"neighboring_probe_adjacent_ratio\": "
        << ratio(
               analysis.locality.neighboring_probe_pairs,
               analysis.locality.adjacent_pairs)
        << ", \"neighboring_tile_adjacent_ratio\": "
        << ratio(
               analysis.locality.neighboring_tile_pairs,
               analysis.locality.adjacent_pairs)
        << ", \"mean_probe_run\": "
        << mean_probe_run(analysis, work_item_count)
        << "}";
}

void write_variant(
    std::ostream& output,
    const BaselineSummary& baseline,
    const VariantSummary& full,
    const VariantSummary& variant) {
    const bool counts_match =
        same_counts(baseline, variant);
    const bool owner_match =
        baseline.owner_hash == variant.owner_hash;
    const bool correct =
        variant.analysis.correct() &&
        counts_match &&
        owner_match;

    const auto& t = variant.timings;
    const auto& m = variant.memory;

    output
        << "{\n"
        << "      \"correct\": "
        << (correct ? "true" : "false") << ",\n"
        << "      \"visibility_correct\": "
        << (variant.analysis.visibility_correct
                ? "true"
                : "false")
        << ",\n"
        << "      \"producer_correct\": "
        << (variant.analysis.producer_correct
                ? "true"
                : "false")
        << ",\n"
        << "      \"resolve_correct\": "
        << (variant.analysis.resolve_correct
                ? "true"
                : "false")
        << ",\n"
        << "      \"counts_match_baseline\": "
        << (counts_match ? "true" : "false")
        << ",\n"
        << "      \"owner_set_match_baseline\": "
        << (owner_match ? "true" : "false")
        << ",\n"
        << "      \"visible_probe_count\": "
        << variant.analysis.visible_probe_count << ",\n"
        << "      \"work_item_count\": "
        << variant.work_item_count << ",\n"
        << "      \"output_count\": "
        << variant.output_count << ",\n"
        << "      \"overflow_flag\": "
        << variant.counters[2] << ",\n"
        << "      \"workload_id\": "
        << variant.workload_id << ",\n"
        << "      \"locality\": ";
    write_locality(
        output,
        variant.analysis,
        variant.work_item_count);
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
        << "        \"gather\": "
        << t.gather_us << ",\n"
        << "        \"merge\": "
        << t.merge_us << ",\n"
        << "        \"resolve\": "
        << t.resolve_us << ",\n"
        << "        \"renderer_prerequisite\": "
        << (variant.mode == D001Mode::Full
                ? full_visibility_prerequisite(full)
                : (variant.mode == D001Mode::DepthReuse
                       ? depth_visibility_prerequisite(full)
                       : full_visibility_prerequisite(full)))
        << ",\n"
        << "        \"incremental_producer\": "
        << (variant.mode == D001Mode::Full
                ? standalone_producer(full, variant)
                : incremental_producer(variant))
        << ",\n"
        << "        \"incremental_end_to_end\": "
        << (variant.mode == D001Mode::Full
                ? standalone_end_to_end(full, variant)
                : incremental_end_to_end(variant))
        << ",\n"
        << "        \"standalone_producer\": "
        << standalone_producer(full, variant)
        << ",\n"
        << "        \"standalone_end_to_end\": "
        << standalone_end_to_end(full, variant)
        << "\n"
        << "      },\n"
        << "      \"memory\": {\n"
        << "        \"physical_persistent_bytes\": "
        << m.physical_persistent_bytes << ",\n"
        << "        \"physical_transient_bytes\": "
        << m.physical_transient_bytes << ",\n"
        << "        \"physical_resident_bytes\": "
        << m.physical_resident_bytes << ",\n"
        << "        \"gi_owned_persistent_bytes\": "
        << m.gi_owned_persistent_bytes << ",\n"
        << "        \"gi_owned_transient_bytes\": "
        << m.gi_owned_transient_bytes << ",\n"
        << "        \"producer_scratch_bytes\": "
        << m.producer_scratch_bytes << ",\n"
        << "        \"stream_capacity_bytes\": "
        << m.stream_capacity_bytes << ",\n"
        << "        \"actual_stream_bytes\": "
        << variant.work_item_count *
               sizeof(lane_a::SplitRcWorkItemV1)
        << ",\n"
        << "        \"reused_visibility_bytes\": "
        << m.reused_visibility_bytes << ",\n"
        << "        \"prerequisite_visibility_bytes\": "
        << m.prerequisite_visibility_bytes << "\n"
        << "      },\n"
        << "      \"errors\": [";

    for (std::size_t i = 0;
         i < variant.analysis.errors.size();
         ++i) {
        if (i) {
            output << ", ";
        }
        output
            << "\""
            << json_escape(variant.analysis.errors[i])
            << "\"";
    }
    output << "]\n    }";
}

void write_metrics(
    const std::filesystem::path& path,
    const Cli& cli,
    const std::string& gpu,
    const std::string& commit,
    const BaselineSummary& baseline,
    const std::array<VariantSummary, 3>& variants) {
    const auto& full = variants[0];

    bool cross_correct = baseline.analysis.correct();
    for (const auto& variant : variants) {
        cross_correct =
            cross_correct &&
            variant.analysis.correct() &&
            same_counts(baseline, variant) &&
            baseline.owner_hash == variant.owner_hash;
    }

    std::filesystem::create_directories(path.parent_path());
    std::ofstream output(path);
    output << std::setprecision(10);

    output
        << "{\n"
        << "  \"experiment\": \"001-visibility-reuse\",\n"
        << "  \"case\": \""
        << lane_a::case_name(cli.settings.case_id)
        << "\",\n"
        << "  \"gpu\": \""
        << json_escape(gpu) << "\",\n"
        << "  \"git_commit\": \""
        << json_escape(commit) << "\",\n"
        << "  \"iterations\": "
        << cli.iterations << ",\n"
        << "  \"validation\": "
        << (cli.validation ? "true" : "false")
        << ",\n"
        << "  \"cross_variant_correct\": "
        << (cross_correct ? "true" : "false")
        << ",\n"
        << "  \"baseline_a001\": {\n"
        << "    \"correct\": "
        << (baseline.analysis.correct()
                ? "true"
                : "false")
        << ",\n"
        << "    \"visible_probe_count\": "
        << baseline.analysis.visible_probe_count
        << ",\n"
        << "    \"work_item_count\": "
        << baseline.work_item_count << ",\n"
        << "    \"output_count\": "
        << baseline.output_count << ",\n"
        << "    \"overflow_flag\": "
        << baseline.counters[2] << ",\n"
        << "    \"workload_id\": "
        << baseline.workload_id << ",\n"
        << "    \"locality\": ";
    write_locality(
        output,
        baseline.analysis,
        baseline.work_item_count);
    output
        << ",\n"
        << "    \"timings_us\": {"
        << "\"visibility_depth\": "
        << baseline.timings.visibility_depth_us
        << ", \"visibility_owner\": "
        << baseline.timings.visibility_owner_us
        << ", \"producer_emit\": "
        << baseline.timings.producer_emit_us
        << ", \"finalize\": "
        << baseline.timings.finalize_us
        << ", \"producer_total\": "
        << baseline.timings.producer_total_us
        << ", \"gather\": "
        << baseline.timings.gather_us
        << ", \"merge\": "
        << baseline.timings.merge_us
        << ", \"resolve\": "
        << baseline.timings.resolve_us
        << ", \"end_to_end\": "
        << baseline.timings.end_to_end_us
        << "},\n"
        << "    \"memory\": {"
        << "\"persistent_bytes\": "
        << baseline.memory.persistent_bytes
        << ", \"transient_bytes\": "
        << baseline.memory.transient_bytes
        << ", \"resident_bytes\": "
        << baseline.memory.resident_bytes
        << ", \"max_stream_bytes\": "
        << baseline.memory.max_stream_bytes
        << "}\n"
        << "  },\n"
        << "  \"variants\": {\n";

    for (std::size_t i = 0; i < variants.size(); ++i) {
        output
            << "    \""
            << mode_name(variants[i].mode)
            << "\": ";
        write_variant(
            output,
            baseline,
            full,
            variants[i]);
        output
            << (i + 1 == variants.size()
                    ? "\n"
                    : ",\n");
    }

    output
        << "  }\n"
        << "}\n";
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
                << "D001: synthetic bring-up workload "
                   "(not architectural evidence)\n";
            scene = make_synthetic_surface_samples(262144);
        } else {
            if (!std::filesystem::exists(cli.scene)) {
                throw std::runtime_error(
                    "Scene not found: " +
                    cli.scene.string());
            }
            scene = load_scene_surface_samples(cli.scene);
        }

        const auto params =
            build_a001_params(scene, cli.settings);
        VulkanContext vk(cli.validation);
        std::cerr
            << "GPU: "
            << vk.device_name()
            << '\n';

        const auto baseline =
            run_baseline(
                vk,
                scene,
                cli.settings,
                params,
                cli.iterations);

        std::array<VariantSummary, 3> variants{{
            run_variant(
                vk,
                scene,
                cli.settings,
                params,
                D001Mode::Full,
                cli.iterations),
            run_variant(
                vk,
                scene,
                cli.settings,
                params,
                D001Mode::DepthReuse,
                cli.iterations),
            run_variant(
                vk,
                scene,
                cli.settings,
                params,
                D001Mode::OwnerReuse,
                cli.iterations),
        }};

        bool correct = baseline.analysis.correct();
        for (const auto& variant : variants) {
            correct =
                correct &&
                variant.analysis.correct() &&
                same_counts(baseline, variant) &&
                baseline.owner_hash == variant.owner_hash;
        }

        const char* commit_env =
            std::getenv("PHOS_RESEARCH_GIT_COMMIT");
        const std::string commit =
            commit_env ? commit_env : "unknown";

        std::filesystem::create_directories(
            cli.output_dir);
        write_metrics(
            cli.output_dir / "metrics.json",
            cli,
            vk.device_name(),
            commit,
            baseline,
            variants);

        std::cout
            << std::fixed
            << std::setprecision(3)
            << "case="
            << case_name(cli.settings.case_id)
            << " gpu=\""
            << vk.device_name()
            << "\""
            << " surfaces="
            << scene.samples.size()
            << " visible_probes="
            << baseline.analysis.visible_probe_count
            << " work_items="
            << baseline.work_item_count
            << " baseline_producer_us="
            << baseline.timings.producer_total_us
            << " full_us="
            << standalone_producer(
                   variants[0],
                   variants[0])
            << " depth_reuse_incremental_us="
            << incremental_producer(variants[1])
            << " owner_reuse_incremental_us="
            << incremental_producer(variants[2])
            << " correctness="
            << (correct ? "pass" : "FAIL")
            << '\n';

        if (!correct) {
            std::cerr
                << "D001 semantic/cross-variant correctness "
                   "gate failed\n";
            return 2;
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "fatal: "
            << error.what()
            << '\n';
        return 1;
    }
}

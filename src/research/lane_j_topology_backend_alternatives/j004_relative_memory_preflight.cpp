#include "baseline/lane_e_hwrt/b002_hwrt.hpp"
#include "j003_persistent_gpu.hpp"
#include "j003_persistent_layout.hpp"
#include "j003_snapshot.hpp"
#include "j003_transition.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace lane_j = phos::gi::research::lane_j;
namespace lane_b = phos::gi::research::lane_b;

namespace {

constexpr double kMemoryRatioLimit = 1.25;

constexpr std::array<const char*, 5> kProfiles = {
    "small-global-high",
    "medium-global-representative",
    "medium-local-high",
    "large-global-high",
    "large-local-high",
};

struct Options {
    std::filesystem::path root{
        "out/research/lane-j-topology-backend-alternatives/"
        "002-deterministic-topology-contract/materialized"};
    std::filesystem::path output{};
    bool validation{};
};

struct MemorySample {
    std::uint32_t cycle{};
    std::uint32_t step{};
    std::size_t persistent_bytes{};
    std::size_t true_peak_resident_bytes{};
    std::size_t old_new_overlap_bytes{};
    std::size_t staging_bytes{};
};

struct Replay {
    std::string device;
    std::vector<MemorySample> samples;
    std::size_t cycle1_end_persistent_bytes{};
    std::size_t cycle2_end_persistent_bytes{};
    bool bounded{};
};

struct ProfileResult {
    std::string name;
    Replay candidate;
    Replay comparator;
    double max_persistent_ratio{};
    double max_peak_ratio{};
    bool passed{};
};

Options parse_options(int argc, char** argv) {
    Options options;
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        const auto value = [&](const char* name) -> std::string {
            if (index + 1 >= argc) {
                throw std::runtime_error(std::string(name) + " requires a value");
            }
            return argv[++index];
        };
        if (argument == "--root") {
            options.root = value("--root");
        } else if (argument == "--output") {
            options.output = value("--output");
        } else if (argument == "--validation") {
            options.validation = true;
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-j-j004-memory-preflight "
                   "[--root path] [--output path] [--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error(
                "unknown J004 memory-preflight option: " + argument);
        }
    }
    if (options.output.empty()) {
        if (const char* artifact = std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");
            artifact != nullptr && *artifact != '\0') {
            options.output =
                std::filesystem::path(artifact) /
                "j004-relative-memory-preflight.json";
        }
    }
    return options;
}

std::filesystem::path snapshot_path(
    const std::filesystem::path& root,
    const std::string& profile,
    std::uint32_t step) {
    std::ostringstream name;
    name << "step-" << std::setw(2) << std::setfill('0')
         << step << ".bin";
    return root / profile / name.str();
}

std::vector<std::vector<lane_j::Triangle>> load_profile(
    const std::filesystem::path& root,
    const std::string& profile) {
    std::vector<std::vector<lane_j::Triangle>> snapshots;
    snapshots.reserve(8U);
    for (std::uint32_t step = 0U; step < 8U; ++step) {
        const auto path = snapshot_path(root, profile, step);
        if (!std::filesystem::is_regular_file(path)) {
            throw std::runtime_error(
                "missing frozen J002 snapshot: " + path.string());
        }
        snapshots.push_back(lane_j::load_j002_snapshot(path));
    }
    return snapshots;
}

std::vector<lane_b::Triangle> to_lane_e(
    const std::vector<lane_j::Triangle>& input) {
    std::vector<lane_b::Triangle> output;
    output.reserve(input.size());
    for (const auto& triangle : input) {
        output.push_back({
            {triangle.v0.x, triangle.v0.y, triangle.v0.z},
            {triangle.v1.x, triangle.v1.y, triangle.v1.z},
            {triangle.v2.x, triangle.v2.y, triangle.v2.z},
            triangle.primitive_id,
            triangle.material_id,
            triangle.instance_id,
            triangle.two_sided,
        });
    }
    return output;
}

Replay run_candidate(
    const std::vector<std::vector<lane_j::Triangle>>& snapshots,
    bool validation) {
    lane_j::ClusterTransitionState transition_state(snapshots.front());
    lane_j::PersistentClusterLayout layout(transition_state);

    phos::gi::VulkanContext context(validation);
    if (context.device_name() != lane_b::kB002TargetDeviceName) {
        throw std::runtime_error(
            "J004 clustered candidate selected unexpected device: " +
            context.device_name());
    }
    lane_j::PersistentGpuState gpu(context, layout);

    Replay replay;
    replay.device = context.device_name();
    replay.samples.push_back({
        0U,
        0U,
        gpu.persistent_allocation_bytes(),
        gpu.persistent_allocation_bytes(),
        0U,
        0U,
    });

    for (std::uint32_t cycle = 1U; cycle <= 2U; ++cycle) {
        for (std::uint32_t offset = 1U; offset <= 8U; ++offset) {
            const auto step = offset % 8U;
            const auto transition =
                transition_state.update(snapshots[step]);
            const auto layout_update =
                layout.synchronize(transition_state, transition);
            const auto sync = gpu.synchronize(layout, layout_update);
            replay.samples.push_back({
                cycle,
                step,
                sync.candidate_persistent_allocation_bytes,
                sync.true_peak_resident_bytes,
                sync.resize_old_new_overlap_allocation_bytes,
                sync.max_staging_allocation_bytes,
            });
        }
        const auto end = gpu.persistent_allocation_bytes();
        if (cycle == 1U) {
            replay.cycle1_end_persistent_bytes = end;
        } else {
            replay.cycle2_end_persistent_bytes = end;
        }
    }

    replay.bounded =
        replay.cycle1_end_persistent_bytes ==
        replay.cycle2_end_persistent_bytes;
    return replay;
}

std::size_t comparator_live_expected(
    const lane_b::B002HwrtTraversal& traversal) {
    return traversal.setup_stats().persistent_bytes +
           traversal.setup_stats().scratch_bytes;
}

Replay run_hwrt_comparator(
    const std::vector<std::vector<lane_j::Triangle>>& snapshots,
    bool validation) {
    lane_b::B002VulkanContext context(
        validation,
        lane_b::kB002TargetDeviceName,
        true);

    auto current = std::make_unique<lane_b::B002HwrtTraversal>(
        context,
        to_lane_e(snapshots.front()),
        std::string{},
        false);

    if (context.live_allocation_bytes() !=
        comparator_live_expected(*current)) {
        throw std::runtime_error(
            "Lane-E HWRT initial allocation census is incomplete");
    }

    Replay replay;
    replay.device = context.device_name();
    replay.samples.push_back({
        0U,
        0U,
        current->setup_stats().persistent_bytes,
        context.peak_allocation_bytes(),
        0U,
        current->setup_stats().scratch_bytes,
    });

    for (std::uint32_t cycle = 1U; cycle <= 2U; ++cycle) {
        for (std::uint32_t offset = 1U; offset <= 8U; ++offset) {
            const auto step = offset % 8U;
            const auto old_persistent =
                current->setup_stats().persistent_bytes;

            context.reset_allocation_peak();
            auto next = std::make_unique<lane_b::B002HwrtTraversal>(
                context,
                to_lane_e(snapshots[step]),
                std::string{},
                false);

            const auto next_persistent =
                next->setup_stats().persistent_bytes;
            const auto overlap =
                old_persistent + next_persistent;
            const auto peak = context.peak_allocation_bytes();

            current.reset();
            current = std::move(next);

            if (context.live_allocation_bytes() !=
                comparator_live_expected(*current)) {
                throw std::runtime_error(
                    "Lane-E HWRT post-rebuild allocation census is incomplete");
            }
            if (peak < overlap) {
                throw std::runtime_error(
                    "Lane-E HWRT true peak omitted old/new persistent overlap");
            }

            replay.samples.push_back({
                cycle,
                step,
                next_persistent,
                peak,
                overlap,
                current->setup_stats().scratch_bytes,
            });
        }

        const auto end = current->setup_stats().persistent_bytes;
        if (cycle == 1U) {
            replay.cycle1_end_persistent_bytes = end;
        } else {
            replay.cycle2_end_persistent_bytes = end;
        }
    }

    replay.bounded =
        replay.cycle1_end_persistent_bytes ==
        replay.cycle2_end_persistent_bytes;
    return replay;
}

ProfileResult compare_profile(
    const std::filesystem::path& root,
    const std::string& name,
    bool validation) {
    const auto snapshots = load_profile(root, name);

    ProfileResult result;
    result.name = name;
    result.candidate = run_candidate(snapshots, validation);
    result.comparator =
        run_hwrt_comparator(snapshots, validation);

    if (result.candidate.device != result.comparator.device) {
        throw std::runtime_error(
            "J004 memory preflight device provenance mismatch");
    }
    if (result.candidate.samples.size() !=
        result.comparator.samples.size()) {
        throw std::runtime_error(
            "J004 memory preflight sample structure mismatch");
    }

    result.passed =
        result.candidate.bounded &&
        result.comparator.bounded;

    for (std::size_t index = 0U;
         index < result.candidate.samples.size();
         ++index) {
        const auto& candidate = result.candidate.samples[index];
        const auto& comparator = result.comparator.samples[index];

        if (candidate.cycle != comparator.cycle ||
            candidate.step != comparator.step) {
            throw std::runtime_error(
                "J004 memory preflight transition identity mismatch");
        }
        if (comparator.persistent_bytes == 0U ||
            comparator.true_peak_resident_bytes == 0U) {
            throw std::runtime_error(
                "J004 memory comparator reported zero memory");
        }

        const auto persistent_ratio =
            double(candidate.persistent_bytes) /
            double(comparator.persistent_bytes);
        const auto peak_ratio =
            double(candidate.true_peak_resident_bytes) /
            double(comparator.true_peak_resident_bytes);

        result.max_persistent_ratio =
            std::max(result.max_persistent_ratio, persistent_ratio);
        result.max_peak_ratio =
            std::max(result.max_peak_ratio, peak_ratio);

        if (persistent_ratio > kMemoryRatioLimit ||
            peak_ratio > kMemoryRatioLimit) {
            result.passed = false;
        }
    }

    return result;
}

void write_sample(
    std::ostream& out,
    const MemorySample& sample) {
    out
        << "{\"cycle\":" << sample.cycle
        << ",\"step\":" << sample.step
        << ",\"persistent_bytes\":" << sample.persistent_bytes
        << ",\"true_peak_resident_bytes\":"
        << sample.true_peak_resident_bytes
        << ",\"old_new_overlap_bytes\":"
        << sample.old_new_overlap_bytes
        << ",\"staging_or_scratch_bytes\":"
        << sample.staging_bytes
        << "}";
}

std::string make_json(
    const std::vector<ProfileResult>& results) {
    std::ostringstream out;
    out << std::setprecision(9);
    out << "{\n";
    out << "  \"schema_version\": 1,\n";
    out << "  \"experiment\": "
           "\"J004-relative-memory-preflight\",\n";
    out << "  \"formal_timing_decision\": false,\n";
    out << "  \"gate\": "
           "\"candidate <= 1.25x same-run Lane-E HWRT comparator\",\n";
    out << "  \"lane_e_source_commit\": "
           "\"2911790d8fd1716615a59dc86034e4fea783c9ec\",\n";
    out << "  \"profiles\": [\n";

    bool all_passed = true;
    for (std::size_t profile_index = 0U;
         profile_index < results.size();
         ++profile_index) {
        const auto& result = results[profile_index];
        all_passed = all_passed && result.passed;

        if (profile_index != 0U) out << ",\n";
        out << "    {\n";
        out << "      \"name\": \"" << result.name << "\",\n";
        out << "      \"device\": \""
            << result.candidate.device << "\",\n";
        out << "      \"candidate_bounded\": "
            << (result.candidate.bounded ? "true" : "false")
            << ",\n";
        out << "      \"comparator_bounded\": "
            << (result.comparator.bounded ? "true" : "false")
            << ",\n";
        out << "      \"max_persistent_ratio\": "
            << result.max_persistent_ratio << ",\n";
        out << "      \"max_true_peak_ratio\": "
            << result.max_peak_ratio << ",\n";
        out << "      \"passed\": "
            << (result.passed ? "true" : "false") << ",\n";

        out << "      \"candidate_samples\": [";
        for (std::size_t index = 0U;
             index < result.candidate.samples.size();
             ++index) {
            if (index != 0U) out << ",";
            write_sample(out, result.candidate.samples[index]);
        }
        out << "],\n";

        out << "      \"comparator_samples\": [";
        for (std::size_t index = 0U;
             index < result.comparator.samples.size();
             ++index) {
            if (index != 0U) out << ",";
            write_sample(out, result.comparator.samples[index]);
        }
        out << "]\n";
        out << "    }";
    }

    out << "\n  ],\n";
    out << "  \"all_profiles_passed\": "
        << (all_passed ? "true" : "false") << "\n";
    out << "}\n";
    return out.str();
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto options = parse_options(argc, argv);
        std::vector<ProfileResult> results;
        results.reserve(kProfiles.size());

        for (const auto* profile : kProfiles) {
            std::cerr
                << "J004 memory preflight: "
                << profile << "\n";
            results.push_back(
                compare_profile(
                    options.root,
                    profile,
                    options.validation));
        }

        const auto json = make_json(results);
        if (!options.output.empty()) {
            if (options.output.has_parent_path()) {
                std::filesystem::create_directories(
                    options.output.parent_path());
            }
            std::ofstream file(options.output);
            if (!file) {
                throw std::runtime_error(
                    "cannot open J004 memory-preflight output");
            }
            file << json;
        }
        std::cout << json;

        const auto all_passed = std::all_of(
            results.begin(),
            results.end(),
            [](const ProfileResult& result) {
                return result.passed;
            });

        std::cerr
            << "J004 relative memory eligibility: "
            << (all_passed ? "PASS" : "FAIL")
            << "\n";
        return all_passed ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr
            << "J004 memory preflight fatal: "
            << error.what() << "\n";
        return 1;
    }
}

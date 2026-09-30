#include "j003_snapshot.hpp"
#include "j003_transition.hpp"

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace lane_j = phos::gi::research::lane_j;

namespace {

struct Options {
    std::filesystem::path profile_dir;
    std::filesystem::path output;
};

[[nodiscard]] Options parse_options(int argc, char** argv) {
    Options options{};
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        const auto value = [&](const char* name) -> std::string {
            if (i + 1 >= argc) {
                throw std::runtime_error(std::string("missing value for ") + name);
            }
            return argv[++i];
        };
        if (arg == "--profile-dir") {
            options.profile_dir = value("--profile-dir");
        } else if (arg == "--output") {
            options.output = value("--output");
        } else {
            throw std::runtime_error("unknown argument: " + arg);
        }
    }
    if (options.profile_dir.empty()) {
        throw std::runtime_error("--profile-dir is required");
    }
    return options;
}

[[nodiscard]] std::vector<std::filesystem::path> snapshot_paths(
    const std::filesystem::path& directory) {
    std::vector<std::filesystem::path> paths;
    for (std::uint32_t index = 0U; index < 8U; ++index) {
        std::ostringstream name;
        name << "step-0" << index << ".bin";
        const auto path = directory / name.str();
        if (!std::filesystem::exists(path)) {
            throw std::runtime_error("missing snapshot: " + path.string());
        }
        paths.push_back(path);
    }
    return paths;
}

[[nodiscard]] std::pair<std::uint32_t, std::uint32_t> occupancy(
    const lane_j::ClusterTransitionState& state) {
    std::uint32_t low = std::numeric_limits<std::uint32_t>::max();
    std::uint32_t high = 0U;
    for (const auto& cluster : state.clusters()) {
        const auto size = static_cast<std::uint32_t>(cluster.triangles.size());
        low = std::min(low, size);
        high = std::max(high, size);
    }
    return {low, high};
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto options = parse_options(argc, argv);
        const auto paths = snapshot_paths(options.profile_dir);
        const auto first = lane_j::load_j002_snapshot(paths.front());
        lane_j::ClusterTransitionState state(first);

        std::ostringstream json;
        json << "{\n";
        json << "  \"schema_version\": 1,\n";
        json << "  \"experiment\": \"J003-cpp-transition-replay\",\n";
        json << "  \"rows\": [\n";

        const auto [initial_min, initial_max] = occupancy(state);
        json << "    {\"index\":0,\"cluster_count\":" << state.clusters().size()
             << ",\"dirty_cluster_count\":0,\"rebuilt_triangle_count\":0"
             << ",\"split_count\":0,\"merge_count\":0"
             << ",\"retired_empty_cluster_count\":0"
             << ",\"unaffected_cluster_rebuild_count\":0"
             << ",\"occupancy_min\":" << initial_min
             << ",\"occupancy_max\":" << initial_max << "}";

        std::uint64_t total_splits = 0U;
        std::uint64_t total_merges = 0U;
        std::uint64_t total_retires = 0U;
        for (std::uint32_t index = 1U; index < paths.size(); ++index) {
            const auto triangles = lane_j::load_j002_snapshot(paths[index]);
            const auto stats = state.update(triangles);
            if (stats.unaffected_cluster_rebuild_count != 0U) {
                throw std::runtime_error("unaffected cluster mutation detected");
            }
            if (stats.occupancy_max > lane_j::kClusterMaximum ||
                stats.occupancy_min == 0U) {
                throw std::runtime_error("cluster occupancy invariant failed");
            }
            total_splits += stats.split_count;
            total_merges += stats.merge_count;
            total_retires += stats.retired_empty_cluster_count;

            json << ",\n    {\"index\":" << index
                 << ",\"cluster_count\":" << stats.cluster_count
                 << ",\"dirty_cluster_count\":" << stats.dirty_cluster_count
                 << ",\"changed_triangle_count\":" << stats.changed_triangle_count
                 << ",\"rebuilt_triangle_count\":" << stats.rebuilt_triangle_count
                 << ",\"split_count\":" << stats.split_count
                 << ",\"merge_count\":" << stats.merge_count
                 << ",\"retired_empty_cluster_count\":"
                 << stats.retired_empty_cluster_count
                 << ",\"unaffected_cluster_rebuild_count\":"
                 << stats.unaffected_cluster_rebuild_count
                 << ",\"occupancy_min\":" << stats.occupancy_min
                 << ",\"occupancy_max\":" << stats.occupancy_max << "}";
        }

        json << "\n  ],\n";
        json << "  \"total_split_count\": " << total_splits << ",\n";
        json << "  \"total_merge_count\": " << total_merges << ",\n";
        json << "  \"total_retired_empty_cluster_count\": " << total_retires << "\n";
        json << "}\n";

        if (!options.output.empty()) {
            if (options.output.has_parent_path()) {
                std::filesystem::create_directories(options.output.parent_path());
            }
            std::ofstream file(options.output);
            if (!file) {
                throw std::runtime_error("cannot open output");
            }
            file << json.str();
        }

        std::cout << json.str();
        std::cout << "J003 C++ transition replay PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "fatal: " << error.what() << "\n";
        return 1;
    }
}

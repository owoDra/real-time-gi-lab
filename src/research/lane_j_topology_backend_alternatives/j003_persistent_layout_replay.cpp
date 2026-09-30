#include "j003_persistent_layout.hpp"
#include "j003_snapshot.hpp"
#include "j003_transition.hpp"

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
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

Options parse_options(int argc, char** argv) {
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

std::vector<std::filesystem::path> snapshot_paths(
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

} // namespace

int main(int argc, char** argv) {
    try {
        const auto options = parse_options(argc, argv);
        const auto paths = snapshot_paths(options.profile_dir);
        const auto first = lane_j::load_j002_snapshot(paths.front());

        lane_j::ClusterTransitionState state(first);
        lane_j::PersistentClusterLayout layout(state);

        std::ostringstream json;
        json << "{\n";
        json << "  \"schema_version\": 1,\n";
        json << "  \"experiment\": \"J003-persistent-layout-replay\",\n";
        json << "  \"rows\": [\n";
        json << "    {\"index\":0"
             << ",\"slot_capacity\":" << layout.slot_capacity()
             << ",\"active_cluster_count\":" << layout.active_cluster_count()
             << ",\"dirty_slot_count\":" << layout.active_cluster_count()
             << ",\"upper_rebuild_node_count\":" << layout.upper_node_count()
             << ",\"upper_refit_node_count\":0"
             << ",\"resized\":false"
             << ",\"candidate_persistent_logical_bytes\":"
             << layout.candidate_persistent_logical_bytes()
             << ",\"resize_old_new_overlap_logical_bytes\":0}";

        std::uint64_t resize_count = 0U;
        std::uint64_t total_dirty_slots = layout.active_cluster_count();
        std::uint64_t total_upper_refits = 0U;
        std::uint64_t total_upper_rebuilds = layout.upper_node_count();

        for (std::uint32_t index = 1U; index < paths.size(); ++index) {
            const auto triangles = lane_j::load_j002_snapshot(paths[index]);
            const auto transition = state.update(triangles);
            const auto update = layout.synchronize(state, transition);

            resize_count += update.resized ? 1U : 0U;
            total_dirty_slots += update.dirty_slot_count;
            total_upper_refits += update.upper_refit_node_count;
            total_upper_rebuilds += update.upper_rebuild_node_count;

            json << ",\n    {\"index\":" << index
                 << ",\"slot_capacity\":" << update.slot_capacity
                 << ",\"active_cluster_count\":" << update.active_cluster_count
                 << ",\"dirty_slot_count\":" << update.dirty_slot_count
                 << ",\"upper_rebuild_node_count\":"
                 << update.upper_rebuild_node_count
                 << ",\"upper_refit_node_count\":"
                 << update.upper_refit_node_count
                 << ",\"resized\":" << (update.resized ? "true" : "false")
                 << ",\"candidate_persistent_logical_bytes\":"
                 << update.candidate_persistent_logical_bytes
                 << ",\"resize_old_new_overlap_logical_bytes\":"
                 << update.resize_old_new_overlap_logical_bytes
                 << "}";
        }

        json << "\n  ],\n";
        json << "  \"resize_count\": " << resize_count << ",\n";
        json << "  \"total_dirty_slot_updates\": " << total_dirty_slots << ",\n";
        json << "  \"total_upper_refit_nodes\": " << total_upper_refits << ",\n";
        json << "  \"total_upper_rebuild_nodes\": " << total_upper_rebuilds << "\n";
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
        std::cout << "J003 persistent layout replay PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "fatal: " << error.what() << "\n";
        return 1;
    }
}

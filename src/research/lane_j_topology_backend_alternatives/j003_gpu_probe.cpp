#include "j003_clustered_bvh.hpp"
#include "j003_gpu_runtime.hpp"
#include "j003_reference.hpp"
#include "j003_snapshot.hpp"
#include "vk_context.hpp"

#include <cstddef>
#include <cstdint>
#include <cstdlib>
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
    std::filesystem::path snapshot;
    std::filesystem::path output;
    std::size_t ray_count{4096U};
    bool validation{false};
};

[[nodiscard]] std::string json_escape(const std::string& input) {
    std::ostringstream out;
    for (const char c : input) {
        switch (c) {
        case '\\': out << "\\\\"; break;
        case '"': out << "\\\""; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default: out << c; break;
        }
    }
    return out.str();
}

[[nodiscard]] Options parse_options(int argc, char** argv) {
    Options options{};
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        const auto require_value = [&](const char* name) -> std::string {
            if (i + 1 >= argc) {
                throw std::runtime_error(
                    std::string("missing value for ") + name);
            }
            return argv[++i];
        };

        if (arg == "--snapshot") {
            options.snapshot = require_value("--snapshot");
        } else if (arg == "--output") {
            options.output = require_value("--output");
        } else if (arg == "--ray-count") {
            const auto value = std::stoull(require_value("--ray-count"));
            if (value == 0U ||
                value > std::numeric_limits<std::uint32_t>::max()) {
                throw std::runtime_error("--ray-count is out of range");
            }
            options.ray_count = static_cast<std::size_t>(value);
        } else if (arg == "--validation") {
            options.validation = true;
        } else if (arg == "--help" || arg == "-h") {
            std::cout
                << "Usage: phos-lane-j-j003-probe "
                   "--snapshot <step.bin> [--output result.json] "
                   "[--ray-count N] [--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error("unknown argument: " + arg);
        }
    }
    if (options.snapshot.empty()) {
        throw std::runtime_error("--snapshot is required");
    }
    return options;
}

[[nodiscard]] std::string make_json(
    const phos::gi::VulkanContext& context,
    const lane_j::ClusteredBvhData& bvh,
    const lane_j::GpuTraversalResult& gpu,
    std::size_t ray_count,
    std::uint64_t upper_visits,
    std::uint64_t micro_visits,
    std::uint64_t triangle_tests,
    std::uint64_t hit_mismatches,
    std::uint64_t runtime_errors) {
    std::ostringstream out;
    out << "{\n";
    out << "  \"schema_version\": 1,\n";
    out << "  \"experiment\": \"J003-target-gpu-traversal-probe\",\n";
    out << "  \"formal_timing_decision\": false,\n";
    out << "  \"device_name\": \"" << json_escape(context.device_name())
        << "\",\n";
    out << "  \"primitive_count\": " << bvh.triangles.size() << ",\n";
    out << "  \"cluster_count\": " << bvh.summary.cluster_count << ",\n";
    out << "  \"occupancy_min\": " << bvh.summary.occupancy_min << ",\n";
    out << "  \"occupancy_max\": " << bvh.summary.occupancy_max << ",\n";
    out << "  \"upper_node_count\": " << bvh.summary.upper_node_count << ",\n";
    out << "  \"micro_node_count\": " << bvh.summary.micro_node_count << ",\n";
    out << "  \"ray_count\": " << ray_count << ",\n";
    out << "  \"hit_mismatch_count\": " << hit_mismatches << ",\n";
    out << "  \"traversal_runtime_error_count\": " << runtime_errors << ",\n";
    out << "  \"cluster_node_visits\": " << upper_visits << ",\n";
    out << "  \"micro_node_visits\": " << micro_visits << ",\n";
    out << "  \"exact_triangle_tests\": " << triangle_tests << ",\n";
    out << "  \"diagnostic_traversal_gpu_us\": " << gpu.traversal_gpu_us << ",\n";
    out << "  \"candidate_persistent_bytes\": "
        << gpu.candidate_persistent_bytes << ",\n";
    out << "  \"validation_harness_bytes\": "
        << gpu.validation_harness_bytes << ",\n";
    out << "  \"allocations\": [\n";
    for (std::size_t i = 0U; i < gpu.allocations.size(); ++i) {
        const auto& allocation = gpu.allocations[i];
        out << "    {\"name\": \"" << json_escape(allocation.name)
            << "\", \"allocation_class\": \""
            << json_escape(allocation.allocation_class)
            << "\", \"logical_bytes\": " << allocation.logical_bytes
            << ", \"allocation_bytes\": " << allocation.allocation_bytes
            << "}";
        if (i + 1U != gpu.allocations.size()) {
            out << ",";
        }
        out << "\n";
    }
    out << "  ]\n";
    out << "}\n";
    return out.str();
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto options = parse_options(argc, argv);
        const auto triangles = lane_j::load_j002_snapshot(options.snapshot);
        const auto bvh = lane_j::build_initial_clustered_bvh(triangles);
        const auto rays =
            lane_j::make_validation_rays(triangles, options.ray_count);

        std::vector<lane_j::Hit> expected;
        expected.reserve(rays.size());
        std::vector<lane_j::GpuRay> gpu_rays;
        gpu_rays.reserve(rays.size());
        for (const auto& ray : rays) {
            expected.push_back(lane_j::trace_reference(triangles, ray));
            gpu_rays.push_back(lane_j::to_gpu_ray(ray));
        }

        phos::gi::VulkanContext context(options.validation);
        const auto shader_path =
            std::filesystem::path(PHOS_GI_LANE_J_SHADER_DIR) /
            "j003_traverse.spv";
        const auto gpu = lane_j::run_gpu_traversal_probe(
            context,
            bvh,
            gpu_rays,
            shader_path);

        if (gpu.hits.size() != expected.size()) {
            throw std::runtime_error("GPU hit count mismatch");
        }

        std::uint64_t mismatches = 0U;
        std::uint64_t runtime_errors = 0U;
        std::uint64_t upper_visits = 0U;
        std::uint64_t micro_visits = 0U;
        std::uint64_t triangle_tests = 0U;
        for (std::size_t i = 0U; i < gpu.hits.size(); ++i) {
            if (!lane_j::equivalent_hit(expected[i], gpu.hits[i])) {
                ++mismatches;
            }
            upper_visits += gpu.hits[i].stats[0];
            micro_visits += gpu.hits[i].stats[1];
            triangle_tests += gpu.hits[i].stats[2];
            runtime_errors += gpu.hits[i].stats[3] != 0U ? 1U : 0U;
        }

        const auto json = make_json(
            context,
            bvh,
            gpu,
            rays.size(),
            upper_visits,
            micro_visits,
            triangle_tests,
            mismatches,
            runtime_errors);

        if (!options.output.empty()) {
            if (options.output.has_parent_path()) {
                std::filesystem::create_directories(
                    options.output.parent_path());
            }
            std::ofstream output(options.output);
            if (!output) {
                throw std::runtime_error(
                    "cannot open output: " + options.output.string());
            }
            output << json;
        }

        std::cout
            << "J003 target-GPU traversal probe\n"
            << "GPU: " << context.device_name() << "\n"
            << "Triangles: " << triangles.size()
            << ", clusters: " << bvh.summary.cluster_count
            << ", upper nodes: " << bvh.summary.upper_node_count
            << ", micro nodes: " << bvh.summary.micro_node_count << "\n"
            << "Rays: " << rays.size()
            << ", hit mismatches: " << mismatches
            << ", runtime errors: " << runtime_errors << "\n"
            << "Diagnostic traversal GPU us: "
            << gpu.traversal_gpu_us << "\n";

        if (mismatches != 0U || runtime_errors != 0U) {
            return 2;
        }
        std::cout << "J003 target-GPU traversal probe PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "fatal: " << error.what() << "\n";
        return 1;
    }
}

#include "j003_persistent_gpu.hpp"
#include "j003_persistent_layout.hpp"
#include "j003_reference.hpp"
#include "j003_snapshot.hpp"
#include "j003_transition.hpp"
#include "vk_context.hpp"

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace lane_j = phos::gi::research::lane_j;

namespace {

struct Options {
    std::filesystem::path profile_dir;
    std::filesystem::path output;
    std::size_t ray_count{4096U};
    bool validation{false};
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
        } else if (arg == "--ray-count") {
            const auto parsed = std::stoull(value("--ray-count"));
            if (parsed == 0U ||
                parsed > std::numeric_limits<std::uint32_t>::max()) {
                throw std::runtime_error("--ray-count out of range");
            }
            options.ray_count = static_cast<std::size_t>(parsed);
        } else if (arg == "--validation") {
            options.validation = true;
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

struct MismatchDetail {
    std::size_t ray_index{};
    lane_j::Hit expected{};
    lane_j::GpuHit actual{};
};

struct ValidationSummary {
    std::uint64_t hit_mismatches{};
    std::uint64_t runtime_errors{};
    std::uint64_t upper_visits{};
    std::uint64_t micro_visits{};
    std::uint64_t triangle_tests{};
    std::vector<MismatchDetail> mismatches;
};

[[nodiscard]] ValidationSummary validate_hits(
    std::span<const lane_j::Hit> expected,
    std::span<const lane_j::GpuHit> actual) {
    if (expected.size() != actual.size()) {
        throw std::runtime_error("persistent GPU hit count mismatch");
    }
    ValidationSummary result{};
    for (std::size_t index = 0U; index < expected.size(); ++index) {
        if (!lane_j::equivalent_hit(expected[index], actual[index])) {
            ++result.hit_mismatches;
            if (result.mismatches.size() < 16U) {
                result.mismatches.push_back({
                    index,
                    expected[index],
                    actual[index],
                });
            }
        }
        result.runtime_errors += actual[index].stats[3] != 0U ? 1U : 0U;
        result.upper_visits += actual[index].stats[0];
        result.micro_visits += actual[index].stats[1];
        result.triangle_tests += actual[index].stats[2];
    }
    return result;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto options = parse_options(argc, argv);
        const auto paths = snapshot_paths(options.profile_dir);
        const auto shader_path =
            std::filesystem::path(PHOS_GI_LANE_J_SHADER_DIR) /
            "j003_traverse.spv";

        const auto first = lane_j::load_j002_snapshot(paths.front());
        lane_j::ClusterTransitionState transition_state(first);
        lane_j::PersistentClusterLayout layout(transition_state);

        phos::gi::VulkanContext context(options.validation);
        lane_j::PersistentGpuState gpu(context, layout);

        std::ostringstream json;
        json << "{\n";
        json << "  \"schema_version\": 1,\n";
        json << "  \"experiment\": \"J003-persistent-gpu-replay\",\n";
        json << "  \"formal_timing_decision\": false,\n";
        json << "  \"device_name\": \"" << context.device_name() << "\",\n";
        json << "  \"rows\": [\n";

        std::uint64_t total_mismatches = 0U;
        std::uint64_t total_runtime_errors = 0U;
        std::size_t max_true_peak = gpu.persistent_allocation_bytes();

        for (std::uint32_t step = 0U; step < paths.size(); ++step) {
            const auto triangles =
                step == 0U ? first : lane_j::load_j002_snapshot(paths[step]);

            lane_j::PersistentGpuSyncResult sync{};
            if (step != 0U) {
                const auto transition = transition_state.update(triangles);
                const auto layout_update =
                    layout.synchronize(transition_state, transition);
                sync = gpu.synchronize(layout, layout_update);
                max_true_peak = std::max(
                    max_true_peak,
                    sync.true_peak_resident_bytes);
            } else {
                sync.candidate_persistent_allocation_bytes =
                    gpu.persistent_allocation_bytes();
                sync.true_peak_resident_bytes =
                    sync.candidate_persistent_allocation_bytes;
            }

            const auto rays =
                lane_j::make_validation_rays(triangles, options.ray_count);
            std::vector<lane_j::Hit> expected;
            std::vector<lane_j::GpuRay> gpu_rays;
            expected.reserve(rays.size());
            gpu_rays.reserve(rays.size());
            for (const auto& ray : rays) {
                expected.push_back(
                    lane_j::trace_reference(triangles, ray));
                gpu_rays.push_back(lane_j::to_gpu_ray(ray));
            }

            const auto traversal =
                gpu.trace(layout, gpu_rays, shader_path);
            const auto validation =
                validate_hits(expected, traversal.hits);
            total_mismatches += validation.hit_mismatches;
            total_runtime_errors += validation.runtime_errors;

            for (const auto& mismatch : validation.mismatches) {
                const auto& expected_hit = mismatch.expected;
                const auto& actual_hit = mismatch.actual;
                std::cerr
                    << "J003 mismatch step=" << step
                    << " ray=" << mismatch.ray_index
                    << " expected_hit=" << (expected_hit.hit ? 1 : 0)
                    << " expected_t=" << expected_hit.t
                    << " expected_primitive=" << expected_hit.primitive_id
                    << " expected_material=" << expected_hit.material_id
                    << " expected_instance=" << expected_hit.instance_id
                    << " expected_normal=("
                    << expected_hit.normal.x << ","
                    << expected_hit.normal.y << ","
                    << expected_hit.normal.z << ")"
                    << " actual_hit=" << actual_hit.ids[3]
                    << " actual_t=" << actual_hit.t_normal[0]
                    << " actual_primitive=" << actual_hit.ids[0]
                    << " actual_material=" << actual_hit.ids[1]
                    << " actual_instance=" << actual_hit.ids[2]
                    << " actual_normal=("
                    << actual_hit.t_normal[1] << ","
                    << actual_hit.t_normal[2] << ","
                    << actual_hit.t_normal[3] << ")"
                    << " visits=("
                    << actual_hit.stats[0] << ","
                    << actual_hit.stats[1] << ","
                    << actual_hit.stats[2] << ")"
                    << " runtime_error=" << actual_hit.stats[3]
                    << "\n";
            }

            if (step != 0U) {
                json << ",\n";
            }
            json << "    {\"index\":" << step
                 << ",\"primitive_count\":" << triangles.size()
                 << ",\"slot_capacity\":" << layout.slot_capacity()
                 << ",\"active_cluster_count\":" << layout.active_cluster_count()
                 << ",\"upper_node_count\":" << layout.upper_node_count()
                 << ",\"upload_region_count\":" << sync.upload_region_count
                 << ",\"uploaded_logical_bytes\":" << sync.uploaded_logical_bytes
                 << ",\"candidate_persistent_allocation_bytes\":"
                 << sync.candidate_persistent_allocation_bytes
                 << ",\"resize_old_new_overlap_allocation_bytes\":"
                 << sync.resize_old_new_overlap_allocation_bytes
                 << ",\"max_staging_allocation_bytes\":"
                 << sync.max_staging_allocation_bytes
                 << ",\"true_peak_resident_bytes\":"
                 << sync.true_peak_resident_bytes
                 << ",\"validation_harness_allocation_bytes\":"
                 << traversal.validation_harness_allocation_bytes
                 << ",\"hit_mismatch_count\":"
                 << validation.hit_mismatches
                 << ",\"traversal_runtime_error_count\":"
                 << validation.runtime_errors
                 << ",\"cluster_node_visits\":"
                 << validation.upper_visits
                 << ",\"micro_node_visits\":"
                 << validation.micro_visits
                 << ",\"exact_triangle_tests\":"
                 << validation.triangle_tests
                 << ",\"diagnostic_traversal_gpu_us\":"
                 << traversal.traversal_gpu_us
                 << ",\"mismatches\":[";
            for (std::size_t mismatch_index = 0U;
                 mismatch_index < validation.mismatches.size();
                 ++mismatch_index) {
                const auto& mismatch =
                    validation.mismatches[mismatch_index];
                if (mismatch_index != 0U) {
                    json << ",";
                }
                json << "{\"ray_index\":" << mismatch.ray_index
                     << ",\"expected_hit\":"
                     << (mismatch.expected.hit ? "true" : "false")
                     << ",\"expected_t\":" << mismatch.expected.t
                     << ",\"expected_primitive\":"
                     << mismatch.expected.primitive_id
                     << ",\"expected_material\":"
                     << mismatch.expected.material_id
                     << ",\"expected_instance\":"
                     << mismatch.expected.instance_id
                     << ",\"actual_hit\":"
                     << (mismatch.actual.ids[3] != 0U ? "true" : "false")
                     << ",\"actual_t\":" << mismatch.actual.t_normal[0]
                     << ",\"actual_primitive\":"
                     << mismatch.actual.ids[0]
                     << ",\"actual_material\":"
                     << mismatch.actual.ids[1]
                     << ",\"actual_instance\":"
                     << mismatch.actual.ids[2]
                     << ",\"actual_upper_visits\":"
                     << mismatch.actual.stats[0]
                     << ",\"actual_micro_visits\":"
                     << mismatch.actual.stats[1]
                     << ",\"actual_triangle_tests\":"
                     << mismatch.actual.stats[2]
                     << "}";
            }
            json << "]}";
        }

        json << "\n  ],\n";
        json << "  \"total_hit_mismatch_count\": "
             << total_mismatches << ",\n";
        json << "  \"total_traversal_runtime_error_count\": "
             << total_runtime_errors << ",\n";
        json << "  \"max_candidate_true_peak_resident_bytes\": "
             << max_true_peak << "\n";
        json << "}\n";

        if (!options.output.empty()) {
            if (options.output.has_parent_path()) {
                std::filesystem::create_directories(
                    options.output.parent_path());
            }
            std::ofstream file(options.output);
            if (!file) {
                throw std::runtime_error("cannot open output");
            }
            file << json.str();
        }

        std::cout << json.str();
        if (total_mismatches != 0U ||
            total_runtime_errors != 0U) {
            return 2;
        }
        std::cout << "J003 persistent GPU replay PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "fatal: " << error.what() << "\n";
        return 1;
    }
}

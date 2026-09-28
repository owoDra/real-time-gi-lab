#include "b002_compute.hpp"
#include "b002_gpu_layout.hpp"
#include "b002_hwrt.hpp"
#include "b002_replay.hpp"
#include "b002_scene.hpp"
#include "b002_vulkan.hpp"
#include "gpu_software_bvh.hpp"
#include "hierarchical_stratabrick.hpp"
#include "software_bvh.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <numeric>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace phos::gi::research::lane_b {
namespace {

using Clock = std::chrono::steady_clock;

struct Cli {
    std::filesystem::path scene{
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"};
    std::filesystem::path lane_a_artifact{
        "out/research/lane-a-split-rc/001-representative-producer/"
        "20260928T143212Z"};
    std::uint32_t iterations{30};
    std::uint32_t build_repeats{3};
    bool validation{};
};

struct PreparedCase {
    std::string name;
    std::uint64_t workload_id{};
    std::vector<Ray> rays;
    std::vector<GpuRay> gpu_rays;
    std::vector<Hit> reference_hits;
    std::uint64_t reference_semantic_checksum{};
    double stream_parse_us{};
    double replay_convert_us{};
};

struct ResultRow {
    std::string workload;
    std::string candidate;
    std::uint64_t workload_id{};
    std::size_t rays{};
    std::uint32_t iterations{};
    std::size_t mismatches{};
    std::size_t runtime_errors{};
    std::uint64_t semantic_checksum{};
    double stream_parse_us{};
    double replay_convert_us{};
    double scene_load_us{};
    double setup_wall_us{};
    double build_cpu_us{};
    double membership_us{};
    double segment_build_us{};
    double occupancy_us{};
    double pack_cpu_us{};
    double accel_upload_us{};
    double ray_upload_us{};
    double blas_build_us{};
    double tlas_build_us{};
    double trace_us{};
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t explicit_scratch_bytes{};
    std::size_t logical_stack_bytes_per_ray{};
};

struct ValidationResult {
    std::size_t mismatches{};
    std::size_t runtime_errors{};
    std::uint64_t semantic_checksum{};
};

[[nodiscard]] double elapsed_us(Clock::time_point start) {
    return std::chrono::duration<double, std::micro>(
        Clock::now() - start).count();
}

[[nodiscard]] Cli parse_cli(int argc, char** argv) {
    Cli cli;
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        const auto value = [&](const char* option) -> std::string {
            if (index + 1 >= argc) {
                throw std::runtime_error(
                    std::string(option) + " requires a value");
            }
            return argv[++index];
        };

        if (argument == "--scene") {
            cli.scene = value("--scene");
        } else if (argument == "--lane-a-artifact") {
            cli.lane_a_artifact = value("--lane-a-artifact");
        } else if (argument == "--iterations") {
            cli.iterations = static_cast<std::uint32_t>(
                std::stoul(value("--iterations")));
        } else if (argument == "--build-repeats") {
            cli.build_repeats = static_cast<std::uint32_t>(
                std::stoul(value("--build-repeats")));
        } else if (argument == "--validation") {
            cli.validation = true;
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-b-b002 "
                   "[--scene path] [--lane-a-artifact path] "
                   "[--iterations N] [--build-repeats N] [--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error(
                "Unknown B002 argument: " + argument);
        }
    }

    if (cli.iterations == 0 || cli.iterations > 255 ||
        cli.build_repeats == 0) {
        throw std::runtime_error(
            "B002 iterations must be 1..255 and build-repeats positive");
    }
    return cli;
}

[[nodiscard]] std::uint64_t fnv_add(
    std::uint64_t hash,
    std::uint32_t value) noexcept {
    for (int byte = 0; byte < 4; ++byte) {
        hash ^= static_cast<unsigned char>(
            (value >> (byte * 8)) & 0xffU);
        hash *= 1099511628211ULL;
    }
    return hash;
}

[[nodiscard]] std::uint64_t semantic_checksum(
    std::span<const Hit> hits) noexcept {
    std::uint64_t hash = 14695981039346656037ULL;
    for (const auto& hit : hits) {
        hash = fnv_add(hash, hit.hit ? 1U : 0U);
        hash = fnv_add(hash, hit.primitive_id);
        hash = fnv_add(hash, hit.material_id);
        hash = fnv_add(hash, hit.instance_id);
        if (hit.hit) {
            hash = fnv_add(hash, std::bit_cast<std::uint32_t>(hit.t));
            hash = fnv_add(hash, std::bit_cast<std::uint32_t>(hit.normal.x));
            hash = fnv_add(hash, std::bit_cast<std::uint32_t>(hit.normal.y));
            hash = fnv_add(hash, std::bit_cast<std::uint32_t>(hit.normal.z));
        }
    }
    return hash;
}

[[nodiscard]] ValidationResult validate_gpu_hits(
    std::span<const Hit> expected,
    std::span<const GpuHit> actual) {
    if (expected.size() != actual.size()) {
        throw std::runtime_error(
            "B002 GPU hit count differs from reference");
    }

    ValidationResult result;
    std::vector<Hit> canonical;
    canonical.reserve(actual.size());
    for (std::size_t index = 0; index < actual.size(); ++index) {
        if (actual[index].metadata[3] > 1U) {
            ++result.runtime_errors;
            ++result.mismatches;
            canonical.push_back({});
            continue;
        }
        const auto hit = from_gpu_hit(actual[index]);
        if (!equivalent_hit(expected[index], hit)) {
            ++result.mismatches;
            canonical.push_back(hit);
        } else {
            // Hash the shared-contract canonical representative after proving
            // that the candidate hit is equivalent within B001 tolerances.
            // This makes equal checksums meaningful across architectures even
            // when their floating-point hit values differ by allowed ulps.
            canonical.push_back(expected[index]);
        }
    }
    result.semantic_checksum = semantic_checksum(canonical);
    return result;
}

void verify_reference_sample(
    const B002Scene& scene,
    const SoftwareBvh& reference,
    std::span<const Ray> rays) {
    const std::size_t samples = std::min<std::size_t>(64, rays.size());
    for (std::size_t sample = 0; sample < samples; ++sample) {
        const auto index = sample * rays.size() / samples;
        const auto brute =
            trace_reference(scene.triangles, rays[index]);
        const auto accelerated = reference.trace(rays[index]);
        if (!equivalent_hit(brute, accelerated)) {
            throw std::runtime_error(
                "B002 CPU reference BVH diverged from brute-force contract");
        }
    }
}

[[nodiscard]] PreparedCase prepare_case(
    const std::filesystem::path& artifact_root,
    std::string_view name,
    const B002Scene& scene,
    const SoftwareBvh& reference) {
    const auto path =
        artifact_root / std::string(name) / "stream-v1.bin";

    auto start = Clock::now();
    auto stream = load_lane_a_stream_v1(path);
    const auto parse_us = elapsed_us(start);

    for (const auto& item : stream.items) {
        if (item.surface_id >= scene.triangles.size() ||
            scene.triangles[item.surface_id].primitive_id !=
                item.surface_id) {
            throw std::runtime_error(
                "B002 scene primitive order is not aligned with Lane A surface_id");
        }
    }

    start = Clock::now();
    auto rays = lane_a_replay_rays(stream);
    std::vector<GpuRay> gpu_rays;
    gpu_rays.reserve(rays.size());
    for (const auto ray : rays) {
        gpu_rays.push_back(to_gpu_ray(ray));
    }
    const auto convert_us = elapsed_us(start);

    verify_reference_sample(scene, reference, rays);

    std::vector<Hit> reference_hits;
    reference_hits.reserve(rays.size());
    for (const auto ray : rays) {
        reference_hits.push_back(reference.trace(ray));
    }
    const auto checksum = semantic_checksum(reference_hits);

    return {
        std::string(name),
        stream.header.workload_id,
        std::move(rays),
        std::move(gpu_rays),
        std::move(reference_hits),
        checksum,
        parse_us,
        convert_us,
    };
}

[[nodiscard]] double measure_software_build(
    const std::vector<Triangle>& triangles,
    std::uint32_t repeats) {
    std::vector<double> samples;
    samples.reserve(repeats);
    for (std::uint32_t repeat = 0; repeat < repeats; ++repeat) {
        const auto start = Clock::now();
        GpuSoftwareBvhData build(triangles);
        volatile auto root = build.root();
        (void)root;
        samples.push_back(elapsed_us(start));
    }
    return median_us(std::move(samples));
}

struct HierarchyBuildMeasurement {
    double total_us{};
    double membership_us{};
    double segment_build_us{};
    double occupancy_us{};
};

[[nodiscard]] HierarchyBuildMeasurement measure_hierarchy_build(
    const std::vector<Triangle>& triangles,
    float segment_size,
    std::uint32_t repeats) {
    std::vector<double> total;
    std::vector<double> membership;
    std::vector<double> segment;
    std::vector<double> occupancy;
    total.reserve(repeats);
    membership.reserve(repeats);
    segment.reserve(repeats);
    occupancy.reserve(repeats);

    for (std::uint32_t repeat = 0; repeat < repeats; ++repeat) {
        const auto start = Clock::now();
        HierarchicalStrataBrick build(triangles, segment_size);
        total.push_back(elapsed_us(start));
        membership.push_back(
            build.build_stats().membership_generation_us);
        segment.push_back(
            build.build_stats().segment_construction_us);
        occupancy.push_back(
            build.build_stats().occupancy_bounds_us);
    }
    return {
        median_us(std::move(total)),
        median_us(std::move(membership)),
        median_us(std::move(segment)),
        median_us(std::move(occupancy)),
    };
}

[[nodiscard]] std::string json_escape(std::string_view value) {
    std::string output;
    output.reserve(value.size());
    for (const char ch : value) {
        switch (ch) {
        case '\\': output += "\\\\"; break;
        case '"': output += "\\\""; break;
        case '\n': output += "\\n"; break;
        case '\r': output += "\\r"; break;
        case '\t': output += "\\t"; break;
        default:
            if (static_cast<unsigned char>(ch) < 0x20U) {
                output += '?';
            } else {
                output += ch;
            }
        }
    }
    return output;
}

[[nodiscard]] std::filesystem::path artifact_root() {
    if (const char* value =
            std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");
        value != nullptr && *value != '\0') {
        return value;
    }
    return
        "out/research/lane-b-traversal/"
        "002-lane-a-exact-stream-traversal/manual";
}

void write_rows(
    const std::filesystem::path& path,
    std::span<const ResultRow> rows) {
    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error(
            "Could not create B002 result CSV: " + path.string());
    }

    output
        << "workload,candidate,workload_id,rays,iterations,mismatches,"
           "runtime_errors,semantic_checksum,stream_parse_us,replay_convert_us,"
           "scene_load_us,setup_wall_us,build_cpu_us,membership_us,"
           "segment_build_us,occupancy_us,pack_cpu_us,accel_upload_us,"
           "ray_upload_us,blas_build_us,tlas_build_us,trace_us,"
           "persistent_bytes,transient_bytes,explicit_scratch_bytes,"
           "logical_stack_bytes_per_ray\n";
    output << std::fixed << std::setprecision(3);

    for (const auto& row : rows) {
        output
            << row.workload << ','
            << row.candidate << ','
            << row.workload_id << ','
            << row.rays << ','
            << row.iterations << ','
            << row.mismatches << ','
            << row.runtime_errors << ','
            << row.semantic_checksum << ','
            << row.stream_parse_us << ','
            << row.replay_convert_us << ','
            << row.scene_load_us << ','
            << row.setup_wall_us << ','
            << row.build_cpu_us << ','
            << row.membership_us << ','
            << row.segment_build_us << ','
            << row.occupancy_us << ','
            << row.pack_cpu_us << ','
            << row.accel_upload_us << ','
            << row.ray_upload_us << ','
            << row.blas_build_us << ','
            << row.tlas_build_us << ','
            << row.trace_us << ','
            << row.persistent_bytes << ','
            << row.transient_bytes << ','
            << row.explicit_scratch_bytes << ','
            << row.logical_stack_bytes_per_ray
            << '\n';
    }
}

void write_correctness_json(
    const std::filesystem::path& path,
    std::span<const PreparedCase> cases,
    std::span<const ResultRow> rows) {
    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error(
            "Could not create B002 correctness JSON");
    }
    std::size_t total_mismatches = 0;
    std::size_t total_runtime_errors = 0;
    for (const auto& row : rows) {
        total_mismatches += row.mismatches;
        total_runtime_errors += row.runtime_errors;
    }

    output
        << "{\n"
        << "  \"shared_hit_contract\": \"B001\",\n"
        << "  \"reference_sample\": \"brute-force parity checked\",\n"
        << "  \"total_mismatches\": " << total_mismatches << ",\n"
        << "  \"total_runtime_errors\": " << total_runtime_errors << ",\n"
        << "  \"cases\": {\n";
    for (std::size_t index = 0; index < cases.size(); ++index) {
        const auto& current = cases[index];
        output
            << "    \"" << current.name << "\": {"
            << "\"workload_id\": " << current.workload_id << ", "
            << "\"rays\": " << current.rays.size() << ", "
            << "\"reference_semantic_checksum\": "
            << current.reference_semantic_checksum
            << "}";
        if (index + 1 != cases.size()) output << ',';
        output << '\n';
    }
    output
        << "  }\n"
        << "}\n";
}

[[nodiscard]] std::vector<GpuTriangle> make_gpu_triangles(
    const B002Scene& scene) {
    std::vector<GpuTriangle> triangles;
    triangles.reserve(scene.triangles.size());
    for (const auto& triangle : scene.triangles) {
        triangles.push_back(to_gpu_triangle(triangle));
    }
    return triangles;
}

} // namespace
} // namespace phos::gi::research::lane_b

int main(int argc, char** argv) {
    using namespace phos::gi::research::lane_b;

    try {
        const auto cli = parse_cli(argc, argv);
        if (!std::filesystem::exists(cli.scene)) {
            throw std::runtime_error(
                "B002 scene not found; run 'mise run assets' first: " +
                cli.scene.string());
        }
        for (const auto name : kB002Cases) {
            const auto path =
                cli.lane_a_artifact /
                std::string(name) /
                "stream-v1.bin";
            if (!std::filesystem::exists(path)) {
                throw std::runtime_error(
                    "B002 accepted Lane A stream not found: " +
                    path.string());
            }
        }

        const auto output_root = artifact_root();
        std::filesystem::create_directories(output_root);

        auto start = Clock::now();
        const auto scene = load_b002_scene(cli.scene);
        const auto scene_load_us = elapsed_us(start);
        const auto segment_size = b002_segment_size(scene);

        SoftwareBvh reference(scene.triangles);
        std::vector<PreparedCase> cases;
        cases.reserve(kB002Cases.size());
        for (const auto name : kB002Cases) {
            cases.push_back(prepare_case(
                cli.lane_a_artifact,
                name,
                scene,
                reference));
        }

        const auto software_build_us =
            measure_software_build(
                scene.triangles,
                cli.build_repeats);
        GpuSoftwareBvhData software_data(scene.triangles);
        const auto software_nodes = software_data.gpu_nodes();

        const auto hierarchy_measurement =
            measure_hierarchy_build(
                scene.triangles,
                segment_size,
                cli.build_repeats);
        HierarchicalStrataBrick hierarchy(
            scene.triangles,
            segment_size);

        start = Clock::now();
        const auto flat = hierarchy.flatten();
        const auto hierarchy_payload =
            make_hierarchical_gpu_payload(flat);
        const auto hierarchy_pack_us = elapsed_us(start);

        const auto gpu_triangles = make_gpu_triangles(scene);

        {
            std::ofstream config(output_root / "b002-config.json");
            if (!config) {
                throw std::runtime_error(
                    "Could not create B002 config JSON");
            }
            config
                << "{\n"
                << "  \"schema_version\": 1,\n"
                << "  \"experiment\": \"002-lane-a-exact-stream-traversal\",\n"
                << "  \"lane_a_measurement_commit\": "
                   "\"8b647ef8dcf1150f86a9d25c039ca48bd7f30b8f\",\n"
                << "  \"lane_a_artifact\": \""
                << json_escape(cli.lane_a_artifact.string()) << "\",\n"
                << "  \"scene\": \""
                << json_escape(cli.scene.string()) << "\",\n"
                << "  \"scene_triangles\": "
                << scene.triangles.size() << ",\n"
                << "  \"scene_diagonal\": "
                << std::setprecision(9) << scene.diagonal << ",\n"
                << "  \"hierarchy_segment_size\": "
                << segment_size << ",\n"
                << "  \"hierarchy_segments\": "
                << flat.segments.size() << ",\n"
                << "  \"hierarchy_memberships\": "
                << hierarchy.membership_count() << ",\n"
                << "  \"hierarchy_hash_slots\": "
                << hierarchy_payload.hash_table.size() << ",\n"
                << "  \"hierarchy_hash_max_probe\": "
                << hierarchy_payload.hash_max_probe << ",\n"
                << "  \"iterations\": " << cli.iterations << ",\n"
                << "  \"build_repeats\": "
                << cli.build_repeats << ",\n"
                << "  \"validation\": "
                << (cli.validation ? "true" : "false") << "\n"
                << "}\n";
        }

        std::vector<ResultRow> rows;

        std::string selected_device;
        std::string selected_driver;
        std::string selected_driver_info;
        std::uint32_t selected_api_version{};

        {
            B002VulkanContext context(cli.validation);
            selected_device = context.device_name();
            selected_driver = context.driver_name();
            selected_driver_info = context.driver_info();
            selected_api_version = context.api_version();
            std::cout << "GPU: " << context.device_name() << '\n';

            start = Clock::now();
            auto triangle_buffer =
                context.upload_device_buffer(
                    gpu_triangles.data(),
                    gpu_triangles.size() * sizeof(GpuTriangle),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            const auto common_triangle_upload_us =
                elapsed_us(start);

            start = Clock::now();
            auto software_node_buffer =
                context.upload_device_buffer(
                    software_nodes.data(),
                    software_nodes.size() * sizeof(GpuBvhNode),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            auto software_order_buffer =
                context.upload_device_buffer(
                    software_data.ordered_primitives().data(),
                    software_data.ordered_primitives().size() *
                        sizeof(std::uint32_t),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            const auto software_upload_us =
                elapsed_us(start) + common_triangle_upload_us;

            start = Clock::now();
            auto hierarchy_node_buffer =
                context.upload_device_buffer(
                    hierarchy_payload.nodes.data(),
                    hierarchy_payload.nodes.size() *
                        sizeof(GpuBvhNode),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            auto hierarchy_order_buffer =
                context.upload_device_buffer(
                    hierarchy_payload.ordered_primitives.data(),
                    hierarchy_payload.ordered_primitives.size() *
                        sizeof(std::uint32_t),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            auto hierarchy_hash_buffer =
                context.upload_device_buffer(
                    hierarchy_payload.hash_table.data(),
                    hierarchy_payload.hash_table.size() *
                        sizeof(GpuSegmentHashEntry),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            const auto hierarchy_upload_us =
                elapsed_us(start) + common_triangle_upload_us;

            const auto software_persistent =
                static_cast<std::size_t>(
                    triangle_buffer.allocation_size +
                    software_node_buffer.allocation_size +
                    software_order_buffer.allocation_size);
            const auto hierarchy_persistent =
                static_cast<std::size_t>(
                    triangle_buffer.allocation_size +
                    hierarchy_node_buffer.allocation_size +
                    hierarchy_order_buffer.allocation_size +
                    hierarchy_hash_buffer.allocation_size);

            for (const auto& replay : cases) {
                const auto ray_bytes =
                    VkDeviceSize(
                        replay.gpu_rays.size() * sizeof(GpuRay));
                const auto hit_bytes =
                    VkDeviceSize(
                        replay.gpu_rays.size() * sizeof(GpuHit));

                start = Clock::now();
                auto ray_buffer =
                    context.upload_device_buffer(
                        replay.gpu_rays.data(),
                        ray_bytes,
                        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                const auto ray_upload_us = elapsed_us(start);

                auto software_hit_buffer =
                    context.create_device_buffer(
                        hit_bytes,
                        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                std::array<const B002Buffer*, 5> software_bindings{
                    &ray_buffer,
                    &triangle_buffer,
                    &software_node_buffer,
                    &software_order_buffer,
                    &software_hit_buffer,
                };
                B002ComputeTraversal software_runner(
                    context,
                    (std::filesystem::path(
                        PHOS_GI_LANE_B_SHADER_DIR) /
                        "lane_b_b002_software_bvh.spv").string(),
                    software_bindings,
                    sizeof(SoftwareTraversalPush));
                SoftwareTraversalPush software_push{
                    static_cast<std::uint32_t>(
                        replay.gpu_rays.size()),
                    software_data.root(),
                    0,
                    0,
                };
                const auto software_trace_us =
                    software_runner.measure(
                        software_push.ray_count,
                        cli.iterations,
                        &software_push,
                        sizeof(software_push));
                std::vector<GpuHit> software_hits(
                    replay.gpu_rays.size());
                context.download_device_buffer(
                    software_hit_buffer,
                    software_hits.data(),
                    hit_bytes);
                const auto software_validation =
                    validate_gpu_hits(
                        replay.reference_hits,
                        software_hits);

                rows.push_back({
                    replay.name,
                    "software-bvh",
                    replay.workload_id,
                    replay.rays.size(),
                    cli.iterations,
                    software_validation.mismatches,
                    software_validation.runtime_errors,
                    software_validation.semantic_checksum,
                    replay.stream_parse_us,
                    replay.replay_convert_us,
                    scene_load_us,
                    0.0,
                    software_build_us,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    software_upload_us,
                    ray_upload_us,
                    0.0,
                    0.0,
                    software_trace_us,
                    software_persistent,
                    static_cast<std::size_t>(
                        ray_buffer.allocation_size +
                        software_hit_buffer.allocation_size),
                    0,
                    128U * sizeof(std::uint32_t),
                });

                auto hierarchy_hit_buffer =
                    context.create_device_buffer(
                        hit_bytes,
                        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                std::array<const B002Buffer*, 6> hierarchy_bindings{
                    &ray_buffer,
                    &triangle_buffer,
                    &hierarchy_node_buffer,
                    &hierarchy_order_buffer,
                    &hierarchy_hash_buffer,
                    &hierarchy_hit_buffer,
                };
                B002ComputeTraversal hierarchy_runner(
                    context,
                    (std::filesystem::path(
                        PHOS_GI_LANE_B_SHADER_DIR) /
                        "lane_b_b002_hierarchical.spv").string(),
                    hierarchy_bindings,
                    sizeof(HierarchicalTraversalPush));

                HierarchicalTraversalPush hierarchy_push{};
                hierarchy_push.values[0] =
                    static_cast<std::uint32_t>(
                        replay.gpu_rays.size());
                hierarchy_push.values[1] =
                    hierarchy_payload.hash_mask;
                hierarchy_push.values[2] =
                    hierarchy_payload.hash_max_probe;
                const auto max_steps =
                    std::max<std::uint64_t>(
                        64,
                        std::uint64_t(flat.segments.size()) *
                                16U +
                            64U);
                hierarchy_push.values[3] =
                    static_cast<std::uint32_t>(
                        std::min<std::uint64_t>(
                            max_steps,
                            std::numeric_limits<std::uint32_t>::max()));
                hierarchy_push.occupied_min_segment_size[0] =
                    hierarchy_payload.occupied_bounds.min.x;
                hierarchy_push.occupied_min_segment_size[1] =
                    hierarchy_payload.occupied_bounds.min.y;
                hierarchy_push.occupied_min_segment_size[2] =
                    hierarchy_payload.occupied_bounds.min.z;
                hierarchy_push.occupied_min_segment_size[3] =
                    segment_size;
                hierarchy_push.occupied_max_pad[0] =
                    hierarchy_payload.occupied_bounds.max.x;
                hierarchy_push.occupied_max_pad[1] =
                    hierarchy_payload.occupied_bounds.max.y;
                hierarchy_push.occupied_max_pad[2] =
                    hierarchy_payload.occupied_bounds.max.z;

                const auto hierarchy_trace_us =
                    hierarchy_runner.measure(
                        hierarchy_push.values[0],
                        cli.iterations,
                        &hierarchy_push,
                        sizeof(hierarchy_push));
                std::vector<GpuHit> hierarchy_hits(
                    replay.gpu_rays.size());
                context.download_device_buffer(
                    hierarchy_hit_buffer,
                    hierarchy_hits.data(),
                    hit_bytes);
                const auto hierarchy_validation =
                    validate_gpu_hits(
                        replay.reference_hits,
                        hierarchy_hits);

                rows.push_back({
                    replay.name,
                    "hierarchical-stratabrick",
                    replay.workload_id,
                    replay.rays.size(),
                    cli.iterations,
                    hierarchy_validation.mismatches,
                    hierarchy_validation.runtime_errors,
                    hierarchy_validation.semantic_checksum,
                    replay.stream_parse_us,
                    replay.replay_convert_us,
                    scene_load_us,
                    0.0,
                    hierarchy_measurement.total_us,
                    hierarchy_measurement.membership_us,
                    hierarchy_measurement.segment_build_us,
                    hierarchy_measurement.occupancy_us,
                    hierarchy_pack_us,
                    hierarchy_upload_us,
                    ray_upload_us,
                    0.0,
                    0.0,
                    hierarchy_trace_us,
                    hierarchy_persistent,
                    static_cast<std::size_t>(
                        ray_buffer.allocation_size +
                        hierarchy_hit_buffer.allocation_size),
                    0,
                    128U * sizeof(std::uint32_t),
                });

                context.destroy_buffer(
                    hierarchy_hit_buffer);
                context.destroy_buffer(
                    software_hit_buffer);
                context.destroy_buffer(ray_buffer);
            }

            context.destroy_buffer(hierarchy_hash_buffer);
            context.destroy_buffer(hierarchy_order_buffer);
            context.destroy_buffer(hierarchy_node_buffer);
            context.destroy_buffer(software_order_buffer);
            context.destroy_buffer(software_node_buffer);
            context.destroy_buffer(triangle_buffer);
        }

        std::string hwrt_status{"feature-gate-failed"};
        std::string hwrt_reason;
        bool hwrt_correct = false;
        std::unique_ptr<B002VulkanContext> hwrt_context;
        try {
            hwrt_context =
                std::make_unique<B002VulkanContext>(
                    cli.validation,
                    kB002TargetDeviceName,
                    true);
        } catch (const std::exception& error) {
            hwrt_reason = error.what();
        }

        if (hwrt_context) {
            hwrt_status = "features-enabled";
            const auto hwrt_shader =
                (std::filesystem::path(
                    PHOS_GI_LANE_B_SHADER_DIR) /
                    "lane_b_b002_hwrt.spv").string();

            std::vector<double> setup_wall_samples;
            std::vector<double> vertex_upload_samples;
            std::vector<double> metadata_upload_samples;
            std::vector<double> blas_build_samples;
            std::vector<double> tlas_build_samples;
            setup_wall_samples.reserve(cli.build_repeats);
            vertex_upload_samples.reserve(cli.build_repeats);
            metadata_upload_samples.reserve(cli.build_repeats);
            blas_build_samples.reserve(cli.build_repeats);
            tlas_build_samples.reserve(cli.build_repeats);

            std::unique_ptr<B002HwrtTraversal> hwrt;
            for (std::uint32_t repeat = 0;
                 repeat < cli.build_repeats;
                 ++repeat) {
                start = Clock::now();
                auto candidate =
                    std::make_unique<B002HwrtTraversal>(
                        *hwrt_context,
                        scene.triangles,
                        hwrt_shader);
                setup_wall_samples.push_back(
                    elapsed_us(start));
                const auto& setup =
                    candidate->setup_stats();
                vertex_upload_samples.push_back(
                    setup.vertex_upload_us);
                metadata_upload_samples.push_back(
                    setup.metadata_upload_us);
                blas_build_samples.push_back(
                    setup.blas_build_us);
                tlas_build_samples.push_back(
                    setup.tlas_build_us);

                if (repeat + 1U == cli.build_repeats) {
                    hwrt = std::move(candidate);
                }
            }

            if (!hwrt) {
                throw std::runtime_error(
                    "B002 HWRT setup repetition produced no candidate");
            }

            const auto hwrt_setup_wall_us =
                median_us(std::move(setup_wall_samples));
            HwrtSetupStats hwrt_setup =
                hwrt->setup_stats();
            hwrt_setup.vertex_upload_us =
                median_us(std::move(vertex_upload_samples));
            hwrt_setup.metadata_upload_us =
                median_us(std::move(metadata_upload_samples));
            hwrt_setup.blas_build_us =
                median_us(std::move(blas_build_samples));
            hwrt_setup.tlas_build_us =
                median_us(std::move(tlas_build_samples));

            hwrt_status = "usable";
            hwrt_correct = true;

            for (const auto& replay : cases) {
                const auto result =
                    hwrt->trace(
                        replay.gpu_rays,
                        cli.iterations);
                const auto validation =
                    validate_gpu_hits(
                        replay.reference_hits,
                        result.hits);
                if (validation.mismatches != 0 ||
                    validation.runtime_errors != 0) {
                    hwrt_correct = false;
                }

                rows.push_back({
                    replay.name,
                    "hwrt-tlas",
                    replay.workload_id,
                    replay.rays.size(),
                    cli.iterations,
                    validation.mismatches,
                    validation.runtime_errors,
                    validation.semantic_checksum,
                    replay.stream_parse_us,
                    replay.replay_convert_us,
                    scene_load_us,
                    hwrt_setup_wall_us,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    hwrt_setup.vertex_upload_us +
                        hwrt_setup.metadata_upload_us,
                    result.ray_upload_us,
                    hwrt_setup.blas_build_us,
                    hwrt_setup.tlas_build_us,
                    result.trace_us,
                    hwrt_setup.persistent_bytes,
                    result.ray_allocation_bytes +
                        result.hit_allocation_bytes,
                    hwrt_setup.scratch_bytes,
                    0,
                });
            }
        }

        const auto results_path =
            output_root / "b002-results.csv";
        write_rows(results_path, rows);
        write_correctness_json(
            output_root / "b002-correctness.json",
            cases,
            rows);

        // Device provenance is anchored to the exact-device base context used
        // for software/hierarchy. The HWRT context uses the same exact name and
        // additionally requires its feature chain during logical-device creation.
        {
            std::ofstream device(
                output_root / "b002-device.json");
            if (!device) {
                throw std::runtime_error(
                    "Could not create B002 device JSON");
            }
            device
                << "{\n"
                << "  \"target_device\": \""
                << kB002TargetDeviceName << "\",\n"
                << "  \"selected_device\": \""
                << json_escape(selected_device) << "\",\n"
                << "  \"driver_name\": \""
                << json_escape(selected_driver) << "\",\n"
                << "  \"driver_info\": \""
                << json_escape(selected_driver_info) << "\",\n"
                << "  \"api_version\": "
                << selected_api_version << ",\n"
                << "  \"exact_device_match\": "
                << (selected_device == kB002TargetDeviceName
                        ? "true"
                        : "false")
                << ",\n"
                << "  \"hwrt\": {\n"
                << "    \"status\": \"" << hwrt_status << "\",\n"
                << "    \"reason\": \""
                << json_escape(hwrt_reason) << "\",\n"
                << "    \"required_extensions\": ["
                   "\"VK_KHR_acceleration_structure\", "
                   "\"VK_KHR_ray_query\", "
                   "\"VK_KHR_deferred_host_operations\"],\n"
                << "    \"buffer_device_address_required\": true,\n"
                << "    \"blas_tlas_created\": "
                << (hwrt_status == "usable"
                        ? "true"
                        : "false")
                << ",\n"
                << "    \"ray_query_correct\": "
                << (hwrt_correct ? "true" : "false")
                << "\n"
                << "  }\n"
                << "}\n";
        }

        std::size_t total_mismatches = 0;
        std::size_t total_runtime_errors = 0;
        for (const auto& row : rows) {
            total_mismatches += row.mismatches;
            total_runtime_errors += row.runtime_errors;
            std::cout
                << std::fixed
                << std::setprecision(3)
                << "case=" << row.workload
                << " candidate=" << row.candidate
                << " rays=" << row.rays
                << " trace_us=" << row.trace_us
                << " mismatches=" << row.mismatches
                << " persistent_bytes="
                << row.persistent_bytes
                << '\n';
        }

        constexpr std::size_t kRequiredCandidateRows =
            kB002Cases.size() * 3U;
        if (rows.size() != kRequiredCandidateRows) {
            std::cerr
                << "B002 candidate gate: FAIL rows="
                << rows.size()
                << " expected=" << kRequiredCandidateRows
                << " hwrt_status=" << hwrt_status
                << " reason=" << hwrt_reason
                << '\n';
            return 3;
        }

        if (total_mismatches != 0 ||
            total_runtime_errors != 0) {
            std::cerr
                << "B002 correctness: FAIL mismatches="
                << total_mismatches
                << " runtime_errors="
                << total_runtime_errors
                << '\n';
            return 2;
        }

        std::cout
            << "B002 exact-stream correctness: PASS"
            << " hwrt_status=" << hwrt_status
            << " segment_size=" << segment_size
            << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "B002 error: " << error.what() << '\n';
        return 1;
    }
}

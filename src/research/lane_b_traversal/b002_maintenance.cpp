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
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <span>
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
    std::uint32_t iterations{20};
    bool validation{};
};

struct Regime {
    std::string name;
    float delta_x{};
    std::size_t expected_membership_changes{};
};

struct Row {
    std::string regime;
    std::string candidate;
    std::uint32_t moved_instance{};
    std::size_t moved_primitives{};
    float delta_x{};
    std::size_t membership_changes{};
    std::size_t refit_segments{};
    std::size_t rebuilt_segments{};
    std::size_t removed_segments{};
    double geometry_transform_us{};
    double accel_cpu_us{};
    double pack_cpu_us{};
    double geometry_upload_us{};
    double accel_upload_us{};
    std::size_t geometry_update_bytes{};
    std::size_t accel_update_bytes{};
    double blas_update_us{};
    double tlas_update_us{};
    double trace_us{};
    std::size_t mismatches{};
    std::size_t runtime_errors{};
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t explicit_scratch_bytes{};
};

struct Validation {
    std::size_t mismatches{};
    std::size_t runtime_errors{};
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
        } else if (argument == "--validation") {
            cli.validation = true;
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-b-b002-maintenance "
                   "[--scene path] [--lane-a-artifact path] "
                   "[--iterations N] [--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error(
                "Unknown B002 maintenance argument: " + argument);
        }
    }
    if (cli.iterations == 0 || cli.iterations > 255) {
        throw std::runtime_error(
            "B002 maintenance iterations must be 1..255");
    }
    return cli;
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
            output += static_cast<unsigned char>(ch) < 0x20U ? '?' : ch;
        }
    }
    return output;
}

[[nodiscard]] std::filesystem::path output_root() {
    if (const char* value =
            std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");
        value != nullptr && *value != '\0') {
        return value;
    }
    return
        "out/research/lane-b-traversal/"
        "002-lane-a-exact-stream-traversal/manual";
}

struct MovingSelection {
    std::uint32_t instance_id{};
    std::vector<std::uint32_t> primitives;
    Regime bounds_only;
    Regime topology_change;
};

[[nodiscard]] std::vector<std::vector<std::uint32_t>> group_instances(
    const B002Scene& scene) {
    std::uint32_t max_instance = 0;
    for (const auto& triangle : scene.triangles) {
        if (triangle.instance_id == kInvalidId) continue;
        max_instance = std::max(max_instance, triangle.instance_id);
    }

    std::vector<std::vector<std::uint32_t>> groups(
        std::size_t(max_instance) + 1U);
    for (std::uint32_t primitive = 0;
         primitive < scene.triangles.size();
         ++primitive) {
        const auto instance = scene.triangles[primitive].instance_id;
        if (instance != kInvalidId) {
            groups.at(instance).push_back(primitive);
        }
    }
    return groups;
}

[[nodiscard]] std::vector<Triangle> translated(
    const std::vector<Triangle>& source,
    std::span<const std::uint32_t> moved,
    float delta_x) {
    auto output = source;
    const Vec3 delta{delta_x, 0.0F, 0.0F};
    for (const auto primitive : moved) {
        auto& triangle = output.at(primitive);
        triangle.v0 = triangle.v0 + delta;
        triangle.v1 = triangle.v1 + delta;
        triangle.v2 = triangle.v2 + delta;
    }
    return output;
}

[[nodiscard]] double measure_translation(
    std::vector<Triangle>& geometry,
    std::span<const std::uint32_t> moved,
    float delta_x) {
    const Vec3 delta{delta_x, 0.0F, 0.0F};
    const auto start = Clock::now();
    for (const auto primitive : moved) {
        auto& triangle = geometry.at(primitive);
        triangle.v0 = triangle.v0 + delta;
        triangle.v1 = triangle.v1 + delta;
        triangle.v2 = triangle.v2 + delta;
    }
    return elapsed_us(start);
}

[[nodiscard]] Regime find_bounds_only_regime(
    const B002Scene& scene,
    std::span<const std::uint32_t> moved,
    float segment_size) {
    constexpr std::array<float, 6> divisors{
        32.0F, 64.0F, 128.0F, 256.0F, 512.0F, 1024.0F};
    for (const auto divisor : divisors) {
        const float delta = segment_size / divisor;
        auto geometry = translated(
            scene.triangles,
            moved,
            delta);
        HierarchicalStrataBrick candidate(
            scene.triangles,
            segment_size);
        const auto stats = candidate.update(geometry, moved);
        if (stats.membership_changes == 0) {
            return {"bounds-only", delta, 0};
        }
    }
    throw std::runtime_error(
        "B002 could not isolate a bounds-only hierarchical update");
}

[[nodiscard]] Regime find_topology_regime(
    const B002Scene& scene,
    std::span<const std::uint32_t> moved,
    float segment_size) {
    constexpr std::array<float, 5> multipliers{
        1.25F, 2.5F, 5.0F, 10.0F, 20.0F};
    for (const auto multiplier : multipliers) {
        const float delta = segment_size * multiplier;
        auto geometry = translated(
            scene.triangles,
            moved,
            delta);
        HierarchicalStrataBrick candidate(
            scene.triangles,
            segment_size);
        const auto stats = candidate.update(geometry, moved);
        if (stats.membership_changes != 0) {
            return {
                "topology-change",
                delta,
                stats.membership_changes};
        }
    }
    throw std::runtime_error(
        "B002 could not isolate a topology-changing hierarchical update");
}

[[nodiscard]] MovingSelection choose_moving_selection(
    const B002Scene& scene,
    float segment_size) {
    const auto groups = group_instances(scene);
    std::vector<std::uint32_t> candidates;
    candidates.reserve(groups.size());

    // Prefer medium-size real mesh groups so maintenance remains controlled,
    // but choose by mechanism viability only. No timing result participates in
    // this selection.
    for (std::uint32_t instance = 0;
         instance < groups.size();
         ++instance) {
        const auto count = groups[instance].size();
        if (count >= 32U && count <= 2048U) {
            candidates.push_back(instance);
        }
    }
    for (std::uint32_t instance = 0;
         instance < groups.size();
         ++instance) {
        if (groups[instance].empty() ||
            std::find(
                candidates.begin(),
                candidates.end(),
                instance) != candidates.end()) {
            continue;
        }
        candidates.push_back(instance);
    }

    std::string last_error;
    for (const auto instance : candidates) {
        try {
            const auto bounds_only =
                find_bounds_only_regime(
                    scene,
                    groups[instance],
                    segment_size);
            const auto topology_change =
                find_topology_regime(
                    scene,
                    groups[instance],
                    segment_size);
            return {
                instance,
                groups[instance],
                bounds_only,
                topology_change,
            };
        } catch (const std::exception& error) {
            last_error = error.what();
        }
    }

    throw std::runtime_error(
        "B002 could not select a real Sponza mesh supporting both "
        "controlled maintenance regimes; last failure: " +
        last_error);
}

[[nodiscard]] std::vector<GpuTriangle> gpu_triangles(
    const std::vector<Triangle>& triangles) {
    std::vector<GpuTriangle> output;
    output.reserve(triangles.size());
    for (const auto& triangle : triangles) {
        output.push_back(to_gpu_triangle(triangle));
    }
    return output;
}

[[nodiscard]] std::vector<GpuRay> gpu_rays(
    std::span<const Ray> rays) {
    std::vector<GpuRay> output;
    output.reserve(rays.size());
    for (const auto ray : rays) output.push_back(to_gpu_ray(ray));
    return output;
}

[[nodiscard]] std::vector<Hit> reference_hits(
    const std::vector<Triangle>& triangles,
    std::span<const Ray> rays) {
    SoftwareBvh reference(triangles);
    std::vector<Hit> output;
    output.reserve(rays.size());
    for (const auto ray : rays) {
        output.push_back(reference.trace(ray));
    }

    const std::size_t sample_count =
        std::min<std::size_t>(64, rays.size());
    for (std::size_t sample = 0;
         sample < sample_count;
         ++sample) {
        const auto index =
            sample * rays.size() / sample_count;
        const auto brute =
            trace_reference(triangles, rays[index]);
        if (!equivalent_hit(brute, output[index])) {
            throw std::runtime_error(
                "B002 maintenance reference failed brute-force parity");
        }
    }
    return output;
}

[[nodiscard]] Validation validate_hits(
    std::span<const Hit> expected,
    std::span<const GpuHit> actual) {
    if (expected.size() != actual.size()) {
        throw std::runtime_error(
            "B002 maintenance hit count differs");
    }
    Validation result;
    for (std::size_t index = 0;
         index < actual.size();
         ++index) {
        if (actual[index].metadata[3] > 1U) {
            ++result.runtime_errors;
            ++result.mismatches;
            continue;
        }
        if (!equivalent_hit(
                expected[index],
                from_gpu_hit(actual[index]))) {
            ++result.mismatches;
        }
    }
    return result;
}

[[nodiscard]] std::vector<B002BufferUpdate> triangle_updates(
    std::span<const GpuTriangle> triangles,
    std::span<const std::uint32_t> moved) {
    std::vector<B002BufferUpdate> updates;
    updates.reserve(moved.size());
    for (const auto primitive : moved) {
        updates.push_back({
            VkDeviceSize(primitive) *
                VkDeviceSize(sizeof(GpuTriangle)),
            &triangles[primitive],
            VkDeviceSize(sizeof(GpuTriangle)),
        });
    }
    return updates;
}

[[nodiscard]] std::vector<B002BufferUpdate> node_diff_updates(
    std::span<const GpuBvhNode> before,
    std::span<const GpuBvhNode> after) {
    if (before.size() != after.size()) {
        throw std::runtime_error(
            "B002 partial node diff requires stable node count");
    }

    std::vector<B002BufferUpdate> updates;
    std::size_t begin = 0;
    while (begin < after.size()) {
        while (begin < after.size() &&
               std::memcmp(
                   &before[begin],
                   &after[begin],
                   sizeof(GpuBvhNode)) == 0) {
            ++begin;
        }
        if (begin == after.size()) break;

        std::size_t end = begin + 1;
        while (end < after.size() &&
               std::memcmp(
                   &before[end],
                   &after[end],
                   sizeof(GpuBvhNode)) != 0) {
            ++end;
        }
        updates.push_back({
            VkDeviceSize(begin * sizeof(GpuBvhNode)),
            after.data() + begin,
            VkDeviceSize((end - begin) * sizeof(GpuBvhNode)),
        });
        begin = end;
    }
    return updates;
}

[[nodiscard]] std::size_t allocations(
    std::span<const B002Buffer* const> buffers) {
    std::size_t total = 0;
    for (const auto* buffer : buffers) {
        total += static_cast<std::size_t>(
            buffer->allocation_size);
    }
    return total;
}

[[nodiscard]] Row run_software(
    const B002Scene& scene,
    const Regime& regime,
    std::uint32_t moved_instance,
    std::span<const std::uint32_t> moved,
    std::span<const Ray> rays,
    std::span<const GpuRay> replay_rays,
    std::span<const Hit> expected,
    const Cli& cli) {
    auto geometry = scene.triangles;
    GpuSoftwareBvhData acceleration(scene.triangles);
    const auto before_nodes = acceleration.gpu_nodes();
    const auto base_triangles = gpu_triangles(scene.triangles);

    B002VulkanContext context(cli.validation);
    auto triangle_buffer = context.upload_device_buffer(
        base_triangles.data(),
        base_triangles.size() * sizeof(GpuTriangle),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto node_buffer = context.upload_device_buffer(
        before_nodes.data(),
        before_nodes.size() * sizeof(GpuBvhNode),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto order_buffer = context.upload_device_buffer(
        acceleration.ordered_primitives().data(),
        acceleration.ordered_primitives().size() *
            sizeof(std::uint32_t),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto ray_buffer = context.upload_device_buffer(
        replay_rays.data(),
        replay_rays.size() * sizeof(GpuRay),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto hit_buffer = context.create_device_buffer(
        replay_rays.size() * sizeof(GpuHit),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

    const auto geometry_us =
        measure_translation(
            geometry,
            moved,
            regime.delta_x);

    const auto accel_start = Clock::now();
    acceleration.refit(geometry);
    const auto accel_us = elapsed_us(accel_start);

    const auto pack_start = Clock::now();
    const auto after_nodes = acceleration.gpu_nodes();
    const auto after_triangles = gpu_triangles(geometry);
    const auto pack_us = elapsed_us(pack_start);

    const auto geometry_updates =
        triangle_updates(after_triangles, moved);
    auto upload_start = Clock::now();
    context.update_device_buffer(
        triangle_buffer,
        geometry_updates);
    const auto geometry_upload_us =
        elapsed_us(upload_start);

    const B002BufferUpdate node_update{
        0,
        after_nodes.data(),
        VkDeviceSize(
            after_nodes.size() * sizeof(GpuBvhNode)),
    };
    upload_start = Clock::now();
    context.update_device_buffer(
        node_buffer,
        std::span<const B002BufferUpdate>(
            &node_update,
            1));
    const auto accel_upload_us =
        elapsed_us(upload_start);

    std::array<const B002Buffer*, 5> bindings{
        &ray_buffer,
        &triangle_buffer,
        &node_buffer,
        &order_buffer,
        &hit_buffer,
    };
    B002ComputeTraversal runner(
        context,
        (std::filesystem::path(
            PHOS_GI_LANE_B_SHADER_DIR) /
            "lane_b_b002_software_bvh.spv").string(),
        bindings,
        sizeof(SoftwareTraversalPush));
    const SoftwareTraversalPush push{
        static_cast<std::uint32_t>(rays.size()),
        acceleration.root(),
        0,
        0,
    };
    const auto trace_us = runner.measure(
        push.ray_count,
        cli.iterations,
        &push,
        sizeof(push));

    std::vector<GpuHit> hits(rays.size());
    context.download_device_buffer(
        hit_buffer,
        hits.data(),
        hits.size() * sizeof(GpuHit));
    const auto validation =
        validate_hits(expected, hits);

    const std::array<const B002Buffer*, 3> persistent{
        &triangle_buffer,
        &node_buffer,
        &order_buffer,
    };
    const auto persistent_bytes =
        allocations(persistent);
    const auto transient_bytes =
        static_cast<std::size_t>(
            ray_buffer.allocation_size +
            hit_buffer.allocation_size);

    context.destroy_buffer(hit_buffer);
    context.destroy_buffer(ray_buffer);
    context.destroy_buffer(order_buffer);
    context.destroy_buffer(node_buffer);
    context.destroy_buffer(triangle_buffer);

    return {
        regime.name,
        "software-bvh",
        moved_instance,
        moved.size(),
        regime.delta_x,
        0,
        0,
        0,
        0,
        geometry_us,
        accel_us,
        pack_us,
        geometry_upload_us,
        accel_upload_us,
        moved.size() * sizeof(GpuTriangle),
        after_nodes.size() * sizeof(GpuBvhNode),
        0.0,
        0.0,
        trace_us,
        validation.mismatches,
        validation.runtime_errors,
        persistent_bytes,
        transient_bytes,
        0,
    };
}

[[nodiscard]] Row run_hierarchy(
    const B002Scene& scene,
    const Regime& regime,
    std::uint32_t moved_instance,
    std::span<const std::uint32_t> moved,
    std::span<const Ray> rays,
    std::span<const GpuRay> replay_rays,
    std::span<const Hit> expected,
    const Cli& cli,
    float segment_size) {
    auto geometry = scene.triangles;
    HierarchicalStrataBrick acceleration(
        scene.triangles,
        segment_size);
    const auto before_payload =
        make_hierarchical_gpu_payload(
            acceleration.flatten());
    const auto base_triangles =
        gpu_triangles(scene.triangles);

    B002VulkanContext context(cli.validation);
    auto triangle_buffer = context.upload_device_buffer(
        base_triangles.data(),
        base_triangles.size() * sizeof(GpuTriangle),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto node_buffer = context.upload_device_buffer(
        before_payload.nodes.data(),
        before_payload.nodes.size() * sizeof(GpuBvhNode),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto order_buffer = context.upload_device_buffer(
        before_payload.ordered_primitives.data(),
        before_payload.ordered_primitives.size() *
            sizeof(std::uint32_t),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto hash_buffer = context.upload_device_buffer(
        before_payload.hash_table.data(),
        before_payload.hash_table.size() *
            sizeof(GpuSegmentHashEntry),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto ray_buffer = context.upload_device_buffer(
        replay_rays.data(),
        replay_rays.size() * sizeof(GpuRay),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto hit_buffer = context.create_device_buffer(
        replay_rays.size() * sizeof(GpuHit),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

    const auto geometry_us =
        measure_translation(
            geometry,
            moved,
            regime.delta_x);

    const auto accel_start = Clock::now();
    const auto stats =
        acceleration.update(geometry, moved);
    const auto accel_us = elapsed_us(accel_start);

    const auto pack_start = Clock::now();
    const auto after_payload =
        make_hierarchical_gpu_payload(
            acceleration.flatten());
    const auto after_triangles =
        gpu_triangles(geometry);
    const auto pack_us = elapsed_us(pack_start);

    if (regime.name == "bounds-only" &&
        stats.membership_changes != 0) {
        throw std::runtime_error(
            "B002 bounds-only regime changed hierarchy membership");
    }
    if (regime.name == "topology-change" &&
        stats.membership_changes == 0) {
        throw std::runtime_error(
            "B002 topology regime did not change hierarchy membership");
    }

    const auto geometry_updates =
        triangle_updates(after_triangles, moved);
    auto upload_start = Clock::now();
    context.update_device_buffer(
        triangle_buffer,
        geometry_updates);
    const auto geometry_upload_us =
        elapsed_us(upload_start);

    std::size_t accel_update_bytes = 0;
    upload_start = Clock::now();
    if (stats.membership_changes == 0) {
        if (before_payload.ordered_primitives !=
                after_payload.ordered_primitives ||
            before_payload.hash_table.size() !=
                after_payload.hash_table.size()) {
            throw std::runtime_error(
                "B002 bounds-only hierarchy changed stable GPU topology");
        }
        const auto node_updates =
            node_diff_updates(
                before_payload.nodes,
                after_payload.nodes);
        for (const auto& update : node_updates) {
            accel_update_bytes +=
                static_cast<std::size_t>(update.size);
        }
        context.update_device_buffer(
            node_buffer,
            node_updates);
    } else {
        accel_update_bytes =
            after_payload.nodes.size() * sizeof(GpuBvhNode) +
            after_payload.ordered_primitives.size() *
                sizeof(std::uint32_t) +
            after_payload.hash_table.size() *
                sizeof(GpuSegmentHashEntry);
        context.replace_device_buffer(
            node_buffer,
            after_payload.nodes.data(),
            after_payload.nodes.size() *
                sizeof(GpuBvhNode),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        context.replace_device_buffer(
            order_buffer,
            after_payload.ordered_primitives.data(),
            after_payload.ordered_primitives.size() *
                sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        context.replace_device_buffer(
            hash_buffer,
            after_payload.hash_table.data(),
            after_payload.hash_table.size() *
                sizeof(GpuSegmentHashEntry),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    }
    const auto accel_upload_us =
        elapsed_us(upload_start);

    std::array<const B002Buffer*, 6> bindings{
        &ray_buffer,
        &triangle_buffer,
        &node_buffer,
        &order_buffer,
        &hash_buffer,
        &hit_buffer,
    };
    B002ComputeTraversal runner(
        context,
        (std::filesystem::path(
            PHOS_GI_LANE_B_SHADER_DIR) /
            "lane_b_b002_hierarchical.spv").string(),
        bindings,
        sizeof(HierarchicalTraversalPush));

    HierarchicalTraversalPush push{};
    push.values[0] =
        static_cast<std::uint32_t>(rays.size());
    push.values[1] = after_payload.hash_mask;
    push.values[2] = after_payload.hash_max_probe;
    const auto max_steps =
        std::max<std::uint64_t>(
            64,
            std::uint64_t(acceleration.segment_count()) *
                    16U +
                64U);
    push.values[3] =
        static_cast<std::uint32_t>(
            std::min<std::uint64_t>(
                max_steps,
                std::numeric_limits<std::uint32_t>::max()));
    push.occupied_min_segment_size[0] =
        after_payload.occupied_bounds.min.x;
    push.occupied_min_segment_size[1] =
        after_payload.occupied_bounds.min.y;
    push.occupied_min_segment_size[2] =
        after_payload.occupied_bounds.min.z;
    push.occupied_min_segment_size[3] =
        segment_size;
    push.occupied_max_pad[0] =
        after_payload.occupied_bounds.max.x;
    push.occupied_max_pad[1] =
        after_payload.occupied_bounds.max.y;
    push.occupied_max_pad[2] =
        after_payload.occupied_bounds.max.z;

    const auto trace_us = runner.measure(
        push.values[0],
        cli.iterations,
        &push,
        sizeof(push));
    std::vector<GpuHit> hits(rays.size());
    context.download_device_buffer(
        hit_buffer,
        hits.data(),
        hits.size() * sizeof(GpuHit));
    const auto validation =
        validate_hits(expected, hits);

    const std::array<const B002Buffer*, 4> persistent{
        &triangle_buffer,
        &node_buffer,
        &order_buffer,
        &hash_buffer,
    };
    const auto persistent_bytes =
        allocations(persistent);
    const auto transient_bytes =
        static_cast<std::size_t>(
            ray_buffer.allocation_size +
            hit_buffer.allocation_size);

    context.destroy_buffer(hit_buffer);
    context.destroy_buffer(ray_buffer);
    context.destroy_buffer(hash_buffer);
    context.destroy_buffer(order_buffer);
    context.destroy_buffer(node_buffer);
    context.destroy_buffer(triangle_buffer);

    return {
        regime.name,
        "hierarchical-stratabrick",
        moved_instance,
        moved.size(),
        regime.delta_x,
        stats.membership_changes,
        stats.refit_segments,
        stats.rebuilt_segments,
        stats.removed_segments,
        geometry_us,
        accel_us,
        pack_us,
        geometry_upload_us,
        accel_upload_us,
        moved.size() * sizeof(GpuTriangle),
        accel_update_bytes,
        0.0,
        0.0,
        trace_us,
        validation.mismatches,
        validation.runtime_errors,
        persistent_bytes,
        transient_bytes,
        0,
    };
}

[[nodiscard]] Row run_hwrt(
    const B002Scene& scene,
    const Regime& regime,
    std::uint32_t moved_instance,
    std::span<const std::uint32_t> moved,
    std::span<const Ray> rays,
    std::span<const GpuRay> replay_rays,
    std::span<const Hit> expected,
    const Cli& cli) {
    auto geometry = scene.triangles;
    B002VulkanContext context(
        cli.validation,
        kB002TargetDeviceName,
        true);
    B002HwrtTraversal acceleration(
        context,
        scene.triangles,
        (std::filesystem::path(
            PHOS_GI_LANE_B_SHADER_DIR) /
            "lane_b_b002_hwrt.spv").string());

    const auto geometry_us =
        measure_translation(
            geometry,
            moved,
            regime.delta_x);
    const auto update =
        acceleration.update_geometry(
            geometry,
            moved);
    const auto trace =
        acceleration.trace(
            replay_rays,
            cli.iterations);
    const auto validation =
        validate_hits(expected, trace.hits);

    return {
        regime.name,
        "hwrt-tlas",
        moved_instance,
        moved.size(),
        regime.delta_x,
        0,
        0,
        0,
        0,
        geometry_us,
        0.0,
        0.0,
        update.geometry_upload_us,
        0.0,
        moved.size() *
            (3U * sizeof(float) * 3U + sizeof(GpuTriangle)),
        0,
        update.blas_update_us,
        update.tlas_update_us,
        trace.trace_us,
        validation.mismatches,
        validation.runtime_errors,
        acceleration.setup_stats().persistent_bytes,
        trace.ray_allocation_bytes +
            trace.hit_allocation_bytes,
        acceleration.setup_stats().scratch_bytes,
    };
}

void write_csv(
    const std::filesystem::path& path,
    std::span<const Row> rows) {
    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error(
            "Could not create B002 maintenance CSV");
    }
    output
        << "regime,candidate,moved_instance,moved_primitives,delta_x,"
           "membership_changes,refit_segments,rebuilt_segments,removed_segments,"
           "geometry_transform_us,accel_cpu_us,pack_cpu_us,geometry_upload_us,"
           "accel_upload_us,geometry_update_bytes,accel_update_bytes,"
           "blas_update_us,tlas_update_us,trace_us,mismatches,"
           "runtime_errors,persistent_bytes,transient_bytes,explicit_scratch_bytes\n";
    output << std::fixed << std::setprecision(3);
    for (const auto& row : rows) {
        output
            << row.regime << ','
            << row.candidate << ','
            << row.moved_instance << ','
            << row.moved_primitives << ','
            << row.delta_x << ','
            << row.membership_changes << ','
            << row.refit_segments << ','
            << row.rebuilt_segments << ','
            << row.removed_segments << ','
            << row.geometry_transform_us << ','
            << row.accel_cpu_us << ','
            << row.pack_cpu_us << ','
            << row.geometry_upload_us << ','
            << row.accel_upload_us << ','
            << row.geometry_update_bytes << ','
            << row.accel_update_bytes << ','
            << row.blas_update_us << ','
            << row.tlas_update_us << ','
            << row.trace_us << ','
            << row.mismatches << ','
            << row.runtime_errors << ','
            << row.persistent_bytes << ','
            << row.transient_bytes << ','
            << row.explicit_scratch_bytes << '\n';
    }
}

} // namespace
} // namespace phos::gi::research::lane_b

int main(int argc, char** argv) {
    using namespace phos::gi::research::lane_b;

    try {
        const auto cli = parse_cli(argc, argv);
        const auto scene = load_b002_scene(cli.scene);
        const auto segment_size =
            b002_segment_size(scene);

        auto replay = load_b002_replay_case(
            cli.lane_a_artifact,
            "static",
            scene);
        const auto replay_gpu =
            gpu_rays(replay.rays);

        const auto moving =
            choose_moving_selection(
                scene,
                segment_size);
        const auto moved_instance = moving.instance_id;
        const auto& moved = moving.primitives;
        const auto& bounds_regime = moving.bounds_only;
        const auto& topology_regime = moving.topology_change;

        std::vector<Row> rows;
        std::size_t hwrt_rows = 0;
        std::string hwrt_error;
        for (const auto& regime :
             {bounds_regime, topology_regime}) {
            const auto moved_geometry =
                translated(
                    scene.triangles,
                    moved,
                    regime.delta_x);
            const auto expected =
                reference_hits(
                    moved_geometry,
                    replay.rays);

            rows.push_back(run_software(
                scene,
                regime,
                moved_instance,
                moved,
                replay.rays,
                replay_gpu,
                expected,
                cli));
            rows.push_back(run_hierarchy(
                scene,
                regime,
                moved_instance,
                moved,
                replay.rays,
                replay_gpu,
                expected,
                cli,
                segment_size));

            try {
                rows.push_back(run_hwrt(
                    scene,
                    regime,
                    moved_instance,
                    moved,
                    replay.rays,
                    replay_gpu,
                    expected,
                    cli));
                ++hwrt_rows;
            } catch (const std::exception& error) {
                hwrt_error = error.what();
                std::cerr
                    << "B002 maintenance HWRT unavailable: "
                    << error.what() << '\n';
            }
        }

        const auto root = output_root();
        std::filesystem::create_directories(root);
        write_csv(
            root / "b002-maintenance.csv",
            rows);

        {
            std::ofstream config(
                root / "b002-maintenance.json");
            if (!config) {
                throw std::runtime_error(
                    "Could not create B002 maintenance JSON");
            }
            config
                << "{\n"
                << "  \"evidence_class\": \"controlled-moving-geometry\",\n"
                << "  \"representative_stream_case\": \"static\",\n"
                << "  \"moved_instance\": "
                << moved_instance << ",\n"
                << "  \"moved_primitives\": "
                << moved.size() << ",\n"
                << "  \"segment_size\": "
                << std::setprecision(9)
                << segment_size << ",\n"
                << "  \"bounds_only_delta_x\": "
                << bounds_regime.delta_x << ",\n"
                << "  \"topology_change_delta_x\": "
                << topology_regime.delta_x << ",\n"
                << "  \"topology_probe_membership_changes\": "
                << topology_regime.expected_membership_changes
                << ",\n"
                << "  \"hwrt_rows\": " << hwrt_rows << ",\n"
                << "  \"hwrt_error\": \""
                << json_escape(hwrt_error) << "\"\n"
                << "}\n";
        }

        std::size_t mismatches = 0;
        std::size_t runtime_errors = 0;
        for (const auto& row : rows) {
            mismatches += row.mismatches;
            runtime_errors += row.runtime_errors;
            std::cout
                << "maintenance regime="
                << row.regime
                << " candidate=" << row.candidate
                << " moved=" << row.moved_primitives
                << " trace_us=" << row.trace_us
                << " mismatches=" << row.mismatches
                << '\n';
        }

        if (mismatches != 0 ||
            runtime_errors != 0) {
            std::cerr
                << "B002 maintenance correctness: FAIL mismatches="
                << mismatches
                << " runtime_errors="
                << runtime_errors
                << '\n';
            return 2;
        }

        std::cout
            << "B002 maintenance correctness: PASS "
            << "instance=" << moved_instance
            << " moved_primitives=" << moved.size()
            << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "B002 maintenance error: "
            << error.what()
            << '\n';
        return 1;
    }
}

#pragma once

#include "../lane_b_traversal/b002_gpu_layout.hpp"
#include "../lane_b_traversal/b003_quantized_bvh8.hpp"
#include "../lane_b_traversal/hierarchical_stratabrick.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::lane_e {

namespace lane_b = phos::gi::research::lane_b;

struct alignas(16) E003GpuInstance {
    float world_min[4]{};
    float world_max[4]{};
    float translation[4]{};
    float local_min_segment_size[4]{};
    float local_max_pad[4]{};
    std::uint32_t hash[4]{};
};
static_assert(sizeof(E003GpuInstance) == 96);

struct alignas(16) E003TraversalPush {
    std::uint32_t values[4]{};
};
static_assert(sizeof(E003TraversalPush) == 16);

struct E003BinaryPayload {
    std::vector<lane_b::GpuTriangle> triangles;
    std::vector<lane_b::GpuBvhNode> nodes;
    std::vector<std::uint32_t> ordered_primitives;
    std::vector<lane_b::GpuSegmentHashEntry> hash_table;
    std::vector<E003GpuInstance> instances;
    std::uint32_t moving_instance_index{1U};
};

struct E003QuantizedPayload {
    std::vector<lane_b::GpuTriangle> triangles;
    std::vector<lane_b::B003GpuQuantNode> nodes;
    std::vector<std::uint32_t> ordered_primitives;
    std::vector<lane_b::GpuSegmentHashEntry> hash_table;
    std::vector<E003GpuInstance> instances;
    std::uint32_t moving_instance_index{1U};
};

namespace detail {

struct Partition {
    std::vector<lane_b::Triangle> static_triangles;
    std::vector<lane_b::Triangle> rigid_triangles;
};

[[nodiscard]] inline Partition partition_rigid(
    const std::vector<lane_b::Triangle>& source,
    std::span<const std::uint32_t> rigid_primitives) {
    if (source.empty() || rigid_primitives.empty()) {
        throw std::runtime_error(
            "E003 requires non-empty source and rigid primitive set");
    }

    std::vector<bool> rigid(source.size(), false);
    std::uint32_t rigid_instance = lane_b::kInvalidId;
    for (const auto primitive : rigid_primitives) {
        if (primitive >= source.size()) {
            throw std::runtime_error(
                "E003 rigid primitive index is out of range");
        }
        if (rigid[primitive]) {
            throw std::runtime_error(
                "E003 rigid primitive set contains duplicates");
        }
        rigid[primitive] = true;
        const auto instance = source[primitive].instance_id;
        if (instance == lane_b::kInvalidId) {
            throw std::runtime_error(
                "E003 rigid primitive has invalid instance id");
        }
        if (rigid_instance == lane_b::kInvalidId) {
            rigid_instance = instance;
        } else if (rigid_instance != instance) {
            throw std::runtime_error(
                "E003 rigid primitive set spans multiple source instances");
        }
    }

    Partition result;
    result.static_triangles.reserve(
        source.size() - rigid_primitives.size());
    result.rigid_triangles.reserve(
        rigid_primitives.size());
    for (std::size_t index = 0; index < source.size(); ++index) {
        if (rigid[index]) {
            result.rigid_triangles.push_back(source[index]);
        } else {
            result.static_triangles.push_back(source[index]);
        }
    }
    if (result.static_triangles.empty() ||
        result.rigid_triangles.empty()) {
        throw std::runtime_error(
            "E003 ownership partition must contain static and rigid geometry");
    }
    return result;
}

[[nodiscard]] inline std::uint32_t max_dda_steps(
    std::size_t segment_count) {
    const auto steps = std::max<std::uint64_t>(
        64U,
        std::uint64_t(segment_count) * 16U + 64U);
    return static_cast<std::uint32_t>(
        std::min<std::uint64_t>(
            steps,
            std::numeric_limits<std::uint32_t>::max()));
}

[[nodiscard]] inline E003GpuInstance make_instance(
    const lane_b::Aabb& local_bounds,
    float segment_size,
    std::uint32_t hash_base,
    std::uint32_t hash_mask,
    std::uint32_t hash_max_probe,
    std::uint32_t dda_steps) {
    E003GpuInstance instance;
    instance.world_min[0] = local_bounds.min.x;
    instance.world_min[1] = local_bounds.min.y;
    instance.world_min[2] = local_bounds.min.z;
    instance.world_max[0] = local_bounds.max.x;
    instance.world_max[1] = local_bounds.max.y;
    instance.world_max[2] = local_bounds.max.z;
    instance.local_min_segment_size[0] = local_bounds.min.x;
    instance.local_min_segment_size[1] = local_bounds.min.y;
    instance.local_min_segment_size[2] = local_bounds.min.z;
    instance.local_min_segment_size[3] = segment_size;
    instance.local_max_pad[0] = local_bounds.max.x;
    instance.local_max_pad[1] = local_bounds.max.y;
    instance.local_max_pad[2] = local_bounds.max.z;
    instance.hash[0] = hash_base;
    instance.hash[1] = hash_mask;
    instance.hash[2] = hash_max_probe;
    instance.hash[3] = dda_steps;
    return instance;
}

inline void append_triangles(
    std::vector<lane_b::GpuTriangle>& target,
    const std::vector<lane_b::Triangle>& source) {
    target.reserve(target.size() + source.size());
    for (const auto& triangle : source) {
        target.push_back(lane_b::to_gpu_triangle(triangle));
    }
}

inline void append_binary_partition(
    E003BinaryPayload& output,
    const std::vector<lane_b::Triangle>& triangles,
    float segment_size) {
    const auto triangle_base =
        static_cast<std::uint32_t>(output.triangles.size());
    append_triangles(output.triangles, triangles);

    lane_b::HierarchicalStrataBrick hierarchy(
        triangles,
        segment_size);
    const auto flat = hierarchy.flatten();
    auto payload =
        lane_b::make_hierarchical_gpu_payload(flat);

    const auto node_base =
        static_cast<std::uint32_t>(output.nodes.size());
    const auto order_base =
        static_cast<std::uint32_t>(
            output.ordered_primitives.size());
    const auto hash_base =
        static_cast<std::uint32_t>(
            output.hash_table.size());

    for (auto node : payload.nodes) {
        if (node.data[0] == lane_b::kInvalidId) {
            node.data[2] += order_base;
        } else {
            node.data[0] += node_base;
            node.data[1] += node_base;
        }
        output.nodes.push_back(node);
    }
    for (const auto primitive : payload.ordered_primitives) {
        output.ordered_primitives.push_back(
            triangle_base + primitive);
    }
    for (auto entry : payload.hash_table) {
        if (entry.metadata[0] != lane_b::kInvalidId) {
            entry.metadata[0] += node_base;
        }
        output.hash_table.push_back(entry);
    }

    output.instances.push_back(
        make_instance(
            payload.occupied_bounds,
            segment_size,
            hash_base,
            payload.hash_mask,
            payload.hash_max_probe,
            max_dda_steps(flat.segments.size())));
}

inline void append_quantized_partition(
    E003QuantizedPayload& output,
    const std::vector<lane_b::Triangle>& triangles,
    float segment_size) {
    const auto triangle_base =
        static_cast<std::uint32_t>(output.triangles.size());
    append_triangles(output.triangles, triangles);

    lane_b::HierarchicalStrataBrick hierarchy(
        triangles,
        segment_size);
    auto wide =
        lane_b::make_b003_wide_micro_payload(
            hierarchy.flatten());
    auto payload =
        lane_b::make_b003_quantized_micro_payload(wide);

    const auto node_base =
        static_cast<std::uint32_t>(output.nodes.size());
    const auto order_base =
        static_cast<std::uint32_t>(
            output.ordered_primitives.size());
    const auto hash_base =
        static_cast<std::uint32_t>(
            output.hash_table.size());

    for (auto node : payload.nodes) {
        for (auto& child : node.children) {
            auto token = child.packed[3];
            if (token == lane_b::kInvalidId) {
                continue;
            }
            if (lane_b::b003_wide_is_leaf(token)) {
                const auto begin =
                    lane_b::b003_wide_leaf_begin(token);
                const auto count =
                    lane_b::b003_wide_leaf_count(token);
                child.packed[3] =
                    lane_b::b003_wide_leaf_token(
                        order_base + begin,
                        count);
            } else {
                child.packed[3] += node_base;
            }
        }
        output.nodes.push_back(node);
    }
    for (const auto primitive : payload.ordered_primitives) {
        output.ordered_primitives.push_back(
            triangle_base + primitive);
    }
    for (auto entry : payload.hash_table) {
        if (entry.metadata[0] != lane_b::kInvalidId) {
            entry.metadata[0] += node_base;
        }
        output.hash_table.push_back(entry);
    }

    output.instances.push_back(
        make_instance(
            payload.occupied_bounds,
            segment_size,
            hash_base,
            payload.hash_mask,
            payload.hash_max_probe,
            max_dda_steps(payload.segment_count)));
}

} // namespace detail

[[nodiscard]] inline E003BinaryPayload
make_e003_binary_payload(
    const std::vector<lane_b::Triangle>& source,
    std::span<const std::uint32_t> rigid_primitives,
    float segment_size) {
    const auto partition =
        detail::partition_rigid(
            source,
            rigid_primitives);
    E003BinaryPayload output;
    detail::append_binary_partition(
        output,
        partition.static_triangles,
        segment_size);
    detail::append_binary_partition(
        output,
        partition.rigid_triangles,
        segment_size);
    return output;
}

[[nodiscard]] inline E003QuantizedPayload
make_e003_quantized_payload(
    const std::vector<lane_b::Triangle>& source,
    std::span<const std::uint32_t> rigid_primitives,
    float segment_size) {
    const auto partition =
        detail::partition_rigid(
            source,
            rigid_primitives);
    E003QuantizedPayload output;
    detail::append_quantized_partition(
        output,
        partition.static_triangles,
        segment_size);
    detail::append_quantized_partition(
        output,
        partition.rigid_triangles,
        segment_size);
    return output;
}

[[nodiscard]] inline E003GpuInstance
translated_instance(
    E003GpuInstance source,
    float delta_x) noexcept {
    source.translation[0] += delta_x;
    source.world_min[0] += delta_x;
    source.world_max[0] += delta_x;
    return source;
}

} // namespace phos::gi::research::lane_e

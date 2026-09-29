#pragma once

#include "e003_instance_payload.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <numeric>
#include <span>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::lane_e {

namespace lane_b = phos::gi::research::lane_b;

struct E004QuantizedPartition {
    std::vector<lane_b::B003GpuQuantNode> nodes;
    std::vector<std::uint32_t> ordered_primitives;
    std::vector<lane_b::GpuSegmentHashEntry> hash_table;
    lane_b::Aabb occupied_bounds{};
    std::uint32_t hash_mask{};
    std::uint32_t hash_max_probe{};
    std::size_t segment_count{};
};

struct E004QuantizedSetup {
    std::vector<lane_b::Triangle> dynamic_triangles;
    std::vector<std::uint32_t> dynamic_global_primitives;

    std::vector<lane_b::GpuTriangle> triangles;
    std::vector<lane_b::B003GpuQuantNode> nodes;
    std::vector<std::uint32_t> ordered_primitives;
    std::vector<lane_b::GpuSegmentHashEntry> hash_table;
    std::vector<E003GpuInstance> instances;

    std::size_t dynamic_triangle_base{};
    std::size_t dynamic_node_base{};
    std::size_t dynamic_order_base{};
    std::size_t dynamic_hash_base{};
    std::size_t dynamic_node_capacity{};
    std::size_t dynamic_order_capacity{};
    std::size_t dynamic_hash_capacity{};
};

[[nodiscard]] inline E004QuantizedPartition
make_e004_quantized_partition(
    const lane_b::HierarchicalStrataBrick& hierarchy) {
    auto wide =
        lane_b::make_b003_wide_micro_payload(
            hierarchy.flatten());
    auto quant =
        lane_b::make_b003_quantized_micro_payload(
            wide);
    return {
        std::move(quant.nodes),
        std::move(quant.ordered_primitives),
        std::move(quant.hash_table),
        quant.occupied_bounds,
        quant.hash_mask,
        quant.hash_max_probe,
        quant.segment_count,
    };
}

inline void rebase_e004_partition(
    E004QuantizedPartition& payload,
    std::uint32_t triangle_base,
    std::uint32_t node_base,
    std::uint32_t order_base) {
    for (auto& node : payload.nodes) {
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
    }

    for (auto& primitive : payload.ordered_primitives) {
        primitive += triangle_base;
    }

    for (auto& entry : payload.hash_table) {
        if (entry.metadata[0] != lane_b::kInvalidId) {
            entry.metadata[0] += node_base;
        }
    }
}

[[nodiscard]] inline E003GpuInstance
make_e004_instance(
    const E004QuantizedPartition& payload,
    float segment_size,
    std::uint32_t hash_base) {
    E003GpuInstance instance;
    instance.world_min[0] = payload.occupied_bounds.min.x;
    instance.world_min[1] = payload.occupied_bounds.min.y;
    instance.world_min[2] = payload.occupied_bounds.min.z;
    instance.world_max[0] = payload.occupied_bounds.max.x;
    instance.world_max[1] = payload.occupied_bounds.max.y;
    instance.world_max[2] = payload.occupied_bounds.max.z;

    instance.local_min_segment_size[0] =
        payload.occupied_bounds.min.x;
    instance.local_min_segment_size[1] =
        payload.occupied_bounds.min.y;
    instance.local_min_segment_size[2] =
        payload.occupied_bounds.min.z;
    instance.local_min_segment_size[3] =
        segment_size;
    instance.local_max_pad[0] =
        payload.occupied_bounds.max.x;
    instance.local_max_pad[1] =
        payload.occupied_bounds.max.y;
    instance.local_max_pad[2] =
        payload.occupied_bounds.max.z;

    instance.hash[0] = hash_base;
    instance.hash[1] = payload.hash_mask;
    instance.hash[2] = payload.hash_max_probe;
    instance.hash[3] =
        detail::max_dda_steps(
            payload.segment_count);
    return instance;
}

[[nodiscard]] inline E004QuantizedSetup
make_e004_quantized_setup(
    const std::vector<lane_b::Triangle>& source,
    std::span<const std::uint32_t> dynamic_primitives,
    const std::vector<lane_b::Triangle>& target,
    float segment_size) {
    if (source.size() != target.size()) {
        throw std::runtime_error(
            "E004 setup requires stable primitive count");
    }

    const auto split =
        detail::partition_rigid(
            source,
            dynamic_primitives);

    std::vector<lane_b::Triangle> target_dynamic;
    target_dynamic.reserve(dynamic_primitives.size());
    for (const auto primitive : dynamic_primitives) {
        target_dynamic.push_back(target.at(primitive));
    }

    lane_b::HierarchicalStrataBrick static_hierarchy(
        split.static_triangles,
        segment_size);
    lane_b::HierarchicalStrataBrick dynamic_hierarchy(
        split.rigid_triangles,
        segment_size);
    lane_b::HierarchicalStrataBrick target_hierarchy(
        target_dynamic,
        segment_size);

    auto static_payload =
        make_e004_quantized_partition(
            static_hierarchy);
    auto dynamic_payload =
        make_e004_quantized_partition(
            dynamic_hierarchy);
    const auto target_payload =
        make_e004_quantized_partition(
            target_hierarchy);

    E004QuantizedSetup output;
    output.dynamic_triangles =
        split.rigid_triangles;
    output.dynamic_global_primitives.assign(
        dynamic_primitives.begin(),
        dynamic_primitives.end());

    output.dynamic_triangle_base =
        split.static_triangles.size();
    output.dynamic_node_base =
        static_payload.nodes.size();
    output.dynamic_order_base =
        static_payload.ordered_primitives.size();
    output.dynamic_hash_base =
        static_payload.hash_table.size();
    output.dynamic_node_capacity =
        std::max(
            dynamic_payload.nodes.size(),
            target_payload.nodes.size());
    output.dynamic_order_capacity =
        std::max(
            dynamic_payload.ordered_primitives.size(),
            target_payload.ordered_primitives.size());
    output.dynamic_hash_capacity =
        std::max(
            dynamic_payload.hash_table.size(),
            target_payload.hash_table.size());

    output.triangles.reserve(source.size());
    for (const auto& triangle : split.static_triangles) {
        output.triangles.push_back(
            lane_b::to_gpu_triangle(triangle));
    }
    for (const auto& triangle : split.rigid_triangles) {
        output.triangles.push_back(
            lane_b::to_gpu_triangle(triangle));
    }

    rebase_e004_partition(
        static_payload,
        0U,
        0U,
        0U);
    rebase_e004_partition(
        dynamic_payload,
        static_cast<std::uint32_t>(
            output.dynamic_triangle_base),
        static_cast<std::uint32_t>(
            output.dynamic_node_base),
        static_cast<std::uint32_t>(
            output.dynamic_order_base));

    output.nodes.resize(
        output.dynamic_node_base +
        output.dynamic_node_capacity);
    std::copy(
        static_payload.nodes.begin(),
        static_payload.nodes.end(),
        output.nodes.begin());
    std::copy(
        dynamic_payload.nodes.begin(),
        dynamic_payload.nodes.end(),
        output.nodes.begin() +
            static_cast<std::ptrdiff_t>(
                output.dynamic_node_base));

    output.ordered_primitives.resize(
        output.dynamic_order_base +
        output.dynamic_order_capacity);
    std::copy(
        static_payload.ordered_primitives.begin(),
        static_payload.ordered_primitives.end(),
        output.ordered_primitives.begin());
    std::copy(
        dynamic_payload.ordered_primitives.begin(),
        dynamic_payload.ordered_primitives.end(),
        output.ordered_primitives.begin() +
            static_cast<std::ptrdiff_t>(
                output.dynamic_order_base));

    output.hash_table.resize(
        output.dynamic_hash_base +
        output.dynamic_hash_capacity);
    std::copy(
        static_payload.hash_table.begin(),
        static_payload.hash_table.end(),
        output.hash_table.begin());
    std::copy(
        dynamic_payload.hash_table.begin(),
        dynamic_payload.hash_table.end(),
        output.hash_table.begin() +
            static_cast<std::ptrdiff_t>(
                output.dynamic_hash_base));

    output.instances.push_back(
        make_e004_instance(
            static_payload,
            segment_size,
            0U));
    output.instances.push_back(
        make_e004_instance(
            dynamic_payload,
            segment_size,
            static_cast<std::uint32_t>(
                output.dynamic_hash_base)));

    return output;
}

[[nodiscard]] inline E004QuantizedPartition
make_e004_dynamic_partition(
    const lane_b::HierarchicalStrataBrick& hierarchy,
    const E004QuantizedSetup& setup) {
    auto payload =
        make_e004_quantized_partition(
            hierarchy);
    if (payload.nodes.size() >
            setup.dynamic_node_capacity ||
        payload.ordered_primitives.size() >
            setup.dynamic_order_capacity ||
        payload.hash_table.size() >
            setup.dynamic_hash_capacity) {
        throw std::runtime_error(
            "E004 dynamic partition exceeded frozen setup capacity");
    }

    rebase_e004_partition(
        payload,
        static_cast<std::uint32_t>(
            setup.dynamic_triangle_base),
        static_cast<std::uint32_t>(
            setup.dynamic_node_base),
        static_cast<std::uint32_t>(
            setup.dynamic_order_base));
    return payload;
}

} // namespace phos::gi::research::lane_e

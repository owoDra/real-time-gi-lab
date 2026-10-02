#pragma once

#include "hierarchical_stratabrick.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::lane_b {

struct alignas(16) GpuRay {
    float origin_tmax[4]{};
    float direction_pad[4]{};
};
static_assert(sizeof(GpuRay) == 32);

struct alignas(16) GpuTriangle {
    float v0[4]{};
    float v1[4]{};
    float v2[4]{};
    std::uint32_t metadata[4]{};
};
static_assert(sizeof(GpuTriangle) == 64);

struct alignas(16) GpuBvhNode {
    float bounds_min[4]{};
    float bounds_max[4]{};
    std::uint32_t data[4]{};
};
static_assert(sizeof(GpuBvhNode) == 48);

struct alignas(16) GpuHit {
    float normal_t[4]{};
    std::uint32_t metadata[4]{};
};
static_assert(sizeof(GpuHit) == 32);

struct alignas(16) GpuSegmentHashEntry {
    std::int32_t coord[4]{};
    std::uint32_t metadata[4]{
        kInvalidId, 0U, 0U, 0U};
};
static_assert(sizeof(GpuSegmentHashEntry) == 32);

[[nodiscard]] inline GpuRay to_gpu_ray(const Ray& ray) noexcept {
    return {
        {ray.origin.x, ray.origin.y, ray.origin.z, ray.t_max},
        {ray.direction.x, ray.direction.y, ray.direction.z, 0.0F},
    };
}

[[nodiscard]] inline GpuTriangle to_gpu_triangle(const Triangle& triangle) noexcept {
    return {
        {triangle.v0.x, triangle.v0.y, triangle.v0.z, 0.0F},
        {triangle.v1.x, triangle.v1.y, triangle.v1.z, 0.0F},
        {triangle.v2.x, triangle.v2.y, triangle.v2.z, 0.0F},
        {
            triangle.primitive_id,
            triangle.material_id,
            triangle.instance_id,
            triangle.two_sided ? 1U : 0U,
        },
    };
}

[[nodiscard]] inline GpuBvhNode to_gpu_node(
    const Aabb& bounds,
    std::uint32_t left,
    std::uint32_t right,
    std::uint32_t begin,
    std::uint32_t count) noexcept {
    return {
        {bounds.min.x, bounds.min.y, bounds.min.z, 0.0F},
        {bounds.max.x, bounds.max.y, bounds.max.z, 0.0F},
        {left, right, begin, count},
    };
}

[[nodiscard]] inline Hit from_gpu_hit(const GpuHit& hit) noexcept {
    if (hit.metadata[3] == 0U) return {};
    return {
        true,
        hit.normal_t[3],
        {hit.normal_t[0], hit.normal_t[1], hit.normal_t[2]},
        hit.metadata[0],
        hit.metadata[1],
        hit.metadata[2],
    };
}

[[nodiscard]] inline std::uint32_t segment_hash(
    SegmentCoord key) noexcept {
    auto mix = [](std::uint32_t value) {
        value ^= value >> 16U;
        value *= 0x7feb352dU;
        value ^= value >> 15U;
        value *= 0x846ca68bU;
        value ^= value >> 16U;
        return value;
    };
    const auto x = mix(static_cast<std::uint32_t>(key.x));
    const auto y = mix(static_cast<std::uint32_t>(key.y) ^ 0x9e3779b9U);
    const auto z = mix(static_cast<std::uint32_t>(key.z) ^ 0x85ebca6bU);
    return mix(x ^ (y << 1U) ^ (z << 2U));
}

struct HierarchicalGpuPayload {
    std::vector<GpuBvhNode> nodes;
    std::vector<std::uint32_t> ordered_primitives;
    std::vector<GpuSegmentHashEntry> hash_table;
    Aabb occupied_bounds{};
    std::uint32_t hash_mask{};
    std::uint32_t hash_max_probe{};
};

[[nodiscard]] inline HierarchicalGpuPayload make_hierarchical_gpu_payload(
    const HierarchicalFlatPayload& flat) {
    HierarchicalGpuPayload payload;
    payload.occupied_bounds = flat.occupied_bounds;
    payload.ordered_primitives = flat.ordered_primitives;
    payload.nodes.reserve(flat.nodes.size());
    for (const auto& node : flat.nodes) {
        payload.nodes.push_back(to_gpu_node(
            node.bounds,
            node.left,
            node.right,
            node.begin,
            node.count));
    }

    std::size_t table_size = 1;
    const auto target =
        std::max<std::size_t>(2, flat.segments.size() * 2);
    while (table_size < target) table_size <<= 1U;
    if (table_size > std::numeric_limits<std::uint32_t>::max()) {
        throw std::runtime_error("hierarchical segment hash exceeds 32-bit capacity");
    }

    payload.hash_table.resize(table_size);
    payload.hash_mask = static_cast<std::uint32_t>(table_size - 1U);
    for (const auto& segment : flat.segments) {
        std::uint32_t slot = segment_hash(segment.coord) & payload.hash_mask;
        std::uint32_t probe = 1;
        while (payload.hash_table[slot].metadata[0] != kInvalidId) {
            slot = (slot + 1U) & payload.hash_mask;
            ++probe;
            if (probe > table_size) {
                throw std::runtime_error("hierarchical segment hash insertion failed");
            }
        }
        auto& entry = payload.hash_table[slot];
        entry.coord[0] = segment.coord.x;
        entry.coord[1] = segment.coord.y;
        entry.coord[2] = segment.coord.z;
        entry.metadata[0] = segment.root;
        payload.hash_max_probe = std::max(payload.hash_max_probe, probe);
    }
    return payload;
}

} // namespace phos::gi::research::lane_b

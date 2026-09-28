#pragma once

#include "b003_micro_bvh8.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::lane_b {

struct alignas(16) B003GpuQuantChild {
    std::uint32_t packed[4]{
        0U,
        0U,
        0U,
        kInvalidId,
    };
};
static_assert(sizeof(B003GpuQuantChild) == 16);

struct alignas(16) B003GpuQuantNode {
    float origin[4]{};
    float scale[4]{};
    std::uint32_t metadata[4]{};
    B003GpuQuantChild children[8]{};
};
static_assert(sizeof(B003GpuQuantNode) == 176);

struct B003QuantizedMicroPayload {
    std::vector<B003GpuQuantNode> nodes;
    std::vector<std::uint32_t> ordered_primitives;
    std::vector<GpuSegmentHashEntry> hash_table;
    Aabb occupied_bounds{};
    std::uint32_t hash_mask{};
    std::uint32_t hash_max_probe{};
    std::size_t max_depth{};
    std::size_t max_stack_entries{};
    std::size_t segment_count{};
};

namespace b003_quant_detail {

inline constexpr float kQuantMax = 65535.0F;

[[nodiscard]] inline float component(
    const float values[4],
    int axis) noexcept {
    return values[axis];
}

[[nodiscard]] inline std::uint16_t quantize_min(
    float value,
    float origin,
    float extent) noexcept {
    if (!(extent > 0.0F) ||
        !std::isfinite(extent)) {
        return 0U;
    }
    const auto normalized =
        std::clamp(
            (value - origin) / extent,
            0.0F,
            1.0F);
    const auto quantized =
        std::floor(normalized * kQuantMax);
    return static_cast<std::uint16_t>(
        std::clamp(
            quantized,
            0.0F,
            kQuantMax));
}

[[nodiscard]] inline std::uint16_t quantize_max(
    float value,
    float origin,
    float extent) noexcept {
    if (!(extent > 0.0F) ||
        !std::isfinite(extent)) {
        return 0U;
    }
    const auto normalized =
        std::clamp(
            (value - origin) / extent,
            0.0F,
            1.0F);
    const auto quantized =
        std::ceil(normalized * kQuantMax);
    return static_cast<std::uint16_t>(
        std::clamp(
            quantized,
            0.0F,
            kQuantMax));
}

[[nodiscard]] inline std::uint32_t pack_axis(
    float child_min,
    float child_max,
    float origin,
    float extent) noexcept {
    const auto qmin =
        static_cast<std::uint32_t>(
            quantize_min(
                child_min,
                origin,
                extent));
    const auto qmax =
        static_cast<std::uint32_t>(
            quantize_max(
                child_max,
                origin,
                extent));
    return qmin | (qmax << 16U);
}

[[nodiscard]] inline Aabb node_bounds(
    const B003GpuWideNode& node) {
    Aabb bounds{};
    bool any = false;
    for (const auto& child : node.children) {
        if (child.data[0] == kInvalidId) {
            continue;
        }
        const Aabb child_bounds{
            {
                child.bounds_min[0],
                child.bounds_min[1],
                child.bounds_min[2],
            },
            {
                child.bounds_max[0],
                child.bounds_max[1],
                child.bounds_max[2],
            },
        };
        bounds =
            any
            ? merge(bounds, child_bounds)
            : child_bounds;
        any = true;
    }
    if (!any) {
        throw std::runtime_error(
            "B003 quantization encountered an empty wide node");
    }
    return bounds;
}

[[nodiscard]] inline B003GpuQuantNode
quantize_node(
    const B003GpuWideNode& source) {
    const auto bounds =
        node_bounds(source);
    const auto extent =
        bounds.max - bounds.min;

    B003GpuQuantNode output;
    output.origin[0] = bounds.min.x;
    output.origin[1] = bounds.min.y;
    output.origin[2] = bounds.min.z;
    output.scale[0] =
        extent.x / kQuantMax;
    output.scale[1] =
        extent.y / kQuantMax;
    output.scale[2] =
        extent.z / kQuantMax;

    std::uint32_t axis = 0U;
    bool have_axis = false;
    for (std::size_t slot = 0;
         slot < 8U;
         ++slot) {
        const auto& child =
            source.children[slot];
        auto& target =
            output.children[slot];

        if (child.data[0] == kInvalidId) {
            continue;
        }

        if (!have_axis) {
            axis = child.data[1];
            have_axis = true;
        } else if (axis != child.data[1]) {
            throw std::runtime_error(
                "B003 wide node children disagree on ordering axis");
        }

        target.packed[0] =
            pack_axis(
                child.bounds_min[0],
                child.bounds_max[0],
                bounds.min.x,
                extent.x);
        target.packed[1] =
            pack_axis(
                child.bounds_min[1],
                child.bounds_max[1],
                bounds.min.y,
                extent.y);
        target.packed[2] =
            pack_axis(
                child.bounds_min[2],
                child.bounds_max[2],
                bounds.min.z,
                extent.z);
        target.packed[3] =
            child.data[0];
    }
    output.metadata[0] = axis;
    return output;
}

} // namespace b003_quant_detail

[[nodiscard]] inline B003QuantizedMicroPayload
make_b003_quantized_micro_payload(
    const B003WideMicroPayload& wide) {
    B003QuantizedMicroPayload output;
    output.ordered_primitives =
        wide.ordered_primitives;
    output.hash_table =
        wide.hash_table;
    output.occupied_bounds =
        wide.occupied_bounds;
    output.hash_mask =
        wide.hash_mask;
    output.hash_max_probe =
        wide.hash_max_probe;
    output.max_depth =
        wide.max_depth;
    output.max_stack_entries =
        wide.max_stack_entries;
    output.segment_count =
        wide.segment_count;

    output.nodes.reserve(
        wide.nodes.size());
    for (const auto& node : wide.nodes) {
        output.nodes.push_back(
            b003_quant_detail::quantize_node(node));
    }
    return output;
}

[[nodiscard]] inline Aabb
b003_decode_quant_child(
    const B003GpuQuantNode& node,
    const B003GpuQuantChild& child) noexcept {
    const auto unpack_min =
        [](std::uint32_t packed) {
            return static_cast<float>(
                packed & 0xffffU);
        };
    const auto unpack_max =
        [](std::uint32_t packed) {
            return static_cast<float>(
                packed >> 16U);
        };

    return {
        {
            node.origin[0] +
                node.scale[0] *
                    unpack_min(child.packed[0]),
            node.origin[1] +
                node.scale[1] *
                    unpack_min(child.packed[1]),
            node.origin[2] +
                node.scale[2] *
                    unpack_min(child.packed[2]),
        },
        {
            node.origin[0] +
                node.scale[0] *
                    unpack_max(child.packed[0]),
            node.origin[1] +
                node.scale[1] *
                    unpack_max(child.packed[1]),
            node.origin[2] +
                node.scale[2] *
                    unpack_max(child.packed[2]),
        },
    };
}

} // namespace phos::gi::research::lane_b

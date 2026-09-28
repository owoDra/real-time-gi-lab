#pragma once

#include "hierarchical_stratabrick.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::lane_b {

inline constexpr std::uint32_t kB003MacroSegment = 0U;
inline constexpr std::uint32_t kB003MacroInternal = 1U;

struct alignas(16) B003GpuMacroChild {
    float bounds_min[4]{};
    float bounds_max[4]{};
    std::uint32_t data[4]{
        kInvalidId,
        kInvalidId,
        0U,
        0U,
    };
};
static_assert(sizeof(B003GpuMacroChild) == 48);

struct alignas(16) B003GpuMacroNode {
    B003GpuMacroChild children[8]{};
};
static_assert(sizeof(B003GpuMacroNode) == 384);

struct B003MacroBvh8Payload {
    std::vector<B003GpuMacroNode> nodes;
    std::uint32_t root{kInvalidId};
    std::size_t segment_count{};
    std::size_t max_depth{};
    std::size_t max_stack_entries{};
};

namespace b003_detail {

struct MacroItem {
    Aabb bounds{};
    std::uint32_t segment_root{kInvalidId};
};

[[nodiscard]] inline float axis_value(
    Vec3 value,
    int axis) noexcept {
    return axis == 0
        ? value.x
        : (axis == 1 ? value.y : value.z);
}

[[nodiscard]] inline B003GpuMacroChild make_child(
    const Aabb& bounds,
    std::uint32_t reference,
    std::uint32_t kind) noexcept {
    B003GpuMacroChild child;
    child.bounds_min[0] = bounds.min.x;
    child.bounds_min[1] = bounds.min.y;
    child.bounds_min[2] = bounds.min.z;
    child.bounds_max[0] = bounds.max.x;
    child.bounds_max[1] = bounds.max.y;
    child.bounds_max[2] = bounds.max.z;
    child.data[0] = reference;
    child.data[1] = kind;
    return child;
}

class MacroBuilder {
public:
    explicit MacroBuilder(std::vector<MacroItem> items)
        : items_(std::move(items)) {
        if (!items_.empty()) {
            payload_.root = build(
                0U,
                static_cast<std::uint32_t>(items_.size()),
                1U);
        }
        payload_.segment_count = items_.size();
    }

    [[nodiscard]] B003MacroBvh8Payload finish() && {
        if (payload_.root != kInvalidId) {
            std::vector<std::uint32_t> stack;
            stack.push_back(payload_.root);
            payload_.max_stack_entries = 1;
            while (!stack.empty()) {
                const auto node_index = stack.back();
                stack.pop_back();
                if (node_index >= payload_.nodes.size()) {
                    throw std::runtime_error(
                        "B003 macro BVH contains an invalid internal reference");
                }
                for (const auto& child :
                     payload_.nodes[node_index].children) {
                    if (child.data[0] == kInvalidId ||
                        child.data[1] != kB003MacroInternal) {
                        continue;
                    }
                    stack.push_back(child.data[0]);
                }
                payload_.max_stack_entries =
                    std::max(
                        payload_.max_stack_entries,
                        stack.size());
            }
        }
        return std::move(payload_);
    }

private:
    [[nodiscard]] Aabb range_bounds(
        std::uint32_t begin,
        std::uint32_t end) const {
        Aabb bounds{};
        for (auto cursor = begin; cursor < end; ++cursor) {
            bounds = merge(bounds, items_[cursor].bounds);
        }
        return bounds;
    }

    [[nodiscard]] std::uint32_t build(
        std::uint32_t begin,
        std::uint32_t end,
        std::size_t depth) {
        if (begin >= end) {
            throw std::runtime_error(
                "B003 macro BVH cannot build an empty range");
        }

        if (payload_.nodes.size() >=
            std::numeric_limits<std::uint32_t>::max()) {
            throw std::runtime_error(
                "B003 macro BVH exceeds 32-bit node indexing");
        }

        const auto node_index =
            static_cast<std::uint32_t>(payload_.nodes.size());
        payload_.nodes.emplace_back();
        payload_.max_depth =
            std::max(payload_.max_depth, depth);

        const auto count = end - begin;
        if (count <= 8U) {
            auto& node = payload_.nodes[node_index];
            for (std::uint32_t slot = 0; slot < count; ++slot) {
                const auto& item = items_[begin + slot];
                node.children[slot] = make_child(
                    item.bounds,
                    item.segment_root,
                    kB003MacroSegment);
            }
            return node_index;
        }

        Aabb center_bounds{};
        for (auto cursor = begin; cursor < end; ++cursor) {
            const auto point = center(items_[cursor].bounds);
            center_bounds = merge(center_bounds, {point, point});
        }
        const auto extent =
            center_bounds.max - center_bounds.min;
        const int axis =
            (extent.y > extent.x && extent.y >= extent.z)
            ? 1
            : (extent.z > extent.x ? 2 : 0);

        std::stable_sort(
            items_.begin() + begin,
            items_.begin() + end,
            [&](const MacroItem& a, const MacroItem& b) {
                const auto ca = axis_value(center(a.bounds), axis);
                const auto cb = axis_value(center(b.bounds), axis);
                if (ca != cb) return ca < cb;
                return a.segment_root < b.segment_root;
            });

        constexpr std::uint32_t kFanout = 8U;
        const auto group_count =
            std::min(kFanout, count);
        const auto base = count / group_count;
        const auto extra = count % group_count;

        std::uint32_t cursor = begin;
        for (std::uint32_t slot = 0;
             slot < group_count;
             ++slot) {
            const auto group_size =
                base + (slot < extra ? 1U : 0U);
            const auto group_begin = cursor;
            const auto group_end = cursor + group_size;
            cursor = group_end;

            const auto bounds =
                range_bounds(group_begin, group_end);

            // Avoid adding a redundant internal node for a single segment.
            if (group_size == 1U) {
                const auto& item = items_[group_begin];
                payload_.nodes[node_index].children[slot] =
                    make_child(
                        bounds,
                        item.segment_root,
                        kB003MacroSegment);
                continue;
            }

            const auto child_index =
                build(group_begin, group_end, depth + 1U);
            payload_.nodes[node_index].children[slot] =
                make_child(
                    bounds,
                    child_index,
                    kB003MacroInternal);
        }

        return node_index;
    }

    std::vector<MacroItem> items_;
    B003MacroBvh8Payload payload_;
};

} // namespace b003_detail

[[nodiscard]] inline B003MacroBvh8Payload
make_b003_macro_bvh8(
    const HierarchicalFlatPayload& flat) {
    std::vector<b003_detail::MacroItem> items;
    items.reserve(flat.segments.size());

    for (const auto& segment : flat.segments) {
        if (segment.root == kInvalidId) continue;
        if (segment.root >= flat.nodes.size()) {
            throw std::runtime_error(
                "B003 macro segment root is outside flat node buffer");
        }
        items.push_back({
            flat.nodes[segment.root].bounds,
            segment.root,
        });
    }

    return b003_detail::MacroBuilder(
        std::move(items)).finish();
}

[[nodiscard]] inline std::size_t
b003_macro_persistent_bytes(
    const B003MacroBvh8Payload& payload) noexcept {
    return payload.nodes.size() *
        sizeof(B003GpuMacroNode);
}

} // namespace phos::gi::research::lane_b

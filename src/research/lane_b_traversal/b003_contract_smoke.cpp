#include "b003_macro_bvh8.hpp"

#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::lane_b {
namespace {

[[nodiscard]] bool finite_bounds(
    const B003GpuMacroChild& child) noexcept {
    for (int axis = 0; axis < 3; ++axis) {
        if (!std::isfinite(child.bounds_min[axis]) ||
            !std::isfinite(child.bounds_max[axis]) ||
            child.bounds_min[axis] >
                child.bounds_max[axis]) {
            return false;
        }
    }
    return true;
}

void verify_payload(
    const HierarchicalFlatPayload& flat,
    const B003MacroBvh8Payload& payload) {
    if (flat.segments.empty()) {
        if (payload.root != kInvalidId ||
            !payload.nodes.empty() ||
            payload.segment_count != 0) {
            throw std::runtime_error(
                "empty B003 macro payload is not empty");
        }
        return;
    }

    if (payload.root >= payload.nodes.size()) {
        throw std::runtime_error(
            "B003 macro root is invalid");
    }
    if (payload.max_stack_entries > 32U) {
        throw std::runtime_error(
            "B003 smoke exceeds shader macro stack");
    }

    std::vector<std::uint32_t> expected;
    expected.reserve(flat.segments.size());
    for (const auto& segment : flat.segments) {
        expected.push_back(segment.root);
    }

    std::vector<std::uint32_t> observed;
    std::vector<bool> visited(
        payload.nodes.size(),
        false);
    std::vector<std::uint32_t> stack{
        payload.root};

    while (!stack.empty()) {
        const auto node_index = stack.back();
        stack.pop_back();
        if (node_index >= payload.nodes.size() ||
            visited[node_index]) {
            throw std::runtime_error(
                "B003 macro payload contains a cycle or invalid node");
        }
        visited[node_index] = true;

        for (const auto& child :
             payload.nodes[node_index].children) {
            if (child.data[0] == kInvalidId) {
                continue;
            }
            if (!finite_bounds(child)) {
                throw std::runtime_error(
                    "B003 macro payload contains invalid bounds");
            }
            if (child.data[1] == kB003MacroInternal) {
                stack.push_back(child.data[0]);
            } else if (
                child.data[1] ==
                kB003MacroSegment) {
                observed.push_back(child.data[0]);
            } else {
                throw std::runtime_error(
                    "B003 macro payload contains invalid child kind");
            }
        }
    }

    std::sort(expected.begin(), expected.end());
    std::sort(observed.begin(), observed.end());
    if (observed != expected) {
        throw std::runtime_error(
            "B003 macro payload changed segment-root membership");
    }
}

[[nodiscard]] HierarchicalFlatPayload
make_control(std::uint32_t segments) {
    HierarchicalFlatPayload flat;
    flat.nodes.reserve(segments);
    flat.segments.reserve(segments);

    for (std::uint32_t index = 0;
         index < segments;
         ++index) {
        const float x =
            static_cast<float>(index % 17U);
        const float y =
            static_cast<float>(
                (index / 17U) % 7U);
        const float z =
            static_cast<float>(index / 119U);
        const Aabb bounds{
            {x, y, z},
            {x + 0.75F, y + 0.5F, z + 1.0F},
        };
        flat.nodes.push_back({
            bounds,
            kInvalidId,
            kInvalidId,
            0U,
            0U,
        });
        flat.segments.push_back({
            {
                static_cast<std::int32_t>(index),
                0,
                0,
            },
            index,
        });
        flat.occupied_bounds =
            merge(
                flat.occupied_bounds,
                bounds);
    }
    return flat;
}

} // namespace
} // namespace phos::gi::research::lane_b

int main() {
    using namespace phos::gi::research::lane_b;

    try {
        HierarchicalFlatPayload empty;
        verify_payload(
            empty,
            make_b003_macro_bvh8(empty));

        for (const auto count :
             {1U, 8U, 9U, 64U, 257U, 682U}) {
            const auto flat =
                make_control(count);
            const auto payload =
                make_b003_macro_bvh8(flat);
            verify_payload(flat, payload);
        }

        std::cout
            << "B003 macro BVH8 structural smoke: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "B003 macro BVH8 structural smoke: FAIL: "
            << error.what()
            << '\n';
        return 1;
    }
}

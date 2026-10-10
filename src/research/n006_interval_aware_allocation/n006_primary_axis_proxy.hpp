#pragma once
// N006-only metadata packing for software-primary traversal.
// Internal GpuBvhNode.data[2] is unused by accepted N003 shaders; leaves retain
// data[2] as ordered primitive begin. Zero means coincident centers / default order.
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::integration {
template <class GpuNode>
[[nodiscard]] inline std::size_t n006_pack_primary_axis_proxy(
    std::vector<GpuNode>& nodes) {
    std::size_t packed = 0;
    for (auto& node : nodes) {
        if (node.data[0] == std::numeric_limits<std::uint32_t>::max())
            continue; // leaf: data[2] stores ordered begin
        const auto left = node.data[0], right = node.data[1];
        if (left >= nodes.size() || right >= nodes.size() || left == right)
            throw std::runtime_error("N006 B1c invalid BVH children");
        float delta[3]{};
        for (int a = 0; a != 3; ++a) {
            const auto& l = nodes[left];
            const auto& r = nodes[right];
            delta[a] = (r.bounds_min[a] * 0.5F + r.bounds_max[a] * 0.5F) -
                       (l.bounds_min[a] * 0.5F + l.bounds_max[a] * 0.5F);
            if (!std::isfinite(delta[a]))
                throw std::runtime_error("N006 B1c invalid BVH bounds");
        }
        std::uint32_t axis = 0;
        for (std::uint32_t a = 1; a < 3; ++a)
            if (std::abs(delta[a]) > std::abs(delta[axis])) axis = a;
        // 0 = equal child centers => original x-then-y stack order.
        // 1..3 = left center lower on X/Y/Z, 4..6 = right center lower.
        node.data[2] = delta[axis] == 0.0F ? 0U
                     : 1U + axis + (delta[axis] < 0.0F ? 3U : 0U);
        ++packed;
    }
    return packed;
}
} // namespace phos::gi::research::integration

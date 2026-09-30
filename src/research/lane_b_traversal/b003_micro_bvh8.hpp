#pragma once

#include "b002_gpu_layout.hpp"
#include "hierarchical_stratabrick.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>

namespace phos::gi::research::lane_b {

inline constexpr std::uint32_t kB003WideLeafBit = 0x80000000U;
inline constexpr std::uint32_t kB003WideCountShift = 28U;
inline constexpr std::uint32_t kB003WideCountMask = 0x70000000U;
inline constexpr std::uint32_t kB003WideBeginMask = 0x0fffffffU;

[[nodiscard]] inline bool
b003_wide_is_leaf(std::uint32_t token) noexcept {
    return (token & kB003WideLeafBit) != 0U;
}

[[nodiscard]] inline std::uint32_t
b003_wide_leaf_begin(std::uint32_t token) noexcept {
    return token & kB003WideBeginMask;
}

[[nodiscard]] inline std::uint32_t
b003_wide_leaf_count(std::uint32_t token) noexcept {
    return ((token & kB003WideCountMask) >>
            kB003WideCountShift) +
        1U;
}

[[nodiscard]] inline std::uint32_t
b003_wide_leaf_token(
    std::uint32_t begin,
    std::uint32_t count) {
    if (count == 0U || count > 8U ||
        begin > kB003WideBeginMask) {
        throw std::runtime_error(
            "B003 wide leaf cannot be encoded");
    }
    return kB003WideLeafBit |
        ((count - 1U) << kB003WideCountShift) |
        begin;
}

struct alignas(16) B003GpuWideChild {
    float bounds_min[4]{};
    float bounds_max[4]{};
    std::uint32_t data[4]{
        kInvalidId,
        0U,
        0U,
        0U,
    };
};
static_assert(sizeof(B003GpuWideChild) == 48);

struct alignas(16) B003GpuWideNode {
    B003GpuWideChild children[8]{};
};
static_assert(sizeof(B003GpuWideNode) == 384);

struct B003WideMicroPayload {
    std::vector<B003GpuWideNode> nodes;
    std::vector<std::uint32_t> ordered_primitives;
    std::vector<GpuSegmentHashEntry> hash_table;
    Aabb occupied_bounds{};
    std::uint32_t hash_mask{};
    std::uint32_t hash_max_probe{};
    std::size_t max_depth{};
    std::size_t max_stack_entries{};
    std::size_t segment_count{};
};

namespace b003_wide_detail {

[[nodiscard]] inline float area(
    const Aabb& bounds) noexcept {
    const auto extent = bounds.max - bounds.min;
    return 2.0F * (
        std::max(0.0F, extent.x) *
            std::max(0.0F, extent.y) +
        std::max(0.0F, extent.y) *
            std::max(0.0F, extent.z) +
        std::max(0.0F, extent.z) *
            std::max(0.0F, extent.x));
}

[[nodiscard]] inline float axis_value(
    Vec3 value,
    int axis) noexcept {
    return axis == 0
        ? value.x
        : (axis == 1 ? value.y : value.z);
}

class WideBuilder {
public:
    explicit WideBuilder(
        const HierarchicalFlatPayload& flat)
        : flat_(flat) {
        payload_.ordered_primitives =
            flat.ordered_primitives;
        payload_.occupied_bounds =
            flat.occupied_bounds;

        std::vector<std::pair<SegmentCoord, std::uint32_t>>
            roots;
        roots.reserve(flat.segments.size());

        for (const auto& segment : flat.segments) {
            if (segment.root == kInvalidId) continue;
            if (segment.root >= flat.nodes.size()) {
                throw std::runtime_error(
                    "B003 wide micro segment root is invalid");
            }
            roots.push_back({
                segment.coord,
                build_node(segment.root, 1U),
            });
        }

        payload_.segment_count = roots.size();
        build_hash(roots);
        compute_stack_bound(roots);
    }

    [[nodiscard]] B003WideMicroPayload finish() && {
        return std::move(payload_);
    }

private:
    [[nodiscard]] bool binary_leaf(
        std::uint32_t index) const {
        if (index >= flat_.nodes.size()) {
            throw std::runtime_error(
                "B003 wide micro binary node index is invalid");
        }
        return flat_.nodes[index].left == kInvalidId;
    }

    [[nodiscard]] int split_axis(
        const std::vector<std::uint32_t>& frontier) const {
        Aabb centers{};
        for (const auto index : frontier) {
            const auto point =
                center(flat_.nodes[index].bounds);
            centers = merge(
                centers,
                {point, point});
        }
        const auto extent = centers.max - centers.min;
        return
            (extent.y > extent.x &&
             extent.y >= extent.z)
            ? 1
            : (extent.z > extent.x ? 2 : 0);
    }

    [[nodiscard]] std::uint32_t build_node(
        std::uint32_t binary_root,
        std::size_t depth) {
        if (payload_.nodes.size() >=
            kB003WideLeafBit) {
            throw std::runtime_error(
                "B003 wide micro exceeds token index capacity");
        }

        std::vector<std::uint32_t> frontier{
            binary_root};

        // Collapse the binary tree by repeatedly expanding the largest
        // internal child until this wide node has at most eight children.
        while (frontier.size() < 8U) {
            std::size_t selected =
                std::numeric_limits<std::size_t>::max();
            float selected_area = -1.0F;

            for (std::size_t index = 0;
                 index < frontier.size();
                 ++index) {
                if (binary_leaf(frontier[index])) {
                    continue;
                }
                const auto candidate_area =
                    area(flat_.nodes[
                        frontier[index]].bounds);
                if (candidate_area >
                    selected_area) {
                    selected = index;
                    selected_area =
                        candidate_area;
                }
            }

            if (selected ==
                std::numeric_limits<std::size_t>::max()) {
                break;
            }

            const auto binary =
                flat_.nodes[frontier[selected]];
            frontier[selected] = binary.left;
            frontier.insert(
                frontier.begin() +
                    static_cast<std::ptrdiff_t>(
                        selected + 1U),
                binary.right);
        }

        const int axis = split_axis(frontier);
        std::stable_sort(
            frontier.begin(),
            frontier.end(),
            [&](std::uint32_t a, std::uint32_t b) {
                const auto ca =
                    axis_value(
                        center(flat_.nodes[a].bounds),
                        axis);
                const auto cb =
                    axis_value(
                        center(flat_.nodes[b].bounds),
                        axis);
                return ca == cb ? a < b : ca < cb;
            });

        const auto output_index =
            static_cast<std::uint32_t>(
                payload_.nodes.size());
        payload_.nodes.emplace_back();
        payload_.max_depth =
            std::max(payload_.max_depth, depth);

        for (std::size_t slot = 0;
             slot < frontier.size();
             ++slot) {
            const auto binary_index =
                frontier[slot];
            const auto& binary =
                flat_.nodes[binary_index];

            std::uint32_t token{};
            if (binary.left == kInvalidId) {
                token = b003_wide_leaf_token(
                    binary.begin,
                    binary.count);
            } else {
                token = build_node(
                    binary_index,
                    depth + 1U);
            }

            auto& child =
                payload_.nodes[
                    output_index].children[slot];
            child.bounds_min[0] =
                binary.bounds.min.x;
            child.bounds_min[1] =
                binary.bounds.min.y;
            child.bounds_min[2] =
                binary.bounds.min.z;
            child.bounds_max[0] =
                binary.bounds.max.x;
            child.bounds_max[1] =
                binary.bounds.max.y;
            child.bounds_max[2] =
                binary.bounds.max.z;
            child.data[0] = token;
            child.data[1] =
                static_cast<std::uint32_t>(axis);
        }

        return output_index;
    }

    void build_hash(
        const std::vector<
            std::pair<SegmentCoord, std::uint32_t>>& roots) {
        std::size_t table_size = 1U;
        const auto target =
            std::max<std::size_t>(
                2U,
                roots.size() * 2U);
        while (table_size < target) {
            table_size <<= 1U;
        }
        if (table_size >
            std::numeric_limits<std::uint32_t>::max()) {
            throw std::runtime_error(
                "B003 wide micro hash exceeds 32-bit capacity");
        }

        payload_.hash_table.resize(table_size);
        payload_.hash_mask =
            static_cast<std::uint32_t>(
                table_size - 1U);

        for (const auto& [coord, root] : roots) {
            std::uint32_t slot =
                segment_hash(coord) &
                payload_.hash_mask;
            std::uint32_t probe = 1U;

            while (payload_.hash_table[
                       slot].metadata[0] !=
                   kInvalidId) {
                slot =
                    (slot + 1U) &
                    payload_.hash_mask;
                ++probe;
                if (probe > table_size) {
                    throw std::runtime_error(
                        "B003 wide micro hash insertion failed");
                }
            }

            auto& entry =
                payload_.hash_table[slot];
            entry.coord[0] = coord.x;
            entry.coord[1] = coord.y;
            entry.coord[2] = coord.z;
            entry.metadata[0] = root;
            payload_.hash_max_probe =
                std::max(
                    payload_.hash_max_probe,
                    probe);
        }
    }

    void compute_stack_bound(
        const std::vector<
            std::pair<SegmentCoord, std::uint32_t>>& roots) {
        payload_.max_stack_entries = 1U;

        for (const auto& [coord, root] : roots) {
            (void)coord;
            std::vector<std::uint32_t> stack{
                root};
            while (!stack.empty()) {
                const auto token = stack.back();
                stack.pop_back();

                if (b003_wide_is_leaf(token)) {
                    continue;
                }
                if (token >= payload_.nodes.size()) {
                    throw std::runtime_error(
                        "B003 wide micro internal token is invalid");
                }

                for (const auto& child :
                     payload_.nodes[token].children) {
                    if (child.data[0] == kInvalidId) {
                        continue;
                    }
                    stack.push_back(
                        child.data[0]);
                }
                payload_.max_stack_entries =
                    std::max(
                        payload_.max_stack_entries,
                        stack.size());
            }
        }
    }

    const HierarchicalFlatPayload& flat_;
    B003WideMicroPayload payload_;
};

} // namespace b003_wide_detail

[[nodiscard]] inline B003WideMicroPayload
make_b003_wide_micro_payload(
    const HierarchicalFlatPayload& flat) {
    return b003_wide_detail::WideBuilder(
        flat).finish();
}

} // namespace phos::gi::research::lane_b

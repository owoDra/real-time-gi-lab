#include "j003_persistent_layout.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <functional>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <tuple>
#include <unordered_set>
#include <utility>
#include <vector>

namespace phos::gi::research::lane_j {
namespace {

struct Bounds {
    double min[3]{
        std::numeric_limits<double>::infinity(),
        std::numeric_limits<double>::infinity(),
        std::numeric_limits<double>::infinity(),
    };
    double max[3]{
        -std::numeric_limits<double>::infinity(),
        -std::numeric_limits<double>::infinity(),
        -std::numeric_limits<double>::infinity(),
    };
};

[[nodiscard]] GpuTriangle to_gpu_triangle(const Triangle& triangle) {
    GpuTriangle result{};
    result.v0 = {triangle.v0.x, triangle.v0.y, triangle.v0.z, 0.0F};
    result.v1 = {triangle.v1.x, triangle.v1.y, triangle.v1.z, 0.0F};
    result.v2 = {triangle.v2.x, triangle.v2.y, triangle.v2.z, 0.0F};
    result.meta = {
        triangle.primitive_id,
        triangle.material_id,
        triangle.instance_id,
        triangle.two_sided ? 1U : 0U,
    };
    return result;
}

void include(Bounds& bounds, double x, double y, double z) {
    bounds.min[0] = std::min(bounds.min[0], x);
    bounds.min[1] = std::min(bounds.min[1], y);
    bounds.min[2] = std::min(bounds.min[2], z);
    bounds.max[0] = std::max(bounds.max[0], x);
    bounds.max[1] = std::max(bounds.max[1], y);
    bounds.max[2] = std::max(bounds.max[2], z);
}

void include(Bounds& bounds, const Triangle& triangle) {
    include(bounds, triangle.v0.x, triangle.v0.y, triangle.v0.z);
    include(bounds, triangle.v1.x, triangle.v1.y, triangle.v1.z);
    include(bounds, triangle.v2.x, triangle.v2.y, triangle.v2.z);
}

[[nodiscard]] Bounds bounds_of(std::span<const Triangle> triangles) {
    if (triangles.empty()) {
        throw std::runtime_error("persistent cluster bounds require triangles");
    }
    Bounds bounds{};
    for (const auto& triangle : triangles) {
        include(bounds, triangle);
    }
    return bounds;
}

[[nodiscard]] Bounds merge(const Bounds& a, const Bounds& b) {
    Bounds result{};
    for (std::uint32_t axis = 0U; axis < 3U; ++axis) {
        result.min[axis] = std::min(a.min[axis], b.min[axis]);
        result.max[axis] = std::max(a.max[axis], b.max[axis]);
    }
    return result;
}

[[nodiscard]] Bounds bounds_of(const GpuCluster& cluster) {
    Bounds bounds{};
    for (std::uint32_t axis = 0U; axis < 3U; ++axis) {
        bounds.min[axis] = cluster.bounds_min[axis];
        bounds.max[axis] = cluster.bounds_max[axis];
    }
    return bounds;
}

[[nodiscard]] Bounds bounds_of(const GpuBvhNode& node) {
    Bounds bounds{};
    for (std::uint32_t axis = 0U; axis < 3U; ++axis) {
        bounds.min[axis] = node.bounds_min[axis];
        bounds.max[axis] = node.bounds_max[axis];
    }
    return bounds;
}

[[nodiscard]] std::array<double, 3> center(const Bounds& bounds) {
    return {
        (bounds.min[0] + bounds.max[0]) * 0.5,
        (bounds.min[1] + bounds.max[1]) * 0.5,
        (bounds.min[2] + bounds.max[2]) * 0.5,
    };
}

[[nodiscard]] std::array<double, 3> centroid(const Triangle& triangle) {
    return {
        (double(triangle.v0.x) + double(triangle.v1.x) +
         double(triangle.v2.x)) /
            3.0,
        (double(triangle.v0.y) + double(triangle.v1.y) +
         double(triangle.v2.y)) /
            3.0,
        (double(triangle.v0.z) + double(triangle.v1.z) +
         double(triangle.v2.z)) /
            3.0,
    };
}

[[nodiscard]] std::uint32_t spread10(std::uint32_t value) {
    std::uint32_t result = 0U;
    for (std::uint32_t bit = 0U; bit < 10U; ++bit) {
        result |= ((value >> bit) & 1U) << (3U * bit);
    }
    return result;
}

[[nodiscard]] std::uint32_t quantize10(
    double value,
    double low,
    double high) {
    const auto extent = std::max(high - low, 1.0e-9);
    const auto scaled = (value - low) / extent * 1023.0 + 0.5;
    return static_cast<std::uint32_t>(
        std::clamp(static_cast<int>(scaled), 0, 1023));
}

[[nodiscard]] std::uint32_t morton10(
    const std::array<double, 3>& point,
    const Bounds& bounds) {
    const auto x = quantize10(point[0], bounds.min[0], bounds.max[0]);
    const auto y = quantize10(point[1], bounds.min[1], bounds.max[1]);
    const auto z = quantize10(point[2], bounds.min[2], bounds.max[2]);
    return spread10(x) | (spread10(y) << 1U) | (spread10(z) << 2U);
}

[[nodiscard]] std::vector<std::uint32_t> morton_triangle_order(
    std::span<const Triangle> triangles) {
    Bounds centroid_bounds{};
    for (const auto& triangle : triangles) {
        const auto c = centroid(triangle);
        include(centroid_bounds, c[0], c[1], c[2]);
    }

    std::vector<std::uint32_t> order(triangles.size());
    std::iota(order.begin(), order.end(), 0U);
    std::sort(
        order.begin(),
        order.end(),
        [&](std::uint32_t a, std::uint32_t b) {
            const auto code_a =
                morton10(centroid(triangles[a]), centroid_bounds);
            const auto code_b =
                morton10(centroid(triangles[b]), centroid_bounds);
            return std::tuple{code_a, triangles[a].primitive_id} <
                   std::tuple{code_b, triangles[b].primitive_id};
        });
    return order;
}

[[nodiscard]] GpuBvhNode make_node(
    const Bounds& bounds,
    std::uint32_t left,
    std::uint32_t right,
    std::uint32_t payload,
    std::uint32_t leaf_count) {
    GpuBvhNode node{};
    node.bounds_min = {
        static_cast<float>(bounds.min[0]),
        static_cast<float>(bounds.min[1]),
        static_cast<float>(bounds.min[2]),
        0.0F,
    };
    node.bounds_max = {
        static_cast<float>(bounds.max[0]),
        static_cast<float>(bounds.max[1]),
        static_cast<float>(bounds.max[2]),
        0.0F,
    };
    node.meta = {left, right, payload, leaf_count};
    return node;
}

[[nodiscard]] GpuBvhNode invalid_node() {
    GpuBvhNode node{};
    node.meta = {kInvalidId, kInvalidId, kInvalidId, 0U};
    return node;
}

} // namespace

std::uint32_t PersistentClusterLayout::next_power_of_two(
    std::uint32_t value) {
    if (value == 0U) {
        throw std::runtime_error("persistent layout requires active clusters");
    }
    std::uint32_t result = 1U;
    while (result < value) {
        if (result > std::numeric_limits<std::uint32_t>::max() / 2U) {
            throw std::runtime_error("persistent slot capacity overflow");
        }
        result *= 2U;
    }
    return result;
}

PersistentClusterLayout::PersistentClusterLayout(
    const ClusterTransitionState& state) {
    active_cluster_count_ =
        static_cast<std::uint32_t>(state.clusters().size());
    slot_capacity_ = next_power_of_two(active_cluster_count_);
    resize_capacity(slot_capacity_);

    std::vector<const TransitionCluster*> ordered;
    ordered.reserve(state.clusters().size());
    for (const auto& cluster : state.clusters()) {
        ordered.push_back(&cluster);
    }
    std::sort(
        ordered.begin(),
        ordered.end(),
        [](const TransitionCluster* a, const TransitionCluster* b) {
            return a->cluster_id < b->cluster_id;
        });

    for (const auto* cluster : ordered) {
        const auto slot = allocate_slot();
        logical_to_slot_.emplace(cluster->cluster_id, slot);
        slot_to_logical_[slot] = cluster->cluster_id;
        rebuild_cluster_slot(slot, *cluster);
    }
    rebuild_upper(state);
}

std::uint32_t PersistentClusterLayout::allocate_slot() {
    for (std::uint32_t slot = 0U; slot < slot_capacity_; ++slot) {
        if (slot_to_logical_[slot] == kInvalidId) {
            return slot;
        }
    }
    throw std::runtime_error("persistent layout has no free physical slot");
}

void PersistentClusterLayout::resize_capacity(
    std::uint32_t new_capacity) {
    if (new_capacity < active_cluster_count_) {
        throw std::runtime_error("persistent slot resize below active count");
    }
    slot_capacity_ = new_capacity;
    slot_to_logical_.resize(slot_capacity_, kInvalidId);
    triangles_.resize(
        std::size_t(slot_capacity_) * kTrianglesPerPhysicalSlot);
    micro_nodes_.resize(
        std::size_t(slot_capacity_) * kMicroNodesPerPhysicalSlot,
        invalid_node());
    clusters_.resize(slot_capacity_);
    upper_nodes_.resize(
        std::size_t(slot_capacity_) * 2U - 1U,
        invalid_node());
    upper_parent_.resize(upper_nodes_.size(), kInvalidId);
    slot_to_upper_leaf_.resize(slot_capacity_, kInvalidId);
}

void PersistentClusterLayout::rebuild_cluster_slot(
    std::uint32_t physical_slot,
    const TransitionCluster& cluster) {
    if (physical_slot >= slot_capacity_) {
        throw std::runtime_error("persistent cluster slot out of range");
    }
    if (cluster.triangles.empty() ||
        cluster.triangles.size() > kTrianglesPerPhysicalSlot) {
        throw std::runtime_error("persistent cluster occupancy invalid");
    }

    const auto triangle_base =
        std::size_t(physical_slot) * kTrianglesPerPhysicalSlot;
    const auto micro_base =
        std::size_t(physical_slot) * kMicroNodesPerPhysicalSlot;

    for (std::uint32_t i = 0U; i < kTrianglesPerPhysicalSlot; ++i) {
        triangles_[triangle_base + i] = {};
    }
    for (std::uint32_t i = 0U; i < kMicroNodesPerPhysicalSlot; ++i) {
        micro_nodes_[micro_base + i] = invalid_node();
    }

    const auto order = morton_triangle_order(cluster.triangles);
    for (std::size_t local = 0U; local < order.size(); ++local) {
        triangles_[triangle_base + local] =
            to_gpu_triangle(cluster.triangles[order[local]]);
    }

    std::uint32_t next_local_node = 0U;
    std::function<std::pair<std::uint32_t, Bounds>(
        std::size_t, std::size_t)> build =
        [&](std::size_t begin, std::size_t end)
        -> std::pair<std::uint32_t, Bounds> {
        const auto local_node = next_local_node++;
        if (local_node >= kMicroNodesPerPhysicalSlot) {
            throw std::runtime_error("micro-BVH slot overflow");
        }
        const auto absolute_node =
            static_cast<std::uint32_t>(micro_base + local_node);

        if (end - begin == 1U) {
            const auto local_triangle = begin;
            const auto& source =
                cluster.triangles[order[local_triangle]];
            const auto bounds = bounds_of(
                std::span<const Triangle>(&source, 1U));
            micro_nodes_[absolute_node] = make_node(
                bounds,
                kInvalidId,
                kInvalidId,
                static_cast<std::uint32_t>(
                    triangle_base + local_triangle),
                1U);
            return {absolute_node, bounds};
        }

        const auto middle = begin + (end - begin) / 2U;
        const auto [left, left_bounds] = build(begin, middle);
        const auto [right, right_bounds] = build(middle, end);
        const auto bounds = merge(left_bounds, right_bounds);
        micro_nodes_[absolute_node] = make_node(
            bounds,
            left,
            right,
            kInvalidId,
            0U);
        return {absolute_node, bounds};
    };

    const auto [root, root_bounds] = build(0U, order.size());
    GpuCluster metadata{};
    metadata.bounds_min = {
        static_cast<float>(root_bounds.min[0]),
        static_cast<float>(root_bounds.min[1]),
        static_cast<float>(root_bounds.min[2]),
        0.0F,
    };
    metadata.bounds_max = {
        static_cast<float>(root_bounds.max[0]),
        static_cast<float>(root_bounds.max[1]),
        static_cast<float>(root_bounds.max[2]),
        0.0F,
    };
    metadata.meta = {
        root,
        cluster.cluster_id,
        static_cast<std::uint32_t>(cluster.triangles.size()),
        0U,
    };
    clusters_[physical_slot] = metadata;
}

void PersistentClusterLayout::rebuild_upper(
    const ClusterTransitionState& state) {
    if (state.clusters().empty()) {
        throw std::runtime_error("upper BVH requires active clusters");
    }

    std::vector<std::uint32_t> slots;
    slots.reserve(state.clusters().size());
    Bounds centroid_bounds{};
    for (const auto& cluster : state.clusters()) {
        const auto slot = physical_slot(cluster.cluster_id);
        slots.push_back(slot);
        const auto c = center(bounds_of(clusters_[slot]));
        include(centroid_bounds, c[0], c[1], c[2]);
    }

    std::sort(
        slots.begin(),
        slots.end(),
        [&](std::uint32_t a, std::uint32_t b) {
            const auto ca = center(bounds_of(clusters_[a]));
            const auto cb = center(bounds_of(clusters_[b]));
            const auto code_a = morton10(ca, centroid_bounds);
            const auto code_b = morton10(cb, centroid_bounds);
            return std::tuple{code_a, clusters_[a].meta[1]} <
                   std::tuple{code_b, clusters_[b].meta[1]};
        });

    std::fill(upper_nodes_.begin(), upper_nodes_.end(), invalid_node());
    std::fill(upper_parent_.begin(), upper_parent_.end(), kInvalidId);
    std::fill(slot_to_upper_leaf_.begin(), slot_to_upper_leaf_.end(), kInvalidId);
    std::uint32_t next_node = 0U;
    std::function<std::pair<std::uint32_t, Bounds>(
        std::size_t, std::size_t)> build =
        [&](std::size_t begin, std::size_t end)
        -> std::pair<std::uint32_t, Bounds> {
        const auto node = next_node++;
        if (node >= upper_nodes_.size()) {
            throw std::runtime_error("upper BVH capacity overflow");
        }

        if (end - begin == 1U) {
            const auto slot = slots[begin];
            const auto bounds = bounds_of(clusters_[slot]);
            upper_nodes_[node] = make_node(
                bounds,
                kInvalidId,
                kInvalidId,
                slot,
                1U);
            slot_to_upper_leaf_[slot] = node;
            return {node, bounds};
        }

        const auto middle = begin + (end - begin) / 2U;
        const auto [left, left_bounds] = build(begin, middle);
        const auto [right, right_bounds] = build(middle, end);
        const auto bounds = merge(left_bounds, right_bounds);
        upper_nodes_[node] = make_node(
            bounds,
            left,
            right,
            kInvalidId,
            0U);
        upper_parent_[left] = node;
        upper_parent_[right] = node;
        return {node, bounds};
    };

    const auto [root, bounds] = build(0U, slots.size());
    (void)bounds;
    upper_root_ = root;
    upper_node_count_ = next_node;
}

std::vector<std::uint32_t> PersistentClusterLayout::refit_upper(
    std::span<const std::uint32_t> dirty_physical_slots) {
    if (upper_root_ == kInvalidId || upper_root_ >= upper_node_count_) {
        throw std::runtime_error("upper refit missing root");
    }

    std::unordered_set<std::uint32_t> affected;
    for (const auto slot : dirty_physical_slots) {
        if (slot >= slot_to_upper_leaf_.size()) {
            throw std::runtime_error("upper refit slot out of range");
        }
        auto node = slot_to_upper_leaf_[slot];
        if (node == kInvalidId) {
            throw std::runtime_error("dirty slot has no upper leaf");
        }

        const auto bounds = bounds_of(clusters_[slot]);
        upper_nodes_[node].bounds_min = {
            static_cast<float>(bounds.min[0]),
            static_cast<float>(bounds.min[1]),
            static_cast<float>(bounds.min[2]),
            0.0F,
        };
        upper_nodes_[node].bounds_max = {
            static_cast<float>(bounds.max[0]),
            static_cast<float>(bounds.max[1]),
            static_cast<float>(bounds.max[2]),
            0.0F,
        };

        for (;;) {
            affected.insert(node);
            const auto parent = upper_parent_[node];
            if (parent == kInvalidId) {
                break;
            }
            node = parent;
        }
    }

    std::vector<std::uint32_t> internal;
    internal.reserve(affected.size());
    for (const auto node : affected) {
        if (upper_nodes_[node].meta[3] == 0U) {
            internal.push_back(node);
        }
    }
    std::sort(internal.begin(), internal.end(), std::greater<>());

    for (const auto node : internal) {
        const auto left = upper_nodes_[node].meta[0];
        const auto right = upper_nodes_[node].meta[1];
        const auto bounds =
            merge(bounds_of(upper_nodes_[left]), bounds_of(upper_nodes_[right]));
        upper_nodes_[node].bounds_min = {
            static_cast<float>(bounds.min[0]),
            static_cast<float>(bounds.min[1]),
            static_cast<float>(bounds.min[2]),
            0.0F,
        };
        upper_nodes_[node].bounds_max = {
            static_cast<float>(bounds.max[0]),
            static_cast<float>(bounds.max[1]),
            static_cast<float>(bounds.max[2]),
            0.0F,
        };
    }

    std::vector<std::uint32_t> dirty_nodes(
        affected.begin(),
        affected.end());
    std::sort(dirty_nodes.begin(), dirty_nodes.end());
    return dirty_nodes;
}

PersistentLayoutUpdate PersistentClusterLayout::synchronize(
    const ClusterTransitionState& state,
    const TransitionStats& transition) {
    const auto old_persistent_bytes =
        candidate_persistent_logical_bytes();

    for (const auto logical_id : transition.released_cluster_ids) {
        const auto found = logical_to_slot_.find(logical_id);
        if (found == logical_to_slot_.end()) {
            throw std::runtime_error("retired logical cluster has no slot");
        }
        const auto slot = found->second;
        slot_to_logical_[slot] = kInvalidId;
        logical_to_slot_.erase(found);
    }

    active_cluster_count_ =
        static_cast<std::uint32_t>(state.clusters().size());

    bool resized = false;
    if (active_cluster_count_ > slot_capacity_) {
        auto new_capacity = slot_capacity_;
        do {
            new_capacity *= 2U;
        } while (new_capacity < active_cluster_count_);
        resize_capacity(new_capacity);
        resized = true;
    }

    std::vector<const TransitionCluster*> ordered;
    ordered.reserve(state.clusters().size());
    for (const auto& cluster : state.clusters()) {
        ordered.push_back(&cluster);
    }
    std::sort(
        ordered.begin(),
        ordered.end(),
        [](const TransitionCluster* a, const TransitionCluster* b) {
            return a->cluster_id < b->cluster_id;
        });

    for (const auto* cluster : ordered) {
        if (logical_to_slot_.contains(cluster->cluster_id)) {
            continue;
        }
        const auto slot = allocate_slot();
        logical_to_slot_.emplace(cluster->cluster_id, slot);
        slot_to_logical_[slot] = cluster->cluster_id;
    }

    std::unordered_set<std::uint32_t> dirty_set(
        transition.dirty_cluster_ids.begin(),
        transition.dirty_cluster_ids.end());
    std::vector<std::uint32_t> dirty_slots;
    for (const auto* cluster : ordered) {
        const auto is_new =
            clusters_[physical_slot(cluster->cluster_id)].meta[1] !=
            cluster->cluster_id;
        if (!dirty_set.contains(cluster->cluster_id) && !is_new) {
            continue;
        }
        const auto slot = physical_slot(cluster->cluster_id);
        rebuild_cluster_slot(slot, *cluster);
        dirty_slots.push_back(slot);
    }
    std::sort(dirty_slots.begin(), dirty_slots.end());
    dirty_slots.erase(
        std::unique(dirty_slots.begin(), dirty_slots.end()),
        dirty_slots.end());

    PersistentLayoutUpdate result{};
    result.resized = resized;
    result.slot_capacity = slot_capacity_;
    result.active_cluster_count = active_cluster_count_;
    result.dirty_slot_count =
        static_cast<std::uint32_t>(dirty_slots.size());
    result.dirty_physical_slots = dirty_slots;

    if (transition.cluster_set_changed) {
        rebuild_upper(state);
        result.upper_rebuilt = true;
        result.upper_rebuild_node_count = upper_node_count_;
    } else {
        result.dirty_upper_nodes = refit_upper(dirty_slots);
        result.upper_refit_node_count =
            static_cast<std::uint32_t>(result.dirty_upper_nodes.size());
    }

    if (logical_to_slot_.size() != state.clusters().size()) {
        throw std::runtime_error("persistent logical/physical ownership leak");
    }
    for (const auto& cluster : state.clusters()) {
        const auto slot = physical_slot(cluster.cluster_id);
        if (slot_to_logical_[slot] != cluster.cluster_id) {
            throw std::runtime_error("persistent slot ownership mismatch");
        }
    }

    result.candidate_persistent_logical_bytes =
        candidate_persistent_logical_bytes();
    if (resized) {
        result.resize_old_new_overlap_logical_bytes =
            old_persistent_bytes +
            result.candidate_persistent_logical_bytes;
    }
    return result;
}

std::uint32_t PersistentClusterLayout::physical_slot(
    std::uint32_t logical_cluster_id) const {
    const auto found = logical_to_slot_.find(logical_cluster_id);
    if (found == logical_to_slot_.end()) {
        throw std::runtime_error("logical cluster has no physical slot");
    }
    return found->second;
}

std::size_t PersistentClusterLayout::candidate_persistent_logical_bytes()
    const noexcept {
    return triangles_.size() * sizeof(GpuTriangle) +
           micro_nodes_.size() * sizeof(GpuBvhNode) +
           clusters_.size() * sizeof(GpuCluster) +
           upper_nodes_.size() * sizeof(GpuBvhNode);
}

} // namespace phos::gi::research::lane_j

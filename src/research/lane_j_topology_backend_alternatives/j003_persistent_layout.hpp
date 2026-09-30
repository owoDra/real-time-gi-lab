#pragma once

#include "j003_transition.hpp"
#include "j003_types.hpp"

#include <cstddef>
#include <cstdint>
#include <span>
#include <unordered_map>
#include <vector>

namespace phos::gi::research::lane_j {

constexpr std::uint32_t kTrianglesPerPhysicalSlot = kClusterMaximum;
constexpr std::uint32_t kMicroNodesPerPhysicalSlot =
    kClusterMaximum * 2U - 1U;

struct PersistentLayoutUpdate {
    bool resized{};
    bool upper_rebuilt{};
    std::uint32_t slot_capacity{};
    std::uint32_t active_cluster_count{};
    std::uint32_t dirty_slot_count{};
    std::uint32_t upper_refit_node_count{};
    std::uint32_t upper_rebuild_node_count{};
    std::size_t candidate_persistent_logical_bytes{};
    std::size_t resize_old_new_overlap_logical_bytes{};
    std::vector<std::uint32_t> dirty_physical_slots;
};

class PersistentClusterLayout {
public:
    explicit PersistentClusterLayout(
        const ClusterTransitionState& state);

    [[nodiscard]] PersistentLayoutUpdate synchronize(
        const ClusterTransitionState& state,
        const TransitionStats& transition);

    [[nodiscard]] std::uint32_t slot_capacity() const noexcept {
        return slot_capacity_;
    }
    [[nodiscard]] std::uint32_t active_cluster_count() const noexcept {
        return active_cluster_count_;
    }
    [[nodiscard]] std::uint32_t upper_root() const noexcept {
        return upper_root_;
    }
    [[nodiscard]] std::uint32_t upper_node_count() const noexcept {
        return upper_node_count_;
    }

    [[nodiscard]] const std::vector<GpuTriangle>& triangles() const noexcept {
        return triangles_;
    }
    [[nodiscard]] const std::vector<GpuBvhNode>& micro_nodes() const noexcept {
        return micro_nodes_;
    }
    [[nodiscard]] const std::vector<GpuCluster>& clusters() const noexcept {
        return clusters_;
    }
    [[nodiscard]] const std::vector<GpuBvhNode>& upper_nodes() const noexcept {
        return upper_nodes_;
    }

    [[nodiscard]] std::uint32_t physical_slot(
        std::uint32_t logical_cluster_id) const;

    [[nodiscard]] std::size_t candidate_persistent_logical_bytes() const noexcept;

private:
    [[nodiscard]] static std::uint32_t next_power_of_two(
        std::uint32_t value);
    [[nodiscard]] std::uint32_t allocate_slot();
    void resize_capacity(std::uint32_t new_capacity);
    void rebuild_cluster_slot(
        std::uint32_t physical_slot,
        const TransitionCluster& cluster);
    void rebuild_upper(const ClusterTransitionState& state);
    [[nodiscard]] std::uint32_t refit_upper_node(std::uint32_t node_index);

    std::uint32_t slot_capacity_{};
    std::uint32_t active_cluster_count_{};
    std::uint32_t upper_root_{kInvalidId};
    std::uint32_t upper_node_count_{};

    std::unordered_map<std::uint32_t, std::uint32_t> logical_to_slot_;
    std::vector<std::uint32_t> slot_to_logical_;

    std::vector<GpuTriangle> triangles_;
    std::vector<GpuBvhNode> micro_nodes_;
    std::vector<GpuCluster> clusters_;
    std::vector<GpuBvhNode> upper_nodes_;
};

} // namespace phos::gi::research::lane_j

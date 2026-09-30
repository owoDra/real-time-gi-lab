#pragma once

#include "j003_types.hpp"

#include <cstdint>
#include <span>
#include <unordered_map>
#include <vector>

namespace phos::gi::research::lane_j {

struct TransitionCluster {
    std::uint32_t cluster_id{};
    std::vector<Triangle> triangles;
};

struct TransitionStats {
    std::uint32_t cluster_count{};
    std::uint32_t dirty_cluster_count{};
    std::uint32_t changed_triangle_count{};
    std::uint32_t rebuilt_triangle_count{};
    std::uint32_t unaffected_cluster_rebuild_count{};
    std::uint32_t split_count{};
    std::uint32_t merge_count{};
    std::uint32_t retired_empty_cluster_count{};
    std::uint32_t occupancy_min{};
    std::uint32_t occupancy_max{};
    bool cluster_set_changed{};
    std::vector<std::uint32_t> dirty_cluster_ids;
    std::vector<std::uint32_t> retired_cluster_ids;
};

class ClusterTransitionState {
public:
    explicit ClusterTransitionState(std::span<const Triangle> triangles);

    [[nodiscard]] const std::vector<TransitionCluster>& clusters() const noexcept {
        return clusters_;
    }

    [[nodiscard]] TransitionStats update(std::span<const Triangle> triangles);

private:
    [[nodiscard]] std::uint32_t next_id() noexcept {
        return next_cluster_id_++;
    }

    std::vector<TransitionCluster> clusters_;
    std::uint32_t next_cluster_id_{};
};

} // namespace phos::gi::research::lane_j

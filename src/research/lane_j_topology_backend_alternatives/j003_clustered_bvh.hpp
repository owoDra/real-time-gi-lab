#pragma once

#include "j003_types.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace phos::gi::research::lane_j {

struct ClusterBuildSummary {
    std::uint32_t cluster_count{};
    std::uint32_t occupancy_min{};
    std::uint32_t occupancy_max{};
    std::uint32_t upper_node_count{};
    std::uint32_t micro_node_count{};
};

struct ClusteredBvhData {
    std::vector<GpuTriangle> triangles;
    std::vector<GpuCluster> clusters;
    std::vector<GpuBvhNode> upper_nodes;
    std::vector<GpuBvhNode> micro_nodes;
    std::uint32_t upper_root{kInvalidId};
    ClusterBuildSummary summary{};
};

// J003 initial clustering is setup-only: object-space Morton order followed by
// stable 48-triangle partitions. Per-transition update semantics remain owned by
// the v1.1/v1.2 state machine and are added separately.
[[nodiscard]] ClusteredBvhData build_initial_clustered_bvh(
    std::span<const Triangle> triangles);

[[nodiscard]] Aabb triangle_bounds(const Triangle& triangle);
[[nodiscard]] Aabb merge_bounds(const Aabb& a, const Aabb& b);

} // namespace phos::gi::research::lane_j

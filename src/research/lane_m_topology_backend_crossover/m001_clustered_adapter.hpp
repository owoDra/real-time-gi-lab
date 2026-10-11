#pragma once

#include "m001_contract.hpp"
#include "../lane_j_topology_backend_alternatives/j003_persistent_layout.hpp"
#include "../lane_j_topology_backend_alternatives/j003_transition.hpp"
#include "../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal/b002_vulkan.hpp"

#include <cstddef>
#include <cstdint>
#include <memory>
#include <span>
#include <vector>

namespace phos::gi::research::lane_m {

namespace lane_b = phos::gi::research::lane_b;
namespace lane_j = phos::gi::research::lane_j;

struct M001ClusteredTraversalPush {
    std::uint32_t ray_count{};
    std::uint32_t upper_root{};
    std::uint32_t upper_node_count{};
    std::uint32_t micro_node_count{};
    std::uint32_t cluster_count{};
    std::uint32_t triangle_count{};
};
static_assert(sizeof(M001ClusteredTraversalPush) == 24);

struct M001ClusteredUpdate {
    std::uint32_t changed_triangle_count{};
    std::uint32_t dirty_cluster_count{};
    std::uint32_t rebuilt_triangle_count{};
    std::uint32_t unaffected_cluster_rebuild_count{};
    std::uint32_t split_count{};
    std::uint32_t merge_count{};
    std::uint32_t retired_empty_cluster_count{};
    std::uint32_t upload_region_count{};
    std::size_t uploaded_logical_bytes{};
    std::size_t persistent_bytes{};
    std::size_t transient_staging_bytes{};
    std::size_t old_new_overlap_bytes{};
    bool resized{};
    bool topology_work_executed{};
};

class M001ClusteredBackend {
public:
    M001ClusteredBackend(
        lane_b::B002VulkanContext& context,
        std::span<const lane_b::Triangle> triangles);
    ~M001ClusteredBackend();

    M001ClusteredBackend(const M001ClusteredBackend&) = delete;
    M001ClusteredBackend& operator=(const M001ClusteredBackend&) = delete;

    [[nodiscard]] M001ClusteredUpdate update(
        std::span<const lane_b::Triangle> triangles);

    [[nodiscard]] const lane_b::B002Buffer& triangles() const noexcept;
    [[nodiscard]] const lane_b::B002Buffer& upper() const noexcept;
    [[nodiscard]] const lane_b::B002Buffer& micro() const noexcept;
    [[nodiscard]] const lane_b::B002Buffer& clusters() const noexcept;

    [[nodiscard]] M001ClusteredTraversalPush traversal_push(
        std::uint32_t ray_count) const noexcept;

    [[nodiscard]] std::size_t persistent_bytes() const noexcept;
    [[nodiscard]] const M001ClusteredUpdate& last_update() const noexcept {
        return last_update_;
    }

private:
    struct BufferSet {
        lane_b::B002Buffer triangles{};
        lane_b::B002Buffer upper{};
        lane_b::B002Buffer micro{};
        lane_b::B002Buffer clusters{};
    };

    [[nodiscard]] static std::vector<lane_j::Triangle> convert(
        std::span<const lane_b::Triangle> triangles);
    [[nodiscard]] BufferSet create_full_buffer_set(
        const lane_j::PersistentClusterLayout& layout,
        std::size_t& max_staging_bytes,
        std::uint32_t& upload_region_count,
        std::size_t& uploaded_logical_bytes);
    void destroy(BufferSet& buffers) noexcept;
    [[nodiscard]] std::size_t allocation_bytes(
        const BufferSet& buffers) const noexcept;

    lane_b::B002VulkanContext& context_;
    std::unique_ptr<lane_j::ClusterTransitionState> transition_;
    std::unique_ptr<lane_j::PersistentClusterLayout> layout_;
    BufferSet buffers_{};
    M001ClusteredUpdate last_update_{};
};

} // namespace phos::gi::research::lane_m

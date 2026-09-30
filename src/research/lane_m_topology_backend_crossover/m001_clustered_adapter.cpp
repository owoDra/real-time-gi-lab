#include "m001_clustered_adapter.hpp"

#include <algorithm>
#include <array>
#include <stdexcept>\n#include <type_traits>
#include <utility>
#include <vector>

namespace phos::gi::research::lane_m {
namespace {

[[nodiscard]] std::size_t buffer_bytes(
    const lane_b::B002Buffer& buffer) noexcept {
    return static_cast<std::size_t>(buffer.allocation_size);
}

template <typename T>
[[nodiscard]] const void* at(
    const std::vector<T>& values,
    std::size_t index) {
    if (index >= values.size()) {
        throw std::runtime_error("Lane M clustered upload index out of range");
    }
    return values.data() + index;
}

} // namespace

std::vector<lane_j::Triangle> M001ClusteredBackend::convert(
    std::span<const lane_b::Triangle> triangles) {
    std::vector<lane_j::Triangle> output;
    output.reserve(triangles.size());
    for (const auto& triangle : triangles) {
        output.push_back({
            {triangle.v0.x, triangle.v0.y, triangle.v0.z},
            {triangle.v1.x, triangle.v1.y, triangle.v1.z},
            {triangle.v2.x, triangle.v2.y, triangle.v2.z},
            triangle.primitive_id,
            triangle.material_id,
            triangle.instance_id,
            triangle.two_sided,
        });
    }
    return output;
}

M001ClusteredBackend::M001ClusteredBackend(
    lane_b::B002VulkanContext& context,
    std::span<const lane_b::Triangle> triangles)
    : context_(context) {
    const auto converted = convert(triangles);
    transition_ =
        std::make_unique<lane_j::ClusterTransitionState>(converted);
    layout_ =
        std::make_unique<lane_j::PersistentClusterLayout>(*transition_);

    std::size_t staging = 0U;
    std::uint32_t regions = 0U;
    std::size_t uploaded = 0U;
    buffers_ = create_full_buffer_set(
        *layout_, staging, regions, uploaded);
    last_update_.persistent_bytes = persistent_bytes();
    last_update_.transient_staging_bytes = staging;
    last_update_.upload_region_count = regions;
    last_update_.uploaded_logical_bytes = uploaded;
}

M001ClusteredBackend::~M001ClusteredBackend() {
    destroy(buffers_);
}

M001ClusteredBackend::BufferSet
M001ClusteredBackend::create_full_buffer_set(
    const lane_j::PersistentClusterLayout& layout,
    std::size_t& max_staging_bytes,
    std::uint32_t& upload_region_count,
    std::size_t& uploaded_logical_bytes) {
    constexpr auto usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
    BufferSet result{};
    try {
        const auto upload = [&](auto& destination, const auto& values) {
            const auto bytes =
                values.size() * sizeof(typename std::decay_t<decltype(values)>::value_type);
            if (bytes == 0U) {
                throw std::runtime_error(
                    "Lane M clustered full upload cannot be empty");
            }
            destination = context_.upload_device_buffer(
                values.data(),
                static_cast<VkDeviceSize>(bytes),
                usage);
            max_staging_bytes = std::max(max_staging_bytes, bytes);
            ++upload_region_count;
            uploaded_logical_bytes += bytes;
        };

        upload(result.triangles, layout.triangles());
        upload(result.upper, layout.upper_nodes());
        upload(result.micro, layout.micro_nodes());
        upload(result.clusters, layout.clusters());
    } catch (...) {
        destroy(result);
        throw;
    }
    return result;
}

void M001ClusteredBackend::destroy(BufferSet& buffers) noexcept {
    context_.destroy_buffer(buffers.triangles);
    context_.destroy_buffer(buffers.upper);
    context_.destroy_buffer(buffers.micro);
    context_.destroy_buffer(buffers.clusters);
}

std::size_t M001ClusteredBackend::allocation_bytes(
    const BufferSet& buffers) const noexcept {
    return buffer_bytes(buffers.triangles) +
           buffer_bytes(buffers.upper) +
           buffer_bytes(buffers.micro) +
           buffer_bytes(buffers.clusters);
}

std::size_t M001ClusteredBackend::persistent_bytes() const noexcept {
    return allocation_bytes(buffers_);
}

M001ClusteredUpdate M001ClusteredBackend::update(
    std::span<const lane_b::Triangle> triangles) {
    const auto converted = convert(triangles);
    const auto transition_stats = transition_->update(converted);
    const auto layout_update =
        layout_->synchronize(*transition_, transition_stats);

    M001ClusteredUpdate result{};
    result.changed_triangle_count =
        transition_stats.changed_triangle_count;
    result.dirty_cluster_count =
        transition_stats.dirty_cluster_count;
    result.rebuilt_triangle_count =
        transition_stats.rebuilt_triangle_count;
    result.unaffected_cluster_rebuild_count =
        transition_stats.unaffected_cluster_rebuild_count;
    result.split_count = transition_stats.split_count;
    result.merge_count = transition_stats.merge_count;
    result.retired_empty_cluster_count =
        transition_stats.retired_empty_cluster_count;
    result.resized = layout_update.resized;
    result.topology_work_executed =
        transition_stats.changed_triangle_count != 0U ||
        transition_stats.cluster_set_changed;

    constexpr auto usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
    if (layout_update.resized) {
        const auto old_persistent = persistent_bytes();
        std::size_t max_staging = 0U;
        auto replacement = create_full_buffer_set(
            *layout_,
            max_staging,
            result.upload_region_count,
            result.uploaded_logical_bytes);
        const auto new_persistent = allocation_bytes(replacement);
        result.old_new_overlap_bytes =
            old_persistent + new_persistent;
        result.transient_staging_bytes = max_staging;

        auto old = std::exchange(buffers_, replacement);
        destroy(old);
    } else {
        const auto update_buffer = [&](
            lane_b::B002Buffer& buffer,
            const std::vector<lane_b::B002BufferUpdate>& updates) {
            if (updates.empty()) {
                return;
            }
            std::size_t staging = 0U;
            for (const auto& update : updates) {
                staging += static_cast<std::size_t>(update.size);
            }
            result.transient_staging_bytes =
                std::max(result.transient_staging_bytes, staging);
            result.upload_region_count +=
                static_cast<std::uint32_t>(updates.size());
            result.uploaded_logical_bytes += staging;
            (void)context_.update_device_buffer_timed(buffer, updates);
        };

        std::vector<lane_b::B002BufferUpdate> triangle_updates;
        std::vector<lane_b::B002BufferUpdate> micro_updates;
        std::vector<lane_b::B002BufferUpdate> cluster_updates;
        triangle_updates.reserve(layout_update.dirty_physical_slots.size());
        micro_updates.reserve(layout_update.dirty_physical_slots.size());
        cluster_updates.reserve(layout_update.dirty_physical_slots.size());

        for (const auto slot : layout_update.dirty_physical_slots) {
            const auto triangle_index =
                std::size_t(slot) * lane_j::kTrianglesPerPhysicalSlot;
            const auto micro_index =
                std::size_t(slot) * lane_j::kMicroNodesPerPhysicalSlot;
            triangle_updates.push_back({
                static_cast<VkDeviceSize>(
                    triangle_index * sizeof(lane_j::GpuTriangle)),
                at(layout_->triangles(), triangle_index),
                static_cast<VkDeviceSize>(
                    lane_j::kTrianglesPerPhysicalSlot *
                    sizeof(lane_j::GpuTriangle)),
            });
            micro_updates.push_back({
                static_cast<VkDeviceSize>(
                    micro_index * sizeof(lane_j::GpuBvhNode)),
                at(layout_->micro_nodes(), micro_index),
                static_cast<VkDeviceSize>(
                    lane_j::kMicroNodesPerPhysicalSlot *
                    sizeof(lane_j::GpuBvhNode)),
            });
            cluster_updates.push_back({
                static_cast<VkDeviceSize>(
                    std::size_t(slot) * sizeof(lane_j::GpuCluster)),
                at(layout_->clusters(), slot),
                static_cast<VkDeviceSize>(sizeof(lane_j::GpuCluster)),
            });
        }

        update_buffer(buffers_.triangles, triangle_updates);
        update_buffer(buffers_.micro, micro_updates);
        update_buffer(buffers_.clusters, cluster_updates);

        std::vector<lane_b::B002BufferUpdate> upper_updates;
        if (layout_update.upper_rebuilt) {
            const auto bytes =
                std::size_t(layout_->upper_node_count()) *
                sizeof(lane_j::GpuBvhNode);
            if (bytes != 0U) {
                upper_updates.push_back({
                    0U,
                    layout_->upper_nodes().data(),
                    static_cast<VkDeviceSize>(bytes),
                });
            }
        } else {
            upper_updates.reserve(layout_update.dirty_upper_nodes.size());
            for (const auto node : layout_update.dirty_upper_nodes) {
                upper_updates.push_back({
                    static_cast<VkDeviceSize>(
                        std::size_t(node) * sizeof(lane_j::GpuBvhNode)),
                    at(layout_->upper_nodes(), node),
                    static_cast<VkDeviceSize>(sizeof(lane_j::GpuBvhNode)),
                });
            }
        }
        update_buffer(buffers_.upper, upper_updates);
    }

    result.persistent_bytes = persistent_bytes();
    last_update_ = result;
    return result;
}

const lane_b::B002Buffer& M001ClusteredBackend::triangles() const noexcept {
    return buffers_.triangles;
}
const lane_b::B002Buffer& M001ClusteredBackend::upper() const noexcept {
    return buffers_.upper;
}
const lane_b::B002Buffer& M001ClusteredBackend::micro() const noexcept {
    return buffers_.micro;
}
const lane_b::B002Buffer& M001ClusteredBackend::clusters() const noexcept {
    return buffers_.clusters;
}

M001ClusteredTraversalPush M001ClusteredBackend::traversal_push(
    std::uint32_t ray_count) const noexcept {
    return {
        ray_count,
        layout_->upper_root(),
        layout_->upper_node_count(),
        static_cast<std::uint32_t>(layout_->micro_nodes().size()),
        static_cast<std::uint32_t>(layout_->clusters().size()),
        static_cast<std::uint32_t>(layout_->triangles().size()),
    };
}

} // namespace phos::gi::research::lane_m

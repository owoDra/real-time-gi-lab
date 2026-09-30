#pragma once

#include "j003_persistent_layout.hpp"
#include "j003_types.hpp"
#include "vk_context.hpp"

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace phos::gi::research::lane_j {

struct PersistentGpuSyncResult {
    bool resized{};
    std::uint32_t upload_region_count{};
    std::size_t uploaded_logical_bytes{};
    std::size_t candidate_persistent_allocation_bytes{};
    std::size_t resize_old_new_overlap_allocation_bytes{};
    std::size_t max_staging_allocation_bytes{};
    std::size_t true_peak_resident_bytes{};
};

class PersistentGpuState {
public:
    PersistentGpuState(
        VulkanContext& context,
        const PersistentClusterLayout& layout);
    ~PersistentGpuState();

    PersistentGpuState(const PersistentGpuState&) = delete;
    PersistentGpuState& operator=(const PersistentGpuState&) = delete;

    [[nodiscard]] PersistentGpuSyncResult synchronize(
        const PersistentClusterLayout& layout,
        const PersistentLayoutUpdate& update);

    [[nodiscard]] const GpuBuffer& triangle_buffer() const noexcept {
        return triangles_;
    }
    [[nodiscard]] const GpuBuffer& upper_buffer() const noexcept {
        return upper_;
    }
    [[nodiscard]] const GpuBuffer& micro_buffer() const noexcept {
        return micro_;
    }
    [[nodiscard]] const GpuBuffer& cluster_buffer() const noexcept {
        return clusters_;
    }

    [[nodiscard]] std::size_t persistent_allocation_bytes() const;

private:
    struct CopyRegion {
        const std::byte* source{};
        VkDeviceSize destination_offset{};
        VkDeviceSize size{};
    };

    struct BufferSet {
        GpuBuffer triangles{};
        GpuBuffer upper{};
        GpuBuffer micro{};
        GpuBuffer clusters{};
    };

    [[nodiscard]] BufferSet create_buffer_set(
        const PersistentClusterLayout& layout);
    void destroy_buffer_set(BufferSet& buffers);
    [[nodiscard]] std::size_t allocation_bytes(
        const GpuBuffer& buffer) const;
    [[nodiscard]] std::size_t allocation_bytes(
        const BufferSet& buffers) const;
    [[nodiscard]] std::size_t upload_regions(
        GpuBuffer& destination,
        std::span<const CopyRegion> regions,
        std::uint32_t& region_count,
        std::size_t& uploaded_logical_bytes);
    [[nodiscard]] std::size_t upload_full_layout(
        BufferSet& buffers,
        const PersistentClusterLayout& layout,
        std::uint32_t& region_count,
        std::size_t& uploaded_logical_bytes);

    VulkanContext& context_;
    GpuBuffer triangles_{};
    GpuBuffer upper_{};
    GpuBuffer micro_{};
    GpuBuffer clusters_{};
};

} // namespace phos::gi::research::lane_j

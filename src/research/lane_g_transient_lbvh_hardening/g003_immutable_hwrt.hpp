#pragma once

#include "baseline/lane_b_traversal/b002_hwrt.hpp"

namespace phos::gi::research::lane_g {

class G003ImmutableHwrtTraversal {
public:
    G003ImmutableHwrtTraversal(
        lane_b::B002VulkanContext& context,
        const std::vector<lane_b::Triangle>& triangles);
    ~G003ImmutableHwrtTraversal();

    G003ImmutableHwrtTraversal(const G003ImmutableHwrtTraversal&) = delete;
    G003ImmutableHwrtTraversal& operator=(const G003ImmutableHwrtTraversal&) = delete;

    [[nodiscard]] const lane_b::HwrtSetupStats& setup_stats() const noexcept {
        return setup_stats_;
    }
    [[nodiscard]] std::vector<lane_b::HwrtAllocationRecord>
    allocation_census() const;

    [[nodiscard]] VkAccelerationStructureKHR top_level() const noexcept {
        return tlas_.handle;
    }
    [[nodiscard]] const lane_b::B002Buffer& triangle_buffer() const noexcept {
        return triangle_buffer_;
    }

private:
    struct AccelerationStructure {
        lane_b::B002Buffer storage{};
        VkAccelerationStructureKHR handle{VK_NULL_HANDLE};
        VkDeviceAddress address{};
    };

    [[nodiscard]] double build_blas(
        const std::vector<lane_b::Triangle>& triangles);
    [[nodiscard]] double build_tlas();
    void ensure_scratch_capacity(VkDeviceSize required_bytes);
    [[nodiscard]] VkDeviceAddress scratch_address() const noexcept;
    [[nodiscard]] double submit_build(
        VkAccelerationStructureBuildGeometryInfoKHR& build_info,
        const VkAccelerationStructureBuildRangeInfoKHR& range,
        bool depends_on_previous_build);
    void destroy_acceleration_structure(
        AccelerationStructure& acceleration);

    lane_b::B002VulkanContext& context_;
    lane_b::B002Buffer vertex_buffer_{};
    lane_b::B002Buffer triangle_buffer_{};
    lane_b::B002Buffer instance_buffer_{};
    lane_b::B002Buffer scratch_{};
    AccelerationStructure blas_{};
    AccelerationStructure tlas_{};

    VkCommandPool command_pool_{VK_NULL_HANDLE};
    VkQueryPool query_pool_{VK_NULL_HANDLE};
    VkFence fence_{VK_NULL_HANDLE};

    lane_b::HwrtSetupStats setup_stats_{};
};

} // namespace phos::gi::research::lane_g

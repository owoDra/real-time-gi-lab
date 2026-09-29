#pragma once

#include "b002_gpu_layout.hpp"
#include "b002_vulkan.hpp"
#include "traversal_contract.hpp"

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace phos::gi::research::lane_b {

struct HwrtSetupStats {
    double vertex_upload_us{};
    double metadata_upload_us{};
    double blas_build_us{};
    double tlas_build_us{};
    std::size_t persistent_bytes{};
    std::size_t scratch_bytes{};
};

struct HwrtTraceResult {
    double ray_upload_us{};
    double trace_us{};
    std::size_t ray_allocation_bytes{};
    std::size_t hit_allocation_bytes{};
    std::vector<GpuHit> hits;
};

struct HwrtUpdateStats {
    std::size_t moved_primitives{};
    double geometry_upload_us{};
    double blas_update_us{};
    double tlas_update_us{};
    double geometry_upload_gpu_us{};
};

enum class HwrtTlasPolicy {
    Update,
    Build,
};

struct HwrtRigidUpdateStats {
    std::size_t moved_primitives{};
    double instance_upload_us{};
    double instance_upload_gpu_us{};
    double tlas_update_us{};
};

class B002HwrtTraversal {
public:
    B002HwrtTraversal(
        B002VulkanContext& context,
        const std::vector<Triangle>& triangles,
        std::string shader_path,
        bool create_trace_runtime = true);
    B002HwrtTraversal(
        B002VulkanContext& context,
        const std::vector<Triangle>& triangles,
        std::span<const std::uint32_t> rigid_primitives,
        std::string shader_path,
        bool create_trace_runtime = true);
    ~B002HwrtTraversal();

    B002HwrtTraversal(const B002HwrtTraversal&) = delete;
    B002HwrtTraversal& operator=(const B002HwrtTraversal&) = delete;

    [[nodiscard]] const HwrtSetupStats& setup_stats() const noexcept {
        return setup_stats_;
    }

    [[nodiscard]] HwrtTraceResult trace(
        std::span<const GpuRay> rays,
        std::uint32_t iterations);

    [[nodiscard]] HwrtUpdateStats update_geometry(
        const std::vector<Triangle>& triangles,
        std::span<const std::uint32_t> moved_primitives);

    // Lane E E002: rigid geometry is immutable after setup. Only the second
    // TLAS instance transform is changed; no vertex/metadata upload or BLAS
    // update is permitted on this path.
    [[nodiscard]] HwrtRigidUpdateStats update_rigid_transform(
        float translation_x,
        HwrtTlasPolicy policy);

    // Integration #13 reuses the accepted B002 AS build/update ownership while
    // recording traversal in a larger end-to-end command stream.
    [[nodiscard]] VkAccelerationStructureKHR top_level() const noexcept {
        return tlas_.handle;
    }
    [[nodiscard]] const B002Buffer& triangle_buffer() const noexcept {
        return triangle_buffer_;
    }

private:
    struct AccelerationStructure {
        B002Buffer storage{};
        VkAccelerationStructureKHR handle{
            VK_NULL_HANDLE};
        VkDeviceAddress address{};
    };

    [[nodiscard]] double build_blas_range(
        VkDeviceAddress vertex_address,
        std::size_t triangle_count,
        AccelerationStructure& target);
    [[nodiscard]] double build_tlas();
    [[nodiscard]] double update_blas(std::size_t triangle_count);
    [[nodiscard]] double update_tlas();
    [[nodiscard]] double maintain_tlas(HwrtTlasPolicy policy);
    void ensure_scratch_capacity(VkDeviceSize required_bytes);
    [[nodiscard]] VkDeviceAddress scratch_address() const noexcept;
    [[nodiscard]] double submit_build(
        VkAccelerationStructureBuildGeometryInfoKHR& build_info,
        const VkAccelerationStructureBuildRangeInfoKHR& range,
        bool depends_on_previous_build);
    void create_trace_pipeline(const std::string& shader_path);
    [[nodiscard]] double measure_trace(
        std::uint32_t ray_count,
        std::uint32_t iterations);
    void destroy_acceleration_structure(
        AccelerationStructure& acceleration);

    B002VulkanContext& context_;
    B002Buffer vertex_buffer_{};
    B002Buffer triangle_buffer_{};
    B002Buffer instance_buffer_{};
    B002Buffer scratch_{};
    AccelerationStructure blas_{};
    AccelerationStructure dynamic_blas_{};
    AccelerationStructure tlas_{};

    VkDescriptorSetLayout descriptor_layout_{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout_{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool_{VK_NULL_HANDLE};
    VkDescriptorSet descriptor_set_{VK_NULL_HANDLE};
    VkPipeline pipeline_{VK_NULL_HANDLE};
    VkCommandPool command_pool_{VK_NULL_HANDLE};
    VkQueryPool query_pool_{VK_NULL_HANDLE};
    VkFence fence_{VK_NULL_HANDLE};

    HwrtSetupStats setup_stats_{};
    std::size_t triangle_count_{};
    std::size_t static_triangle_count_{};
    std::size_t dynamic_triangle_count_{};
    bool rigid_partitioned_{};
};

} // namespace phos::gi::research::lane_b

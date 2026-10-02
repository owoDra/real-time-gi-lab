#pragma once

#include "../lane_b_traversal/b002_vulkan.hpp"

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace phos::gi::research::integration {

using lane_b::B002Buffer;
using lane_b::B002VulkanContext;

struct I001Binding {
    std::uint32_t binding{};
    VkDescriptorType type{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER};
    const B002Buffer* buffer{};
    VkAccelerationStructureKHR acceleration{VK_NULL_HANDLE};
};

class I001ComputeStage {
public:
    I001ComputeStage(
        B002VulkanContext& context,
        std::string shader_path,
        std::span<const I001Binding> bindings,
        std::size_t push_constant_bytes = 0);
    ~I001ComputeStage();

    I001ComputeStage(const I001ComputeStage&) = delete;
    I001ComputeStage& operator=(const I001ComputeStage&) = delete;

    void record(
        VkCommandBuffer command,
        std::uint32_t groups_x,
        std::uint32_t groups_y = 1,
        std::uint32_t groups_z = 1,
        const void* push_constants = nullptr,
        std::size_t push_constant_bytes = 0) const;

    void record_indirect(
        VkCommandBuffer command,
        VkBuffer indirect,
        VkDeviceSize offset,
        const void* push_constants = nullptr,
        std::size_t push_constant_bytes = 0) const;

private:
    void bind(
        VkCommandBuffer command,
        const void* push_constants,
        std::size_t push_constant_bytes) const;

    B002VulkanContext& context_;
    VkDescriptorSetLayout descriptor_layout_{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout_{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool_{VK_NULL_HANDLE};
    VkDescriptorSet descriptor_set_{VK_NULL_HANDLE};
    VkPipeline pipeline_{VK_NULL_HANDLE};
    std::size_t push_constant_bytes_{};
};

void i001_compute_barrier(
    B002VulkanContext& context,
    VkCommandBuffer command);

void i001_transfer_to_compute_barrier(
    B002VulkanContext& context,
    VkCommandBuffer command);

void i001_acceleration_to_compute_barrier(
    B002VulkanContext& context,
    VkCommandBuffer command);

} // namespace phos::gi::research::integration

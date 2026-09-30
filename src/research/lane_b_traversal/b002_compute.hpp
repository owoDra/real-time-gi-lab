#pragma once

#include "b002_gpu_layout.hpp"
#include "b002_vulkan.hpp"

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace phos::gi::research::lane_b {

struct alignas(16) SoftwareTraversalPush {
    std::uint32_t ray_count{};
    std::uint32_t root{kInvalidId};
    std::uint32_t reserved0{};
    std::uint32_t reserved1{};
};
static_assert(sizeof(SoftwareTraversalPush) == 16);

struct alignas(16) HierarchicalTraversalPush {
    std::uint32_t values[4]{};
    float occupied_min_segment_size[4]{};
    float occupied_max_pad[4]{};
};
static_assert(sizeof(HierarchicalTraversalPush) == 48);

class B002ComputeTraversal {
public:
    B002ComputeTraversal(
        B002VulkanContext& context,
        std::string shader_path,
        std::span<const B002Buffer* const> bindings,
        std::size_t push_constant_bytes);
    ~B002ComputeTraversal();

    B002ComputeTraversal(const B002ComputeTraversal&) = delete;
    B002ComputeTraversal& operator=(const B002ComputeTraversal&) = delete;

    [[nodiscard]] double measure(
        std::uint32_t ray_count,
        std::uint32_t iterations,
        const void* push_constants,
        std::size_t push_constant_bytes);

private:
    void record_dispatch(
        VkCommandBuffer command,
        std::uint32_t ray_count,
        const void* push_constants,
        std::size_t push_constant_bytes);

    B002VulkanContext& context_;
    VkDescriptorSetLayout descriptor_layout_{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout_{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool_{VK_NULL_HANDLE};
    VkDescriptorSet descriptor_set_{VK_NULL_HANDLE};
    VkPipeline pipeline_{VK_NULL_HANDLE};
    VkCommandPool command_pool_{VK_NULL_HANDLE};
    VkQueryPool query_pool_{VK_NULL_HANDLE};
    VkFence fence_{VK_NULL_HANDLE};
    std::size_t push_constant_bytes_{};
};

[[nodiscard]] double median_us(std::vector<double> values);

} // namespace phos::gi::research::lane_b

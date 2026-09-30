#pragma once

#include "i001_contract.hpp"
#include "vk_context.hpp"

#include <cstdint>
#include <vector>

namespace phos::gi::research::lane_i {

struct BatchResult {
    CalibrationVariant variant{};
    double gpu_us{};
    double wall_us{};
    std::uint64_t controlled_work_units{};
};

class CalibrationGpu {
public:
    CalibrationGpu(VulkanContext& context, std::uint32_t elements);
    ~CalibrationGpu();
    CalibrationGpu(const CalibrationGpu&) = delete;
    CalibrationGpu& operator=(const CalibrationGpu&) = delete;

    [[nodiscard]] BatchResult run(
        CalibrationVariant variant,
        std::uint32_t batch_dispatches);
    [[nodiscard]] std::uint64_t download_checksum();
    [[nodiscard]] std::uint64_t reference_checksum(
        CalibrationVariant variant,
        std::uint32_t batch_dispatches) const;

private:
    void create_pipeline();
    void create_commands();

    VulkanContext& ctx_;
    std::uint32_t elements_{};
    std::vector<std::uint32_t> input_cpu_;
    std::vector<std::uint32_t> initial_cpu_;
    GpuBuffer input_{};
    GpuBuffer initial_{};
    GpuBuffer state_{};
    VkDescriptorSetLayout descriptor_layout_{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout_{VK_NULL_HANDLE};
    VkPipeline pipeline_{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool_{VK_NULL_HANDLE};
    VkDescriptorSet descriptor_set_{VK_NULL_HANDLE};
    VkCommandPool command_pool_{VK_NULL_HANDLE};
    VkCommandBuffer command_buffer_{VK_NULL_HANDLE};
    VkQueryPool query_pool_{VK_NULL_HANDLE};
    VkFence fence_{VK_NULL_HANDLE};
};

} // namespace phos::gi::research::lane_i

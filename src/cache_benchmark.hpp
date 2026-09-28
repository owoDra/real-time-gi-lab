#pragma once
#include "types.hpp"
#include "vk_context.hpp"
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace phos::gi {

struct BenchmarkResult {
    std::string variant;
    std::size_t queries{};
    std::size_t pages{};
    std::size_t bytes{};
    double gpu_us_per_dispatch{};
    std::uint64_t checksum{};
    std::uint64_t expected_checksum{};
    bool correct{};
};

class CacheBenchmark {
public:
    explicit CacheBenchmark(VulkanContext& context);
    ~CacheBenchmark();
    std::vector<BenchmarkResult> run(const Workload& workload, std::uint32_t iterations);

private:
    BenchmarkResult run_variant(const char* name, const std::vector<Query>& queries,
        const std::vector<std::uint32_t>& table0, const std::vector<std::uint32_t>& payload,
        std::uint32_t mode_value, std::uint32_t mask_or_page_size, std::uint32_t lookup_limit,
        std::uint32_t iterations, std::size_t logical_bytes, std::uint64_t expected_checksum);

    VkPipeline create_pipeline(const std::string& filename);
    GpuBuffer upload(const void* data, std::size_t bytes);

    VulkanContext& ctx_;
    VkDescriptorSetLayout descriptor_layout_{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout_{VK_NULL_HANDLE};
    VkPipeline hash_pipeline_{VK_NULL_HANDLE};
    VkPipeline paged_pipeline_{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool_{VK_NULL_HANDLE};
    VkCommandPool command_pool_{VK_NULL_HANDLE};
    VkCommandBuffer command_buffer_{VK_NULL_HANDLE};
    VkQueryPool query_pool_{VK_NULL_HANDLE};
    VkFence fence_{VK_NULL_HANDLE};
};

} // namespace phos::gi

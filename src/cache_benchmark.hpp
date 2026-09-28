#pragma once
#include "types.hpp"
#include "vk_context.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace phos::gi {

struct BenchmarkResult {
    // Keep the original CSV fields authoritative for lookup timing. The
    // representation/ordering axes and GPU scheduling measurements are additive.
    std::string variant;
    std::size_t queries{};
    std::size_t pages{};
    std::size_t bytes{};
    double gpu_us_per_dispatch{};
    std::uint64_t checksum{};
    std::uint64_t expected_checksum{};
    bool correct{};

    std::string representation;
    std::string ordering;
    std::size_t scheduling_bytes{};
    std::optional<double> scheduling_gpu_us_per_dispatch;
    std::optional<double> end_to_end_gpu_us_per_dispatch;
};

class CacheBenchmark {
public:
    explicit CacheBenchmark(VulkanContext& context);
    ~CacheBenchmark();
    std::vector<BenchmarkResult> run(const Workload& workload, std::uint32_t iterations);

private:
    struct CacheGpuData {
        const char* name{};
        VkPipeline pipeline{VK_NULL_HANDLE};
        GpuBuffer table;
        GpuBuffer payload;
        std::uint32_t mask_or_page_size{};
        std::uint32_t lookup_limit{};
        std::size_t logical_bytes{};
        std::size_t pages{};
    };

    struct SchedulerGpuData {
        GpuBuffer counts;
        GpuBuffer offsets;
        GpuBuffer cursors;
        GpuBuffer grouped_queries;
        std::uint32_t query_count{};
        std::uint32_t page_count{};
        std::size_t transient_bytes{};
    };

    struct SchedulerSets {
        VkDescriptorSet histogram{VK_NULL_HANDLE};
        VkDescriptorSet prefix{VK_NULL_HANDLE};
        VkDescriptorSet scatter{VK_NULL_HANDLE};
    };

    struct LookupMeasurement {
        double gpu_us_per_dispatch{};
        std::uint64_t checksum{};
        // Order-sensitive guard for variants that must preserve source-index
        // semantics. This is compared only between identical query orderings.
        std::uint64_t sequence_fingerprint{};
    };

    VkPipeline create_pipeline(const std::string& filename);
    GpuBuffer upload(const void* data, std::size_t bytes);
    VkDescriptorSet create_descriptor_set(
        const std::array<const GpuBuffer*, 4>& buffers);

    LookupMeasurement measure_lookup(
        const GpuBuffer& queries,
        std::uint32_t query_count,
        const CacheGpuData& cache,
        std::uint32_t iterations);

    double measure_scheduler(
        const GpuBuffer& source_queries,
        SchedulerGpuData& scheduler,
        std::uint32_t iterations);

    LookupMeasurement measure_end_to_end(
        const GpuBuffer& source_queries,
        SchedulerGpuData& scheduler,
        const CacheGpuData& cache,
        std::uint32_t iterations);

    SchedulerSets create_scheduler_sets(
        const GpuBuffer& source_queries,
        const SchedulerGpuData& scheduler);

    void record_schedule_pass(
        VkCommandBuffer command_buffer,
        const SchedulerGpuData& scheduler,
        const SchedulerSets& sets);

    void record_lookup_pass(
        VkCommandBuffer command_buffer,
        const CacheGpuData& cache,
        VkDescriptorSet set,
        const GpuBuffer& output,
        std::uint32_t query_count);

    [[nodiscard]] bool validate_gpu_grouping(
        const Workload& workload,
        const GpuBuffer& grouped_queries);

    double finish_timed_submission(std::uint32_t iterations);

    VulkanContext& ctx_;
    VkDescriptorSetLayout descriptor_layout_{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout_{VK_NULL_HANDLE};

    VkPipeline hash_pipeline_{VK_NULL_HANDLE};
    VkPipeline hash_wg_bin16_pipeline_{VK_NULL_HANDLE};
    VkPipeline paged_pipeline_{VK_NULL_HANDLE};
    VkPipeline histogram_pipeline_{VK_NULL_HANDLE};
    VkPipeline prefix_pipeline_{VK_NULL_HANDLE};
    VkPipeline scatter_pipeline_{VK_NULL_HANDLE};

    VkDescriptorPool descriptor_pool_{VK_NULL_HANDLE};
    VkCommandPool command_pool_{VK_NULL_HANDLE};
    VkCommandBuffer command_buffer_{VK_NULL_HANDLE};
    VkQueryPool query_pool_{VK_NULL_HANDLE};
    VkFence fence_{VK_NULL_HANDLE};
};

} // namespace phos::gi

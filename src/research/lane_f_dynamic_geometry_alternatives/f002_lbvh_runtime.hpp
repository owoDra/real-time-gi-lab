#pragma once

#include "../lane_b_traversal/b002_gpu_layout.hpp"
#include "../lane_b_traversal/b002_vulkan.hpp"

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <vector>

namespace phos::gi::research::lane_f {

struct F002BuildSample {
    double reset_us{};
    double input_us{};
    double aabb_us{};
    double morton_us{};
    double sort_us{};
    double topology_us{};
    double bounds_us{};
    double total_us{};
};

struct F002Validation {
    std::size_t sort_mismatches{};
    std::size_t root_count_mismatches{};
    std::size_t root_index_mismatches{};
    std::size_t root_bounds_mismatches{};
    std::size_t leaf_mapping_mismatches{};
    std::size_t topology_mismatches{};

    [[nodiscard]] bool passed() const noexcept {
        return sort_mismatches == 0 &&
               root_count_mismatches == 0 &&
               root_index_mismatches == 0 &&
               root_bounds_mismatches == 0 &&
               leaf_mapping_mismatches == 0 &&
               topology_mismatches == 0;
    }
};

struct F002Memory {
    std::size_t template_bytes{};
    std::size_t working_geometry_bytes{};
    std::size_t aabb_bytes{};
    std::size_t key_bytes{};
    std::size_t histogram_bytes{};
    std::size_t prefix_bytes{};
    std::size_t node_bytes{};
    std::size_t ready_bytes{};

    [[nodiscard]] std::size_t total_bytes() const noexcept {
        return template_bytes + working_geometry_bytes + aabb_bytes +
               key_bytes + histogram_bytes + prefix_bytes + node_bytes +
               ready_bytes;
    }
};

class F002LbvhBuilder {
public:
    F002LbvhBuilder(
        lane_b::B002VulkanContext& context,
        std::span<const lane_b::GpuTriangle> template_triangles,
        std::uint32_t primitive_count,
        lane_b::Vec3 origin,
        float page_extent,
        std::filesystem::path shader_path);
    ~F002LbvhBuilder();

    F002LbvhBuilder(const F002LbvhBuilder&) = delete;
    F002LbvhBuilder& operator=(const F002LbvhBuilder&) = delete;

    [[nodiscard]] std::vector<F002BuildSample> measure(
        std::uint32_t warmup_builds,
        std::uint32_t measured_builds);

    [[nodiscard]] F002Validation validate() const;
    [[nodiscard]] F002Memory memory() const noexcept { return memory_; }

private:
    struct Push {
        std::uint32_t mode{};
        std::uint32_t count{};
        std::uint32_t template_count{};
        std::uint32_t pass_index{};
        float origin_page_extent[4]{};
    };
    static_assert(sizeof(Push) == 32);

    void record_build(
        VkCommandBuffer command,
        VkQueryPool query_pool,
        std::uint32_t query_base,
        bool timed) const;
    void dispatch(
        VkCommandBuffer command,
        std::uint32_t mode,
        std::uint32_t pass,
        std::uint32_t groups) const;
    void compute_barrier(VkCommandBuffer command) const;
    void compute_to_transfer_barrier(VkCommandBuffer command) const;
    void transfer_to_compute_barrier(VkCommandBuffer command) const;
    void submit_and_wait(VkCommandBuffer command) const;

    lane_b::B002VulkanContext& context_;
    std::vector<lane_b::GpuTriangle> template_cpu_;
    std::uint32_t count_{};
    lane_b::Vec3 origin_{};
    float page_extent_{};
    std::filesystem::path shader_path_;

    lane_b::B002Buffer template_buffer_{};
    lane_b::B002Buffer working_buffer_{};
    lane_b::B002Buffer aabb_min_buffer_{};
    lane_b::B002Buffer aabb_max_buffer_{};
    lane_b::B002Buffer keys_a_buffer_{};
    lane_b::B002Buffer keys_b_buffer_{};
    lane_b::B002Buffer histogram_buffer_{};
    lane_b::B002Buffer offsets_buffer_{};
    lane_b::B002Buffer digit_base_buffer_{};
    lane_b::B002Buffer nodes_buffer_{};
    lane_b::B002Buffer ready_buffer_{};

    VkDescriptorSetLayout descriptor_layout_{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout_{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool_{VK_NULL_HANDLE};
    VkDescriptorSet descriptor_set_{VK_NULL_HANDLE};
    VkPipeline pipeline_{VK_NULL_HANDLE};
    VkCommandPool command_pool_{VK_NULL_HANDLE};
    VkFence fence_{VK_NULL_HANDLE};

    F002Memory memory_{};
};

[[nodiscard]] double f002_median(std::vector<double> values);

} // namespace phos::gi::research::lane_f

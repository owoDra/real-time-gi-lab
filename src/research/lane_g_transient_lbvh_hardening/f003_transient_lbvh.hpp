#pragma once

#include "baseline/lane_b_traversal/b002_gpu_layout.hpp"
#include "baseline/lane_b_traversal/b002_vulkan.hpp"

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <span>
#include <vector>

namespace phos::gi::research::lane_f {

struct F003LbvhMemory {
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t scratch_bytes{};
    std::size_t peak_bytes{};
    std::size_t input_geometry_bytes{};
};

struct F003LbvhAllocation {
    const char* name{};
    const char* role{};
    const char* capacity_kind{};
    const char* use_lifetime{};
    std::size_t logical_bytes{};
    std::size_t allocation_bytes{};
};

class F003TransientLbvh {
public:
    F003TransientLbvh(
        lane_b::B002VulkanContext& context,
        std::span<const lane_b::GpuTriangle> template_triangles,
        lane_b::Vec3 origin,
        float page_extent,
        std::filesystem::path shader_path);
    ~F003TransientLbvh();

    F003TransientLbvh(const F003TransientLbvh&) = delete;
    F003TransientLbvh& operator=(const F003TransientLbvh&) = delete;

    // Emits 8 timestamps: reset begin/end, input, AABB, Morton, sort,
    // topology, bounds/end. Query slots [base, base+7] must be available.
    void record_build(
        VkCommandBuffer command,
        float delta_x,
        VkQueryPool query_pool,
        std::uint32_t query_base) const;

    // F006 controlled geometry-class adapter: replace the immutable source
    // template before the measured build without changing LBVH structure/layout.
    [[nodiscard]] double update_template(
        std::span<const lane_b::GpuTriangle> triangles);

    [[nodiscard]] const lane_b::B002Buffer& triangles() const noexcept {
        return working_buffer_;
    }
    [[nodiscard]] const lane_b::B002Buffer& nodes() const noexcept {
        return nodes_buffer_;
    }
    [[nodiscard]] const lane_b::B002Buffer& sorted_keys() const noexcept {
        return keys_a_buffer_;
    }
    [[nodiscard]] std::uint32_t primitive_count() const noexcept {
        return count_;
    }
    [[nodiscard]] const F003LbvhMemory& memory() const noexcept {
        return memory_;
    }
    [[nodiscard]] std::vector<F003LbvhAllocation> allocation_census() const;

private:
    struct Push {
        std::uint32_t mode{};
        std::uint32_t count{};
        std::uint32_t template_count{};
        std::uint32_t pass_index{};
        float origin_page_extent[4]{};
        float input_delta[4]{};
    };
    static_assert(sizeof(Push) == 48);

    void dispatch(
        VkCommandBuffer command,
        std::uint32_t mode,
        std::uint32_t pass,
        std::uint32_t groups,
        float delta_x) const;
    void compute_barrier(VkCommandBuffer command) const;
    void compute_to_transfer_barrier(VkCommandBuffer command) const;
    void transfer_to_compute_barrier(VkCommandBuffer command) const;

    lane_b::B002VulkanContext& context_;
    std::uint32_t count_{};
    lane_b::Vec3 origin_{};
    float page_extent_{};

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

    F003LbvhMemory memory_{};
};

} // namespace phos::gi::research::lane_f

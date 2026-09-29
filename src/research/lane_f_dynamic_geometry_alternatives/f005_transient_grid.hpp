#pragma once

#include "../lane_b_traversal/b002_gpu_layout.hpp"
#include "../lane_b_traversal/b002_vulkan.hpp"

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <span>

namespace phos::gi::research::lane_f {

inline constexpr std::uint32_t kF005LocalCellsPerAxis = 8U;
inline constexpr std::uint32_t kF005RadixPasses = 11U;

struct alignas(16) F005GridTraversalPush {
    float origin_page_extent[4]{};
    std::uint32_t local_cells_per_axis{kF005LocalCellsPerAxis};
    std::uint32_t pair_capacity{};
    std::uint32_t reserved0{};
    std::uint32_t reserved1{};
};
static_assert(sizeof(F005GridTraversalPush) == 32);

struct F005GridMemory {
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t scratch_bytes{};
    std::size_t peak_bytes{};
    std::size_t input_geometry_bytes{};
    std::size_t pair_stream_bytes{};
    std::size_t sort_scratch_bytes{};
};

struct F005GridStats {
    std::uint32_t emitted_references{};
    std::uint32_t max_references_per_triangle{};
    std::uint32_t visited_macro_cells{};
    std::uint32_t visited_local_cells{};
    std::uint32_t empty_cell_steps{};
    std::uint32_t tested_primitive_references{};
    std::uint32_t cell_ranges{};
    std::uint32_t macro_ranges{};
    std::uint32_t overflow{};
};

class F005TransientGrid {
public:
    F005TransientGrid(
        lane_b::B002VulkanContext& context,
        std::span<const lane_b::GpuTriangle> template_triangles,
        lane_b::Vec3 origin,
        float page_extent,
        std::filesystem::path builder_shader_path);
    ~F005TransientGrid();

    F005TransientGrid(const F005TransientGrid&) = delete;
    F005TransientGrid& operator=(const F005TransientGrid&) = delete;

    // Emits 8 timestamps: reset begin/end, input, overlap/AABB, scan,
    // pair emit, radix sort, RLE/ranges end. Slots [base, base+7].
    void record_build(
        VkCommandBuffer command,
        float delta_x,
        VkQueryPool query_pool,
        std::uint32_t query_base) const;

    [[nodiscard]] F005GridTraversalPush traversal_push() const noexcept;
    [[nodiscard]] F005GridStats stats() const noexcept;
    [[nodiscard]] const F005GridMemory& memory() const noexcept {
        return memory_;
    }

    [[nodiscard]] const lane_b::B002Buffer& triangles() const noexcept {
        return working_buffer_;
    }
    [[nodiscard]] const lane_b::B002Buffer& pairs() const noexcept {
        return pairs_b_buffer_;
    }
    [[nodiscard]] const lane_b::B002Buffer& cell_ranges() const noexcept {
        return cell_ranges_buffer_;
    }
    [[nodiscard]] const lane_b::B002Buffer& macro_ranges() const noexcept {
        return macro_ranges_buffer_;
    }
    [[nodiscard]] const lane_b::B002Buffer& build_counters() const noexcept {
        return counters_buffer_;
    }
    [[nodiscard]] const lane_b::B002Buffer& stats_buffer() const noexcept {
        return stats_buffer_;
    }
    [[nodiscard]] std::uint32_t primitive_count() const noexcept {
        return count_;
    }
    [[nodiscard]] std::uint32_t pair_capacity() const noexcept {
        return pair_capacity_;
    }

private:
    struct Push {
        std::uint32_t mode{};
        std::uint32_t count{};
        std::uint32_t pair_capacity{};
        std::uint32_t pass_index{};
        float origin_page_extent[4]{};
        float input_delta[4]{};
        std::uint32_t grid_params[4]{};
    };
    static_assert(sizeof(Push) == 64);

    void dispatch(
        VkCommandBuffer command,
        std::uint32_t mode,
        std::uint32_t pass,
        std::uint32_t groups,
        float delta_x) const;
    void compute_barrier(VkCommandBuffer command) const;
    void compute_to_transfer_barrier(VkCommandBuffer command) const;
    void transfer_to_compute_barrier(VkCommandBuffer command) const;
    void compute_to_indirect_barrier(VkCommandBuffer command) const;

    lane_b::B002VulkanContext& context_;
    std::uint32_t count_{};
    std::uint32_t pair_capacity_{};
    lane_b::Vec3 origin_{};
    float page_extent_{};

    lane_b::B002Buffer template_buffer_{};
    lane_b::B002Buffer working_buffer_{};
    lane_b::B002Buffer aabb_min_buffer_{};
    lane_b::B002Buffer aabb_max_buffer_{};
    lane_b::B002Buffer overlap_counts_buffer_{};
    lane_b::B002Buffer offsets_buffer_{};
    lane_b::B002Buffer pairs_a_buffer_{};
    lane_b::B002Buffer pairs_b_buffer_{};
    lane_b::B002Buffer histogram_buffer_{};
    lane_b::B002Buffer block_offsets_buffer_{};
    lane_b::B002Buffer digit_base_buffer_{};
    lane_b::B002Buffer cell_ranges_buffer_{};
    lane_b::B002Buffer macro_ranges_buffer_{};
    lane_b::B002Buffer counters_buffer_{};
    lane_b::B002Buffer indirect_buffer_{};
    lane_b::B002Buffer stats_buffer_{};

    VkDescriptorSetLayout descriptor_layout_{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout_{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool_{VK_NULL_HANDLE};
    VkDescriptorSet descriptor_set_{VK_NULL_HANDLE};
    VkPipeline pipeline_{VK_NULL_HANDLE};

    F005GridMemory memory_{};
};

} // namespace phos::gi::research::lane_f

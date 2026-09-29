#include "f005_transient_grid.hpp"

#include "vk_init.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace phos::gi::research::lane_f {
namespace {

constexpr std::uint32_t kWorkgroupSize = 256U;
constexpr std::uint32_t kStatsWords = 9U;

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

[[nodiscard]] std::uint32_t groups_for(std::uint32_t count) {
    return (count + kWorkgroupSize - 1U) / kWorkgroupSize;
}

[[nodiscard]] std::uint32_t compute_pair_capacity(
    std::span<const lane_b::GpuTriangle> triangles,
    float cell_extent) {
    std::uint64_t total = 0U;
    for (const auto& triangle : triangles) {
        const auto axis_cells = [&](std::size_t axis) {
            const float lo = std::min({
                triangle.v0[axis], triangle.v1[axis], triangle.v2[axis]});
            const float hi = std::max({
                triangle.v0[axis], triangle.v1[axis], triangle.v2[axis]});
            const auto extent = std::max(0.0F, hi - lo);
            // Alignment-independent conservative capacity. An interval can
            // straddle one extra cell on each side relative to its extent.
            return std::uint64_t(std::ceil(extent / cell_extent)) + 2U;
        };
        const auto references =
            axis_cells(0) * axis_cells(1) * axis_cells(2);
        if (references == 0U ||
            references > std::numeric_limits<std::uint32_t>::max()) {
            fail("F005 per-triangle grid reference capacity overflow");
        }
        total += references;
        if (total > std::numeric_limits<std::uint32_t>::max()) {
            fail("F005 grid pair capacity exceeds 32-bit range");
        }
    }
    return std::max<std::uint32_t>(
        static_cast<std::uint32_t>(total),
        static_cast<std::uint32_t>(triangles.size()));
}

} // namespace

F005TransientGrid::F005TransientGrid(
    lane_b::B002VulkanContext& context,
    std::span<const lane_b::GpuTriangle> template_triangles,
    lane_b::Vec3 origin,
    float page_extent,
    std::filesystem::path builder_shader_path)
    : context_(context),
      count_(static_cast<std::uint32_t>(template_triangles.size())),
      origin_(origin),
      page_extent_(page_extent) {
    if (count_ == 0U || !(page_extent_ > 0.0F) ||
        !std::isfinite(page_extent_)) {
        fail("F005 invalid transient grid dimensions");
    }
    const auto cell_extent =
        page_extent_ / static_cast<float>(kF005LocalCellsPerAxis);
    pair_capacity_ =
        compute_pair_capacity(template_triangles, cell_extent);

    const auto storage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
    const auto triangle_bytes =
        VkDeviceSize(count_) * sizeof(lane_b::GpuTriangle);
    const auto aabb_bytes = VkDeviceSize(count_) * sizeof(float) * 4U;
    const auto count_bytes = VkDeviceSize(count_) * sizeof(std::uint32_t);
    const auto pair_bytes =
        VkDeviceSize(pair_capacity_) * sizeof(std::uint32_t) * 4U;
    const auto pair_groups = groups_for(pair_capacity_);
    const auto histogram_bytes =
        VkDeviceSize(pair_groups) * 16U * sizeof(std::uint32_t);
    const auto digit_bytes = VkDeviceSize(16U) * sizeof(std::uint32_t);
    const auto range_bytes =
        VkDeviceSize(pair_capacity_) * sizeof(std::uint32_t) * 4U;
    const auto counter_bytes = VkDeviceSize(12U) * sizeof(std::uint32_t);
    const auto indirect_bytes = VkDeviceSize(3U) * sizeof(std::uint32_t);
    const auto stats_bytes = VkDeviceSize(kStatsWords) * sizeof(std::uint32_t);

    template_buffer_ = context_.upload_device_buffer(
        template_triangles.data(), triangle_bytes, storage);
    working_buffer_ = context_.create_device_buffer(triangle_bytes, storage);
    aabb_min_buffer_ = context_.create_device_buffer(aabb_bytes, storage);
    aabb_max_buffer_ = context_.create_device_buffer(aabb_bytes, storage);
    overlap_counts_buffer_ = context_.create_device_buffer(count_bytes, storage);
    offsets_buffer_ = context_.create_device_buffer(count_bytes, storage);
    pairs_a_buffer_ = context_.create_device_buffer(pair_bytes, storage);
    pairs_b_buffer_ = context_.create_device_buffer(pair_bytes, storage);
    histogram_buffer_ = context_.create_device_buffer(histogram_bytes, storage);
    block_offsets_buffer_ = context_.create_device_buffer(histogram_bytes, storage);
    digit_base_buffer_ = context_.create_device_buffer(digit_bytes, storage);
    cell_ranges_buffer_ = context_.create_device_buffer(range_bytes, storage);
    macro_ranges_buffer_ = context_.create_device_buffer(range_bytes, storage);
    counters_buffer_ = context_.create_device_buffer(counter_bytes, storage);
    indirect_buffer_ = context_.create_device_buffer(
        indirect_bytes,
        storage | VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT);
    stats_buffer_ = context_.create_host_buffer(
        stats_bytes,
        storage | VK_BUFFER_USAGE_TRANSFER_DST_BIT);

    const auto alloc = [](const lane_b::B002Buffer& buffer) {
        return static_cast<std::size_t>(buffer.allocation_size);
    };
    memory_.persistent_bytes = alloc(template_buffer_);
    memory_.input_geometry_bytes = alloc(working_buffer_);
    memory_.pair_stream_bytes = alloc(pairs_a_buffer_);
    memory_.sort_scratch_bytes =
        alloc(pairs_b_buffer_) + alloc(histogram_buffer_) +
        alloc(block_offsets_buffer_) + alloc(digit_base_buffer_) +
        alloc(overlap_counts_buffer_) + alloc(offsets_buffer_) +
        alloc(counters_buffer_) + alloc(indirect_buffer_);
    memory_.transient_bytes =
        alloc(working_buffer_) + alloc(aabb_min_buffer_) +
        alloc(aabb_max_buffer_) + alloc(pairs_a_buffer_) +
        alloc(cell_ranges_buffer_) + alloc(macro_ranges_buffer_) +
        alloc(stats_buffer_);
    memory_.scratch_bytes = memory_.sort_scratch_bytes;
    memory_.peak_bytes =
        memory_.persistent_bytes + memory_.transient_bytes +
        memory_.scratch_bytes;

    constexpr std::size_t binding_count = 16U;
    std::array<const lane_b::B002Buffer*, binding_count> buffers{
        &template_buffer_,
        &working_buffer_,
        &aabb_min_buffer_,
        &aabb_max_buffer_,
        &overlap_counts_buffer_,
        &offsets_buffer_,
        &pairs_a_buffer_,
        &pairs_b_buffer_,
        &histogram_buffer_,
        &block_offsets_buffer_,
        &digit_base_buffer_,
        &cell_ranges_buffer_,
        &macro_ranges_buffer_,
        &counters_buffer_,
        &indirect_buffer_,
        &stats_buffer_,
    };
    std::array<VkDescriptorSetLayoutBinding, binding_count> layout_bindings{};
    for (std::uint32_t index = 0; index < binding_count; ++index) {
        layout_bindings[index].binding = index;
        layout_bindings[index].descriptorType =
            VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        layout_bindings[index].descriptorCount = 1;
        layout_bindings[index].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }

    auto set_layout_info =
        detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
    set_layout_info.bindingCount =
        static_cast<std::uint32_t>(layout_bindings.size());
    set_layout_info.pBindings = layout_bindings.data();
    if (context_.vk().createDescriptorSetLayout(
            &set_layout_info, nullptr, &descriptor_layout_) != VK_SUCCESS) {
        fail("F005 descriptor set layout");
    }

    VkPushConstantRange push_range{};
    push_range.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    push_range.offset = 0;
    push_range.size = sizeof(Push);

    auto pipeline_layout_info =
        detail::make_vk_info<VkPipelineLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
    pipeline_layout_info.setLayoutCount = 1;
    pipeline_layout_info.pSetLayouts = &descriptor_layout_;
    pipeline_layout_info.pushConstantRangeCount = 1;
    pipeline_layout_info.pPushConstantRanges = &push_range;
    if (context_.vk().createPipelineLayout(
            &pipeline_layout_info, nullptr, &pipeline_layout_) != VK_SUCCESS) {
        fail("F005 pipeline layout");
    }

    VkDescriptorPoolSize pool_size{
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
        static_cast<std::uint32_t>(binding_count),
    };
    auto pool_info = detail::make_vk_info<VkDescriptorPoolCreateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
    pool_info.maxSets = 1U;
    pool_info.poolSizeCount = 1U;
    pool_info.pPoolSizes = &pool_size;
    if (context_.vk().createDescriptorPool(
            &pool_info, nullptr, &descriptor_pool_) != VK_SUCCESS) {
        fail("F005 descriptor pool");
    }

    auto alloc_info =
        detail::make_vk_info<VkDescriptorSetAllocateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
    alloc_info.descriptorPool = descriptor_pool_;
    alloc_info.descriptorSetCount = 1U;
    alloc_info.pSetLayouts = &descriptor_layout_;
    if (context_.vk().allocateDescriptorSets(
            &alloc_info, &descriptor_set_) != VK_SUCCESS) {
        fail("F005 descriptor set");
    }

    std::array<VkDescriptorBufferInfo, binding_count> infos{};
    std::array<VkWriteDescriptorSet, binding_count> writes{};
    for (std::uint32_t index = 0; index < binding_count; ++index) {
        infos[index] = {
            buffers[index]->buffer, 0, buffers[index]->size};
        writes[index] =
            detail::make_vk_info<VkWriteDescriptorSet>(
                VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
        writes[index].dstSet = descriptor_set_;
        writes[index].dstBinding = index;
        writes[index].descriptorCount = 1;
        writes[index].descriptorType =
            VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        writes[index].pBufferInfo = &infos[index];
    }
    context_.vk().updateDescriptorSets(
        static_cast<std::uint32_t>(writes.size()),
        writes.data(), 0, nullptr);

    const auto code =
        lane_b::read_b002_binary(builder_shader_path.string());
    auto module_info =
        detail::make_vk_info<VkShaderModuleCreateInfo>(
            VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    module_info.codeSize = code.size();
    module_info.pCode =
        reinterpret_cast<const std::uint32_t*>(code.data());
    VkShaderModule module{VK_NULL_HANDLE};
    if (context_.vk().createShaderModule(
            &module_info, nullptr, &module) != VK_SUCCESS) {
        fail("F005 shader module");
    }

    auto stage =
        detail::make_vk_info<VkPipelineShaderStageCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
    stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
    stage.module = module;
    stage.pName = "main";
    auto pipeline_info =
        detail::make_vk_info<VkComputePipelineCreateInfo>(
            VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO);
    pipeline_info.stage = stage;
    pipeline_info.layout = pipeline_layout_;
    const auto result = context_.vk().createComputePipelines(
        VK_NULL_HANDLE, 1U, &pipeline_info, nullptr, &pipeline_);
    context_.vk().destroyShaderModule(module, nullptr);
    if (result != VK_SUCCESS) {
        fail("F005 compute pipeline");
    }
}

F005TransientGrid::~F005TransientGrid() {
    context_.vk().deviceWaitIdle();
    if (pipeline_ != VK_NULL_HANDLE)
        context_.vk().destroyPipeline(pipeline_, nullptr);
    if (descriptor_pool_ != VK_NULL_HANDLE)
        context_.vk().destroyDescriptorPool(descriptor_pool_, nullptr);
    if (pipeline_layout_ != VK_NULL_HANDLE)
        context_.vk().destroyPipelineLayout(pipeline_layout_, nullptr);
    if (descriptor_layout_ != VK_NULL_HANDLE)
        context_.vk().destroyDescriptorSetLayout(descriptor_layout_, nullptr);

    context_.destroy_buffer(stats_buffer_);
    context_.destroy_buffer(indirect_buffer_);
    context_.destroy_buffer(counters_buffer_);
    context_.destroy_buffer(macro_ranges_buffer_);
    context_.destroy_buffer(cell_ranges_buffer_);
    context_.destroy_buffer(digit_base_buffer_);
    context_.destroy_buffer(block_offsets_buffer_);
    context_.destroy_buffer(histogram_buffer_);
    context_.destroy_buffer(pairs_b_buffer_);
    context_.destroy_buffer(pairs_a_buffer_);
    context_.destroy_buffer(offsets_buffer_);
    context_.destroy_buffer(overlap_counts_buffer_);
    context_.destroy_buffer(aabb_max_buffer_);
    context_.destroy_buffer(aabb_min_buffer_);
    context_.destroy_buffer(working_buffer_);
    context_.destroy_buffer(template_buffer_);
}

void F005TransientGrid::compute_barrier(
    VkCommandBuffer command) const {
    auto barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask =
        VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    barrier.dstAccessMask =
        VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    context_.vk().cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        0, 1, &barrier, 0, nullptr, 0, nullptr);
}

void F005TransientGrid::compute_to_transfer_barrier(
    VkCommandBuffer command) const {
    auto barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask =
        VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    barrier.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    context_.vk().cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        0, 1, &barrier, 0, nullptr, 0, nullptr);
}

void F005TransientGrid::transfer_to_compute_barrier(
    VkCommandBuffer command) const {
    auto barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    barrier.dstAccessMask =
        VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    context_.vk().cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        0, 1, &barrier, 0, nullptr, 0, nullptr);
}

void F005TransientGrid::compute_to_indirect_barrier(
    VkCommandBuffer command) const {
    auto barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
    barrier.dstAccessMask = VK_ACCESS_INDIRECT_COMMAND_READ_BIT;
    context_.vk().cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_DRAW_INDIRECT_BIT,
        0, 1, &barrier, 0, nullptr, 0, nullptr);
}

void F005TransientGrid::dispatch(
    VkCommandBuffer command,
    std::uint32_t mode,
    std::uint32_t pass,
    std::uint32_t groups,
    float delta_x) const {
    Push push{};
    push.mode = mode;
    push.count = count_;
    push.pair_capacity = pair_capacity_;
    push.pass_index = pass;
    push.origin_page_extent[0] = origin_.x;
    push.origin_page_extent[1] = origin_.y;
    push.origin_page_extent[2] = origin_.z;
    push.origin_page_extent[3] = page_extent_;
    push.input_delta[0] = delta_x;
    push.grid_params[0] = kF005LocalCellsPerAxis;
    push.grid_params[1] = kF005RadixPasses;

    context_.vk().cmdPushConstants(
        command, pipeline_layout_,
        VK_SHADER_STAGE_COMPUTE_BIT,
        0, sizeof(Push), &push);
    context_.vk().cmdDispatch(command, groups, 1U, 1U);
}

void F005TransientGrid::record_build(
    VkCommandBuffer command,
    float delta_x,
    VkQueryPool query_pool,
    std::uint32_t query_base) const {
    auto stamp = [&](std::uint32_t slot) {
        context_.vk().cmdWriteTimestamp(
            command, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
            query_pool, query_base + slot);
    };

    stamp(0U);
    compute_to_transfer_barrier(command);
    context_.vk().cmdFillBuffer(
        command, overlap_counts_buffer_.buffer,
        0, overlap_counts_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, offsets_buffer_.buffer,
        0, offsets_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, histogram_buffer_.buffer,
        0, histogram_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, block_offsets_buffer_.buffer,
        0, block_offsets_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, digit_base_buffer_.buffer,
        0, digit_base_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, counters_buffer_.buffer,
        0, counters_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, counters_buffer_.buffer,
        4U * sizeof(std::uint32_t),
        3U * sizeof(std::uint32_t),
        0xffffffffU);
    context_.vk().cmdFillBuffer(
        command, indirect_buffer_.buffer,
        0, indirect_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, stats_buffer_.buffer,
        0, stats_buffer_.size, 0U);
    transfer_to_compute_barrier(command);
    stamp(1U);

    context_.vk().cmdBindPipeline(
        command, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_);
    context_.vk().cmdBindDescriptorSets(
        command, VK_PIPELINE_BIND_POINT_COMPUTE,
        pipeline_layout_, 0, 1, &descriptor_set_,
        0, nullptr);

    const auto primitive_groups = groups_for(count_);
    dispatch(command, 0U, 0U, primitive_groups, delta_x);
    compute_barrier(command);
    stamp(2U);

    dispatch(command, 1U, 0U, primitive_groups, delta_x);
    compute_barrier(command);
    stamp(3U);

    dispatch(command, 2U, 0U, 1U, delta_x);
    compute_barrier(command);
    compute_to_indirect_barrier(command);
    stamp(4U);

    dispatch(command, 3U, 0U, primitive_groups, delta_x);
    compute_barrier(command);
    stamp(5U);

    for (std::uint32_t pass = 0U;
         pass < kF005RadixPasses;
         ++pass) {
        Push push{};
        push.mode = 4U;
        push.count = count_;
        push.pair_capacity = pair_capacity_;
        push.pass_index = pass;
        push.origin_page_extent[0] = origin_.x;
        push.origin_page_extent[1] = origin_.y;
        push.origin_page_extent[2] = origin_.z;
        push.origin_page_extent[3] = page_extent_;
        push.input_delta[0] = delta_x;
        push.grid_params[0] = kF005LocalCellsPerAxis;
        push.grid_params[1] = kF005RadixPasses;
        context_.vk().cmdPushConstants(
            command, pipeline_layout_,
            VK_SHADER_STAGE_COMPUTE_BIT,
            0, sizeof(Push), &push);
        context_.vk().cmdDispatchIndirect(
            command, indirect_buffer_.buffer, 0U);
        compute_barrier(command);

        dispatch(command, 5U, pass, 1U, delta_x);
        compute_barrier(command);

        push.mode = 6U;
        context_.vk().cmdPushConstants(
            command, pipeline_layout_,
            VK_SHADER_STAGE_COMPUTE_BIT,
            0, sizeof(Push), &push);
        context_.vk().cmdDispatchIndirect(
            command, indirect_buffer_.buffer, 0U);
        compute_barrier(command);
    }
    stamp(6U);

    dispatch(command, 7U, 0U, 1U, delta_x);
    compute_barrier(command);
    stamp(7U);
}

F005GridTraversalPush
F005TransientGrid::traversal_push() const noexcept {
    F005GridTraversalPush push{};
    push.origin_page_extent[0] = origin_.x;
    push.origin_page_extent[1] = origin_.y;
    push.origin_page_extent[2] = origin_.z;
    push.origin_page_extent[3] = page_extent_;
    push.local_cells_per_axis = kF005LocalCellsPerAxis;
    push.pair_capacity = pair_capacity_;
    return push;
}

F005GridStats F005TransientGrid::stats() const noexcept {
    const auto* words =
        static_cast<const std::uint32_t*>(stats_buffer_.mapped);
    if (words == nullptr) return {};
    return {
        words[0],
        words[1],
        words[2],
        words[3],
        words[4],
        words[5],
        words[6],
        words[7],
        words[8],
    };
}

} // namespace phos::gi::research::lane_f

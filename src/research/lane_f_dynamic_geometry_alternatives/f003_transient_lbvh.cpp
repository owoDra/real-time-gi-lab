#include "f003_transient_lbvh.hpp"

#include "vk_init.hpp"

#include <array>
#include <cmath>
#include <stdexcept>

namespace phos::gi::research::lane_f {
namespace {

constexpr std::uint32_t kWorkgroupSize = 256U;
constexpr std::uint32_t kRadixPasses = 16U;
constexpr std::uint32_t kInvalidId = 0xffffffffU;

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

[[nodiscard]] std::uint32_t groups_for(std::uint32_t count) {
    return (count + kWorkgroupSize - 1U) / kWorkgroupSize;
}

} // namespace

F003TransientLbvh::F003TransientLbvh(
    lane_b::B002VulkanContext& context,
    std::span<const lane_b::GpuTriangle> template_triangles,
    lane_b::Vec3 origin,
    float page_extent,
    std::filesystem::path shader_path)
    : context_(context),
      count_(static_cast<std::uint32_t>(template_triangles.size())),
      origin_(origin),
      page_extent_(page_extent) {
    if (count_ < 2U || !(page_extent_ > 0.0F) || !std::isfinite(page_extent_)) {
        fail("F003 invalid transient LBVH dimensions");
    }

    const auto storage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
    const auto template_bytes =
        VkDeviceSize(count_) * sizeof(lane_b::GpuTriangle);
    const auto aabb_bytes = VkDeviceSize(count_) * sizeof(float) * 4U;
    const auto key_bytes = VkDeviceSize(count_) * sizeof(std::uint32_t) * 4U;
    const auto block_count = groups_for(count_);
    const auto histogram_bytes =
        VkDeviceSize(block_count) * 16U * sizeof(std::uint32_t);
    const auto digit_base_bytes = VkDeviceSize(16U) * sizeof(std::uint32_t);
    const auto node_bytes =
        VkDeviceSize(std::size_t(count_) * 2U - 1U) *
        sizeof(lane_b::GpuBvhNode);
    const auto ready_bytes =
        VkDeviceSize(count_ - 1U) * sizeof(std::uint32_t);

    template_buffer_ = context_.upload_device_buffer(
        template_triangles.data(), template_bytes, storage);
    working_buffer_ = context_.create_device_buffer(template_bytes, storage);
    aabb_min_buffer_ = context_.create_device_buffer(aabb_bytes, storage);
    aabb_max_buffer_ = context_.create_device_buffer(aabb_bytes, storage);
    keys_a_buffer_ = context_.create_device_buffer(key_bytes, storage);
    keys_b_buffer_ = context_.create_device_buffer(key_bytes, storage);
    histogram_buffer_ = context_.create_device_buffer(histogram_bytes, storage);
    offsets_buffer_ = context_.create_device_buffer(histogram_bytes, storage);
    digit_base_buffer_ = context_.create_device_buffer(digit_base_bytes, storage);
    nodes_buffer_ = context_.create_device_buffer(node_bytes, storage);
    ready_buffer_ = context_.create_device_buffer(ready_bytes, storage);

    const auto alloc = [](const lane_b::B002Buffer& b) {
        return static_cast<std::size_t>(b.allocation_size);
    };
    memory_.persistent_bytes = alloc(template_buffer_);
    // The immutable source template is persistent candidate state; the
    // working buffer is the current-frame world-space geometry.
    memory_.input_geometry_bytes = alloc(working_buffer_);
    memory_.transient_bytes =
        alloc(working_buffer_) + alloc(aabb_min_buffer_) + alloc(aabb_max_buffer_) +
        alloc(keys_a_buffer_) + alloc(keys_b_buffer_) + alloc(nodes_buffer_);
    memory_.scratch_bytes =
        alloc(histogram_buffer_) + alloc(offsets_buffer_) +
        alloc(digit_base_buffer_) + alloc(ready_buffer_);
    memory_.peak_bytes =
        memory_.persistent_bytes + memory_.transient_bytes + memory_.scratch_bytes;

    constexpr std::size_t binding_count = 11U;
    std::array<const lane_b::B002Buffer*, binding_count> buffers{
        &template_buffer_, &working_buffer_, &aabb_min_buffer_, &aabb_max_buffer_,
        &keys_a_buffer_, &keys_b_buffer_, &histogram_buffer_, &offsets_buffer_,
        &digit_base_buffer_, &nodes_buffer_, &ready_buffer_,
    };
    std::array<VkDescriptorSetLayoutBinding, binding_count> layout_bindings{};
    for (std::uint32_t index = 0; index < binding_count; ++index) {
        layout_bindings[index].binding = index;
        layout_bindings[index].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        layout_bindings[index].descriptorCount = 1;
        layout_bindings[index].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }

    auto set_layout_info = detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
    set_layout_info.bindingCount = static_cast<std::uint32_t>(layout_bindings.size());
    set_layout_info.pBindings = layout_bindings.data();
    if (context_.vk().createDescriptorSetLayout(
            &set_layout_info, nullptr, &descriptor_layout_) != VK_SUCCESS) {
        fail("F003 descriptor set layout");
    }

    VkPushConstantRange push_range{};
    push_range.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    push_range.offset = 0;
    push_range.size = sizeof(Push);

    auto pipeline_layout_info = detail::make_vk_info<VkPipelineLayoutCreateInfo>(
        VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
    pipeline_layout_info.setLayoutCount = 1;
    pipeline_layout_info.pSetLayouts = &descriptor_layout_;
    pipeline_layout_info.pushConstantRangeCount = 1;
    pipeline_layout_info.pPushConstantRanges = &push_range;
    if (context_.vk().createPipelineLayout(
            &pipeline_layout_info, nullptr, &pipeline_layout_) != VK_SUCCESS) {
        fail("F003 pipeline layout");
    }

    VkDescriptorPoolSize pool_size{
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
        static_cast<std::uint32_t>(binding_count),
    };
    auto pool_info = detail::make_vk_info<VkDescriptorPoolCreateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
    pool_info.maxSets = 1;
    pool_info.poolSizeCount = 1;
    pool_info.pPoolSizes = &pool_size;
    if (context_.vk().createDescriptorPool(
            &pool_info, nullptr, &descriptor_pool_) != VK_SUCCESS) {
        fail("F003 descriptor pool");
    }

    auto alloc_info = detail::make_vk_info<VkDescriptorSetAllocateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
    alloc_info.descriptorPool = descriptor_pool_;
    alloc_info.descriptorSetCount = 1;
    alloc_info.pSetLayouts = &descriptor_layout_;
    if (context_.vk().allocateDescriptorSets(
            &alloc_info, &descriptor_set_) != VK_SUCCESS) {
        fail("F003 descriptor set");
    }

    std::array<VkDescriptorBufferInfo, binding_count> infos{};
    std::array<VkWriteDescriptorSet, binding_count> writes{};
    for (std::uint32_t index = 0; index < binding_count; ++index) {
        infos[index] = {buffers[index]->buffer, 0, buffers[index]->size};
        writes[index] = detail::make_vk_info<VkWriteDescriptorSet>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
        writes[index].dstSet = descriptor_set_;
        writes[index].dstBinding = index;
        writes[index].descriptorCount = 1;
        writes[index].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        writes[index].pBufferInfo = &infos[index];
    }
    context_.vk().updateDescriptorSets(
        static_cast<std::uint32_t>(writes.size()), writes.data(), 0, nullptr);

    const auto code = lane_b::read_b002_binary(shader_path.string());
    auto module_info = detail::make_vk_info<VkShaderModuleCreateInfo>(
        VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    module_info.codeSize = code.size();
    module_info.pCode = reinterpret_cast<const std::uint32_t*>(code.data());
    VkShaderModule module{VK_NULL_HANDLE};
    if (context_.vk().createShaderModule(
            &module_info, nullptr, &module) != VK_SUCCESS) {
        fail("F003 shader module");
    }

    auto stage = detail::make_vk_info<VkPipelineShaderStageCreateInfo>(
        VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
    stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
    stage.module = module;
    stage.pName = "main";
    auto pipeline_info = detail::make_vk_info<VkComputePipelineCreateInfo>(
        VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO);
    pipeline_info.stage = stage;
    pipeline_info.layout = pipeline_layout_;
    const auto result = context_.vk().createComputePipelines(
        VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &pipeline_);
    context_.vk().destroyShaderModule(module, nullptr);
    if (result != VK_SUCCESS) fail("F003 compute pipeline");
}

F003TransientLbvh::~F003TransientLbvh() {
    context_.vk().deviceWaitIdle();
    if (pipeline_ != VK_NULL_HANDLE) context_.vk().destroyPipeline(pipeline_, nullptr);
    if (descriptor_pool_ != VK_NULL_HANDLE)
        context_.vk().destroyDescriptorPool(descriptor_pool_, nullptr);
    if (pipeline_layout_ != VK_NULL_HANDLE)
        context_.vk().destroyPipelineLayout(pipeline_layout_, nullptr);
    if (descriptor_layout_ != VK_NULL_HANDLE)
        context_.vk().destroyDescriptorSetLayout(descriptor_layout_, nullptr);

    context_.destroy_buffer(ready_buffer_);
    context_.destroy_buffer(nodes_buffer_);
    context_.destroy_buffer(digit_base_buffer_);
    context_.destroy_buffer(offsets_buffer_);
    context_.destroy_buffer(histogram_buffer_);
    context_.destroy_buffer(keys_b_buffer_);
    context_.destroy_buffer(keys_a_buffer_);
    context_.destroy_buffer(aabb_max_buffer_);
    context_.destroy_buffer(aabb_min_buffer_);
    context_.destroy_buffer(working_buffer_);
    context_.destroy_buffer(template_buffer_);
}

void F003TransientLbvh::compute_barrier(VkCommandBuffer command) const {
    auto barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    barrier.dstAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    context_.vk().cmdPipelineBarrier(
        command, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 1, &barrier,
        0, nullptr, 0, nullptr);
}

void F003TransientLbvh::compute_to_transfer_barrier(VkCommandBuffer command) const {
    auto barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    barrier.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    context_.vk().cmdPipelineBarrier(
        command, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 1, &barrier,
        0, nullptr, 0, nullptr);
}

void F003TransientLbvh::transfer_to_compute_barrier(VkCommandBuffer command) const {
    auto barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    barrier.dstAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    context_.vk().cmdPipelineBarrier(
        command, VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 1, &barrier,
        0, nullptr, 0, nullptr);
}

void F003TransientLbvh::dispatch(
    VkCommandBuffer command,
    std::uint32_t mode,
    std::uint32_t pass,
    std::uint32_t groups,
    float delta_x) const {
    Push push{};
    push.mode = mode;
    push.count = count_;
    push.template_count = count_;
    push.pass_index = pass;
    push.origin_page_extent[0] = origin_.x;
    push.origin_page_extent[1] = origin_.y;
    push.origin_page_extent[2] = origin_.z;
    push.origin_page_extent[3] = page_extent_;
    push.input_delta[0] = delta_x;

    context_.vk().cmdPushConstants(
        command, pipeline_layout_, VK_SHADER_STAGE_COMPUTE_BIT,
        0, sizeof(Push), &push);
    context_.vk().cmdDispatch(command, groups, 1, 1);
}

void F003TransientLbvh::record_build(
    VkCommandBuffer command,
    float delta_x,
    VkQueryPool query_pool,
    std::uint32_t query_base) const {
    auto stamp = [&](std::uint32_t slot) {
        context_.vk().cmdWriteTimestamp(
            command, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
            query_pool, query_base + slot);
    };

    stamp(0);
    compute_to_transfer_barrier(command);
    context_.vk().cmdFillBuffer(
        command, ready_buffer_.buffer, 0, ready_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, histogram_buffer_.buffer, 0, histogram_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, offsets_buffer_.buffer, 0, offsets_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, digit_base_buffer_.buffer, 0, digit_base_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, nodes_buffer_.buffer, 0, nodes_buffer_.size, kInvalidId);
    transfer_to_compute_barrier(command);
    stamp(1);

    context_.vk().cmdBindPipeline(command, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_);
    context_.vk().cmdBindDescriptorSets(
        command, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_layout_,
        0, 1, &descriptor_set_, 0, nullptr);

    const auto groups = groups_for(count_);
    dispatch(command, 0U, 0U, groups, delta_x);
    compute_barrier(command);
    stamp(2);

    dispatch(command, 1U, 0U, groups, delta_x);
    compute_barrier(command);
    stamp(3);

    dispatch(command, 2U, 0U, groups, delta_x);
    compute_barrier(command);
    stamp(4);

    for (std::uint32_t pass = 0U; pass < kRadixPasses; ++pass) {
        dispatch(command, 3U, pass, groups, delta_x);
        compute_barrier(command);
        dispatch(command, 4U, pass, 1U, delta_x);
        compute_barrier(command);
        dispatch(command, 5U, pass, groups, delta_x);
        compute_barrier(command);
    }
    stamp(5);

    dispatch(command, 6U, 0U, groups_for(count_ - 1U), delta_x);
    compute_barrier(command);
    stamp(6);

    dispatch(command, 7U, 0U, groups, delta_x);
    compute_barrier(command);
    stamp(7);
}

} // namespace phos::gi::research::lane_f

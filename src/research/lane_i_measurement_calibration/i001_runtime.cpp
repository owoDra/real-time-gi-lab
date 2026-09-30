#include "i001_runtime.hpp"
#include "vk_init.hpp"

#include <array>
#include <chrono>
#include <filesystem>
#include <stdexcept>

namespace phos::gi::research::lane_i {
namespace {

struct PushConstants {
    std::uint32_t element_count;
    std::uint32_t work_iterations;
    std::uint32_t reserved0;
    std::uint32_t reserved1;
};

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

VkBufferMemoryBarrier buffer_barrier(
    const GpuBuffer& buffer,
    VkAccessFlags src_access,
    VkAccessFlags dst_access) {
    auto barrier = detail::make_vk_info<VkBufferMemoryBarrier>(
        VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER);
    barrier.srcAccessMask = src_access;
    barrier.dstAccessMask = dst_access;
    barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.buffer = buffer.buffer;
    barrier.offset = 0;
    barrier.size = buffer.size;
    return barrier;
}

} // namespace

CalibrationGpu::CalibrationGpu(VulkanContext& context, std::uint32_t elements)
    : ctx_(context), elements_(elements), input_cpu_(make_input(elements)),
      initial_cpu_(make_initial_state(elements)) {
    const auto bytes = static_cast<VkDeviceSize>(elements_) * sizeof(std::uint32_t);
    input_ = ctx_.upload_device_buffer(
        input_cpu_.data(), bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    initial_ = ctx_.upload_device_buffer(
        initial_cpu_.data(), bytes,
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT);
    state_ = ctx_.create_device_buffer(
        bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    create_pipeline();
    create_commands();
}

CalibrationGpu::~CalibrationGpu() {
    ctx_.vk().deviceWaitIdle();
    if (fence_) ctx_.vk().destroyFence(fence_, nullptr);
    if (query_pool_) ctx_.vk().destroyQueryPool(query_pool_, nullptr);
    if (command_pool_) ctx_.vk().destroyCommandPool(command_pool_, nullptr);
    if (descriptor_pool_) ctx_.vk().destroyDescriptorPool(descriptor_pool_, nullptr);
    if (pipeline_) ctx_.vk().destroyPipeline(pipeline_, nullptr);
    if (pipeline_layout_) ctx_.vk().destroyPipelineLayout(pipeline_layout_, nullptr);
    if (descriptor_layout_) ctx_.vk().destroyDescriptorSetLayout(descriptor_layout_, nullptr);
    ctx_.destroy_buffer(state_);
    ctx_.destroy_buffer(initial_);
    ctx_.destroy_buffer(input_);
}

BatchResult CalibrationGpu::run(
    CalibrationVariant variant,
    std::uint32_t batch_dispatches) {
    const auto spec = make_work_spec(variant, elements_, batch_dispatches);
    const auto wall_start = std::chrono::steady_clock::now();

    ctx_.vk().resetCommandBuffer(command_buffer_, 0);
    auto begin = detail::make_vk_info<VkCommandBufferBeginInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (ctx_.vk().beginCommandBuffer(command_buffer_, &begin) != VK_SUCCESS) {
        fail("Lane I beginCommandBuffer failed");
    }
    ctx_.vk().cmdResetQueryPool(command_buffer_, query_pool_, 0, 2);

    VkBufferCopy copy{0, 0, state_.size};
    ctx_.vk().cmdCopyBuffer(command_buffer_, initial_.buffer, state_.buffer, 1, &copy);
    auto initial_ready = buffer_barrier(
        state_, VK_ACCESS_TRANSFER_WRITE_BIT,
        VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT);
    ctx_.vk().cmdPipelineBarrier(
        command_buffer_, VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 0, nullptr, 1,
        &initial_ready, 0, nullptr);

    ctx_.vk().cmdWriteTimestamp(
        command_buffer_, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, query_pool_, 0);
    ctx_.vk().cmdBindPipeline(
        command_buffer_, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_);
    ctx_.vk().cmdBindDescriptorSets(
        command_buffer_, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_layout_,
        0, 1, &descriptor_set_, 0, nullptr);
    const PushConstants constants{elements_, spec.work_iterations, 0U, 0U};
    ctx_.vk().cmdPushConstants(
        command_buffer_, pipeline_layout_, VK_SHADER_STAGE_COMPUTE_BIT,
        0, sizeof(constants), &constants);

    const auto groups = (elements_ + 255U) / 256U;
    for (std::uint32_t dispatch = 0; dispatch < batch_dispatches; ++dispatch) {
        ctx_.vk().cmdDispatch(command_buffer_, groups, 1, 1);
        if (dispatch + 1U != batch_dispatches) {
            auto next_dispatch = buffer_barrier(
                state_, VK_ACCESS_SHADER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT);
            ctx_.vk().cmdPipelineBarrier(
                command_buffer_, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 0, nullptr, 1,
                &next_dispatch, 0, nullptr);
        }
    }
    ctx_.vk().cmdWriteTimestamp(
        command_buffer_, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, query_pool_, 1);
    if (ctx_.vk().endCommandBuffer(command_buffer_) != VK_SUCCESS) {
        fail("Lane I endCommandBuffer failed");
    }

    ctx_.vk().resetFences(1, &fence_);
    auto submit = detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &command_buffer_;
    if (ctx_.vk().queueSubmit(ctx_.queue(), 1, &submit, fence_) != VK_SUCCESS) {
        fail("Lane I queueSubmit failed");
    }
    if (ctx_.vk().waitForFences(1, &fence_, VK_TRUE, UINT64_MAX) != VK_SUCCESS) {
        fail("Lane I waitForFences failed");
    }

    std::array<std::uint64_t, 2> timestamps{};
    if (ctx_.vk().getQueryPoolResults(
            query_pool_, 0, 2, sizeof(timestamps), timestamps.data(),
            sizeof(std::uint64_t),
            VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
        fail("Lane I timestamp query failed");
    }
    const auto wall_end = std::chrono::steady_clock::now();
    const double gpu_us =
        static_cast<double>(timestamps[1] - timestamps[0]) *
        static_cast<double>(ctx_.timestamp_period_ns()) / 1000.0;
    const double wall_us =
        std::chrono::duration<double, std::micro>(wall_end - wall_start).count();
    return {variant, gpu_us, wall_us, spec.controlled_work_units()};
}

std::uint64_t CalibrationGpu::download_checksum() {
    std::vector<std::uint32_t> values(elements_);
    ctx_.download_device_buffer(state_, values.data(), state_.size);
    return checksum(values);
}

std::uint64_t CalibrationGpu::reference_checksum(
    CalibrationVariant variant,
    std::uint32_t batch_dispatches) const {
    auto state = initial_cpu_;
    run_reference_batch(
        input_cpu_, state, work_iterations(variant), batch_dispatches);
    return checksum(state);
}

void CalibrationGpu::create_pipeline() {
    std::array<VkDescriptorSetLayoutBinding, 2> bindings{};
    for (std::uint32_t index = 0; index < bindings.size(); ++index) {
        bindings[index].binding = index;
        bindings[index].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        bindings[index].descriptorCount = 1;
        bindings[index].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }
    auto layout_info = detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
    layout_info.bindingCount = static_cast<std::uint32_t>(bindings.size());
    layout_info.pBindings = bindings.data();
    if (ctx_.vk().createDescriptorSetLayout(
            &layout_info, nullptr, &descriptor_layout_) != VK_SUCCESS) {
        fail("Lane I descriptor layout failed");
    }

    VkPushConstantRange range{VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(PushConstants)};
    auto pipeline_layout_info = detail::make_vk_info<VkPipelineLayoutCreateInfo>(
        VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
    pipeline_layout_info.setLayoutCount = 1;
    pipeline_layout_info.pSetLayouts = &descriptor_layout_;
    pipeline_layout_info.pushConstantRangeCount = 1;
    pipeline_layout_info.pPushConstantRanges = &range;
    if (ctx_.vk().createPipelineLayout(
            &pipeline_layout_info, nullptr, &pipeline_layout_) != VK_SUCCESS) {
        fail("Lane I pipeline layout failed");
    }

    const auto path = std::filesystem::path(PHOS_GI_LANE_I_SHADER_DIR) /
                      "lane_i_calibration.spv";
    const auto code = read_binary_file(path.string());
    auto module_info = detail::make_vk_info<VkShaderModuleCreateInfo>(
        VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    module_info.codeSize = code.size();
    module_info.pCode = reinterpret_cast<const std::uint32_t*>(code.data());
    VkShaderModule module{};
    if (ctx_.vk().createShaderModule(&module_info, nullptr, &module) != VK_SUCCESS) {
        fail("Lane I shader module failed");
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
    const auto result = ctx_.vk().createComputePipelines(
        VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &pipeline_);
    ctx_.vk().destroyShaderModule(module, nullptr);
    if (result != VK_SUCCESS) fail("Lane I compute pipeline failed");

    VkDescriptorPoolSize pool_size{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 2};
    auto pool_info = detail::make_vk_info<VkDescriptorPoolCreateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
    pool_info.maxSets = 1;
    pool_info.poolSizeCount = 1;
    pool_info.pPoolSizes = &pool_size;
    if (ctx_.vk().createDescriptorPool(&pool_info, nullptr, &descriptor_pool_) != VK_SUCCESS) {
        fail("Lane I descriptor pool failed");
    }
    auto allocate = detail::make_vk_info<VkDescriptorSetAllocateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
    allocate.descriptorPool = descriptor_pool_;
    allocate.descriptorSetCount = 1;
    allocate.pSetLayouts = &descriptor_layout_;
    if (ctx_.vk().allocateDescriptorSets(&allocate, &descriptor_set_) != VK_SUCCESS) {
        fail("Lane I descriptor allocation failed");
    }

    std::array<VkDescriptorBufferInfo, 2> infos{{
        {input_.buffer, 0, input_.size},
        {state_.buffer, 0, state_.size},
    }};
    std::array<VkWriteDescriptorSet, 2> writes{};
    for (std::uint32_t index = 0; index < writes.size(); ++index) {
        writes[index] = detail::make_vk_info<VkWriteDescriptorSet>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
        writes[index].dstSet = descriptor_set_;
        writes[index].dstBinding = index;
        writes[index].descriptorCount = 1;
        writes[index].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        writes[index].pBufferInfo = &infos[index];
    }
    ctx_.vk().updateDescriptorSets(
        static_cast<std::uint32_t>(writes.size()), writes.data(), 0, nullptr);
}

void CalibrationGpu::create_commands() {
    auto pool_info = detail::make_vk_info<VkCommandPoolCreateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
    pool_info.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    pool_info.queueFamilyIndex = ctx_.queue_family();
    if (ctx_.vk().createCommandPool(&pool_info, nullptr, &command_pool_) != VK_SUCCESS) {
        fail("Lane I command pool failed");
    }
    auto allocate = detail::make_vk_info<VkCommandBufferAllocateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    allocate.commandPool = command_pool_;
    allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocate.commandBufferCount = 1;
    if (ctx_.vk().allocateCommandBuffers(&allocate, &command_buffer_) != VK_SUCCESS) {
        fail("Lane I command buffer allocation failed");
    }
    auto query_info = detail::make_vk_info<VkQueryPoolCreateInfo>(
        VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
    query_info.queryType = VK_QUERY_TYPE_TIMESTAMP;
    query_info.queryCount = 2;
    if (ctx_.vk().createQueryPool(&query_info, nullptr, &query_pool_) != VK_SUCCESS) {
        fail("Lane I query pool failed");
    }
    auto fence_info = detail::make_vk_info<VkFenceCreateInfo>(
        VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    if (ctx_.vk().createFence(&fence_info, nullptr, &fence_) != VK_SUCCESS) {
        fail("Lane I fence failed");
    }
}

} // namespace phos::gi::research::lane_i

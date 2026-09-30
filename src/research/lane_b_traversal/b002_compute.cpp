#include "b002_compute.hpp"

#include "vk_init.hpp"

#include <algorithm>
#include <array>
#include <filesystem>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::lane_b {
namespace {

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

} // namespace

double median_us(std::vector<double> values) {
    if (values.empty()) return 0.0;
    const auto middle = values.begin() + values.size() / 2;
    std::nth_element(values.begin(), middle, values.end());
    if ((values.size() & 1U) != 0U) return *middle;
    const auto upper = *middle;
    const auto lower = *std::max_element(values.begin(), middle);
    return (lower + upper) * 0.5;
}

B002ComputeTraversal::B002ComputeTraversal(
    B002VulkanContext& context,
    std::string shader_path,
    std::span<const B002Buffer* const> bindings,
    std::size_t push_constant_bytes)
    : context_(context),
      push_constant_bytes_(push_constant_bytes) {
    if (bindings.empty() || push_constant_bytes == 0 ||
        push_constant_bytes > 128) {
        fail("B002 invalid compute traversal layout");
    }

    std::vector<VkDescriptorSetLayoutBinding> layout_bindings(bindings.size());
    for (std::uint32_t index = 0;
         index < static_cast<std::uint32_t>(layout_bindings.size());
         ++index) {
        layout_bindings[index].binding = index;
        layout_bindings[index].descriptorType =
            VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        layout_bindings[index].descriptorCount = 1;
        layout_bindings[index].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }

    auto layout_info =
        detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
    layout_info.bindingCount =
        static_cast<std::uint32_t>(layout_bindings.size());
    layout_info.pBindings = layout_bindings.data();
    if (context_.vk().createDescriptorSetLayout(
            &layout_info,
            nullptr,
            &descriptor_layout_) != VK_SUCCESS) {
        fail("B002 descriptor set layout");
    }

    VkPushConstantRange push_range{};
    push_range.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    push_range.offset = 0;
    push_range.size = static_cast<std::uint32_t>(push_constant_bytes_);

    auto pipeline_layout_info =
        detail::make_vk_info<VkPipelineLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
    pipeline_layout_info.setLayoutCount = 1;
    pipeline_layout_info.pSetLayouts = &descriptor_layout_;
    pipeline_layout_info.pushConstantRangeCount = 1;
    pipeline_layout_info.pPushConstantRanges = &push_range;
    if (context_.vk().createPipelineLayout(
            &pipeline_layout_info,
            nullptr,
            &pipeline_layout_) != VK_SUCCESS) {
        fail("B002 pipeline layout");
    }

    VkDescriptorPoolSize pool_size{
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
        static_cast<std::uint32_t>(bindings.size()),
    };
    auto pool_info = detail::make_vk_info<VkDescriptorPoolCreateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
    pool_info.maxSets = 1;
    pool_info.poolSizeCount = 1;
    pool_info.pPoolSizes = &pool_size;
    if (context_.vk().createDescriptorPool(
            &pool_info,
            nullptr,
            &descriptor_pool_) != VK_SUCCESS) {
        fail("B002 descriptor pool");
    }

    auto allocate_info = detail::make_vk_info<VkDescriptorSetAllocateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
    allocate_info.descriptorPool = descriptor_pool_;
    allocate_info.descriptorSetCount = 1;
    allocate_info.pSetLayouts = &descriptor_layout_;
    if (context_.vk().allocateDescriptorSets(
            &allocate_info,
            &descriptor_set_) != VK_SUCCESS) {
        fail("B002 descriptor set");
    }

    std::vector<VkDescriptorBufferInfo> buffer_infos(bindings.size());
    std::vector<VkWriteDescriptorSet> writes(bindings.size());
    for (std::uint32_t index = 0;
         index < static_cast<std::uint32_t>(bindings.size());
         ++index) {
        if (bindings[index] == nullptr ||
            bindings[index]->buffer == VK_NULL_HANDLE) {
            fail("B002 null traversal binding");
        }
        buffer_infos[index] = {
            bindings[index]->buffer,
            0,
            bindings[index]->size,
        };
        writes[index] = detail::make_vk_info<VkWriteDescriptorSet>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
        writes[index].dstSet = descriptor_set_;
        writes[index].dstBinding = index;
        writes[index].descriptorCount = 1;
        writes[index].descriptorType =
            VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        writes[index].pBufferInfo = &buffer_infos[index];
    }
    context_.vk().updateDescriptorSets(
        static_cast<std::uint32_t>(writes.size()),
        writes.data(),
        0,
        nullptr);

    const auto code = read_b002_binary(shader_path);
    auto module_info = detail::make_vk_info<VkShaderModuleCreateInfo>(
        VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    module_info.codeSize = code.size();
    module_info.pCode =
        reinterpret_cast<const std::uint32_t*>(code.data());
    VkShaderModule module{};
    if (context_.vk().createShaderModule(
            &module_info,
            nullptr,
            &module) != VK_SUCCESS) {
        fail("B002 shader module");
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
    const auto pipeline_result = context_.vk().createComputePipelines(
        VK_NULL_HANDLE,
        1,
        &pipeline_info,
        nullptr,
        &pipeline_);
    context_.vk().destroyShaderModule(module, nullptr);
    if (pipeline_result != VK_SUCCESS) {
        fail("B002 compute pipeline");
    }

    auto command_pool_info =
        detail::make_vk_info<VkCommandPoolCreateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
    command_pool_info.flags =
        VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    command_pool_info.queueFamilyIndex = context_.queue_family();
    if (context_.vk().createCommandPool(
            &command_pool_info,
            nullptr,
            &command_pool_) != VK_SUCCESS) {
        fail("B002 command pool");
    }

    auto query_info = detail::make_vk_info<VkQueryPoolCreateInfo>(
        VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
    query_info.queryType = VK_QUERY_TYPE_TIMESTAMP;
    query_info.queryCount = 512;
    if (context_.vk().createQueryPool(
            &query_info,
            nullptr,
            &query_pool_) != VK_SUCCESS) {
        fail("B002 query pool");
    }

    auto fence_info = detail::make_vk_info<VkFenceCreateInfo>(
        VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    if (context_.vk().createFence(
            &fence_info,
            nullptr,
            &fence_) != VK_SUCCESS) {
        fail("B002 traversal fence");
    }
}

B002ComputeTraversal::~B002ComputeTraversal() {
    context_.vk().deviceWaitIdle();
    if (fence_ != VK_NULL_HANDLE)
        context_.vk().destroyFence(fence_, nullptr);
    if (query_pool_ != VK_NULL_HANDLE)
        context_.vk().destroyQueryPool(query_pool_, nullptr);
    if (command_pool_ != VK_NULL_HANDLE)
        context_.vk().destroyCommandPool(command_pool_, nullptr);
    if (pipeline_ != VK_NULL_HANDLE)
        context_.vk().destroyPipeline(pipeline_, nullptr);
    if (descriptor_pool_ != VK_NULL_HANDLE)
        context_.vk().destroyDescriptorPool(descriptor_pool_, nullptr);
    if (pipeline_layout_ != VK_NULL_HANDLE)
        context_.vk().destroyPipelineLayout(pipeline_layout_, nullptr);
    if (descriptor_layout_ != VK_NULL_HANDLE)
        context_.vk().destroyDescriptorSetLayout(
            descriptor_layout_,
            nullptr);
}

void B002ComputeTraversal::record_dispatch(
    VkCommandBuffer command,
    std::uint32_t ray_count,
    const void* push_constants,
    std::size_t push_constant_bytes) {
    if (push_constant_bytes != push_constant_bytes_) {
        fail("B002 push constant size mismatch");
    }
    context_.vk().cmdBindPipeline(
        command,
        VK_PIPELINE_BIND_POINT_COMPUTE,
        pipeline_);
    context_.vk().cmdBindDescriptorSets(
        command,
        VK_PIPELINE_BIND_POINT_COMPUTE,
        pipeline_layout_,
        0,
        1,
        &descriptor_set_,
        0,
        nullptr);
    context_.vk().cmdPushConstants(
        command,
        pipeline_layout_,
        VK_SHADER_STAGE_COMPUTE_BIT,
        0,
        static_cast<std::uint32_t>(push_constant_bytes),
        push_constants);
    context_.vk().cmdDispatch(
        command,
        (ray_count + 63U) / 64U,
        1,
        1);
}

double B002ComputeTraversal::measure(
    std::uint32_t ray_count,
    std::uint32_t iterations,
    const void* push_constants,
    std::size_t push_constant_bytes) {
    if (ray_count == 0 || iterations == 0 || iterations > 255) {
        fail("B002 invalid traversal measurement dimensions");
    }

    context_.vk().resetFences(1, &fence_);
    context_.vk().resetCommandPool(command_pool_, 0);

    VkCommandBuffer command{};
    auto allocate_info = detail::make_vk_info<VkCommandBufferAllocateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    allocate_info.commandPool = command_pool_;
    allocate_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocate_info.commandBufferCount = 1;
    if (context_.vk().allocateCommandBuffers(
            &allocate_info,
            &command) != VK_SUCCESS) {
        fail("B002 traversal command buffer");
    }

    auto begin_info = detail::make_vk_info<VkCommandBufferBeginInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (context_.vk().beginCommandBuffer(
            command,
            &begin_info) != VK_SUCCESS) {
        fail("B002 traversal command begin");
    }

    context_.vk().cmdResetQueryPool(
        command,
        query_pool_,
        0,
        iterations * 2U);

    // One untimed dispatch warms pipeline/code caches. It is separated from the
    // first timestamp by an explicit shader write dependency.
    record_dispatch(
        command,
        ray_count,
        push_constants,
        push_constant_bytes);
    auto warmup_barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    warmup_barrier.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
    warmup_barrier.dstAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
    context_.vk().cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        0,
        1,
        &warmup_barrier,
        0,
        nullptr,
        0,
        nullptr);

    for (std::uint32_t iteration = 0;
         iteration < iterations;
         ++iteration) {
        context_.vk().cmdWriteTimestamp(
            command,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool_,
            iteration * 2U);
        record_dispatch(
            command,
            ray_count,
            push_constants,
            push_constant_bytes);
        context_.vk().cmdWriteTimestamp(
            command,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool_,
            iteration * 2U + 1U);

        if (iteration + 1U < iterations) {
            auto barrier = detail::make_vk_info<VkMemoryBarrier>(
                VK_STRUCTURE_TYPE_MEMORY_BARRIER);
            barrier.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
            barrier.dstAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
            context_.vk().cmdPipelineBarrier(
                command,
                VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                0,
                1,
                &barrier,
                0,
                nullptr,
                0,
                nullptr);
        }
    }

    if (context_.vk().endCommandBuffer(command) != VK_SUCCESS) {
        fail("B002 traversal command end");
    }

    auto submit_info = detail::make_vk_info<VkSubmitInfo>(
        VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit_info.commandBufferCount = 1;
    submit_info.pCommandBuffers = &command;
    if (context_.vk().queueSubmit(
            context_.queue(),
            1,
            &submit_info,
            fence_) != VK_SUCCESS) {
        fail("B002 traversal submit");
    }
    if (context_.vk().waitForFences(
            1,
            &fence_,
            VK_TRUE,
            UINT64_MAX) != VK_SUCCESS) {
        fail("B002 traversal wait");
    }

    std::vector<std::uint64_t> timestamps(iterations * 2U);
    if (context_.vk().getQueryPoolResults(
            query_pool_,
            0,
            iterations * 2U,
            timestamps.size() * sizeof(std::uint64_t),
            timestamps.data(),
            sizeof(std::uint64_t),
            VK_QUERY_RESULT_64_BIT |
                VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
        fail("B002 traversal timestamp readback");
    }

    std::vector<double> samples;
    samples.reserve(iterations);
    for (std::uint32_t iteration = 0;
         iteration < iterations;
         ++iteration) {
        const auto begin = timestamps[iteration * 2U];
        const auto end = timestamps[iteration * 2U + 1U];
        samples.push_back(
            double(end - begin) *
            double(context_.timestamp_period_ns()) /
            1000.0);
    }
    return median_us(std::move(samples));
}

} // namespace phos::gi::research::lane_b

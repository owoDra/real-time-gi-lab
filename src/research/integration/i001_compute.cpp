#include "i001_compute.hpp"

#include "../lane_b_traversal/b002_vulkan.hpp"
#include "vk_init.hpp"

#include <array>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::integration {
namespace {

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

} // namespace

I001ComputeStage::I001ComputeStage(
    B002VulkanContext& context,
    std::string shader_path,
    std::span<const I001Binding> bindings,
    std::size_t push_constant_bytes)
    : context_(context),
      push_constant_bytes_(push_constant_bytes) {
    if (bindings.empty() || push_constant_bytes > 128U) {
        fail("I001 invalid compute-stage layout");
    }

    std::vector<VkDescriptorSetLayoutBinding> layout;
    layout.reserve(bindings.size());
    std::array<std::uint32_t, 3> pool_counts{};
    for (const auto& binding : bindings) {
        VkDescriptorSetLayoutBinding value{};
        value.binding = binding.binding;
        value.descriptorType = binding.type;
        value.descriptorCount = 1;
        value.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
        layout.push_back(value);

        if (binding.type == VK_DESCRIPTOR_TYPE_STORAGE_BUFFER) {
            ++pool_counts[0];
        } else if (binding.type == VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER) {
            ++pool_counts[1];
        } else if (binding.type ==
                   VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR) {
            ++pool_counts[2];
        } else {
            fail("I001 unsupported descriptor type");
        }
    }

    auto layout_info =
        detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
    layout_info.bindingCount =
        static_cast<std::uint32_t>(layout.size());
    layout_info.pBindings = layout.data();
    if (context_.vk().createDescriptorSetLayout(
            &layout_info, nullptr, &descriptor_layout_) != VK_SUCCESS) {
        fail("I001 descriptor-set layout");
    }

    VkPushConstantRange push{};
    push.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    push.offset = 0;
    push.size = static_cast<std::uint32_t>(push_constant_bytes_);

    auto pipeline_layout_info =
        detail::make_vk_info<VkPipelineLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
    pipeline_layout_info.setLayoutCount = 1;
    pipeline_layout_info.pSetLayouts = &descriptor_layout_;
    if (push_constant_bytes_ != 0U) {
        pipeline_layout_info.pushConstantRangeCount = 1;
        pipeline_layout_info.pPushConstantRanges = &push;
    }
    if (context_.vk().createPipelineLayout(
            &pipeline_layout_info, nullptr, &pipeline_layout_) != VK_SUCCESS) {
        fail("I001 pipeline layout");
    }

    std::vector<VkDescriptorPoolSize> pool_sizes;
    if (pool_counts[0] != 0U) {
        pool_sizes.push_back(
            {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, pool_counts[0]});
    }
    if (pool_counts[1] != 0U) {
        pool_sizes.push_back(
            {VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, pool_counts[1]});
    }
    if (pool_counts[2] != 0U) {
        pool_sizes.push_back(
            {VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,
             pool_counts[2]});
    }

    auto pool_info =
        detail::make_vk_info<VkDescriptorPoolCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
    pool_info.maxSets = 1;
    pool_info.poolSizeCount =
        static_cast<std::uint32_t>(pool_sizes.size());
    pool_info.pPoolSizes = pool_sizes.data();
    if (context_.vk().createDescriptorPool(
            &pool_info, nullptr, &descriptor_pool_) != VK_SUCCESS) {
        fail("I001 descriptor pool");
    }

    auto allocation =
        detail::make_vk_info<VkDescriptorSetAllocateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
    allocation.descriptorPool = descriptor_pool_;
    allocation.descriptorSetCount = 1;
    allocation.pSetLayouts = &descriptor_layout_;
    if (context_.vk().allocateDescriptorSets(
            &allocation, &descriptor_set_) != VK_SUCCESS) {
        fail("I001 descriptor set");
    }

    for (const auto& binding : bindings) {
        auto write =
            detail::make_vk_info<VkWriteDescriptorSet>(
                VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
        write.dstSet = descriptor_set_;
        write.dstBinding = binding.binding;
        write.descriptorCount = 1;
        write.descriptorType = binding.type;

        VkDescriptorBufferInfo buffer_info{};
        auto acceleration_info =
            detail::make_vk_info<
                VkWriteDescriptorSetAccelerationStructureKHR>(
                VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET_ACCELERATION_STRUCTURE_KHR);
        if (binding.type ==
            VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR) {
            if (binding.acceleration == VK_NULL_HANDLE) {
                fail("I001 null acceleration-structure binding");
            }
            acceleration_info.accelerationStructureCount = 1;
            acceleration_info.pAccelerationStructures =
                &binding.acceleration;
            write.pNext = &acceleration_info;
        } else {
            if (binding.buffer == nullptr ||
                binding.buffer->buffer == VK_NULL_HANDLE) {
                fail("I001 null buffer binding");
            }
            buffer_info = {
                binding.buffer->buffer,
                0,
                binding.buffer->size,
            };
            write.pBufferInfo = &buffer_info;
        }
        context_.vk().updateDescriptorSets(
            1, &write, 0, nullptr);
    }

    const auto code =
        lane_b::read_b002_binary(shader_path);
    auto module_info =
        detail::make_vk_info<VkShaderModuleCreateInfo>(
            VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    module_info.codeSize = code.size();
    module_info.pCode =
        reinterpret_cast<const std::uint32_t*>(code.data());
    VkShaderModule module{};
    if (context_.vk().createShaderModule(
            &module_info, nullptr, &module) != VK_SUCCESS) {
        fail("I001 shader module");
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
        VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &pipeline_);
    context_.vk().destroyShaderModule(module, nullptr);
    if (result != VK_SUCCESS) {
        fail("I001 compute pipeline");
    }
}

I001ComputeStage::~I001ComputeStage() {
    if (pipeline_ != VK_NULL_HANDLE)
        context_.vk().destroyPipeline(pipeline_, nullptr);
    if (descriptor_pool_ != VK_NULL_HANDLE)
        context_.vk().destroyDescriptorPool(descriptor_pool_, nullptr);
    if (pipeline_layout_ != VK_NULL_HANDLE)
        context_.vk().destroyPipelineLayout(pipeline_layout_, nullptr);
    if (descriptor_layout_ != VK_NULL_HANDLE)
        context_.vk().destroyDescriptorSetLayout(
            descriptor_layout_, nullptr);
}

void I001ComputeStage::bind(
    VkCommandBuffer command,
    const void* push_constants,
    std::size_t push_constant_bytes) const {
    if (push_constant_bytes != push_constant_bytes_) {
        fail("I001 push-constant size mismatch");
    }
    if (push_constant_bytes != 0U && push_constants == nullptr) {
        fail("I001 missing push constants");
    }

    context_.vk().cmdBindPipeline(
        command, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_);
    context_.vk().cmdBindDescriptorSets(
        command,
        VK_PIPELINE_BIND_POINT_COMPUTE,
        pipeline_layout_,
        0,
        1,
        &descriptor_set_,
        0,
        nullptr);
    if (push_constant_bytes != 0U) {
        context_.vk().cmdPushConstants(
            command,
            pipeline_layout_,
            VK_SHADER_STAGE_COMPUTE_BIT,
            0,
            static_cast<std::uint32_t>(push_constant_bytes),
            push_constants);
    }
}

void I001ComputeStage::record(
    VkCommandBuffer command,
    std::uint32_t groups_x,
    std::uint32_t groups_y,
    std::uint32_t groups_z,
    const void* push_constants,
    std::size_t push_constant_bytes) const {
    bind(command, push_constants, push_constant_bytes);
    context_.vk().cmdDispatch(
        command, groups_x, groups_y, groups_z);
}

void I001ComputeStage::record_indirect(
    VkCommandBuffer command,
    VkBuffer indirect,
    VkDeviceSize offset,
    const void* push_constants,
    std::size_t push_constant_bytes) const {
    if (indirect == VK_NULL_HANDLE) {
        fail("I001 null indirect buffer");
    }
    bind(command, push_constants, push_constant_bytes);
    context_.vk().cmdDispatchIndirect(command, indirect, offset);
}

void i001_compute_barrier(
    B002VulkanContext& context,
    VkCommandBuffer command) {
    auto barrier =
        detail::make_vk_info<VkMemoryBarrier>(
            VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
    barrier.dstAccessMask =
        VK_ACCESS_SHADER_READ_BIT |
        VK_ACCESS_SHADER_WRITE_BIT |
        VK_ACCESS_INDIRECT_COMMAND_READ_BIT;
    context.vk().cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT |
            VK_PIPELINE_STAGE_DRAW_INDIRECT_BIT,
        0,
        1,
        &barrier,
        0,
        nullptr,
        0,
        nullptr);
}

void i001_transfer_to_compute_barrier(
    B002VulkanContext& context,
    VkCommandBuffer command) {
    auto barrier =
        detail::make_vk_info<VkMemoryBarrier>(
            VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    barrier.dstAccessMask =
        VK_ACCESS_SHADER_READ_BIT |
        VK_ACCESS_SHADER_WRITE_BIT;
    context.vk().cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        0,
        1,
        &barrier,
        0,
        nullptr,
        0,
        nullptr);
}

} // namespace phos::gi::research::integration

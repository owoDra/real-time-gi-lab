#include "j003_gpu_runtime.hpp"

#include "vk_init.hpp"

#include <array>
#include <cstdint>
#include <stdexcept>
#include <utility>

namespace phos::gi::research::lane_j {
namespace {

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

[[nodiscard]] std::size_t allocation_bytes(
    VulkanContext& context,
    const GpuBuffer& buffer) {
    VkMemoryRequirements requirements{};
    context.vk().getBufferMemoryRequirements(buffer.buffer, &requirements);
    return static_cast<std::size_t>(requirements.size);
}

struct RuntimeObjects {
    VulkanContext& context;
    std::array<GpuBuffer, 6> buffers{};
    VkDescriptorSetLayout descriptor_layout{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool{VK_NULL_HANDLE};
    VkPipeline pipeline{VK_NULL_HANDLE};
    VkCommandPool command_pool{VK_NULL_HANDLE};
    VkQueryPool query_pool{VK_NULL_HANDLE};
    VkFence fence{VK_NULL_HANDLE};

    ~RuntimeObjects() {
        auto& vk = context.vk();
        if (context.device() != VK_NULL_HANDLE) {
            vk.deviceWaitIdle();
        }
        if (fence != VK_NULL_HANDLE) {
            vk.destroyFence(fence, nullptr);
        }
        if (query_pool != VK_NULL_HANDLE) {
            vk.destroyQueryPool(query_pool, nullptr);
        }
        if (command_pool != VK_NULL_HANDLE) {
            vk.destroyCommandPool(command_pool, nullptr);
        }
        if (pipeline != VK_NULL_HANDLE) {
            vk.destroyPipeline(pipeline, nullptr);
        }
        if (descriptor_pool != VK_NULL_HANDLE) {
            vk.destroyDescriptorPool(descriptor_pool, nullptr);
        }
        if (pipeline_layout != VK_NULL_HANDLE) {
            vk.destroyPipelineLayout(pipeline_layout, nullptr);
        }
        if (descriptor_layout != VK_NULL_HANDLE) {
            vk.destroyDescriptorSetLayout(descriptor_layout, nullptr);
        }
        for (auto& buffer : buffers) {
            context.destroy_buffer(buffer);
        }
    }
};

struct Push {
    std::uint32_t ray_count{};
    std::uint32_t upper_root{};
    std::uint32_t upper_node_count{};
    std::uint32_t micro_node_count{};
    std::uint32_t cluster_count{};
    std::uint32_t triangle_count{};
    std::uint32_t debug_ray_index{kInvalidId};
    std::uint32_t debug_primitive_id{kInvalidId};
};
static_assert(sizeof(Push) == 32);

} // namespace

GpuTraversalResult run_gpu_traversal_probe(
    VulkanContext& context,
    const ClusteredBvhData& bvh,
    std::span<const GpuRay> rays,
    const std::filesystem::path& shader_path) {
    if (bvh.triangles.empty() ||
        bvh.clusters.empty() ||
        bvh.upper_nodes.empty() ||
        bvh.micro_nodes.empty() ||
        rays.empty()) {
        fail("J003 GPU traversal received empty input");
    }
    if (bvh.upper_root >= bvh.upper_nodes.size()) {
        fail("J003 upper root is out of range");
    }

    RuntimeObjects runtime{context};
    constexpr auto storage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;

    runtime.buffers[0] = context.upload_device_buffer(
        bvh.triangles.data(),
        VkDeviceSize(bvh.triangles.size() * sizeof(GpuTriangle)),
        storage);
    runtime.buffers[1] = context.upload_device_buffer(
        bvh.upper_nodes.data(),
        VkDeviceSize(bvh.upper_nodes.size() * sizeof(GpuBvhNode)),
        storage);
    runtime.buffers[2] = context.upload_device_buffer(
        bvh.micro_nodes.data(),
        VkDeviceSize(bvh.micro_nodes.size() * sizeof(GpuBvhNode)),
        storage);
    runtime.buffers[3] = context.upload_device_buffer(
        bvh.clusters.data(),
        VkDeviceSize(bvh.clusters.size() * sizeof(GpuCluster)),
        storage);
    runtime.buffers[4] = context.upload_device_buffer(
        rays.data(),
        VkDeviceSize(rays.size() * sizeof(GpuRay)),
        storage);
    runtime.buffers[5] = context.create_device_buffer(
        VkDeviceSize(rays.size() * sizeof(GpuHit)),
        storage);

    std::array<VkDescriptorSetLayoutBinding, 6> bindings{};
    for (std::uint32_t index = 0U; index < bindings.size(); ++index) {
        bindings[index].binding = index;
        bindings[index].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        bindings[index].descriptorCount = 1U;
        bindings[index].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }

    auto descriptor_layout_info =
        detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
    descriptor_layout_info.bindingCount =
        static_cast<std::uint32_t>(bindings.size());
    descriptor_layout_info.pBindings = bindings.data();
    if (context.vk().createDescriptorSetLayout(
            &descriptor_layout_info,
            nullptr,
            &runtime.descriptor_layout) != VK_SUCCESS) {
        fail("J003 descriptor set layout creation failed");
    }

    VkPushConstantRange push_range{};
    push_range.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    push_range.offset = 0U;
    push_range.size = sizeof(Push);

    auto pipeline_layout_info =
        detail::make_vk_info<VkPipelineLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
    pipeline_layout_info.setLayoutCount = 1U;
    pipeline_layout_info.pSetLayouts = &runtime.descriptor_layout;
    pipeline_layout_info.pushConstantRangeCount = 1U;
    pipeline_layout_info.pPushConstantRanges = &push_range;
    if (context.vk().createPipelineLayout(
            &pipeline_layout_info,
            nullptr,
            &runtime.pipeline_layout) != VK_SUCCESS) {
        fail("J003 pipeline layout creation failed");
    }

    VkDescriptorPoolSize pool_size{
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
        static_cast<std::uint32_t>(runtime.buffers.size()),
    };
    auto pool_info = detail::make_vk_info<VkDescriptorPoolCreateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
    pool_info.maxSets = 1U;
    pool_info.poolSizeCount = 1U;
    pool_info.pPoolSizes = &pool_size;
    if (context.vk().createDescriptorPool(
            &pool_info,
            nullptr,
            &runtime.descriptor_pool) != VK_SUCCESS) {
        fail("J003 descriptor pool creation failed");
    }

    VkDescriptorSet descriptor_set{VK_NULL_HANDLE};
    auto allocate_info = detail::make_vk_info<VkDescriptorSetAllocateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
    allocate_info.descriptorPool = runtime.descriptor_pool;
    allocate_info.descriptorSetCount = 1U;
    allocate_info.pSetLayouts = &runtime.descriptor_layout;
    if (context.vk().allocateDescriptorSets(
            &allocate_info,
            &descriptor_set) != VK_SUCCESS) {
        fail("J003 descriptor set allocation failed");
    }

    std::array<VkDescriptorBufferInfo, 6> buffer_infos{};
    std::array<VkWriteDescriptorSet, 6> writes{};
    for (std::uint32_t index = 0U; index < runtime.buffers.size(); ++index) {
        buffer_infos[index] = {
            runtime.buffers[index].buffer,
            0U,
            runtime.buffers[index].size,
        };
        writes[index] = detail::make_vk_info<VkWriteDescriptorSet>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
        writes[index].dstSet = descriptor_set;
        writes[index].dstBinding = index;
        writes[index].descriptorCount = 1U;
        writes[index].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        writes[index].pBufferInfo = &buffer_infos[index];
    }
    context.vk().updateDescriptorSets(
        static_cast<std::uint32_t>(writes.size()),
        writes.data(),
        0U,
        nullptr);

    const auto shader = read_binary_file(shader_path.string());
    if (shader.empty() || shader.size() % sizeof(std::uint32_t) != 0U) {
        fail("J003 invalid shader binary");
    }
    auto module_info = detail::make_vk_info<VkShaderModuleCreateInfo>(
        VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    module_info.codeSize = shader.size();
    module_info.pCode =
        reinterpret_cast<const std::uint32_t*>(shader.data());
    VkShaderModule module{VK_NULL_HANDLE};
    if (context.vk().createShaderModule(
            &module_info,
            nullptr,
            &module) != VK_SUCCESS) {
        fail("J003 shader module creation failed");
    }

    auto stage = detail::make_vk_info<VkPipelineShaderStageCreateInfo>(
        VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
    stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
    stage.module = module;
    stage.pName = "main";

    auto pipeline_info = detail::make_vk_info<VkComputePipelineCreateInfo>(
        VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO);
    pipeline_info.stage = stage;
    pipeline_info.layout = runtime.pipeline_layout;
    const auto pipeline_result = context.vk().createComputePipelines(
        VK_NULL_HANDLE,
        1U,
        &pipeline_info,
        nullptr,
        &runtime.pipeline);
    context.vk().destroyShaderModule(module, nullptr);
    if (pipeline_result != VK_SUCCESS) {
        fail("J003 compute pipeline creation failed");
    }

    auto command_pool_info = detail::make_vk_info<VkCommandPoolCreateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
    command_pool_info.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
    command_pool_info.queueFamilyIndex = context.queue_family();
    if (context.vk().createCommandPool(
            &command_pool_info,
            nullptr,
            &runtime.command_pool) != VK_SUCCESS) {
        fail("J003 command pool creation failed");
    }

    VkCommandBuffer command{VK_NULL_HANDLE};
    auto command_allocate =
        detail::make_vk_info<VkCommandBufferAllocateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    command_allocate.commandPool = runtime.command_pool;
    command_allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    command_allocate.commandBufferCount = 1U;
    if (context.vk().allocateCommandBuffers(
            &command_allocate,
            &command) != VK_SUCCESS) {
        fail("J003 command buffer allocation failed");
    }

    auto query_info = detail::make_vk_info<VkQueryPoolCreateInfo>(
        VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
    query_info.queryType = VK_QUERY_TYPE_TIMESTAMP;
    query_info.queryCount = 2U;
    if (context.vk().createQueryPool(
            &query_info,
            nullptr,
            &runtime.query_pool) != VK_SUCCESS) {
        fail("J003 query pool creation failed");
    }

    auto fence_info = detail::make_vk_info<VkFenceCreateInfo>(
        VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    if (context.vk().createFence(
            &fence_info,
            nullptr,
            &runtime.fence) != VK_SUCCESS) {
        fail("J003 fence creation failed");
    }

    auto begin_info = detail::make_vk_info<VkCommandBufferBeginInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (context.vk().beginCommandBuffer(command, &begin_info) != VK_SUCCESS) {
        fail("J003 command buffer begin failed");
    }

    context.vk().cmdResetQueryPool(command, runtime.query_pool, 0U, 2U);
    context.vk().cmdBindPipeline(
        command,
        VK_PIPELINE_BIND_POINT_COMPUTE,
        runtime.pipeline);
    context.vk().cmdBindDescriptorSets(
        command,
        VK_PIPELINE_BIND_POINT_COMPUTE,
        runtime.pipeline_layout,
        0U,
        1U,
        &descriptor_set,
        0U,
        nullptr);

    const Push push{
        static_cast<std::uint32_t>(rays.size()),
        bvh.upper_root,
        static_cast<std::uint32_t>(bvh.upper_nodes.size()),
        static_cast<std::uint32_t>(bvh.micro_nodes.size()),
        static_cast<std::uint32_t>(bvh.clusters.size()),
        static_cast<std::uint32_t>(bvh.triangles.size()),
        kInvalidId,
        kInvalidId,
    };
    context.vk().cmdPushConstants(
        command,
        runtime.pipeline_layout,
        VK_SHADER_STAGE_COMPUTE_BIT,
        0U,
        sizeof(Push),
        &push);

    context.vk().cmdWriteTimestamp(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        runtime.query_pool,
        0U);
    const auto groups =
        (static_cast<std::uint32_t>(rays.size()) + 63U) / 64U;
    context.vk().cmdDispatch(command, groups, 1U, 1U);
    context.vk().cmdWriteTimestamp(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        runtime.query_pool,
        1U);

    auto shader_to_transfer =
        detail::make_vk_info<VkMemoryBarrier>(
            VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    shader_to_transfer.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
    shader_to_transfer.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
    context.vk().cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        0U,
        1U,
        &shader_to_transfer,
        0U,
        nullptr,
        0U,
        nullptr);

    if (context.vk().endCommandBuffer(command) != VK_SUCCESS) {
        fail("J003 command buffer end failed");
    }

    auto submit_info = detail::make_vk_info<VkSubmitInfo>(
        VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit_info.commandBufferCount = 1U;
    submit_info.pCommandBuffers = &command;
    if (context.vk().queueSubmit(
            context.queue(),
            1U,
            &submit_info,
            runtime.fence) != VK_SUCCESS) {
        fail("J003 queue submit failed");
    }
    if (context.vk().waitForFences(
            1U,
            &runtime.fence,
            VK_TRUE,
            UINT64_MAX) != VK_SUCCESS) {
        fail("J003 fence wait failed");
    }

    std::array<std::uint64_t, 2> timestamps{};
    if (context.vk().getQueryPoolResults(
            runtime.query_pool,
            0U,
            2U,
            sizeof(timestamps),
            timestamps.data(),
            sizeof(std::uint64_t),
            VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
        fail("J003 timestamp readback failed");
    }

    GpuTraversalResult result{};
    result.hits.resize(rays.size());
    context.download_device_buffer(
        runtime.buffers[5],
        result.hits.data(),
        VkDeviceSize(result.hits.size() * sizeof(GpuHit)));
    result.traversal_gpu_us =
        double(timestamps[1] - timestamps[0]) *
        double(context.timestamp_period_ns()) /
        1000.0;

    constexpr std::array<const char*, 6> names{
        "candidate.triangles",
        "candidate.upper-nodes",
        "candidate.micro-nodes",
        "candidate.clusters",
        "validation.rays",
        "validation.hits",
    };
    for (std::size_t index = 0U; index < runtime.buffers.size(); ++index) {
        const auto bytes = allocation_bytes(context, runtime.buffers[index]);
        const auto candidate = index < 4U;
        result.allocations.push_back({
            names[index],
            candidate ? "candidate-persistent" : "validation-harness",
            static_cast<std::size_t>(runtime.buffers[index].size),
            bytes,
        });
        if (candidate) {
            result.candidate_persistent_bytes += bytes;
        } else {
            result.validation_harness_bytes += bytes;
        }
    }

    return result;
}

} // namespace phos::gi::research::lane_j

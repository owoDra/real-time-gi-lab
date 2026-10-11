#include "j003_persistent_gpu.hpp"

#include "vk_init.hpp"

#include <algorithm>
#include <array>
#include <cstring>
#include <stdexcept>
#include <utility>
#include <vector>

namespace phos::gi::research::lane_j {
namespace {

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

template <typename T>
[[nodiscard]] const std::byte* bytes_at(
    const std::vector<T>& values,
    std::size_t index) {
    return reinterpret_cast<const std::byte*>(values.data() + index);
}

struct TraversalPush {
    std::uint32_t ray_count{};
    std::uint32_t upper_root{};
    std::uint32_t upper_node_count{};
    std::uint32_t micro_node_count{};
    std::uint32_t cluster_count{};
    std::uint32_t triangle_count{};
    std::uint32_t debug_ray_index{kInvalidId};
    std::uint32_t debug_primitive_id{kInvalidId};
};
static_assert(sizeof(TraversalPush) == 32);

struct ValidationRuntime {
    VulkanContext& context;
    GpuBuffer rays{};
    GpuBuffer hits{};
    VkDescriptorSetLayout descriptor_layout{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool{VK_NULL_HANDLE};
    VkPipeline pipeline{VK_NULL_HANDLE};
    VkCommandPool command_pool{VK_NULL_HANDLE};
    VkQueryPool query_pool{VK_NULL_HANDLE};
    VkFence fence{VK_NULL_HANDLE};

    ~ValidationRuntime() {
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
        context.destroy_buffer(rays);
        context.destroy_buffer(hits);
    }
};

} // namespace

PersistentGpuState::PersistentGpuState(
    VulkanContext& context,
    const PersistentClusterLayout& layout)
    : context_(context) {
    auto buffers = create_buffer_set(layout);
    std::uint32_t regions = 0U;
    std::size_t uploaded = 0U;
    try {
        (void)upload_full_layout(
            buffers,
            layout,
            regions,
            uploaded);
    } catch (...) {
        destroy_buffer_set(buffers);
        throw;
    }
    triangles_ = std::exchange(buffers.triangles, {});
    upper_ = std::exchange(buffers.upper, {});
    micro_ = std::exchange(buffers.micro, {});
    clusters_ = std::exchange(buffers.clusters, {});
}

PersistentGpuState::~PersistentGpuState() {
    BufferSet buffers{
        std::exchange(triangles_, {}),
        std::exchange(upper_, {}),
        std::exchange(micro_, {}),
        std::exchange(clusters_, {}),
    };
    destroy_buffer_set(buffers);
}

PersistentGpuState::BufferSet PersistentGpuState::create_buffer_set(
    const PersistentClusterLayout& layout) {
    constexpr auto usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
    BufferSet buffers{};
    try {
        buffers.triangles = context_.create_device_buffer(
            VkDeviceSize(layout.triangles().size() * sizeof(GpuTriangle)),
            usage);
        buffers.upper = context_.create_device_buffer(
            VkDeviceSize(layout.upper_nodes().size() * sizeof(GpuBvhNode)),
            usage);
        buffers.micro = context_.create_device_buffer(
            VkDeviceSize(layout.micro_nodes().size() * sizeof(GpuBvhNode)),
            usage);
        buffers.clusters = context_.create_device_buffer(
            VkDeviceSize(layout.clusters().size() * sizeof(GpuCluster)),
            usage);
    } catch (...) {
        destroy_buffer_set(buffers);
        throw;
    }
    return buffers;
}

void PersistentGpuState::destroy_buffer_set(BufferSet& buffers) {
    context_.destroy_buffer(buffers.triangles);
    context_.destroy_buffer(buffers.upper);
    context_.destroy_buffer(buffers.micro);
    context_.destroy_buffer(buffers.clusters);
}

std::size_t PersistentGpuState::allocation_bytes(
    const GpuBuffer& buffer) const {
    if (buffer.buffer == VK_NULL_HANDLE) {
        return 0U;
    }
    VkMemoryRequirements requirements{};
    context_.vk().getBufferMemoryRequirements(
        buffer.buffer,
        &requirements);
    return static_cast<std::size_t>(requirements.size);
}

std::size_t PersistentGpuState::allocation_bytes(
    const BufferSet& buffers) const {
    return allocation_bytes(buffers.triangles) +
           allocation_bytes(buffers.upper) +
           allocation_bytes(buffers.micro) +
           allocation_bytes(buffers.clusters);
}

std::size_t PersistentGpuState::persistent_allocation_bytes() const {
    BufferSet view{triangles_, upper_, micro_, clusters_};
    return allocation_bytes(view);
}

std::size_t PersistentGpuState::upload_regions(
    GpuBuffer& destination,
    std::span<const CopyRegion> regions,
    std::uint32_t& region_count,
    std::size_t& uploaded_logical_bytes) {
    if (regions.empty()) {
        return 0U;
    }

    VkDeviceSize staging_size = 0U;
    for (const auto& region : regions) {
        if (region.source == nullptr || region.size == 0U) {
            fail("J003 persistent upload contains empty region");
        }
        if (region.destination_offset + region.size > destination.size) {
            fail("J003 persistent upload exceeds destination");
        }
        staging_size += region.size;
    }

    auto staging = context_.create_host_buffer(
        staging_size,
        VK_BUFFER_USAGE_TRANSFER_SRC_BIT);
    const auto staging_allocation = allocation_bytes(staging);

    VkCommandPool pool{VK_NULL_HANDLE};
    VkFence fence{VK_NULL_HANDLE};
    try {
        std::vector<VkBufferCopy> copies;
        copies.reserve(regions.size());

        VkDeviceSize source_offset = 0U;
        for (const auto& region : regions) {
            std::memcpy(
                static_cast<std::byte*>(staging.mapped) + source_offset,
                region.source,
                static_cast<std::size_t>(region.size));
            copies.push_back({
                source_offset,
                region.destination_offset,
                region.size,
            });
            source_offset += region.size;
            ++region_count;
            uploaded_logical_bytes +=
                static_cast<std::size_t>(region.size);
        }

        auto pool_info =
            detail::make_vk_info<VkCommandPoolCreateInfo>(
                VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
        pool_info.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
        pool_info.queueFamilyIndex = context_.queue_family();
        if (context_.vk().createCommandPool(
                &pool_info,
                nullptr,
                &pool) != VK_SUCCESS) {
            fail("J003 persistent upload command pool");
        }

        VkCommandBuffer command{VK_NULL_HANDLE};
        auto allocate =
            detail::make_vk_info<VkCommandBufferAllocateInfo>(
                VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
        allocate.commandPool = pool;
        allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        allocate.commandBufferCount = 1U;
        if (context_.vk().allocateCommandBuffers(
                &allocate,
                &command) != VK_SUCCESS) {
            fail("J003 persistent upload command buffer");
        }

        auto begin =
            detail::make_vk_info<VkCommandBufferBeginInfo>(
                VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
        begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        if (context_.vk().beginCommandBuffer(
                command,
                &begin) != VK_SUCCESS) {
            fail("J003 persistent upload begin");
        }

        auto before = detail::make_vk_info<VkMemoryBarrier>(
            VK_STRUCTURE_TYPE_MEMORY_BARRIER);
        before.srcAccessMask = VK_ACCESS_MEMORY_READ_BIT |
                               VK_ACCESS_MEMORY_WRITE_BIT;
        before.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        context_.vk().cmdPipelineBarrier(
            command,
            VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            0U,
            1U,
            &before,
            0U,
            nullptr,
            0U,
            nullptr);

        context_.vk().cmdCopyBuffer(
            command,
            staging.buffer,
            destination.buffer,
            static_cast<std::uint32_t>(copies.size()),
            copies.data());

        auto after = detail::make_vk_info<VkMemoryBarrier>(
            VK_STRUCTURE_TYPE_MEMORY_BARRIER);
        after.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        after.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
        context_.vk().cmdPipelineBarrier(
            command,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            0U,
            1U,
            &after,
            0U,
            nullptr,
            0U,
            nullptr);

        if (context_.vk().endCommandBuffer(command) != VK_SUCCESS) {
            fail("J003 persistent upload end");
        }

        auto fence_info =
            detail::make_vk_info<VkFenceCreateInfo>(
                VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
        if (context_.vk().createFence(
                &fence_info,
                nullptr,
                &fence) != VK_SUCCESS) {
            fail("J003 persistent upload fence");
        }

        auto submit = detail::make_vk_info<VkSubmitInfo>(
            VK_STRUCTURE_TYPE_SUBMIT_INFO);
        submit.commandBufferCount = 1U;
        submit.pCommandBuffers = &command;
        if (context_.vk().queueSubmit(
                context_.queue(),
                1U,
                &submit,
                fence) != VK_SUCCESS) {
            fail("J003 persistent upload submit");
        }
        if (context_.vk().waitForFences(
                1U,
                &fence,
                VK_TRUE,
                UINT64_MAX) != VK_SUCCESS) {
            fail("J003 persistent upload wait");
        }
    } catch (...) {
        if (fence != VK_NULL_HANDLE) {
            context_.vk().destroyFence(fence, nullptr);
        }
        if (pool != VK_NULL_HANDLE) {
            context_.vk().destroyCommandPool(pool, nullptr);
        }
        context_.destroy_buffer(staging);
        throw;
    }

    context_.vk().destroyFence(fence, nullptr);
    context_.vk().destroyCommandPool(pool, nullptr);
    context_.destroy_buffer(staging);
    return staging_allocation;
}

std::size_t PersistentGpuState::upload_full_layout(
    BufferSet& buffers,
    const PersistentClusterLayout& layout,
    std::uint32_t& region_count,
    std::size_t& uploaded_logical_bytes) {
    std::size_t max_staging = 0U;

    const std::array<CopyRegion, 1> triangle_region{{
        reinterpret_cast<const std::byte*>(layout.triangles().data()),
        0U,
        VkDeviceSize(layout.triangles().size() * sizeof(GpuTriangle)),
    }};
    max_staging = std::max(
        max_staging,
        upload_regions(
            buffers.triangles,
            triangle_region,
            region_count,
            uploaded_logical_bytes));

    const std::array<CopyRegion, 1> upper_region{{
        reinterpret_cast<const std::byte*>(layout.upper_nodes().data()),
        0U,
        VkDeviceSize(layout.upper_nodes().size() * sizeof(GpuBvhNode)),
    }};
    max_staging = std::max(
        max_staging,
        upload_regions(
            buffers.upper,
            upper_region,
            region_count,
            uploaded_logical_bytes));

    const std::array<CopyRegion, 1> micro_region{{
        reinterpret_cast<const std::byte*>(layout.micro_nodes().data()),
        0U,
        VkDeviceSize(layout.micro_nodes().size() * sizeof(GpuBvhNode)),
    }};
    max_staging = std::max(
        max_staging,
        upload_regions(
            buffers.micro,
            micro_region,
            region_count,
            uploaded_logical_bytes));

    const std::array<CopyRegion, 1> cluster_region{{
        reinterpret_cast<const std::byte*>(layout.clusters().data()),
        0U,
        VkDeviceSize(layout.clusters().size() * sizeof(GpuCluster)),
    }};
    max_staging = std::max(
        max_staging,
        upload_regions(
            buffers.clusters,
            cluster_region,
            region_count,
            uploaded_logical_bytes));

    return max_staging;
}

PersistentGpuSyncResult PersistentGpuState::synchronize(
    const PersistentClusterLayout& layout,
    const PersistentLayoutUpdate& update) {
    PersistentGpuSyncResult result{};
    result.resized = update.resized;

    const auto old_persistent = persistent_allocation_bytes();
    if (update.resized) {
        auto replacement = create_buffer_set(layout);
        const auto new_persistent = allocation_bytes(replacement);
        result.resize_old_new_overlap_allocation_bytes =
            old_persistent + new_persistent;
        try {
            result.max_staging_allocation_bytes =
                upload_full_layout(
                    replacement,
                    layout,
                    result.upload_region_count,
                    result.uploaded_logical_bytes);
        } catch (...) {
            destroy_buffer_set(replacement);
            throw;
        }

        BufferSet old{
            std::exchange(triangles_, replacement.triangles),
            std::exchange(upper_, replacement.upper),
            std::exchange(micro_, replacement.micro),
            std::exchange(clusters_, replacement.clusters),
        };
        destroy_buffer_set(old);
    } else {
        std::vector<CopyRegion> triangle_regions;
        std::vector<CopyRegion> micro_regions;
        std::vector<CopyRegion> cluster_regions;
        triangle_regions.reserve(update.dirty_physical_slots.size());
        micro_regions.reserve(update.dirty_physical_slots.size());
        cluster_regions.reserve(update.dirty_physical_slots.size());

        for (const auto slot : update.dirty_physical_slots) {
            const auto triangle_index =
                std::size_t(slot) * kTrianglesPerPhysicalSlot;
            triangle_regions.push_back({
                bytes_at(layout.triangles(), triangle_index),
                VkDeviceSize(triangle_index * sizeof(GpuTriangle)),
                VkDeviceSize(
                    kTrianglesPerPhysicalSlot * sizeof(GpuTriangle)),
            });

            const auto micro_index =
                std::size_t(slot) * kMicroNodesPerPhysicalSlot;
            micro_regions.push_back({
                bytes_at(layout.micro_nodes(), micro_index),
                VkDeviceSize(micro_index * sizeof(GpuBvhNode)),
                VkDeviceSize(
                    kMicroNodesPerPhysicalSlot * sizeof(GpuBvhNode)),
            });

            cluster_regions.push_back({
                bytes_at(layout.clusters(), slot),
                VkDeviceSize(std::size_t(slot) * sizeof(GpuCluster)),
                VkDeviceSize(sizeof(GpuCluster)),
            });
        }

        result.max_staging_allocation_bytes = std::max(
            result.max_staging_allocation_bytes,
            upload_regions(
                triangles_,
                triangle_regions,
                result.upload_region_count,
                result.uploaded_logical_bytes));
        result.max_staging_allocation_bytes = std::max(
            result.max_staging_allocation_bytes,
            upload_regions(
                micro_,
                micro_regions,
                result.upload_region_count,
                result.uploaded_logical_bytes));
        result.max_staging_allocation_bytes = std::max(
            result.max_staging_allocation_bytes,
            upload_regions(
                clusters_,
                cluster_regions,
                result.upload_region_count,
                result.uploaded_logical_bytes));

        std::vector<CopyRegion> upper_regions;
        if (update.upper_rebuilt) {
            upper_regions.push_back({
                reinterpret_cast<const std::byte*>(
                    layout.upper_nodes().data()),
                0U,
                VkDeviceSize(
                    layout.upper_node_count() * sizeof(GpuBvhNode)),
            });
        } else {
            upper_regions.reserve(update.dirty_upper_nodes.size());
            for (const auto node : update.dirty_upper_nodes) {
                upper_regions.push_back({
                    bytes_at(layout.upper_nodes(), node),
                    VkDeviceSize(std::size_t(node) * sizeof(GpuBvhNode)),
                    VkDeviceSize(sizeof(GpuBvhNode)),
                });
            }
        }
        result.max_staging_allocation_bytes = std::max(
            result.max_staging_allocation_bytes,
            upload_regions(
                upper_,
                upper_regions,
                result.upload_region_count,
                result.uploaded_logical_bytes));
    }

    result.candidate_persistent_allocation_bytes =
        persistent_allocation_bytes();
    const auto persistent_peak = update.resized
        ? result.resize_old_new_overlap_allocation_bytes
        : result.candidate_persistent_allocation_bytes;
    result.true_peak_resident_bytes =
        persistent_peak + result.max_staging_allocation_bytes;
    return result;
}


PersistentGpuTraversalResult PersistentGpuState::trace(
    const PersistentClusterLayout& layout,
    std::span<const GpuRay> rays,
    const std::filesystem::path& shader_path,
    PersistentGpuDebugRequest debug) {
    if (rays.empty()) {
        fail("J003 persistent traversal requires rays");
    }
    if (layout.upper_root() >= layout.upper_node_count()) {
        fail("J003 persistent traversal upper root out of range");
    }

    ValidationRuntime runtime{context_};
    constexpr auto storage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
    runtime.rays = context_.upload_device_buffer(
        rays.data(),
        VkDeviceSize(rays.size() * sizeof(GpuRay)),
        storage);
    runtime.hits = context_.create_device_buffer(
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
    if (context_.vk().createDescriptorSetLayout(
            &descriptor_layout_info,
            nullptr,
            &runtime.descriptor_layout) != VK_SUCCESS) {
        fail("J003 persistent traversal descriptor layout");
    }

    VkPushConstantRange push_range{};
    push_range.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    push_range.offset = 0U;
    push_range.size = sizeof(TraversalPush);

    auto pipeline_layout_info =
        detail::make_vk_info<VkPipelineLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
    pipeline_layout_info.setLayoutCount = 1U;
    pipeline_layout_info.pSetLayouts = &runtime.descriptor_layout;
    pipeline_layout_info.pushConstantRangeCount = 1U;
    pipeline_layout_info.pPushConstantRanges = &push_range;
    if (context_.vk().createPipelineLayout(
            &pipeline_layout_info,
            nullptr,
            &runtime.pipeline_layout) != VK_SUCCESS) {
        fail("J003 persistent traversal pipeline layout");
    }

    VkDescriptorPoolSize pool_size{
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
        6U,
    };
    auto pool_info = detail::make_vk_info<VkDescriptorPoolCreateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
    pool_info.maxSets = 1U;
    pool_info.poolSizeCount = 1U;
    pool_info.pPoolSizes = &pool_size;
    if (context_.vk().createDescriptorPool(
            &pool_info,
            nullptr,
            &runtime.descriptor_pool) != VK_SUCCESS) {
        fail("J003 persistent traversal descriptor pool");
    }

    VkDescriptorSet descriptor_set{VK_NULL_HANDLE};
    auto allocate_info =
        detail::make_vk_info<VkDescriptorSetAllocateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
    allocate_info.descriptorPool = runtime.descriptor_pool;
    allocate_info.descriptorSetCount = 1U;
    allocate_info.pSetLayouts = &runtime.descriptor_layout;
    if (context_.vk().allocateDescriptorSets(
            &allocate_info,
            &descriptor_set) != VK_SUCCESS) {
        fail("J003 persistent traversal descriptor set");
    }

    const std::array<GpuBuffer, 6> buffers{
        triangles_,
        upper_,
        micro_,
        clusters_,
        runtime.rays,
        runtime.hits,
    };
    std::array<VkDescriptorBufferInfo, 6> buffer_infos{};
    std::array<VkWriteDescriptorSet, 6> writes{};
    for (std::uint32_t index = 0U; index < buffers.size(); ++index) {
        buffer_infos[index] = {
            buffers[index].buffer,
            0U,
            buffers[index].size,
        };
        writes[index] = detail::make_vk_info<VkWriteDescriptorSet>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
        writes[index].dstSet = descriptor_set;
        writes[index].dstBinding = index;
        writes[index].descriptorCount = 1U;
        writes[index].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        writes[index].pBufferInfo = &buffer_infos[index];
    }
    context_.vk().updateDescriptorSets(
        static_cast<std::uint32_t>(writes.size()),
        writes.data(),
        0U,
        nullptr);

    const auto shader = read_binary_file(shader_path.string());
    if (shader.empty() ||
        shader.size() % sizeof(std::uint32_t) != 0U) {
        fail("J003 persistent traversal invalid shader");
    }

    auto module_info =
        detail::make_vk_info<VkShaderModuleCreateInfo>(
            VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    module_info.codeSize = shader.size();
    module_info.pCode =
        reinterpret_cast<const std::uint32_t*>(shader.data());
    VkShaderModule module{VK_NULL_HANDLE};
    if (context_.vk().createShaderModule(
            &module_info,
            nullptr,
            &module) != VK_SUCCESS) {
        fail("J003 persistent traversal shader module");
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
    pipeline_info.layout = runtime.pipeline_layout;
    const auto pipeline_result = context_.vk().createComputePipelines(
        VK_NULL_HANDLE,
        1U,
        &pipeline_info,
        nullptr,
        &runtime.pipeline);
    context_.vk().destroyShaderModule(module, nullptr);
    if (pipeline_result != VK_SUCCESS) {
        fail("J003 persistent traversal compute pipeline");
    }

    auto command_pool_info =
        detail::make_vk_info<VkCommandPoolCreateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
    command_pool_info.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
    command_pool_info.queueFamilyIndex = context_.queue_family();
    if (context_.vk().createCommandPool(
            &command_pool_info,
            nullptr,
            &runtime.command_pool) != VK_SUCCESS) {
        fail("J003 persistent traversal command pool");
    }

    VkCommandBuffer command{VK_NULL_HANDLE};
    auto command_allocate =
        detail::make_vk_info<VkCommandBufferAllocateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    command_allocate.commandPool = runtime.command_pool;
    command_allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    command_allocate.commandBufferCount = 1U;
    if (context_.vk().allocateCommandBuffers(
            &command_allocate,
            &command) != VK_SUCCESS) {
        fail("J003 persistent traversal command buffer");
    }

    auto query_info =
        detail::make_vk_info<VkQueryPoolCreateInfo>(
            VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
    query_info.queryType = VK_QUERY_TYPE_TIMESTAMP;
    query_info.queryCount = 2U;
    if (context_.vk().createQueryPool(
            &query_info,
            nullptr,
            &runtime.query_pool) != VK_SUCCESS) {
        fail("J003 persistent traversal query pool");
    }

    auto fence_info = detail::make_vk_info<VkFenceCreateInfo>(
        VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    if (context_.vk().createFence(
            &fence_info,
            nullptr,
            &runtime.fence) != VK_SUCCESS) {
        fail("J003 persistent traversal fence");
    }

    auto begin_info =
        detail::make_vk_info<VkCommandBufferBeginInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (context_.vk().beginCommandBuffer(
            command,
            &begin_info) != VK_SUCCESS) {
        fail("J003 persistent traversal begin");
    }

    context_.vk().cmdResetQueryPool(
        command,
        runtime.query_pool,
        0U,
        2U);
    context_.vk().cmdBindPipeline(
        command,
        VK_PIPELINE_BIND_POINT_COMPUTE,
        runtime.pipeline);
    context_.vk().cmdBindDescriptorSets(
        command,
        VK_PIPELINE_BIND_POINT_COMPUTE,
        runtime.pipeline_layout,
        0U,
        1U,
        &descriptor_set,
        0U,
        nullptr);

    const TraversalPush push{
        static_cast<std::uint32_t>(rays.size()),
        layout.upper_root(),
        layout.upper_node_count(),
        static_cast<std::uint32_t>(layout.micro_nodes().size()),
        layout.slot_capacity(),
        static_cast<std::uint32_t>(layout.triangles().size()),
        debug.ray_index,
        debug.primitive_id,
    };
    context_.vk().cmdPushConstants(
        command,
        runtime.pipeline_layout,
        VK_SHADER_STAGE_COMPUTE_BIT,
        0U,
        sizeof(push),
        &push);

    context_.vk().cmdWriteTimestamp(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        runtime.query_pool,
        0U);
    const auto groups =
        (static_cast<std::uint32_t>(rays.size()) + 63U) / 64U;
    context_.vk().cmdDispatch(command, groups, 1U, 1U);
    context_.vk().cmdWriteTimestamp(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        runtime.query_pool,
        1U);

    auto barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
    barrier.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
    context_.vk().cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        0U,
        1U,
        &barrier,
        0U,
        nullptr,
        0U,
        nullptr);

    if (context_.vk().endCommandBuffer(command) != VK_SUCCESS) {
        fail("J003 persistent traversal end");
    }

    auto submit = detail::make_vk_info<VkSubmitInfo>(
        VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit.commandBufferCount = 1U;
    submit.pCommandBuffers = &command;
    if (context_.vk().queueSubmit(
            context_.queue(),
            1U,
            &submit,
            runtime.fence) != VK_SUCCESS) {
        fail("J003 persistent traversal submit");
    }
    if (context_.vk().waitForFences(
            1U,
            &runtime.fence,
            VK_TRUE,
            UINT64_MAX) != VK_SUCCESS) {
        fail("J003 persistent traversal wait");
    }

    std::array<std::uint64_t, 2> timestamps{};
    if (context_.vk().getQueryPoolResults(
            runtime.query_pool,
            0U,
            2U,
            sizeof(timestamps),
            timestamps.data(),
            sizeof(std::uint64_t),
            VK_QUERY_RESULT_64_BIT |
                VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
        fail("J003 persistent traversal timestamps");
    }

    PersistentGpuTraversalResult result{};
    result.hits.resize(rays.size());
    context_.download_device_buffer(
        runtime.hits,
        result.hits.data(),
        VkDeviceSize(result.hits.size() * sizeof(GpuHit)));
    result.traversal_gpu_us =
        double(timestamps[1] - timestamps[0]) *
        double(context_.timestamp_period_ns()) /
        1000.0;
    result.validation_harness_allocation_bytes =
        allocation_bytes(runtime.rays) +
        allocation_bytes(runtime.hits);
    return result;
}

} // namespace phos::gi::research::lane_j

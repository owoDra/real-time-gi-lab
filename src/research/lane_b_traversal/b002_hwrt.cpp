#include "b002_hwrt.hpp"

#include "b002_compute.hpp"
#include "vk_init.hpp"

#include <algorithm>
#include <chrono>
#include <cstring>
#include <stdexcept>
#include <utility>
#include <vector>

namespace phos::gi::research::lane_b {
namespace {

using Clock = std::chrono::steady_clock;

struct Vertex3 {
    float x{};
    float y{};
    float z{};
};
static_assert(sizeof(Vertex3) == 12);

[[nodiscard]] double elapsed_us(Clock::time_point start) {
    return std::chrono::duration<double, std::micro>(
        Clock::now() - start).count();
}

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

} // namespace

B002HwrtTraversal::B002HwrtTraversal(
    B002VulkanContext& context,
    const std::vector<Triangle>& triangles,
    std::string shader_path)
    : context_(context) {
    if (!context_.hwrt_enabled()) {
        fail("B002 HWRT traversal requires an HWRT-enabled context");
    }
    if (triangles.empty()) {
        fail("B002 HWRT requires non-empty geometry");
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
        fail("B002 HWRT command pool");
    }

    auto query_info = detail::make_vk_info<VkQueryPoolCreateInfo>(
        VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
    query_info.queryType = VK_QUERY_TYPE_TIMESTAMP;
    query_info.queryCount = 512;
    if (context_.vk().createQueryPool(
            &query_info,
            nullptr,
            &query_pool_) != VK_SUCCESS) {
        fail("B002 HWRT query pool");
    }

    auto fence_info = detail::make_vk_info<VkFenceCreateInfo>(
        VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    if (context_.vk().createFence(
            &fence_info,
            nullptr,
            &fence_) != VK_SUCCESS) {
        fail("B002 HWRT fence");
    }

    std::vector<Vertex3> vertices;
    vertices.reserve(triangles.size() * 3U);
    std::vector<GpuTriangle> gpu_triangles;
    gpu_triangles.reserve(triangles.size());
    for (const auto& triangle : triangles) {
        vertices.push_back({
            triangle.v0.x,
            triangle.v0.y,
            triangle.v0.z});
        vertices.push_back({
            triangle.v1.x,
            triangle.v1.y,
            triangle.v1.z});
        vertices.push_back({
            triangle.v2.x,
            triangle.v2.y,
            triangle.v2.z});
        gpu_triangles.push_back(to_gpu_triangle(triangle));
    }

    auto start = Clock::now();
    vertex_buffer_ = context_.upload_device_address_buffer(
        vertices.data(),
        vertices.size() * sizeof(Vertex3),
        VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_BUILD_INPUT_READ_ONLY_BIT_KHR);
    setup_stats_.vertex_upload_us = elapsed_us(start);

    start = Clock::now();
    triangle_buffer_ = context_.upload_device_buffer(
        gpu_triangles.data(),
        gpu_triangles.size() * sizeof(GpuTriangle),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    setup_stats_.metadata_upload_us = elapsed_us(start);

    setup_stats_.blas_build_us = build_blas(triangles);
    setup_stats_.tlas_build_us = build_tlas();

    setup_stats_.persistent_bytes =
        static_cast<std::size_t>(
            vertex_buffer_.allocation_size +
            triangle_buffer_.allocation_size +
            instance_buffer_.allocation_size +
            blas_.storage.allocation_size +
            tlas_.storage.allocation_size);
    setup_stats_.scratch_bytes =
        static_cast<std::size_t>(std::max(
            blas_scratch_.allocation_size,
            tlas_scratch_.allocation_size));

    create_trace_pipeline(shader_path);
}

B002HwrtTraversal::~B002HwrtTraversal() {
    context_.vk().deviceWaitIdle();

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

    destroy_acceleration_structure(tlas_);
    destroy_acceleration_structure(blas_);
    context_.destroy_buffer(tlas_scratch_);
    context_.destroy_buffer(blas_scratch_);
    context_.destroy_buffer(instance_buffer_);
    context_.destroy_buffer(triangle_buffer_);
    context_.destroy_buffer(vertex_buffer_);

    if (fence_ != VK_NULL_HANDLE)
        context_.vk().destroyFence(fence_, nullptr);
    if (query_pool_ != VK_NULL_HANDLE)
        context_.vk().destroyQueryPool(query_pool_, nullptr);
    if (command_pool_ != VK_NULL_HANDLE)
        context_.vk().destroyCommandPool(command_pool_, nullptr);
}

void B002HwrtTraversal::destroy_acceleration_structure(
    AccelerationStructure& acceleration) {
    if (acceleration.handle != VK_NULL_HANDLE) {
        context_.vk().destroyAccelerationStructureKHR(
            acceleration.handle,
            nullptr);
    }
    context_.destroy_buffer(acceleration.storage);
    acceleration = {};
}

double B002HwrtTraversal::build_blas(
    const std::vector<Triangle>& triangles) {
    auto triangle_geometry =
        detail::make_vk_info<VkAccelerationStructureGeometryTrianglesDataKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_TRIANGLES_DATA_KHR);
    triangle_geometry.vertexFormat =
        VK_FORMAT_R32G32B32_SFLOAT;
    triangle_geometry.vertexData.deviceAddress =
        vertex_buffer_.address;
    triangle_geometry.vertexStride = sizeof(Vertex3);
    triangle_geometry.maxVertex =
        static_cast<std::uint32_t>(
            triangles.size() * 3U - 1U);
    triangle_geometry.indexType = VK_INDEX_TYPE_NONE_KHR;

    auto geometry =
        detail::make_vk_info<VkAccelerationStructureGeometryKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_KHR);
    geometry.geometryType = VK_GEOMETRY_TYPE_TRIANGLES_KHR;
    geometry.geometry.triangles = triangle_geometry;
    // Deliberately non-opaque: ray-query must expose every triangle candidate
    // so the shared deterministic tie/face policy can be applied in shader.
    geometry.flags = 0;

    auto build_info =
        detail::make_vk_info<VkAccelerationStructureBuildGeometryInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_GEOMETRY_INFO_KHR);
    build_info.type =
        VK_ACCELERATION_STRUCTURE_TYPE_BOTTOM_LEVEL_KHR;
    build_info.flags =
        VK_BUILD_ACCELERATION_STRUCTURE_PREFER_FAST_TRACE_BIT_KHR |
        VK_BUILD_ACCELERATION_STRUCTURE_ALLOW_UPDATE_BIT_KHR;
    build_info.mode =
        VK_BUILD_ACCELERATION_STRUCTURE_MODE_BUILD_KHR;
    build_info.geometryCount = 1;
    build_info.pGeometries = &geometry;

    const std::uint32_t primitive_count =
        static_cast<std::uint32_t>(triangles.size());
    auto size_info =
        detail::make_vk_info<VkAccelerationStructureBuildSizesInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_SIZES_INFO_KHR);
    context_.vk().getAccelerationStructureBuildSizesKHR(
        VK_ACCELERATION_STRUCTURE_BUILD_TYPE_DEVICE_KHR,
        &build_info,
        &primitive_count,
        &size_info);

    blas_.storage = context_.create_device_buffer(
        size_info.accelerationStructureSize,
        VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_STORAGE_BIT_KHR);
    auto create_info =
        detail::make_vk_info<VkAccelerationStructureCreateInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_CREATE_INFO_KHR);
    create_info.buffer = blas_.storage.buffer;
    create_info.size = size_info.accelerationStructureSize;
    create_info.type =
        VK_ACCELERATION_STRUCTURE_TYPE_BOTTOM_LEVEL_KHR;
    if (context_.vk().createAccelerationStructureKHR(
            &create_info,
            nullptr,
            &blas_.handle) != VK_SUCCESS) {
        fail("B002 HWRT BLAS creation failed");
    }

    const auto scratch_size = std::max(
        size_info.buildScratchSize,
        size_info.updateScratchSize);
    blas_scratch_ = context_.create_device_address_buffer(
        scratch_size,
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    build_info.dstAccelerationStructure = blas_.handle;
    build_info.scratchData.deviceAddress =
        blas_scratch_.address;

    VkAccelerationStructureBuildRangeInfoKHR range{};
    range.primitiveCount = primitive_count;
    const auto build_us =
        submit_build(build_info, range, false);

    auto address_info =
        detail::make_vk_info<VkAccelerationStructureDeviceAddressInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_DEVICE_ADDRESS_INFO_KHR);
    address_info.accelerationStructure = blas_.handle;
    blas_.address =
        context_.vk().getAccelerationStructureDeviceAddressKHR(
            &address_info);
    if (blas_.address == 0) {
        fail("B002 HWRT BLAS address is zero");
    }
    return build_us;
}

double B002HwrtTraversal::build_tlas() {
    VkAccelerationStructureInstanceKHR instance{};
    instance.transform.matrix[0][0] = 1.0F;
    instance.transform.matrix[1][1] = 1.0F;
    instance.transform.matrix[2][2] = 1.0F;
    instance.instanceCustomIndex = 0;
    instance.mask = 0xff;
    instance.instanceShaderBindingTableRecordOffset = 0;
    instance.flags =
        VK_GEOMETRY_INSTANCE_TRIANGLE_FACING_CULL_DISABLE_BIT_KHR;
    instance.accelerationStructureReference = blas_.address;

    instance_buffer_ = context_.upload_device_address_buffer(
        &instance,
        sizeof(instance),
        VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_BUILD_INPUT_READ_ONLY_BIT_KHR);

    auto instances =
        detail::make_vk_info<VkAccelerationStructureGeometryInstancesDataKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_INSTANCES_DATA_KHR);
    instances.arrayOfPointers = VK_FALSE;
    instances.data.deviceAddress = instance_buffer_.address;

    auto geometry =
        detail::make_vk_info<VkAccelerationStructureGeometryKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_KHR);
    geometry.geometryType = VK_GEOMETRY_TYPE_INSTANCES_KHR;
    geometry.geometry.instances = instances;

    auto build_info =
        detail::make_vk_info<VkAccelerationStructureBuildGeometryInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_GEOMETRY_INFO_KHR);
    build_info.type =
        VK_ACCELERATION_STRUCTURE_TYPE_TOP_LEVEL_KHR;
    build_info.flags =
        VK_BUILD_ACCELERATION_STRUCTURE_PREFER_FAST_TRACE_BIT_KHR |
        VK_BUILD_ACCELERATION_STRUCTURE_ALLOW_UPDATE_BIT_KHR;
    build_info.mode =
        VK_BUILD_ACCELERATION_STRUCTURE_MODE_BUILD_KHR;
    build_info.geometryCount = 1;
    build_info.pGeometries = &geometry;

    constexpr std::uint32_t primitive_count = 1;
    auto size_info =
        detail::make_vk_info<VkAccelerationStructureBuildSizesInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_SIZES_INFO_KHR);
    context_.vk().getAccelerationStructureBuildSizesKHR(
        VK_ACCELERATION_STRUCTURE_BUILD_TYPE_DEVICE_KHR,
        &build_info,
        &primitive_count,
        &size_info);

    tlas_.storage = context_.create_device_buffer(
        size_info.accelerationStructureSize,
        VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_STORAGE_BIT_KHR);
    auto create_info =
        detail::make_vk_info<VkAccelerationStructureCreateInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_CREATE_INFO_KHR);
    create_info.buffer = tlas_.storage.buffer;
    create_info.size = size_info.accelerationStructureSize;
    create_info.type =
        VK_ACCELERATION_STRUCTURE_TYPE_TOP_LEVEL_KHR;
    if (context_.vk().createAccelerationStructureKHR(
            &create_info,
            nullptr,
            &tlas_.handle) != VK_SUCCESS) {
        fail("B002 HWRT TLAS creation failed");
    }

    const auto scratch_size = std::max(
        size_info.buildScratchSize,
        size_info.updateScratchSize);
    tlas_scratch_ = context_.create_device_address_buffer(
        scratch_size,
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    build_info.dstAccelerationStructure = tlas_.handle;
    build_info.scratchData.deviceAddress =
        tlas_scratch_.address;

    VkAccelerationStructureBuildRangeInfoKHR range{};
    range.primitiveCount = primitive_count;
    return submit_build(build_info, range, true);
}

double B002HwrtTraversal::submit_build(
    VkAccelerationStructureBuildGeometryInfoKHR& build_info,
    const VkAccelerationStructureBuildRangeInfoKHR& range,
    bool depends_on_previous_build) {
    context_.vk().resetFences(1, &fence_);
    context_.vk().resetCommandPool(command_pool_, 0);

    VkCommandBuffer command{};
    auto allocate_info =
        detail::make_vk_info<VkCommandBufferAllocateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    allocate_info.commandPool = command_pool_;
    allocate_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocate_info.commandBufferCount = 1;
    if (context_.vk().allocateCommandBuffers(
            &allocate_info,
            &command) != VK_SUCCESS) {
        fail("B002 HWRT build command buffer");
    }

    auto begin_info =
        detail::make_vk_info<VkCommandBufferBeginInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (context_.vk().beginCommandBuffer(
            command,
            &begin_info) != VK_SUCCESS) {
        fail("B002 HWRT build begin");
    }

    context_.vk().cmdResetQueryPool(command, query_pool_, 0, 2);

    if (depends_on_previous_build) {
        auto barrier = detail::make_vk_info<VkMemoryBarrier>(
            VK_STRUCTURE_TYPE_MEMORY_BARRIER);
        barrier.srcAccessMask =
            VK_ACCESS_ACCELERATION_STRUCTURE_WRITE_BIT_KHR;
        barrier.dstAccessMask =
            VK_ACCESS_ACCELERATION_STRUCTURE_READ_BIT_KHR;
        context_.vk().cmdPipelineBarrier(
            command,
            VK_PIPELINE_STAGE_ACCELERATION_STRUCTURE_BUILD_BIT_KHR,
            VK_PIPELINE_STAGE_ACCELERATION_STRUCTURE_BUILD_BIT_KHR,
            0,
            1,
            &barrier,
            0,
            nullptr,
            0,
            nullptr);
    }

    context_.vk().cmdWriteTimestamp(
        command,
        VK_PIPELINE_STAGE_ACCELERATION_STRUCTURE_BUILD_BIT_KHR,
        query_pool_,
        0);
    const VkAccelerationStructureBuildRangeInfoKHR* ranges[]{&range};
    context_.vk().cmdBuildAccelerationStructuresKHR(
        command,
        1,
        &build_info,
        ranges);
    context_.vk().cmdWriteTimestamp(
        command,
        VK_PIPELINE_STAGE_ACCELERATION_STRUCTURE_BUILD_BIT_KHR,
        query_pool_,
        1);

    if (context_.vk().endCommandBuffer(command) != VK_SUCCESS) {
        fail("B002 HWRT build end");
    }

    auto submit_info =
        detail::make_vk_info<VkSubmitInfo>(
            VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit_info.commandBufferCount = 1;
    submit_info.pCommandBuffers = &command;
    if (context_.vk().queueSubmit(
            context_.queue(),
            1,
            &submit_info,
            fence_) != VK_SUCCESS) {
        fail("B002 HWRT build submit");
    }
    if (context_.vk().waitForFences(
            1,
            &fence_,
            VK_TRUE,
            UINT64_MAX) != VK_SUCCESS) {
        fail("B002 HWRT build wait");
    }

    std::uint64_t timestamps[2]{};
    if (context_.vk().getQueryPoolResults(
            query_pool_,
            0,
            2,
            sizeof(timestamps),
            timestamps,
            sizeof(std::uint64_t),
            VK_QUERY_RESULT_64_BIT |
                VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
        fail("B002 HWRT build timestamp readback");
    }
    return double(timestamps[1] - timestamps[0]) *
        double(context_.timestamp_period_ns()) /
        1000.0;
}

void B002HwrtTraversal::create_trace_pipeline(
    const std::string& shader_path) {
    VkDescriptorSetLayoutBinding ray_binding{};
    ray_binding.binding = 0;
    ray_binding.descriptorType =
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    ray_binding.descriptorCount = 1;
    ray_binding.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;

    VkDescriptorSetLayoutBinding acceleration_binding{};
    acceleration_binding.binding = 1;
    acceleration_binding.descriptorType =
        VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR;
    acceleration_binding.descriptorCount = 1;
    acceleration_binding.stageFlags =
        VK_SHADER_STAGE_COMPUTE_BIT;

    VkDescriptorSetLayoutBinding triangle_binding{};
    triangle_binding.binding = 2;
    triangle_binding.descriptorType =
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    triangle_binding.descriptorCount = 1;
    triangle_binding.stageFlags =
        VK_SHADER_STAGE_COMPUTE_BIT;

    VkDescriptorSetLayoutBinding hit_binding{};
    hit_binding.binding = 3;
    hit_binding.descriptorType =
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    hit_binding.descriptorCount = 1;
    hit_binding.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;

    const VkDescriptorSetLayoutBinding bindings[]{
        ray_binding,
        acceleration_binding,
        triangle_binding,
        hit_binding,
    };
    auto layout_info =
        detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
    layout_info.bindingCount = 4;
    layout_info.pBindings = bindings;
    if (context_.vk().createDescriptorSetLayout(
            &layout_info,
            nullptr,
            &descriptor_layout_) != VK_SUCCESS) {
        fail("B002 HWRT descriptor layout");
    }

    VkPushConstantRange push{};
    push.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    push.size = sizeof(std::uint32_t);
    auto pipeline_layout_info =
        detail::make_vk_info<VkPipelineLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
    pipeline_layout_info.setLayoutCount = 1;
    pipeline_layout_info.pSetLayouts = &descriptor_layout_;
    pipeline_layout_info.pushConstantRangeCount = 1;
    pipeline_layout_info.pPushConstantRanges = &push;
    if (context_.vk().createPipelineLayout(
            &pipeline_layout_info,
            nullptr,
            &pipeline_layout_) != VK_SUCCESS) {
        fail("B002 HWRT pipeline layout");
    }

    VkDescriptorPoolSize pool_sizes[2]{
        {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 3},
        {VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR, 1},
    };
    auto pool_info =
        detail::make_vk_info<VkDescriptorPoolCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
    pool_info.maxSets = 1;
    pool_info.poolSizeCount = 2;
    pool_info.pPoolSizes = pool_sizes;
    if (context_.vk().createDescriptorPool(
            &pool_info,
            nullptr,
            &descriptor_pool_) != VK_SUCCESS) {
        fail("B002 HWRT descriptor pool");
    }

    auto allocate_info =
        detail::make_vk_info<VkDescriptorSetAllocateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
    allocate_info.descriptorPool = descriptor_pool_;
    allocate_info.descriptorSetCount = 1;
    allocate_info.pSetLayouts = &descriptor_layout_;
    if (context_.vk().allocateDescriptorSets(
            &allocate_info,
            &descriptor_set_) != VK_SUCCESS) {
        fail("B002 HWRT descriptor set");
    }

    auto as_info =
        detail::make_vk_info<VkWriteDescriptorSetAccelerationStructureKHR>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET_ACCELERATION_STRUCTURE_KHR);
    as_info.accelerationStructureCount = 1;
    as_info.pAccelerationStructures = &tlas_.handle;

    auto acceleration_write =
        detail::make_vk_info<VkWriteDescriptorSet>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
    acceleration_write.pNext = &as_info;
    acceleration_write.dstSet = descriptor_set_;
    acceleration_write.dstBinding = 1;
    acceleration_write.descriptorCount = 1;
    acceleration_write.descriptorType =
        VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR;

    VkDescriptorBufferInfo triangle_info{
        triangle_buffer_.buffer,
        0,
        triangle_buffer_.size,
    };
    auto triangle_write =
        detail::make_vk_info<VkWriteDescriptorSet>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
    triangle_write.dstSet = descriptor_set_;
    triangle_write.dstBinding = 2;
    triangle_write.descriptorCount = 1;
    triangle_write.descriptorType =
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    triangle_write.pBufferInfo = &triangle_info;

    const VkWriteDescriptorSet static_writes[]{
        acceleration_write,
        triangle_write,
    };
    context_.vk().updateDescriptorSets(
        2,
        static_writes,
        0,
        nullptr);

    const auto code = read_b002_binary(shader_path);
    auto module_info =
        detail::make_vk_info<VkShaderModuleCreateInfo>(
            VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    module_info.codeSize = code.size();
    module_info.pCode =
        reinterpret_cast<const std::uint32_t*>(code.data());
    VkShaderModule module{};
    if (context_.vk().createShaderModule(
            &module_info,
            nullptr,
            &module) != VK_SUCCESS) {
        fail("B002 HWRT shader module");
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
        VK_NULL_HANDLE,
        1,
        &pipeline_info,
        nullptr,
        &pipeline_);
    context_.vk().destroyShaderModule(module, nullptr);
    if (result != VK_SUCCESS) {
        fail("B002 HWRT compute pipeline");
    }
}

HwrtTraceResult B002HwrtTraversal::trace(
    std::span<const GpuRay> rays,
    std::uint32_t iterations) {
    if (rays.empty()) fail("B002 HWRT cannot trace zero rays");

    const auto ray_bytes =
        VkDeviceSize(rays.size() * sizeof(GpuRay));
    const auto hit_bytes =
        VkDeviceSize(rays.size() * sizeof(GpuHit));

    const auto start = Clock::now();
    auto ray_buffer = context_.upload_device_buffer(
        rays.data(),
        ray_bytes,
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    const auto ray_upload_us = elapsed_us(start);
    auto hit_buffer = context_.create_device_buffer(
        hit_bytes,
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

    VkDescriptorBufferInfo ray_info{
        ray_buffer.buffer,
        0,
        ray_buffer.size};
    VkDescriptorBufferInfo hit_info{
        hit_buffer.buffer,
        0,
        hit_buffer.size};
    auto ray_write =
        detail::make_vk_info<VkWriteDescriptorSet>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
    ray_write.dstSet = descriptor_set_;
    ray_write.dstBinding = 0;
    ray_write.descriptorCount = 1;
    ray_write.descriptorType =
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    ray_write.pBufferInfo = &ray_info;

    auto hit_write =
        detail::make_vk_info<VkWriteDescriptorSet>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
    hit_write.dstSet = descriptor_set_;
    hit_write.dstBinding = 3;
    hit_write.descriptorCount = 1;
    hit_write.descriptorType =
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    hit_write.pBufferInfo = &hit_info;

    const VkWriteDescriptorSet writes[]{ray_write, hit_write};
    context_.vk().updateDescriptorSets(
        2,
        writes,
        0,
        nullptr);

    const auto trace_us = measure_trace(
        static_cast<std::uint32_t>(rays.size()),
        iterations);

    std::vector<GpuHit> hits(rays.size());
    context_.download_device_buffer(
        hit_buffer,
        hits.data(),
        hit_bytes);

    HwrtTraceResult result{
        ray_upload_us,
        trace_us,
        static_cast<std::size_t>(ray_buffer.allocation_size),
        std::move(hits),
    };
    context_.destroy_buffer(hit_buffer);
    context_.destroy_buffer(ray_buffer);
    return result;
}

double B002HwrtTraversal::measure_trace(
    std::uint32_t ray_count,
    std::uint32_t iterations) {
    if (iterations == 0 || iterations > 255) {
        fail("B002 HWRT invalid iteration count");
    }

    context_.vk().resetFences(1, &fence_);
    context_.vk().resetCommandPool(command_pool_, 0);

    VkCommandBuffer command{};
    auto allocate_info =
        detail::make_vk_info<VkCommandBufferAllocateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    allocate_info.commandPool = command_pool_;
    allocate_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocate_info.commandBufferCount = 1;
    if (context_.vk().allocateCommandBuffers(
            &allocate_info,
            &command) != VK_SUCCESS) {
        fail("B002 HWRT trace command buffer");
    }

    auto begin_info =
        detail::make_vk_info<VkCommandBufferBeginInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (context_.vk().beginCommandBuffer(
            command,
            &begin_info) != VK_SUCCESS) {
        fail("B002 HWRT trace begin");
    }

    context_.vk().cmdResetQueryPool(
        command,
        query_pool_,
        0,
        iterations * 2U);

    const auto dispatch = [&] {
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
            sizeof(ray_count),
            &ray_count);
        context_.vk().cmdDispatch(
            command,
            (ray_count + 63U) / 64U,
            1,
            1);
    };

    dispatch();
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

    for (std::uint32_t iteration = 0;
         iteration < iterations;
         ++iteration) {
        context_.vk().cmdWriteTimestamp(
            command,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool_,
            iteration * 2U);
        dispatch();
        context_.vk().cmdWriteTimestamp(
            command,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool_,
            iteration * 2U + 1U);
        if (iteration + 1U < iterations) {
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
        fail("B002 HWRT trace end");
    }
    auto submit_info =
        detail::make_vk_info<VkSubmitInfo>(
            VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit_info.commandBufferCount = 1;
    submit_info.pCommandBuffers = &command;
    if (context_.vk().queueSubmit(
            context_.queue(),
            1,
            &submit_info,
            fence_) != VK_SUCCESS) {
        fail("B002 HWRT trace submit");
    }
    if (context_.vk().waitForFences(
            1,
            &fence_,
            VK_TRUE,
            UINT64_MAX) != VK_SUCCESS) {
        fail("B002 HWRT trace wait");
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
        fail("B002 HWRT trace timestamp readback");
    }

    std::vector<double> samples;
    samples.reserve(iterations);
    for (std::uint32_t iteration = 0;
         iteration < iterations;
         ++iteration) {
        samples.push_back(
            double(
                timestamps[iteration * 2U + 1U] -
                timestamps[iteration * 2U]) *
            double(context_.timestamp_period_ns()) /
            1000.0);
    }
    return median_us(std::move(samples));
}

} // namespace phos::gi::research::lane_b

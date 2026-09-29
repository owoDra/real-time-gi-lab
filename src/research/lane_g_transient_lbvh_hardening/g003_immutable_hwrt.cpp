#include "g003_immutable_hwrt.hpp"

#include "vk_init.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::lane_g {
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

[[nodiscard]] VkDeviceAddress align_device_address(
    VkDeviceAddress address,
    VkDeviceSize alignment) noexcept {
    const auto mask = static_cast<VkDeviceAddress>(alignment - 1U);
    return (address + mask) & ~mask;
}

} // namespace

G003ImmutableHwrtTraversal::G003ImmutableHwrtTraversal(
    lane_b::B002VulkanContext& context,
    const std::vector<lane_b::Triangle>& triangles)
    : context_(context) {
    if (!context_.hwrt_enabled()) {
        fail("G003 immutable HWRT requires an HWRT-enabled context");
    }
    if (triangles.empty()) {
        fail("G003 immutable HWRT requires non-empty geometry");
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
        fail("G003 immutable HWRT command pool");
    }

    auto query_info =
        detail::make_vk_info<VkQueryPoolCreateInfo>(
            VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
    query_info.queryType = VK_QUERY_TYPE_TIMESTAMP;
    query_info.queryCount = 2;
    if (context_.vk().createQueryPool(
            &query_info,
            nullptr,
            &query_pool_) != VK_SUCCESS) {
        fail("G003 immutable HWRT query pool");
    }

    auto fence_info =
        detail::make_vk_info<VkFenceCreateInfo>(
            VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    if (context_.vk().createFence(
            &fence_info,
            nullptr,
            &fence_) != VK_SUCCESS) {
        fail("G003 immutable HWRT fence");
    }

    std::vector<Vertex3> vertices;
    vertices.reserve(triangles.size() * 3U);
    std::vector<lane_b::GpuTriangle> gpu_triangles;
    gpu_triangles.reserve(triangles.size());
    for (const auto& triangle : triangles) {
        vertices.push_back({triangle.v0.x, triangle.v0.y, triangle.v0.z});
        vertices.push_back({triangle.v1.x, triangle.v1.y, triangle.v1.z});
        vertices.push_back({triangle.v2.x, triangle.v2.y, triangle.v2.z});
        gpu_triangles.push_back(lane_b::to_gpu_triangle(triangle));
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
        gpu_triangles.size() * sizeof(lane_b::GpuTriangle),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    setup_stats_.metadata_upload_us = elapsed_us(start);

    setup_stats_.blas_build_us = build_blas(triangles);
    setup_stats_.tlas_build_us = build_tlas();

    setup_stats_.released_build_only_bytes =
        static_cast<std::size_t>(
            vertex_buffer_.allocation_size +
            instance_buffer_.allocation_size +
            scratch_.allocation_size);

    // submit_build() waits its fence. After both AS builds complete, traversal
    // references only BLAS/TLAS storage and triangle metadata.
    context_.destroy_buffer(scratch_);
    context_.destroy_buffer(instance_buffer_);
    context_.destroy_buffer(vertex_buffer_);

    setup_stats_.persistent_bytes =
        static_cast<std::size_t>(
            triangle_buffer_.allocation_size +
            blas_.storage.allocation_size +
            tlas_.storage.allocation_size);
    setup_stats_.scratch_bytes = 0U;
}

G003ImmutableHwrtTraversal::~G003ImmutableHwrtTraversal() {
    context_.vk().deviceWaitIdle();

    destroy_acceleration_structure(tlas_);
    destroy_acceleration_structure(blas_);
    context_.destroy_buffer(scratch_);
    context_.destroy_buffer(instance_buffer_);
    context_.destroy_buffer(triangle_buffer_);
    context_.destroy_buffer(vertex_buffer_);

    if (fence_ != VK_NULL_HANDLE) {
        context_.vk().destroyFence(fence_, nullptr);
    }
    if (query_pool_ != VK_NULL_HANDLE) {
        context_.vk().destroyQueryPool(query_pool_, nullptr);
    }
    if (command_pool_ != VK_NULL_HANDLE) {
        context_.vk().destroyCommandPool(command_pool_, nullptr);
    }
}

std::vector<lane_b::HwrtAllocationRecord>
G003ImmutableHwrtTraversal::allocation_census() const {
    std::vector<lane_b::HwrtAllocationRecord> rows;
    rows.reserve(3U);
    const auto add = [&](const char* name,
                         const lane_b::B002Buffer& buffer,
                         bool scratch) {
        if (buffer.buffer == VK_NULL_HANDLE) return;
        rows.push_back({
            name,
            static_cast<std::size_t>(buffer.size),
            static_cast<std::size_t>(buffer.allocation_size),
            scratch,
        });
    };
    add("static-hwrt.triangle-metadata", triangle_buffer_, false);
    add("static-hwrt.blas-storage", blas_.storage, false);
    add("static-hwrt.tlas-storage", tlas_.storage, false);
    return rows;
}

void G003ImmutableHwrtTraversal::destroy_acceleration_structure(
    AccelerationStructure& acceleration) {
    if (acceleration.handle != VK_NULL_HANDLE) {
        context_.vk().destroyAccelerationStructureKHR(
            acceleration.handle,
            nullptr);
    }
    context_.destroy_buffer(acceleration.storage);
    acceleration = {};
}

double G003ImmutableHwrtTraversal::build_blas(
    const std::vector<lane_b::Triangle>& triangles) {
    auto triangle_geometry =
        detail::make_vk_info<VkAccelerationStructureGeometryTrianglesDataKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_TRIANGLES_DATA_KHR);
    triangle_geometry.vertexFormat = VK_FORMAT_R32G32B32_SFLOAT;
    triangle_geometry.vertexData.deviceAddress = vertex_buffer_.address;
    triangle_geometry.vertexStride = sizeof(Vertex3);
    triangle_geometry.maxVertex =
        static_cast<std::uint32_t>(triangles.size() * 3U - 1U);
    triangle_geometry.indexType = VK_INDEX_TYPE_NONE_KHR;

    auto geometry =
        detail::make_vk_info<VkAccelerationStructureGeometryKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_KHR);
    geometry.geometryType = VK_GEOMETRY_TYPE_TRIANGLES_KHR;
    geometry.geometry.triangles = triangle_geometry;
    geometry.flags = 0;

    auto build_info =
        detail::make_vk_info<VkAccelerationStructureBuildGeometryInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_GEOMETRY_INFO_KHR);
    build_info.type = VK_ACCELERATION_STRUCTURE_TYPE_BOTTOM_LEVEL_KHR;
    build_info.flags =
        VK_BUILD_ACCELERATION_STRUCTURE_PREFER_FAST_TRACE_BIT_KHR |
        VK_BUILD_ACCELERATION_STRUCTURE_ALLOW_UPDATE_BIT_KHR;
    build_info.mode = VK_BUILD_ACCELERATION_STRUCTURE_MODE_BUILD_KHR;
    build_info.geometryCount = 1;
    build_info.pGeometries = &geometry;

    const auto primitive_count =
        static_cast<std::uint32_t>(triangles.size());
    auto size_info =
        detail::make_vk_info<VkAccelerationStructureBuildSizesInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_SIZES_INFO_KHR);
    context_.vk().getAccelerationStructureBuildSizesKHR(
        VK_ACCELERATION_STRUCTURE_BUILD_TYPE_DEVICE_KHR,
        &build_info,
        &primitive_count,
        &size_info);

    blas_.storage = context_.create_device_address_buffer(
        size_info.accelerationStructureSize,
        VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_STORAGE_BIT_KHR);

    auto create_info =
        detail::make_vk_info<VkAccelerationStructureCreateInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_CREATE_INFO_KHR);
    create_info.buffer = blas_.storage.buffer;
    create_info.size = size_info.accelerationStructureSize;
    create_info.type = VK_ACCELERATION_STRUCTURE_TYPE_BOTTOM_LEVEL_KHR;
    if (context_.vk().createAccelerationStructureKHR(
            &create_info,
            nullptr,
            &blas_.handle) != VK_SUCCESS) {
        fail("G003 immutable HWRT BLAS creation");
    }

    ensure_scratch_capacity(std::max(
        size_info.buildScratchSize,
        size_info.updateScratchSize));
    build_info.dstAccelerationStructure = blas_.handle;
    build_info.scratchData.deviceAddress = scratch_address();

    VkAccelerationStructureBuildRangeInfoKHR range{};
    range.primitiveCount = primitive_count;
    const auto build_us = submit_build(build_info, range, false);

    auto address_info =
        detail::make_vk_info<VkAccelerationStructureDeviceAddressInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_DEVICE_ADDRESS_INFO_KHR);
    address_info.accelerationStructure = blas_.handle;
    blas_.address =
        context_.vk().getAccelerationStructureDeviceAddressKHR(&address_info);
    if (blas_.address == 0U) {
        fail("G003 immutable HWRT BLAS address is zero");
    }
    return build_us;
}

double G003ImmutableHwrtTraversal::build_tlas() {
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
    build_info.type = VK_ACCELERATION_STRUCTURE_TYPE_TOP_LEVEL_KHR;
    build_info.flags =
        VK_BUILD_ACCELERATION_STRUCTURE_PREFER_FAST_TRACE_BIT_KHR |
        VK_BUILD_ACCELERATION_STRUCTURE_ALLOW_UPDATE_BIT_KHR;
    build_info.mode = VK_BUILD_ACCELERATION_STRUCTURE_MODE_BUILD_KHR;
    build_info.geometryCount = 1;
    build_info.pGeometries = &geometry;

    constexpr std::uint32_t primitive_count = 1U;
    auto size_info =
        detail::make_vk_info<VkAccelerationStructureBuildSizesInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_SIZES_INFO_KHR);
    context_.vk().getAccelerationStructureBuildSizesKHR(
        VK_ACCELERATION_STRUCTURE_BUILD_TYPE_DEVICE_KHR,
        &build_info,
        &primitive_count,
        &size_info);

    tlas_.storage = context_.create_device_address_buffer(
        size_info.accelerationStructureSize,
        VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_STORAGE_BIT_KHR);

    auto create_info =
        detail::make_vk_info<VkAccelerationStructureCreateInfoKHR>(
            VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_CREATE_INFO_KHR);
    create_info.buffer = tlas_.storage.buffer;
    create_info.size = size_info.accelerationStructureSize;
    create_info.type = VK_ACCELERATION_STRUCTURE_TYPE_TOP_LEVEL_KHR;
    if (context_.vk().createAccelerationStructureKHR(
            &create_info,
            nullptr,
            &tlas_.handle) != VK_SUCCESS) {
        fail("G003 immutable HWRT TLAS creation");
    }

    ensure_scratch_capacity(std::max(
        size_info.buildScratchSize,
        size_info.updateScratchSize));
    build_info.dstAccelerationStructure = tlas_.handle;
    build_info.scratchData.deviceAddress = scratch_address();

    VkAccelerationStructureBuildRangeInfoKHR range{};
    range.primitiveCount = primitive_count;
    return submit_build(build_info, range, true);
}

void G003ImmutableHwrtTraversal::ensure_scratch_capacity(
    VkDeviceSize required_bytes) {
    const auto alignment = context_.acceleration_scratch_alignment();
    const auto requested = required_bytes + alignment - 1U;
    if (scratch_.buffer != VK_NULL_HANDLE &&
        scratch_.size >= requested) {
        return;
    }

    context_.destroy_buffer(scratch_);
    scratch_ = context_.create_device_address_buffer(
        requested,
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
}

VkDeviceAddress
G003ImmutableHwrtTraversal::scratch_address() const noexcept {
    return align_device_address(
        scratch_.address,
        context_.acceleration_scratch_alignment());
}

double G003ImmutableHwrtTraversal::submit_build(
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
        fail("G003 immutable HWRT build command buffer");
    }

    auto begin_info =
        detail::make_vk_info<VkCommandBufferBeginInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (context_.vk().beginCommandBuffer(
            command,
            &begin_info) != VK_SUCCESS) {
        fail("G003 immutable HWRT build begin");
    }

    context_.vk().cmdResetQueryPool(command, query_pool_, 0, 2);

    if (depends_on_previous_build) {
        auto barrier =
            detail::make_vk_info<VkMemoryBarrier>(
                VK_STRUCTURE_TYPE_MEMORY_BARRIER);
        barrier.srcAccessMask =
            VK_ACCESS_ACCELERATION_STRUCTURE_WRITE_BIT_KHR;
        barrier.dstAccessMask =
            VK_ACCESS_ACCELERATION_STRUCTURE_READ_BIT_KHR |
            VK_ACCESS_ACCELERATION_STRUCTURE_WRITE_BIT_KHR;
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
        fail("G003 immutable HWRT build end");
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
        fail("G003 immutable HWRT build submit");
    }
    if (context_.vk().waitForFences(
            1,
            &fence_,
            VK_TRUE,
            UINT64_MAX) != VK_SUCCESS) {
        fail("G003 immutable HWRT build wait");
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
        fail("G003 immutable HWRT timestamp readback");
    }
    return double(timestamps[1] - timestamps[0]) *
        double(context_.timestamp_period_ns()) /
        1000.0;
}

} // namespace phos::gi::research::lane_g

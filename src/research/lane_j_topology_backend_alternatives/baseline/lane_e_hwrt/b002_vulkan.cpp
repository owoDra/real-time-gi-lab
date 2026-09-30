#include "b002_vulkan.hpp"

#include "vk_init.hpp"

#include <algorithm>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <utility>

namespace phos::gi::research::lane_b {
namespace {

[[noreturn]] void fail(const std::string& message) {
    throw std::runtime_error(message);
}

} // namespace

B002VulkanContext::B002VulkanContext(
    bool validation,
    std::string target_device,
    bool require_hwrt) {
    vkb::InstanceBuilder instance_builder;
    instance_builder
        .set_app_name("phos-lane-b-b002")
        .set_engine_name("research")
        .set_headless()
        .require_api_version(1, 3);
    if (validation) {
        instance_builder
            .request_validation_layers()
            .use_default_debug_messenger();
    }

    auto instance_result = instance_builder.build();
    if (!instance_result) {
        fail("B002 Vulkan instance: " + instance_result.error().message());
    }
    instance_ = instance_result.value();
    instance_dispatch_ = instance_.make_table();

    vkb::PhysicalDeviceSelector selector(instance_);
    selector
        .set_minimum_version(1, 3)
        .require_present(false)
        .set_name(target_device);

    VkPhysicalDeviceVulkan12Features vulkan12_features{};
    VkPhysicalDeviceAccelerationStructureFeaturesKHR acceleration_features{};
    VkPhysicalDeviceRayQueryFeaturesKHR ray_query_features{};
    if (require_hwrt) {
        vulkan12_features.sType =
            VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES;
        vulkan12_features.bufferDeviceAddress = VK_TRUE;
        acceleration_features.sType =
            VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ACCELERATION_STRUCTURE_FEATURES_KHR;
        acceleration_features.accelerationStructure = VK_TRUE;
        ray_query_features.sType =
            VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_RAY_QUERY_FEATURES_KHR;
        ray_query_features.rayQuery = VK_TRUE;

        selector
            .add_required_extension(
                VK_KHR_ACCELERATION_STRUCTURE_EXTENSION_NAME)
            .add_required_extension(
                VK_KHR_RAY_QUERY_EXTENSION_NAME)
            .add_required_extension(
                VK_KHR_DEFERRED_HOST_OPERATIONS_EXTENSION_NAME)
            .set_required_features_12(vulkan12_features)
            .add_required_extension_features(acceleration_features)
            .add_required_extension_features(ray_query_features);
    }

    auto physical_result = selector.select();
    if (!physical_result) {
        fail(
            "B002 target physical device selection failed: " +
            physical_result.error().message());
    }
    auto physical = physical_result.value();
    if (physical.name != target_device) {
        fail(
            "B002 refused fallback physical device '" + physical.name +
            "'; expected exact target '" + target_device + "'");
    }

    vkb::DeviceBuilder device_builder(physical);
    auto device_result = device_builder.build();
    if (!device_result) {
        fail("B002 logical device: " + device_result.error().message());
    }
    device_ = device_result.value();
    dispatch_ = device_.make_table();

    auto queue_result = device_.get_queue(vkb::QueueType::compute);
    auto family_result = device_.get_queue_index(vkb::QueueType::compute);
    if (!queue_result || !family_result) {
        fail("B002 target device has no compute-capable queue");
    }
    queue_ = queue_result.value();
    queue_family_ = family_result.value();

    VkPhysicalDeviceAccelerationStructurePropertiesKHR acceleration_properties{};
    if (require_hwrt) {
        acceleration_properties.sType =
            VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ACCELERATION_STRUCTURE_PROPERTIES_KHR;
    }

    VkPhysicalDeviceDriverProperties driver{};
    driver.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES;
    if (require_hwrt) {
        driver.pNext = &acceleration_properties;
    }

    VkPhysicalDeviceProperties2 properties{};
    properties.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2;
    properties.pNext = &driver;
    instance_dispatch_.getPhysicalDeviceProperties2(
        device_.physical_device.physical_device,
        &properties);

    device_name_ = properties.properties.deviceName;
    driver_name_ = driver.driverName;
    driver_info_ = driver.driverInfo;
    api_version_ = properties.properties.apiVersion;
    timestamp_period_ns_ = properties.properties.limits.timestampPeriod;
    hwrt_enabled_ = require_hwrt;
    if (require_hwrt) {
        acceleration_scratch_alignment_ =
            acceleration_properties.minAccelerationStructureScratchOffsetAlignment;
        if (acceleration_scratch_alignment_ == 0 ||
            (acceleration_scratch_alignment_ &
             (acceleration_scratch_alignment_ - 1U)) != 0U) {
            fail("B002 target reports invalid acceleration-structure scratch alignment");
        }
    }

    if (device_name_ != target_device) {
        fail(
            "B002 created unexpected physical device '" + device_name_ +
            "' after exact selection");
    }

    const auto& queue = device_.queue_families.at(queue_family_);
    if (queue.timestampValidBits == 0) {
        fail("B002 selected compute queue does not support timestamps");
    }
}

B002VulkanContext::~B002VulkanContext() {
    if (device_.device != VK_NULL_HANDLE) {
        dispatch_.deviceWaitIdle();
        vkb::destroy_device(device_);
    }
    if (instance_.instance != VK_NULL_HANDLE) {
        vkb::destroy_instance(instance_);
    }
}

std::uint32_t B002VulkanContext::find_memory_type(
    std::uint32_t bits,
    VkMemoryPropertyFlags required) const {
    VkPhysicalDeviceMemoryProperties properties{};
    instance_dispatch_.getPhysicalDeviceMemoryProperties(
        device_.physical_device.physical_device,
        &properties);
    for (std::uint32_t index = 0; index < properties.memoryTypeCount; ++index) {
        if ((bits & (1U << index)) != 0U &&
            (properties.memoryTypes[index].propertyFlags & required) == required) {
            return index;
        }
    }
    fail("B002 could not find a compatible Vulkan memory type");
}

B002Buffer B002VulkanContext::create_buffer(
    VkDeviceSize size,
    VkBufferUsageFlags usage,
    VkMemoryPropertyFlags properties,
    bool map,
    bool device_address) {
    if (size == 0) fail("B002 cannot allocate a zero-byte buffer");

    B002Buffer output{};
    output.size = size;

    auto buffer_info = detail::make_vk_info<VkBufferCreateInfo>(
        VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO);
    buffer_info.size = size;
    buffer_info.usage = usage;
    buffer_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    if (dispatch_.createBuffer(
            &buffer_info,
            nullptr,
            &output.buffer) != VK_SUCCESS) {
        fail("B002 vkCreateBuffer failed");
    }

    VkMemoryRequirements requirements{};
    dispatch_.getBufferMemoryRequirements(
        output.buffer,
        &requirements);
    output.allocation_size = requirements.size;

    auto allocation_info = detail::make_vk_info<VkMemoryAllocateInfo>(
        VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO);
    VkMemoryAllocateFlagsInfo allocation_flags{};
    if (device_address) {
        if (!hwrt_enabled_) {
            destroy_buffer(output);
            fail("B002 device-address buffer requires HWRT-enabled context");
        }
        allocation_flags.sType =
            VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_FLAGS_INFO;
        allocation_flags.flags =
            VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT;
        allocation_info.pNext = &allocation_flags;
    }
    allocation_info.allocationSize = requirements.size;
    allocation_info.memoryTypeIndex =
        find_memory_type(requirements.memoryTypeBits, properties);
    if (dispatch_.allocateMemory(
            &allocation_info,
            nullptr,
            &output.memory) != VK_SUCCESS) {
        dispatch_.destroyBuffer(output.buffer, nullptr);
        output.buffer = VK_NULL_HANDLE;
        fail("B002 vkAllocateMemory failed");
    }
    if (dispatch_.bindBufferMemory(
            output.buffer,
            output.memory,
            0) != VK_SUCCESS) {
        destroy_buffer(output);
        fail("B002 vkBindBufferMemory failed");
    }

    live_allocation_bytes_ += static_cast<std::size_t>(output.allocation_size);
    peak_allocation_bytes_ = std::max(
        peak_allocation_bytes_,
        live_allocation_bytes_);

    if (map &&
        dispatch_.mapMemory(
            output.memory,
            0,
            size,
            0,
            &output.mapped) != VK_SUCCESS) {
        destroy_buffer(output);
        fail("B002 vkMapMemory failed");
    }
    if (device_address) {
        auto address_info = detail::make_vk_info<VkBufferDeviceAddressInfo>(
            VK_STRUCTURE_TYPE_BUFFER_DEVICE_ADDRESS_INFO);
        address_info.buffer = output.buffer;
        output.address = dispatch_.getBufferDeviceAddress(&address_info);
        if (output.address == 0) {
            destroy_buffer(output);
            fail("B002 vkGetBufferDeviceAddress returned zero");
        }
    }
    return output;
}

B002Buffer B002VulkanContext::create_host_buffer(
    VkDeviceSize size,
    VkBufferUsageFlags usage) {
    return create_buffer(
        size,
        usage,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
            VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
        true,
        false);
}

B002Buffer B002VulkanContext::create_device_buffer(
    VkDeviceSize size,
    VkBufferUsageFlags usage) {
    return create_buffer(
        size,
        usage |
            VK_BUFFER_USAGE_TRANSFER_SRC_BIT |
            VK_BUFFER_USAGE_TRANSFER_DST_BIT,
        VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
        false,
        false);
}

B002Buffer B002VulkanContext::create_device_address_buffer(
    VkDeviceSize size,
    VkBufferUsageFlags usage) {
    return create_buffer(
        size,
        usage |
            VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT |
            VK_BUFFER_USAGE_TRANSFER_SRC_BIT |
            VK_BUFFER_USAGE_TRANSFER_DST_BIT,
        VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
        false,
        true);
}

void B002VulkanContext::copy_buffer(
    VkBuffer source,
    VkBuffer destination,
    VkDeviceSize size) {
    const VkBufferCopy region{0, 0, size};
    copy_buffer_regions(
        source,
        destination,
        std::span<const VkBufferCopy>(&region, 1));
}

void B002VulkanContext::copy_buffer_regions(
    VkBuffer source,
    VkBuffer destination,
    std::span<const VkBufferCopy> regions) {
    (void)copy_buffer_regions_timed(
        source,
        destination,
        regions);
}

double B002VulkanContext::copy_buffer_regions_timed(
    VkBuffer source,
    VkBuffer destination,
    std::span<const VkBufferCopy> regions) {
    if (regions.empty()) return 0.0;

    VkCommandPool pool{};
    auto pool_info = detail::make_vk_info<VkCommandPoolCreateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
    pool_info.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
    pool_info.queueFamilyIndex = queue_family_;
    if (dispatch_.createCommandPool(
            &pool_info,
            nullptr,
            &pool) != VK_SUCCESS) {
        fail("B002 copy command pool");
    }

    VkCommandBuffer command{};
    auto allocate_info = detail::make_vk_info<VkCommandBufferAllocateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    allocate_info.commandPool = pool;
    allocate_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocate_info.commandBufferCount = 1;
    if (dispatch_.allocateCommandBuffers(
            &allocate_info,
            &command) != VK_SUCCESS) {
        dispatch_.destroyCommandPool(pool, nullptr);
        fail("B002 copy command buffer");
    }

    VkQueryPool query_pool{};
    auto query_info = detail::make_vk_info<VkQueryPoolCreateInfo>(
        VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
    query_info.queryType = VK_QUERY_TYPE_TIMESTAMP;
    query_info.queryCount = 2;
    if (dispatch_.createQueryPool(
            &query_info,
            nullptr,
            &query_pool) != VK_SUCCESS) {
        dispatch_.destroyCommandPool(pool, nullptr);
        fail("B002 copy query pool");
    }

    auto begin_info = detail::make_vk_info<VkCommandBufferBeginInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (dispatch_.beginCommandBuffer(command, &begin_info) != VK_SUCCESS) {
        dispatch_.destroyQueryPool(query_pool, nullptr);
        dispatch_.destroyCommandPool(pool, nullptr);
        fail("B002 copy begin");
    }

    dispatch_.cmdResetQueryPool(command, query_pool, 0, 2);
    dispatch_.cmdWriteTimestamp(
        command,
        VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
        query_pool,
        0);

    auto before = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    before.srcAccessMask = VK_ACCESS_MEMORY_WRITE_BIT;
    before.dstAccessMask =
        VK_ACCESS_TRANSFER_READ_BIT |
        VK_ACCESS_TRANSFER_WRITE_BIT;
    dispatch_.cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        0,
        1,
        &before,
        0,
        nullptr,
        0,
        nullptr);

    dispatch_.cmdCopyBuffer(
        command,
        source,
        destination,
        static_cast<std::uint32_t>(regions.size()),
        regions.data());

    auto barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    barrier.dstAccessMask = VK_ACCESS_MEMORY_READ_BIT;
    dispatch_.cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
        0,
        1,
        &barrier,
        0,
        nullptr,
        0,
        nullptr);
    dispatch_.cmdWriteTimestamp(
        command,
        VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,
        query_pool,
        1);

    if (dispatch_.endCommandBuffer(command) != VK_SUCCESS) {
        dispatch_.destroyQueryPool(query_pool, nullptr);
        dispatch_.destroyCommandPool(pool, nullptr);
        fail("B002 copy end");
    }

    VkFence fence{};
    auto fence_info = detail::make_vk_info<VkFenceCreateInfo>(
        VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    if (dispatch_.createFence(
            &fence_info,
            nullptr,
            &fence) != VK_SUCCESS) {
        dispatch_.destroyQueryPool(query_pool, nullptr);
        dispatch_.destroyCommandPool(pool, nullptr);
        fail("B002 copy fence");
    }

    auto submit_info = detail::make_vk_info<VkSubmitInfo>(
        VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit_info.commandBufferCount = 1;
    submit_info.pCommandBuffers = &command;
    if (dispatch_.queueSubmit(
            queue_,
            1,
            &submit_info,
            fence) != VK_SUCCESS) {
        dispatch_.destroyFence(fence, nullptr);
        dispatch_.destroyQueryPool(query_pool, nullptr);
        dispatch_.destroyCommandPool(pool, nullptr);
        fail("B002 copy submit");
    }
    if (dispatch_.waitForFences(
            1,
            &fence,
            VK_TRUE,
            UINT64_MAX) != VK_SUCCESS) {
        dispatch_.destroyFence(fence, nullptr);
        dispatch_.destroyQueryPool(query_pool, nullptr);
        dispatch_.destroyCommandPool(pool, nullptr);
        fail("B002 copy wait");
    }

    std::uint64_t timestamps[2]{};
    if (dispatch_.getQueryPoolResults(
            query_pool,
            0,
            2,
            sizeof(timestamps),
            timestamps,
            sizeof(std::uint64_t),
            VK_QUERY_RESULT_64_BIT |
                VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
        dispatch_.destroyFence(fence, nullptr);
        dispatch_.destroyQueryPool(query_pool, nullptr);
        dispatch_.destroyCommandPool(pool, nullptr);
        fail("B002 copy timestamp readback");
    }

    const auto gpu_us =
        double(timestamps[1] - timestamps[0]) *
        double(timestamp_period_ns_) /
        1000.0;
    dispatch_.destroyFence(fence, nullptr);
    dispatch_.destroyQueryPool(query_pool, nullptr);
    dispatch_.destroyCommandPool(pool, nullptr);
    return gpu_us;
}

B002Buffer B002VulkanContext::upload_device_buffer(
    const void* data,
    VkDeviceSize size,
    VkBufferUsageFlags usage) {
    auto staging =
        create_host_buffer(size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT);
    std::memcpy(staging.mapped, data, static_cast<std::size_t>(size));
    auto device = create_device_buffer(size, usage);
    copy_buffer(staging.buffer, device.buffer, size);
    destroy_buffer(staging);
    return device;
}

B002Buffer B002VulkanContext::upload_device_address_buffer(
    const void* data,
    VkDeviceSize size,
    VkBufferUsageFlags usage) {
    auto staging =
        create_host_buffer(size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT);
    std::memcpy(staging.mapped, data, static_cast<std::size_t>(size));
    auto device = create_device_address_buffer(size, usage);
    copy_buffer(staging.buffer, device.buffer, size);
    destroy_buffer(staging);
    return device;
}

void B002VulkanContext::replace_device_buffer(
    B002Buffer& destination,
    const void* data,
    VkDeviceSize size,
    VkBufferUsageFlags usage) {
    auto replacement = upload_device_buffer(data, size, usage);
    destroy_buffer(destination);
    destination = replacement;
}

void B002VulkanContext::update_device_buffer(
    B002Buffer& destination,
    std::span<const B002BufferUpdate> updates) {
    (void)update_device_buffer_timed(
        destination,
        updates);
}

double B002VulkanContext::update_device_buffer_timed(
    B002Buffer& destination,
    std::span<const B002BufferUpdate> updates) {
    if (updates.empty()) return 0.0;

    VkDeviceSize staging_size = 0;
    for (const auto& update : updates) {
        if (update.data == nullptr || update.size == 0 ||
            update.destination_offset + update.size > destination.size) {
            fail("B002 invalid partial buffer update");
        }
        staging_size += update.size;
    }

    auto staging = create_host_buffer(
        staging_size,
        VK_BUFFER_USAGE_TRANSFER_SRC_BIT);
    std::vector<VkBufferCopy> regions;
    regions.reserve(updates.size());

    VkDeviceSize source_offset = 0;
    for (const auto& update : updates) {
        std::memcpy(
            static_cast<std::byte*>(staging.mapped) + source_offset,
            update.data,
            static_cast<std::size_t>(update.size));
        regions.push_back({
            source_offset,
            update.destination_offset,
            update.size,
        });
        source_offset += update.size;
    }

    const auto gpu_us = copy_buffer_regions_timed(
        staging.buffer,
        destination.buffer,
        regions);
    destroy_buffer(staging);
    return gpu_us;
}

void B002VulkanContext::download_device_buffer(
    const B002Buffer& source,
    void* destination,
    VkDeviceSize size) {
    if (size > source.size) {
        fail("B002 readback exceeds source buffer");
    }
    auto staging =
        create_host_buffer(size, VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    copy_buffer(source.buffer, staging.buffer, size);
    std::memcpy(destination, staging.mapped, static_cast<std::size_t>(size));
    destroy_buffer(staging);
}

void B002VulkanContext::destroy_buffer(B002Buffer& buffer) {
    if (buffer.mapped != nullptr && buffer.memory != VK_NULL_HANDLE) {
        dispatch_.unmapMemory(buffer.memory);
    }
    if (buffer.buffer != VK_NULL_HANDLE) {
        dispatch_.destroyBuffer(buffer.buffer, nullptr);
    }
    if (buffer.memory != VK_NULL_HANDLE) {
        const auto bytes = static_cast<std::size_t>(buffer.allocation_size);
        live_allocation_bytes_ =
            bytes <= live_allocation_bytes_
                ? live_allocation_bytes_ - bytes
                : 0U;
        dispatch_.freeMemory(buffer.memory, nullptr);
    }
    buffer = {};
}

std::vector<std::byte> read_b002_binary(const std::string& path) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) fail("Cannot open B002 binary file: " + path);
    const auto size = static_cast<std::size_t>(input.tellg());
    std::vector<std::byte> data(size);
    input.seekg(0);
    input.read(
        reinterpret_cast<char*>(data.data()),
        static_cast<std::streamsize>(size));
    if (!input) fail("Could not read B002 binary file: " + path);
    return data;
}

} // namespace phos::gi::research::lane_b

#include "vk_context.hpp"
#include "vk_init.hpp"

#include <cstring>
#include <fstream>
#include <stdexcept>

namespace phos::gi {

namespace {
[[noreturn]] void fail(const std::string& message) { throw std::runtime_error(message); }
}

VulkanContext::VulkanContext(bool validation)
    : VulkanContext(VulkanContextOptions{validation, false}) {}

VulkanContext::VulkanContext(VulkanContextOptions options) {
    const bool validation = options.validation;
    vkb::InstanceBuilder builder;
    builder.set_app_name("phos-gi-lab")
        .set_engine_name("research")
        .set_headless()
        .require_api_version(1, 3);
    if (validation) {
        builder.request_validation_layers().use_default_debug_messenger();
    }
    auto instance_ret = builder.build();
    if (!instance_ret) fail("Vulkan instance: " + instance_ret.error().message());
    instance_ = instance_ret.value();
    instance_dispatch_ = instance_.make_table();

    vkb::PhysicalDeviceSelector selector(instance_);
    selector.set_minimum_version(1, 3);
    if (options.require_shader_buffer_int64_atomics) {
        VkPhysicalDeviceFeatures required{};
        required.shaderInt64 = VK_TRUE;
        selector.set_required_features(required);

        VkPhysicalDeviceVulkan12Features required12{};
        required12.shaderBufferInt64Atomics = VK_TRUE;
        selector.set_required_features_12(required12);
    }
    auto physical_ret = selector.select();
    if (!physical_ret) fail("Physical device: " + physical_ret.error().message());

    vkb::DeviceBuilder device_builder(physical_ret.value());
    auto device_ret = device_builder.build();
    if (!device_ret) fail("Logical device: " + device_ret.error().message());
    device_ = device_ret.value();
    dispatch_ = device_.make_table();

    auto queue_ret = device_.get_queue(vkb::QueueType::compute);
    auto family_ret = device_.get_queue_index(vkb::QueueType::compute);
    if (!queue_ret || !family_ret) fail("No compute-capable queue available");
    queue_ = queue_ret.value();
    queue_family_ = family_ret.value();

    VkPhysicalDeviceProperties properties{};
    instance_dispatch_.getPhysicalDeviceProperties(device_.physical_device.physical_device, &properties);
    timestamp_period_ns_ = properties.limits.timestampPeriod;
    device_name_ = properties.deviceName;

    const auto& q = device_.queue_families.at(queue_family_);
    if (q.timestampValidBits == 0) {
        fail("Selected compute queue does not support timestamps");
    }
}

VulkanContext::~VulkanContext() {
    if (device_.device != VK_NULL_HANDLE) {
        dispatch_.deviceWaitIdle();
        vkb::destroy_device(device_);
    }
    if (instance_.instance != VK_NULL_HANDLE) {
        vkb::destroy_instance(instance_);
    }
}

std::uint32_t VulkanContext::find_memory_type(std::uint32_t bits, VkMemoryPropertyFlags required) const {
    VkPhysicalDeviceMemoryProperties props{};
    instance_dispatch_.getPhysicalDeviceMemoryProperties(device_.physical_device.physical_device, &props);
    for (std::uint32_t i = 0; i < props.memoryTypeCount; ++i) {
        if ((bits & (1u << i)) && (props.memoryTypes[i].propertyFlags & required) == required) return i;
    }
    fail("No compatible Vulkan memory type");
}

GpuBuffer VulkanContext::create_buffer(VkDeviceSize size, VkBufferUsageFlags usage,
                                       VkMemoryPropertyFlags properties, bool map) {
    GpuBuffer out{};
    out.size = size;

    auto bi = detail::make_vk_info<VkBufferCreateInfo>(VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO);
    bi.size = size;
    bi.usage = usage;
    bi.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    if (dispatch_.createBuffer(&bi, nullptr, &out.buffer) != VK_SUCCESS) fail("vkCreateBuffer failed");

    VkMemoryRequirements req{};
    dispatch_.getBufferMemoryRequirements(out.buffer, &req);
    auto ai = detail::make_vk_info<VkMemoryAllocateInfo>(VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO);
    ai.allocationSize = req.size;
    ai.memoryTypeIndex = find_memory_type(req.memoryTypeBits, properties);
    if (dispatch_.allocateMemory(&ai, nullptr, &out.memory) != VK_SUCCESS) fail("vkAllocateMemory failed");
    if (dispatch_.bindBufferMemory(out.buffer, out.memory, 0) != VK_SUCCESS) fail("vkBindBufferMemory failed");
    if (map && dispatch_.mapMemory(out.memory, 0, size, 0, &out.mapped) != VK_SUCCESS) fail("vkMapMemory failed");
    return out;
}

GpuBuffer VulkanContext::create_host_buffer(VkDeviceSize size, VkBufferUsageFlags usage) {
    return create_buffer(size, usage,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, true);
}

GpuBuffer VulkanContext::create_device_buffer(VkDeviceSize size, VkBufferUsageFlags usage) {
    return create_buffer(size, usage | VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT,
        VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, false);
}

void VulkanContext::copy_buffer(VkBuffer source, VkBuffer destination, VkDeviceSize size) {
    VkCommandPool pool{};
    auto pci = detail::make_vk_info<VkCommandPoolCreateInfo>(VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
    pci.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
    pci.queueFamilyIndex = queue_family_;
    if (dispatch_.createCommandPool(&pci, nullptr, &pool) != VK_SUCCESS) fail("upload command pool");

    VkCommandBuffer cmd{};
    auto cai = detail::make_vk_info<VkCommandBufferAllocateInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    cai.commandPool = pool;
    cai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    cai.commandBufferCount = 1;
    if (dispatch_.allocateCommandBuffers(&cai, &cmd) != VK_SUCCESS) fail("upload command buffer");

    auto cbi = detail::make_vk_info<VkCommandBufferBeginInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    cbi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    dispatch_.beginCommandBuffer(cmd, &cbi);

    // Copies are setup/validation work, not part of benchmark timestamps.
    // Make dependencies across sequential queue submissions explicit so upload
    // and readback correctness never relies on implicit cache visibility.
    auto before = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    before.srcAccessMask = VK_ACCESS_MEMORY_WRITE_BIT;
    before.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT | VK_ACCESS_TRANSFER_WRITE_BIT;
    dispatch_.cmdPipelineBarrier(
        cmd,
        VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        0, 1, &before, 0, nullptr, 0, nullptr);

    VkBufferCopy region{0, 0, size};
    dispatch_.cmdCopyBuffer(cmd, source, destination, 1, &region);

    auto after = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    after.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    after.dstAccessMask = VK_ACCESS_MEMORY_READ_BIT;
    dispatch_.cmdPipelineBarrier(
        cmd,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
        0, 1, &after, 0, nullptr, 0, nullptr);

    dispatch_.endCommandBuffer(cmd);

    VkFence fence{};
    auto fi = detail::make_vk_info<VkFenceCreateInfo>(VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    dispatch_.createFence(&fi, nullptr, &fence);
    auto si = detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
    si.commandBufferCount = 1;
    si.pCommandBuffers = &cmd;
    if (dispatch_.queueSubmit(queue_, 1, &si, fence) != VK_SUCCESS) fail("upload submit");
    dispatch_.waitForFences(1, &fence, VK_TRUE, UINT64_MAX);
    dispatch_.destroyFence(fence, nullptr);
    dispatch_.destroyCommandPool(pool, nullptr);
}

GpuBuffer VulkanContext::upload_device_buffer(const void* data, VkDeviceSize size, VkBufferUsageFlags usage) {
    auto staging = create_host_buffer(size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT);
    std::memcpy(staging.mapped, data, static_cast<std::size_t>(size));
    auto device = create_device_buffer(size, usage);
    copy_buffer(staging.buffer, device.buffer, size);
    destroy_buffer(staging);
    return device;
}

void VulkanContext::download_device_buffer(const GpuBuffer& source, void* destination, VkDeviceSize size) {
    auto staging = create_host_buffer(size, VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    copy_buffer(source.buffer, staging.buffer, size);
    std::memcpy(destination, staging.mapped, static_cast<std::size_t>(size));
    destroy_buffer(staging);
}

void VulkanContext::destroy_buffer(GpuBuffer& buffer) {
    if (buffer.mapped) dispatch_.unmapMemory(buffer.memory);
    if (buffer.buffer) dispatch_.destroyBuffer(buffer.buffer, nullptr);
    if (buffer.memory) dispatch_.freeMemory(buffer.memory, nullptr);
    buffer = {};
}

std::vector<std::byte> read_binary_file(const std::string& path) {
    std::ifstream f(path, std::ios::binary | std::ios::ate);
    if (!f) fail("Cannot open file: " + path);
    const auto size = static_cast<std::size_t>(f.tellg());
    std::vector<std::byte> data(size);
    f.seekg(0);
    f.read(reinterpret_cast<char*>(data.data()), static_cast<std::streamsize>(size));
    return data;
}

} // namespace phos::gi

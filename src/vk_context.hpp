#pragma once
#include <VkBootstrap.h>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace phos::gi {

struct GpuBuffer {
    VkBuffer buffer{VK_NULL_HANDLE};
    VkDeviceMemory memory{VK_NULL_HANDLE};
    VkDeviceSize size{};
    void* mapped{};
};

class VulkanContext {
public:
    explicit VulkanContext(bool validation);
    ~VulkanContext();
    VulkanContext(const VulkanContext&) = delete;
    VulkanContext& operator=(const VulkanContext&) = delete;

    [[nodiscard]] vkb::DispatchTable& vk() { return dispatch_; }
    [[nodiscard]] VkDevice device() const { return device_.device; }
    [[nodiscard]] VkPhysicalDevice physical_device() const { return device_.physical_device.physical_device; }
    [[nodiscard]] VkQueue queue() const { return queue_; }
    [[nodiscard]] std::uint32_t queue_family() const { return queue_family_; }
    [[nodiscard]] float timestamp_period_ns() const { return timestamp_period_ns_; }
    [[nodiscard]] const std::string& device_name() const { return device_name_; }

    GpuBuffer create_host_buffer(VkDeviceSize size, VkBufferUsageFlags usage);
    GpuBuffer create_device_buffer(VkDeviceSize size, VkBufferUsageFlags usage);
    GpuBuffer upload_device_buffer(const void* data, VkDeviceSize size, VkBufferUsageFlags usage);
    void download_device_buffer(const GpuBuffer& source, void* destination, VkDeviceSize size);
    void destroy_buffer(GpuBuffer& buffer);

private:
    GpuBuffer create_buffer(VkDeviceSize size, VkBufferUsageFlags usage, VkMemoryPropertyFlags properties, bool map);
    void copy_buffer(VkBuffer source, VkBuffer destination, VkDeviceSize size);
    std::uint32_t find_memory_type(std::uint32_t bits, VkMemoryPropertyFlags required) const;

    vkb::Instance instance_{};
    vkb::InstanceDispatchTable instance_dispatch_{};
    vkb::Device device_{};
    vkb::DispatchTable dispatch_{};
    VkQueue queue_{VK_NULL_HANDLE};
    std::uint32_t queue_family_{};
    float timestamp_period_ns_{1.0f};
    std::string device_name_;
};

std::vector<std::byte> read_binary_file(const std::string& path);

} // namespace phos::gi

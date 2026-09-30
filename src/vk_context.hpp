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
    [[nodiscard]] const std::string& driver_name() const { return driver_name_; }
    [[nodiscard]] const std::string& driver_info() const { return driver_info_; }
    [[nodiscard]] std::uint32_t api_version() const { return api_version_; }
    [[nodiscard]] std::uint32_t driver_version() const { return driver_version_; }
    [[nodiscard]] std::uint32_t vendor_id() const { return vendor_id_; }
    [[nodiscard]] std::uint32_t device_id() const { return device_id_; }

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
    std::string driver_name_;
    std::string driver_info_;
    std::uint32_t api_version_{};
    std::uint32_t driver_version_{};
    std::uint32_t vendor_id_{};
    std::uint32_t device_id_{};
};

std::vector<std::byte> read_binary_file(const std::string& path);

} // namespace phos::gi

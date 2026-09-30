#pragma once

#include <VkBootstrap.h>

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace phos::gi::research::lane_b {

inline constexpr const char* kB002TargetDeviceName =
    "AMD Radeon 8060S Graphics (RADV STRIX_HALO)";

struct B002BufferUpdate {
    VkDeviceSize destination_offset{};
    const void* data{};
    VkDeviceSize size{};
};

struct B002Buffer {
    VkBuffer buffer{VK_NULL_HANDLE};
    VkDeviceMemory memory{VK_NULL_HANDLE};
    VkDeviceSize size{};
    VkDeviceSize allocation_size{};
    VkDeviceAddress address{};
    void* mapped{};
};

class B002VulkanContext {
public:
    explicit B002VulkanContext(
        bool validation,
        std::string target_device = kB002TargetDeviceName,
        bool require_hwrt = false);
    ~B002VulkanContext();

    B002VulkanContext(const B002VulkanContext&) = delete;
    B002VulkanContext& operator=(const B002VulkanContext&) = delete;

    [[nodiscard]] vkb::DispatchTable& vk() noexcept { return dispatch_; }
    [[nodiscard]] VkDevice device() const noexcept { return device_.device; }
    [[nodiscard]] VkPhysicalDevice physical_device() const noexcept {
        return device_.physical_device.physical_device;
    }
    [[nodiscard]] VkQueue queue() const noexcept { return queue_; }
    [[nodiscard]] std::uint32_t queue_family() const noexcept {
        return queue_family_;
    }
    [[nodiscard]] float timestamp_period_ns() const noexcept {
        return timestamp_period_ns_;
    }
    [[nodiscard]] const std::string& device_name() const noexcept {
        return device_name_;
    }
    [[nodiscard]] const std::string& driver_name() const noexcept {
        return driver_name_;
    }
    [[nodiscard]] const std::string& driver_info() const noexcept {
        return driver_info_;
    }
    [[nodiscard]] std::uint32_t api_version() const noexcept {
        return api_version_;
    }
    [[nodiscard]] bool hwrt_enabled() const noexcept {
        return hwrt_enabled_;
    }
    [[nodiscard]] VkDeviceSize acceleration_scratch_alignment() const noexcept {
        return acceleration_scratch_alignment_;
    }

    // Lane J #23 selective comparator import: track only B002Buffer-backed
    // Vulkan allocations so topology-rebuild old/new overlap and staging/scratch
    // lifetimes can be compared with J003's allocation-requirement census.
    [[nodiscard]] std::size_t live_allocation_bytes() const noexcept {
        return live_allocation_bytes_;
    }
    [[nodiscard]] std::size_t peak_allocation_bytes() const noexcept {
        return peak_allocation_bytes_;
    }
    void reset_allocation_peak() noexcept {
        peak_allocation_bytes_ = live_allocation_bytes_;
    }

    [[nodiscard]] B002Buffer create_host_buffer(
        VkDeviceSize size,
        VkBufferUsageFlags usage);
    [[nodiscard]] B002Buffer create_device_buffer(
        VkDeviceSize size,
        VkBufferUsageFlags usage);
    [[nodiscard]] B002Buffer create_device_address_buffer(
        VkDeviceSize size,
        VkBufferUsageFlags usage);
    [[nodiscard]] B002Buffer upload_device_buffer(
        const void* data,
        VkDeviceSize size,
        VkBufferUsageFlags usage);
    [[nodiscard]] B002Buffer upload_device_address_buffer(
        const void* data,
        VkDeviceSize size,
        VkBufferUsageFlags usage);
    void replace_device_buffer(
        B002Buffer& destination,
        const void* data,
        VkDeviceSize size,
        VkBufferUsageFlags usage);
    void update_device_buffer(
        B002Buffer& destination,
        std::span<const B002BufferUpdate> updates);
    [[nodiscard]] double update_device_buffer_timed(
        B002Buffer& destination,
        std::span<const B002BufferUpdate> updates);
    void download_device_buffer(
        const B002Buffer& source,
        void* destination,
        VkDeviceSize size);
    void destroy_buffer(B002Buffer& buffer);

private:
    [[nodiscard]] B002Buffer create_buffer(
        VkDeviceSize size,
        VkBufferUsageFlags usage,
        VkMemoryPropertyFlags properties,
        bool map,
        bool device_address = false);
    void copy_buffer(
        VkBuffer source,
        VkBuffer destination,
        VkDeviceSize size);
    void copy_buffer_regions(
        VkBuffer source,
        VkBuffer destination,
        std::span<const VkBufferCopy> regions);
    [[nodiscard]] double copy_buffer_regions_timed(
        VkBuffer source,
        VkBuffer destination,
        std::span<const VkBufferCopy> regions);
    [[nodiscard]] std::uint32_t find_memory_type(
        std::uint32_t bits,
        VkMemoryPropertyFlags required) const;

    vkb::Instance instance_{};
    vkb::InstanceDispatchTable instance_dispatch_{};
    vkb::Device device_{};
    vkb::DispatchTable dispatch_{};
    VkQueue queue_{VK_NULL_HANDLE};
    std::uint32_t queue_family_{};
    float timestamp_period_ns_{1.0F};
    std::string device_name_;
    std::string driver_name_;
    std::string driver_info_;
    std::uint32_t api_version_{};
    VkDeviceSize acceleration_scratch_alignment_{1};
    bool hwrt_enabled_{};
    std::size_t live_allocation_bytes_{};
    std::size_t peak_allocation_bytes_{};
};

[[nodiscard]] std::vector<std::byte> read_b002_binary(
    const std::string& path);

} // namespace phos::gi::research::lane_b

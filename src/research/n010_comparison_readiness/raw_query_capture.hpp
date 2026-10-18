#pragma once
// Private descriptive-pilot instrumentation. No default target includes this.
#include <vulkan/vulkan.h>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <map>
#include <mutex>
#include <stdexcept>
#include <string>
#include <type_traits>

namespace phos::gi::research::n010 {
class RawQueryCapture {
    struct Device {
        PFN_vkGetQueryPoolResults query;
        PFN_vkWaitForFences wait;
        double period;
        std::uint32_t bits, family, id;
    };
    std::map<VkDevice, Device> devices_;
    std::mutex mutex_;
    std::ofstream output_;
    std::uint64_t sequence_{};
    std::uint32_t next_device_{};
    std::int32_t frame_{-1};
    std::string phase_{"setup"};

    static std::uint64_t handle(auto value) {
        if constexpr (std::is_pointer_v<decltype(value)>)
            return reinterpret_cast<std::uintptr_t>(value);
        else return std::uint64_t(value);
    }
    void require_stream() {
        if (!output_.is_open()) {
            const char* path = std::getenv("PHOS_N010_RAW_QUERY_CAPTURE");
            if (!path || !*path || std::filesystem::exists(path))
                throw std::runtime_error("fresh explicit raw-query capture path required");
            output_.open(path);
            output_ << std::setprecision(17);
        }
        if (!output_) throw std::runtime_error("raw-query stream failed");
    }
    Device lookup(VkDevice device) {
        std::lock_guard lock(mutex_);
        return devices_.at(device);
    }
    void finish_row() {
        output_ << "}\n";
        output_.flush();
        if (!output_) throw std::runtime_error("raw-query receipt write failed");
    }
    static VKAPI_ATTR VkResult VKAPI_CALL query(
            VkDevice device, VkQueryPool pool, std::uint32_t first,
            std::uint32_t count, std::size_t size, void* data,
            VkDeviceSize stride, VkQueryResultFlags flags) noexcept {
        try {
            auto& capture = instance();
            const auto info = capture.lookup(device);
            const auto result = info.query(device, pool, first, count, size, data, stride, flags);
            std::lock_guard lock(capture.mutex_);
            capture.output_ << "{\"kind\":\"query\",\"sequence\":" << capture.sequence_++
                << ",\"context\":" << info.id << ",\"frame\":" << capture.frame_
                << ",\"phase\":\"" << capture.phase_ << "\",\"query_pool\":" << handle(pool)
                << ",\"first\":" << first << ",\"count\":" << count
                << ",\"data_size\":" << size << ",\"stride\":" << stride
                << ",\"flags\":" << flags << ",\"result\":" << int(result)
                << ",\"timestamp_period_ns\":" << info.period
                << ",\"timestamp_valid_bits\":" << info.bits << ",\"ticks\":[";
            if (result == VK_SUCCESS) {
                if (!(flags & VK_QUERY_RESULT_64_BIT) || !count || count > 1048576U ||
                    stride < 8 || size < std::size_t(count-1)*stride+8 || !data)
                    throw std::runtime_error("unsupported raw-query receipt layout");
                for (std::uint32_t i=0; i<count; ++i) {
                    std::uint64_t word;
                    std::memcpy(&word, static_cast<const std::byte*>(data)+i*stride, 8);
                    capture.output_ << (i ? "," : "") << word;
                }
            }
            capture.output_ << ']';
            capture.finish_row();
            return result;
        } catch (...) { std::abort(); }
    }
    static VKAPI_ATTR VkResult VKAPI_CALL wait(
            VkDevice device, std::uint32_t count, const VkFence* fences,
            VkBool32 all, std::uint64_t timeout) noexcept {
        try {
            auto& capture = instance();
            const auto info = capture.lookup(device);
            const auto bounded = timeout < 500000000ULL ? timeout : 500000000ULL;
            const auto result = info.wait(device, count, fences, all, bounded);
            std::lock_guard lock(capture.mutex_);
            capture.output_ << "{\"kind\":\"fence\",\"sequence\":" << capture.sequence_++
                << ",\"context\":" << info.id << ",\"frame\":" << capture.frame_
                << ",\"phase\":\"" << capture.phase_ << "\",\"count\":" << count
                << ",\"wait_all\":" << all << ",\"requested_timeout_ns\":" << timeout
                << ",\"bounded_timeout_ns\":" << bounded << ",\"result\":" << int(result);
            capture.finish_row();
            // Some legacy setup paths ignore the return code. Stop the native
            // before any further readback/reuse after an unsuccessful wait.
            if (result != VK_SUCCESS) std::abort();
            return result;
        } catch (...) { std::abort(); }
    }
public:
    static RawQueryCapture& instance() { static RawQueryCapture capture; return capture; }
    void phase(std::int32_t frame, const char* label) {
        std::lock_guard lock(mutex_);
        require_stream();
        if (!label || std::strspn(label, "abcdefghijklmnopqrstuvwxyz-0123456789") != std::strlen(label))
            throw std::runtime_error("invalid raw-query phase");
        frame_ = frame;phase_ = label;
        output_ << "{\"kind\":\"phase\",\"sequence\":" << sequence_++
                << ",\"frame\":" << frame_ << ",\"phase\":\"" << phase_ << '"';
        finish_row();
    }
    void install(auto& table, double period, std::uint32_t bits, std::uint32_t family) {
        std::lock_guard lock(mutex_);
        require_stream();
        if (!(period > 0) || !std::isfinite(period) || !bits || bits > 64 || devices_.contains(table.device) ||
                !table.fp_vkGetQueryPoolResults || !table.fp_vkWaitForFences)
            throw std::runtime_error("invalid/duplicate raw-query device registration");
        const Device info{table.fp_vkGetQueryPoolResults, table.fp_vkWaitForFences,
                          period, bits, family, ++next_device_};
        devices_.emplace(table.device, info);
        output_ << "{\"kind\":\"context\",\"sequence\":" << sequence_++
                << ",\"context\":" << info.id << ",\"device_handle\":" << handle(table.device)
                << ",\"queue_family\":" << family << ",\"timestamp_period_ns\":" << period
                << ",\"timestamp_valid_bits\":" << bits;
        finish_row();
        table.fp_vkGetQueryPoolResults = &query;
        table.fp_vkWaitForFences = &wait;
    }
};
}

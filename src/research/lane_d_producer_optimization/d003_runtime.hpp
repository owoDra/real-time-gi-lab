#pragma once

#include "../lane_a_split_rc/a001_runtime.hpp"

#include <cstddef>
#include <cstdint>
#include <memory>

namespace phos::gi::lane_d {

struct D003Timings {
    double visibility_reset_us{};
    double visibility_select_us{};
    double producer_reset_us{};
    double producer_emit_us{};
    double finalize_us{};
    double gather_us{};
    double merge_us{};
    double resolve_us{};

    [[nodiscard]] double producer_total_us() const {
        return visibility_reset_us +
               visibility_select_us +
               producer_reset_us +
               producer_emit_us +
               finalize_us;
    }

    [[nodiscard]] double end_to_end_us() const {
        return producer_total_us() +
               gather_us +
               merge_us +
               resolve_us;
    }
};

struct D003Memory {
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t resident_bytes{};
    std::size_t packed_visibility_bytes{};
    std::size_t producer_scratch_bytes{};
    std::size_t stream_capacity_bytes{};
};

class D003Runtime {
public:
    D003Runtime(
        VulkanContext& context,
        const lane_a::SceneSurfaceSet& scene,
        const lane_a::A001ParamsGpu& params);
    ~D003Runtime();

    D003Runtime(const D003Runtime&) = delete;
    D003Runtime& operator=(const D003Runtime&) = delete;

    D003Timings measure(std::uint32_t iterations);
    lane_a::A001Readback readback();
    [[nodiscard]] D003Memory memory() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace phos::gi::lane_d

#pragma once

#include "traversal_contract.hpp"

#include <cstdint>

namespace phos::gi::research::lane_b {

// Minimal B002 GPU ABI required by the exact Lane-E HWRT rebuild comparator.
// The software hierarchy types are intentionally not imported into this
// primary-HWRT memory preflight.
struct alignas(16) GpuRay {
    float origin_tmax[4]{};
    float direction_pad[4]{};
};
static_assert(sizeof(GpuRay) == 32);

struct alignas(16) GpuTriangle {
    float v0[4]{};
    float v1[4]{};
    float v2[4]{};
    std::uint32_t metadata[4]{};
};
static_assert(sizeof(GpuTriangle) == 64);

struct alignas(16) GpuHit {
    float normal_t[4]{};
    std::uint32_t metadata[4]{};
};
static_assert(sizeof(GpuHit) == 32);

[[nodiscard]] inline GpuTriangle to_gpu_triangle(
    const Triangle& triangle) noexcept {
    return {
        {triangle.v0.x, triangle.v0.y, triangle.v0.z, 0.0F},
        {triangle.v1.x, triangle.v1.y, triangle.v1.z, 0.0F},
        {triangle.v2.x, triangle.v2.y, triangle.v2.z, 0.0F},
        {
            triangle.primitive_id,
            triangle.material_id,
            triangle.instance_id,
            triangle.two_sided ? 1U : 0U,
        },
    };
}

} // namespace phos::gi::research::lane_b

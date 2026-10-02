#pragma once
#include <cstdint>
#include <type_traits>

namespace phos::gi::lane_a {

struct alignas(16) SurfaceSampleGpu {
    float position[4]{};
    float normal[4]{};
};
static_assert(sizeof(SurfaceSampleGpu) == 32);
static_assert(std::is_standard_layout_v<SurfaceSampleGpu>);

} // namespace phos::gi::lane_a

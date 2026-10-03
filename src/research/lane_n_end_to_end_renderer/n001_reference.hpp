#pragma once

#include "n001_runtime.hpp"

#include <cstdint>
#include <vector>

namespace phos::gi::research::integration {

struct N001ReferenceSettings {
    std::uint32_t min_spp{512};
    std::uint32_t max_spp{8192};
    std::uint32_t max_diffuse_bounces{8};
    std::uint64_t seed_a{0x12345678ULL};
    std::uint64_t seed_b{0x9abcdef0ULL};
    double p99_abs_luminance_max{0.001};
    double p99_relative_luminance_max{0.01};
    double relative_luminance_floor{1.0e-4};
};

struct N001ReferenceResult {
    std::uint32_t spp{};
    bool converged{};
    double replicate_p99_abs_luminance{};
    double replicate_p99_relative_luminance{};
    std::vector<float> rgb;
};

[[nodiscard]] N001ReferenceResult n001_render_reference(
    const I001RendererReadback& frame,
    const N001ReferenceSettings& settings = {});

} // namespace phos::gi::research::integration

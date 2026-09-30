#pragma once

#include "j003_types.hpp"

#include <cstddef>
#include <span>
#include <vector>

namespace phos::gi::research::lane_j {

[[nodiscard]] std::vector<Ray> make_validation_rays(
    std::span<const Triangle> triangles,
    std::size_t count);

[[nodiscard]] Hit trace_reference(
    std::span<const Triangle> triangles,
    const Ray& ray);

// Diagnostic form of the same B001-compatible exact triangle test. It is
// intentionally public so a retained mismatch can distinguish traversal-state
// errors from a triangle-intersection/tie-boundary difference.
[[nodiscard]] Hit trace_reference_triangle(
    const Triangle& triangle,
    const Ray& ray);

[[nodiscard]] bool equivalent_hit(const Hit& expected, const GpuHit& actual);

[[nodiscard]] GpuRay to_gpu_ray(const Ray& ray);

} // namespace phos::gi::research::lane_j

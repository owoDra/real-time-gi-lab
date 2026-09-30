#include "j003_reference.hpp"

#include "j003_clustered_bvh.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace phos::gi::research::lane_j {
namespace {

[[nodiscard]] Vec3 add(Vec3 a, Vec3 b) {
    return {a.x + b.x, a.y + b.y, a.z + b.z};
}

[[nodiscard]] Vec3 sub(Vec3 a, Vec3 b) {
    return {a.x - b.x, a.y - b.y, a.z - b.z};
}

[[nodiscard]] Vec3 mul(Vec3 value, float scalar) {
    return {value.x * scalar, value.y * scalar, value.z * scalar};
}

[[nodiscard]] float dot(Vec3 a, Vec3 b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

[[nodiscard]] Vec3 cross(Vec3 a, Vec3 b) {
    return {
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    };
}

[[nodiscard]] float length(Vec3 value) {
    return std::sqrt(dot(value, value));
}

[[nodiscard]] Vec3 normalize(Vec3 value) {
    const auto len = length(value);
    if (!(len > 0.0F) || !std::isfinite(len)) {
        return {};
    }
    return mul(value, 1.0F / len);
}

[[nodiscard]] std::uint32_t mix32(std::uint32_t value) {
    value ^= value >> 16U;
    value *= 0x7feb352dU;
    value ^= value >> 15U;
    value *= 0x846ca68bU;
    value ^= value >> 16U;
    return value;
}

[[nodiscard]] Vec3 triangle_centroid(const Triangle& triangle) {
    return mul(add(add(triangle.v0, triangle.v1), triangle.v2), 1.0F / 3.0F);
}

[[nodiscard]] bool prefer(const Hit& candidate, const Hit& current) {
    if (!candidate.hit) {
        return false;
    }
    if (!current.hit) {
        return true;
    }
    const auto tolerance = std::max(
        kHitAbsTol,
        std::abs(current.t) * kHitRelTol);
    return candidate.t < current.t - tolerance ||
           (std::abs(candidate.t - current.t) <= tolerance &&
            candidate.primitive_id < current.primitive_id);
}

[[nodiscard]] Hit intersect_triangle(
    const Triangle& triangle,
    const Ray& ray,
    float best_t) {
    const auto e1 = sub(triangle.v1, triangle.v0);
    const auto e2 = sub(triangle.v2, triangle.v0);
    const auto p = cross(ray.direction, e2);
    const auto determinant = dot(e1, p);

    if (triangle.two_sided
            ? std::abs(determinant) < 1.0e-8F
            : determinant <= 1.0e-8F) {
        return {};
    }

    const auto inverse = 1.0F / determinant;
    const auto tv = sub(ray.origin, triangle.v0);
    const auto u = dot(tv, p) * inverse;
    if (u < 0.0F || u > 1.0F) {
        return {};
    }
    const auto q = cross(tv, e1);
    const auto v = dot(ray.direction, q) * inverse;
    if (v < 0.0F || u + v > 1.0F) {
        return {};
    }
    const auto distance = dot(e2, q) * inverse;
    const auto tolerance = std::max(
        kHitAbsTol,
        std::abs(best_t) * kHitRelTol);
    if (distance < kRayTMin ||
        distance > ray.t_max ||
        distance > best_t + tolerance) {
        return {};
    }

    return {
        true,
        distance,
        normalize(cross(e1, e2)),
        triangle.primitive_id,
        triangle.material_id,
        triangle.instance_id,
    };
}

} // namespace

std::vector<Ray> make_validation_rays(
    std::span<const Triangle> triangles,
    std::size_t count) {
    if (triangles.empty() || count == 0U) {
        throw std::runtime_error("J003 validation rays require non-empty input");
    }

    Aabb bounds{};
    for (const auto& triangle : triangles) {
        bounds = merge_bounds(bounds, triangle_bounds(triangle));
    }
    const auto extent = sub(bounds.max, bounds.min);
    const auto diagonal = std::max(length(extent), 1.0F);
    const auto scene_center = mul(add(bounds.min, bounds.max), 0.5F);

    std::vector<Ray> rays;
    rays.reserve(count);
    for (std::size_t i = 0U; i < count; ++i) {
        const auto seed = mix32(static_cast<std::uint32_t>(i) ^ 0x4a303033U);
        if ((i & 7U) == 7U) {
            // Deterministic miss ray exercises the no-hit encoding.
            const Vec3 offset{
                diagonal * (2.0F + float(seed & 7U) * 0.1F),
                diagonal * (1.5F + float((seed >> 3U) & 7U) * 0.1F),
                diagonal * (2.5F + float((seed >> 6U) & 7U) * 0.1F),
            };
            const auto origin = add(scene_center, offset);
            const auto direction = normalize(offset);
            rays.push_back({origin, direction, diagonal * 4.0F});
            continue;
        }

        const auto triangle_index =
            std::size_t(seed) % triangles.size();
        const auto& triangle = triangles[triangle_index];
        const auto e1 = sub(triangle.v1, triangle.v0);
        const auto e2 = sub(triangle.v2, triangle.v0);
        auto normal = normalize(cross(e1, e2));
        if (length(normal) <= 0.0F) {
            normal = {0.0F, 1.0F, 0.0F};
        }
        const auto center = triangle_centroid(triangle);
        const auto distance =
            diagonal * (0.25F + 0.05F * float((seed >> 9U) & 3U));
        const auto origin = add(center, mul(normal, distance));
        rays.push_back({
            origin,
            mul(normal, -1.0F),
            diagonal * 4.0F,
        });
    }
    return rays;
}

Hit trace_reference(
    std::span<const Triangle> triangles,
    const Ray& input_ray) {
    const auto direction_length = length(input_ray.direction);
    if (!std::isfinite(direction_length) ||
        direction_length <= 1.0e-8F ||
        !std::isfinite(input_ray.t_max) ||
        input_ray.t_max <= kRayTMin) {
        return {};
    }

    const Ray ray{
        input_ray.origin,
        mul(input_ray.direction, 1.0F / direction_length),
        input_ray.t_max,
    };
    Hit best{};
    for (const auto& triangle : triangles) {
        const auto candidate = intersect_triangle(
            triangle,
            ray,
            best.hit ? best.t : ray.t_max);
        if (prefer(candidate, best)) {
            best = candidate;
        }
    }
    return best;
}

bool equivalent_hit(const Hit& expected, const GpuHit& actual) {
    const auto actual_hit = actual.ids[3] != 0U;
    if (expected.hit != actual_hit) {
        return false;
    }
    if (!expected.hit) {
        return std::isinf(actual.t_normal[0]) &&
               actual.ids[0] == kInvalidId &&
               actual.ids[1] == kInvalidId &&
               actual.ids[2] == kInvalidId;
    }

    const auto tolerance = std::max(
        kHitAbsTol,
        std::abs(expected.t) * kHitRelTol);
    const Vec3 actual_normal{
        actual.t_normal[1],
        actual.t_normal[2],
        actual.t_normal[3],
    };
    const auto normal_agreement = dot(
        normalize(expected.normal),
        normalize(actual_normal));
    return std::abs(expected.t - actual.t_normal[0]) <= tolerance &&
           expected.primitive_id == actual.ids[0] &&
           expected.material_id == actual.ids[1] &&
           expected.instance_id == actual.ids[2] &&
           normal_agreement > 0.9999F;
}

GpuRay to_gpu_ray(const Ray& ray) {
    GpuRay out{};
    out.origin_tmax = {
        ray.origin.x,
        ray.origin.y,
        ray.origin.z,
        ray.t_max,
    };
    out.direction = {
        ray.direction.x,
        ray.direction.y,
        ray.direction.z,
        0.0F,
    };
    return out;
}

} // namespace phos::gi::research::lane_j

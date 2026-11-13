#pragma once

#include <cmath>
#include <cstdint>
#include <limits>
#include <span>

namespace phos::gi::research::lane_b {

constexpr std::uint32_t kInvalidId = std::numeric_limits<std::uint32_t>::max();
constexpr float kRayTMin = 1.0e-4F;
constexpr float kHitDistanceAbsTolerance = 2.0e-4F;
constexpr float kHitDistanceRelTolerance = 2.0e-5F;

struct Vec3 {
    float x{};
    float y{};
    float z{};
};

[[nodiscard]] inline Vec3 operator+(Vec3 a, Vec3 b) noexcept {
    return {a.x + b.x, a.y + b.y, a.z + b.z};
}
[[nodiscard]] inline Vec3 operator-(Vec3 a, Vec3 b) noexcept {
    return {a.x - b.x, a.y - b.y, a.z - b.z};
}
[[nodiscard]] inline Vec3 operator*(Vec3 v, float s) noexcept {
    return {v.x * s, v.y * s, v.z * s};
}
[[nodiscard]] inline Vec3 operator/(Vec3 v, float s) noexcept {
    return {v.x / s, v.y / s, v.z / s};
}
[[nodiscard]] inline float dot(Vec3 a, Vec3 b) noexcept {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}
[[nodiscard]] inline Vec3 cross(Vec3 a, Vec3 b) noexcept {
    return {
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    };
}
[[nodiscard]] inline float length(Vec3 v) noexcept { return std::sqrt(dot(v, v)); }
[[nodiscard]] inline Vec3 normalize(Vec3 v) noexcept {
    const float len = length(v);
    return len > 0.0F ? v / len : Vec3{};
}

struct Ray {
    Vec3 origin{};
    Vec3 direction{}; // Contract boundary normalizes this to preserve world-distance t.
    float t_max{};
};

struct Triangle {
    Vec3 v0{};
    Vec3 v1{};
    Vec3 v2{};
    std::uint32_t primitive_id{kInvalidId};
    std::uint32_t material_id{kInvalidId};
    std::uint32_t instance_id{kInvalidId};
    bool two_sided{true};
};

struct Hit {
    bool hit{false};
    float t{std::numeric_limits<float>::infinity()};
    Vec3 normal{}; // World-space geometric normal; never face-forwarded.
    std::uint32_t primitive_id{kInvalidId};
    std::uint32_t material_id{kInvalidId};
    std::uint32_t instance_id{kInvalidId};
};

// B001 semantic contract:
// - finite, non-zero direction is normalized at the contract boundary;
// - t is world-space distance and the closest hit in [kRayTMin, t_max];
// - per-primitive two_sided controls back-face acceptance;
// - ties inside the distance tolerance choose the lower primitive_id;
// - misses use +INF and kInvalidId sentinels;
// - material/instance/primitive identity are part of correctness, not optional metadata.
[[nodiscard]] Hit trace_reference(std::span<const Triangle> triangles, Ray ray);
[[nodiscard]] bool equivalent_hit(const Hit& expected, const Hit& actual) noexcept;

} // namespace phos::gi::research::lane_b

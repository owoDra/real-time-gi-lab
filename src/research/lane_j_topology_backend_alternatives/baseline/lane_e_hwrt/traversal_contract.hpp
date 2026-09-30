#pragma once

#include <cstdint>
#include <limits>

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

struct Ray {
    Vec3 origin{};
    Vec3 direction{};
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
    Vec3 normal{};
    std::uint32_t primitive_id{kInvalidId};
    std::uint32_t material_id{kInvalidId};
    std::uint32_t instance_id{kInvalidId};
};

} // namespace phos::gi::research::lane_b

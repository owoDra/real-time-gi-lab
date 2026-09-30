#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace phos::gi::research::lane_j {

constexpr std::uint32_t kInvalidId = 0xffffffffU;
constexpr float kRayTMin = 1.0e-4F;
constexpr float kHitAbsTol = 2.0e-4F;
constexpr float kHitRelTol = 2.0e-5F;
constexpr std::uint32_t kClusterTarget = 48U;
constexpr std::uint32_t kClusterMaximum = 64U;
constexpr std::uint32_t kClusterMergeBelow = 24U;

struct Vec3 {
    float x{};
    float y{};
    float z{};
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

struct Aabb {
    Vec3 min{
        std::numeric_limits<float>::infinity(),
        std::numeric_limits<float>::infinity(),
        std::numeric_limits<float>::infinity(),
    };
    Vec3 max{
        -std::numeric_limits<float>::infinity(),
        -std::numeric_limits<float>::infinity(),
        -std::numeric_limits<float>::infinity(),
    };
};

struct alignas(16) GpuTriangle {
    std::array<float, 4> v0{};
    std::array<float, 4> v1{};
    std::array<float, 4> v2{};
    std::array<std::uint32_t, 4> meta{};
};
static_assert(sizeof(GpuTriangle) == 64);

struct alignas(16) GpuBvhNode {
    std::array<float, 4> bounds_min{};
    std::array<float, 4> bounds_max{};
    // x=left, y=right, z=leaf payload, w=leaf count.
    std::array<std::uint32_t, 4> meta{};
};
static_assert(sizeof(GpuBvhNode) == 48);

struct alignas(16) GpuCluster {
    std::array<float, 4> bounds_min{};
    std::array<float, 4> bounds_max{};
    // x=micro root, y=stable cluster id, z=primitive count, w=reserved.
    std::array<std::uint32_t, 4> meta{};
};
static_assert(sizeof(GpuCluster) == 48);

struct alignas(16) GpuRay {
    // origin.xyz, t_max
    std::array<float, 4> origin_tmax{};
    // direction.xyz, reserved
    std::array<float, 4> direction{};
};
static_assert(sizeof(GpuRay) == 32);

struct alignas(16) GpuHit {
    // t, normal.xyz
    std::array<float, 4> t_normal{};
    // primitive id, material id, instance id, hit flag
    std::array<std::uint32_t, 4> ids{};
    // upper node visits, micro node visits, exact triangle tests, runtime error
    std::array<std::uint32_t, 4> stats{};
    // Validation-only watched-primitive diagnostics:
    // x=flags, y=candidate t bits, z=current t bits, w=current primitive id.
    // flags: bit0 leaf/test reached, bit1 intersect accepted,
    // bit2 prefer accepted, bit3 current hit existed before candidate.
    std::array<std::uint32_t, 4> debug{};
};
static_assert(sizeof(GpuHit) == 64);

struct Ray {
    Vec3 origin{};
    Vec3 direction{};
    float t_max{};
};

struct Hit {
    bool hit{false};
    float t{std::numeric_limits<float>::infinity()};
    Vec3 normal{};
    std::uint32_t primitive_id{kInvalidId};
    std::uint32_t material_id{kInvalidId};
    std::uint32_t instance_id{kInvalidId};
};

} // namespace phos::gi::research::lane_j

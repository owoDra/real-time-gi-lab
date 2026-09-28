#pragma once

#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace phos::gi::lane_a {

inline constexpr std::uint32_t kStreamSchemaVersion = 1;
inline constexpr std::uint32_t kWorkItemValid = 1u << 0u;

struct alignas(16) SurfaceSampleGpu {
    float position[4]{};
    float normal[4]{};
};
static_assert(sizeof(SurfaceSampleGpu) == 32);
static_assert(std::is_standard_layout_v<SurfaceSampleGpu>);

struct alignas(16) ConfigGpu {
    float eye[4]{};
    float right[4]{};
    float up[4]{};
    float forward[4]{};

    // x=tan(fov_y/2), y=aspect, z=near, w=far
    float camera[4]{};

    // x=tile width, y=tile height, z=surface count, w=frame id
    std::uint32_t grid[4]{};

    // x=cascade count, y=rays/probe, z=work-item count, w=output count
    std::uint32_t rc[4]{};

    // x=first interval end, y=interval scale, z=origin bias, w=light intensity
    float rc_params[4]{};

    // xyz=light position, w=sky intensity
    float light[4]{};
};
static_assert(sizeof(ConfigGpu) == 144);
static_assert(std::is_standard_layout_v<ConfigGpu>);

// Versioned replay record. Its byte layout is part of the Lane A -> Lane B/C
// contract. Do not reorder fields in schema version 1.
struct alignas(16) WorkItemV1 {
    std::uint32_t frame_id{};
    std::uint32_t probe_id{};
    std::uint32_t cascade{};
    std::uint32_t ray_index{};

    float origin_x{};
    float origin_y{};
    float origin_z{};
    float t_min{};

    float direction_x{};
    float direction_y{};
    float direction_z{};
    float t_max{};

    std::uint32_t output_id{};
    std::uint32_t surface_id{};
    std::uint32_t tile_id{};
    std::uint32_t flags{};
};
static_assert(sizeof(WorkItemV1) == 64);
static_assert(offsetof(WorkItemV1, origin_x) == 16);
static_assert(offsetof(WorkItemV1, direction_x) == 32);
static_assert(offsetof(WorkItemV1, output_id) == 48);
static_assert(std::is_standard_layout_v<WorkItemV1>);

struct alignas(16) RadianceGpu {
    float r{};
    float g{};
    float b{};
    float a{};
};
static_assert(sizeof(RadianceGpu) == 16);

} // namespace phos::gi::lane_a

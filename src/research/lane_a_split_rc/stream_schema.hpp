#pragma once
#include <array>
#include <cstdint>
#include <type_traits>

namespace phos::gi::lane_a {

inline constexpr std::uint32_t kSplitRcStreamSchemaVersion = 1;
inline constexpr std::array<char, 8> kSplitRcStreamMagic{'P', 'H', 'O', 'S', 'R', 'C', '1', '\0'};

struct SplitRcStreamHeaderV1 {
    std::array<char, 8> magic{kSplitRcStreamMagic};
    std::uint32_t schema_version{kSplitRcStreamSchemaVersion};
    std::uint32_t header_bytes{64};
    std::uint32_t item_bytes{};
    std::uint32_t frame_id{};
    std::uint32_t item_count{};
    std::uint32_t output_count{};
    std::uint32_t cascade_count{};
    std::uint32_t rays_per_probe{};
    std::uint32_t tile_width{};
    std::uint32_t tile_height{};
    std::uint32_t reserved0{};
    std::uint64_t workload_id{};
};

struct SplitRcWorkItemV1 {
    std::int32_t probe_x{};
    std::int32_t probe_y{};
    std::int32_t probe_z{};
    std::uint32_t cascade{};
    std::uint32_t ray_index{};
    std::uint32_t output_id{};
    std::uint32_t surface_id{};
    std::uint32_t tile_id{};
    float interval_min{};
    float interval_max{};
    float dir_x{};
    float dir_y{};
    float dir_z{};
    float probe_px{};
    float probe_py{};
    float probe_pz{};
};

static_assert(std::is_standard_layout_v<SplitRcStreamHeaderV1>);
static_assert(std::is_trivially_copyable_v<SplitRcStreamHeaderV1>);
static_assert(sizeof(SplitRcStreamHeaderV1) == 64);
static_assert(std::is_standard_layout_v<SplitRcWorkItemV1>);
static_assert(std::is_trivially_copyable_v<SplitRcWorkItemV1>);
static_assert(sizeof(SplitRcWorkItemV1) == 64);

} // namespace phos::gi::lane_a

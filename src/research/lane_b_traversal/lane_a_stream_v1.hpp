#pragma once

#include "traversal_contract.hpp"

#include <array>
#include <bit>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <vector>

namespace phos::gi::research::lane_b {

inline constexpr std::uint32_t kLaneAStreamSchemaVersion = 1;
inline constexpr std::array<char, 8> kLaneAStreamMagic{
    'P', 'H', 'O', 'S', 'R', 'C', '1', '\0'};

// ABI mirror of Lane A commit 8b647ef8.../stream_schema.hpp. Lane B owns this
// reader so it can consume the accepted stream without editing Lane A's branch.
// Any layout change in Lane A requires a new schema version rather than silent
// reinterpretation here.
struct LaneAStreamHeaderV1 {
    std::array<char, 8> magic{kLaneAStreamMagic};
    std::uint32_t schema_version{kLaneAStreamSchemaVersion};
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

struct LaneAWorkItemV1 {
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

static_assert(std::is_standard_layout_v<LaneAStreamHeaderV1>);
static_assert(std::is_trivially_copyable_v<LaneAStreamHeaderV1>);
static_assert(sizeof(LaneAStreamHeaderV1) == 64);
static_assert(offsetof(LaneAStreamHeaderV1, workload_id) == 56);
static_assert(std::is_standard_layout_v<LaneAWorkItemV1>);
static_assert(std::is_trivially_copyable_v<LaneAWorkItemV1>);
static_assert(sizeof(LaneAWorkItemV1) == 64);
static_assert(offsetof(LaneAWorkItemV1, cascade) == 12);
static_assert(offsetof(LaneAWorkItemV1, output_id) == 20);
static_assert(offsetof(LaneAWorkItemV1, interval_min) == 32);
static_assert(offsetof(LaneAWorkItemV1, dir_x) == 40);
static_assert(offsetof(LaneAWorkItemV1, probe_px) == 52);

struct LaneAReplayStreamV1 {
    LaneAStreamHeaderV1 header{};
    std::vector<LaneAWorkItemV1> items;
};

[[nodiscard]] inline std::uint64_t lane_a_workload_id(
    const void* data,
    std::size_t bytes) noexcept {
    // This intentionally matches A001's accepted exporter byte-for-byte. The
    // offset basis differs from canonical FNV-1a, so do not "correct" it here.
    const auto* ptr = static_cast<const unsigned char*>(data);
    std::uint64_t hash = 1469598103934665603ull;
    for (std::size_t index = 0; index < bytes; ++index) {
        hash ^= ptr[index];
        hash *= 1099511628211ull;
    }
    return hash;
}

[[nodiscard]] inline LaneAReplayStreamV1 load_lane_a_stream_v1(
    const std::filesystem::path& path) {
    if constexpr (std::endian::native != std::endian::little) {
        throw std::runtime_error("Lane A stream v1 requires a little-endian host");
    }

    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) {
        throw std::runtime_error("Cannot open Lane A stream: " + path.string());
    }
    const auto size = static_cast<std::uint64_t>(input.tellg());
    if (size < sizeof(LaneAStreamHeaderV1)) {
        throw std::runtime_error("Lane A stream is smaller than the v1 header");
    }
    input.seekg(0);

    LaneAReplayStreamV1 stream;
    input.read(reinterpret_cast<char*>(&stream.header), sizeof(stream.header));
    if (!input) {
        throw std::runtime_error("Could not read Lane A stream header");
    }

    const auto& header = stream.header;
    if (header.magic != kLaneAStreamMagic ||
        header.schema_version != kLaneAStreamSchemaVersion ||
        header.header_bytes != sizeof(LaneAStreamHeaderV1) ||
        header.item_bytes != sizeof(LaneAWorkItemV1)) {
        throw std::runtime_error("Lane A stream v1 header/layout mismatch");
    }
    if (header.reserved0 != 0 || header.cascade_count == 0 ||
        header.rays_per_probe == 0 || header.tile_width == 0 ||
        header.tile_height == 0) {
        throw std::runtime_error("Lane A stream v1 header contains invalid dimensions");
    }

    const std::uint64_t expected_size =
        std::uint64_t(header.header_bytes) +
        std::uint64_t(header.item_count) * header.item_bytes;
    if (size != expected_size) {
        throw std::runtime_error("Lane A stream byte size does not match header");
    }

    stream.items.resize(header.item_count);
    input.read(
        reinterpret_cast<char*>(stream.items.data()),
        static_cast<std::streamsize>(stream.items.size() * sizeof(LaneAWorkItemV1)));
    if (!input) {
        throw std::runtime_error("Could not read all Lane A work items");
    }

    const auto actual_id = lane_a_workload_id(
        stream.items.data(),
        stream.items.size() * sizeof(LaneAWorkItemV1));
    if (actual_id != header.workload_id) {
        throw std::runtime_error("Lane A workload_id mismatch; stream is corrupted or reordered");
    }

    return stream;
}

[[nodiscard]] inline Ray lane_a_item_to_ray(const LaneAWorkItemV1& item) {
    const Vec3 raw_direction{item.dir_x, item.dir_y, item.dir_z};
    const float direction_length = length(raw_direction);
    if (!std::isfinite(direction_length) || direction_length <= 1.0e-8F ||
        !std::isfinite(item.interval_min) || !std::isfinite(item.interval_max) ||
        item.interval_min < 0.0F || item.interval_max <= item.interval_min) {
        throw std::runtime_error("Lane A work item has invalid ray interval semantics");
    }

    const Vec3 direction = raw_direction / direction_length;
    const Vec3 probe{item.probe_px, item.probe_py, item.probe_pz};
    return {
        probe + direction * item.interval_min,
        direction,
        item.interval_max - item.interval_min,
    };
}

[[nodiscard]] inline std::vector<Ray> lane_a_replay_rays(
    const LaneAReplayStreamV1& stream) {
    std::vector<Ray> rays;
    rays.reserve(stream.items.size());
    for (const auto& item : stream.items) {
        rays.push_back(lane_a_item_to_ray(item));
    }
    return rays;
}

} // namespace phos::gi::research::lane_b

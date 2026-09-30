#pragma once

#include "b002_scene.hpp"
#include "lane_a_stream_v1.hpp"

#include <array>
#include <filesystem>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace phos::gi::research::lane_b {

inline constexpr std::array<std::string_view, 3> kB002Cases{
    "static",
    "camera-motion",
    "light-motion",
};

struct B002ReplayCase {
    std::string_view name;
    LaneAReplayStreamV1 stream;
    std::vector<Ray> rays;
};

[[nodiscard]] inline B002ReplayCase load_b002_replay_case(
    const std::filesystem::path& artifact_root,
    std::string_view case_name,
    const B002Scene& scene) {
    const auto path =
        artifact_root / std::string(case_name) / "stream-v1.bin";
    auto stream = load_lane_a_stream_v1(path);

    for (const auto& item : stream.items) {
        if (item.surface_id >= scene.triangles.size()) {
            throw std::runtime_error(
                "Lane A surface_id is not aligned with B002 scene triangle order");
        }
        if (scene.triangles[item.surface_id].primitive_id != item.surface_id) {
            throw std::runtime_error(
                "B002 primitive identity no longer matches Lane A surface identity");
        }
    }

    auto rays = lane_a_replay_rays(stream);
    if (rays.size() != stream.header.item_count) {
        throw std::runtime_error("B002 replay conversion changed item count");
    }
    return {case_name, std::move(stream), std::move(rays)};
}

} // namespace phos::gi::research::lane_b

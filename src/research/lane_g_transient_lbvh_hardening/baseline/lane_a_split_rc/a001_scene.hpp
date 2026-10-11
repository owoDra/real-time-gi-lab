#pragma once

#include "a001_types.hpp"

#include <cstddef>
#include <filesystem>
#include <vector>

namespace phos::gi::lane_a {

struct SceneSurfaceSet {
    std::vector<SurfaceSampleGpu> samples;
    float min_position[3]{};
    float max_position[3]{};
};

SceneSurfaceSet load_scene_surface_samples(const std::filesystem::path& scene_path);
SceneSurfaceSet make_synthetic_surface_samples(std::size_t count);

} // namespace phos::gi::lane_a

#pragma once

#include "traversal_common.hpp"

#include <filesystem>
#include <vector>

namespace phos::gi::research::lane_b {

struct B002Scene {
    std::vector<Triangle> triangles;
    Aabb bounds{};
    float diagonal{};
};

// Load the same raw-mesh coordinate space consumed by A001. A001 intentionally
// did not apply node transforms, so B002 mirrors that accepted producer space
// rather than silently changing the geometry under the replay stream.
//
// Non-degenerate triangles are kept in the same mesh/primitive/index order as
// A001 surface samples. Consequently primitive_id is also the A001 surface_id
// for the accepted Sponza producer.
[[nodiscard]] B002Scene load_b002_scene(
    const std::filesystem::path& scene_path);

[[nodiscard]] float b002_segment_size(const B002Scene& scene);

} // namespace phos::gi::research::lane_b

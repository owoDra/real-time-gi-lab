#pragma once
#include "types.hpp"
#include <cstddef>
#include <filesystem>
#include <vector>

namespace phos::gi {

std::vector<Vec3> load_surface_points(const std::filesystem::path& scene_path);
std::vector<Vec3> make_synthetic_surface_points(std::size_t count);
Workload build_workload(const std::vector<Vec3>& points, std::size_t query_count);

} // namespace phos::gi

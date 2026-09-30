#include "a001_scene.hpp"

#include <fastgltf/core.hpp>
#include <fastgltf/tools.hpp>
#include <fastgltf/types.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

namespace phos::gi::lane_a {
namespace {

struct Float3 { float x, y, z; };

Float3 sub(Float3 a, Float3 b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
Float3 cross(Float3 a, Float3 b) {
    return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}
float length(Float3 v) { return std::sqrt(v.x * v.x + v.y * v.y + v.z * v.z); }
Float3 normalize(Float3 v) {
    const float len = length(v);
    if (len <= 1e-12f) return {};
    return {v.x / len, v.y / len, v.z / len};
}

void include_position(SceneSurfaceSet& out, Float3 p) {
    for (int axis = 0; axis < 3; ++axis) {
        const float value = axis == 0 ? p.x : axis == 1 ? p.y : p.z;
        out.min_position[axis] = std::min(out.min_position[axis], value);
        out.max_position[axis] = std::max(out.max_position[axis], value);
    }
}

SceneSurfaceSet begin_set() {
    SceneSurfaceSet out;
    for (int axis = 0; axis < 3; ++axis) {
        out.min_position[axis] = std::numeric_limits<float>::infinity();
        out.max_position[axis] = -std::numeric_limits<float>::infinity();
    }
    return out;
}

} // namespace

SceneSurfaceSet load_scene_surface_samples(const std::filesystem::path& scene_path) {
    fastgltf::Parser parser;
    auto data = fastgltf::GltfDataBuffer::FromPath(scene_path);
    if (data.error() != fastgltf::Error::None) {
        throw std::runtime_error("Could not read glTF: " + scene_path.string());
    }

    constexpr auto options = fastgltf::Options::LoadExternalBuffers |
                             fastgltf::Options::GenerateMeshIndices;
    auto asset_result = parser.loadGltf(data.get(), scene_path.parent_path(), options);
    if (asset_result.error() != fastgltf::Error::None) {
        throw std::runtime_error("Could not parse glTF scene");
    }
    auto& asset = asset_result.get();

    auto out = begin_set();
    for (const auto& mesh : asset.meshes) {
        for (const auto& primitive : mesh.primitives) {
            const auto position_it = primitive.findAttribute("POSITION");
            if (position_it == primitive.attributes.end() || !primitive.indicesAccessor.has_value()) {
                continue;
            }

            const auto& position_accessor = asset.accessors[position_it->accessorIndex];
            std::vector<fastgltf::math::fvec3> positions(position_accessor.count);
            fastgltf::iterateAccessorWithIndex<fastgltf::math::fvec3>(
                asset, position_accessor,
                [&](fastgltf::math::fvec3 p, std::size_t i) { positions[i] = p; });

            const auto& index_accessor = asset.accessors[primitive.indicesAccessor.value()];
            std::vector<std::uint32_t> indices(index_accessor.count);
            fastgltf::iterateAccessorWithIndex<std::uint32_t>(
                asset, index_accessor,
                [&](std::uint32_t value, std::size_t i) { indices[i] = value; });

            for (std::size_t i = 0; i + 2 < indices.size(); i += 3) {
                const auto av = positions.at(indices[i]);
                const auto bv = positions.at(indices[i + 1]);
                const auto cv = positions.at(indices[i + 2]);
                const Float3 a{av.x(), av.y(), av.z()};
                const Float3 b{bv.x(), bv.y(), bv.z()};
                const Float3 c{cv.x(), cv.y(), cv.z()};
                const auto n = normalize(cross(sub(b, a), sub(c, a)));
                if (length(n) <= 0.5f) continue;
                const Float3 center{
                    (a.x + b.x + c.x) / 3.0f,
                    (a.y + b.y + c.y) / 3.0f,
                    (a.z + b.z + c.z) / 3.0f,
                };
                SurfaceSampleGpu sample{};
                sample.position[0] = center.x;
                sample.position[1] = center.y;
                sample.position[2] = center.z;
                sample.position[3] = 1.0f;
                sample.normal[0] = n.x;
                sample.normal[1] = n.y;
                sample.normal[2] = n.z;
                out.samples.push_back(sample);
                include_position(out, center);
            }
        }
    }

    if (out.samples.empty()) {
        throw std::runtime_error("No non-degenerate triangle surface samples found in scene");
    }
    return out;
}

SceneSurfaceSet make_synthetic_surface_samples(std::size_t count) {
    if (count == 0) throw std::runtime_error("Synthetic surface count must be positive");
    auto out = begin_set();
    out.samples.reserve(count);
    for (std::size_t i = 0; i < count; ++i) {
        const float x = (static_cast<float>(i % 512u) - 256.0f) * 0.08f;
        const float z = (static_cast<float>((i / 512u) % 512u) - 256.0f) * 0.08f;
        const float y = std::sin(x * 0.17f) * 0.7f + std::cos(z * 0.13f) * 0.5f;
        SurfaceSampleGpu sample{};
        sample.position[0] = x;
        sample.position[1] = y;
        sample.position[2] = z;
        sample.position[3] = 1.0f;
        sample.normal[1] = 1.0f;
        out.samples.push_back(sample);
        include_position(out, {x, y, z});
    }
    return out;
}

} // namespace phos::gi::lane_a

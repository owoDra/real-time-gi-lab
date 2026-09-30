#include "b002_scene.hpp"

#include <fastgltf/core.hpp>
#include <fastgltf/tools.hpp>
#include <fastgltf/types.hpp>

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::lane_b {
namespace {

[[nodiscard]] Vec3 to_vec3(fastgltf::math::fvec3 value) noexcept {
    return {value.x(), value.y(), value.z()};
}

[[nodiscard]] bool non_degenerate(Vec3 a, Vec3 b, Vec3 c) noexcept {
    // A001's exporter normalizes the cross product and rejects the zero vector.
    // Testing the pre-normalized length against the same practical epsilon
    // preserves the same accepted triangle order without introducing NaNs.
    return length(cross(b - a, c - a)) > 1.0e-12F;
}

} // namespace

B002Scene load_b002_scene(const std::filesystem::path& scene_path) {
    fastgltf::Parser parser;
    auto data = fastgltf::GltfDataBuffer::FromPath(scene_path);
    if (data.error() != fastgltf::Error::None) {
        throw std::runtime_error("Could not read B002 glTF: " + scene_path.string());
    }

    constexpr auto options =
        fastgltf::Options::LoadExternalBuffers |
        fastgltf::Options::GenerateMeshIndices;
    auto asset_result = parser.loadGltf(data.get(), scene_path.parent_path(), options);
    if (asset_result.error() != fastgltf::Error::None) {
        throw std::runtime_error("Could not parse B002 glTF scene");
    }
    auto& asset = asset_result.get();

    B002Scene scene;
    for (std::size_t mesh_index = 0; mesh_index < asset.meshes.size(); ++mesh_index) {
        const auto& mesh = asset.meshes[mesh_index];
        if (mesh_index > std::numeric_limits<std::uint32_t>::max()) {
            throw std::runtime_error("B002 mesh index exceeds 32-bit instance identity");
        }

        for (const auto& primitive : mesh.primitives) {
            const auto position_it = primitive.findAttribute("POSITION");
            if (position_it == primitive.attributes.end() ||
                !primitive.indicesAccessor.has_value()) {
                continue;
            }

            const auto& position_accessor =
                asset.accessors[position_it->accessorIndex];
            std::vector<fastgltf::math::fvec3> positions(position_accessor.count);
            fastgltf::iterateAccessorWithIndex<fastgltf::math::fvec3>(
                asset,
                position_accessor,
                [&](fastgltf::math::fvec3 position, std::size_t index) {
                    positions[index] = position;
                });

            const auto& index_accessor =
                asset.accessors[primitive.indicesAccessor.value()];
            std::vector<std::uint32_t> indices(index_accessor.count);
            fastgltf::iterateAccessorWithIndex<std::uint32_t>(
                asset,
                index_accessor,
                [&](std::uint32_t value, std::size_t index) {
                    indices[index] = value;
                });

            std::uint32_t material_id = kInvalidId;
            bool two_sided = false;
            if (primitive.materialIndex.has_value()) {
                const auto value = primitive.materialIndex.value();
                if (value > std::numeric_limits<std::uint32_t>::max()) {
                    throw std::runtime_error(
                        "B002 material index exceeds 32-bit identity");
                }
                if (value >= asset.materials.size()) {
                    throw std::runtime_error(
                        "B002 primitive references an invalid material");
                }
                material_id = static_cast<std::uint32_t>(value);
                two_sided = asset.materials[value].doubleSided;
            }

            for (std::size_t index = 0; index + 2 < indices.size(); index += 3) {
                const auto a = to_vec3(positions.at(indices[index]));
                const auto b = to_vec3(positions.at(indices[index + 1]));
                const auto c = to_vec3(positions.at(indices[index + 2]));
                if (!non_degenerate(a, b, c)) continue;

                if (scene.triangles.size() >=
                    std::numeric_limits<std::uint32_t>::max()) {
                    throw std::runtime_error(
                        "B002 primitive identity exceeds 32-bit capacity");
                }

                const auto primitive_id =
                    static_cast<std::uint32_t>(scene.triangles.size());
                scene.triangles.push_back({
                    a,
                    b,
                    c,
                    primitive_id,
                    material_id,
                    static_cast<std::uint32_t>(mesh_index),
                    two_sided,
                });
                scene.bounds = merge(scene.bounds, triangle_bounds(scene.triangles.back()));
            }
        }
    }

    if (scene.triangles.empty()) {
        throw std::runtime_error("B002 scene has no non-degenerate triangles");
    }
    scene.diagonal = length(scene.bounds.max - scene.bounds.min);
    if (!std::isfinite(scene.diagonal) || scene.diagonal <= 0.0F) {
        throw std::runtime_error("B002 scene has invalid bounds");
    }
    return scene;
}

float b002_segment_size(const B002Scene& scene) {
    // A001 uses finest probe spacing scene_diagonal / 64. Four such cells form
    // the Lane B segment. This fixes hierarchy granularity from the producer's
    // own spatial scale instead of tuning it after seeing candidate timings.
    return scene.diagonal / 16.0F;
}

} // namespace phos::gi::research::lane_b

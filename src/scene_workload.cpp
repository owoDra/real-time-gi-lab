#include "scene_workload.hpp"

#include <fastgltf/core.hpp>
#include <fastgltf/tools.hpp>
#include <fastgltf/types.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <unordered_map>

namespace phos::gi {
namespace {

struct Cell { int x, y, z; };

std::uint32_t mix32(std::uint32_t x) {
    x ^= x >> 16;
    x *= 0x7feb352du;
    x ^= x >> 15;
    x *= 0x846ca68bu;
    x ^= x >> 16;
    return x ? x : 1u;
}

std::uint64_t pack_signed_21(int x, int y, int z) {
    constexpr std::uint64_t mask = (1ull << 21) - 1ull;
    const auto ux = static_cast<std::uint64_t>(static_cast<std::uint32_t>(x)) & mask;
    const auto uy = static_cast<std::uint64_t>(static_cast<std::uint32_t>(y)) & mask;
    const auto uz = static_cast<std::uint64_t>(static_cast<std::uint32_t>(z)) & mask;
    return ux | (uy << 21) | (uz << 42);
}

std::uint32_t local_index_4(Cell c) {
    const auto m = [](int v) -> std::uint32_t { return static_cast<std::uint32_t>(v & 3); };
    return m(c.x) | (m(c.y) << 2u) | (m(c.z) << 4u);
}

std::uint64_t page_key(Cell c) {
    auto floor_div4 = [](int v) {
        int q = v / 4;
        int r = v % 4;
        if (r < 0) --q;
        return q;
    };
    return pack_signed_21(floor_div4(c.x), floor_div4(c.y), floor_div4(c.z));
}

Cell quantize(Vec3 p) {
    constexpr float cell = 0.25f;
    return {static_cast<int>(std::floor(p.x / cell)),
            static_cast<int>(std::floor(p.y / cell)),
            static_cast<int>(std::floor(p.z / cell))};
}

std::uint32_t next_pow2(std::uint32_t v) {
    if (v <= 1) return 1;
    --v;
    v |= v >> 1; v |= v >> 2; v |= v >> 4; v |= v >> 8; v |= v >> 16;
    return v + 1;
}

} // namespace

std::vector<Vec3> load_surface_points(const std::filesystem::path& scene_path) {
    fastgltf::Parser parser;
    auto data = fastgltf::GltfDataBuffer::FromPath(scene_path);
    if (data.error() != fastgltf::Error::None) throw std::runtime_error("Could not read glTF: " + scene_path.string());

    constexpr auto options = fastgltf::Options::LoadExternalBuffers | fastgltf::Options::GenerateMeshIndices;
    auto asset_result = parser.loadGltf(data.get(), scene_path.parent_path(), options);
    if (asset_result.error() != fastgltf::Error::None) throw std::runtime_error("Could not parse glTF");
    auto& asset = asset_result.get();

    std::vector<Vec3> points;
    for (const auto& mesh : asset.meshes) {
        for (const auto& primitive : mesh.primitives) {
            auto pos_it = primitive.findAttribute("POSITION");
            if (pos_it == primitive.attributes.end()) continue;
            const auto& position_accessor = asset.accessors[pos_it->accessorIndex];
            std::vector<fastgltf::math::fvec3> positions(position_accessor.count);
            fastgltf::iterateAccessorWithIndex<fastgltf::math::fvec3>(asset, position_accessor,
                [&](fastgltf::math::fvec3 p, std::size_t i) { positions[i] = p; });

            if (!primitive.indicesAccessor.has_value()) continue;
            const auto& index_accessor = asset.accessors[primitive.indicesAccessor.value()];
            std::vector<std::uint32_t> indices(index_accessor.count);
            fastgltf::iterateAccessorWithIndex<std::uint32_t>(asset, index_accessor,
                [&](std::uint32_t v, std::size_t i) { indices[i] = v; });

            for (std::size_t i = 0; i + 2 < indices.size(); i += 3) {
                const auto a = positions.at(indices[i]);
                const auto b = positions.at(indices[i + 1]);
                const auto c = positions.at(indices[i + 2]);
                points.push_back({(a.x() + b.x() + c.x()) / 3.0f,
                                  (a.y() + b.y() + c.y()) / 3.0f,
                                  (a.z() + b.z() + c.z()) / 3.0f});
            }
        }
    }
    if (points.empty()) throw std::runtime_error("No triangle surface points found in scene");
    return points;
}

std::vector<Vec3> make_synthetic_surface_points(std::size_t count) {
    std::vector<Vec3> out;
    out.reserve(count);
    for (std::size_t i = 0; i < count; ++i) {
        const float x = static_cast<float>(i % 1024) * 0.07f;
        const float z = static_cast<float>((i / 1024) % 1024) * 0.07f;
        const float y = std::sin(x * 0.1f) * 2.0f + std::cos(z * 0.13f);
        out.push_back({x, y, z});
    }
    return out;
}

Workload build_workload(const std::vector<Vec3>& points, std::size_t query_count) {
    if (points.empty() || query_count == 0) throw std::runtime_error("Workload requires points and queries");

    Workload w;
    w.original.reserve(query_count);
    std::unordered_map<std::uint64_t, std::uint32_t> page_ids;
    page_ids.reserve(points.size() / 8 + 1);

    for (std::size_t i = 0; i < query_count; ++i) {
        const auto& p = points[(i * 2654435761ull) % points.size()];
        const auto c = quantize(p);
        const auto pk = page_key(c);
        auto [it, inserted] = page_ids.try_emplace(pk, static_cast<std::uint32_t>(page_ids.size()));
        const std::uint32_t page = it->second;
        const std::uint32_t local = local_index_4(c);
        const std::uint32_t key = mix32(static_cast<std::uint32_t>(pk) ^ static_cast<std::uint32_t>(pk >> 32) ^ local * 0x9e3779b9u);
        w.original.push_back({key, page, local, 0});
    }

    w.page_sorted = w.original;
    std::stable_sort(w.page_sorted.begin(), w.page_sorted.end(), [](const Query& a, const Query& b) {
        return a.page_id < b.page_id || (a.page_id == b.page_id && a.local_index < b.local_index);
    });

    const std::uint32_t page_count = static_cast<std::uint32_t>(page_ids.size());
    w.page_table.resize(page_count);
    w.paged_payload.resize(static_cast<std::size_t>(page_count) * w.page_size);
    for (std::uint32_t page = 0; page < page_count; ++page) {
        w.page_table[page] = page * w.page_size;
        for (std::uint32_t local = 0; local < w.page_size; ++local) {
            w.paged_payload[static_cast<std::size_t>(page) * w.page_size + local] = mix32(page * 1315423911u ^ local);
        }
    }

    const std::uint32_t table_size = next_pow2(std::max<std::uint32_t>(1024u, page_count * w.page_size * 2u));
    w.hash_mask = table_size - 1u;
    w.hash_keys.assign(table_size, 0u);
    w.hash_payload.assign(table_size, 0u);

    for (const auto& q : w.original) {
        std::uint32_t slot = mix32(q.key) & w.hash_mask;
        while (w.hash_keys[slot] != 0u && w.hash_keys[slot] != q.key) slot = (slot + 1u) & w.hash_mask;
        w.hash_keys[slot] = q.key;
        w.hash_payload[slot] = mix32(q.key ^ 0x51ed270bu);
    }
    return w;
}

} // namespace phos::gi

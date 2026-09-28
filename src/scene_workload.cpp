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
#include <unordered_set>

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
        const int r = v % 4;
        if (r < 0) --q;
        return q;
    };
    return pack_signed_21(floor_div4(c.x), floor_div4(c.y), floor_div4(c.z));
}

Cell quantize(Vec3 p) {
    constexpr float cell = 0.25f;
    return {
        static_cast<int>(std::floor(p.x / cell)),
        static_cast<int>(std::floor(p.y / cell)),
        static_cast<int>(std::floor(p.z / cell)),
    };
}

std::uint32_t table_size_for(std::size_t active_cells) {
    // M0 fixes the hash competitor at <= 0.5 load factor. Size from actual
    // active cells, not from page capacity, so inactive page slots do not
    // artificially inflate the hash baseline.
    const std::uint64_t target =
        std::max<std::uint64_t>(1024u, static_cast<std::uint64_t>(active_cells) * 2u);
    std::uint64_t size = 1;
    while (size < target) size <<= 1u;
    if (size > std::numeric_limits<std::uint32_t>::max()) {
        throw std::runtime_error("Hash workload exceeds 32-bit table capacity");
    }
    return static_cast<std::uint32_t>(size);
}

std::uint32_t semantic_payload(std::uint32_t page, std::uint32_t local) {
    return mix32(page * 1315423911u ^ local);
}

std::uint32_t hash_lookup_cpu(const Workload& w, std::uint32_t key) {
    std::uint32_t slot = mix32(key) & w.hash_mask;
    for (std::uint32_t probe = 0; probe < w.hash_max_probe; ++probe) {
        const auto candidate = w.hash_keys[slot];
        if (candidate == key) return w.hash_payload[slot];
        if (candidate == 0u) return 0u;
        slot = (slot + 1u) & w.hash_mask;
    }
    return 0u;
}

void validate_semantic_equivalence(Workload& w) {
    std::uint64_t checksum = 0;
    for (const auto& q : w.original) {
        const auto base = w.page_table.at(q.page_id);
        const auto expected = w.paged_payload.at(static_cast<std::size_t>(base) + q.local_index);
        const auto hashed = hash_lookup_cpu(w, q.key);
        if (hashed != expected) {
            throw std::runtime_error("CPU correctness guard: hash and paged payloads diverged");
        }
        checksum += expected;
    }
    w.expected_checksum = checksum;
}

} // namespace

std::vector<Vec3> load_surface_points(const std::filesystem::path& scene_path) {
    fastgltf::Parser parser;
    auto data = fastgltf::GltfDataBuffer::FromPath(scene_path);
    if (data.error() != fastgltf::Error::None) {
        throw std::runtime_error("Could not read glTF: " + scene_path.string());
    }

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
            fastgltf::iterateAccessorWithIndex<fastgltf::math::fvec3>(
                asset, position_accessor,
                [&](fastgltf::math::fvec3 p, std::size_t i) { positions[i] = p; });

            if (!primitive.indicesAccessor.has_value()) continue;
            const auto& index_accessor = asset.accessors[primitive.indicesAccessor.value()];
            std::vector<std::uint32_t> indices(index_accessor.count);
            fastgltf::iterateAccessorWithIndex<std::uint32_t>(
                asset, index_accessor,
                [&](std::uint32_t v, std::size_t i) { indices[i] = v; });

            for (std::size_t i = 0; i + 2 < indices.size(); i += 3) {
                const auto a = positions.at(indices[i]);
                const auto b = positions.at(indices[i + 1]);
                const auto c = positions.at(indices[i + 2]);
                points.push_back({
                    (a.x() + b.x() + c.x()) / 3.0f,
                    (a.y() + b.y() + c.y()) / 3.0f,
                    (a.z() + b.z() + c.z()) / 3.0f,
                });
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
    if (points.empty() || query_count == 0) {
        throw std::runtime_error("Workload requires points and queries");
    }

    Workload w;
    w.original.reserve(query_count);

    std::unordered_map<std::uint64_t, std::uint32_t> page_ids;
    page_ids.reserve(points.size() / 8 + 1);

    std::unordered_set<std::uint32_t> active_keys;
    active_keys.reserve(points.size());

    for (std::size_t i = 0; i < query_count; ++i) {
        const auto& p = points[(i * 2654435761ull) % points.size()];
        const auto c = quantize(p);
        const auto pk = page_key(c);
        auto [it, inserted] = page_ids.try_emplace(pk, static_cast<std::uint32_t>(page_ids.size()));
        (void)inserted;

        const std::uint32_t page = it->second;
        const std::uint32_t local = local_index_4(c);
        const std::uint64_t logical_cell =
            static_cast<std::uint64_t>(page) * w.page_size + local;
        if (logical_cell >= std::numeric_limits<std::uint32_t>::max()) {
            throw std::runtime_error("M0 workload exceeds 32-bit logical cell key space");
        }

        // Zero is reserved as the empty hash-table sentinel.
        const auto key = static_cast<std::uint32_t>(logical_cell + 1u);
        w.original.push_back({key, page, local, 0});
        active_keys.insert(key);
    }

    w.active_cells = static_cast<std::uint32_t>(active_keys.size());

    w.page_sorted = w.original;
    std::stable_sort(w.page_sorted.begin(), w.page_sorted.end(), [](const Query& a, const Query& b) {
        return a.page_id < b.page_id ||
               (a.page_id == b.page_id && a.local_index < b.local_index);
    });

    const std::uint32_t page_count = static_cast<std::uint32_t>(page_ids.size());
    w.page_table.resize(page_count);
    w.paged_payload.resize(static_cast<std::size_t>(page_count) * w.page_size);
    for (std::uint32_t page = 0; page < page_count; ++page) {
        w.page_table[page] = page * w.page_size;
        for (std::uint32_t local = 0; local < w.page_size; ++local) {
            w.paged_payload[static_cast<std::size_t>(page) * w.page_size + local] =
                semantic_payload(page, local);
        }
    }

    const std::uint32_t table_size = table_size_for(active_keys.size());
    w.hash_mask = table_size - 1u;
    w.hash_keys.assign(table_size, 0u);
    w.hash_payload.assign(table_size, 0u);

    for (const auto& q : w.original) {
        std::uint32_t slot = mix32(q.key) & w.hash_mask;
        std::uint32_t probes = 1;
        while (w.hash_keys[slot] != 0u && w.hash_keys[slot] != q.key) {
            slot = (slot + 1u) & w.hash_mask;
            ++probes;
            if (probes > table_size) throw std::runtime_error("Hash table insertion failed");
        }

        const auto value = semantic_payload(q.page_id, q.local_index);
        if (w.hash_keys[slot] == q.key && w.hash_payload[slot] != value) {
            throw std::runtime_error("Logical cell key collision");
        }

        w.hash_keys[slot] = q.key;
        w.hash_payload[slot] = value;
        w.hash_max_probe = std::max(w.hash_max_probe, probes);
    }

    validate_semantic_equivalence(w);
    return w;
}

} // namespace phos::gi

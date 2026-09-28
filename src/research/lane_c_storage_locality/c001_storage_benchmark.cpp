#include "vk_context.hpp"
#include "vk_init.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

namespace phos::gi::lane_c {
namespace {

constexpr std::uint32_t kBrickEdge = 4;
constexpr std::uint32_t kCellsPerBrick = kBrickEdge * kBrickEdge * kBrickEdge;
constexpr std::uint32_t kUpdateXor = 0xa5a5a5a5u;

struct Unit {
    std::uint32_t cascade{};
    std::uint32_t x{};
    std::uint32_t y{};
    std::uint32_t z{};
};
static_assert(sizeof(Unit) == 16);

struct Address {
    std::uint32_t probe_key{};
    std::uint32_t brick_key{};
    std::uint32_t local_index{};
    std::uint32_t payload{};
};
static_assert(sizeof(Address) == 16);

struct SplitRcStreamHeaderV1 {
    std::array<char, 8> magic{};
    std::uint32_t schema_version{};
    std::uint32_t header_bytes{};
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
static_assert(sizeof(SplitRcStreamHeaderV1) == 64);

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
static_assert(sizeof(SplitRcWorkItemV1) == 64);

struct CascadeLayout {
    std::int32_t min_bx{};
    std::int32_t min_by{};
    std::int32_t min_bz{};
    std::int32_t pad{};
};
static_assert(sizeof(CascadeLayout) == 16);

struct TransitionLayout {
    std::int32_t min_bx{};
    std::int32_t min_by{};
    std::int32_t min_bz{};
    std::uint32_t page_base{};
    std::uint32_t union_x{};
    std::uint32_t union_y{};
    std::uint32_t union_z{};
    std::uint32_t pad{};
};
static_assert(sizeof(TransitionLayout) == 32);

struct Push {
    std::uint32_t count{};
    std::uint32_t op{};
    std::uint32_t mask{};
    std::uint32_t max_probe{};
    std::uint32_t brick_edge{kBrickEdge};
    std::uint32_t clip_x{};
    std::uint32_t clip_y{};
    std::uint32_t clip_z{};
};
static_assert(sizeof(Push) == 32);

enum class Rep { ProbeHash, BrickHash, Clipmap };

const char* rep_name(Rep rep) {
    switch (rep) {
    case Rep::ProbeHash: return "probe-hash";
    case Rep::BrickHash: return "hashed-brick-pool";
    case Rep::Clipmap: return "virtual-clipmap";
    }
    return "unknown";
}

std::uint32_t rep_mode(Rep rep) {
    switch (rep) {
    case Rep::ProbeHash: return 0u;
    case Rep::BrickHash: return 1u;
    case Rep::Clipmap: return 2u;
    }
    return 0u;
}

std::uint32_t mix32(std::uint32_t x) {
    x ^= x >> 16u;
    x *= 0x7feb352du;
    x ^= x >> 15u;
    x *= 0x846ca68bu;
    x ^= x >> 16u;
    return x == 0u ? 1u : x;
}

std::uint32_t next_pow2(std::uint32_t v) {
    std::uint32_t out = 1u;
    while (out < v) out <<= 1u;
    return out;
}

struct Config {
    std::uint32_t cascades{3};
    std::uint32_t bricks_x{24};
    std::uint32_t bricks_y{24};
    std::uint32_t bricks_z{8};
    std::uint32_t clip_x{32};
    std::uint32_t clip_y{32};
    std::uint32_t clip_z{16};
    std::uint32_t iterations{50};
    bool validation{false};
    std::optional<std::filesystem::path> stream;
    std::optional<std::filesystem::path> stream_from;
    std::optional<std::filesystem::path> stream_to;
    std::vector<std::uint32_t> occupancies{4, 16, 48};
};

std::uint32_t page_of_brick(const Unit& b, const Config& cfg) {
    return (((b.cascade * cfg.clip_z + b.z) * cfg.clip_y + b.y) * cfg.clip_x + b.x);
}

Address make_address(const Unit& p, Rep rep, const Config& cfg) {
    const auto bx = p.x / kBrickEdge;
    const auto by = p.y / kBrickEdge;
    const auto bz = p.z / kBrickEdge;
    const auto lx = p.x - bx * kBrickEdge;
    const auto ly = p.y - by * kBrickEdge;
    const auto lz = p.z - bz * kBrickEdge;
    const auto local = lx + kBrickEdge * (ly + kBrickEdge * lz);
    Unit b{p.cascade, bx, by, bz};
    const auto page = page_of_brick(b, cfg);
    const auto key = page * kCellsPerBrick + local + 1u;
    Address a{};
    a.probe_key = key;
    a.payload = mix32(key ^ 0x9e3779b9u);
    if (rep != Rep::ProbeHash) {
        a.brick_key = page + 1u;
        a.local_index = local;
    }
    return a;
}

std::int32_t floor_div(std::int32_t value, std::int32_t divisor) {
    const auto q = value / divisor;
    const auto r = value % divisor;
    return r < 0 ? q - 1 : q;
}

std::uint64_t fnv1a(const void* data, std::size_t bytes) {
    const auto* p = static_cast<const unsigned char*>(data);
    std::uint64_t hash = 1469598103934665603ull;
    for (std::size_t i = 0; i < bytes; ++i) {
        hash ^= p[i];
        hash *= 1099511628211ull;
    }
    return hash;
}

struct ExactStream {
    SplitRcStreamHeaderV1 header{};
    std::vector<SplitRcWorkItemV1> items;
    std::vector<CascadeLayout> layouts;
    std::uint32_t clip_x{};
    std::uint32_t clip_y{};
    std::uint32_t clip_z{};
    std::uint32_t unique_probes{};
    std::uint32_t unique_bricks{};
};

ExactStream load_exact_stream(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("cannot open Split RC stream: " + path.string());

    ExactStream stream{};
    in.read(reinterpret_cast<char*>(&stream.header), sizeof(stream.header));
    if (!in) throw std::runtime_error("truncated Split RC stream header");

    constexpr std::array<char, 8> magic{'P', 'H', 'O', 'S', 'R', 'C', '1', '\0'};
    if (stream.header.magic != magic ||
        stream.header.schema_version != 1u ||
        stream.header.header_bytes != sizeof(SplitRcStreamHeaderV1) ||
        stream.header.item_bytes != sizeof(SplitRcWorkItemV1)) {
        throw std::runtime_error("unsupported Split RC stream schema");
    }
    if (stream.header.item_count == 0u ||
        stream.header.cascade_count == 0u ||
        stream.header.rays_per_probe == 0u) {
        throw std::runtime_error("invalid empty Split RC stream");
    }

    const auto expected_bytes =
        static_cast<std::uintmax_t>(stream.header.header_bytes) +
        static_cast<std::uintmax_t>(stream.header.item_count) * stream.header.item_bytes;
    if (std::filesystem::file_size(path) != expected_bytes) {
        throw std::runtime_error("Split RC stream file size does not match header");
    }

    stream.items.resize(stream.header.item_count);
    in.read(
        reinterpret_cast<char*>(stream.items.data()),
        static_cast<std::streamsize>(stream.items.size() * sizeof(SplitRcWorkItemV1)));
    if (!in) throw std::runtime_error("truncated Split RC stream items");

    if (fnv1a(stream.items.data(), stream.items.size() * sizeof(SplitRcWorkItemV1)) !=
        stream.header.workload_id) {
        throw std::runtime_error("Split RC workload_id mismatch");
    }

    struct Bounds {
        std::int32_t min_x{std::numeric_limits<std::int32_t>::max()};
        std::int32_t min_y{std::numeric_limits<std::int32_t>::max()};
        std::int32_t min_z{std::numeric_limits<std::int32_t>::max()};
        std::int32_t max_x{std::numeric_limits<std::int32_t>::min()};
        std::int32_t max_y{std::numeric_limits<std::int32_t>::min()};
        std::int32_t max_z{std::numeric_limits<std::int32_t>::min()};
        bool seen{false};
    };
    std::vector<Bounds> bounds(stream.header.cascade_count);
    std::uint32_t write_count = 0u;
    for (const auto& item : stream.items) {
        if (item.cascade >= stream.header.cascade_count ||
            item.ray_index >= stream.header.rays_per_probe) {
            throw std::runtime_error("Split RC item exceeds header dimensions");
        }
        if (item.ray_index != 0u) continue;
        ++write_count;
        auto& b = bounds[item.cascade];
        const auto bx = floor_div(item.probe_x, static_cast<std::int32_t>(kBrickEdge));
        const auto by = floor_div(item.probe_y, static_cast<std::int32_t>(kBrickEdge));
        const auto bz = floor_div(item.probe_z, static_cast<std::int32_t>(kBrickEdge));
        b.min_x = std::min(b.min_x, bx);
        b.min_y = std::min(b.min_y, by);
        b.min_z = std::min(b.min_z, bz);
        b.max_x = std::max(b.max_x, bx);
        b.max_y = std::max(b.max_y, by);
        b.max_z = std::max(b.max_z, bz);
        b.seen = true;
    }
    if (write_count != stream.header.output_count) {
        throw std::runtime_error("Split RC ray-0 count does not match output_count");
    }

    stream.layouts.resize(stream.header.cascade_count);
    for (std::uint32_t cascade = 0; cascade < stream.header.cascade_count; ++cascade) {
        const auto& b = bounds[cascade];
        if (!b.seen) throw std::runtime_error("Split RC cascade has no ray-0 item");
        stream.layouts[cascade] = {b.min_x, b.min_y, b.min_z, 0};
        stream.clip_x = std::max(
            stream.clip_x, static_cast<std::uint32_t>(b.max_x - b.min_x + 1));
        stream.clip_y = std::max(
            stream.clip_y, static_cast<std::uint32_t>(b.max_y - b.min_y + 1));
        stream.clip_z = std::max(
            stream.clip_z, static_cast<std::uint32_t>(b.max_z - b.min_z + 1));
    }

    std::unordered_set<std::uint32_t> probes;
    std::unordered_set<std::uint32_t> bricks;
    for (const auto& item : stream.items) {
        if (item.ray_index != 0u) continue;
        const auto bx = floor_div(item.probe_x, static_cast<std::int32_t>(kBrickEdge));
        const auto by = floor_div(item.probe_y, static_cast<std::int32_t>(kBrickEdge));
        const auto bz = floor_div(item.probe_z, static_cast<std::int32_t>(kBrickEdge));
        const auto& origin = stream.layouts[item.cascade];
        const auto nbx = static_cast<std::uint32_t>(bx - origin.min_bx);
        const auto nby = static_cast<std::uint32_t>(by - origin.min_by);
        const auto nbz = static_cast<std::uint32_t>(bz - origin.min_bz);
        const std::uint64_t page =
            ((static_cast<std::uint64_t>(item.cascade) * stream.clip_z + nbz) *
                stream.clip_y + nby) *
                stream.clip_x + nbx;
        const auto lx = item.probe_x - bx * static_cast<std::int32_t>(kBrickEdge);
        const auto ly = item.probe_y - by * static_cast<std::int32_t>(kBrickEdge);
        const auto lz = item.probe_z - bz * static_cast<std::int32_t>(kBrickEdge);
        const auto local = static_cast<std::uint32_t>(
            lx + static_cast<std::int32_t>(kBrickEdge) *
                (ly + static_cast<std::int32_t>(kBrickEdge) * lz));
        const std::uint64_t key = page * kCellsPerBrick + local + 1u;
        if (key > std::numeric_limits<std::uint32_t>::max()) {
            throw std::runtime_error("Split RC exact storage key exceeds uint32");
        }
        probes.insert(static_cast<std::uint32_t>(key));
        bricks.insert(static_cast<std::uint32_t>(page));
    }
    stream.unique_probes = static_cast<std::uint32_t>(probes.size());
    stream.unique_bricks = static_cast<std::uint32_t>(bricks.size());
    if (stream.unique_probes == 0u || stream.unique_bricks == 0u) {
        throw std::runtime_error("Split RC stream produced no storage units");
    }
    return stream;
}

Address make_exact_address(
    const SplitRcWorkItemV1& item,
    Rep rep,
    const ExactStream& stream) {
    const auto bx = floor_div(item.probe_x, static_cast<std::int32_t>(kBrickEdge));
    const auto by = floor_div(item.probe_y, static_cast<std::int32_t>(kBrickEdge));
    const auto bz = floor_div(item.probe_z, static_cast<std::int32_t>(kBrickEdge));
    const auto& origin = stream.layouts[item.cascade];
    const auto nbx = static_cast<std::uint32_t>(bx - origin.min_bx);
    const auto nby = static_cast<std::uint32_t>(by - origin.min_by);
    const auto nbz = static_cast<std::uint32_t>(bz - origin.min_bz);
    const auto lx = item.probe_x - bx * static_cast<std::int32_t>(kBrickEdge);
    const auto ly = item.probe_y - by * static_cast<std::int32_t>(kBrickEdge);
    const auto lz = item.probe_z - bz * static_cast<std::int32_t>(kBrickEdge);
    const auto local = static_cast<std::uint32_t>(
        lx + static_cast<std::int32_t>(kBrickEdge) *
            (ly + static_cast<std::int32_t>(kBrickEdge) * lz));
    const auto page = static_cast<std::uint32_t>(
        ((static_cast<std::uint64_t>(item.cascade) * stream.clip_z + nbz) *
            stream.clip_y + nby) *
            stream.clip_x + nbx);
    const auto key = page * kCellsPerBrick + local + 1u;
    Address address{};
    address.probe_key = key;
    address.payload = item.ray_index == 0u ? mix32(key ^ 0x9e3779b9u) : 0u;
    if (rep != Rep::ProbeHash) {
        address.brick_key = page + 1u;
        address.local_index = local;
    }
    return address;
}


struct TransitionPair {
    ExactStream from;
    ExactStream to;
    std::vector<TransitionLayout> layouts;
    std::uint32_t clip_x{};
    std::uint32_t clip_y{};
    std::uint32_t clip_z{};
    std::uint32_t union_unique_probes{};
    std::uint32_t union_unique_bricks{};
    std::uint32_t from_unique_probes{};
    std::uint32_t to_unique_probes{};
    std::uint32_t from_unique_bricks{};
    std::uint32_t to_unique_bricks{};
    std::uint32_t entering_probes{};
    std::uint32_t leaving_probes{};
    std::uint32_t entering_bricks{};
    std::uint32_t leaving_bricks{};
};

struct BrickBounds {
    std::int32_t min_x{std::numeric_limits<std::int32_t>::max()};
    std::int32_t min_y{std::numeric_limits<std::int32_t>::max()};
    std::int32_t min_z{std::numeric_limits<std::int32_t>::max()};
    std::int32_t max_x{std::numeric_limits<std::int32_t>::min()};
    std::int32_t max_y{std::numeric_limits<std::int32_t>::min()};
    std::int32_t max_z{std::numeric_limits<std::int32_t>::min()};
    bool seen{false};
};

std::vector<BrickBounds> stream_brick_bounds(
    const ExactStream& stream) {
    std::vector<BrickBounds> bounds(stream.header.cascade_count);
    for (const auto& item : stream.items) {
        if (item.ray_index != 0u) continue;
        auto& b = bounds[item.cascade];
        const auto bx = floor_div(item.probe_x, static_cast<std::int32_t>(kBrickEdge));
        const auto by = floor_div(item.probe_y, static_cast<std::int32_t>(kBrickEdge));
        const auto bz = floor_div(item.probe_z, static_cast<std::int32_t>(kBrickEdge));
        b.min_x = std::min(b.min_x, bx);
        b.min_y = std::min(b.min_y, by);
        b.min_z = std::min(b.min_z, bz);
        b.max_x = std::max(b.max_x, bx);
        b.max_y = std::max(b.max_y, by);
        b.max_z = std::max(b.max_z, bz);
        b.seen = true;
    }
    return bounds;
}

Address make_transition_address(
    const SplitRcWorkItemV1& item,
    Rep rep,
    const TransitionPair& pair) {
    const auto bx = floor_div(item.probe_x, static_cast<std::int32_t>(kBrickEdge));
    const auto by = floor_div(item.probe_y, static_cast<std::int32_t>(kBrickEdge));
    const auto bz = floor_div(item.probe_z, static_cast<std::int32_t>(kBrickEdge));
    const auto& dims = pair.layouts[item.cascade];
    const auto ubx = static_cast<std::uint32_t>(bx - dims.min_bx);
    const auto uby = static_cast<std::uint32_t>(by - dims.min_by);
    const auto ubz = static_cast<std::uint32_t>(bz - dims.min_bz);
    const auto lx = item.probe_x - bx * static_cast<std::int32_t>(kBrickEdge);
    const auto ly = item.probe_y - by * static_cast<std::int32_t>(kBrickEdge);
    const auto lz = item.probe_z - bz * static_cast<std::int32_t>(kBrickEdge);
    const auto local = static_cast<std::uint32_t>(
        lx + static_cast<std::int32_t>(kBrickEdge) *
            (ly + static_cast<std::int32_t>(kBrickEdge) * lz));
    const std::uint64_t canonical_page =
        static_cast<std::uint64_t>(dims.page_base) +
        (static_cast<std::uint64_t>(ubz) * dims.union_y + uby) *
            dims.union_x + ubx;
    const std::uint64_t key64 = canonical_page * kCellsPerBrick + local + 1u;
    if (key64 >= 0x80000000ull || canonical_page + 1u >= 0x80000000ull) {
        throw std::runtime_error("C001d canonical key exceeds tagged uint32 range");
    }

    Address address{};
    address.probe_key = static_cast<std::uint32_t>(key64);
    address.payload =
        item.ray_index == 0u ? mix32(address.probe_key ^ 0x9e3779b9u) : 0u;
    if (rep != Rep::ProbeHash) {
        const auto sx = ubx % pair.clip_x;
        const auto sy = uby % pair.clip_y;
        const auto sz = ubz % pair.clip_z;
        const auto slot =
            ((item.cascade * pair.clip_z + sz) * pair.clip_y + sy) *
                pair.clip_x + sx;
        address.brick_key = slot + 1u;
        address.local_index = local;
    }
    return address;
}

TransitionPair load_transition_pair(
    const std::filesystem::path& from_path,
    const std::filesystem::path& to_path) {
    TransitionPair pair{};
    pair.from = load_exact_stream(from_path);
    pair.to = load_exact_stream(to_path);
    if (pair.from.header.cascade_count != pair.to.header.cascade_count ||
        pair.from.header.rays_per_probe != pair.to.header.rays_per_probe) {
        throw std::runtime_error("C001d stream dimensions are incompatible");
    }

    const auto from_bounds = stream_brick_bounds(pair.from);
    const auto to_bounds = stream_brick_bounds(pair.to);
    pair.layouts.resize(pair.from.header.cascade_count);

    std::uint64_t page_base = 0u;
    for (std::uint32_t cascade = 0; cascade < pair.layouts.size(); ++cascade) {
        const auto& a = from_bounds[cascade];
        const auto& b = to_bounds[cascade];
        if (!a.seen || !b.seen) {
            throw std::runtime_error("C001d cascade missing from one frame");
        }
        const auto min_x = std::min(a.min_x, b.min_x);
        const auto min_y = std::min(a.min_y, b.min_y);
        const auto min_z = std::min(a.min_z, b.min_z);
        const auto max_x = std::max(a.max_x, b.max_x);
        const auto max_y = std::max(a.max_y, b.max_y);
        const auto max_z = std::max(a.max_z, b.max_z);
        const auto ux = static_cast<std::uint32_t>(max_x - min_x + 1);
        const auto uy = static_cast<std::uint32_t>(max_y - min_y + 1);
        const auto uz = static_cast<std::uint32_t>(max_z - min_z + 1);
        if (page_base > std::numeric_limits<std::uint32_t>::max()) {
            throw std::runtime_error("C001d page base overflow");
        }
        pair.layouts[cascade] = {
            min_x, min_y, min_z, static_cast<std::uint32_t>(page_base),
            ux, uy, uz, 0u};
        page_base += static_cast<std::uint64_t>(ux) * uy * uz;

        pair.clip_x = std::max(
            pair.clip_x,
            std::max(
                static_cast<std::uint32_t>(a.max_x - a.min_x + 1),
                static_cast<std::uint32_t>(b.max_x - b.min_x + 1)));
        pair.clip_y = std::max(
            pair.clip_y,
            std::max(
                static_cast<std::uint32_t>(a.max_y - a.min_y + 1),
                static_cast<std::uint32_t>(b.max_y - b.min_y + 1)));
        pair.clip_z = std::max(
            pair.clip_z,
            std::max(
                static_cast<std::uint32_t>(a.max_z - a.min_z + 1),
                static_cast<std::uint32_t>(b.max_z - b.min_z + 1)));
    }

    std::unordered_set<std::uint32_t> from_probes, to_probes;
    std::unordered_set<std::uint32_t> from_bricks, to_bricks;
    std::unordered_set<std::uint64_t> from_slots, to_slots;
    auto collect = [&](const ExactStream& stream,
                       std::unordered_set<std::uint32_t>& probes,
                       std::unordered_set<std::uint32_t>& bricks,
                       std::unordered_set<std::uint64_t>& slots) {
        for (const auto& item : stream.items) {
            if (item.ray_index != 0u) continue;
            const auto address = make_transition_address(item, Rep::Clipmap, pair);
            probes.insert(address.probe_key);
            const auto tag = ((address.probe_key - 1u) / kCellsPerBrick) + 1u;
            bricks.insert(tag);
            const auto slot_tag =
                (static_cast<std::uint64_t>(address.brick_key) << 32u) | tag;
            slots.insert(slot_tag);
        }
    };
    collect(pair.from, from_probes, from_bricks, from_slots);
    collect(pair.to, to_probes, to_bricks, to_slots);

    auto verify_slots = [&](const auto& slots, std::size_t expected_bricks) {
        std::unordered_set<std::uint32_t> seen;
        for (const auto packed : slots) {
            const auto slot = static_cast<std::uint32_t>(packed >> 32u);
            if (!seen.insert(slot).second) {
                throw std::runtime_error(
                    "C001d toroidal clip extent aliases active bricks");
            }
        }
        if (seen.size() != expected_bricks) {
            throw std::runtime_error("C001d clip slot accounting mismatch");
        }
    };
    verify_slots(from_slots, from_bricks.size());
    verify_slots(to_slots, to_bricks.size());

    std::unordered_set<std::uint32_t> union_probes = from_probes;
    union_probes.insert(to_probes.begin(), to_probes.end());
    std::unordered_set<std::uint32_t> union_bricks = from_bricks;
    union_bricks.insert(to_bricks.begin(), to_bricks.end());

    auto count_difference = [](const auto& lhs, const auto& rhs) {
        std::uint32_t count = 0u;
        for (const auto value : lhs) {
            if (!rhs.contains(value)) ++count;
        }
        return count;
    };

    pair.union_unique_probes = static_cast<std::uint32_t>(union_probes.size());
    pair.union_unique_bricks = static_cast<std::uint32_t>(union_bricks.size());
    pair.from_unique_probes = static_cast<std::uint32_t>(from_probes.size());
    pair.to_unique_probes = static_cast<std::uint32_t>(to_probes.size());
    pair.from_unique_bricks = static_cast<std::uint32_t>(from_bricks.size());
    pair.to_unique_bricks = static_cast<std::uint32_t>(to_bricks.size());
    pair.entering_probes = count_difference(to_probes, from_probes);
    pair.leaving_probes = count_difference(from_probes, to_probes);
    pair.entering_bricks = count_difference(to_bricks, from_bricks);
    pair.leaving_bricks = count_difference(from_bricks, to_bricks);
    return pair;
}

struct Workload {
    std::uint32_t occupancy{};
    std::vector<Unit> active_bricks;
    std::vector<Unit> leaving_bricks;
    std::vector<Unit> entering_bricks;
    std::vector<Unit> probes;
    std::vector<Unit> update_probes;
    std::vector<Unit> invalidate_probes;
    std::vector<Unit> leaving_probes;
    std::vector<Unit> entering_probes;
};

Workload make_workload(const Config& cfg, std::uint32_t occupancy) {
    Workload w{};
    w.occupancy = occupancy;
    std::vector<std::uint32_t> locals;
    locals.reserve(occupancy);
    for (std::uint32_t i = 0; i < occupancy; ++i) {
        locals.push_back((i * 37u) % kCellsPerBrick);
    }

    for (std::uint32_t c = 0; c < cfg.cascades; ++c) {
        for (std::uint32_t bz = 0; bz < cfg.bricks_z; ++bz) {
            for (std::uint32_t by = 0; by < cfg.bricks_y; ++by) {
                for (std::uint32_t bx = 0; bx < cfg.bricks_x; ++bx) {
                    w.active_bricks.push_back({c, bx, by, bz});
                    if (bx == 0u) w.leaving_bricks.push_back({c, bx, by, bz});
                    for (const auto local : locals) {
                        const auto lx = local % kBrickEdge;
                        const auto ly = (local / kBrickEdge) % kBrickEdge;
                        const auto lz = local / (kBrickEdge * kBrickEdge);
                        Unit p{
                            c,
                            bx * kBrickEdge + lx,
                            by * kBrickEdge + ly,
                            bz * kBrickEdge + lz,
                        };
                        const auto index = w.probes.size();
                        w.probes.push_back(p);
                        if ((index % 17u) == 0u) w.update_probes.push_back(p);
                        if ((index % 257u) == 0u) w.invalidate_probes.push_back(p);
                        if (bx == 0u) w.leaving_probes.push_back(p);
                    }
                }
                const Unit entering_brick{c, cfg.bricks_x, by, bz};
                w.entering_bricks.push_back(entering_brick);
                for (const auto local : locals) {
                    const auto lx = local % kBrickEdge;
                    const auto ly = (local / kBrickEdge) % kBrickEdge;
                    const auto lz = local / (kBrickEdge * kBrickEdge);
                    w.entering_probes.push_back({
                        c,
                        cfg.bricks_x * kBrickEdge + lx,
                        by * kBrickEdge + ly,
                        bz * kBrickEdge + lz,
                    });
                }
            }
        }
    }
    return w;
}

std::vector<Address> addresses_for(
    const std::vector<Unit>& probes, Rep rep, const Config& cfg) {
    std::vector<Address> out;
    out.reserve(probes.size());
    for (const auto& p : probes) out.push_back(make_address(p, rep, cfg));
    return out;
}

struct HostState {
    std::vector<std::uint32_t> keys;
    std::vector<std::uint32_t> values;
    std::vector<std::uint32_t> payloads;
    std::array<std::uint32_t, 4> counters{};
    std::vector<std::uint32_t> free_list;
    std::uint32_t mask{};
    std::uint32_t max_probe{512};
    std::size_t persistent_bytes{};
};

std::uint32_t insert_linear(
    std::vector<std::uint32_t>& keys,
    std::uint32_t mask,
    std::uint32_t key,
    std::uint32_t& max_probe) {
    std::uint32_t slot = mix32(key) & mask;
    for (std::uint32_t probe = 1; probe <= keys.size(); ++probe) {
        if (keys[slot] == 0u || keys[slot] == key) {
            keys[slot] = key;
            max_probe = std::max(max_probe, probe);
            return slot;
        }
        slot = (slot + 1u) & mask;
    }
    throw std::runtime_error("host hash insertion failed");
}

HostState make_state(
    Rep rep,
    const Workload& w,
    const std::vector<Address>& all_addresses,
    const Config& cfg,
    bool populated) {
    HostState s{};
    if (rep == Rep::ProbeHash) {
        const auto capacity =
            next_pow2(std::max<std::uint32_t>(2u, static_cast<std::uint32_t>(w.probes.size() * 2u)));
        s.keys.assign(capacity, 0u);
        s.values.assign(1, 0u);
        s.free_list.assign(1, 0u);
        s.payloads.assign(capacity, 0u);
        s.mask = capacity - 1u;
        std::uint32_t observed_probe = 1u;
        for (const auto& a : all_addresses) {
            const auto slot = insert_linear(s.keys, s.mask, a.probe_key, observed_probe);
            if (populated) s.payloads[slot] = a.payload;
        }
        s.max_probe = capacity;
        s.persistent_bytes =
            s.keys.size() * sizeof(std::uint32_t) +
            s.payloads.size() * sizeof(std::uint32_t);
        return s;
    }

    const auto brick_count = static_cast<std::uint32_t>(w.active_bricks.size());
    s.payloads.assign(static_cast<std::size_t>(brick_count) * kCellsPerBrick, 0u);
    s.free_list.assign(brick_count, 0u);
    s.counters[0] = brick_count;

    if (rep == Rep::BrickHash) {
        const auto capacity = next_pow2(std::max(2u, brick_count * 2u));
        s.keys.assign(capacity, 0u);
        s.values.assign(capacity, 0u);
        s.mask = capacity - 1u;
        std::uint32_t observed_probe = 1u;
        for (std::uint32_t physical = 0; physical < brick_count; ++physical) {
            const auto key = page_of_brick(w.active_bricks[physical], cfg) + 1u;
            const auto slot = insert_linear(s.keys, s.mask, key, observed_probe);
            s.values[slot] = physical + 1u;
        }
        s.max_probe = capacity;
        if (populated) {
            for (const auto& a : all_addresses) {
                std::uint32_t slot = mix32(a.brick_key) & s.mask;
                while (s.keys[slot] != a.brick_key) slot = (slot + 1u) & s.mask;
                const auto physical = s.values[slot] - 1u;
                s.payloads[static_cast<std::size_t>(physical) * kCellsPerBrick + a.local_index] =
                    a.payload;
            }
        }
        s.persistent_bytes =
            (s.keys.size() + s.values.size() + s.payloads.size() + s.counters.size() + s.free_list.size()) *
            sizeof(std::uint32_t);
        return s;
    }

    const auto page_count = cfg.cascades * cfg.clip_x * cfg.clip_y * cfg.clip_z;
    s.keys.assign(page_count, 0u);
    s.values.assign(1, 0u);
    for (std::uint32_t physical = 0; physical < brick_count; ++physical) {
        s.keys[page_of_brick(w.active_bricks[physical], cfg)] = physical + 1u;
    }
    if (populated) {
        for (const auto& a : all_addresses) {
            const auto physical = s.keys[a.brick_key - 1u] - 1u;
            s.payloads[static_cast<std::size_t>(physical) * kCellsPerBrick + a.local_index] =
                a.payload;
        }
    }
    s.persistent_bytes =
        (s.keys.size() + s.payloads.size() + s.counters.size() + s.free_list.size()) * sizeof(std::uint32_t);
    return s;
}

HostState make_exact_state(
    Rep rep,
    const ExactStream& stream,
    const std::vector<Address>& addresses,
    bool populated) {
    HostState state{};
    if (rep == Rep::ProbeHash) {
        const auto capacity = next_pow2(std::max(2u, stream.unique_probes * 2u));
        state.keys.assign(capacity, 0u);
        state.values.assign(1, 0u);
        state.payloads.assign(capacity, 0u);
        state.free_list.assign(1, 0u);
        state.mask = capacity - 1u;
        state.max_probe = capacity;
        std::uint32_t observed_probe = 1u;
        for (const auto& address : addresses) {
            if (address.payload == 0u) continue;
            const auto slot = insert_linear(
                state.keys, state.mask, address.probe_key, observed_probe);
            if (populated) state.payloads[slot] = address.payload;
        }
        state.persistent_bytes =
            (state.keys.size() + state.payloads.size()) * sizeof(std::uint32_t);
        return state;
    }
    if (rep != Rep::Clipmap) {
        throw std::runtime_error("exact replay supports probe hash and virtual clipmap only");
    }

    const auto page_count =
        static_cast<std::size_t>(stream.header.cascade_count) *
        stream.clip_x * stream.clip_y * stream.clip_z;
    state.keys.assign(page_count, 0u);
    state.values.assign(1, 0u);
    state.payloads.assign(
        static_cast<std::size_t>(stream.unique_bricks) * kCellsPerBrick, 0u);
    state.free_list.assign(stream.unique_bricks, 0u);
    state.max_probe = stream.unique_bricks;

    std::uint32_t next_physical = 0u;
    for (const auto& address : addresses) {
        if (address.payload == 0u) continue;
        const auto page = address.brick_key - 1u;
        if (state.keys[page] == 0u) state.keys[page] = ++next_physical;
        if (populated) {
            const auto physical = state.keys[page] - 1u;
            state.payloads[
                static_cast<std::size_t>(physical) * kCellsPerBrick +
                address.local_index] = address.payload;
        }
    }
    if (next_physical != stream.unique_bricks) {
        throw std::runtime_error("exact replay brick count mismatch");
    }
    state.counters[0] = stream.unique_bricks;
    state.persistent_bytes =
        (state.keys.size() + state.payloads.size() +
            state.counters.size() + state.free_list.size()) *
        sizeof(std::uint32_t);
    return state;
}

HostState make_transition_state(
    Rep rep,
    const TransitionPair& pair,
    const std::vector<Address>& from_addresses) {
    HostState state{};
    if (rep == Rep::ProbeHash) {
        const auto capacity =
            next_pow2(std::max(2u, pair.union_unique_probes * 2u));
        state.keys.assign(capacity, 0u);
        state.values.assign(1, 0u);
        state.payloads.assign(capacity, 0u);
        state.free_list.assign(1, 0u);
        state.mask = capacity - 1u;
        state.max_probe = capacity;
        std::uint32_t observed_probe = 1u;
        for (const auto& address : from_addresses) {
            if (address.payload == 0u) continue;
            const auto slot = insert_linear(
                state.keys, state.mask, address.probe_key, observed_probe);
            state.payloads[slot] = address.payload;
        }
        state.persistent_bytes =
            (state.keys.size() + state.payloads.size()) * sizeof(std::uint32_t);
        return state;
    }
    if (rep != Rep::Clipmap) {
        throw std::runtime_error("C001d supports probe hash and virtual clipmap only");
    }

    const auto page_count =
        static_cast<std::size_t>(pair.from.header.cascade_count) *
        pair.clip_x * pair.clip_y * pair.clip_z;
    state.keys.assign(page_count, 0u);
    state.values.assign(page_count, 0u);
    state.payloads.assign(
        static_cast<std::size_t>(pair.union_unique_bricks) * kCellsPerBrick, 0u);
    state.free_list.assign(pair.union_unique_bricks, 0u);
    state.max_probe = pair.union_unique_bricks;

    std::uint32_t physical_count = 0u;
    for (const auto& address : from_addresses) {
        if (address.payload == 0u) continue;
        const auto slot = address.brick_key - 1u;
        const auto tag = ((address.probe_key - 1u) / kCellsPerBrick) + 1u;
        if (state.values[slot] == 0u) {
            state.values[slot] = tag;
            state.keys[slot] = ++physical_count;
        } else if (state.values[slot] != tag) {
            throw std::runtime_error("C001d seed clip slot alias");
        }
        const auto physical = state.keys[slot] - 1u;
        state.payloads[
            static_cast<std::size_t>(physical) * kCellsPerBrick +
            address.local_index] = address.payload;
    }
    if (physical_count != pair.from_unique_bricks) {
        throw std::runtime_error("C001d seed brick count mismatch");
    }
    state.counters[0] = physical_count;
    state.persistent_bytes =
        (state.keys.size() + state.values.size() + state.payloads.size() +
            state.counters.size() + state.free_list.size()) *
        sizeof(std::uint32_t);
    return state;
}

HostState make_empty_like(const HostState& seeded, Rep rep) {
    HostState e = seeded;
    std::fill(e.keys.begin(), e.keys.end(), 0u);
    std::fill(e.values.begin(), e.values.end(), 0u);
    std::fill(e.payloads.begin(), e.payloads.end(), 0u);
    std::fill(e.free_list.begin(), e.free_list.end(), 0u);
    e.counters = {0u, 0u, 0u, 0u};
    if (rep == Rep::ProbeHash) e.persistent_bytes = seeded.persistent_bytes;
    return e;
}

struct Dispatch {
    VkPipeline pipeline{VK_NULL_HANDLE};
    VkDescriptorSet set{VK_NULL_HANDLE};
    Push push{};
};

struct CopyPair {
    const GpuBuffer* src{};
    const GpuBuffer* dst{};
};

class VulkanBench {
public:
    explicit VulkanBench(bool validation) : ctx_(validation) {
        std::array<VkDescriptorSetLayoutBinding, 8> bindings{};
        for (std::uint32_t i = 0; i < bindings.size(); ++i) {
            bindings[i].binding = i;
            bindings[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            bindings[i].descriptorCount = 1;
            bindings[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
        }
        auto dli = detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
        dli.bindingCount = static_cast<std::uint32_t>(bindings.size());
        dli.pBindings = bindings.data();
        check(ctx_.vk().createDescriptorSetLayout(&dli, nullptr, &layout_), "descriptor layout");

        VkPushConstantRange pcr{VK_SHADER_STAGE_COMPUTE_BIT, 0u, sizeof(Push)};
        auto pli = detail::make_vk_info<VkPipelineLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
        pli.setLayoutCount = 1;
        pli.pSetLayouts = &layout_;
        pli.pushConstantRangeCount = 1;
        pli.pPushConstantRanges = &pcr;
        check(ctx_.vk().createPipelineLayout(&pli, nullptr, &pipeline_layout_), "pipeline layout");

        VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 8u * 128u};
        auto dpi = detail::make_vk_info<VkDescriptorPoolCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
        dpi.maxSets = 128;
        dpi.poolSizeCount = 1;
        dpi.pPoolSizes = &ps;
        check(ctx_.vk().createDescriptorPool(&dpi, nullptr, &descriptor_pool_), "descriptor pool");

        auto cpi = detail::make_vk_info<VkCommandPoolCreateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
        cpi.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        cpi.queueFamilyIndex = ctx_.queue_family();
        check(ctx_.vk().createCommandPool(&cpi, nullptr, &command_pool_), "command pool");

        address_ = create_pipeline("c001_address.spv");
        exact_address_ = create_pipeline("c001_exact_address.spv");
        transition_address_ = create_pipeline("c001_transition_address.spv");
        transition_hash_ = create_pipeline("c001_transition_hash.spv");
        transition_clipmap_ = create_pipeline("c001_transition_clipmap.spv");
        probe_hash_ = create_pipeline("c001_probe_hash.spv");
        brick_hash_ = create_pipeline("c001_brick_hash.spv");
        clipmap_ = create_pipeline("c001_clipmap.spv");

        const std::array<std::uint32_t, 4> zeros{};
        dummy_ = upload(zeros.data(), sizeof(zeros));
    }

    ~VulkanBench() {
        ctx_.vk().deviceWaitIdle();
        ctx_.destroy_buffer(dummy_);
        if (clipmap_) ctx_.vk().destroyPipeline(clipmap_, nullptr);
        if (brick_hash_) ctx_.vk().destroyPipeline(brick_hash_, nullptr);
        if (probe_hash_) ctx_.vk().destroyPipeline(probe_hash_, nullptr);
        if (transition_clipmap_) ctx_.vk().destroyPipeline(transition_clipmap_, nullptr);
        if (transition_hash_) ctx_.vk().destroyPipeline(transition_hash_, nullptr);
        if (transition_address_) ctx_.vk().destroyPipeline(transition_address_, nullptr);
        if (exact_address_) ctx_.vk().destroyPipeline(exact_address_, nullptr);
        if (address_) ctx_.vk().destroyPipeline(address_, nullptr);
        if (command_pool_) ctx_.vk().destroyCommandPool(command_pool_, nullptr);
        if (descriptor_pool_) ctx_.vk().destroyDescriptorPool(descriptor_pool_, nullptr);
        if (pipeline_layout_) ctx_.vk().destroyPipelineLayout(pipeline_layout_, nullptr);
        if (layout_) ctx_.vk().destroyDescriptorSetLayout(layout_, nullptr);
    }

    VulkanContext& context() { return ctx_; }
    const std::string& device_name() const { return ctx_.device_name(); }
    VkPipeline address_pipeline() const { return address_; }
    VkPipeline exact_address_pipeline() const { return exact_address_; }
    VkPipeline transition_address_pipeline() const { return transition_address_; }
    VkPipeline transition_storage_pipeline(Rep rep) const {
        return rep == Rep::ProbeHash ? transition_hash_ : transition_clipmap_;
    }
    VkPipeline storage_pipeline(Rep rep) const {
        if (rep == Rep::ProbeHash) return probe_hash_;
        if (rep == Rep::BrickHash) return brick_hash_;
        return clipmap_;
    }

    GpuBuffer upload(const void* data, std::size_t bytes) {
        return ctx_.upload_device_buffer(
            data, static_cast<VkDeviceSize>(bytes), VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    }

    template <class T>
    GpuBuffer upload_vector(const std::vector<T>& values) {
        if (values.empty()) throw std::runtime_error("cannot upload empty vector");
        return upload(values.data(), values.size() * sizeof(T));
    }

    GpuBuffer make_zero(std::size_t bytes) {
        std::vector<std::byte> zero(bytes);
        return upload(zero.data(), zero.size());
    }

    VkDescriptorSet create_set(const std::array<const GpuBuffer*, 8>& buffers) {
        VkDescriptorSet set{};
        auto ai = detail::make_vk_info<VkDescriptorSetAllocateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
        ai.descriptorPool = descriptor_pool_;
        ai.descriptorSetCount = 1;
        ai.pSetLayouts = &layout_;
        check(ctx_.vk().allocateDescriptorSets(&ai, &set), "descriptor allocate");

        std::array<VkDescriptorBufferInfo, 8> infos{};
        std::array<VkWriteDescriptorSet, 8> writes{};
        for (std::uint32_t i = 0; i < buffers.size(); ++i) {
            infos[i] = {buffers[i]->buffer, 0u, buffers[i]->size};
            writes[i] = detail::make_vk_info<VkWriteDescriptorSet>(
                VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
            writes[i].dstSet = set;
            writes[i].dstBinding = i;
            writes[i].descriptorCount = 1;
            writes[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            writes[i].pBufferInfo = &infos[i];
        }
        ctx_.vk().updateDescriptorSets(
            static_cast<std::uint32_t>(writes.size()), writes.data(), 0, nullptr);
        return set;
    }

    double measure(
        const std::vector<Dispatch>& sequence,
        const std::vector<CopyPair>& resets,
        std::uint32_t iterations) {
        VkCommandBuffer cmd = allocate_command_buffer();
        VkQueryPool query{};
        auto qci = detail::make_vk_info<VkQueryPoolCreateInfo>(
            VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
        qci.queryType = VK_QUERY_TYPE_TIMESTAMP;
        qci.queryCount = iterations * 2u;
        check(ctx_.vk().createQueryPool(&qci, nullptr, &query), "query pool");

        begin(cmd);
        ctx_.vk().cmdResetQueryPool(cmd, query, 0u, iterations * 2u);
        for (std::uint32_t i = 0; i < iterations; ++i) {
            if (!resets.empty()) {
                memory_barrier(
                    cmd,
                    VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                    VK_PIPELINE_STAGE_TRANSFER_BIT,
                    VK_ACCESS_SHADER_WRITE_BIT,
                    VK_ACCESS_TRANSFER_WRITE_BIT);
                for (const auto& pair : resets) {
                    VkBufferCopy region{0u, 0u, pair.dst->size};
                    ctx_.vk().cmdCopyBuffer(cmd, pair.src->buffer, pair.dst->buffer, 1u, &region);
                }
                memory_barrier(
                    cmd,
                    VK_PIPELINE_STAGE_TRANSFER_BIT,
                    VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                    VK_ACCESS_TRANSFER_WRITE_BIT,
                    VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT);
            }
            ctx_.vk().cmdWriteTimestamp(
                cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, query, i * 2u);
            record_sequence(cmd, sequence);
            ctx_.vk().cmdWriteTimestamp(
                cmd, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, query, i * 2u + 1u);
        }
        end_submit_wait(cmd);

        std::vector<std::uint64_t> timestamps(iterations * 2u);
        check(ctx_.vk().getQueryPoolResults(
                  query, 0u, iterations * 2u,
                  timestamps.size() * sizeof(std::uint64_t),
                  timestamps.data(), sizeof(std::uint64_t),
                  VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT),
              "query results");

        std::vector<double> samples;
        samples.reserve(iterations);
        for (std::uint32_t i = 0; i < iterations; ++i) {
            const auto ticks = timestamps[i * 2u + 1u] - timestamps[i * 2u];
            samples.push_back(
                static_cast<double>(ticks) * ctx_.timestamp_period_ns() / 1000.0);
        }
        std::sort(samples.begin(), samples.end());
        const double median = samples[samples.size() / 2u];

        ctx_.vk().destroyQueryPool(query, nullptr);
        ctx_.vk().freeCommandBuffers(command_pool_, 1u, &cmd);
        return median;
    }

    void execute(
        const std::vector<Dispatch>& sequence,
        const std::vector<CopyPair>& resets = {}) {
        VkCommandBuffer cmd = allocate_command_buffer();
        begin(cmd);
        if (!resets.empty()) {
            memory_barrier(
                cmd,
                VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_ACCESS_MEMORY_WRITE_BIT,
                VK_ACCESS_TRANSFER_WRITE_BIT);
            for (const auto& pair : resets) {
                VkBufferCopy region{0u, 0u, pair.dst->size};
                ctx_.vk().cmdCopyBuffer(cmd, pair.src->buffer, pair.dst->buffer, 1u, &region);
            }
            memory_barrier(
                cmd,
                VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT);
        }
        record_sequence(cmd, sequence);
        end_submit_wait(cmd);
        ctx_.vk().freeCommandBuffers(command_pool_, 1u, &cmd);
    }

    void copy_once(const std::vector<CopyPair>& copies) {
        execute({}, copies);
    }

private:
    static void check(VkResult result, const char* what) {
        if (result != VK_SUCCESS) throw std::runtime_error(what);
    }

    VkPipeline create_pipeline(const std::string& filename) {
        const auto path = std::filesystem::path(PHOS_LANE_C_SHADER_DIR) / filename;
        auto code = read_binary_file(path.string());
        auto smi = detail::make_vk_info<VkShaderModuleCreateInfo>(
            VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
        smi.codeSize = code.size();
        smi.pCode = reinterpret_cast<const std::uint32_t*>(code.data());
        VkShaderModule module{};
        check(ctx_.vk().createShaderModule(&smi, nullptr, &module), "shader module");
        auto stage = detail::make_vk_info<VkPipelineShaderStageCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
        stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        stage.module = module;
        stage.pName = "main";
        auto ci = detail::make_vk_info<VkComputePipelineCreateInfo>(
            VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO);
        ci.stage = stage;
        ci.layout = pipeline_layout_;
        VkPipeline out{};
        const auto result =
            ctx_.vk().createComputePipelines(VK_NULL_HANDLE, 1u, &ci, nullptr, &out);
        ctx_.vk().destroyShaderModule(module, nullptr);
        check(result, "compute pipeline");
        return out;
    }

    VkCommandBuffer allocate_command_buffer() {
        VkCommandBuffer cmd{};
        auto ai = detail::make_vk_info<VkCommandBufferAllocateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
        ai.commandPool = command_pool_;
        ai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        ai.commandBufferCount = 1u;
        check(ctx_.vk().allocateCommandBuffers(&ai, &cmd), "command buffer");
        return cmd;
    }

    void begin(VkCommandBuffer cmd) {
        auto bi = detail::make_vk_info<VkCommandBufferBeginInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
        bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        check(ctx_.vk().beginCommandBuffer(cmd, &bi), "begin command buffer");
    }

    void end_submit_wait(VkCommandBuffer cmd) {
        check(ctx_.vk().endCommandBuffer(cmd), "end command buffer");
        VkFence fence{};
        auto fi = detail::make_vk_info<VkFenceCreateInfo>(VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
        check(ctx_.vk().createFence(&fi, nullptr, &fence), "fence");
        auto si = detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
        si.commandBufferCount = 1u;
        si.pCommandBuffers = &cmd;
        check(ctx_.vk().queueSubmit(ctx_.queue(), 1u, &si, fence), "queue submit");
        check(ctx_.vk().waitForFences(1u, &fence, VK_TRUE, UINT64_MAX), "wait fence");
        ctx_.vk().destroyFence(fence, nullptr);
    }

    void memory_barrier(
        VkCommandBuffer cmd,
        VkPipelineStageFlags src_stage,
        VkPipelineStageFlags dst_stage,
        VkAccessFlags src_access,
        VkAccessFlags dst_access) {
        auto barrier = detail::make_vk_info<VkMemoryBarrier>(
            VK_STRUCTURE_TYPE_MEMORY_BARRIER);
        barrier.srcAccessMask = src_access;
        barrier.dstAccessMask = dst_access;
        ctx_.vk().cmdPipelineBarrier(
            cmd, src_stage, dst_stage, 0u,
            1u, &barrier, 0u, nullptr, 0u, nullptr);
    }

    void record_sequence(VkCommandBuffer cmd, const std::vector<Dispatch>& sequence) {
        for (std::size_t i = 0; i < sequence.size(); ++i) {
            const auto& d = sequence[i];
            ctx_.vk().cmdBindPipeline(
                cmd, VK_PIPELINE_BIND_POINT_COMPUTE, d.pipeline);
            ctx_.vk().cmdBindDescriptorSets(
                cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_layout_,
                0u, 1u, &d.set, 0u, nullptr);
            ctx_.vk().cmdPushConstants(
                cmd, pipeline_layout_, VK_SHADER_STAGE_COMPUTE_BIT,
                0u, sizeof(Push), &d.push);
            const auto groups = (d.push.count + 255u) / 256u;
            ctx_.vk().cmdDispatch(cmd, groups, 1u, 1u);
            memory_barrier(
                cmd,
                VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                VK_ACCESS_SHADER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT);
        }
    }

    VulkanContext ctx_;
    VkDescriptorSetLayout layout_{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout_{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool_{VK_NULL_HANDLE};
    VkCommandPool command_pool_{VK_NULL_HANDLE};
    VkPipeline address_{VK_NULL_HANDLE};
    VkPipeline exact_address_{VK_NULL_HANDLE};
    VkPipeline transition_address_{VK_NULL_HANDLE};
    VkPipeline transition_hash_{VK_NULL_HANDLE};
    VkPipeline transition_clipmap_{VK_NULL_HANDLE};
    VkPipeline probe_hash_{VK_NULL_HANDLE};
    VkPipeline brick_hash_{VK_NULL_HANDLE};
    VkPipeline clipmap_{VK_NULL_HANDLE};
    GpuBuffer dummy_{};
};

struct GpuState {
    GpuBuffer keys;
    GpuBuffer values;
    GpuBuffer payloads;
    GpuBuffer counters;
    GpuBuffer free_list;
    GpuBuffer seed_keys;
    GpuBuffer seed_values;
    GpuBuffer seed_payloads;
    GpuBuffer seed_counters;
    GpuBuffer seed_free_list;
    GpuBuffer empty_keys;
    GpuBuffer empty_values;
    GpuBuffer empty_payloads;
    GpuBuffer empty_counters;
    GpuBuffer empty_free_list;
    std::size_t persistent_bytes{};
    std::uint32_t mask{};
    std::uint32_t max_probe{};
};

GpuState upload_state(
    VulkanBench& bench,
    const HostState& seeded,
    const HostState& empty) {
    auto upload_u32 = [&](const std::vector<std::uint32_t>& v) {
        return bench.upload(v.data(), v.size() * sizeof(std::uint32_t));
    };
    auto upload_counter = [&](const std::array<std::uint32_t, 4>& v) {
        return bench.upload(v.data(), sizeof(v));
    };

    GpuState g{};
    g.keys = upload_u32(seeded.keys);
    g.values = upload_u32(seeded.values);
    g.payloads = upload_u32(seeded.payloads);
    g.counters = upload_counter(seeded.counters);
    g.free_list = upload_u32(seeded.free_list);

    g.seed_keys = upload_u32(seeded.keys);
    g.seed_values = upload_u32(seeded.values);
    g.seed_payloads = upload_u32(seeded.payloads);
    g.seed_counters = upload_counter(seeded.counters);
    g.seed_free_list = upload_u32(seeded.free_list);

    g.empty_keys = upload_u32(empty.keys);
    g.empty_values = upload_u32(empty.values);
    g.empty_payloads = upload_u32(empty.payloads);
    g.empty_counters = upload_counter(empty.counters);
    g.empty_free_list = upload_u32(empty.free_list);

    g.persistent_bytes = seeded.persistent_bytes;
    g.mask = seeded.mask;
    g.max_probe = seeded.max_probe;
    return g;
}

void destroy_state(VulkanBench& bench, GpuState& g) {
    auto& ctx = bench.context();
    ctx.destroy_buffer(g.empty_free_list);
    ctx.destroy_buffer(g.empty_counters);
    ctx.destroy_buffer(g.empty_payloads);
    ctx.destroy_buffer(g.empty_values);
    ctx.destroy_buffer(g.empty_keys);
    ctx.destroy_buffer(g.seed_free_list);
    ctx.destroy_buffer(g.seed_counters);
    ctx.destroy_buffer(g.seed_payloads);
    ctx.destroy_buffer(g.seed_values);
    ctx.destroy_buffer(g.seed_keys);
    ctx.destroy_buffer(g.free_list);
    ctx.destroy_buffer(g.counters);
    ctx.destroy_buffer(g.payloads);
    ctx.destroy_buffer(g.values);
    ctx.destroy_buffer(g.keys);
}

std::vector<CopyPair> baseline_reset(const GpuState& g) {
    return {
        {&g.seed_keys, &g.keys},
        {&g.seed_values, &g.values},
        {&g.seed_payloads, &g.payloads},
        {&g.seed_counters, &g.counters},
        {&g.seed_free_list, &g.free_list},
    };
}

std::vector<CopyPair> empty_reset(const GpuState& g) {
    return {
        {&g.empty_keys, &g.keys},
        {&g.empty_values, &g.values},
        {&g.empty_payloads, &g.payloads},
        {&g.empty_counters, &g.counters},
        {&g.empty_free_list, &g.free_list},
    };
}

Push make_push(
    std::uint32_t count,
    std::uint32_t op,
    const GpuState& state,
    const Config& cfg) {
    Push p{};
    p.count = count;
    p.op = op;
    p.mask = state.mask;
    p.max_probe = state.max_probe;
    p.brick_edge = kBrickEdge;
    p.clip_x = cfg.clip_x;
    p.clip_y = cfg.clip_y;
    p.clip_z = cfg.clip_z;
    return p;
}

std::uint64_t checksum(const std::vector<std::uint32_t>& values) {
    return std::accumulate(
        values.begin(), values.end(), std::uint64_t{0});
}

bool addresses_equal(
    const std::vector<Address>& expected,
    const std::vector<Address>& actual) {
    return expected.size() == actual.size() &&
        std::memcmp(
            expected.data(), actual.data(), expected.size() * sizeof(Address)) == 0;
}

std::vector<std::uint32_t> download_u32(
    VulkanBench& bench, const GpuBuffer& buffer, std::size_t count) {
    std::vector<std::uint32_t> out(count);
    bench.context().download_device_buffer(
        buffer, out.data(), count * sizeof(std::uint32_t));
    return out;
}

std::vector<Address> download_addresses(
    VulkanBench& bench, const GpuBuffer& buffer, std::size_t count) {
    std::vector<Address> out(count);
    bench.context().download_device_buffer(
        buffer, out.data(), count * sizeof(Address));
    return out;
}

std::array<std::uint32_t, 4> download_counters(
    VulkanBench& bench, const GpuBuffer& buffer) {
    std::array<std::uint32_t, 4> out{};
    bench.context().download_device_buffer(buffer, out.data(), sizeof(out));
    return out;
}

bool allocator_ok(
    Rep rep,
    const std::array<std::uint32_t, 4>& counters,
    std::uint32_t expected_active_bricks,
    bool require_empty_free_list) {
    if (counters[1] != 0u) return false;
    if (rep == Rep::ProbeHash) return true;
    if (counters[0] != expected_active_bricks) return false;
    return !require_empty_free_list || counters[2] == 0u;
}

struct Row {
    std::string representation;
    std::uint32_t occupancy{};
    std::string phase;
    std::uint32_t items{};
    std::size_t persistent_bytes{};
    std::size_t scratch_bytes{};
    std::size_t producer_input_bytes{};
    double gpu_us{};
    std::uint64_t checksum{};
    bool correct{};
};

void write_rows(const std::vector<Row>& rows) {
    std::ostream* out = &std::cout;
    std::ofstream file;
    if (const char* dir = std::getenv("PHOS_RESEARCH_ARTIFACT_DIR")) {
        const auto path = std::filesystem::path(dir) / "c001b.csv";
        file.open(path);
        if (!file) throw std::runtime_error("cannot create c001b.csv");
    }

    auto emit = [&](std::ostream& s) {
        s << "representation,occupancy,phase,items,persistent_bytes,scratch_bytes,"
             "producer_input_bytes,gpu_us,checksum,correct\n";
        for (const auto& r : rows) {
            s << r.representation << ','
              << r.occupancy << ','
              << r.phase << ','
              << r.items << ','
              << r.persistent_bytes << ','
              << r.scratch_bytes << ','
              << r.producer_input_bytes << ','
              << r.gpu_us << ','
              << r.checksum << ','
              << (r.correct ? "true" : "false") << '\n';
        }
    };
    emit(*out);
    if (file) emit(file);
}

struct ExactRow {
    std::string representation;
    std::uint64_t workload_id{};
    std::string phase;
    std::uint32_t items{};
    std::uint32_t writes{};
    std::uint32_t bricks{};
    std::size_t persistent_bytes{};
    std::size_t scratch_bytes{};
    std::size_t producer_input_bytes{};
    double gpu_us{};
    std::uint64_t checksum{};
    bool correct{};
};

void write_exact_rows(const std::vector<ExactRow>& rows) {
    std::ostream* out = &std::cout;
    std::ofstream file;
    if (const char* dir = std::getenv("PHOS_RESEARCH_ARTIFACT_DIR")) {
        const auto path = std::filesystem::path(dir) / "c001c.csv";
        file.open(path);
        if (!file) throw std::runtime_error("cannot create c001c.csv");
    }
    auto emit = [&](std::ostream& stream) {
        stream << "representation,workload_id,phase,items,writes,bricks,"
                  "persistent_bytes,scratch_bytes,producer_input_bytes,"
                  "gpu_us,checksum,correct\n";
        for (const auto& row : rows) {
            stream << row.representation << ','
                   << row.workload_id << ','
                   << row.phase << ','
                   << row.items << ','
                   << row.writes << ','
                   << row.bricks << ','
                   << row.persistent_bytes << ','
                   << row.scratch_bytes << ','
                   << row.producer_input_bytes << ','
                   << row.gpu_us << ','
                   << row.checksum << ','
                   << (row.correct ? "true" : "false") << '\n';
        }
    };
    emit(*out);
    if (file) emit(file);
}

bool exact_allocator_ok(
    Rep rep,
    const std::array<std::uint32_t, 4>& counters,
    const ExactStream& stream) {
    if (counters[1] != 0u) return false;
    return rep == Rep::ProbeHash || counters[0] == stream.unique_bricks;
}

int run_exact_stream(
    const Config& base_cfg,
    VulkanBench& bench,
    const std::filesystem::path& path) {
    const auto stream = load_exact_stream(path);
    Config cfg = base_cfg;
    cfg.cascades = stream.header.cascade_count;
    cfg.clip_x = stream.clip_x;
    cfg.clip_y = stream.clip_y;
    cfg.clip_z = stream.clip_z;

    std::cerr
        << "Exact stream: workload_id=" << stream.header.workload_id
        << ", items=" << stream.header.item_count
        << ", outputs=" << stream.header.output_count
        << ", unique_probes=" << stream.unique_probes
        << ", unique_bricks=" << stream.unique_bricks
        << ", clip=" << stream.clip_x << 'x' << stream.clip_y << 'x' << stream.clip_z
        << '\n';

    auto work_items = bench.upload_vector(stream.items);
    auto layouts = bench.upload_vector(stream.layouts);
    std::vector<ExactRow> rows;
    bool all_correct = true;

    for (const auto rep : {Rep::ProbeHash, Rep::Clipmap}) {
        std::vector<Address> expected_addresses;
        expected_addresses.reserve(stream.items.size());
        std::vector<std::uint32_t> expected_base;
        expected_base.reserve(stream.items.size());
        std::vector<std::uint32_t> expected_updated;
        expected_updated.reserve(stream.items.size());
        for (const auto& item : stream.items) {
            const auto address = make_exact_address(item, rep, stream);
            expected_addresses.push_back(address);
            expected_base.push_back(address.payload);
            expected_updated.push_back(
                address.payload == 0u ? 0u : (address.payload ^ kUpdateXor));
        }

        const auto seeded = make_exact_state(rep, stream, expected_addresses, true);
        const auto empty = make_empty_like(seeded, rep);
        auto state = upload_state(bench, seeded, empty);
        auto dynamic_addresses =
            bench.make_zero(expected_addresses.size() * sizeof(Address));
        auto output =
            bench.make_zero(stream.items.size() * sizeof(std::uint32_t));

        auto address_set = bench.create_set({
            &work_items,
            &dynamic_addresses,
            &layouts,
            &layouts,
            &layouts,
            &output,
            &state.counters,
            &state.free_list,
        });
        auto storage_set = bench.create_set({
            &work_items,
            &dynamic_addresses,
            &state.keys,
            &state.values,
            &state.payloads,
            &output,
            &state.counters,
            &state.free_list,
        });

        const auto count = stream.header.item_count;
        auto exact_push = [&](std::uint32_t op) {
            auto p = make_push(count, op, state, cfg);
            return p;
        };
        const Dispatch address{
            bench.exact_address_pipeline(),
            address_set,
            exact_push(rep_mode(rep)),
        };
        auto storage = [&](std::uint32_t op) {
            return Dispatch{
                bench.storage_pipeline(rep),
                storage_set,
                exact_push(op),
            };
        };
        const auto reserve = storage(8u);
        const auto populate = storage(9u);
        const auto update = storage(10u);
        const auto invalidate = storage(11u);
        const auto lookup = storage(12u);

        const auto scratch_bytes =
            dynamic_addresses.size + output.size;
        const auto producer_input_bytes =
            work_items.size + layouts.size;

        const auto producer_us =
            bench.measure({address}, {}, cfg.iterations);
        const auto gpu_addresses =
            download_addresses(bench, dynamic_addresses, expected_addresses.size());
        const bool producer_ok = addresses_equal(expected_addresses, gpu_addresses);
        rows.push_back({
            rep_name(rep), stream.header.workload_id, "producer-address",
            count, stream.header.output_count, stream.unique_bricks,
            state.persistent_bytes, scratch_bytes, producer_input_bytes,
            producer_us, 0u, producer_ok});
        all_correct = all_correct && producer_ok;

        bench.copy_once(baseline_reset(state));
        const auto lookup_us =
            bench.measure({address, lookup}, {}, cfg.iterations);
        const auto lookup_values =
            download_u32(bench, output, stream.items.size());
        const bool lookup_ok = lookup_values == expected_base;
        rows.push_back({
            rep_name(rep), stream.header.workload_id, "producer+lookup",
            count, stream.header.output_count, stream.unique_bricks,
            state.persistent_bytes, scratch_bytes, producer_input_bytes,
            lookup_us, checksum(lookup_values), lookup_ok});
        all_correct = all_correct && lookup_ok;

        const auto update_us =
            bench.measure({address, update}, baseline_reset(state), cfg.iterations);
        bench.execute({lookup});
        const auto updated_values =
            download_u32(bench, output, stream.items.size());
        const auto update_counters = download_counters(bench, state.counters);
        const bool update_ok =
            updated_values == expected_updated &&
            exact_allocator_ok(rep, update_counters, stream);
        rows.push_back({
            rep_name(rep), stream.header.workload_id, "producer+update",
            count, stream.header.output_count, stream.unique_bricks,
            state.persistent_bytes, scratch_bytes, producer_input_bytes,
            update_us, checksum(updated_values), update_ok});
        all_correct = all_correct && update_ok;

        const auto invalidation_us =
            bench.measure({address, invalidate}, baseline_reset(state), cfg.iterations);
        bench.execute({lookup});
        const auto invalidated_values =
            download_u32(bench, output, stream.items.size());
        const auto invalidation_counters = download_counters(bench, state.counters);
        const bool invalidation_ok =
            std::all_of(
                invalidated_values.begin(), invalidated_values.end(),
                [](std::uint32_t value) { return value == 0u; }) &&
            exact_allocator_ok(rep, invalidation_counters, stream);
        rows.push_back({
            rep_name(rep), stream.header.workload_id, "producer+invalidation",
            count, stream.header.output_count, stream.unique_bricks,
            state.persistent_bytes, scratch_bytes, producer_input_bytes,
            invalidation_us, checksum(invalidated_values), invalidation_ok});
        all_correct = all_correct && invalidation_ok;

        const auto allocation_us =
            bench.measure({address, reserve}, empty_reset(state), cfg.iterations);
        bench.execute({populate, lookup});
        const auto allocation_values =
            download_u32(bench, output, stream.items.size());
        const auto allocation_counters = download_counters(bench, state.counters);
        const bool allocation_ok =
            allocation_values == expected_base &&
            exact_allocator_ok(rep, allocation_counters, stream);
        rows.push_back({
            rep_name(rep), stream.header.workload_id, "producer+allocation-residency",
            count, stream.header.output_count, stream.unique_bricks,
            state.persistent_bytes, scratch_bytes, producer_input_bytes,
            allocation_us, checksum(allocation_values), allocation_ok});
        all_correct = all_correct && allocation_ok;

        const auto build_us =
            bench.measure(
                {address, reserve, populate},
                empty_reset(state),
                cfg.iterations);
        bench.execute({lookup});
        const auto build_values =
            download_u32(bench, output, stream.items.size());
        const auto build_counters = download_counters(bench, state.counters);
        const bool build_ok =
            build_values == expected_base &&
            exact_allocator_ok(rep, build_counters, stream);
        rows.push_back({
            rep_name(rep), stream.header.workload_id, "initial-build-e2e",
            count, stream.header.output_count, stream.unique_bricks,
            state.persistent_bytes, scratch_bytes, producer_input_bytes,
            build_us, checksum(build_values), build_ok});
        all_correct = all_correct && build_ok;

        bench.context().destroy_buffer(output);
        bench.context().destroy_buffer(dynamic_addresses);
        destroy_state(bench, state);
    }

    bench.context().destroy_buffer(layouts);
    bench.context().destroy_buffer(work_items);
    write_exact_rows(rows);
    if (!all_correct) {
        std::cerr << "fatal: C001c exact-stream correctness gate failed\n";
        return 2;
    }
    return 0;
}

struct TransitionRow {
    std::string representation;
    std::uint64_t from_workload_id{};
    std::uint64_t to_workload_id{};
    std::string phase;
    std::uint32_t target_items{};
    std::uint32_t from_probes{};
    std::uint32_t to_probes{};
    std::uint32_t entering_probes{};
    std::uint32_t leaving_probes{};
    std::uint32_t from_bricks{};
    std::uint32_t to_bricks{};
    std::uint32_t entering_bricks{};
    std::uint32_t leaving_bricks{};
    std::size_t persistent_bytes{};
    std::size_t scratch_bytes{};
    std::size_t producer_input_bytes{};
    double gpu_us{};
    std::uint64_t checksum{};
    bool correct{};
};

void write_transition_rows(const std::vector<TransitionRow>& rows) {
    std::ostream* out = &std::cout;
    std::ofstream file;
    if (const char* dir = std::getenv("PHOS_RESEARCH_ARTIFACT_DIR")) {
        const auto path = std::filesystem::path(dir) / "c001d.csv";
        file.open(path);
        if (!file) throw std::runtime_error("cannot create c001d.csv");
    }
    auto emit = [&](std::ostream& stream) {
        stream
            << "representation,from_workload_id,to_workload_id,phase,target_items,"
               "from_probes,to_probes,entering_probes,leaving_probes,"
               "from_bricks,to_bricks,entering_bricks,leaving_bricks,"
               "persistent_bytes,scratch_bytes,producer_input_bytes,"
               "gpu_us,checksum,correct\n";
        for (const auto& row : rows) {
            stream << row.representation << ','
                   << row.from_workload_id << ','
                   << row.to_workload_id << ','
                   << row.phase << ','
                   << row.target_items << ','
                   << row.from_probes << ','
                   << row.to_probes << ','
                   << row.entering_probes << ','
                   << row.leaving_probes << ','
                   << row.from_bricks << ','
                   << row.to_bricks << ','
                   << row.entering_bricks << ','
                   << row.leaving_bricks << ','
                   << row.persistent_bytes << ','
                   << row.scratch_bytes << ','
                   << row.producer_input_bytes << ','
                   << row.gpu_us << ','
                   << row.checksum << ','
                   << (row.correct ? "true" : "false") << '\n';
        }
    };
    emit(*out);
    if (file) emit(file);
}

int run_transition_streams(
    const Config& base_cfg,
    VulkanBench& bench,
    const std::filesystem::path& from_path,
    const std::filesystem::path& to_path) {
    const auto pair = load_transition_pair(from_path, to_path);
    Config cfg = base_cfg;
    cfg.cascades = pair.from.header.cascade_count;
    cfg.clip_x = pair.clip_x;
    cfg.clip_y = pair.clip_y;
    cfg.clip_z = pair.clip_z;

    std::cerr
        << "Transition: " << pair.from.header.workload_id
        << " -> " << pair.to.header.workload_id
        << ", probes " << pair.from_unique_probes << " -> " << pair.to_unique_probes
        << " (+" << pair.entering_probes << "/-" << pair.leaving_probes << ')'
        << ", bricks " << pair.from_unique_bricks << " -> " << pair.to_unique_bricks
        << " (+" << pair.entering_bricks << "/-" << pair.leaving_bricks << ')'
        << ", clip=" << pair.clip_x << 'x' << pair.clip_y << 'x' << pair.clip_z
        << '\n';

    auto to_items = bench.upload_vector(pair.to.items);
    auto layouts = bench.upload_vector(pair.layouts);
    std::vector<TransitionRow> rows;
    bool all_correct = true;

    for (const auto rep : {Rep::ProbeHash, Rep::Clipmap}) {
        std::vector<Address> from_addresses;
        from_addresses.reserve(pair.from.items.size());
        std::vector<Address> to_addresses;
        to_addresses.reserve(pair.to.items.size());
        std::unordered_set<std::uint32_t> target_keys;
        std::vector<std::uint32_t> expected_target;
        expected_target.reserve(pair.to.items.size());

        for (const auto& item : pair.from.items) {
            from_addresses.push_back(make_transition_address(item, rep, pair));
        }
        for (const auto& item : pair.to.items) {
            const auto address = make_transition_address(item, rep, pair);
            to_addresses.push_back(address);
            expected_target.push_back(address.payload);
            if (address.payload != 0u) target_keys.insert(address.probe_key);
        }
        std::vector<std::uint32_t> expected_old_after;
        expected_old_after.reserve(from_addresses.size());
        for (const auto& address : from_addresses) {
            expected_old_after.push_back(
                address.payload != 0u && target_keys.contains(address.probe_key)
                    ? address.payload
                    : 0u);
        }

        const auto seeded = make_transition_state(rep, pair, from_addresses);
        const auto empty = make_empty_like(seeded, rep);
        auto state = upload_state(bench, seeded, empty);

        auto dynamic_to =
            bench.make_zero(to_addresses.size() * sizeof(Address));
        auto static_from = bench.upload_vector(from_addresses);
        auto output_to =
            bench.make_zero(pair.to.items.size() * sizeof(std::uint32_t));
        auto output_from =
            bench.make_zero(pair.from.items.size() * sizeof(std::uint32_t));

        auto address_set = bench.create_set({
            &to_items,
            &dynamic_to,
            &layouts,
            &layouts,
            &layouts,
            &output_to,
            &state.counters,
            &state.free_list,
        });
        auto target_set = bench.create_set({
            &to_items,
            &dynamic_to,
            &state.keys,
            &state.values,
            &state.payloads,
            &output_to,
            &state.counters,
            &state.free_list,
        });
        auto old_set = bench.create_set({
            &to_items,
            &static_from,
            &state.keys,
            &state.values,
            &state.payloads,
            &output_from,
            &state.counters,
            &state.free_list,
        });

        auto push = [&](std::uint32_t count, std::uint32_t op) {
            return make_push(count, op, state, cfg);
        };
        const Dispatch address{
            bench.transition_address_pipeline(),
            address_set,
            push(pair.to.header.item_count, rep_mode(rep)),
        };
        auto dispatch = [&](VkDescriptorSet set, std::uint32_t count, std::uint32_t op) {
            return Dispatch{
                bench.transition_storage_pipeline(rep),
                set,
                push(count, op),
            };
        };

        std::vector<Dispatch> transition{
            address,
            dispatch(target_set, pair.to.header.item_count, 13u),
            dispatch(
                target_set,
                static_cast<std::uint32_t>(state.keys.size()),
                14u),
        };
        if (rep == Rep::Clipmap) {
            transition.push_back(
                dispatch(target_set, pair.to.header.item_count, 15u));
            transition.push_back(dispatch(target_set, 1u, 16u));
            transition.push_back(
                dispatch(target_set, pair.to.header.item_count, 17u));
        } else {
            transition.push_back(
                dispatch(target_set, pair.to.header.item_count, 15u));
        }

        const auto target_lookup = dispatch(
            target_set,
            pair.to.header.item_count,
            rep == Rep::ProbeHash ? 16u : 18u);
        const auto old_lookup = dispatch(
            old_set,
            pair.from.header.item_count,
            rep == Rep::ProbeHash ? 16u : 18u);

        const auto scratch_bytes =
            dynamic_to.size + output_to.size + output_from.size;
        const auto producer_input_bytes = to_items.size + layouts.size;

        const auto producer_us =
            bench.measure({address}, {}, cfg.iterations);
        const auto gpu_addresses =
            download_addresses(bench, dynamic_to, to_addresses.size());
        const bool producer_ok = addresses_equal(to_addresses, gpu_addresses);
        rows.push_back({
            rep_name(rep),
            pair.from.header.workload_id,
            pair.to.header.workload_id,
            "producer-address",
            pair.to.header.item_count,
            pair.from_unique_probes,
            pair.to_unique_probes,
            pair.entering_probes,
            pair.leaving_probes,
            pair.from_unique_bricks,
            pair.to_unique_bricks,
            pair.entering_bricks,
            pair.leaving_bricks,
            state.persistent_bytes,
            scratch_bytes,
            producer_input_bytes,
            producer_us,
            0u,
            producer_ok,
        });
        all_correct = all_correct && producer_ok;

        const auto transition_us =
            bench.measure(transition, baseline_reset(state), cfg.iterations);
        bench.execute({target_lookup});
        const auto target_values =
            download_u32(bench, output_to, pair.to.items.size());
        const auto counters_after_target =
            download_counters(bench, state.counters);
        const bool target_ok = target_values == expected_target;

        bench.execute({old_lookup});
        const auto old_values =
            download_u32(bench, output_from, pair.from.items.size());
        const auto counters = download_counters(bench, state.counters);
        bool allocator_ok = counters[1] == 0u && counters[3] == 0u;
        if (rep == Rep::Clipmap) {
            allocator_ok =
                allocator_ok &&
                counters[0] >= counters[2] &&
                counters[0] - counters[2] == pair.to_unique_bricks &&
                counters[0] <= pair.union_unique_bricks;
        } else {
            allocator_ok =
                allocator_ok &&
                counters_after_target[2] == pair.leaving_probes;
        }
        const bool transition_ok =
            target_ok &&
            old_values == expected_old_after &&
            allocator_ok;
        rows.push_back({
            rep_name(rep),
            pair.from.header.workload_id,
            pair.to.header.workload_id,
            "transition-e2e",
            pair.to.header.item_count,
            pair.from_unique_probes,
            pair.to_unique_probes,
            pair.entering_probes,
            pair.leaving_probes,
            pair.from_unique_bricks,
            pair.to_unique_bricks,
            pair.entering_bricks,
            pair.leaving_bricks,
            state.persistent_bytes,
            scratch_bytes,
            producer_input_bytes,
            transition_us,
            checksum(target_values),
            transition_ok,
        });
        all_correct = all_correct && transition_ok;

        bench.context().destroy_buffer(output_from);
        bench.context().destroy_buffer(output_to);
        bench.context().destroy_buffer(static_from);
        bench.context().destroy_buffer(dynamic_to);
        destroy_state(bench, state);
    }

    bench.context().destroy_buffer(layouts);
    bench.context().destroy_buffer(to_items);
    write_transition_rows(rows);
    if (!all_correct) {
        std::cerr << "fatal: C001d transition correctness gate failed\n";
        return 2;
    }
    return 0;
}

Config parse_args(int argc, char** argv) {
    Config cfg{};
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--iterations" && i + 1 < argc) {
            cfg.iterations = static_cast<std::uint32_t>(std::stoul(argv[++i]));
        } else if (arg == "--validation") {
            cfg.validation = true;
        } else if (arg == "--stream" && i + 1 < argc) {
            cfg.stream = std::filesystem::path(argv[++i]);
        } else if (arg == "--stream-from" && i + 1 < argc) {
            cfg.stream_from = std::filesystem::path(argv[++i]);
        } else if (arg == "--stream-to" && i + 1 < argc) {
            cfg.stream_to = std::filesystem::path(argv[++i]);
        } else if (arg == "--occupancies" && i + 1 < argc) {
            cfg.occupancies.clear();
            std::string text = argv[++i];
            std::size_t start = 0;
            while (start < text.size()) {
                const auto end = text.find(',', start);
                cfg.occupancies.push_back(static_cast<std::uint32_t>(
                    std::stoul(text.substr(start, end - start))));
                if (end == std::string::npos) break;
                start = end + 1;
            }
        } else if (arg == "--help") {
            std::cout
                << "phos-c001-storage [--iterations N] [--occupancies 4,16,48] "
                   "[--stream stream-v1.bin] "
                   "[--stream-from stream-v1.bin --stream-to stream-v1.bin] "
                   "[--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error("unknown argument: " + arg);
        }
    }
    if (cfg.iterations == 0u) throw std::runtime_error("iterations must be positive");
    if (cfg.stream_from.has_value() != cfg.stream_to.has_value()) {
        throw std::runtime_error("--stream-from and --stream-to must be supplied together");
    }
    if (cfg.stream && cfg.stream_from) {
        throw std::runtime_error("--stream cannot be combined with transition streams");
    }
    if (!cfg.stream && !cfg.stream_from) {
        for (const auto occ : cfg.occupancies) {
            if (occ == 0u || occ > kCellsPerBrick) {
                throw std::runtime_error("occupancy must be in [1,64]");
            }
        }
        if (cfg.clip_x <= cfg.bricks_x ||
            cfg.clip_y < cfg.bricks_y ||
            cfg.clip_z < cfg.bricks_z) {
            throw std::runtime_error(
                "clipmap extent must contain the active window and one X shift");
        }
    }
    return cfg;
}

} // namespace

int run(int argc, char** argv) {
    const auto cfg = parse_args(argc, argv);
    VulkanBench bench(cfg.validation);
    std::cerr << "GPU: " << bench.device_name() << '\n';
    if (cfg.stream_from) {
        return run_transition_streams(
            cfg, bench, *cfg.stream_from, *cfg.stream_to);
    }
    if (cfg.stream) {
        return run_exact_stream(cfg, bench, *cfg.stream);
    }

    std::vector<Row> rows;
    bool all_correct = true;

    for (const auto occupancy : cfg.occupancies) {
        const auto workload = make_workload(cfg, occupancy);

        for (const auto rep : {Rep::ProbeHash, Rep::BrickHash, Rep::Clipmap}) {
            const auto all_addr = addresses_for(workload.probes, rep, cfg);
            const auto update_addr = addresses_for(workload.update_probes, rep, cfg);
            const auto invalidate_addr = addresses_for(workload.invalidate_probes, rep, cfg);
            const auto leaving_addr = addresses_for(workload.leaving_probes, rep, cfg);
            const auto entering_addr = addresses_for(workload.entering_probes, rep, cfg);

            const auto seeded = make_state(rep, workload, all_addr, cfg, true);
            const auto empty = make_empty_like(seeded, rep);
            auto state = upload_state(bench, seeded, empty);

            auto probes = bench.upload_vector(workload.probes);
            auto update_probes = bench.upload_vector(workload.update_probes);
            auto invalidate_probes = bench.upload_vector(workload.invalidate_probes);
            auto leaving_probes = bench.upload_vector(workload.leaving_probes);
            auto entering_probes = bench.upload_vector(workload.entering_probes);
            auto active_bricks = bench.upload_vector(workload.active_bricks);
            auto leaving_bricks = bench.upload_vector(workload.leaving_bricks);
            auto entering_bricks = bench.upload_vector(workload.entering_bricks);

            auto static_all_addr = bench.upload_vector(all_addr);
            auto static_update_addr = bench.upload_vector(update_addr);
            auto static_invalidate_addr = bench.upload_vector(invalidate_addr);
            auto static_leaving_addr = bench.upload_vector(leaving_addr);
            auto static_entering_addr = bench.upload_vector(entering_addr);

            auto dynamic_all_addr = bench.make_zero(all_addr.size() * sizeof(Address));
            auto dynamic_update_addr = bench.make_zero(update_addr.size() * sizeof(Address));
            auto dynamic_entering_addr = bench.make_zero(entering_addr.size() * sizeof(Address));
            auto output = bench.make_zero(workload.probes.size() * sizeof(std::uint32_t));

            const auto scratch_bytes =
                dynamic_all_addr.size + output.size +
                (rep == Rep::ProbeHash ? state.counters.size : 0u);

            auto make_set = [&](const GpuBuffer& input, const GpuBuffer& addr) {
                return bench.create_set({
                    &input,
                    &addr,
                    &state.keys,
                    &state.values,
                    &state.payloads,
                    &output,
                    &state.counters,
                    &state.free_list,
                });
            };

            const auto addr_all_set = make_set(probes, dynamic_all_addr);
            const auto addr_update_set = make_set(update_probes, dynamic_update_addr);
            const auto addr_entering_set = make_set(entering_probes, dynamic_entering_addr);
            const auto lookup_static_set = make_set(probes, static_all_addr);
            const auto lookup_dynamic_set = make_set(probes, dynamic_all_addr);
            const auto update_static_set = make_set(update_probes, static_update_addr);
            const auto update_dynamic_set = make_set(update_probes, dynamic_update_addr);
            const auto invalidate_set = make_set(invalidate_probes, static_invalidate_addr);
            const auto lookup_entering_set = make_set(entering_probes, static_entering_addr);
            const auto populate_entering_dynamic_set = make_set(entering_probes, dynamic_entering_addr);
            const auto evict_probe_set = make_set(leaving_probes, static_leaving_addr);
            const auto reserve_probe_static_set = lookup_static_set;
            const auto reserve_probe_dynamic_set = lookup_dynamic_set;
            const auto reserve_brick_set = make_set(active_bricks, static_all_addr);
            const auto reserve_entering_brick_set = make_set(entering_bricks, dynamic_entering_addr);
            const auto evict_brick_set = make_set(leaving_bricks, static_all_addr);

            const auto address_all = Dispatch{
                bench.address_pipeline(),
                addr_all_set,
                make_push(
                    static_cast<std::uint32_t>(workload.probes.size()),
                    rep_mode(rep), state, cfg)};
            const auto address_update = Dispatch{
                bench.address_pipeline(),
                addr_update_set,
                make_push(
                    static_cast<std::uint32_t>(workload.update_probes.size()),
                    rep_mode(rep), state, cfg)};
            const auto address_entering = Dispatch{
                bench.address_pipeline(),
                addr_entering_set,
                make_push(
                    static_cast<std::uint32_t>(workload.entering_probes.size()),
                    rep_mode(rep), state, cfg)};

            auto storage_dispatch = [&](VkDescriptorSet set, std::uint32_t count, std::uint32_t op) {
                return Dispatch{
                    bench.storage_pipeline(rep),
                    set,
                    make_push(count, op, state, cfg)};
            };

            const auto lookup_static = storage_dispatch(
                lookup_static_set, static_cast<std::uint32_t>(workload.probes.size()), 2u);
            const auto lookup_dynamic = storage_dispatch(
                lookup_dynamic_set, static_cast<std::uint32_t>(workload.probes.size()), 2u);
            const auto update_static = storage_dispatch(
                update_static_set, static_cast<std::uint32_t>(workload.update_probes.size()), 3u);
            const auto update_dynamic = storage_dispatch(
                update_dynamic_set, static_cast<std::uint32_t>(workload.update_probes.size()), 3u);
            const auto invalidate = storage_dispatch(
                invalidate_set, static_cast<std::uint32_t>(workload.invalidate_probes.size()), 4u);

            const auto evict = rep == Rep::ProbeHash
                ? storage_dispatch(
                    evict_probe_set, static_cast<std::uint32_t>(workload.leaving_probes.size()), 5u)
                : storage_dispatch(
                    evict_brick_set, static_cast<std::uint32_t>(workload.leaving_bricks.size()), 5u);

            const auto reserve_static = rep == Rep::ProbeHash
                ? storage_dispatch(
                    reserve_probe_static_set, static_cast<std::uint32_t>(workload.probes.size()), 0u)
                : storage_dispatch(
                    reserve_brick_set, static_cast<std::uint32_t>(workload.active_bricks.size()), 0u);
            const auto reserve_dynamic = rep == Rep::ProbeHash
                ? storage_dispatch(
                    reserve_probe_dynamic_set, static_cast<std::uint32_t>(workload.probes.size()), 0u)
                : reserve_static;
            const auto populate_static = storage_dispatch(
                lookup_static_set, static_cast<std::uint32_t>(workload.probes.size()), 1u);
            const auto populate_dynamic = storage_dispatch(
                lookup_dynamic_set, static_cast<std::uint32_t>(workload.probes.size()), 1u);
            const auto lookup_entering = storage_dispatch(
                lookup_entering_set, static_cast<std::uint32_t>(workload.entering_probes.size()), 2u);
            const auto reserve_entering = rep == Rep::ProbeHash
                ? storage_dispatch(
                    populate_entering_dynamic_set,
                    static_cast<std::uint32_t>(workload.entering_probes.size()), 0u)
                : storage_dispatch(
                    reserve_entering_brick_set,
                    static_cast<std::uint32_t>(workload.entering_bricks.size()), 6u);
            const auto finalize_reclaimed = storage_dispatch(
                reserve_entering_brick_set, 1u, 7u);
            const auto populate_entering = storage_dispatch(
                populate_entering_dynamic_set,
                static_cast<std::uint32_t>(workload.entering_probes.size()), 1u);

            // Producer address generation: no storage mutation and no manufactured ordering.
            const auto producer_us = bench.measure({address_all}, {}, cfg.iterations);
            const auto gpu_addresses =
                download_addresses(bench, dynamic_all_addr, all_addr.size());
            const bool producer_ok = addresses_equal(all_addr, gpu_addresses);
            rows.push_back({
                rep_name(rep), occupancy, "producer-address",
                static_cast<std::uint32_t>(workload.probes.size()),
                state.persistent_bytes, scratch_bytes,
                workload.probes.size() * sizeof(Unit),
                producer_us, 0u, producer_ok});
            all_correct = all_correct && producer_ok;

            // Lookup-only baseline.
            bench.copy_once(baseline_reset(state));
            const auto lookup_us = bench.measure({lookup_static}, {}, cfg.iterations);
            const auto lookup_values =
                download_u32(bench, output, workload.probes.size());
            std::vector<std::uint32_t> expected_base;
            expected_base.reserve(all_addr.size());
            for (const auto& a : all_addr) expected_base.push_back(a.payload);
            const bool lookup_ok = lookup_values == expected_base;
            rows.push_back({
                rep_name(rep), occupancy, "lookup",
                static_cast<std::uint32_t>(workload.probes.size()),
                state.persistent_bytes, scratch_bytes,
                workload.probes.size() * sizeof(Unit),
                lookup_us, checksum(lookup_values), lookup_ok});
            all_correct = all_correct && lookup_ok;

            // End-to-end producer address + lookup.
            bench.copy_once(baseline_reset(state));
            const auto e2e_lookup_us =
                bench.measure({address_all, lookup_dynamic}, {}, cfg.iterations);
            const auto e2e_lookup_values =
                download_u32(bench, output, workload.probes.size());
            const bool e2e_lookup_ok = e2e_lookup_values == expected_base;
            rows.push_back({
                rep_name(rep), occupancy, "producer+lookup",
                static_cast<std::uint32_t>(workload.probes.size()),
                state.persistent_bytes, scratch_bytes,
                workload.probes.size() * sizeof(Unit),
                e2e_lookup_us, checksum(e2e_lookup_values), e2e_lookup_ok});
            all_correct = all_correct && e2e_lookup_ok;

            std::unordered_set<std::uint32_t> update_keys;
            for (const auto& a : update_addr) update_keys.insert(a.probe_key);
            std::vector<std::uint32_t> expected_updated = expected_base;
            for (std::size_t i = 0; i < all_addr.size(); ++i) {
                if (update_keys.contains(all_addr[i].probe_key)) {
                    expected_updated[i] ^= kUpdateXor;
                }
            }

            const auto update_us =
                bench.measure({update_static}, baseline_reset(state), cfg.iterations);
            bench.execute({lookup_static});
            auto update_values = download_u32(bench, output, workload.probes.size());
            const auto update_counters = download_counters(bench, state.counters);
            const bool update_ok =
                update_values == expected_updated &&
                allocator_ok(
                    rep, update_counters,
                    static_cast<std::uint32_t>(workload.active_bricks.size()), true);
            rows.push_back({
                rep_name(rep), occupancy, "update",
                static_cast<std::uint32_t>(workload.update_probes.size()),
                state.persistent_bytes, scratch_bytes,
                workload.update_probes.size() * sizeof(Unit),
                update_us, checksum(update_values), update_ok});
            all_correct = all_correct && update_ok;

            const auto e2e_update_us =
                bench.measure({address_update, update_dynamic}, baseline_reset(state), cfg.iterations);
            bench.execute({lookup_static});
            auto e2e_update_values = download_u32(bench, output, workload.probes.size());
            const auto e2e_update_counters = download_counters(bench, state.counters);
            const bool e2e_update_ok =
                e2e_update_values == expected_updated &&
                allocator_ok(
                    rep, e2e_update_counters,
                    static_cast<std::uint32_t>(workload.active_bricks.size()), true);
            rows.push_back({
                rep_name(rep), occupancy, "producer+update",
                static_cast<std::uint32_t>(workload.update_probes.size()),
                state.persistent_bytes, scratch_bytes,
                workload.update_probes.size() * sizeof(Unit),
                e2e_update_us, checksum(e2e_update_values), e2e_update_ok});
            all_correct = all_correct && e2e_update_ok;

            std::unordered_set<std::uint32_t> invalid_keys;
            for (const auto& a : invalidate_addr) invalid_keys.insert(a.probe_key);
            auto expected_invalidated = expected_base;
            for (std::size_t i = 0; i < all_addr.size(); ++i) {
                if (invalid_keys.contains(all_addr[i].probe_key)) expected_invalidated[i] = 0u;
            }
            const auto invalidate_us =
                bench.measure({invalidate}, baseline_reset(state), cfg.iterations);
            bench.execute({lookup_static});
            auto invalid_values = download_u32(bench, output, workload.probes.size());
            const auto invalidate_counters = download_counters(bench, state.counters);
            const bool invalidate_ok =
                invalid_values == expected_invalidated &&
                allocator_ok(
                    rep, invalidate_counters,
                    static_cast<std::uint32_t>(workload.active_bricks.size()), true);
            rows.push_back({
                rep_name(rep), occupancy, "invalidation",
                static_cast<std::uint32_t>(workload.invalidate_probes.size()),
                state.persistent_bytes, scratch_bytes,
                workload.invalidate_probes.size() * sizeof(Unit),
                invalidate_us, checksum(invalid_values), invalidate_ok});
            all_correct = all_correct && invalidate_ok;

            std::unordered_set<std::uint32_t> leaving_keys;
            for (const auto& a : leaving_addr) leaving_keys.insert(a.probe_key);
            auto expected_evicted = expected_base;
            for (std::size_t i = 0; i < all_addr.size(); ++i) {
                if (leaving_keys.contains(all_addr[i].probe_key)) expected_evicted[i] = 0u;
            }
            const auto evict_us =
                bench.measure({evict}, baseline_reset(state), cfg.iterations);
            bench.execute({lookup_static});
            auto evicted_values = download_u32(bench, output, workload.probes.size());
            const auto evict_counters = download_counters(bench, state.counters);
            const bool evict_ok =
                evicted_values == expected_evicted &&
                evict_counters[1] == 0u &&
                (rep == Rep::ProbeHash ||
                    evict_counters[2] == workload.leaving_bricks.size());
            rows.push_back({
                rep_name(rep), occupancy, "eviction",
                rep == Rep::ProbeHash
                    ? static_cast<std::uint32_t>(workload.leaving_probes.size())
                    : static_cast<std::uint32_t>(workload.leaving_bricks.size()),
                state.persistent_bytes, scratch_bytes,
                rep == Rep::ProbeHash
                    ? workload.leaving_probes.size() * sizeof(Unit)
                    : workload.leaving_bricks.size() * sizeof(Unit),
                evict_us, checksum(evicted_values), evict_ok});
            all_correct = all_correct && evict_ok;

            // Dynamic one-brick X shift: evict the leaving plane, generate the
            // entering probe addresses, reuse residency capacity, and repopulate.
            std::vector<Dispatch> churn_sequence{
                evict,
                address_entering,
                reserve_entering,
            };
            if (rep != Rep::ProbeHash) {
                churn_sequence.push_back(finalize_reclaimed);
            }
            churn_sequence.push_back(populate_entering);
            const auto churn_us = bench.measure(
                churn_sequence, baseline_reset(state), cfg.iterations);
            bench.execute({lookup_static});
            const auto churn_old_values =
                download_u32(bench, output, workload.probes.size());
            bench.execute({lookup_entering});
            const auto churn_new_values =
                download_u32(bench, output, workload.entering_probes.size());
            std::vector<std::uint32_t> expected_entering;
            expected_entering.reserve(entering_addr.size());
            for (const auto& a : entering_addr) expected_entering.push_back(a.payload);
            const auto churn_counters = download_counters(bench, state.counters);
            const bool churn_ok =
                churn_old_values == expected_evicted &&
                churn_new_values == expected_entering &&
                allocator_ok(
                    rep, churn_counters,
                    static_cast<std::uint32_t>(workload.active_bricks.size()), true);
            rows.push_back({
                rep_name(rep), occupancy, "residency-churn-e2e",
                static_cast<std::uint32_t>(workload.entering_probes.size()),
                state.persistent_bytes, scratch_bytes,
                (rep == Rep::ProbeHash
                    ? workload.leaving_probes.size() * sizeof(Unit)
                    : workload.leaving_bricks.size() * sizeof(Unit)) +
                    workload.entering_probes.size() * sizeof(Unit) +
                    (rep == Rep::ProbeHash
                        ? 0u
                        : workload.entering_bricks.size() * sizeof(Unit)),
                churn_us,
                checksum(churn_old_values) + checksum(churn_new_values),
                churn_ok});
            all_correct = all_correct && churn_ok;

            // Empty -> residency map/key allocation only.
            const auto allocation_us =
                bench.measure({reserve_static}, empty_reset(state), cfg.iterations);
            // Populate outside the measured allocation region, then verify every probe resolves.
            bench.execute({populate_static, lookup_static});
            auto allocation_values = download_u32(bench, output, workload.probes.size());
            const auto allocation_counters = download_counters(bench, state.counters);
            const bool allocation_ok =
                allocation_values == expected_base &&
                allocator_ok(
                    rep, allocation_counters,
                    static_cast<std::uint32_t>(workload.active_bricks.size()), true);
            rows.push_back({
                rep_name(rep), occupancy, "allocation-residency",
                rep == Rep::ProbeHash
                    ? static_cast<std::uint32_t>(workload.probes.size())
                    : static_cast<std::uint32_t>(workload.active_bricks.size()),
                state.persistent_bytes, scratch_bytes,
                rep == Rep::ProbeHash
                    ? workload.probes.size() * sizeof(Unit)
                    : workload.active_bricks.size() * sizeof(Unit),
                allocation_us, checksum(allocation_values), allocation_ok});
            all_correct = all_correct && allocation_ok;

            // Empty -> producer address + allocation/residency + payload population.
            std::vector<Dispatch> build_sequence;
            build_sequence.push_back(address_all);
            build_sequence.push_back(reserve_dynamic);
            build_sequence.push_back(populate_dynamic);
            const auto build_us =
                bench.measure(build_sequence, empty_reset(state), cfg.iterations);
            bench.execute({lookup_static});
            auto build_values = download_u32(bench, output, workload.probes.size());
            const auto build_counters = download_counters(bench, state.counters);
            const bool build_ok =
                build_values == expected_base &&
                allocator_ok(
                    rep, build_counters,
                    static_cast<std::uint32_t>(workload.active_bricks.size()), true);
            rows.push_back({
                rep_name(rep), occupancy, "initial-build-e2e",
                static_cast<std::uint32_t>(workload.probes.size()),
                state.persistent_bytes, scratch_bytes,
                workload.probes.size() * sizeof(Unit) +
                    (rep == Rep::ProbeHash ? 0u : workload.active_bricks.size() * sizeof(Unit)),
                build_us, checksum(build_values), build_ok});
            all_correct = all_correct && build_ok;

            bench.context().destroy_buffer(output);
            bench.context().destroy_buffer(dynamic_entering_addr);
            bench.context().destroy_buffer(dynamic_update_addr);
            bench.context().destroy_buffer(dynamic_all_addr);
            bench.context().destroy_buffer(static_entering_addr);
            bench.context().destroy_buffer(static_leaving_addr);
            bench.context().destroy_buffer(static_invalidate_addr);
            bench.context().destroy_buffer(static_update_addr);
            bench.context().destroy_buffer(static_all_addr);
            bench.context().destroy_buffer(entering_bricks);
            bench.context().destroy_buffer(leaving_bricks);
            bench.context().destroy_buffer(active_bricks);
            bench.context().destroy_buffer(entering_probes);
            bench.context().destroy_buffer(leaving_probes);
            bench.context().destroy_buffer(invalidate_probes);
            bench.context().destroy_buffer(update_probes);
            bench.context().destroy_buffer(probes);
            destroy_state(bench, state);
        }
    }

    write_rows(rows);
    if (!all_correct) {
        std::cerr << "fatal: C001b correctness gate failed; timing evidence is invalid\n";
        return 2;
    }
    return 0;
}

} // namespace phos::gi::lane_c

int main(int argc, char** argv) {
    try {
        return phos::gi::lane_c::run(argc, argv);
    } catch (const std::exception& e) {
        std::cerr << "fatal: " << e.what() << '\n';
        return 1;
    }
}

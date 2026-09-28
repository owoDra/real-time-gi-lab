#pragma once
#include <cstdint>
#include <vector>

namespace phos::gi {

struct Vec3 {
    float x{};
    float y{};
    float z{};
};

struct Query {
    // M0 uses a unique, non-zero logical cell identifier so every cache
    // representation is required to return exactly the same semantic payload.
    std::uint32_t key{};
    std::uint32_t page_id{};
    std::uint32_t local_index{};
    std::uint32_t pad{};
};
static_assert(sizeof(Query) == 16);

struct Workload {
    // Query locality is an independent experimental axis from cache
    // representation. Every vector contains exactly the same logical queries.
    std::vector<Query> source;
    std::vector<Query> randomized;
    std::vector<Query> page_grouped;

    std::vector<std::uint32_t> hash_keys;
    std::vector<std::uint32_t> hash_payload;
    std::vector<std::uint32_t> page_table;
    std::vector<std::uint32_t> paged_payload;

    std::uint32_t hash_mask{};
    std::uint32_t hash_max_probe{1};
    std::uint32_t page_size{64};
    std::uint32_t active_cells{};
    std::uint64_t expected_checksum{};
};

} // namespace phos::gi

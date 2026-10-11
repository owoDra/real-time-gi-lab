#include "m001_contract.hpp"

#include <algorithm>
#include <array>
#include <cstring>
#include <stdexcept>
#include <unordered_map>
#include <vector>

namespace phos::gi::research::lane_m {
namespace {

constexpr std::array<M001ScenarioSpec, 4> kSpecs{{
    {
        M001Scenario::TopologyChangingObjectLocal,
        "topology-changing-object-local",
        "medium-global-representative",
        796U,
        0.25,
        "global",
        true,
    },
    {
        M001Scenario::HighChurnGlobal,
        "high-churn-global",
        "large-global-high",
        8192U,
        0.50,
        "global",
        true,
    },
    {
        M001Scenario::HighChurnLocal,
        "high-churn-local",
        "large-local-high",
        8192U,
        0.50,
        "local",
        true,
    },
    {
        M001Scenario::StableNoChangeGuard,
        "stable-no-change-guard",
        "medium-global-representative",
        796U,
        0.0,
        "none",
        false,
    },
}};

[[nodiscard]] bool same_triangle(
    const lane_b::Triangle& a,
    const lane_b::Triangle& b) noexcept {
    return
        a.v0.x == b.v0.x && a.v0.y == b.v0.y && a.v0.z == b.v0.z &&
        a.v1.x == b.v1.x && a.v1.y == b.v1.y && a.v1.z == b.v1.z &&
        a.v2.x == b.v2.x && a.v2.y == b.v2.y && a.v2.z == b.v2.z &&
        a.primitive_id == b.primitive_id &&
        a.material_id == b.material_id &&
        a.instance_id == b.instance_id &&
        a.two_sided == b.two_sided;
}

void hash_bytes(
    std::uint64_t& hash,
    const void* data,
    std::size_t bytes) noexcept {
    const auto* ptr = static_cast<const unsigned char*>(data);
    for (std::size_t index = 0; index < bytes; ++index) {
        hash ^= ptr[index];
        hash *= 1099511628211ULL;
    }
}

[[nodiscard]] std::uint64_t geometry_digest(
    std::span<const lane_b::Triangle> triangles) {
    std::vector<const lane_b::Triangle*> ordered;
    ordered.reserve(triangles.size());
    for (const auto& triangle : triangles) {
        ordered.push_back(&triangle);
    }
    std::sort(
        ordered.begin(),
        ordered.end(),
        [](const lane_b::Triangle* a, const lane_b::Triangle* b) {
            return a->primitive_id < b->primitive_id;
        });

    std::uint64_t hash = 1469598103934665603ULL;
    const auto count = static_cast<std::uint64_t>(triangles.size());
    hash_bytes(hash, &count, sizeof(count));
    for (const auto* triangle : ordered) {
        hash_bytes(hash, &triangle->v0.x, sizeof(float));
        hash_bytes(hash, &triangle->v0.y, sizeof(float));
        hash_bytes(hash, &triangle->v0.z, sizeof(float));
        hash_bytes(hash, &triangle->v1.x, sizeof(float));
        hash_bytes(hash, &triangle->v1.y, sizeof(float));
        hash_bytes(hash, &triangle->v1.z, sizeof(float));
        hash_bytes(hash, &triangle->v2.x, sizeof(float));
        hash_bytes(hash, &triangle->v2.y, sizeof(float));
        hash_bytes(hash, &triangle->v2.z, sizeof(float));
        hash_bytes(hash, &triangle->primitive_id, sizeof(triangle->primitive_id));
        hash_bytes(hash, &triangle->material_id, sizeof(triangle->material_id));
        hash_bytes(hash, &triangle->instance_id, sizeof(triangle->instance_id));
        const std::uint8_t two_sided = triangle->two_sided ? 1U : 0U;
        hash_bytes(hash, &two_sided, sizeof(two_sided));
    }
    return hash;
}

} // namespace

M001Scenario parse_m001_scenario(std::string_view value) {
    for (const auto& spec : kSpecs) {
        if (value == spec.name) {
            return spec.scenario;
        }
    }
    throw std::runtime_error("unknown Lane M M001 scenario");
}

const M001ScenarioSpec& m001_scenario_spec(M001Scenario scenario) {
    for (const auto& spec : kSpecs) {
        if (spec.scenario == scenario) {
            return spec;
        }
    }
    throw std::runtime_error("invalid Lane M M001 scenario");
}

void validate_m001_profile(
    M001Scenario scenario,
    std::string_view profile) {
    const auto& spec = m001_scenario_spec(scenario);
    if (profile != spec.profile) {
        throw std::runtime_error(
            "Lane M scenario/profile identity mismatch");
    }
}

M001MutationEvidence m001_mutation_evidence(
    std::span<const lane_b::Triangle> from,
    std::span<const lane_b::Triangle> to) {
    if (from.empty() || to.empty()) {
        throw std::runtime_error(
            "Lane M mutation evidence requires non-empty geometry");
    }

    std::unordered_map<std::uint32_t, const lane_b::Triangle*> old_by_id;
    std::unordered_map<std::uint32_t, const lane_b::Triangle*> new_by_id;
    old_by_id.reserve(from.size());
    new_by_id.reserve(to.size());

    for (const auto& triangle : from) {
        if (!old_by_id.emplace(triangle.primitive_id, &triangle).second) {
            throw std::runtime_error(
                "Lane M old geometry has duplicate primitive id");
        }
    }
    for (const auto& triangle : to) {
        if (!new_by_id.emplace(triangle.primitive_id, &triangle).second) {
            throw std::runtime_error(
                "Lane M new geometry has duplicate primitive id");
        }
    }

    M001MutationEvidence result{};
    result.from_primitive_count =
        static_cast<std::uint32_t>(from.size());
    result.to_primitive_count =
        static_cast<std::uint32_t>(to.size());
    result.from_geometry_digest = geometry_digest(from);
    result.to_geometry_digest = geometry_digest(to);

    for (const auto& [primitive_id, triangle] : old_by_id) {
        const auto found = new_by_id.find(primitive_id);
        if (found == new_by_id.end()) {
            ++result.deleted_count;
        } else if (!same_triangle(*triangle, *found->second)) {
            ++result.modified_count;
        }
    }
    for (const auto& [primitive_id, triangle] : new_by_id) {
        (void)triangle;
        if (!old_by_id.contains(primitive_id)) {
            ++result.inserted_count;
        }
    }

    result.topology_changed =
        result.from_primitive_count != result.to_primitive_count ||
        result.inserted_count != 0U ||
        result.deleted_count != 0U;
    return result;
}

} // namespace phos::gi::research::lane_m

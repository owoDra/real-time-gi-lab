#pragma once

#include "../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal/b002_scene.hpp"

#include <cstdint>
#include <span>
#include <string_view>

namespace phos::gi::research::lane_m {

namespace lane_b = phos::gi::research::lane_b;

enum class M001Scenario {
    TopologyChangingObjectLocal,
    HighChurnGlobal,
    HighChurnLocal,
    StableNoChangeGuard,
};

struct M001ScenarioSpec {
    M001Scenario scenario{};
    const char* name{};
    const char* profile{};
    std::uint32_t base_primitive_count{};
    double nominal_replacement_fraction{};
    const char* locality{};
    bool topology_mutation_required{};
};

struct M001MutationEvidence {
    std::uint32_t from_primitive_count{};
    std::uint32_t to_primitive_count{};
    std::uint32_t inserted_count{};
    std::uint32_t deleted_count{};
    std::uint32_t modified_count{};
    std::uint64_t from_geometry_digest{};
    std::uint64_t to_geometry_digest{};
    bool topology_changed{};
};

[[nodiscard]] M001Scenario parse_m001_scenario(std::string_view value);
[[nodiscard]] const M001ScenarioSpec& m001_scenario_spec(M001Scenario scenario);
void validate_m001_profile(M001Scenario scenario, std::string_view profile);
[[nodiscard]] M001MutationEvidence m001_mutation_evidence(
    std::span<const lane_b::Triangle> from,
    std::span<const lane_b::Triangle> to);

} // namespace phos::gi::research::lane_m

#include "m001_contract.hpp"

#include <stdexcept>
#include <vector>

namespace lane_b = phos::gi::research::lane_b;
namespace lane_m = phos::gi::research::lane_m;

namespace {

lane_b::Triangle triangle(std::uint32_t id, float x = 0.0F) {
    lane_b::Triangle value{};
    value.v0 = {x, 0.0F, 0.0F};
    value.v1 = {x, 1.0F, 0.0F};
    value.v2 = {x, 0.0F, 1.0F};
    value.primitive_id = id;
    value.material_id = 7U;
    value.instance_id = 11U;
    value.two_sided = true;
    return value;
}

void require(bool value, const char* message) {
    if (!value) {
        throw std::runtime_error(message);
    }
}

} // namespace

int main() {
    const auto topology = lane_m::parse_m001_scenario(
        "topology-changing-object-local");
    const auto high_global =
        lane_m::parse_m001_scenario("high-churn-global");
    const auto high_local =
        lane_m::parse_m001_scenario("high-churn-local");
    const auto stable =
        lane_m::parse_m001_scenario("stable-no-change-guard");

    require(
        lane_m::m001_scenario_spec(topology).base_primitive_count == 796U,
        "topology scenario primitive count drift");
    require(
        lane_m::m001_scenario_spec(high_global).nominal_replacement_fraction == 0.50,
        "global high-churn fraction drift");
    require(
        lane_m::m001_scenario_spec(high_local).locality ==
            std::string_view("local"),
        "local high-churn locality drift");
    require(
        !lane_m::m001_scenario_spec(stable).topology_mutation_required,
        "stable guard must not request mutation");

    const std::vector<lane_b::Triangle> a{
        triangle(1U), triangle(2U)};
    const std::vector<lane_b::Triangle> same{
        triangle(1U), triangle(2U)};
    const std::vector<lane_b::Triangle> changed{
        triangle(1U, 0.25F), triangle(3U), triangle(4U)};

    const auto stable_evidence =
        lane_m::m001_mutation_evidence(a, same);
    require(!stable_evidence.topology_changed, "stable topology false positive");
    require(
        stable_evidence.from_geometry_digest ==
            stable_evidence.to_geometry_digest,
        "stable geometry digest mismatch");

    const auto changed_evidence =
        lane_m::m001_mutation_evidence(a, changed);
    require(changed_evidence.topology_changed, "topology mutation not detected");
    require(changed_evidence.inserted_count == 2U, "insert count mismatch");
    require(changed_evidence.deleted_count == 1U, "delete count mismatch");
    require(changed_evidence.modified_count == 1U, "modified count mismatch");
    require(
        changed_evidence.from_geometry_digest !=
            changed_evidence.to_geometry_digest,
        "mutation geometry digest unchanged");
    return 0;
}

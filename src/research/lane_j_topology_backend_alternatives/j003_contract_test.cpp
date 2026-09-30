#include "j003_clustered_bvh.hpp"
#include "j003_reference.hpp"
#include "j003_transition.hpp"

#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace lane_j = phos::gi::research::lane_j;

namespace {

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

std::vector<lane_j::Triangle> make_triangles(std::uint32_t count) {
    std::vector<lane_j::Triangle> triangles;
    triangles.reserve(count);
    for (std::uint32_t i = 0U; i < count; ++i) {
        const auto x = float(i % 16U);
        const auto z = float(i / 16U);
        triangles.push_back({
            {x, 0.0F, z},
            {x + 0.8F, 0.0F, z},
            {x, 0.0F, z + 0.8F},
            1000U + i,
            7U,
            3U,
            true,
        });
    }
    return triangles;
}

std::vector<lane_j::Triangle> make_linear_triangles(
    std::uint32_t count,
    std::uint32_t first_id = 0U) {
    std::vector<lane_j::Triangle> triangles;
    triangles.reserve(count);
    for (std::uint32_t i = 0U; i < count; ++i) {
        const auto x = float(i) * 2.0F;
        triangles.push_back({
            {x, 0.0F, 0.0F},
            {x + 0.8F, 0.0F, 0.0F},
            {x, 0.0F, 0.8F},
            first_id + i,
            7U,
            3U,
            true,
        });
    }
    return triangles;
}

} // namespace

int main() {
    try {
        const auto triangles = make_triangles(97U);
        const auto bvh = lane_j::build_initial_clustered_bvh(triangles);

        if (bvh.summary.cluster_count != 3U) {
            fail("expected 3 initial clusters");
        }
        if (bvh.summary.occupancy_max != 48U ||
            bvh.summary.occupancy_min != 1U) {
            fail("initial occupancy contract drift");
        }
        if (bvh.summary.upper_node_count != 5U) {
            fail("upper binary tree node count drift");
        }
        if (bvh.summary.micro_node_count != 191U) {
            fail("micro binary tree node count drift");
        }
        if (bvh.upper_root >= bvh.upper_nodes.size()) {
            fail("upper root out of range");
        }

        const lane_j::Ray ray{
            {0.2F, 2.0F, 0.2F},
            {0.0F, -1.0F, 0.0F},
            10.0F,
        };
        const auto hit = lane_j::trace_reference(triangles, ray);
        if (!hit.hit ||
            hit.primitive_id != 1000U ||
            std::abs(hit.t - 2.0F) > lane_j::kHitAbsTol) {
            fail("B001-compatible reference hit contract drift");
        }

        // Empty-cluster retirement regression: one-dimensional Morton order
        // makes the initial 48/48/48 ownership deterministic.
        const auto retire_source = make_linear_triangles(144U);
        lane_j::ClusterTransitionState retire_state(retire_source);
        std::vector<lane_j::Triangle> retire_next(
            retire_source.begin(),
            retire_source.begin() + 20);
        const auto retire_stats = retire_state.update(retire_next);
        if (retire_stats.retired_empty_cluster_count != 2U) {
            fail("transition empty-cluster retirement contract drift");
        }
        if (retire_stats.unaffected_cluster_rebuild_count != 0U ||
            retire_stats.occupancy_min == 0U ||
            retire_stats.occupancy_max > lane_j::kClusterMaximum) {
            fail("retirement transition invariant drift");
        }

        // Split regression: one initial cluster receives all inserted geometry,
        // guaranteeing post-assignment overflow before the deterministic split.
        const auto split_source = make_linear_triangles(48U);
        lane_j::ClusterTransitionState split_state(split_source);
        auto split_next = split_source;
        for (std::uint32_t i = 0U; i < 40U; ++i) {
            const float x = 0.01F * float(i);
            split_next.push_back({
                {x, 0.1F, 0.0F},
                {x + 0.005F, 0.1F, 0.0F},
                {x, 0.1F, 0.005F},
                5000U + i,
                7U,
                3U,
                true,
            });
        }
        const auto split_stats = split_state.update(split_next);
        if (split_stats.split_count == 0U) {
            fail("transition split path was not exercised");
        }
        if (split_stats.unaffected_cluster_rebuild_count != 0U ||
            split_stats.occupancy_min == 0U ||
            split_stats.occupancy_max > lane_j::kClusterMaximum) {
            fail("split transition invariant drift");
        }

        std::cout << "J003 host contract PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "fatal: " << error.what() << "\n";
        return 1;
    }
}

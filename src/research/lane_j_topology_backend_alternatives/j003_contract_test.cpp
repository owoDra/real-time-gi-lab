#include "j003_clustered_bvh.hpp"
#include "j003_reference.hpp"
#include "j003_persistent_layout.hpp"
#include "j003_transition.hpp"

#include <algorithm>
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

        // Persistent slot policy: initial 48-triangle state uses one physical
        // slot, then a 248-triangle transition forces deterministic 1->4
        // capacity growth. Resize accounting must include simultaneous old/new
        // residency, and all active logical clusters must have unique slots.
        const auto persistent_source = make_linear_triangles(48U, 10000U);
        lane_j::ClusterTransitionState persistent_state(persistent_source);
        lane_j::PersistentClusterLayout persistent_layout(persistent_state);
        if (persistent_layout.slot_capacity() != 1U) {
            fail("persistent initial power-of-two capacity drift");
        }
        auto persistent_next = persistent_source;
        for (std::uint32_t i = 0U; i < 200U; ++i) {
            const float x = 0.003F * float(i);
            persistent_next.push_back({
                {x, 0.2F, 0.0F},
                {x + 0.001F, 0.2F, 0.0F},
                {x, 0.2F, 0.001F},
                20000U + i,
                7U,
                3U,
                true,
            });
        }
        const auto persistent_stats =
            persistent_state.update(persistent_next);
        const auto layout_update =
            persistent_layout.synchronize(
                persistent_state,
                persistent_stats);
        if (!layout_update.resized ||
            layout_update.slot_capacity != 4U ||
            layout_update.active_cluster_count != 4U) {
            fail("persistent capacity growth contract drift");
        }
        if (layout_update.resize_old_new_overlap_logical_bytes <=
            layout_update.candidate_persistent_logical_bytes) {
            fail("persistent resize overlap was not accounted");
        }
        std::vector<std::uint32_t> physical_slots;
        for (const auto& cluster : persistent_state.clusters()) {
            physical_slots.push_back(
                persistent_layout.physical_slot(cluster.cluster_id));
        }
        std::sort(physical_slots.begin(), physical_slots.end());
        if (std::adjacent_find(
                physical_slots.begin(),
                physical_slots.end()) != physical_slots.end()) {
            fail("persistent logical clusters share a physical slot");
        }

        // Merge-source release regression: cluster 1 becomes underfilled and
        // legally merges into the short third cluster. Its logical ID must lose
        // physical ownership immediately.
        const auto merge_source = make_linear_triangles(110U, 30000U);
        lane_j::ClusterTransitionState merge_state(merge_source);
        lane_j::PersistentClusterLayout merge_layout(merge_state);
        std::vector<lane_j::Triangle> merge_next;
        merge_next.insert(
            merge_next.end(),
            merge_source.begin(),
            merge_source.begin() + 68);
        merge_next.insert(
            merge_next.end(),
            merge_source.begin() + 96,
            merge_source.end());
        const auto merge_stats = merge_state.update(merge_next);
        if (merge_stats.merge_count == 0U ||
            merge_stats.released_cluster_ids.empty()) {
            fail("merge-source release path was not exercised");
        }
        merge_layout.synchronize(merge_state, merge_stats);
        for (const auto released : merge_stats.released_cluster_ids) {
            bool still_owned = true;
            try {
                (void)merge_layout.physical_slot(released);
            } catch (const std::runtime_error&) {
                still_owned = false;
            }
            if (still_owned) {
                fail("released logical cluster retained physical ownership");
            }
        }

        std::cout << "J003 host contract PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "fatal: " << error.what() << "\n";
        return 1;
    }
}

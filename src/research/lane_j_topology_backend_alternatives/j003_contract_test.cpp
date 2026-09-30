#include "j003_clustered_bvh.hpp"
#include "j003_reference.hpp"

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

        std::cout << "J003 host contract PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "fatal: " << error.what() << "\n";
        return 1;
    }
}

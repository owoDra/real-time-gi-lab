#include "hierarchical_stratabrick.hpp"
#include "lane_a_stream_v1.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <span>
#include <vector>

using namespace phos::gi::research::lane_b;

int main() {
    std::vector<Triangle> triangles;
    const auto add_triangle =
        [&](float x, float z, std::uint32_t id) {
            triangles.push_back({
                {x - 1.0F, -1.0F, z},
                {x + 1.0F, -1.0F, z},
                {x, 1.0F, z},
                id,
                id + 10U,
                id + 20U,
                true,
            });
        };
    add_triangle(0.0F, 5.0F, 0U);
    add_triangle(9.0F, 12.0F, 1U);
    add_triangle(-8.0F, 18.0F, 2U);

    HierarchicalStrataBrick hierarchy(triangles, 8.0F);
    const std::vector<Ray> rays{
        {{0, 0, 0}, {0, 0, 1}, 30},
        {{9, 0, 0}, {0, 0, 1}, 30},
        {{-8, 0, 0}, {0, 0, 1}, 30},
        {{0, 5, 0}, {0, 1, 0}, 30},
    };
    for (const auto ray : rays) {
        const auto expected = trace_reference(triangles, ray);
        const auto actual = hierarchy.trace(ray);
        if (!equivalent_hit(expected, actual)) {
            std::cerr << "hierarchical static mismatch\n";
            return 2;
        }
    }

    const auto flat_before = hierarchy.flatten();
    if (flat_before.segments.size() != hierarchy.segment_count() ||
        flat_before.nodes.empty() ||
        flat_before.ordered_primitives.empty()) {
        std::cerr << "hierarchical flatten failed\n";
        return 3;
    }
    for (std::size_t index = 1; index < flat_before.segments.size(); ++index) {
        if (flat_before.segments[index].coord < flat_before.segments[index - 1].coord) {
            std::cerr << "hierarchical flatten is not deterministic by segment key\n";
            return 4;
        }
    }

    auto moved = triangles;
    moved[0].v0.x += 9.0F;
    moved[0].v1.x += 9.0F;
    moved[0].v2.x += 9.0F;
    const std::uint32_t moved_id = 0;
    const auto update = hierarchy.update(
        moved,
        std::span<const std::uint32_t>(&moved_id, 1));
    for (const auto ray : rays) {
        const auto expected = trace_reference(moved, ray);
        const auto actual = hierarchy.trace(ray);
        if (!equivalent_hit(expected, actual)) {
            std::cerr << "hierarchical update mismatch\n";
            return 5;
        }
    }

    LaneAReplayStreamV1 stream;
    stream.header.item_bytes = 64;
    stream.header.item_count = 1;
    stream.header.output_count = 1;
    stream.header.cascade_count = 1;
    stream.header.rays_per_probe = 1;
    stream.header.tile_width = 1;
    stream.header.tile_height = 1;
    stream.items.resize(1);

    auto& item = stream.items[0];
    item.interval_min = 2.0F;
    item.interval_max = 10.0F;
    item.dir_z = 1.0F;
    item.probe_px = 3.0F;
    item.probe_py = 4.0F;
    item.probe_pz = 5.0F;
    stream.header.workload_id =
        lane_a_workload_id(stream.items.data(), sizeof(LaneAWorkItemV1));

    const auto path =
        std::filesystem::temp_directory_path() / "phos-b002-smoke-stream.bin";
    {
        std::ofstream output(path, std::ios::binary);
        output.write(
            reinterpret_cast<const char*>(&stream.header),
            sizeof(stream.header));
        output.write(
            reinterpret_cast<const char*>(stream.items.data()),
            sizeof(LaneAWorkItemV1));
    }
    const auto loaded = load_lane_a_stream_v1(path);
    const auto replay_ray = lane_a_item_to_ray(loaded.items[0]);
    std::filesystem::remove(path);
    if (replay_ray.origin.z != 7.0F || replay_ray.t_max != 8.0F) {
        std::cerr << "Lane A interval mapping failed\n";
        return 6;
    }

    std::cout
        << "B002 contract smoke: PASS segments=" << hierarchy.segment_count()
        << " membership_changes=" << update.membership_changes << '\n';
    return 0;
}

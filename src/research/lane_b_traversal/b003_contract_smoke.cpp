#include "b003_macro_bvh8.hpp"
#include "b003_micro_bvh8.hpp"
#include "b003_quantized_bvh8.hpp"
#include "b003_triangle_packets.hpp"

#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace phos::gi::research::lane_b {
namespace {

[[nodiscard]] bool finite_bounds(
    const B003GpuMacroChild& child) noexcept {
    for (int axis = 0; axis < 3; ++axis) {
        if (!std::isfinite(child.bounds_min[axis]) ||
            !std::isfinite(child.bounds_max[axis]) ||
            child.bounds_min[axis] >
                child.bounds_max[axis]) {
            return false;
        }
    }
    return true;
}

void verify_payload(
    const HierarchicalFlatPayload& flat,
    const B003MacroBvh8Payload& payload) {
    if (flat.segments.empty()) {
        if (payload.root != kInvalidId ||
            !payload.nodes.empty() ||
            payload.segment_count != 0) {
            throw std::runtime_error(
                "empty B003 macro payload is not empty");
        }
        return;
    }

    if (payload.root >= payload.nodes.size()) {
        throw std::runtime_error(
            "B003 macro root is invalid");
    }
    if (payload.max_stack_entries > 32U) {
        throw std::runtime_error(
            "B003 smoke exceeds shader macro stack");
    }

    std::vector<std::uint32_t> expected;
    expected.reserve(flat.segments.size());
    for (const auto& segment : flat.segments) {
        expected.push_back(segment.root);
    }

    std::vector<std::uint32_t> observed;
    std::vector<bool> visited(
        payload.nodes.size(),
        false);
    std::vector<std::uint32_t> stack{
        payload.root};

    while (!stack.empty()) {
        const auto node_index = stack.back();
        stack.pop_back();
        if (node_index >= payload.nodes.size() ||
            visited[node_index]) {
            throw std::runtime_error(
                "B003 macro payload contains a cycle or invalid node");
        }
        visited[node_index] = true;

        for (const auto& child :
             payload.nodes[node_index].children) {
            if (child.data[0] == kInvalidId) {
                continue;
            }
            if (!finite_bounds(child)) {
                throw std::runtime_error(
                    "B003 macro payload contains invalid bounds");
            }
            if (child.data[1] == kB003MacroInternal) {
                stack.push_back(child.data[0]);
            } else if (
                child.data[1] ==
                kB003MacroSegment) {
                observed.push_back(child.data[0]);
            } else {
                throw std::runtime_error(
                    "B003 macro payload contains invalid child kind");
            }
        }
    }

    std::sort(expected.begin(), expected.end());
    std::sort(observed.begin(), observed.end());
    if (observed != expected) {
        throw std::runtime_error(
            "B003 macro payload changed segment-root membership");
    }
}


void verify_wide_payload(
    const HierarchicalFlatPayload& flat,
    const B003WideMicroPayload& payload) {
    if (payload.segment_count != flat.segments.size()) {
        throw std::runtime_error(
            "B003 wide payload changed segment count");
    }
    if (payload.max_stack_entries > 64U) {
        throw std::runtime_error(
            "B003 wide payload exceeds shader stack");
    }
    if (payload.hash_table.empty() ||
        payload.nodes.empty()) {
        throw std::runtime_error(
            "B003 wide payload unexpectedly empty");
    }

    std::size_t hash_roots = 0;
    for (const auto& entry : payload.hash_table) {
        if (entry.metadata[0] == kInvalidId) {
            continue;
        }
        ++hash_roots;
        if (entry.metadata[0] >= payload.nodes.size()) {
            throw std::runtime_error(
                "B003 wide hash root is invalid");
        }
    }
    if (hash_roots != flat.segments.size()) {
        throw std::runtime_error(
            "B003 wide hash changed occupied segment count");
    }

    for (std::uint32_t count = 1U;
         count <= 8U;
         ++count) {
        const auto token =
            b003_wide_leaf_token(12345U, count);
        if (!b003_wide_is_leaf(token) ||
            b003_wide_leaf_begin(token) != 12345U ||
            b003_wide_leaf_count(token) != count) {
            throw std::runtime_error(
                "B003 wide leaf token round trip failed");
        }
    }
}


[[nodiscard]] std::uint32_t lookup_wide_root(
    const B003WideMicroPayload& payload,
    SegmentCoord coord) {
    std::uint32_t slot =
        segment_hash(coord) & payload.hash_mask;
    for (std::uint32_t probe = 0U;
         probe < payload.hash_max_probe;
         ++probe) {
        const auto& entry =
            payload.hash_table.at(slot);
        if (entry.metadata[0] == kInvalidId) {
            return kInvalidId;
        }
        if (entry.coord[0] == coord.x &&
            entry.coord[1] == coord.y &&
            entry.coord[2] == coord.z) {
            return entry.metadata[0];
        }
        slot =
            (slot + 1U) & payload.hash_mask;
    }
    return kInvalidId;
}

void collect_binary_leaves(
    const HierarchicalFlatPayload& flat,
    std::uint32_t root,
    std::vector<std::pair<
        std::uint32_t,
        std::uint32_t>>& leaves) {
    std::vector<std::uint32_t> stack{root};
    while (!stack.empty()) {
        const auto index = stack.back();
        stack.pop_back();
        if (index >= flat.nodes.size()) {
            throw std::runtime_error(
                "B003 smoke binary root is invalid");
        }
        const auto& node = flat.nodes[index];
        if (node.left == kInvalidId) {
            leaves.emplace_back(
                node.begin,
                node.count);
        } else {
            stack.push_back(node.left);
            stack.push_back(node.right);
        }
    }
}

void collect_wide_leaves(
    const B003WideMicroPayload& payload,
    std::uint32_t root,
    std::vector<std::pair<
        std::uint32_t,
        std::uint32_t>>& leaves) {
    std::vector<std::uint32_t> stack{root};
    while (!stack.empty()) {
        const auto token = stack.back();
        stack.pop_back();
        if (b003_wide_is_leaf(token)) {
            leaves.emplace_back(
                b003_wide_leaf_begin(token),
                b003_wide_leaf_count(token));
            continue;
        }
        if (token >= payload.nodes.size()) {
            throw std::runtime_error(
                "B003 smoke wide token is invalid");
        }
        for (const auto& child :
             payload.nodes[token].children) {
            if (child.data[0] != kInvalidId) {
                stack.push_back(child.data[0]);
            }
        }
    }
}

void verify_wide_leaf_equivalence(
    const HierarchicalFlatPayload& flat,
    const B003WideMicroPayload& payload) {
    for (const auto& segment : flat.segments) {
        const auto wide_root =
            lookup_wide_root(
                payload,
                segment.coord);
        if (wide_root == kInvalidId) {
            throw std::runtime_error(
                "B003 wide payload lost a segment root");
        }

        std::vector<std::pair<
            std::uint32_t,
            std::uint32_t>> binary_leaves;
        std::vector<std::pair<
            std::uint32_t,
            std::uint32_t>> wide_leaves;
        collect_binary_leaves(
            flat,
            segment.root,
            binary_leaves);
        collect_wide_leaves(
            payload,
            wide_root,
            wide_leaves);
        std::sort(
            binary_leaves.begin(),
            binary_leaves.end());
        std::sort(
            wide_leaves.begin(),
            wide_leaves.end());
        if (binary_leaves != wide_leaves) {
            throw std::runtime_error(
                "B003 wide collapse changed binary leaf ranges");
        }
    }
}


void verify_quantized_payload(
    const B003WideMicroPayload& wide,
    const B003QuantizedMicroPayload& quantized) {
    if (quantized.nodes.size() != wide.nodes.size() ||
        quantized.ordered_primitives !=
            wide.ordered_primitives ||
        quantized.hash_table.size() !=
            wide.hash_table.size() ||
        quantized.hash_mask != wide.hash_mask ||
        quantized.hash_max_probe !=
            wide.hash_max_probe ||
        quantized.segment_count !=
            wide.segment_count) {
        throw std::runtime_error(
            "B003 quantization changed non-bound traversal topology");
    }

    constexpr float kTolerance = 1.0e-5F;
    for (std::size_t node_index = 0;
         node_index < wide.nodes.size();
         ++node_index) {
        const auto& source =
            wide.nodes[node_index];
        const auto& packed =
            quantized.nodes[node_index];

        std::uint32_t axis = 0U;
        bool have_axis = false;
        for (std::size_t slot = 0;
             slot < 8U;
             ++slot) {
            const auto& source_child =
                source.children[slot];
            const auto& packed_child =
                packed.children[slot];

            if (source_child.data[0] ==
                kInvalidId) {
                if (packed_child.packed[3] !=
                    kInvalidId) {
                    throw std::runtime_error(
                        "B003 quantization materialized an empty child");
                }
                continue;
            }

            if (packed_child.packed[3] !=
                source_child.data[0]) {
                throw std::runtime_error(
                    "B003 quantization changed child token");
            }

            if (!have_axis) {
                axis = source_child.data[1];
                have_axis = true;
            } else if (axis !=
                       source_child.data[1]) {
                throw std::runtime_error(
                    "B003 source wide node has inconsistent axis");
            }

            const auto decoded =
                b003_decode_quant_child(
                    packed,
                    packed_child);
            const float decoded_min[3]{
                decoded.min.x,
                decoded.min.y,
                decoded.min.z,
            };
            const float decoded_max[3]{
                decoded.max.x,
                decoded.max.y,
                decoded.max.z,
            };
            for (int component = 0;
                 component < 3;
                 ++component) {
                if (decoded_min[component] >
                        source_child
                            .bounds_min[component] +
                            kTolerance ||
                    decoded_max[component] <
                        source_child
                            .bounds_max[component] -
                            kTolerance) {
                    throw std::runtime_error(
                        "B003 quantized child is not conservative");
                }
            }
        }

        if (have_axis &&
            packed.metadata[0] != axis) {
            throw std::runtime_error(
                "B003 quantization changed node ordering axis");
        }
    }
}


void verify_packet_payload(
    const B003QuantizedMicroPayload& quantized,
    const B003PacketMicroPayload& packetized,
    const std::vector<Triangle>& triangles) {
    if (packetized.nodes.size() != quantized.nodes.size() ||
        packetized.hash_table.size() != quantized.hash_table.size() ||
        packetized.hash_mask != quantized.hash_mask ||
        packetized.hash_max_probe != quantized.hash_max_probe ||
        packetized.segment_count != quantized.segment_count ||
        packetized.source_leaf_count != packetized.packets.size()) {
        throw std::runtime_error(
            "B003 packetization changed non-leaf topology");
    }

    std::size_t observed_live = 0;
    for (std::size_t node_index = 0;
         node_index < quantized.nodes.size();
         ++node_index) {
        for (std::size_t slot = 0; slot < 8U; ++slot) {
            const auto source_token =
                quantized.nodes[node_index].children[slot].packed[3];
            const auto packet_token =
                packetized.nodes[node_index].children[slot].packed[3];

            if (source_token == kInvalidId) {
                if (packet_token != kInvalidId) {
                    throw std::runtime_error(
                        "B003 packetization materialized an empty child");
                }
                continue;
            }

            if (!b003_wide_is_leaf(source_token)) {
                if (packet_token != source_token) {
                    throw std::runtime_error(
                        "B003 packetization changed an internal token");
                }
                continue;
            }

            if (!b003_wide_is_leaf(packet_token) ||
                b003_wide_leaf_count(packet_token) !=
                    b003_wide_leaf_count(source_token)) {
                throw std::runtime_error(
                    "B003 packetization changed leaf count");
            }

            const auto begin =
                b003_wide_leaf_begin(source_token);
            const auto count =
                b003_wide_leaf_count(source_token);
            const auto packet_index =
                b003_wide_leaf_begin(packet_token);
            if (packet_index >= packetized.packets.size()) {
                throw std::runtime_error(
                    "B003 packet leaf references invalid packet");
            }

            const auto& packet =
                packetized.packets[packet_index];
            for (std::uint32_t lane = 0; lane < count; ++lane) {
                const auto primitive =
                    quantized.ordered_primitives.at(begin + lane);
                const auto& triangle =
                    triangles.at(primitive);

                const float expected_v0[3]{
                    triangle.v0.x,
                    triangle.v0.y,
                    triangle.v0.z,
                };
                const auto edge1 =
                    triangle.v1 - triangle.v0;
                const auto edge2 =
                    triangle.v2 - triangle.v0;
                const float expected_e1[3]{
                    edge1.x,
                    edge1.y,
                    edge1.z,
                };
                const float expected_e2[3]{
                    edge2.x,
                    edge2.y,
                    edge2.z,
                };

                for (int axis = 0; axis < 3; ++axis) {
                    if (packet.v0[lane][axis] != expected_v0[axis] ||
                        packet.e1[lane][axis] != expected_e1[axis] ||
                        packet.e2[lane][axis] != expected_e2[axis]) {
                        throw std::runtime_error(
                            "B003 packet geometry changed source triangle");
                    }
                }
                if (packet.metadata[lane][0] != triangle.primitive_id ||
                    packet.metadata[lane][1] != triangle.material_id ||
                    packet.metadata[lane][2] != triangle.instance_id ||
                    packet.metadata[lane][3] !=
                        (triangle.two_sided ? 1U : 0U)) {
                    throw std::runtime_error(
                        "B003 packet metadata changed source triangle");
                }
                ++observed_live;
            }
        }
    }

    if (observed_live != packetized.live_triangle_slots ||
        packetized.packet_triangle_slots !=
            packetized.packets.size() * 4U ||
        packetized.live_triangle_slots >
            packetized.packet_triangle_slots) {
        throw std::runtime_error(
            "B003 packet slot accounting is inconsistent");
    }
}

[[nodiscard]] HierarchicalFlatPayload
make_control(std::uint32_t segments) {
    HierarchicalFlatPayload flat;
    flat.nodes.reserve(segments);
    flat.segments.reserve(segments);

    for (std::uint32_t index = 0;
         index < segments;
         ++index) {
        const float x =
            static_cast<float>(index % 17U);
        const float y =
            static_cast<float>(
                (index / 17U) % 7U);
        const float z =
            static_cast<float>(index / 119U);
        const Aabb bounds{
            {x, y, z},
            {x + 0.75F, y + 0.5F, z + 1.0F},
        };
        flat.nodes.push_back({
            bounds,
            kInvalidId,
            kInvalidId,
            index,
            1U,
        });
        flat.ordered_primitives.push_back(index);
        flat.segments.push_back({
            {
                static_cast<std::int32_t>(index),
                0,
                0,
            },
            index,
        });
        flat.occupied_bounds =
            merge(
                flat.occupied_bounds,
                bounds);
    }
    return flat;
}

} // namespace
} // namespace phos::gi::research::lane_b

int main() {
    using namespace phos::gi::research::lane_b;

    try {
        HierarchicalFlatPayload empty;
        verify_payload(
            empty,
            make_b003_macro_bvh8(empty, 2.0F));

        for (const auto count :
             {1U, 8U, 9U, 64U, 257U, 682U}) {
            const auto flat =
                make_control(count);
            const auto payload =
                make_b003_macro_bvh8(flat, 2.0F);
            verify_payload(flat, payload);
            const auto wide =
                make_b003_wide_micro_payload(flat);
            verify_wide_payload(flat, wide);
            verify_wide_leaf_equivalence(
                flat,
                wide);
            const auto quantized =
                make_b003_quantized_micro_payload(
                    wide);
            verify_quantized_payload(
                wide,
                quantized);
            B002Scene packet_scene;
            packet_scene.triangles =
                flat.ordered_primitives.empty()
                ? std::vector<Triangle>{}
                : std::vector<Triangle>(
                    count,
                    Triangle{});
            if (!flat.ordered_primitives.empty()) {
                for (std::uint32_t primitive = 0;
                     primitive < count;
                     ++primitive) {
                    packet_scene.triangles[primitive] = {
                        {float(primitive), 0.0F, 0.0F},
                        {float(primitive), 1.0F, 0.0F},
                        {float(primitive), 0.0F, 1.0F},
                        primitive,
                        primitive + 10U,
                        primitive + 20U,
                        (primitive & 1U) != 0U,
                    };
                }
                const auto packetized =
                    make_b003_packet_micro_payload(
                        quantized,
                        packet_scene);
                verify_packet_payload(
                    quantized,
                    packetized,
                    packet_scene.triangles);
            }
        }

        // Exercise recursive collapse on real multi-level per-segment BVHs,
        // not only the one-leaf synthetic payloads above.
        const auto dense =
            make_scene("dense");
        const HierarchicalStrataBrick hierarchy(
            dense.triangles,
            12.0F);
        const auto dense_flat =
            hierarchy.flatten();
        const auto dense_wide =
            make_b003_wide_micro_payload(
                dense_flat);
        verify_wide_payload(
            dense_flat,
            dense_wide);
        verify_wide_leaf_equivalence(
            dense_flat,
            dense_wide);
        const auto dense_quantized =
            make_b003_quantized_micro_payload(
                dense_wide);
        verify_quantized_payload(
            dense_wide,
            dense_quantized);
        B002Scene dense_scene;
        dense_scene.triangles =
            dense.triangles;
        const auto dense_packetized =
            make_b003_packet_micro_payload(
                dense_quantized,
                dense_scene);
        verify_packet_payload(
            dense_quantized,
            dense_packetized,
            dense_scene.triangles);

        std::cout
            << "B003 macro/wide/quantized/packet BVH8 structural smoke: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "B003 macro/wide/quantized/packet BVH8 structural smoke: FAIL: "
            << error.what()
            << '\n';
        return 1;
    }
}

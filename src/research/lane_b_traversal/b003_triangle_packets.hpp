#pragma once

#include "b002_scene.hpp"
#include "b003_quantized_bvh8.hpp"

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <unordered_map>
#include <vector>

namespace phos::gi::research::lane_b {

struct alignas(16) B003GpuTrianglePacket4 {
    float v0[4][4]{};
    float e1[4][4]{};
    float e2[4][4]{};
    std::uint32_t metadata[4][4]{};
};
static_assert(sizeof(B003GpuTrianglePacket4) == 256);

struct B003PacketMicroPayload {
    std::vector<B003GpuQuantNode> nodes;
    std::vector<B003GpuTrianglePacket4> packets;
    std::vector<GpuSegmentHashEntry> hash_table;
    Aabb occupied_bounds{};
    std::uint32_t hash_mask{};
    std::uint32_t hash_max_probe{};
    std::size_t max_depth{};
    std::size_t max_stack_entries{};
    std::size_t segment_count{};
    std::size_t source_leaf_count{};
    std::size_t packet_triangle_slots{};
    std::size_t live_triangle_slots{};
};

namespace b003_packet_detail {

[[nodiscard]] inline B003GpuTrianglePacket4
make_packet(
    std::uint32_t begin,
    std::uint32_t count,
    const std::vector<std::uint32_t>& ordered,
    const std::vector<Triangle>& triangles) {
    if (count == 0U || count > 4U ||
        static_cast<std::size_t>(begin) + count >
            ordered.size()) {
        throw std::runtime_error(
            "B003 packet leaf range is invalid");
    }

    B003GpuTrianglePacket4 packet;
    for (std::size_t lane = 0; lane < 4U; ++lane) {
        packet.metadata[lane][0] = kInvalidId;
        packet.metadata[lane][1] = kInvalidId;
        packet.metadata[lane][2] = kInvalidId;
    }

    for (std::uint32_t lane = 0; lane < count; ++lane) {
        const auto primitive =
            ordered[begin + lane];
        if (primitive >= triangles.size()) {
            throw std::runtime_error(
                "B003 packet primitive index is invalid");
        }

        const auto& triangle =
            triangles[primitive];
        const auto edge1 =
            triangle.v1 - triangle.v0;
        const auto edge2 =
            triangle.v2 - triangle.v0;

        packet.v0[lane][0] = triangle.v0.x;
        packet.v0[lane][1] = triangle.v0.y;
        packet.v0[lane][2] = triangle.v0.z;
        packet.e1[lane][0] = edge1.x;
        packet.e1[lane][1] = edge1.y;
        packet.e1[lane][2] = edge1.z;
        packet.e2[lane][0] = edge2.x;
        packet.e2[lane][1] = edge2.y;
        packet.e2[lane][2] = edge2.z;
        packet.metadata[lane][0] =
            triangle.primitive_id;
        packet.metadata[lane][1] =
            triangle.material_id;
        packet.metadata[lane][2] =
            triangle.instance_id;
        packet.metadata[lane][3] =
            triangle.two_sided ? 1U : 0U;
    }
    return packet;
}

} // namespace b003_packet_detail

[[nodiscard]] inline B003PacketMicroPayload
make_b003_packet_micro_payload(
    const B003QuantizedMicroPayload& quantized,
    const B002Scene& scene) {
    B003PacketMicroPayload output;
    output.nodes = quantized.nodes;
    output.hash_table = quantized.hash_table;
    output.occupied_bounds = quantized.occupied_bounds;
    output.hash_mask = quantized.hash_mask;
    output.hash_max_probe = quantized.hash_max_probe;
    output.max_depth = quantized.max_depth;
    output.max_stack_entries =
        quantized.max_stack_entries;
    output.segment_count = quantized.segment_count;

    std::unordered_map<
        std::uint32_t,
        std::uint32_t> remap;

    for (auto& node : output.nodes) {
        for (auto& child : node.children) {
            const auto token = child.packed[3];
            if (token == kInvalidId ||
                !b003_wide_is_leaf(token)) {
                continue;
            }

            const auto existing =
                remap.find(token);
            if (existing != remap.end()) {
                child.packed[3] =
                    b003_wide_leaf_token(
                        existing->second,
                        b003_wide_leaf_count(token));
                continue;
            }

            const auto begin =
                b003_wide_leaf_begin(token);
            const auto count =
                b003_wide_leaf_count(token);
            if (output.packets.size() >
                kB003WideBeginMask) {
                throw std::runtime_error(
                    "B003 packet count exceeds leaf token capacity");
            }

            const auto packet_index =
                static_cast<std::uint32_t>(
                    output.packets.size());
            output.packets.push_back(
                b003_packet_detail::make_packet(
                    begin,
                    count,
                    quantized.ordered_primitives,
                    scene.triangles));
            remap.emplace(token, packet_index);
            child.packed[3] =
                b003_wide_leaf_token(
                    packet_index,
                    count);
            ++output.source_leaf_count;
            output.live_triangle_slots += count;
        }
    }

    output.packet_triangle_slots =
        output.packets.size() * 4U;

    if (output.packets.empty()) {
        throw std::runtime_error(
            "B003 packet payload contains no triangle packets");
    }
    return output;
}

} // namespace phos::gi::research::lane_b

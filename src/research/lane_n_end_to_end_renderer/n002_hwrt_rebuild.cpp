#include "imported/lane_b_traversal/b002_hwrt.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::lane_b {
namespace {

using Clock = std::chrono::steady_clock;

struct Vertex3 {
    float x{};
    float y{};
    float z{};
};
static_assert(sizeof(Vertex3) == 12);

[[nodiscard]] double elapsed_us(Clock::time_point start) {
    return std::chrono::duration<double, std::micro>(
        Clock::now() - start).count();
}

[[noreturn]] void fail_rebuild(const char* message) {
    throw std::runtime_error(message);
}

} // namespace

HwrtPartitionRebuildStats B002HwrtTraversal::rebuild_partition_geometry(
    const std::vector<Triangle>& triangles,
    std::span<const std::uint32_t> moved_primitives) {
    if (!rigid_partitioned_ || !dynamic_partition_updates_) {
        fail_rebuild(
            "N002 topology rebuild requires an update-enabled object partition");
    }
    if (triangles.size() != triangle_count_) {
        fail_rebuild(
            "N002 topology rebuild keeps the frozen renderer slot count stable");
    }
    if (moved_primitives.size() != dynamic_primitives_.size() ||
        !std::equal(
            moved_primitives.begin(),
            moved_primitives.end(),
            dynamic_primitives_.begin())) {
        fail_rebuild(
            "N002 topology rebuild must match the frozen dynamic owner partition");
    }

    std::vector<Vertex3> vertices;
    vertices.reserve(moved_primitives.size() * 3U);
    std::vector<GpuTriangle> metadata;
    metadata.reserve(moved_primitives.size());
    for (const auto primitive : moved_primitives) {
        const auto& triangle = triangles.at(primitive);
        vertices.push_back({triangle.v0.x, triangle.v0.y, triangle.v0.z});
        vertices.push_back({triangle.v1.x, triangle.v1.y, triangle.v1.z});
        vertices.push_back({triangle.v2.x, triangle.v2.y, triangle.v2.z});
        metadata.push_back(to_gpu_triangle(triangle));
    }

    const B002BufferUpdate vertex_update{
        VkDeviceSize(static_triangle_count_) *
            VkDeviceSize(3U * sizeof(Vertex3)),
        vertices.data(),
        VkDeviceSize(vertices.size() * sizeof(Vertex3)),
    };
    const B002BufferUpdate metadata_update{
        VkDeviceSize(static_triangle_count_) *
            VkDeviceSize(sizeof(GpuTriangle)),
        metadata.data(),
        VkDeviceSize(metadata.size() * sizeof(GpuTriangle)),
    };

    const auto upload_start = Clock::now();
    const auto vertex_upload_gpu_us =
        context_.update_device_buffer_timed(
            vertex_buffer_,
            std::span<const B002BufferUpdate>(&vertex_update, 1));
    const auto metadata_upload_gpu_us =
        context_.update_device_buffer_timed(
            triangle_buffer_,
            std::span<const B002BufferUpdate>(&metadata_update, 1));
    const auto upload_wall_us = elapsed_us(upload_start);

    // Build the replacement while the previous object-local BLAS remains
    // alive. Static geometry and its BLAS are untouched. This mirrors the
    // Lane-M incumbent lifetime: build replacement -> TLAS switch -> retire old.
    AccelerationStructure replacement{};
    const auto dynamic_vertex_address =
        vertex_buffer_.address +
        VkDeviceAddress(static_triangle_count_) *
            VkDeviceAddress(3U * sizeof(Vertex3));
    const auto blas_build_us = build_blas_range(
        dynamic_vertex_address,
        dynamic_triangle_count_,
        replacement,
        true);

    const auto old_dynamic_bytes =
        static_cast<std::size_t>(dynamic_blas_.storage.allocation_size);
    const auto replacement_bytes =
        static_cast<std::size_t>(replacement.storage.allocation_size);
    const auto old_new_overlap_bytes =
        old_dynamic_bytes + replacement_bytes;

    AccelerationStructure old = dynamic_blas_;
    dynamic_blas_ = replacement;
    replacement = {};

    const auto tlas = update_rigid_transform(
        0.0F,
        HwrtTlasPolicy::Build);

    destroy_acceleration_structure(old);

    setup_stats_.persistent_bytes =
        static_cast<std::size_t>(
            vertex_buffer_.allocation_size +
            triangle_buffer_.allocation_size +
            instance_buffer_.allocation_size +
            blas_.storage.allocation_size +
            dynamic_blas_.storage.allocation_size +
            tlas_.storage.allocation_size);
    setup_stats_.scratch_bytes =
        static_cast<std::size_t>(scratch_.allocation_size);

    return {
        moved_primitives.size(),
        upload_wall_us,
        vertex_upload_gpu_us + metadata_upload_gpu_us,
        blas_build_us,
        tlas.instance_upload_us,
        tlas.instance_upload_gpu_us,
        tlas.tlas_update_us,
        old_new_overlap_bytes,
        replacement_bytes,
    };
}

} // namespace phos::gi::research::lane_b

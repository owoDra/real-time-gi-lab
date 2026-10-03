// N002 topology extension deliberately reuses the accepted N001 runtime
// implementation in the same translation unit. phos-n002-topology compiles
// this file instead of n001_runtime.cpp, so N001 remains unchanged while the
// complete Impl definition is available for the N002-only member below.
#include "n001_runtime.cpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::integration {
namespace {

using Clock = std::chrono::steady_clock;

[[nodiscard]] double n002_elapsed_us(Clock::time_point start) {
    return std::chrono::duration<double, std::micro>(
        Clock::now() - start).count();
}

[[nodiscard]] lane_b::Vec3 n002_normal(const lane_b::Triangle& triangle) {
    const auto a = triangle.v1 - triangle.v0;
    const auto b = triangle.v2 - triangle.v0;
    const lane_b::Vec3 value{
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    };
    const auto length = std::sqrt(
        value.x * value.x + value.y * value.y + value.z * value.z);
    if (length <= 1.0e-10F) {
        throw std::runtime_error(
            "N002 topology mutation produced a degenerate triangle");
    }
    return {value.x / length, value.y / length, value.z / length};
}

void n002_recompute_bounds(
    lane_a::SceneSurfaceSet& a_scene,
    lane_b::B002Scene& b_scene) {
    for (int axis = 0; axis < 3; ++axis) {
        a_scene.min_position[axis] =
            std::numeric_limits<float>::infinity();
        a_scene.max_position[axis] =
            -std::numeric_limits<float>::infinity();
    }
    b_scene.bounds = {};
    for (std::size_t index = 0; index < a_scene.samples.size(); ++index) {
        const auto& sample = a_scene.samples[index];
        for (int axis = 0; axis < 3; ++axis) {
            a_scene.min_position[axis] = std::min(
                a_scene.min_position[axis],
                sample.position[axis]);
            a_scene.max_position[axis] = std::max(
                a_scene.max_position[axis],
                sample.position[axis]);
        }
        b_scene.bounds = lane_b::merge(
            b_scene.bounds,
            lane_b::triangle_bounds(b_scene.triangles[index]));
    }
    b_scene.diagonal = lane_b::length(
        b_scene.bounds.max - b_scene.bounds.min);
    if (!std::isfinite(b_scene.diagonal) || b_scene.diagonal <= 0.0F) {
        throw std::runtime_error(
            "N002 topology mutation produced invalid scene bounds");
    }
}

} // namespace

I001FrameResult I001Runtime::run_topology_churn_frame() {
    if (!impl_) {
        throw std::runtime_error("N002 topology runtime is not initialized");
    }
    if (impl_->options.variant != I001Variant::LaneEFinalHwrt ||
        impl_->options.scenario != I001Scenario::DeformingControl) {
        throw std::runtime_error(
            "N002 topology frame requires LaneEFinalHwrt with the object-local partition");
    }
    if (impl_->geometry_is_target) {
        throw std::runtime_error(
            "N002 topology frame requires a fresh runtime in the source state");
    }
    if (!impl_->hwrt || impl_->moving.primitives.empty()) {
        throw std::runtime_error(
            "N002 topology frame has no dynamic owner partition");
    }

    const auto total_start = Clock::now();
    const auto prepare_start = Clock::now();

    std::uint32_t max_primitive_id = 0U;
    for (const auto& triangle : impl_->b_scene.triangles) {
        if (triangle.primitive_id != lane_b::kInvalidId) {
            max_primitive_id = std::max(
                max_primitive_id,
                triangle.primitive_id);
        }
    }
    const auto primitive_budget = impl_->moving.primitives.size() + 1U;
    if (primitive_budget > std::numeric_limits<std::uint32_t>::max() ||
        max_primitive_id >
            std::numeric_limits<std::uint32_t>::max() -
                static_cast<std::uint32_t>(primitive_budget)) {
        throw std::runtime_error(
            "N002 topology replacement primitive-id range overflow");
    }

    const float amplitude = std::max(
        impl_->moving.delta_x,
        lane_b::b002_segment_size(impl_->b_scene) * 0.04F);
    std::size_t replaced = 0U;
    std::vector<std::array<float, 4>> surface_positions;
    surface_positions.reserve(impl_->moving.primitives.size());

    // Frozen high-churn mutation: replace exactly half of the selected object
    // primitives with new primitive identities and changed geometry while the
    // object slot count remains constant. Semantically this is delete+insert,
    // so topology changes even though renderer buffer capacity is stable.
    for (std::size_t local = 0; local < impl_->moving.primitives.size(); ++local) {
        const auto primitive = impl_->moving.primitives[local];
        auto& triangle = impl_->b_scene.triangles.at(primitive);
        if ((local & 1U) == 0U) {
            const float sign = ((local >> 1U) & 1U) == 0U ? 1.0F : -1.0F;
            const float scale = 1.0F + float(local % 5U) * 0.125F;
            triangle.v0.y += sign * amplitude * 0.50F * scale;
            triangle.v1.z += sign * amplitude * 0.35F * scale;
            triangle.v2.x -= sign * amplitude * 0.20F * scale;
            triangle.primitive_id =
                max_primitive_id + 1U +
                static_cast<std::uint32_t>(local);
            ++replaced;
        }

        auto& sample = impl_->a_scene.samples.at(primitive);
        sample.position[0] =
            (triangle.v0.x + triangle.v1.x + triangle.v2.x) / 3.0F;
        sample.position[1] =
            (triangle.v0.y + triangle.v1.y + triangle.v2.y) / 3.0F;
        sample.position[2] =
            (triangle.v0.z + triangle.v1.z + triangle.v2.z) / 3.0F;
        const auto normal = n002_normal(triangle);
        sample.normal[0] = normal.x;
        sample.normal[1] = normal.y;
        sample.normal[2] = normal.z;
        surface_positions.push_back({
            sample.position[0],
            sample.position[1],
            sample.position[2],
            sample.position[3],
        });
    }
    const auto expected_replaced =
        (impl_->moving.primitives.size() + 1U) / 2U;
    if (replaced != expected_replaced) {
        throw std::runtime_error(
            "N002 topology mutation did not match the frozen 50% churn schedule");
    }
    n002_recompute_bounds(impl_->a_scene, impl_->b_scene);
    const auto geometry_prepare_cpu_us =
        n002_elapsed_us(prepare_start);

    std::vector<lane_b::B002BufferUpdate> surface_updates;
    surface_updates.reserve(impl_->moving.primitives.size());
    for (std::size_t local = 0; local < impl_->moving.primitives.size(); ++local) {
        surface_updates.push_back({
            VkDeviceSize(impl_->moving.primitives[local]) *
                VkDeviceSize(sizeof(std::array<float, 4>)),
            surface_positions[local].data(),
            VkDeviceSize(sizeof(std::array<float, 4>)),
        });
    }
    const auto surface_update_gpu_us =
        impl_->context.update_device_buffer_timed(
            impl_->surfaces,
            surface_updates);

    const auto rebuild = impl_->hwrt->rebuild_partition_geometry(
        impl_->b_scene.triangles,
        impl_->moving.primitives);

    impl_->geometry_is_target = true;
    impl_->calculate_memory();

    // Execute the unchanged renderer/GI command stream. update_dynamic_geometry
    // intentionally becomes a no-op because the topology target state has
    // already been installed through the Lane-M incumbent rebuild boundary.
    auto result = impl_->run_frame(true);

    const double maintenance_gpu_us =
        surface_update_gpu_us +
        rebuild.geometry_upload_gpu_us +
        rebuild.instance_upload_gpu_us +
        rebuild.blas_build_us +
        rebuild.tlas_build_us;

    result.timings.traversal_maintenance_gpu_us = maintenance_gpu_us;
    result.timings.dynamic_update_wall_us =
        n002_elapsed_us(total_start);
    result.timings.geometry_prepare_cpu_us = geometry_prepare_cpu_us;
    result.timings.surface_update_gpu_us = surface_update_gpu_us;
    result.timings.geometry_transfer_wall_us = rebuild.geometry_upload_us;
    result.timings.geometry_transfer_gpu_us =
        rebuild.geometry_upload_gpu_us;
    result.timings.instance_transfer_wall_us =
        rebuild.instance_upload_us;
    result.timings.instance_transfer_gpu_us =
        rebuild.instance_upload_gpu_us;
    result.timings.blas_update_us = rebuild.blas_build_us;
    result.timings.tlas_update_us = rebuild.tlas_build_us;
    result.timings.complete_gpu_us += maintenance_gpu_us;
    result.timings.complete_renderer_gpu_us += maintenance_gpu_us;
    result.timings.incremental_gi_us += maintenance_gpu_us;

    result.stats.moved_primitives =
        static_cast<std::uint32_t>(impl_->moving.primitives.size());
    result.stats.topology_mutations = 1U;
    result.stats.topology_replaced_primitives =
        static_cast<std::uint32_t>(replaced);
    result.stats.backend_rebuilds = 1U;

    result.memory.old_new_overlap_bytes =
        rebuild.old_new_overlap_bytes;
    const auto retired_old_bytes =
        rebuild.old_new_overlap_bytes >= rebuild.replacement_blas_bytes
            ? rebuild.old_new_overlap_bytes - rebuild.replacement_blas_bytes
            : 0U;
    const auto steady_peak = result.memory.peak_resident_bytes;
    if (retired_old_bytes >
        std::numeric_limits<std::size_t>::max() - steady_peak) {
        throw std::runtime_error("N002 topology lifetime peak overflow");
    }
    result.memory.peak_resident_bytes =
        steady_peak + retired_old_bytes;

    impl_->memory_stats = result.memory;
    impl_->last = result;
    impl_->have_last = true;
    return result;
}

} // namespace phos::gi::research::integration

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

[[nodiscard]] std::size_t n002_checked_add(
    std::size_t a,
    std::size_t b) {
    if (b > std::numeric_limits<std::size_t>::max() - a) {
        throw std::runtime_error("N002 topology lifetime byte count overflow");
    }
    return a + b;
}

[[nodiscard]] std::size_t n002_checked_mul(
    std::size_t a,
    std::size_t b) {
    if (a != 0U && b > std::numeric_limits<std::size_t>::max() / a) {
        throw std::runtime_error("N002 topology staging byte count overflow");
    }
    return a * b;
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

    const auto source_steady_peak = impl_->memory_stats.peak_resident_bytes;
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
    // Scene bounds stay frozen: topology churn must not silently move the
    // camera/light contract through build_a001_params().
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

    // All transfer helpers are synchronously fenced. Before the replacement
    // BLAS exists, at most one staging allocation is live. Once replacement
    // BLAS and old BLAS coexist, only the tiny instance-record staging upload
    // is additionally live. This makes the following lifetime maximum exact
    // for the N002 rebuild sequence without adding global allocator state to
    // the accepted N001/core runtime.
    const auto partition_count = impl_->moving.primitives.size();
    const auto surface_staging = n002_checked_mul(
        partition_count,
        sizeof(std::array<float, 4>));
    const auto vertex_staging = n002_checked_mul(
        partition_count,
        3U * 3U * sizeof(float));
    const auto metadata_staging = n002_checked_mul(
        partition_count,
        sizeof(lane_b::GpuTriangle));
    const auto pre_replacement_staging = std::max(
        {surface_staging, vertex_staging, metadata_staging});
    const auto pre_replacement_peak = n002_checked_add(
        source_steady_peak,
        pre_replacement_staging);

    const auto steady_target_peak = result.memory.peak_resident_bytes;
    const auto overlap_peak = n002_checked_add(
        n002_checked_add(
            steady_target_peak,
            retired_old_bytes),
        sizeof(VkAccelerationStructureInstanceKHR));
    result.memory.peak_resident_bytes = std::max(
        {steady_target_peak, pre_replacement_peak, overlap_peak});

    impl_->memory_stats = result.memory;
    impl_->last = result;
    impl_->have_last = true;
    return result;
}

} // namespace phos::gi::research::integration

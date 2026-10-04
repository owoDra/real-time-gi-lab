#include "n005_runtime.hpp"

// N005 is an integration experiment. Reuse the accepted N004/N002/N001
// implementation in this translation unit so the candidate can insert one
// prospective stage without changing historical renderer translation units.
#include "../lane_n_end_to_end_renderer/n004_runtime.cpp"

#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <limits>
#include <map>
#include <span>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::integration {
namespace {

struct alignas(16) N005ExtraPush {
    std::uint32_t mode{};
    std::uint32_t owner_budget{};
    std::uint32_t extra_rays_per_probe{};
    float depth_threshold{};
};
static_assert(sizeof(N005ExtraPush) == 16U);

[[nodiscard]] bool n005_same_base_identity(
    const LaneAWorkItemV1& base,
    const LaneAWorkItemV1& extra) noexcept {
    return base.probe_x == extra.probe_x &&
        base.probe_y == extra.probe_y &&
        base.probe_z == extra.probe_z &&
        base.cascade == extra.cascade &&
        base.output_id == extra.output_id &&
        base.surface_id == extra.surface_id &&
        base.tile_id == extra.tile_id &&
        std::abs(base.interval_min - extra.interval_min) < 1.0e-6F &&
        std::abs(base.interval_max - extra.interval_max) < 1.0e-6F &&
        within_float_ulps(base.probe_px, extra.probe_px, 2) &&
        within_float_ulps(base.probe_py, extra.probe_py, 2) &&
        within_float_ulps(base.probe_pz, extra.probe_pz, 2);
}

[[nodiscard]] bool n005_unit_direction(
    const LaneAWorkItemV1& item) noexcept {
    const double length2 =
        double(item.dir_x) * item.dir_x +
        double(item.dir_y) * item.dir_y +
        double(item.dir_z) * item.dir_z;
    return std::isfinite(length2) &&
        std::abs(length2 - 1.0) <= 2.0e-5;
}

} // namespace

struct N005Runtime::State {
    B002Buffer extra_stats{};
    std::unique_ptr<I001ComputeStage> extra_stage;
};

N005Runtime::N005Runtime(I001Options options)
    : runtime_(std::move(options)),
      state_(std::make_unique<State>()) {
    auto& impl = *runtime_.impl_;
    state_->extra_stats = impl.context.create_device_buffer(
        4U * sizeof(std::uint32_t),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

    const std::array<I001Binding, 6> bindings{{
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.depth},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.owners},
        {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.counters},
        {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.work},
        {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->extra_stats},
        {5, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &impl.uniform},
    }};
    state_->extra_stage = std::make_unique<I001ComputeStage>(
        impl.context,
        shader_path(PHOS_GI_N005_SHADER_DIR, "n005_extra_producer.spv"),
        bindings,
        sizeof(N005ExtraPush));
}

N005Runtime::~N005Runtime() {
    if (!runtime_.impl_ || !state_) return;
    state_->extra_stage.reset();
    runtime_.impl_->context.destroy_buffer(state_->extra_stats);
}

void N005Runtime::set_motion_fraction(float fraction) {
    runtime_.set_n004_motion_fraction(fraction);
}

N005FrameResult N005Runtime::run_frame(
    bool target_state,
    N005ExtraRequest request) {
    return run_candidate_frame(target_state, request);
}

N005FrameResult N005Runtime::run_candidate_frame(
    bool target_state,
    N005ExtraRequest request) {
    auto& impl = *runtime_.impl_;
    if (request.depth_threshold < 0.0F ||
        !std::isfinite(request.depth_threshold)) {
        throw std::runtime_error("N005 depth threshold must be finite/non-negative");
    }
    if (request.extra_rays_per_probe == 0U && request.owner_budget != 0U) {
        throw std::runtime_error("N005 active budget requires extra rays per probe");
    }

    ++impl.frame_id;
    const auto dynamic_update = impl.update_dynamic_geometry(target_state);
    impl.update_params(target_state);

    impl.context.vk().resetFences(1, &impl.fence);
    impl.context.vk().resetCommandPool(impl.command_pool, 0);

    VkCommandBuffer command{};
    auto allocation = detail::make_vk_info<VkCommandBufferAllocateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    allocation.commandPool = impl.command_pool;
    allocation.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocation.commandBufferCount = 1;
    if (impl.context.vk().allocateCommandBuffers(&allocation, &command) != VK_SUCCESS) {
        fail("N005 command allocation");
    }

    auto begin = detail::make_vk_info<VkCommandBufferBeginInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (impl.context.vk().beginCommandBuffer(command, &begin) != VK_SUCCESS) {
        fail("N005 command begin");
    }

    impl.context.vk().cmdResetQueryPool(command, impl.query_pool, 0, kQueryCount);
    auto stamp = [&](std::uint32_t index) {
        impl.context.vk().cmdWriteTimestamp(
            command,
            VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
            impl.query_pool,
            index);
    };

    stamp(12);
    impl.primary_stage->record(
        command,
        (impl.params.counts[1] + 7U) / 8U,
        (impl.params.counts[2] + 7U) / 8U);
    i001_compute_barrier(impl.context, command);
    stamp(13);

    stamp(0);
    impl.context.vk().cmdFillBuffer(
        command, impl.depth.buffer, 0, impl.depth.size, 0x7f800000U);
    i001_transfer_to_compute_barrier(impl.context, command);
    impl.depth_stage->record(command, groups(impl.params.counts[0]));
    i001_compute_barrier(impl.context, command);
    stamp(1);

    impl.context.vk().cmdFillBuffer(
        command, impl.owners.buffer, 0, impl.owners.size, 0xffffffffU);
    impl.context.vk().cmdFillBuffer(
        command, impl.counters.buffer, 0, impl.counters.size, 0U);
    impl.context.vk().cmdFillBuffer(
        command, impl.accum.buffer, 0, impl.accum.size, 0U);
    impl.context.vk().cmdFillBuffer(
        command, impl.resolved.buffer, 0, impl.resolved.size, 0U);
    impl.context.vk().cmdFillBuffer(
        command, impl.storage_stats.buffer, 0, impl.storage_stats.size, 0U);
    impl.context.vk().cmdFillBuffer(
        command, state_->extra_stats.buffer, 0, state_->extra_stats.size, 0U);
    i001_transfer_to_compute_barrier(impl.context, command);
    stamp(2);

    impl.owner_stage->record(command, groups(impl.params.counts[0]));
    i001_compute_barrier(impl.context, command);
    stamp(3);

    // Frozen base producer path.
    impl.producer_stage->record(command, groups(impl.params.counts[0]));
    i001_compute_barrier(impl.context, command);
    impl.clamp_stage->record(command, 1);
    i001_compute_barrier(impl.context, command);
    impl.finalize_stage->record(command, 1);
    i001_compute_barrier(impl.context, command);
    stamp(4);

    double extra_producer_gpu_us = 0.0;
    const bool active_extra =
        request.mode != N005ExtraMode::Current &&
        request.owner_budget != 0U;
    if (active_extra) {
        stamp(16);
        const N005ExtraPush push{
            static_cast<std::uint32_t>(request.mode),
            request.owner_budget,
            request.extra_rays_per_probe,
            request.depth_threshold,
        };
        state_->extra_stage->record(command, 1, 1, 1, &push, sizeof(push));
        i001_compute_barrier(impl.context, command);

        // counters.data[0] changed; rebuild indirect dispatch from the
        // base+extra total without touching outputs or the base prefix.
        impl.finalize_stage->record(command, 1);
        i001_compute_barrier(impl.context, command);
        stamp(17);
    }

    impl.ray_stage->record_indirect(command, impl.indirect.buffer, 0);
    i001_compute_barrier(impl.context, command);
    stamp(5);

    if (uses_hwrt(impl.options.variant)) {
        i001_acceleration_to_compute_barrier(impl.context, command);
    }
    impl.record_candidate_traversal(command);
    i001_compute_barrier(impl.context, command);
    stamp(6);

    impl.radiance_stage->record_indirect(command, impl.indirect.buffer, 0);
    i001_compute_barrier(impl.context, command);
    stamp(7);

    impl.merge_stage->record_indirect(command, impl.indirect.buffer, 0);
    i001_compute_barrier(impl.context, command);
    stamp(8);

    const StoragePush storage_reserve_push{
        impl.storage_capacity - 1U, kHashMaxProbe, impl.frame_id, 0U};
    impl.storage_update_stage->record_indirect(
        command,
        impl.indirect.buffer,
        0,
        &storage_reserve_push,
        sizeof(storage_reserve_push));
    i001_compute_barrier(impl.context, command);

    const StoragePush storage_accumulate_push{
        impl.storage_capacity - 1U, kHashMaxProbe, impl.frame_id, 1U};
    impl.storage_update_stage->record_indirect(
        command,
        impl.indirect.buffer,
        0,
        &storage_accumulate_push,
        sizeof(storage_accumulate_push));
    i001_compute_barrier(impl.context, command);
    stamp(9);

    const InvalidationPush invalidation_push{
        impl.storage_capacity, impl.frame_id, 0U, 0U};
    impl.invalidation_stage->record(
        command,
        groups(impl.storage_capacity),
        1,
        1,
        &invalidation_push,
        sizeof(invalidation_push));
    i001_compute_barrier(impl.context, command);
    stamp(10);

    const StoragePush storage_resolve_push{
        impl.storage_capacity - 1U, kHashMaxProbe, impl.frame_id, 0U};
    impl.resolve_stage->record_indirect(
        command,
        impl.indirect.buffer,
        0,
        &storage_resolve_push,
        sizeof(storage_resolve_push));
    i001_compute_barrier(impl.context, command);
    stamp(11);

    const StoragePush composite_push{
        impl.storage_capacity - 1U, kHashMaxProbe, impl.frame_id, 0U};
    stamp(14);
    impl.composite_stage->record(
        command,
        (impl.params.counts[1] + 7U) / 8U,
        (impl.params.counts[2] + 7U) / 8U,
        1U,
        &composite_push,
        sizeof(composite_push));
    i001_compute_barrier(impl.context, command);
    stamp(15);

    if (impl.context.vk().endCommandBuffer(command) != VK_SUCCESS) {
        fail("N005 command end");
    }
    auto submit = detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &command;
    if (impl.context.vk().queueSubmit(
            impl.context.queue(), 1, &submit, impl.fence) != VK_SUCCESS) {
        fail("N005 submit");
    }
    if (impl.context.vk().waitForFences(
            1, &impl.fence, VK_TRUE, UINT64_MAX) != VK_SUCCESS) {
        fail("N005 fence wait");
    }

    std::array<std::uint64_t, 18> timestamps{};
    if (impl.context.vk().getQueryPoolResults(
            impl.query_pool,
            0,
            static_cast<std::uint32_t>(timestamps.size()),
            sizeof(timestamps),
            timestamps.data(),
            sizeof(std::uint64_t),
            VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
        fail("N005 timestamp readback");
    }

    std::array<std::uint32_t, 6> counter_values{};
    impl.context.download_device_buffer(
        impl.counters, counter_values.data(), sizeof(counter_values));
    std::array<std::uint32_t, 4> storage_values{};
    impl.context.download_device_buffer(
        impl.storage_stats, storage_values.data(), sizeof(storage_values));
    std::array<std::uint32_t, 4> extra_values{};
    impl.context.download_device_buffer(
        state_->extra_stats, extra_values.data(), sizeof(extra_values));

    const auto period = impl.context.timestamp_period_ns();
    if (active_extra) {
        extra_producer_gpu_us =
            timestamp_us(timestamps[16], timestamps[17], period);
    }

    I001FrameResult result{};
    result.timings.primary_visibility_us =
        timestamp_us(timestamps[12], timestamps[13], period);
    result.timings.renderer_depth_us =
        timestamp_us(timestamps[0], timestamps[1], period);
    result.timings.frame_init_us =
        timestamp_us(timestamps[1], timestamps[2], period);
    result.timings.visibility_reuse_us =
        timestamp_us(timestamps[2], timestamps[3], period);
    result.timings.producer_us =
        timestamp_us(timestamps[3], timestamps[4], period);
    result.timings.ray_prepare_us = active_extra
        ? timestamp_us(timestamps[17], timestamps[5], period)
        : timestamp_us(timestamps[4], timestamps[5], period);
    result.timings.traversal_maintenance_gpu_us = dynamic_update.gpu_us;
    result.timings.dynamic_update_wall_us = dynamic_update.wall_us;
    result.timings.geometry_prepare_cpu_us =
        dynamic_update.geometry_prepare_cpu_us;
    result.timings.surface_update_gpu_us =
        dynamic_update.surface_update_gpu_us;
    result.timings.geometry_transfer_wall_us =
        dynamic_update.geometry_transfer_wall_us;
    result.timings.geometry_transfer_gpu_us =
        dynamic_update.geometry_transfer_gpu_us;
    result.timings.instance_transfer_wall_us =
        dynamic_update.instance_transfer_wall_us;
    result.timings.instance_transfer_gpu_us =
        dynamic_update.instance_transfer_gpu_us;
    result.timings.blas_update_us = dynamic_update.blas_update_us;
    result.timings.tlas_update_us = dynamic_update.tlas_update_us;
    result.timings.membership_update_cpu_us =
        dynamic_update.membership_update_cpu_us;
    result.timings.hierarchy_refit_cpu_us =
        dynamic_update.hierarchy_refit_cpu_us;
    result.timings.hierarchy_rebuild_cpu_us =
        dynamic_update.hierarchy_rebuild_cpu_us;
    result.timings.hierarchy_occupancy_cpu_us =
        dynamic_update.hierarchy_occupancy_cpu_us;
    result.timings.packing_cpu_us = dynamic_update.packing_cpu_us;
    result.timings.hierarchy_upload_gpu_us =
        dynamic_update.hierarchy_upload_gpu_us;
    result.timings.software_bvh_rebuild_cpu_us =
        dynamic_update.software_bvh_rebuild_cpu_us;
    result.timings.traversal_us =
        timestamp_us(timestamps[5], timestamps[6], period);
    result.timings.radiance_us =
        timestamp_us(timestamps[6], timestamps[7], period);
    result.timings.merge_us =
        timestamp_us(timestamps[7], timestamps[8], period);
    result.timings.storage_update_us =
        timestamp_us(timestamps[8], timestamps[9], period);
    result.timings.invalidation_us =
        timestamp_us(timestamps[9], timestamps[10], period);
    result.timings.resolve_us =
        timestamp_us(timestamps[10], timestamps[11], period);
    result.timings.composite_us =
        timestamp_us(timestamps[14], timestamps[15], period);
    result.timings.complete_gpu_us =
        result.timings.primary_visibility_us +
        timestamp_us(timestamps[0], timestamps[11], period) +
        dynamic_update.gpu_us;
    result.timings.complete_renderer_gpu_us =
        result.timings.complete_gpu_us + result.timings.composite_us;
    result.timings.incremental_gi_us =
        result.timings.primary_visibility_us +
        timestamp_us(timestamps[0], timestamps[11], period) +
        dynamic_update.gpu_us;

    result.stats.work_items = counter_values[0];
    result.stats.outputs = counter_values[1];
    result.stats.overflow = counter_values[2];
    result.stats.visible_owners = counter_values[3];
    if ((impl.options.scenario == I001Scenario::MovingRigid ||
         impl.options.scenario == I001Scenario::DeformingControl) &&
        target_state) {
        result.stats.moved_primitives =
            static_cast<std::uint32_t>(impl.moving.primitives.size());
        result.stats.segment_membership_changes =
            impl.moving.membership_changes;
        result.stats.hierarchy_refit_segments =
            dynamic_update.refit_segments;
        result.stats.hierarchy_rebuilt_segments =
            dynamic_update.rebuilt_segments;
    }
    result.stats.requested_work_items = counter_values[4];
    result.stats.requested_outputs = counter_values[5];
    result.stats.storage_allocations = storage_values[0];
    result.stats.storage_updates = storage_values[1];
    result.stats.storage_invalidations = storage_values[2];
    result.stats.storage_failures = storage_values[3];
    result.memory = impl.memory_stats;

    impl.last = result;
    impl.have_last = true;

    N005ExtraStats extra{};
    extra.base_traced_rays =
        active_extra ? extra_values[0] : result.stats.work_items;
    extra.eligible_owner_count = active_extra ? extra_values[1] : 0U;
    extra.selected_owner_count = active_extra ? extra_values[2] : 0U;
    extra.extra_work_items = active_extra ? extra_values[3] : 0U;
    extra.extra_rays_requested =
        request.owner_budget *
        impl.settings.cascade_count *
        request.extra_rays_per_probe;
    extra.extra_rays_traced = extra.extra_work_items;
    extra.eligible_probe_count =
        extra.eligible_owner_count * impl.settings.cascade_count;
    extra.extra_probe_count =
        extra.selected_owner_count * impl.settings.cascade_count;
    extra.extra_probe_fraction = result.stats.visible_owners == 0U
        ? 0.0
        : double(extra.selected_owner_count) /
            double(result.stats.visible_owners);
    extra.extra_producer_gpu_us = extra_producer_gpu_us;

    const auto total_work = result.stats.work_items;
    std::vector<LaneAWorkItemV1> work_items(total_work);
    if (total_work != 0U) {
        impl.context.download_device_buffer(
            impl.work,
            work_items.data(),
            work_items.size() * sizeof(LaneAWorkItemV1));
    }
    const auto tile_count = impl.params.counts[1] * impl.params.counts[2];
    std::vector<std::uint32_t> tile_owners(tile_count);
    impl.context.download_device_buffer(
        impl.owners,
        tile_owners.data(),
        tile_owners.size() * sizeof(std::uint32_t));

    const bool base_count_valid =
        extra.base_traced_rays <= total_work &&
        extra.base_traced_rays % (
            impl.settings.cascade_count * impl.settings.rays_per_probe) == 0U;
    if (base_count_valid) {
        lane_a::A001Readback base_readback{};
        base_readback.counters = {
            extra.base_traced_rays,
            result.stats.outputs,
            result.stats.overflow,
            result.stats.visible_owners,
        };
        base_readback.tile_owner = tile_owners;
        base_readback.work_items.resize(extra.base_traced_rays);
        static_assert(
            sizeof(lane_a::SplitRcWorkItemV1) == sizeof(LaneAWorkItemV1));
        for (std::size_t index = 0; index < extra.base_traced_rays; ++index) {
            base_readback.work_items[index] =
                std::bit_cast<lane_a::SplitRcWorkItemV1>(work_items[index]);
        }
        base_readback.resolved.assign(result.stats.outputs, 0.0F);
        const auto analysis = lane_a::analyze_a001(
            impl.a_scene,
            impl.settings,
            impl.params,
            base_readback);
        extra.base_prefix_correct =
            analysis.visibility_correct && analysis.producer_correct;
    }

    bool extra_ok =
        base_count_valid &&
        total_work == extra.base_traced_rays + extra.extra_work_items &&
        extra.extra_work_items ==
            extra.selected_owner_count *
            impl.settings.cascade_count *
            request.extra_rays_per_probe &&
        result.stats.overflow == 0U;
    if (active_extra) {
        extra_ok = extra_ok &&
            extra.selected_owner_count == request.owner_budget &&
            extra.eligible_owner_count >= request.owner_budget;
    } else {
        extra_ok = extra_ok &&
            extra.selected_owner_count == 0U &&
            extra.extra_work_items == 0U;
    }

    std::vector<std::int64_t> base_by_output(result.stats.outputs, -1);
    if (extra_ok) {
        for (std::uint32_t index = 0U;
             index < extra.base_traced_rays;
             ++index) {
            const auto& item = work_items[index];
            if (item.ray_index == 0U && item.output_id < base_by_output.size()) {
                base_by_output[item.output_id] =
                    static_cast<std::int64_t>(index);
            }
        }

        std::vector<std::uint32_t> extras_per_output(result.stats.outputs, 0U);
        for (std::uint32_t index = extra.base_traced_rays;
             extra_ok && index < total_work;
             ++index) {
            const auto& item = work_items[index];
            if (item.output_id >= base_by_output.size() ||
                base_by_output[item.output_id] < 0 ||
                item.tile_id >= tile_owners.size() ||
                tile_owners[item.tile_id] != item.surface_id ||
                item.ray_index < impl.settings.rays_per_probe ||
                item.ray_index >=
                    impl.settings.rays_per_probe +
                    request.extra_rays_per_probe ||
                !n005_unit_direction(item)) {
                extra_ok = false;
                break;
            }
            const auto& base = work_items[
                static_cast<std::size_t>(base_by_output[item.output_id])];
            if (!n005_same_base_identity(base, item)) {
                extra_ok = false;
                break;
            }
            ++extras_per_output[item.output_id];
        }

        std::uint32_t selected_outputs = 0U;
        for (const auto count : extras_per_output) {
            if (count == 0U) continue;
            if (count != request.extra_rays_per_probe) {
                extra_ok = false;
                break;
            }
            ++selected_outputs;
        }
        extra_ok = extra_ok &&
            selected_outputs == extra.extra_probe_count;
    }
    extra.extra_work_correct = extra_ok;

    return {result, extra};
}

N005FrameResult N005Runtime::run_topology_churn_frame(
    N005ExtraRequest request) {
    auto& impl = *runtime_.impl_;
    if (impl.options.variant != I001Variant::LaneEFinalHwrt ||
        impl.options.scenario != I001Scenario::DeformingControl) {
        throw std::runtime_error(
            "N005 topology frame requires LaneEFinalHwrt/deforming-control");
    }
    if (impl.geometry_is_target || !impl.hwrt || impl.moving.primitives.empty()) {
        throw std::runtime_error("N005 topology frame requires fresh dynamic source state");
    }

    const auto source_steady_peak = impl.memory_stats.peak_resident_bytes;
    const auto total_start = Clock::now();
    const auto prepare_start = Clock::now();

    std::uint32_t max_primitive_id = 0U;
    for (const auto& triangle : impl.b_scene.triangles) {
        if (triangle.primitive_id != lane_b::kInvalidId) {
            max_primitive_id = std::max(max_primitive_id, triangle.primitive_id);
        }
    }
    const auto primitive_budget = impl.moving.primitives.size() + 1U;
    if (primitive_budget > std::numeric_limits<std::uint32_t>::max() ||
        max_primitive_id >
            std::numeric_limits<std::uint32_t>::max() -
            static_cast<std::uint32_t>(primitive_budget)) {
        throw std::runtime_error("N005 topology replacement primitive-id overflow");
    }

    const float amplitude = std::max(
        impl.moving.delta_x,
        lane_b::b002_segment_size(impl.b_scene) * 0.04F);
    std::size_t replaced = 0U;
    std::vector<std::array<float, 4>> surface_positions;
    surface_positions.reserve(impl.moving.primitives.size());

    for (std::size_t local = 0; local < impl.moving.primitives.size(); ++local) {
        const auto primitive = impl.moving.primitives[local];
        auto& triangle = impl.b_scene.triangles.at(primitive);
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

        auto& sample = impl.a_scene.samples.at(primitive);
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
        (impl.moving.primitives.size() + 1U) / 2U;
    if (replaced != expected_replaced) {
        throw std::runtime_error("N005 topology mutation schedule drifted");
    }
    const auto geometry_prepare_cpu_us = n002_elapsed_us(prepare_start);

    std::vector<lane_b::B002BufferUpdate> surface_updates;
    surface_updates.reserve(impl.moving.primitives.size());
    for (std::size_t local = 0; local < impl.moving.primitives.size(); ++local) {
        surface_updates.push_back({
            VkDeviceSize(impl.moving.primitives[local]) *
                VkDeviceSize(sizeof(std::array<float, 4>)),
            surface_positions[local].data(),
            VkDeviceSize(sizeof(std::array<float, 4>)),
        });
    }
    const auto surface_update_gpu_us =
        impl.context.update_device_buffer_timed(impl.surfaces, surface_updates);
    const auto rebuild = impl.hwrt->rebuild_partition_geometry(
        impl.b_scene.triangles,
        impl.moving.primitives);

    impl.geometry_is_target = true;
    impl.calculate_memory();

    auto out = run_candidate_frame(true, request);

    const double maintenance_gpu_us =
        surface_update_gpu_us +
        rebuild.geometry_upload_gpu_us +
        rebuild.instance_upload_gpu_us +
        rebuild.blas_build_us +
        rebuild.tlas_build_us;

    out.frame.timings.traversal_maintenance_gpu_us = maintenance_gpu_us;
    out.frame.timings.dynamic_update_wall_us = n002_elapsed_us(total_start);
    out.frame.timings.geometry_prepare_cpu_us = geometry_prepare_cpu_us;
    out.frame.timings.surface_update_gpu_us = surface_update_gpu_us;
    out.frame.timings.geometry_transfer_wall_us = rebuild.geometry_upload_us;
    out.frame.timings.geometry_transfer_gpu_us =
        rebuild.geometry_upload_gpu_us;
    out.frame.timings.instance_transfer_wall_us = rebuild.instance_upload_us;
    out.frame.timings.instance_transfer_gpu_us =
        rebuild.instance_upload_gpu_us;
    out.frame.timings.blas_update_us = rebuild.blas_build_us;
    out.frame.timings.tlas_update_us = rebuild.tlas_build_us;
    out.frame.timings.complete_gpu_us += maintenance_gpu_us;
    out.frame.timings.complete_renderer_gpu_us += maintenance_gpu_us;
    out.frame.timings.incremental_gi_us += maintenance_gpu_us;

    out.frame.stats.moved_primitives =
        static_cast<std::uint32_t>(impl.moving.primitives.size());
    out.frame.stats.topology_mutations = 1U;
    out.frame.stats.topology_replaced_primitives =
        static_cast<std::uint32_t>(replaced);
    out.frame.stats.backend_rebuilds = 1U;

    out.frame.memory.old_new_overlap_bytes =
        rebuild.old_new_overlap_bytes;
    const auto retired_old_bytes =
        rebuild.old_new_overlap_bytes >= rebuild.replacement_blas_bytes
        ? rebuild.old_new_overlap_bytes - rebuild.replacement_blas_bytes
        : 0U;
    const auto partition_count = impl.moving.primitives.size();
    const auto surface_staging = n002_checked_mul(
        partition_count, sizeof(std::array<float, 4>));
    const auto vertex_staging = n002_checked_mul(
        partition_count, 3U * 3U * sizeof(float));
    const auto metadata_staging = n002_checked_mul(
        partition_count, sizeof(lane_b::GpuTriangle));
    const auto pre_replacement_staging = std::max(
        {surface_staging, vertex_staging, metadata_staging});
    const auto pre_replacement_peak = n002_checked_add(
        source_steady_peak, pre_replacement_staging);
    const auto steady_target_peak = out.frame.memory.peak_resident_bytes;
    const auto overlap_peak = n002_checked_add(
        n002_checked_add(steady_target_peak, retired_old_bytes),
        sizeof(VkAccelerationStructureInstanceKHR));
    out.frame.memory.peak_resident_bytes = std::max(
        {steady_target_peak, pre_replacement_peak, overlap_peak});

    impl.memory_stats = out.frame.memory;
    impl.last = out.frame;
    impl.have_last = true;
    return out;
}

I001N004HitDiagnostics N005Runtime::n004_hit_diagnostics() {
    return runtime_.n004_hit_diagnostics();
}

I001RendererReadback N005Runtime::renderer_readback() {
    return runtime_.renderer_readback();
}

const std::string& N005Runtime::device_name() const noexcept {
    return runtime_.device_name();
}
const std::string& N005Runtime::driver_name() const noexcept {
    return runtime_.driver_name();
}
const std::string& N005Runtime::driver_info() const noexcept {
    return runtime_.driver_info();
}
std::uint32_t N005Runtime::api_version() const noexcept {
    return runtime_.api_version();
}
float N005Runtime::timestamp_period_ns() const noexcept {
    return runtime_.timestamp_period_ns();
}

} // namespace phos::gi::research::integration

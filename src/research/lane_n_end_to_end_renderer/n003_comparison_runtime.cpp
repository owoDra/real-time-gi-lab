// N003 comparison extension deliberately compiles the accepted N002 runtime
// implementation into this translation unit, then adds comparison-only hooks.
// N001/N002 targets continue to compile their existing sources unchanged.
#include "n002_runtime.cpp"

#include <chrono>

namespace phos::gi::research::integration {

void I001Runtime::configure_n003_vanilla_software_baseline() {
    if (!impl_) {
        throw std::runtime_error("N003 vanilla runtime is not initialized");
    }
    if (impl_->options.variant != I001Variant::LaneEFinalHwrt) {
        throw std::runtime_error(
            "N003 vanilla reconfiguration requires a fresh LaneEFinalHwrt runtime");
    }
    if (impl_->geometry_is_target || impl_->have_last) {
        throw std::runtime_error(
            "N003 vanilla reconfiguration must happen before the first frame");
    }

    // The accepted renderer constructor is intentionally still HWRT-only.
    // N003 constructs that exact runtime so scene selection, dynamic-owner
    // selection, storage sizing and all shared renderer resources are identical,
    // then destroys the candidate traversal before any warm-up/measurement.
    impl_->context.vk().deviceWaitIdle();
    impl_->composite_stage.reset();
    impl_->primary_stage.reset();
    impl_->traversal_stage.reset();
    impl_->hwrt.reset();

    impl_->options.variant = I001Variant::VanillaSoftware;
    impl_->prepare_candidate_traversal();
    if (!impl_->software_cpu ||
        impl_->software_cpu->root() == lane_b::kInvalidId) {
        throw std::runtime_error("N003 vanilla software BVH is empty");
    }
    // GpuSoftwareBvhData builds its non-empty root first, therefore root 0 is
    // stable for the comparison-only primary/composite shaders.
    if (impl_->software_cpu->root() != 0U) {
        throw std::runtime_error("N003 vanilla software BVH root contract changed");
    }
    impl_->create_traversal_stage();

    const std::array<I001Binding, 5> primary_bindings{{
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->primary_hits},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->triangle_buffer},
        {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->software_nodes},
        {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->software_order},
        {4, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &impl_->uniform},
    }};
    impl_->primary_stage = std::make_unique<I001ComputeStage>(
        impl_->context,
        shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "n003_primary_software.spv"),
        primary_bindings);

    const std::array<I001Binding, 7> composite_bindings{{
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->primary_hits},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->storage_slots},
        {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->image},
        {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->triangle_buffer},
        {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->software_nodes},
        {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->software_order},
        {6, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &impl_->uniform},
    }};
    impl_->composite_stage = std::make_unique<I001ComputeStage>(
        impl_->context,
        shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "n003_composite_software.spv"),
        composite_bindings,
        sizeof(StoragePush));

    impl_->calculate_memory();
}

I001FrameResult I001Runtime::run_n003_vanilla_topology_churn_frame() {
    if (!impl_) {
        throw std::runtime_error("N003 vanilla topology runtime is not initialized");
    }
    if (impl_->options.variant != I001Variant::VanillaSoftware ||
        impl_->options.scenario != I001Scenario::DeformingControl) {
        throw std::runtime_error(
            "N003 vanilla topology frame requires VanillaSoftware/deforming-control");
    }
    if (impl_->geometry_is_target) {
        throw std::runtime_error(
            "N003 vanilla topology frame requires a fresh source state");
    }
    if (!impl_->software_cpu || impl_->moving.primitives.empty()) {
        throw std::runtime_error(
            "N003 vanilla topology frame has no software BVH/dynamic owner");
    }

    using Clock = std::chrono::steady_clock;
    const auto elapsed_us = [](Clock::time_point start) {
        return std::chrono::duration<double, std::micro>(
            Clock::now() - start).count();
    };
    const auto source_steady_peak = impl_->memory_stats.peak_resident_bytes;
    const auto total_start = Clock::now();
    const auto prepare_start = Clock::now();

    std::uint32_t max_primitive_id = 0U;
    for (const auto& triangle : impl_->b_scene.triangles) {
        if (triangle.primitive_id != lane_b::kInvalidId) {
            max_primitive_id = std::max(max_primitive_id, triangle.primitive_id);
        }
    }
    const auto primitive_budget = impl_->moving.primitives.size() + 1U;
    if (primitive_budget > std::numeric_limits<std::uint32_t>::max() ||
        max_primitive_id >
            std::numeric_limits<std::uint32_t>::max() -
                static_cast<std::uint32_t>(primitive_budget)) {
        throw std::runtime_error(
            "N003 vanilla topology replacement primitive-id range overflow");
    }

    const float amplitude = std::max(
        impl_->moving.delta_x,
        lane_b::b002_segment_size(impl_->b_scene) * 0.04F);
    std::size_t replaced = 0U;
    std::vector<std::array<float, 4>> surface_positions;
    surface_positions.reserve(impl_->moving.primitives.size());

    // Match N002's frozen high-churn mutation exactly: replace half of the
    // selected dynamic-owner primitive identities and geometry while keeping
    // primitive count and scene bounds fixed.
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
                max_primitive_id + 1U + static_cast<std::uint32_t>(local);
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
            sample.position[0], sample.position[1],
            sample.position[2], sample.position[3],
        });
    }
    const auto expected_replaced = (impl_->moving.primitives.size() + 1U) / 2U;
    if (replaced != expected_replaced) {
        throw std::runtime_error(
            "N003 vanilla topology mutation diverged from frozen 50% schedule");
    }
    const auto geometry_prepare_cpu_us = elapsed_us(prepare_start);

    std::vector<lane_b::B002BufferUpdate> surface_updates;
    std::vector<GpuTriangle> moved_triangles;
    std::vector<lane_b::B002BufferUpdate> triangle_updates;
    surface_updates.reserve(impl_->moving.primitives.size());
    moved_triangles.reserve(impl_->moving.primitives.size());
    triangle_updates.reserve(impl_->moving.primitives.size());

    for (std::size_t local = 0; local < impl_->moving.primitives.size(); ++local) {
        const auto primitive = impl_->moving.primitives[local];
        surface_updates.push_back({
            VkDeviceSize(primitive) * VkDeviceSize(sizeof(std::array<float, 4>)),
            surface_positions[local].data(),
            VkDeviceSize(sizeof(std::array<float, 4>)),
        });
        moved_triangles.push_back(
            lane_b::to_gpu_triangle(impl_->b_scene.triangles.at(primitive)));
    }
    for (std::size_t local = 0; local < impl_->moving.primitives.size(); ++local) {
        const auto primitive = impl_->moving.primitives[local];
        triangle_updates.push_back({
            VkDeviceSize(primitive) * VkDeviceSize(sizeof(GpuTriangle)),
            &moved_triangles[local],
            VkDeviceSize(sizeof(GpuTriangle)),
        });
    }

    const auto surface_update_gpu_us =
        impl_->context.update_device_buffer_timed(impl_->surfaces, surface_updates);
    const auto geometry_transfer_gpu_us =
        impl_->context.update_device_buffer_timed(
            impl_->triangle_buffer, triangle_updates);

    const auto rebuild_start = Clock::now();
    impl_->software_cpu->rebuild(impl_->b_scene.triangles);
    const auto software_bvh_rebuild_cpu_us = elapsed_us(rebuild_start);
    if (impl_->software_cpu->root() != 0U) {
        throw std::runtime_error(
            "N003 vanilla topology software BVH root contract changed");
    }
    const auto nodes = impl_->software_cpu->gpu_nodes();
    const auto& order = impl_->software_cpu->ordered_primitives();
    const auto node_bytes =
        VkDeviceSize(nodes.size() * sizeof(lane_b::GpuBvhNode));
    const auto order_bytes =
        VkDeviceSize(order.size() * sizeof(std::uint32_t));
    if (impl_->software_nodes.size < node_bytes ||
        impl_->software_order.size < order_bytes) {
        throw std::runtime_error(
            "N003 vanilla topology unexpectedly requires descriptor rebind");
    }
    const lane_b::B002BufferUpdate node_update{
        0U, nodes.data(), node_bytes};
    const lane_b::B002BufferUpdate order_update{
        0U, order.data(), order_bytes};
    const auto hierarchy_upload_gpu_us =
        impl_->context.update_device_buffer_timed(
            impl_->software_nodes,
            std::span<const lane_b::B002BufferUpdate>(&node_update, 1)) +
        impl_->context.update_device_buffer_timed(
            impl_->software_order,
            std::span<const lane_b::B002BufferUpdate>(&order_update, 1));

    impl_->geometry_is_target = true;
    impl_->calculate_memory();
    auto result = impl_->run_frame(true);

    const auto maintenance_gpu_us =
        surface_update_gpu_us + geometry_transfer_gpu_us +
        hierarchy_upload_gpu_us;
    result.timings.traversal_maintenance_gpu_us = maintenance_gpu_us;
    result.timings.dynamic_update_wall_us = elapsed_us(total_start);
    result.timings.geometry_prepare_cpu_us = geometry_prepare_cpu_us;
    result.timings.surface_update_gpu_us = surface_update_gpu_us;
    result.timings.geometry_transfer_gpu_us = geometry_transfer_gpu_us;
    result.timings.hierarchy_upload_gpu_us = hierarchy_upload_gpu_us;
    result.timings.software_bvh_rebuild_cpu_us = software_bvh_rebuild_cpu_us;
    result.timings.complete_gpu_us += maintenance_gpu_us;
    result.timings.complete_renderer_gpu_us += maintenance_gpu_us;
    result.timings.incremental_gi_us += maintenance_gpu_us;

    result.stats.moved_primitives =
        static_cast<std::uint32_t>(impl_->moving.primitives.size());
    result.stats.topology_mutations = 1U;
    result.stats.topology_replaced_primitives =
        static_cast<std::uint32_t>(replaced);
    result.stats.backend_rebuilds = 1U;
    result.memory.old_new_overlap_bytes = 0U;

    // Match N002's true-lifetime convention. Every partial upload is
    // synchronously fenced and destroys its host-visible staging buffer before
    // the next upload starts, so only the largest staging payload can overlap
    // the steady device-resident set at once. The vanilla software BVH rebuild
    // is CPU-side and does not create an old/new device-AS overlap.
    const auto partition_count = impl_->moving.primitives.size();
    const auto surface_staging = n002_checked_mul(
        partition_count,
        sizeof(std::array<float, 4>));
    const auto triangle_staging = n002_checked_mul(
        partition_count,
        sizeof(GpuTriangle));
    const auto node_staging = static_cast<std::size_t>(node_bytes);
    const auto order_staging = static_cast<std::size_t>(order_bytes);
    const auto max_staging = std::max(
        {surface_staging, triangle_staging, node_staging, order_staging});
    const auto steady_peak = std::max(
        source_steady_peak,
        result.memory.peak_resident_bytes);
    result.memory.peak_resident_bytes = std::max(
        result.memory.peak_resident_bytes,
        n002_checked_add(steady_peak, max_staging));

    impl_->memory_stats = result.memory;
    impl_->last = result;
    impl_->have_last = true;
    return result;
}

} // namespace phos::gi::research::integration

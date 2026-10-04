#include "n002_runtime.cpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::integration {

void I001Runtime::set_n004_motion_fraction(float fraction) {
    if (!std::isfinite(fraction) || fraction < 0.0F || fraction > 1.0F) {
        throw std::runtime_error("N004 motion fraction must be finite and within [0,1]");
    }
    impl_->settings.camera_motion_fraction = fraction;
    impl_->settings.light_motion_fraction = fraction;
}

I001N004HitDiagnostics I001Runtime::n004_hit_diagnostics() {
    namespace traversal = phos::gi::research::lane_b;
    if (!impl_->have_last) {
        throw std::runtime_error("N004 hit diagnostics requested before a frame");
    }

    const auto work_count = impl_->last.stats.work_items;
    std::vector<traversal::GpuRay> gpu_rays(work_count);
    std::vector<traversal::GpuHit> gpu_hits(work_count);
    impl_->context.download_device_buffer(
        impl_->rays,
        gpu_rays.data(),
        gpu_rays.size() * sizeof(traversal::GpuRay));
    impl_->context.download_device_buffer(
        impl_->hits,
        gpu_hits.data(),
        gpu_hits.size() * sizeof(traversal::GpuHit));

    // Re-run exactly the GPU software-BVH traversal used by validate_last_frame
    // so N004 can distinguish candidate/HWRT disagreement from a validator
    // reference-path disagreement. This is diagnostic only and does not alter
    // historical N001-N003 correctness semantics.
    GpuSoftwareBvhData validator_cpu(impl_->b_scene.triangles);
    const auto validator_nodes = validator_cpu.gpu_nodes();
    const auto validator_triangles = gpu_triangles(impl_->b_scene);
    auto triangle = impl_->context.upload_device_buffer(
        validator_triangles.data(),
        validator_triangles.size() * sizeof(GpuTriangle),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto nodes = impl_->context.upload_device_buffer(
        validator_nodes.data(),
        validator_nodes.size() * sizeof(traversal::GpuBvhNode),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto ordered = impl_->context.upload_device_buffer(
        validator_cpu.ordered_primitives().data(),
        validator_cpu.ordered_primitives().size() * sizeof(std::uint32_t),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto validator_hits_buffer = impl_->context.create_device_buffer(
        VkDeviceSize(impl_->params.limits[1]) * sizeof(GpuHit),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

    const std::array<I001Binding, 5> bindings{{
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->rays},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &triangle},
        {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &nodes},
        {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &ordered},
        {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &validator_hits_buffer},
    }};
    I001ComputeStage validator_stage(
        impl_->context,
        shader_path(PHOS_GI_LANE_B_SHADER_DIR, "lane_b_b002_software_bvh.spv"),
        bindings,
        sizeof(SoftwareTraversalPush));

    impl_->context.vk().resetFences(1, &impl_->fence);
    impl_->context.vk().resetCommandPool(impl_->command_pool, 0);
    VkCommandBuffer command{};
    auto allocation = detail::make_vk_info<VkCommandBufferAllocateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    allocation.commandPool = impl_->command_pool;
    allocation.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocation.commandBufferCount = 1;
    if (impl_->context.vk().allocateCommandBuffers(&allocation, &command) != VK_SUCCESS) {
        throw std::runtime_error("N004 validator cross-check command allocation failed");
    }
    auto begin = detail::make_vk_info<VkCommandBufferBeginInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (impl_->context.vk().beginCommandBuffer(command, &begin) != VK_SUCCESS) {
        throw std::runtime_error("N004 validator cross-check command begin failed");
    }
    const SoftwareTraversalPush push{
        work_count, validator_cpu.root(), 0U, 0U};
    validator_stage.record(
        command, groups(work_count), 1, 1, &push, sizeof(push));
    i001_compute_barrier(impl_->context, command);
    if (impl_->context.vk().endCommandBuffer(command) != VK_SUCCESS) {
        throw std::runtime_error("N004 validator cross-check command end failed");
    }
    auto submit = detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &command;
    if (impl_->context.vk().queueSubmit(
            impl_->context.queue(), 1, &submit, impl_->fence) != VK_SUCCESS ||
        impl_->context.vk().waitForFences(
            1, &impl_->fence, VK_TRUE, UINT64_MAX) != VK_SUCCESS) {
        throw std::runtime_error("N004 validator cross-check submission failed");
    }

    std::vector<GpuHit> gpu_validator_hits(work_count);
    impl_->context.download_device_buffer(
        validator_hits_buffer,
        gpu_validator_hits.data(),
        gpu_validator_hits.size() * sizeof(GpuHit));

    // B002Buffer is an explicitly-owned Vulkan allocation rather than an RAII
    // wrapper. The N004 cross-check is invoked after individual measured frames,
    // so retaining these temporary buffers until device teardown would leak one
    // set per diagnostic call and could perturb later frames in the same case.
    impl_->context.destroy_buffer(validator_hits_buffer);
    impl_->context.destroy_buffer(ordered);
    impl_->context.destroy_buffer(nodes);
    impl_->context.destroy_buffer(triangle);

    I001N004HitDiagnostics diagnostics{};
    std::size_t candidate_vs_gpu_validator = 0U;
    std::size_t cpu_vs_gpu_validator = 0U;
    bool printed_substantive = false;
    bool printed_validator_difference = false;
    for (std::size_t index = 0; index < gpu_rays.size(); ++index) {
        const auto& gpu_ray = gpu_rays[index];
        const traversal::Ray ray{
            {
                gpu_ray.origin_tmax[0],
                gpu_ray.origin_tmax[1],
                gpu_ray.origin_tmax[2],
            },
            {
                gpu_ray.direction_pad[0],
                gpu_ray.direction_pad[1],
                gpu_ray.direction_pad[2],
            },
            gpu_ray.origin_tmax[3],
        };
        const auto cpu_expected = traversal::trace_reference(
            impl_->b_scene.triangles,
            ray);
        const auto actual = traversal::from_gpu_hit(gpu_hits[index]);
        const auto gpu_validator = traversal::from_gpu_hit(gpu_validator_hits[index]);

        const bool candidate_matches_cpu =
            traversal::equivalent_hit(cpu_expected, actual);
        const bool candidate_matches_gpu_validator =
            traversal::equivalent_hit(gpu_validator, actual);
        const bool cpu_matches_gpu_validator =
            traversal::equivalent_hit(cpu_expected, gpu_validator);
        if (!candidate_matches_gpu_validator) {
            ++candidate_vs_gpu_validator;
        }
        if (!cpu_matches_gpu_validator) {
            ++cpu_vs_gpu_validator;
        }
        if (!printed_validator_difference &&
            candidate_matches_cpu &&
            !candidate_matches_gpu_validator) {
            printed_validator_difference = true;
            std::cerr
                << "N004 validator-reference divergence"
                << " ray_index=" << index
                << " cpu_hit=" << (cpu_expected.hit ? 1 : 0)
                << " cpu_t=" << cpu_expected.t
                << " cpu_primitive=" << cpu_expected.primitive_id
                << " candidate_hit=" << (actual.hit ? 1 : 0)
                << " candidate_t=" << actual.t
                << " candidate_primitive=" << actual.primitive_id
                << " gpu_validator_hit=" << (gpu_validator.hit ? 1 : 0)
                << " gpu_validator_t=" << gpu_validator.t
                << " gpu_validator_primitive=" << gpu_validator.primitive_id
                << '\n';
        }

        if (candidate_matches_cpu) {
            continue;
        }

        ++diagnostics.strict_mismatches;
        bool surface_tie = false;
        float normal_dot = 0.0F;
        float distance_delta = 0.0F;
        if (cpu_expected.hit && actual.hit) {
            distance_delta = std::abs(cpu_expected.t - actual.t);
            normal_dot = traversal::dot(
                traversal::normalize(cpu_expected.normal),
                traversal::normalize(actual.normal));
        }
        if (cpu_expected.hit && actual.hit &&
            cpu_expected.primitive_id != actual.primitive_id &&
            cpu_expected.material_id == actual.material_id &&
            cpu_expected.instance_id == actual.instance_id) {
            const auto tolerance = std::max(
                traversal::kHitDistanceAbsTolerance,
                std::abs(cpu_expected.t) * traversal::kHitDistanceRelTolerance);
            surface_tie =
                distance_delta <= tolerance &&
                normal_dot > 0.9999F;
        }

        if (surface_tie) {
            ++diagnostics.surface_tie_equivalent_mismatches;
        } else {
            ++diagnostics.substantive_mismatches;
            if (!printed_substantive) {
                printed_substantive = true;
                std::cerr
                    << "N004 substantive hit mismatch"
                    << " ray_index=" << index
                    << " ray_origin=(" << ray.origin.x << ',' << ray.origin.y << ',' << ray.origin.z << ')'
                    << " ray_direction=(" << ray.direction.x << ',' << ray.direction.y << ',' << ray.direction.z << ')'
                    << " ray_tmax=" << ray.t_max
                    << " expected_hit=" << (cpu_expected.hit ? 1 : 0)
                    << " expected_t=" << cpu_expected.t
                    << " expected_primitive=" << cpu_expected.primitive_id
                    << " expected_material=" << cpu_expected.material_id
                    << " expected_instance=" << cpu_expected.instance_id
                    << " expected_normal=(" << cpu_expected.normal.x << ',' << cpu_expected.normal.y << ',' << cpu_expected.normal.z << ')'
                    << " actual_hit=" << (actual.hit ? 1 : 0)
                    << " actual_t=" << actual.t
                    << " actual_primitive=" << actual.primitive_id
                    << " actual_material=" << actual.material_id
                    << " actual_instance=" << actual.instance_id
                    << " actual_normal=(" << actual.normal.x << ',' << actual.normal.y << ',' << actual.normal.z << ')'
                    << " distance_delta=" << distance_delta
                    << " normal_dot=" << normal_dot
                    << '\n';
            }
        }
    }

    std::cerr
        << "N004 validator cross-check"
        << " cpu_vs_candidate=" << diagnostics.strict_mismatches
        << " gpu_validator_vs_candidate=" << candidate_vs_gpu_validator
        << " cpu_vs_gpu_validator=" << cpu_vs_gpu_validator
        << '\n';
    return diagnostics;
}

} // namespace phos::gi::research::integration

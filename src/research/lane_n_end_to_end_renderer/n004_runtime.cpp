#include "n002_runtime.cpp"

#include <algorithm>
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

    I001N004HitDiagnostics diagnostics{};
    bool printed_substantive = false;
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
        const auto expected = traversal::trace_reference(
            impl_->b_scene.triangles,
            ray);
        const auto actual = traversal::from_gpu_hit(gpu_hits[index]);
        if (traversal::equivalent_hit(expected, actual)) {
            continue;
        }

        ++diagnostics.strict_mismatches;
        bool surface_tie = false;
        float normal_dot = 0.0F;
        float distance_delta = 0.0F;
        if (expected.hit && actual.hit) {
            distance_delta = std::abs(expected.t - actual.t);
            normal_dot = traversal::dot(
                traversal::normalize(expected.normal),
                traversal::normalize(actual.normal));
        }
        if (expected.hit && actual.hit &&
            expected.primitive_id != actual.primitive_id &&
            expected.material_id == actual.material_id &&
            expected.instance_id == actual.instance_id) {
            const auto tolerance = std::max(
                traversal::kHitDistanceAbsTolerance,
                std::abs(expected.t) * traversal::kHitDistanceRelTolerance);
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
                    << " expected_hit=" << (expected.hit ? 1 : 0)
                    << " expected_t=" << expected.t
                    << " expected_primitive=" << expected.primitive_id
                    << " expected_material=" << expected.material_id
                    << " expected_instance=" << expected.instance_id
                    << " expected_normal=(" << expected.normal.x << ',' << expected.normal.y << ',' << expected.normal.z << ')'
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
    return diagnostics;
}

} // namespace phos::gi::research::integration

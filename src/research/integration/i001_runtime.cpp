#include "i001_runtime.hpp"

#include "i001_compute.hpp"

#include "../lane_a_split_rc/a001_runtime.hpp"
#include "../lane_a_split_rc/a001_scene.hpp"
#include "../lane_a_split_rc/a001_analysis.hpp"
#include "../lane_b_traversal/b002_compute.hpp"
#include "../lane_b_traversal/b002_gpu_layout.hpp"
#include "../lane_b_traversal/b002_hwrt.hpp"
#include "../lane_b_traversal/b002_scene.hpp"
#include "../lane_b_traversal/b002_vulkan.hpp"
#include "../lane_b_traversal/b003_micro_bvh8.hpp"
#include "../lane_b_traversal/b003_quantized_bvh8.hpp"
#include "../lane_b_traversal/gpu_software_bvh.hpp"
#include "../lane_b_traversal/lane_a_stream_v1.hpp"
#include "../lane_b_traversal/hierarchical_stratabrick.hpp"
#include "../lane_b_traversal/traversal_common.hpp"
#include "../lane_e_dynamic_geometry/e003_instance_payload.hpp"
#include "vk_init.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <chrono>
#include <compare>
#include <cstring>
#include <filesystem>
#include <limits>
#include <map>
#include <memory>
#include <span>
#include <stdexcept>
#include <tuple>
#include <utility>
#include <vector>

namespace phos::gi::research::integration {
namespace {

namespace lane_a = phos::gi::lane_a;
namespace lane_b = phos::gi::research::lane_b;
namespace lane_e = phos::gi::research::lane_e;

using lane_b::B002Buffer;
using lane_b::B002HwrtTraversal;
using lane_b::B002VulkanContext;
using lane_b::GpuHit;
using lane_b::GpuRay;
using lane_b::GpuSoftwareBvhData;
using lane_b::GpuTriangle;
using lane_b::HierarchicalStrataBrick;
using lane_b::HierarchicalTraversalPush;
using lane_b::LaneAWorkItemV1;
using lane_b::SoftwareTraversalPush;

constexpr std::uint32_t kQueryCount = 24U;
constexpr std::uint32_t kHashMaxProbe = 128U;

struct alignas(16) HashSlotCpu {
    std::int32_t key[4]{};
    std::uint32_t data[4]{};
};
static_assert(sizeof(HashSlotCpu) == 32);

struct alignas(16) StoragePush {
    std::uint32_t mask{};
    std::uint32_t max_probe{};
    std::uint32_t frame_id{};
    std::uint32_t phase{};
};
static_assert(sizeof(StoragePush) == 16);

struct alignas(16) InvalidationPush {
    std::uint32_t slot_count{};
    std::uint32_t frame_id{};
    std::uint32_t reserved0{};
    std::uint32_t reserved1{};
};
static_assert(sizeof(InvalidationPush) == 16);

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

[[nodiscard]] std::uint32_t groups(std::uint32_t count) noexcept {
    return (count + 63U) / 64U;
}

[[nodiscard]] std::uint32_t estimated_storage_capacity(
    const lane_a::SceneSurfaceSet& scene,
    const lane_a::A001ParamsGpu& params) {
    const auto tile_count = params.counts[1] * params.counts[2];
    std::vector<float> depth(
        tile_count,
        std::numeric_limits<float>::infinity());

    for (const auto& sample : scene.samples) {
        const lane_b::Vec3 position{
            sample.position[0],
            sample.position[1],
            sample.position[2],
        };
        const lane_b::Vec3 eye{
            params.camera_pos_near[0],
            params.camera_pos_near[1],
            params.camera_pos_near[2],
        };
        const auto rel = position - eye;
        const lane_b::Vec3 forward{
            params.camera_forward_far[0],
            params.camera_forward_far[1],
            params.camera_forward_far[2],
        };
        const auto distance = lane_b::dot(rel, forward);
        if (distance < params.camera_pos_near[3] ||
            distance > params.camera_forward_far[3]) {
            continue;
        }

        const lane_b::Vec3 right{
            params.camera_right_tan_x[0],
            params.camera_right_tan_x[1],
            params.camera_right_tan_x[2],
        };
        const lane_b::Vec3 up{
            params.camera_up_tan_y[0],
            params.camera_up_tan_y[1],
            params.camera_up_tan_y[2],
        };
        const auto nx =
            lane_b::dot(rel, right) /
            (distance * params.camera_right_tan_x[3]);
        const auto ny =
            lane_b::dot(rel, up) /
            (distance * params.camera_up_tan_y[3]);
        if (std::abs(nx) > 1.0F || std::abs(ny) > 1.0F) {
            continue;
        }

        const auto x = std::min(
            params.counts[1] - 1U,
            static_cast<std::uint32_t>(
                std::max(
                    0.0F,
                    (nx * 0.5F + 0.5F) *
                        float(params.counts[1]))));
        const auto y = std::min(
            params.counts[2] - 1U,
            static_cast<std::uint32_t>(
                std::max(
                    0.0F,
                    (ny * 0.5F + 0.5F) *
                        float(params.counts[2]))));
        const auto tile = y * params.counts[1] + x;
        depth[tile] = std::min(depth[tile], distance);
    }

    const auto visible = static_cast<std::uint64_t>(
        std::count_if(
            depth.begin(),
            depth.end(),
            [](float value) { return std::isfinite(value); }));
    const auto expected_outputs =
        visible * params.counts[3];
    const auto capped_outputs =
        std::min<std::uint64_t>(
            params.limits[2],
            expected_outputs + expected_outputs / 4U + 16U);
    const auto requested_slots =
        std::max<std::uint64_t>(2U, capped_outputs * 2U);
    if (requested_slots > std::numeric_limits<std::uint32_t>::max()) {
        fail("I001 estimated storage capacity exceeds 32-bit range");
    }
    return static_cast<std::uint32_t>(requested_slots);
}

[[nodiscard]] std::uint32_t next_pow2(std::uint32_t value) {
    if (value <= 1U) return 1U;
    --value;
    value |= value >> 1U;
    value |= value >> 2U;
    value |= value >> 4U;
    value |= value >> 8U;
    value |= value >> 16U;
    if (value == std::numeric_limits<std::uint32_t>::max()) {
        fail("I001 hash capacity overflow");
    }
    return value + 1U;
}

[[nodiscard]] std::string shader_path(
    const char* directory,
    const char* filename) {
    return (std::filesystem::path(directory) / filename).string();
}

[[nodiscard]] bool uses_hwrt(I001Variant value) noexcept {
    return value == I001Variant::CombinedHwrt ||
           value == I001Variant::RigidInstanceHwrtUpdate ||
           value == I001Variant::RigidInstanceHwrtBuild ||
           value == I001Variant::DepthReuseHwrt ||
           value == I001Variant::BoundedHwrt;
}

[[nodiscard]] bool uses_rigid_instance_hwrt(
    I001Variant value) noexcept {
    return value == I001Variant::RigidInstanceHwrtUpdate ||
           value == I001Variant::RigidInstanceHwrtBuild;
}

[[nodiscard]] lane_b::HwrtTlasPolicy rigid_tlas_policy(
    I001Variant value) noexcept {
    return value == I001Variant::RigidInstanceHwrtBuild
        ? lane_b::HwrtTlasPolicy::Build
        : lane_b::HwrtTlasPolicy::Update;
}

[[nodiscard]] bool uses_rigid_instance_software(
    I001Variant value) noexcept {
    return value == I001Variant::RigidInstanceSoftwareBinary ||
           value == I001Variant::RigidInstanceSoftwareQuantized;
}

[[nodiscard]] bool uses_rigid_instance_software_binary(
    I001Variant value) noexcept {
    return value == I001Variant::RigidInstanceSoftwareBinary;
}

[[nodiscard]] bool uses_rigid_instance_software_quantized(
    I001Variant value) noexcept {
    return value == I001Variant::RigidInstanceSoftwareQuantized;
}

[[nodiscard]] bool uses_quantized(I001Variant value) noexcept {
    return value == I001Variant::CombinedSoftware;
}

[[nodiscard]] bool uses_bounded(I001Variant value) noexcept {
    return value == I001Variant::BoundedHwrt;
}

[[nodiscard]] lane_a::A001Case a001_case(
    I001Scenario scenario,
    bool target_state) noexcept {
    if (!target_state) return lane_a::A001Case::Static;
    switch (scenario) {
    case I001Scenario::Static:
        return lane_a::A001Case::Static;
    case I001Scenario::CameraMotion:
        return lane_a::A001Case::CameraMotion;
    case I001Scenario::LightMotion:
        return lane_a::A001Case::LightMotion;
    case I001Scenario::MovingRigid:
    case I001Scenario::DeformingControl:
    case I001Scenario::SparseStress:
    case I001Scenario::DenseStress:
    case I001Scenario::LargeWorldStress:
    case I001Scenario::VerticalWorldStress:
        return lane_a::A001Case::Static;
    }
    return lane_a::A001Case::Static;
}

[[nodiscard]] std::vector<std::array<float, 4>> surface_positions(
    const lane_a::SceneSurfaceSet& surfaces) {
    std::vector<std::array<float, 4>> output(surfaces.samples.size());
    for (std::size_t index = 0; index < surfaces.samples.size(); ++index) {
        std::copy_n(
            surfaces.samples[index].position,
            4,
            output[index].data());
    }
    return output;
}

[[nodiscard]] std::vector<GpuTriangle> gpu_triangles(
    const std::vector<lane_b::Triangle>& triangles) {
    std::vector<GpuTriangle> output;
    output.reserve(triangles.size());
    for (const auto& triangle : triangles) {
        output.push_back(lane_b::to_gpu_triangle(triangle));
    }
    return output;
}

[[nodiscard]] std::vector<GpuTriangle> gpu_triangles(
    const lane_b::B002Scene& scene) {
    return gpu_triangles(scene.triangles);
}

struct MovingSelection {
    std::uint32_t instance_id{};
    std::vector<std::uint32_t> primitives;
    float delta_x{};
    std::uint32_t membership_changes{};
};

[[nodiscard]] std::vector<lane_b::Triangle> translated_geometry(
    const std::vector<lane_b::Triangle>& source,
    std::span<const std::uint32_t> moved,
    float delta_x) {
    auto output = source;
    const lane_b::Vec3 delta{delta_x, 0.0F, 0.0F};
    for (const auto primitive : moved) {
        auto& triangle = output.at(primitive);
        triangle.v0 = triangle.v0 + delta;
        triangle.v1 = triangle.v1 + delta;
        triangle.v2 = triangle.v2 + delta;
    }
    return output;
}

[[nodiscard]] std::vector<lane_b::Triangle> deformed_geometry(
    const std::vector<lane_b::Triangle>& source,
    std::span<const std::uint32_t> moved,
    float amplitude) {
    auto output = source;
    float min_x = std::numeric_limits<float>::infinity();
    float max_x = -std::numeric_limits<float>::infinity();
    for (const auto primitive : moved) {
        const auto& triangle = source.at(primitive);
        for (const auto& vertex : {triangle.v0, triangle.v1, triangle.v2}) {
            min_x = std::min(min_x, vertex.x);
            max_x = std::max(max_x, vertex.x);
        }
    }
    const float extent = std::max(max_x - min_x, 1.0e-4F);
    constexpr float pi = 3.14159265358979323846F;
    const auto deform = [&](lane_b::Vec3 vertex) {
        const float t = std::clamp((vertex.x - min_x) / extent, 0.0F, 1.0F);
        vertex.y += amplitude * std::sin(pi * t);
        vertex.z += amplitude * 0.25F * std::sin(2.0F * pi * t);
        return vertex;
    };
    for (const auto primitive : moved) {
        auto& triangle = output.at(primitive);
        triangle.v0 = deform(triangle.v0);
        triangle.v1 = deform(triangle.v1);
        triangle.v2 = deform(triangle.v2);
    }
    return output;
}

void sync_surface_positions(
    lane_a::SceneSurfaceSet& surfaces,
    const std::vector<lane_b::Triangle>& triangles,
    std::span<const std::uint32_t> primitives) {
    for (const auto primitive : primitives) {
        const auto& triangle = triangles.at(primitive);
        auto& sample = surfaces.samples.at(primitive);
        sample.position[0] =
            (triangle.v0.x + triangle.v1.x + triangle.v2.x) / 3.0F;
        sample.position[1] =
            (triangle.v0.y + triangle.v1.y + triangle.v2.y) / 3.0F;
        sample.position[2] =
            (triangle.v0.z + triangle.v1.z + triangle.v2.z) / 3.0F;
    }
}

[[nodiscard]] MovingSelection choose_moving_selection(
    const lane_b::B002Scene& scene) {
    std::uint32_t max_instance = 0U;
    for (const auto& triangle : scene.triangles) {
        if (triangle.instance_id != lane_b::kInvalidId) {
            max_instance = std::max(max_instance, triangle.instance_id);
        }
    }
    std::vector<std::vector<std::uint32_t>> groups(
        std::size_t(max_instance) + 1U);
    for (std::uint32_t primitive = 0U;
         primitive < scene.triangles.size();
         ++primitive) {
        const auto instance = scene.triangles[primitive].instance_id;
        if (instance != lane_b::kInvalidId) {
            groups.at(instance).push_back(primitive);
        }
    }

    std::vector<std::uint32_t> candidates;
    for (std::uint32_t instance = 0U; instance < groups.size(); ++instance) {
        const auto count = groups[instance].size();
        if (count >= 32U && count <= 2048U) {
            candidates.push_back(instance);
        }
    }
    for (std::uint32_t instance = 0U; instance < groups.size(); ++instance) {
        if (!groups[instance].empty() &&
            std::find(candidates.begin(), candidates.end(), instance) ==
                candidates.end()) {
            candidates.push_back(instance);
        }
    }

    const auto segment_size = lane_b::b002_segment_size(scene);
    constexpr std::array<float, 5> multipliers{
        1.25F, 2.5F, 5.0F, 10.0F, 20.0F};
    for (const auto instance : candidates) {
        for (const auto multiplier : multipliers) {
            const auto delta = segment_size * multiplier;
            auto target = translated_geometry(
                scene.triangles, groups[instance], delta);
            lane_b::HierarchicalStrataBrick probe(
                scene.triangles, segment_size);
            const auto stats = probe.update(target, groups[instance]);
            if (stats.membership_changes != 0U) {
                return {
                    instance,
                    groups[instance],
                    delta,
                    static_cast<std::uint32_t>(stats.membership_changes),
                };
            }
        }
    }
    fail("I001 could not select a topology-changing moving-rigid regime");
}

[[nodiscard]] MovingSelection choose_deforming_selection(
    const lane_b::B002Scene& scene) {
    auto selection = choose_moving_selection(scene);
    selection.delta_x = lane_b::b002_segment_size(scene) * 0.08F;
    auto target = deformed_geometry(
        scene.triangles,
        selection.primitives,
        selection.delta_x);
    lane_b::HierarchicalStrataBrick probe(
        scene.triangles,
        lane_b::b002_segment_size(scene));
    const auto stats = probe.update(target, selection.primitives);
    selection.membership_changes =
        static_cast<std::uint32_t>(stats.membership_changes);
    return selection;
}

void apply_scene_stress(
    I001Scenario scenario,
    lane_a::SceneSurfaceSet& a_scene,
    lane_b::B002Scene& b_scene) {
    if (scenario != I001Scenario::LargeWorldStress &&
        scenario != I001Scenario::VerticalWorldStress) {
        return;
    }

    const bool large = scenario == I001Scenario::LargeWorldStress;
    const float offset_x = large ? 1.0e6F : 0.0F;
    const float offset_z = large ? -1.0e6F : 0.0F;
    const float scale_y = large ? 1.0F : 16.0F;

    for (auto& sample : a_scene.samples) {
        sample.position[0] += offset_x;
        sample.position[1] *= scale_y;
        sample.position[2] += offset_z;
    }

    for (auto& triangle : b_scene.triangles) {
        auto transform = [&](lane_b::Vec3 value) {
            return lane_b::Vec3{
                value.x + offset_x,
                value.y * scale_y,
                value.z + offset_z,
            };
        };
        triangle.v0 = transform(triangle.v0);
        triangle.v1 = transform(triangle.v1);
        triangle.v2 = transform(triangle.v2);
    }

    for (int axis = 0; axis < 3; ++axis) {
        a_scene.min_position[axis] = std::numeric_limits<float>::infinity();
        a_scene.max_position[axis] = -std::numeric_limits<float>::infinity();
    }
    b_scene.bounds = {};
    for (std::size_t index = 0; index < a_scene.samples.size(); ++index) {
        for (int axis = 0; axis < 3; ++axis) {
            const auto value = a_scene.samples[index].position[axis];
            a_scene.min_position[axis] =
                std::min(a_scene.min_position[axis], value);
            a_scene.max_position[axis] =
                std::max(a_scene.max_position[axis], value);
        }
        b_scene.bounds = lane_b::merge(
            b_scene.bounds,
            lane_b::triangle_bounds(b_scene.triangles[index]));
    }
    b_scene.diagonal = lane_b::length(
        b_scene.bounds.max - b_scene.bounds.min);
    if (!std::isfinite(b_scene.diagonal) || b_scene.diagonal <= 0.0F) {
        fail("I001 stress transform produced invalid scene bounds");
    }
}

[[nodiscard]] double timestamp_us(
    std::uint64_t begin,
    std::uint64_t end,
    float period_ns) noexcept {
    return double(end - begin) * double(period_ns) / 1000.0;
}

struct ProbeKey {
    std::int32_t x{};
    std::int32_t y{};
    std::int32_t z{};
    std::uint32_t cascade{};
    auto operator<=>(const ProbeKey&) const = default;
};

[[nodiscard]] ProbeKey slot_key(const HashSlotCpu& slot) noexcept {
    return {
        slot.key[0],
        slot.key[1],
        slot.key[2],
        static_cast<std::uint32_t>(slot.key[3]),
    };
}


[[nodiscard]] std::uint32_t probe_token(
    const ProbeKey& key) noexcept {
    constexpr auto tombstone =
        std::numeric_limits<std::uint32_t>::max();
    if (key.x < 0 || key.x > 1023 ||
        key.y < 0 || key.y > 1023 ||
        key.z < 0 || key.z > 1023 ||
        key.cascade > 3U) {
        return tombstone;
    }
    const auto packed =
        static_cast<std::uint32_t>(key.x) |
        (static_cast<std::uint32_t>(key.y) << 10U) |
        (static_cast<std::uint32_t>(key.z) << 20U) |
        (key.cascade << 30U);
    if (packed >= 0xfffffffeU) {
        return tombstone;
    }
    return packed + 1U;
}

[[nodiscard]] double slot_value(const HashSlotCpu& slot) noexcept {
    return slot.data[2] == 0U
        ? 0.0
        : double(slot.data[1]) /
              (double(slot.data[2]) * 65535.0);
}


[[nodiscard]] lane_b::Vec3 i001_ray_direction(
    std::uint32_t ray) noexcept {
    constexpr float v = 0.5773502691896258F;
    return {
        (ray & 1U) != 0U ? v : -v,
        (ray & 2U) != 0U ? v : -v,
        (ray & 4U) != 0U ? v : -v,
    };
}

[[nodiscard]] bool within_float_ulps(
    float actual,
    float expected,
    int ulps) noexcept {
    if (!std::isfinite(actual) || !std::isfinite(expected)) {
        return actual == expected;
    }
    float lower = expected;
    float upper = expected;
    for (int index = 0; index < ulps; ++index) {
        lower = std::nextafter(
            lower,
            -std::numeric_limits<float>::infinity());
        upper = std::nextafter(
            upper,
            std::numeric_limits<float>::infinity());
    }
    return actual >= lower && actual <= upper;
}

} // namespace

const char* i001_variant_name(I001Variant value) noexcept {
    switch (value) {
    case I001Variant::VanillaSoftware: return "vanilla-software";
    case I001Variant::CombinedHwrt: return "combined-hwrt";
    case I001Variant::RigidInstanceHwrtUpdate:
        return "rigid-instance-hwrt-update";
    case I001Variant::RigidInstanceHwrtBuild:
        return "rigid-instance-hwrt-build";
    case I001Variant::RigidInstanceSoftwareBinary:
        return "rigid-instance-software-binary";
    case I001Variant::RigidInstanceSoftwareQuantized:
        return "rigid-instance-software-quantized";
    case I001Variant::CombinedSoftware: return "combined-software";
    case I001Variant::DepthReuseHwrt: return "depth-reuse-hwrt";
    case I001Variant::BoundedHwrt: return "bounded-hwrt";
    }
    return "unknown";
}

const char* i001_scenario_name(I001Scenario value) noexcept {
    switch (value) {
    case I001Scenario::Static: return "static";
    case I001Scenario::CameraMotion: return "camera-motion";
    case I001Scenario::LightMotion: return "light-motion";
    case I001Scenario::MovingRigid: return "moving-rigid";
    case I001Scenario::DeformingControl: return "deforming-control";
    case I001Scenario::SparseStress: return "sparse-stress";
    case I001Scenario::DenseStress: return "dense-stress";
    case I001Scenario::LargeWorldStress: return "large-world-stress";
    case I001Scenario::VerticalWorldStress: return "vertical-world-stress";
    }
    return "unknown";
}

I001Variant i001_parse_variant(const std::string& value) {
    if (value == "vanilla-software") return I001Variant::VanillaSoftware;
    if (value == "combined-hwrt") return I001Variant::CombinedHwrt;
    if (value == "rigid-instance-hwrt-update")
        return I001Variant::RigidInstanceHwrtUpdate;
    if (value == "rigid-instance-hwrt-build")
        return I001Variant::RigidInstanceHwrtBuild;
    if (value == "rigid-instance-software-binary")
        return I001Variant::RigidInstanceSoftwareBinary;
    if (value == "rigid-instance-software-quantized")
        return I001Variant::RigidInstanceSoftwareQuantized;
    if (value == "combined-software") return I001Variant::CombinedSoftware;
    if (value == "depth-reuse-hwrt") return I001Variant::DepthReuseHwrt;
    if (value == "bounded-hwrt") return I001Variant::BoundedHwrt;
    throw std::runtime_error("unknown I001 variant: " + value);
}

I001Scenario i001_parse_scenario(const std::string& value) {
    if (value == "static") return I001Scenario::Static;
    if (value == "camera-motion") return I001Scenario::CameraMotion;
    if (value == "light-motion") return I001Scenario::LightMotion;
    if (value == "moving-rigid") return I001Scenario::MovingRigid;
    if (value == "deforming-control") return I001Scenario::DeformingControl;
    if (value == "sparse-stress") return I001Scenario::SparseStress;
    if (value == "dense-stress") return I001Scenario::DenseStress;
    if (value == "large-world-stress") return I001Scenario::LargeWorldStress;
    if (value == "vertical-world-stress") return I001Scenario::VerticalWorldStress;
    throw std::runtime_error("unknown I001 scenario: " + value);
}

struct I001Runtime::Impl {
    I001Options options;
    B002VulkanContext context;
    lane_a::SceneSurfaceSet a_scene;
    lane_b::B002Scene b_scene;
    lane_a::A001Settings settings;
    lane_a::A001ParamsGpu params{};

    B002Buffer surfaces{}, depth{}, owners{}, counters{}, work{}, indirect{};
    B002Buffer rays{}, hits{}, contributions{}, accum{}, resolved{}, uniform{};
    B002Buffer storage_slots{}, storage_stats{};
    B002Buffer triangle_buffer{}, software_nodes{}, software_order{};
    B002Buffer quant_nodes{}, quant_order{}, quant_hash{};
    B002Buffer instance_nodes{}, instance_order{}, instance_hash{}, instance_table{};

    lane_e::E003BinaryPayload instance_binary_payload;
    lane_e::E003QuantizedPayload instance_quantized_payload;
    std::unique_ptr<GpuSoftwareBvhData> software_cpu;
    std::unique_ptr<HierarchicalStrataBrick> hierarchy_cpu;
    lane_b::B003QuantizedMicroPayload quant_payload;
    std::unique_ptr<B002HwrtTraversal> hwrt;

    std::unique_ptr<I001ComputeStage> depth_stage, owner_stage, producer_stage;
    std::unique_ptr<I001ComputeStage> clamp_stage, finalize_stage, ray_stage;
    std::unique_ptr<I001ComputeStage> traversal_stage, radiance_stage, merge_stage;
    std::unique_ptr<I001ComputeStage> storage_update_stage, invalidation_stage, resolve_stage;

    VkCommandPool command_pool{VK_NULL_HANDLE};
    VkQueryPool query_pool{VK_NULL_HANDLE};
    VkFence fence{VK_NULL_HANDLE};

    I001Memory memory_stats{};
    MovingSelection moving{};
    bool geometry_is_target{};
    bool have_quality_history{};
    std::map<ProbeKey, double> previous_reference_probe;
    std::map<ProbeKey, double> previous_candidate_probe;
    std::uint32_t storage_capacity{};
    std::uint32_t frame_id{};
    I001FrameResult last{};
    bool have_last{};

    explicit Impl(I001Options value)
        : options(std::move(value)),
          context(
              options.validation,
              lane_b::kB002TargetDeviceName,
              uses_hwrt(options.variant)),
          a_scene(lane_a::load_scene_surface_samples(options.scene)),
          b_scene(lane_b::load_b002_scene(options.scene)) {
        if (a_scene.samples.size() != b_scene.triangles.size()) {
            fail("I001 A001/B002 scene primitive identity diverged");
        }
        apply_scene_stress(options.scenario, a_scene, b_scene);

        settings.case_id = lane_a::A001Case::Static;
        settings.tile_width =
            options.scenario == I001Scenario::SparseStress
            ? 64U
            : (options.scenario == I001Scenario::DenseStress ? 256U : 128U);
        settings.tile_height =
            options.scenario == I001Scenario::SparseStress
            ? 36U
            : (options.scenario == I001Scenario::DenseStress ? 144U : 72U);
        settings.cascade_count = 4;
        settings.rays_per_probe = 8;
        params = lane_a::build_a001_params(a_scene, settings);
        if (options.scenario == I001Scenario::MovingRigid) {
            moving = choose_moving_selection(b_scene);
        } else if (options.scenario == I001Scenario::DeformingControl) {
            moving = choose_deforming_selection(b_scene);
        }

        if (uses_bounded(options.variant)) {
            if (options.bounded_owner_capacity == 0U) {
                fail("I001 bounded owner capacity must be positive");
            }
            const std::uint64_t outputs =
                std::uint64_t(options.bounded_owner_capacity) *
                settings.cascade_count;
            const std::uint64_t items =
                outputs * settings.rays_per_probe;
            if (outputs > params.limits[2] || items > params.limits[1]) {
                fail("I001 bounded capacity exceeds full A001 capacity");
            }
            params.limits[1] = static_cast<std::uint32_t>(items);
            params.limits[2] = static_cast<std::uint32_t>(outputs);
        }

        const auto positions = surface_positions(a_scene);
        surfaces = context.upload_device_buffer(
            positions.data(),
            positions.size() * sizeof(positions[0]),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

        const auto tile_count = params.counts[1] * params.counts[2];
        depth = context.create_device_buffer(
            VkDeviceSize(tile_count) * sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        owners = context.create_device_buffer(
            VkDeviceSize(tile_count) * sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        counters = context.create_device_buffer(
            6U * sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        work = context.create_device_buffer(
            VkDeviceSize(params.limits[1]) * sizeof(LaneAWorkItemV1),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        indirect = context.create_device_buffer(
            6U * sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT);
        rays = context.create_device_buffer(
            VkDeviceSize(params.limits[1]) * sizeof(GpuRay),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        hits = context.create_device_buffer(
            VkDeviceSize(params.limits[1]) * sizeof(GpuHit),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        contributions = context.create_device_buffer(
            VkDeviceSize(params.limits[1]) * sizeof(std::uint32_t) * 2U,
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        accum = context.create_device_buffer(
            VkDeviceSize(params.limits[2]) * sizeof(std::uint32_t) * 2U,
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        resolved = context.create_device_buffer(
            VkDeviceSize(params.limits[2]) * sizeof(float),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        uniform = context.create_host_buffer(
            sizeof(params),
            VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT);
        std::memcpy(uniform.mapped, &params, sizeof(params));

        auto storage_capacity_estimate =
            estimated_storage_capacity(a_scene, params);
        {
            auto target_scene = a_scene;
            if (options.scenario == I001Scenario::MovingRigid) {
                for (const auto primitive : moving.primitives) {
                    target_scene.samples.at(primitive).position[0] +=
                        moving.delta_x;
                }
            } else if (options.scenario == I001Scenario::DeformingControl) {
                const auto target_geometry = deformed_geometry(
                    b_scene.triangles,
                    moving.primitives,
                    moving.delta_x);
                sync_surface_positions(
                    target_scene,
                    target_geometry,
                    moving.primitives);
            }
            auto target_settings = settings;
            target_settings.case_id =
                a001_case(options.scenario, true);
            auto target_params =
                lane_a::build_a001_params(
                    target_scene,
                    target_settings);
            target_params.limits[1] = params.limits[1];
            target_params.limits[2] = params.limits[2];
            storage_capacity_estimate = std::max(
                storage_capacity_estimate,
                estimated_storage_capacity(
                    target_scene,
                    target_params));
        }
        storage_capacity = next_pow2(storage_capacity_estimate);
        std::vector<HashSlotCpu> empty_slots(storage_capacity);
        storage_slots = context.upload_device_buffer(
            empty_slots.data(),
            empty_slots.size() * sizeof(HashSlotCpu),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        storage_stats = context.create_device_buffer(
            4U * sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

        prepare_candidate_traversal();
        create_stages();
        create_command_resources();
        calculate_memory();
    }

    ~Impl() {
        context.vk().deviceWaitIdle();
        resolve_stage.reset();
        invalidation_stage.reset();
        storage_update_stage.reset();
        merge_stage.reset();
        radiance_stage.reset();
        traversal_stage.reset();
        ray_stage.reset();
        finalize_stage.reset();
        clamp_stage.reset();
        producer_stage.reset();
        owner_stage.reset();
        depth_stage.reset();
        hwrt.reset();

        if (fence != VK_NULL_HANDLE) context.vk().destroyFence(fence, nullptr);
        if (query_pool != VK_NULL_HANDLE) context.vk().destroyQueryPool(query_pool, nullptr);
        if (command_pool != VK_NULL_HANDLE) context.vk().destroyCommandPool(command_pool, nullptr);

        for (auto* buffer : {
                 &storage_stats, &storage_slots, &uniform, &resolved, &accum,
                 &contributions, &hits, &rays, &indirect, &work, &counters,
                 &owners, &depth, &surfaces, &instance_table, &instance_hash,
                 &instance_order, &instance_nodes, &quant_hash, &quant_order,
                 &quant_nodes, &software_order, &software_nodes, &triangle_buffer}) {
            context.destroy_buffer(*buffer);
        }
    }

    void prepare_candidate_traversal() {
        if (uses_hwrt(options.variant)) {
            if (uses_rigid_instance_hwrt(options.variant)) {
                if (options.scenario != I001Scenario::MovingRigid) {
                    fail("I001 rigid-instance HWRT variants require moving-rigid");
                }
                hwrt = std::make_unique<B002HwrtTraversal>(
                    context,
                    b_scene.triangles,
                    moving.primitives,
                    shader_path(
                        PHOS_GI_LANE_B_SHADER_DIR,
                        "lane_b_b002_hwrt.spv"),
                    false);
            } else {
                hwrt = std::make_unique<B002HwrtTraversal>(
                    context,
                    b_scene.triangles,
                    shader_path(
                        PHOS_GI_LANE_B_SHADER_DIR,
                        "lane_b_b002_hwrt.spv"),
                    false);
            }
            return;
        }

        if (uses_rigid_instance_software(options.variant)) {
            if (options.scenario != I001Scenario::MovingRigid) {
                fail("I001 rigid-instance software variants require moving-rigid");
            }
            const auto segment_size =
                lane_b::b002_segment_size(b_scene);
            if (uses_rigid_instance_software_binary(options.variant)) {
                instance_binary_payload =
                    lane_e::make_e003_binary_payload(
                        b_scene.triangles,
                        moving.primitives,
                        segment_size);
                triangle_buffer = context.upload_device_buffer(
                    instance_binary_payload.triangles.data(),
                    instance_binary_payload.triangles.size() *
                        sizeof(GpuTriangle),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                instance_nodes = context.upload_device_buffer(
                    instance_binary_payload.nodes.data(),
                    instance_binary_payload.nodes.size() *
                        sizeof(lane_b::GpuBvhNode),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                instance_order = context.upload_device_buffer(
                    instance_binary_payload.ordered_primitives.data(),
                    instance_binary_payload.ordered_primitives.size() *
                        sizeof(std::uint32_t),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                instance_hash = context.upload_device_buffer(
                    instance_binary_payload.hash_table.data(),
                    instance_binary_payload.hash_table.size() *
                        sizeof(lane_b::GpuSegmentHashEntry),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                instance_table = context.upload_device_buffer(
                    instance_binary_payload.instances.data(),
                    instance_binary_payload.instances.size() *
                        sizeof(lane_e::E003GpuInstance),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            } else {
                instance_quantized_payload =
                    lane_e::make_e003_quantized_payload(
                        b_scene.triangles,
                        moving.primitives,
                        segment_size);
                triangle_buffer = context.upload_device_buffer(
                    instance_quantized_payload.triangles.data(),
                    instance_quantized_payload.triangles.size() *
                        sizeof(GpuTriangle),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                instance_nodes = context.upload_device_buffer(
                    instance_quantized_payload.nodes.data(),
                    instance_quantized_payload.nodes.size() *
                        sizeof(lane_b::B003GpuQuantNode),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                instance_order = context.upload_device_buffer(
                    instance_quantized_payload.ordered_primitives.data(),
                    instance_quantized_payload.ordered_primitives.size() *
                        sizeof(std::uint32_t),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                instance_hash = context.upload_device_buffer(
                    instance_quantized_payload.hash_table.data(),
                    instance_quantized_payload.hash_table.size() *
                        sizeof(lane_b::GpuSegmentHashEntry),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                instance_table = context.upload_device_buffer(
                    instance_quantized_payload.instances.data(),
                    instance_quantized_payload.instances.size() *
                        sizeof(lane_e::E003GpuInstance),
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            }
            return;
        }

        const auto triangles = gpu_triangles(b_scene);
        triangle_buffer = context.upload_device_buffer(
            triangles.data(),
            triangles.size() * sizeof(GpuTriangle),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

        if (uses_quantized(options.variant)) {
            hierarchy_cpu = std::make_unique<HierarchicalStrataBrick>(
                b_scene.triangles,
                lane_b::b002_segment_size(b_scene));
            auto wide = lane_b::make_b003_wide_micro_payload(hierarchy_cpu->flatten());
            quant_payload = lane_b::make_b003_quantized_micro_payload(wide);

            auto node_capacity = VkDeviceSize(
                quant_payload.nodes.size() *
                sizeof(lane_b::B003GpuQuantNode));
            auto order_capacity = VkDeviceSize(
                quant_payload.ordered_primitives.size() *
                sizeof(std::uint32_t));
            auto hash_capacity = VkDeviceSize(
                quant_payload.hash_table.size() *
                sizeof(lane_b::GpuSegmentHashEntry));

            if (options.scenario == I001Scenario::MovingRigid ||
                options.scenario == I001Scenario::DeformingControl) {
                auto target_geometry =
                    options.scenario == I001Scenario::MovingRigid
                    ? translated_geometry(
                        b_scene.triangles,
                        moving.primitives,
                        moving.delta_x)
                    : deformed_geometry(
                        b_scene.triangles,
                        moving.primitives,
                        moving.delta_x);
                HierarchicalStrataBrick target_hierarchy(
                    target_geometry,
                    lane_b::b002_segment_size(b_scene));
                auto target_wide =
                    lane_b::make_b003_wide_micro_payload(
                        target_hierarchy.flatten());
                const auto target_quant =
                    lane_b::make_b003_quantized_micro_payload(
                        target_wide);
                node_capacity = std::max(
                    node_capacity,
                    VkDeviceSize(
                        target_quant.nodes.size() *
                        sizeof(lane_b::B003GpuQuantNode)));
                order_capacity = std::max(
                    order_capacity,
                    VkDeviceSize(
                        target_quant.ordered_primitives.size() *
                        sizeof(std::uint32_t)));
                hash_capacity = std::max(
                    hash_capacity,
                    VkDeviceSize(
                        target_quant.hash_table.size() *
                        sizeof(lane_b::GpuSegmentHashEntry)));
            }

            const auto upload_with_capacity =
                [&](B002Buffer& destination,
                    const void* data,
                    VkDeviceSize logical_bytes,
                    VkDeviceSize capacity_bytes) {
                    destination = context.create_device_buffer(
                        capacity_bytes,
                        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
                    const lane_b::B002BufferUpdate update{
                        0U,
                        data,
                        logical_bytes,
                    };
                    context.update_device_buffer(
                        destination,
                        std::span<const lane_b::B002BufferUpdate>(
                            &update,
                            1));
                };
            upload_with_capacity(
                quant_nodes,
                quant_payload.nodes.data(),
                VkDeviceSize(
                    quant_payload.nodes.size() *
                    sizeof(lane_b::B003GpuQuantNode)),
                node_capacity);
            upload_with_capacity(
                quant_order,
                quant_payload.ordered_primitives.data(),
                VkDeviceSize(
                    quant_payload.ordered_primitives.size() *
                    sizeof(std::uint32_t)),
                order_capacity);
            upload_with_capacity(
                quant_hash,
                quant_payload.hash_table.data(),
                VkDeviceSize(
                    quant_payload.hash_table.size() *
                    sizeof(lane_b::GpuSegmentHashEntry)),
                hash_capacity);
        } else {
            software_cpu = std::make_unique<GpuSoftwareBvhData>(b_scene.triangles);
            const auto nodes = software_cpu->gpu_nodes();
            software_nodes = context.upload_device_buffer(
                nodes.data(),
                nodes.size() * sizeof(lane_b::GpuBvhNode),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            software_order = context.upload_device_buffer(
                software_cpu->ordered_primitives().data(),
                software_cpu->ordered_primitives().size() * sizeof(std::uint32_t),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        }
    }

    void create_stages() {
        const std::array<I001Binding, 3> depth_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &surfaces},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &depth},
            {9, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
        }};
        depth_stage = std::make_unique<I001ComputeStage>(
            context, shader_path(PHOS_GI_LANE_A_SHADER_DIR, "lane_a_visibility_depth.spv"), depth_bindings);

        const std::array<I001Binding, 4> owner_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &surfaces},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &depth},
            {8, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &owners},
            {9, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
        }};
        owner_stage = std::make_unique<I001ComputeStage>(
            context, shader_path(PHOS_GI_LANE_A_SHADER_DIR, "lane_a_visibility_owner.spv"), owner_bindings);

        const std::array<I001Binding, 6> producer_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &surfaces},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &depth},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &work},
            {8, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &owners},
            {9, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
        }};
        producer_stage = std::make_unique<I001ComputeStage>(
            context,
            shader_path(
                uses_bounded(options.variant)
                    ? PHOS_GI_INTEGRATION_SHADER_DIR
                    : PHOS_GI_LANE_A_SHADER_DIR,
                uses_bounded(options.variant)
                    ? "i001_bounded_producer.spv"
                    : "lane_a_producer.spv"),
            producer_bindings);

        const std::array<I001Binding, 2> clamp_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            {1, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
        }};
        clamp_stage = std::make_unique<I001ComputeStage>(
            context, shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_clamp_counters.spv"), clamp_bindings);

        const std::array<I001Binding, 2> finalize_bindings{{
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            {7, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &indirect},
        }};
        finalize_stage = std::make_unique<I001ComputeStage>(
            context, shader_path(PHOS_GI_LANE_A_SHADER_DIR, "lane_a_finalize.spv"), finalize_bindings);

        const std::array<I001Binding, 3> ray_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &work},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &rays},
        }};
        ray_stage = std::make_unique<I001ComputeStage>(
            context, shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_work_to_rays.spv"), ray_bindings);

        create_traversal_stage();

        const std::array<I001Binding, 5> radiance_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &work},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &hits},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &contributions},
            {4, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
        }};
        radiance_stage = std::make_unique<I001ComputeStage>(
            context, shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_radiance.spv"), radiance_bindings);

        const std::array<I001Binding, 3> merge_bindings{{
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &contributions},
            {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &accum},
        }};
        merge_stage = std::make_unique<I001ComputeStage>(
            context, shader_path(PHOS_GI_LANE_A_SHADER_DIR, "lane_a_merge.spv"), merge_bindings);

        const std::array<I001Binding, 5> storage_update_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &work},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &accum},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &storage_slots},
            {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &storage_stats},
        }};
        storage_update_stage = std::make_unique<I001ComputeStage>(
            context, shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_storage_update.spv"),
            storage_update_bindings, sizeof(StoragePush));

        const std::array<I001Binding, 2> invalidation_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &storage_slots},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &storage_stats},
        }};
        invalidation_stage = std::make_unique<I001ComputeStage>(
            context, shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_storage_invalidate.spv"),
            invalidation_bindings, sizeof(InvalidationPush));

        const std::array<I001Binding, 4> resolve_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &work},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &storage_slots},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &resolved},
        }};
        resolve_stage = std::make_unique<I001ComputeStage>(
            context, shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_storage_resolve.spv"),
            resolve_bindings, sizeof(StoragePush));
    }

    void create_traversal_stage() {
        if (uses_hwrt(options.variant)) {
            const std::array<I001Binding, 5> bindings{{
                {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &rays},
                {1, VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR, nullptr, hwrt->top_level()},
                {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &hwrt->triangle_buffer()},
                {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &hits},
                {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            }};
            traversal_stage = std::make_unique<I001ComputeStage>(
                context, shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_hwrt.spv"),
                bindings, sizeof(std::uint32_t));
        } else if (uses_rigid_instance_software(options.variant)) {
            const std::array<I001Binding, 8> bindings{{
                {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &rays},
                {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &triangle_buffer},
                {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &instance_nodes},
                {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &instance_order},
                {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &instance_hash},
                {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &instance_table},
                {6, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &hits},
                {7, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            }};
            traversal_stage = std::make_unique<I001ComputeStage>(
                context,
                shader_path(
                    PHOS_GI_INTEGRATION_SHADER_DIR,
                    uses_rigid_instance_software_binary(options.variant)
                        ? "e003_instance_binary.spv"
                        : "e003_instance_quantized.spv"),
                bindings,
                sizeof(lane_e::E003TraversalPush));
        } else if (uses_quantized(options.variant)) {
            const std::array<I001Binding, 7> bindings{{
                {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &rays},
                {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &triangle_buffer},
                {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &quant_nodes},
                {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &quant_order},
                {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &quant_hash},
                {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &hits},
                {6, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            }};
            traversal_stage = std::make_unique<I001ComputeStage>(
                context, shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_quantized_bvh8.spv"),
                bindings, sizeof(HierarchicalTraversalPush));
        } else {
            const std::array<I001Binding, 6> bindings{{
                {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &rays},
                {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &triangle_buffer},
                {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &software_nodes},
                {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &software_order},
                {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &hits},
                {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            }};
            traversal_stage = std::make_unique<I001ComputeStage>(
                context, shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_software_bvh.spv"),
                bindings, sizeof(SoftwareTraversalPush));
        }
    }

    void create_command_resources() {
        auto pool_info = detail::make_vk_info<VkCommandPoolCreateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
        pool_info.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        pool_info.queueFamilyIndex = context.queue_family();
        if (context.vk().createCommandPool(&pool_info, nullptr, &command_pool) != VK_SUCCESS) {
            fail("I001 command pool");
        }

        auto query_info = detail::make_vk_info<VkQueryPoolCreateInfo>(
            VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
        query_info.queryType = VK_QUERY_TYPE_TIMESTAMP;
        query_info.queryCount = kQueryCount;
        if (context.vk().createQueryPool(&query_info, nullptr, &query_pool) != VK_SUCCESS) {
            fail("I001 query pool");
        }

        auto fence_info = detail::make_vk_info<VkFenceCreateInfo>(
            VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
        if (context.vk().createFence(&fence_info, nullptr, &fence) != VK_SUCCESS) {
            fail("I001 fence");
        }
    }

    void calculate_memory() {
        memory_stats = {};
        const auto allocation = [](const B002Buffer& buffer) {
            return static_cast<std::size_t>(buffer.allocation_size);
        };
        memory_stats.persistent_bytes =
            allocation(surfaces) + allocation(uniform) + allocation(storage_slots);

        if (uses_hwrt(options.variant)) {
            memory_stats.persistent_bytes += hwrt->setup_stats().persistent_bytes;
            memory_stats.scratch_bytes = hwrt->setup_stats().scratch_bytes;
        } else {
            memory_stats.persistent_bytes += allocation(triangle_buffer);
            if (uses_rigid_instance_software(options.variant)) {
                memory_stats.persistent_bytes +=
                    allocation(instance_nodes) +
                    allocation(instance_order) +
                    allocation(instance_hash) +
                    allocation(instance_table);
            } else if (uses_quantized(options.variant)) {
                memory_stats.persistent_bytes +=
                    allocation(quant_nodes) + allocation(quant_order) + allocation(quant_hash);
            } else {
                memory_stats.persistent_bytes += allocation(software_nodes) + allocation(software_order);
            }
        }

        memory_stats.transient_bytes =
            allocation(depth) + allocation(owners) + allocation(counters) + allocation(work) +
            allocation(indirect) + allocation(rays) + allocation(hits) + allocation(contributions) +
            allocation(accum) + allocation(resolved) + allocation(storage_stats);
        memory_stats.stream_capacity_bytes =
            allocation(work) +
            allocation(rays) +
            allocation(hits) +
            allocation(contributions) +
            allocation(accum) +
            allocation(resolved);
        memory_stats.storage_capacity_bytes = allocation(storage_slots);
        memory_stats.peak_resident_bytes =
            memory_stats.persistent_bytes + memory_stats.transient_bytes + memory_stats.scratch_bytes;
    }

    struct BufferWriteStats {
        bool rebound{};
        double gpu_us{};
    };

    [[nodiscard]] BufferWriteStats write_storage_buffer(
        B002Buffer& buffer,
        const void* data,
        VkDeviceSize size) {
        if (data == nullptr || size == 0U) {
            fail("I001 cannot write an empty traversal buffer");
        }
        if (buffer.size >= size) {
            const lane_b::B002BufferUpdate update{
                0U,
                data,
                size,
            };
            const auto gpu_us =
                context.update_device_buffer_timed(
                    buffer,
                    std::span<const lane_b::B002BufferUpdate>(&update, 1));
            return {false, gpu_us};
        }
        context.replace_device_buffer(
            buffer,
            data,
            size,
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        return {true, 0.0};
    }

    struct DynamicUpdateStats {
        double wall_us{};
        double gpu_us{};
        double geometry_prepare_cpu_us{};
        double surface_update_gpu_us{};
        double geometry_transfer_wall_us{};
        double geometry_transfer_gpu_us{};
        double instance_transfer_wall_us{};
        double instance_transfer_gpu_us{};
        double blas_update_us{};
        double tlas_update_us{};
        double membership_update_cpu_us{};
        double hierarchy_refit_cpu_us{};
        double hierarchy_rebuild_cpu_us{};
        double hierarchy_occupancy_cpu_us{};
        double packing_cpu_us{};
        double hierarchy_upload_gpu_us{};
        double software_bvh_rebuild_cpu_us{};
        std::uint32_t refit_segments{};
        std::uint32_t rebuilt_segments{};
    };

    [[nodiscard]] DynamicUpdateStats update_dynamic_geometry(bool target_state) {
        const bool dynamic_scenario =
            options.scenario == I001Scenario::MovingRigid ||
            options.scenario == I001Scenario::DeformingControl;
        if (!dynamic_scenario || !target_state || geometry_is_target) {
            return {};
        }

        using Clock = std::chrono::steady_clock;
        const auto elapsed_us = [](Clock::time_point start) {
            return std::chrono::duration<double, std::micro>(
                Clock::now() - start).count();
        };
        const auto start = Clock::now();
        DynamicUpdateStats out{};

        const bool rigid_instance_candidate =
            uses_rigid_instance_hwrt(options.variant) ||
            uses_rigid_instance_software(options.variant);
        auto phase_start = Clock::now();
        if (!rigid_instance_candidate) {
            auto target_geometry =
                options.scenario == I001Scenario::MovingRigid
                ? translated_geometry(
                    b_scene.triangles,
                    moving.primitives,
                    moving.delta_x)
                : deformed_geometry(
                    b_scene.triangles,
                    moving.primitives,
                    moving.delta_x);
            out.geometry_prepare_cpu_us = elapsed_us(phase_start);
            b_scene.triangles = std::move(target_geometry);
        } else if (options.scenario != I001Scenario::MovingRigid) {
            fail("I001 rigid-instance update reached a non-rigid scenario");
        }

        std::vector<std::array<float, 4>> moved_positions;
        moved_positions.reserve(moving.primitives.size());
        for (const auto primitive : moving.primitives) {
            if (options.scenario == I001Scenario::MovingRigid) {
                std::array<float, 4> position{};
                std::copy_n(
                    a_scene.samples.at(primitive).position,
                    4,
                    position.data());
                position[0] += moving.delta_x;
                moved_positions.push_back(position);
            } else {
                const auto& triangle = b_scene.triangles.at(primitive);
                moved_positions.push_back({
                    (triangle.v0.x + triangle.v1.x + triangle.v2.x) / 3.0F,
                    (triangle.v0.y + triangle.v1.y + triangle.v2.y) / 3.0F,
                    (triangle.v0.z + triangle.v1.z + triangle.v2.z) / 3.0F,
                    a_scene.samples.at(primitive).position[3],
                });
            }
        }
        std::vector<lane_b::B002BufferUpdate> surface_updates;
        surface_updates.reserve(moving.primitives.size());
        for (std::size_t index = 0;
             index < moving.primitives.size();
             ++index) {
            surface_updates.push_back({
                VkDeviceSize(moving.primitives[index]) *
                    VkDeviceSize(sizeof(std::array<float, 4>)),
                moved_positions[index].data(),
                VkDeviceSize(sizeof(std::array<float, 4>)),
            });
        }
        out.surface_update_gpu_us =
            context.update_device_buffer_timed(
                surfaces,
                surface_updates);
        out.gpu_us += out.surface_update_gpu_us;

        if (uses_hwrt(options.variant)) {
            if (rigid_instance_candidate) {
                const auto stats = hwrt->update_rigid_transform(
                    moving.delta_x,
                    rigid_tlas_policy(options.variant));
                out.instance_transfer_wall_us =
                    stats.instance_upload_us;
                out.instance_transfer_gpu_us =
                    stats.instance_upload_gpu_us;
                out.tlas_update_us = stats.tlas_update_us;
                out.gpu_us +=
                    out.instance_transfer_gpu_us +
                    out.tlas_update_us;
            } else {
                const auto stats = hwrt->update_geometry(
                    b_scene.triangles,
                    moving.primitives);
                out.geometry_transfer_wall_us =
                    stats.geometry_upload_us;
                out.geometry_transfer_gpu_us =
                    stats.geometry_upload_gpu_us;
                out.blas_update_us = stats.blas_update_us;
                out.tlas_update_us = stats.tlas_update_us;
                out.gpu_us +=
                    out.geometry_transfer_gpu_us +
                    out.blas_update_us +
                    out.tlas_update_us;
            }
        } else if (uses_rigid_instance_software(options.variant)) {
            const bool binary =
                uses_rigid_instance_software_binary(options.variant);
            const auto instance_index =
                binary
                ? instance_binary_payload.moving_instance_index
                : instance_quantized_payload.moving_instance_index;
            const auto& instances =
                binary
                ? instance_binary_payload.instances
                : instance_quantized_payload.instances;
            if (instance_index >= instances.size()) {
                fail("I001 E003 moving instance index is invalid");
            }
            auto moved_instance =
                lane_e::translated_instance(
                    instances[instance_index],
                    moving.delta_x);
            const lane_b::B002BufferUpdate update{
                VkDeviceSize(instance_index) *
                    VkDeviceSize(sizeof(lane_e::E003GpuInstance)),
                &moved_instance,
                VkDeviceSize(sizeof(lane_e::E003GpuInstance)),
            };
            phase_start = Clock::now();
            out.instance_transfer_gpu_us =
                context.update_device_buffer_timed(
                    instance_table,
                    std::span<const lane_b::B002BufferUpdate>(
                        &update,
                        1));
            out.instance_transfer_wall_us =
                elapsed_us(phase_start);
            out.gpu_us +=
                out.instance_transfer_gpu_us;
        } else {
            std::vector<GpuTriangle> moved_triangles;
            moved_triangles.reserve(moving.primitives.size());
            for (const auto primitive : moving.primitives) {
                moved_triangles.push_back(
                    lane_b::to_gpu_triangle(
                        b_scene.triangles.at(primitive)));
            }
            std::vector<lane_b::B002BufferUpdate> triangle_updates;
            triangle_updates.reserve(moving.primitives.size());
            for (std::size_t index = 0;
                 index < moving.primitives.size();
                 ++index) {
                triangle_updates.push_back({
                    VkDeviceSize(moving.primitives[index]) *
                        VkDeviceSize(sizeof(GpuTriangle)),
                    &moved_triangles[index],
                    VkDeviceSize(sizeof(GpuTriangle)),
                });
            }
            phase_start = Clock::now();
            out.geometry_transfer_gpu_us =
                context.update_device_buffer_timed(
                    triangle_buffer,
                    triangle_updates);
            out.geometry_transfer_wall_us = elapsed_us(phase_start);
            out.gpu_us += out.geometry_transfer_gpu_us;

            if (uses_quantized(options.variant)) {
                const auto stats = hierarchy_cpu->update(
                    b_scene.triangles,
                    moving.primitives);
                out.membership_update_cpu_us = stats.membership_dirty_us;
                out.hierarchy_refit_cpu_us = stats.refit_us;
                out.hierarchy_rebuild_cpu_us = stats.rebuild_us;
                out.hierarchy_occupancy_cpu_us = stats.occupancy_us;
                out.refit_segments =
                    static_cast<std::uint32_t>(stats.refit_segments);
                out.rebuilt_segments =
                    static_cast<std::uint32_t>(stats.rebuilt_segments);
                if (options.scenario == I001Scenario::MovingRigid &&
                    stats.membership_changes == 0U) {
                    fail("I001 moving-rigid regime did not exercise hierarchy rebuild");
                }

                phase_start = Clock::now();
                auto wide = lane_b::make_b003_wide_micro_payload(
                    hierarchy_cpu->flatten());
                auto next_quant =
                    lane_b::make_b003_quantized_micro_payload(wide);
                out.packing_cpu_us = elapsed_us(phase_start);

                const auto node_bytes = VkDeviceSize(
                    next_quant.nodes.size() *
                    sizeof(lane_b::B003GpuQuantNode));
                const auto order_bytes = VkDeviceSize(
                    next_quant.ordered_primitives.size() *
                    sizeof(std::uint32_t));
                const auto hash_bytes = VkDeviceSize(
                    next_quant.hash_table.size() *
                    sizeof(lane_b::GpuSegmentHashEntry));
                const bool rebind =
                    quant_nodes.size < node_bytes ||
                    quant_order.size < order_bytes ||
                    quant_hash.size < hash_bytes;
                if (rebind) {
                    traversal_stage.reset();
                }
                const auto node_write = write_storage_buffer(
                    quant_nodes,
                    next_quant.nodes.data(),
                    node_bytes);
                const auto order_write = write_storage_buffer(
                    quant_order,
                    next_quant.ordered_primitives.data(),
                    order_bytes);
                const auto hash_write = write_storage_buffer(
                    quant_hash,
                    next_quant.hash_table.data(),
                    hash_bytes);
                out.hierarchy_upload_gpu_us =
                    node_write.gpu_us +
                    order_write.gpu_us +
                    hash_write.gpu_us;
                out.gpu_us += out.hierarchy_upload_gpu_us;
                quant_payload = std::move(next_quant);
                if (rebind) {
                    create_traversal_stage();
                }
            } else {
                phase_start = Clock::now();
                software_cpu->rebuild(b_scene.triangles);
                out.software_bvh_rebuild_cpu_us = elapsed_us(phase_start);
                const auto next_nodes = software_cpu->gpu_nodes();
                const auto& next_order =
                    software_cpu->ordered_primitives();
                const auto node_bytes = VkDeviceSize(
                    next_nodes.size() *
                    sizeof(lane_b::GpuBvhNode));
                const auto order_bytes = VkDeviceSize(
                    next_order.size() *
                    sizeof(std::uint32_t));
                const bool rebind =
                    software_nodes.size < node_bytes ||
                    software_order.size < order_bytes;
                if (rebind) {
                    traversal_stage.reset();
                }
                const auto node_write = write_storage_buffer(
                    software_nodes,
                    next_nodes.data(),
                    node_bytes);
                const auto order_write = write_storage_buffer(
                    software_order,
                    next_order.data(),
                    order_bytes);
                out.hierarchy_upload_gpu_us =
                    node_write.gpu_us +
                    order_write.gpu_us;
                out.gpu_us += out.hierarchy_upload_gpu_us;
                if (rebind) {
                    create_traversal_stage();
                }
            }
            calculate_memory();
        }

        if (options.scenario == I001Scenario::MovingRigid) {
            for (const auto primitive : moving.primitives) {
                a_scene.samples.at(primitive).position[0] += moving.delta_x;
            }
        } else {
            sync_surface_positions(
                a_scene,
                b_scene.triangles,
                moving.primitives);
        }
        geometry_is_target = true;
        out.wall_us = elapsed_us(start);

        // The rigid-instance candidate does not mutate traversal geometry.
        // Keep the translated CPU scene only as an out-of-band correctness
        // reference after the measured maintenance boundary has closed.
        if (rigid_instance_candidate) {
            b_scene.triangles = translated_geometry(
                b_scene.triangles,
                moving.primitives,
                moving.delta_x);
        }
        return out;
    }

    void update_params(bool target_state) {
        settings.case_id = a001_case(options.scenario, target_state);
        settings.frame_id = frame_id;
        auto next = lane_a::build_a001_params(a_scene, settings);
        next.limits[1] = params.limits[1];
        next.limits[2] = params.limits[2];
        params = next;
        std::memcpy(uniform.mapped, &params, sizeof(params));
    }

    [[nodiscard]] HierarchicalTraversalPush quant_push() const {
        HierarchicalTraversalPush push{};
        push.values[0] = params.limits[1];
        push.values[1] = quant_payload.hash_mask;
        push.values[2] = quant_payload.hash_max_probe;
        const auto max_steps = std::max<std::uint64_t>(
            64U, std::uint64_t(quant_payload.segment_count) * 16U + 64U);
        push.values[3] = static_cast<std::uint32_t>(
            std::min<std::uint64_t>(max_steps, std::numeric_limits<std::uint32_t>::max()));
        push.occupied_min_segment_size[0] = quant_payload.occupied_bounds.min.x;
        push.occupied_min_segment_size[1] = quant_payload.occupied_bounds.min.y;
        push.occupied_min_segment_size[2] = quant_payload.occupied_bounds.min.z;
        push.occupied_min_segment_size[3] = lane_b::b002_segment_size(b_scene);
        push.occupied_max_pad[0] = quant_payload.occupied_bounds.max.x;
        push.occupied_max_pad[1] = quant_payload.occupied_bounds.max.y;
        push.occupied_max_pad[2] = quant_payload.occupied_bounds.max.z;
        return push;
    }

    void record_candidate_traversal(VkCommandBuffer command) {
        if (uses_hwrt(options.variant)) {
            const auto max_rays = params.limits[1];
            traversal_stage->record_indirect(
                command, indirect.buffer, 0, &max_rays, sizeof(max_rays));
        } else if (uses_rigid_instance_software(options.variant)) {
            lane_e::E003TraversalPush push{};
            push.values[0] = params.limits[1];
            push.values[1] = static_cast<std::uint32_t>(
                uses_rigid_instance_software_binary(options.variant)
                    ? instance_binary_payload.instances.size()
                    : instance_quantized_payload.instances.size());
            traversal_stage->record_indirect(
                command, indirect.buffer, 0, &push, sizeof(push));
        } else if (uses_quantized(options.variant)) {
            const auto push = quant_push();
            traversal_stage->record_indirect(
                command, indirect.buffer, 0, &push, sizeof(push));
        } else {
            const SoftwareTraversalPush push{
                params.limits[1], software_cpu->root(), 0U, 0U};
            traversal_stage->record_indirect(
                command, indirect.buffer, 0, &push, sizeof(push));
        }
    }

    [[nodiscard]] I001FrameResult run_frame(bool target_state) {
        ++frame_id;
        const auto dynamic_update = update_dynamic_geometry(target_state);
        update_params(target_state);

        context.vk().resetFences(1, &fence);
        context.vk().resetCommandPool(command_pool, 0);

        VkCommandBuffer command{};
        auto allocation = detail::make_vk_info<VkCommandBufferAllocateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
        allocation.commandPool = command_pool;
        allocation.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        allocation.commandBufferCount = 1;
        if (context.vk().allocateCommandBuffers(&allocation, &command) != VK_SUCCESS) {
            fail("I001 command allocation");
        }

        auto begin = detail::make_vk_info<VkCommandBufferBeginInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
        begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        if (context.vk().beginCommandBuffer(command, &begin) != VK_SUCCESS) {
            fail("I001 command begin");
        }

        context.vk().cmdResetQueryPool(command, query_pool, 0, kQueryCount);
        auto stamp = [&](std::uint32_t index) {
            context.vk().cmdWriteTimestamp(
                command, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, query_pool, index);
        };

        stamp(0);
        context.vk().cmdFillBuffer(command, depth.buffer, 0, depth.size, 0x7f800000U);
        i001_transfer_to_compute_barrier(context, command);
        depth_stage->record(command, groups(params.counts[0]));
        i001_compute_barrier(context, command);
        stamp(1);

        context.vk().cmdFillBuffer(command, owners.buffer, 0, owners.size, 0xffffffffU);
        context.vk().cmdFillBuffer(command, counters.buffer, 0, counters.size, 0U);
        context.vk().cmdFillBuffer(command, accum.buffer, 0, accum.size, 0U);
        context.vk().cmdFillBuffer(command, resolved.buffer, 0, resolved.size, 0U);
        context.vk().cmdFillBuffer(command, storage_stats.buffer, 0, storage_stats.size, 0U);
        i001_transfer_to_compute_barrier(context, command);
        stamp(2);

        owner_stage->record(command, groups(params.counts[0]));
        i001_compute_barrier(context, command);
        stamp(3);

        producer_stage->record(command, groups(params.counts[0]));
        i001_compute_barrier(context, command);
        clamp_stage->record(command, 1);
        i001_compute_barrier(context, command);
        finalize_stage->record(command, 1);
        i001_compute_barrier(context, command);
        stamp(4);

        ray_stage->record_indirect(command, indirect.buffer, 0);
        i001_compute_barrier(context, command);
        stamp(5);

        if (uses_hwrt(options.variant)) {
            i001_acceleration_to_compute_barrier(context, command);
        }
        record_candidate_traversal(command);
        i001_compute_barrier(context, command);
        stamp(6);

        radiance_stage->record_indirect(command, indirect.buffer, 0);
        i001_compute_barrier(context, command);
        stamp(7);

        merge_stage->record_indirect(command, indirect.buffer, 0);
        i001_compute_barrier(context, command);
        stamp(8);

        const StoragePush storage_reserve_push{
            storage_capacity - 1U, kHashMaxProbe, frame_id, 0U};
        storage_update_stage->record_indirect(
            command,
            indirect.buffer,
            0,
            &storage_reserve_push,
            sizeof(storage_reserve_push));
        i001_compute_barrier(context, command);

        const StoragePush storage_accumulate_push{
            storage_capacity - 1U, kHashMaxProbe, frame_id, 1U};
        storage_update_stage->record_indirect(
            command,
            indirect.buffer,
            0,
            &storage_accumulate_push,
            sizeof(storage_accumulate_push));
        i001_compute_barrier(context, command);
        stamp(9);

        const InvalidationPush invalidation_push{
            storage_capacity, frame_id, 0U, 0U};
        invalidation_stage->record(
            command, groups(storage_capacity), 1, 1,
            &invalidation_push, sizeof(invalidation_push));
        i001_compute_barrier(context, command);
        stamp(10);

        const StoragePush storage_resolve_push{
            storage_capacity - 1U, kHashMaxProbe, frame_id, 0U};
        resolve_stage->record_indirect(
            command,
            indirect.buffer,
            0,
            &storage_resolve_push,
            sizeof(storage_resolve_push));
        i001_compute_barrier(context, command);
        stamp(11);

        if (context.vk().endCommandBuffer(command) != VK_SUCCESS) {
            fail("I001 command end");
        }
        auto submit = detail::make_vk_info<VkSubmitInfo>(
            VK_STRUCTURE_TYPE_SUBMIT_INFO);
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command;
        if (context.vk().queueSubmit(context.queue(), 1, &submit, fence) != VK_SUCCESS) {
            fail("I001 submit");
        }
        if (context.vk().waitForFences(1, &fence, VK_TRUE, UINT64_MAX) != VK_SUCCESS) {
            fail("I001 fence wait");
        }

        std::array<std::uint64_t, 12> timestamps{};
        if (context.vk().getQueryPoolResults(
                query_pool, 0, static_cast<std::uint32_t>(timestamps.size()),
                sizeof(timestamps), timestamps.data(), sizeof(std::uint64_t),
                VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
            fail("I001 timestamp readback");
        }

        std::array<std::uint32_t, 6> counter_values{};
        context.download_device_buffer(counters, counter_values.data(), sizeof(counter_values));
        std::array<std::uint32_t, 4> storage_values{};
        context.download_device_buffer(storage_stats, storage_values.data(), sizeof(storage_values));

        I001FrameResult result{};
        const auto period = context.timestamp_period_ns();
        result.timings.renderer_depth_us = timestamp_us(timestamps[0], timestamps[1], period);
        result.timings.frame_init_us = timestamp_us(timestamps[1], timestamps[2], period);
        result.timings.visibility_reuse_us = timestamp_us(timestamps[2], timestamps[3], period);
        result.timings.producer_us = timestamp_us(timestamps[3], timestamps[4], period);
        result.timings.ray_prepare_us = timestamp_us(timestamps[4], timestamps[5], period);
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
        result.timings.packing_cpu_us =
            dynamic_update.packing_cpu_us;
        result.timings.hierarchy_upload_gpu_us =
            dynamic_update.hierarchy_upload_gpu_us;
        result.timings.software_bvh_rebuild_cpu_us =
            dynamic_update.software_bvh_rebuild_cpu_us;
        result.timings.traversal_us = timestamp_us(timestamps[5], timestamps[6], period);
        result.timings.radiance_us = timestamp_us(timestamps[6], timestamps[7], period);
        result.timings.merge_us = timestamp_us(timestamps[7], timestamps[8], period);
        result.timings.storage_update_us = timestamp_us(timestamps[8], timestamps[9], period);
        result.timings.invalidation_us = timestamp_us(timestamps[9], timestamps[10], period);
        result.timings.resolve_us = timestamp_us(timestamps[10], timestamps[11], period);
        result.timings.complete_gpu_us =
            timestamp_us(timestamps[0], timestamps[11], period) +
            dynamic_update.gpu_us;
        result.timings.incremental_gi_us =
            (options.variant == I001Variant::DepthReuseHwrt
             ? timestamp_us(timestamps[1], timestamps[11], period)
             : timestamp_us(timestamps[0], timestamps[11], period)) +
            dynamic_update.gpu_us;

        result.stats.work_items = counter_values[0];
        result.stats.outputs = counter_values[1];
        result.stats.overflow = counter_values[2];
        result.stats.visible_owners = counter_values[3];
        if ((options.scenario == I001Scenario::MovingRigid ||
             options.scenario == I001Scenario::DeformingControl) &&
            target_state) {
            result.stats.moved_primitives =
                static_cast<std::uint32_t>(moving.primitives.size());
            result.stats.segment_membership_changes =
                moving.membership_changes;
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
        result.memory = memory_stats;

        last = result;
        have_last = true;
        return result;
    }

    [[nodiscard]] I001Quality validate_last_frame() {
        if (!have_last) fail("I001 quality requested before a frame");
        const auto work_count = last.stats.work_items;
        if (work_count == 0U) fail("I001 produced zero work items");

        GpuSoftwareBvhData reference_cpu(b_scene.triangles);
        const auto reference_nodes = reference_cpu.gpu_nodes();
        const auto triangles = gpu_triangles(b_scene);
        auto triangle = context.upload_device_buffer(
            triangles.data(), triangles.size() * sizeof(GpuTriangle),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        auto nodes = context.upload_device_buffer(
            reference_nodes.data(), reference_nodes.size() * sizeof(lane_b::GpuBvhNode),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        auto ordered = context.upload_device_buffer(
            reference_cpu.ordered_primitives().data(),
            reference_cpu.ordered_primitives().size() * sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        auto reference_hits = context.create_device_buffer(
            VkDeviceSize(params.limits[1]) * sizeof(GpuHit),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        auto reference_contributions = context.create_device_buffer(
            VkDeviceSize(params.limits[1]) * sizeof(std::uint32_t) * 2U,
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        auto reference_accum = context.create_device_buffer(
            VkDeviceSize(params.limits[2]) * sizeof(std::uint32_t) * 2U,
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

        const std::array<I001Binding, 5> bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &rays},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &triangle},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &nodes},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &ordered},
            {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &reference_hits},
        }};
        I001ComputeStage reference_stage(
            context, shader_path(PHOS_GI_LANE_B_SHADER_DIR, "lane_b_b002_software_bvh.spv"),
            bindings, sizeof(SoftwareTraversalPush));

        const std::array<I001Binding, 5> reference_radiance_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &work},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &reference_hits},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &reference_contributions},
            {4, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
        }};
        I001ComputeStage reference_radiance_stage(
            context,
            shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_radiance.spv"),
            reference_radiance_bindings);

        const std::array<I001Binding, 3> reference_merge_bindings{{
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &counters},
            {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &reference_contributions},
            {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &reference_accum},
        }};
        I001ComputeStage reference_merge_stage(
            context,
            shader_path(PHOS_GI_LANE_A_SHADER_DIR, "lane_a_merge.spv"),
            reference_merge_bindings);

        context.vk().resetFences(1, &fence);
        context.vk().resetCommandPool(command_pool, 0);
        VkCommandBuffer command{};
        auto allocation = detail::make_vk_info<VkCommandBufferAllocateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
        allocation.commandPool = command_pool;
        allocation.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        allocation.commandBufferCount = 1;
        if (context.vk().allocateCommandBuffers(&allocation, &command) != VK_SUCCESS) {
            fail("I001 reference command allocation");
        }
        auto begin = detail::make_vk_info<VkCommandBufferBeginInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
        begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        if (context.vk().beginCommandBuffer(command, &begin) != VK_SUCCESS) {
            fail("I001 reference command begin");
        }
        context.vk().cmdFillBuffer(
            command,
            reference_accum.buffer,
            0,
            reference_accum.size,
            0U);
        i001_transfer_to_compute_barrier(context, command);

        const SoftwareTraversalPush push{
            work_count, reference_cpu.root(), 0U, 0U};
        reference_stage.record(
            command, groups(work_count), 1, 1, &push, sizeof(push));
        i001_compute_barrier(context, command);
        reference_radiance_stage.record(
            command, groups(work_count));
        i001_compute_barrier(context, command);
        reference_merge_stage.record(
            command, groups(work_count));
        i001_compute_barrier(context, command);
        if (context.vk().endCommandBuffer(command) != VK_SUCCESS) {
            fail("I001 reference command end");
        }
        auto submit = detail::make_vk_info<VkSubmitInfo>(
            VK_STRUCTURE_TYPE_SUBMIT_INFO);
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command;
        if (context.vk().queueSubmit(context.queue(), 1, &submit, fence) != VK_SUCCESS ||
            context.vk().waitForFences(1, &fence, VK_TRUE, UINT64_MAX) != VK_SUCCESS) {
            fail("I001 reference submission");
        }

        std::vector<GpuHit> candidate(work_count);
        std::vector<GpuHit> reference(work_count);
        context.download_device_buffer(hits, candidate.data(), candidate.size() * sizeof(GpuHit));
        context.download_device_buffer(reference_hits, reference.data(), reference.size() * sizeof(GpuHit));

        I001Quality quality{};
        for (std::size_t index = 0; index < candidate.size(); ++index) {
            if (candidate[index].metadata[3] > 1U) {
                ++quality.traversal_runtime_errors;
            }
            if (!lane_b::equivalent_hit(
                    lane_b::from_gpu_hit(reference[index]),
                    lane_b::from_gpu_hit(candidate[index]))) {
                ++quality.hit_mismatches;
            }
        }

        std::vector<LaneAWorkItemV1> work_items(work_count);
        context.download_device_buffer(
            work, work_items.data(), work_items.size() * sizeof(LaneAWorkItemV1));

        const auto tile_count = params.counts[1] * params.counts[2];
        std::vector<std::uint32_t> tile_owners(tile_count);
        context.download_device_buffer(
            owners,
            tile_owners.data(),
            tile_owners.size() * sizeof(std::uint32_t));

        lane_a::A001Readback producer_readback{};
        producer_readback.counters = {
            last.stats.work_items,
            last.stats.outputs,
            last.stats.overflow,
            last.stats.visible_owners,
        };
        producer_readback.tile_owner = tile_owners;
        producer_readback.work_items.resize(work_items.size());
        static_assert(
            sizeof(lane_a::SplitRcWorkItemV1) == sizeof(LaneAWorkItemV1));
        static_assert(
            std::is_trivially_copyable_v<lane_a::SplitRcWorkItemV1>);
        static_assert(std::is_trivially_copyable_v<LaneAWorkItemV1>);
        std::transform(
            work_items.begin(),
            work_items.end(),
            producer_readback.work_items.begin(),
            [](const LaneAWorkItemV1& item) {
                return std::bit_cast<lane_a::SplitRcWorkItemV1>(item);
            });
        producer_readback.resolved.assign(last.stats.outputs, 0.0F);

        const auto producer_analysis = lane_a::analyze_a001(
            a_scene,
            settings,
            params,
            producer_readback);
        if (!producer_analysis.visibility_correct) {
            ++quality.visibility_mismatches;
        }

        if (last.stats.overflow == 0U) {
            if (!producer_analysis.producer_correct) {
                ++quality.producer_semantic_errors;
            }
        } else {
            const auto block =
                settings.cascade_count * settings.rays_per_probe;
            const auto expected_requested_work =
                std::uint64_t(last.stats.visible_owners) * block;
            const auto expected_requested_outputs =
                std::uint64_t(last.stats.visible_owners) *
                settings.cascade_count;
            bool bounded_ok =
                last.stats.requested_work_items ==
                    expected_requested_work &&
                last.stats.requested_outputs ==
                    expected_requested_outputs &&
                last.stats.requested_work_items >
                    last.stats.work_items &&
                last.stats.requested_outputs >
                    last.stats.outputs &&
                last.stats.work_items == params.limits[1] &&
                last.stats.outputs == params.limits[2] &&
                block != 0U &&
                work_items.size() % block == 0U;

            std::vector<bool> seen_tile(
                tile_owners.size(),
                false);
            for (std::size_t base = 0;
                 bounded_ok && base + block <= work_items.size();
                 base += block) {
                const auto& first = work_items[base];
                const auto owner_index =
                    base / block;
                const auto expected_output_base =
                    owner_index * settings.cascade_count;
                if (first.tile_id >= tile_owners.size() ||
                    first.surface_id >= a_scene.samples.size() ||
                    tile_owners[first.tile_id] != first.surface_id ||
                    seen_tile[first.tile_id] ||
                    first.output_id != expected_output_base ||
                    first.output_id + settings.cascade_count >
                        last.stats.outputs) {
                    bounded_ok = false;
                    break;
                }
                seen_tile[first.tile_id] = true;

                const auto& sample =
                    a_scene.samples[first.surface_id];
                const lane_b::Vec3 position{
                    sample.position[0],
                    sample.position[1],
                    sample.position[2],
                };
                const lane_b::Vec3 origin{
                    params.scene_origin_spacing[0],
                    params.scene_origin_spacing[1],
                    params.scene_origin_spacing[2],
                };

                for (std::uint32_t cascade = 0U;
                     cascade < settings.cascade_count && bounded_ok;
                     ++cascade) {
                    const auto spacing =
                        params.scene_origin_spacing[3] *
                        float(1U << cascade);
                    const auto probe_x =
                        static_cast<std::int32_t>(
                            std::floor(
                                (position.x - origin.x) /
                                spacing));
                    const auto probe_y =
                        static_cast<std::int32_t>(
                            std::floor(
                                (position.y - origin.y) /
                                spacing));
                    const auto probe_z =
                        static_cast<std::int32_t>(
                            std::floor(
                                (position.z - origin.z) /
                                spacing));
                    const auto probe_px =
                        std::fma(
                            float(probe_x) + 0.5F,
                            spacing,
                            origin.x);
                    const auto probe_py =
                        std::fma(
                            float(probe_y) + 0.5F,
                            spacing,
                            origin.y);
                    const auto probe_pz =
                        std::fma(
                            float(probe_z) + 0.5F,
                            spacing,
                            origin.z);
                    const auto interval_max =
                        params.light_pos_interval[3] *
                        float(1U << cascade);
                    const auto interval_min =
                        cascade == 0U
                        ? 0.0F
                        : params.light_pos_interval[3] *
                            float(1U << (cascade - 1U));

                    for (std::uint32_t ray = 0U;
                         ray < settings.rays_per_probe;
                         ++ray) {
                        const auto& item =
                            work_items[
                                base +
                                cascade * settings.rays_per_probe +
                                ray];
                        const auto direction =
                            i001_ray_direction(ray);
                        if (item.surface_id != first.surface_id ||
                            item.tile_id != first.tile_id ||
                            item.cascade != cascade ||
                            item.ray_index != ray ||
                            item.output_id !=
                                first.output_id + cascade ||
                            item.probe_x != probe_x ||
                            item.probe_y != probe_y ||
                            item.probe_z != probe_z ||
                            std::abs(
                                item.interval_min -
                                interval_min) >= 1.0e-5F ||
                            std::abs(
                                item.interval_max -
                                interval_max) >= 1.0e-5F ||
                            std::abs(
                                item.dir_x -
                                direction.x) >= 1.0e-6F ||
                            std::abs(
                                item.dir_y -
                                direction.y) >= 1.0e-6F ||
                            std::abs(
                                item.dir_z -
                                direction.z) >= 1.0e-6F ||
                            !within_float_ulps(
                                item.probe_px,
                                probe_px,
                                2) ||
                            !within_float_ulps(
                                item.probe_py,
                                probe_py,
                                2) ||
                            !within_float_ulps(
                                item.probe_pz,
                                probe_pz,
                                2)) {
                            bounded_ok = false;
                            break;
                        }
                    }
                }
            }
            if (!bounded_ok) {
                ++quality.producer_semantic_errors;
            }
        }

        std::vector<HashSlotCpu> candidate_slots(storage_capacity);
        context.download_device_buffer(
            storage_slots, candidate_slots.data(), candidate_slots.size() * sizeof(HashSlotCpu));

        std::vector<std::array<std::uint32_t, 2>> reference_accum_values(
            last.stats.outputs);
        context.download_device_buffer(
            reference_accum,
            reference_accum_values.data(),
            reference_accum_values.size() *
                sizeof(reference_accum_values[0]));

        std::map<ProbeKey, std::pair<std::uint64_t, std::uint32_t>> reference_probe;
        for (const auto& item : work_items) {
            if (item.ray_index != 0U ||
                item.output_id >= reference_accum_values.size()) {
                continue;
            }
            const auto merged = reference_accum_values[item.output_id];
            if (merged[1] == 0U) continue;
            const auto sample = static_cast<std::uint32_t>(
                (std::uint64_t(merged[0]) + merged[1] / 2U) /
                merged[1]);
            auto& probe = reference_probe[{
                item.probe_x, item.probe_y, item.probe_z, item.cascade}];
            probe.first += sample;
            ++probe.second;
        }

        std::map<ProbeKey, double> candidate_probe;
        for (const auto& slot : candidate_slots) {
            const bool occupied =
                slot.data[0] != 0U &&
                slot.data[0] != 0xffffffffU;
            if (occupied && slot.data[3] != frame_id) {
                ++quality.stale_storage_slots;
                continue;
            }
            if (!occupied || slot.data[3] != frame_id) continue;
            const auto key = slot_key(slot);
            if (probe_token(key) != slot.data[0] ||
                candidate_probe.contains(key)) {
                ++quality.leaked_probes;
                continue;
            }
            candidate_probe.emplace(key, slot_value(slot));
        }

        std::vector<float> candidate_resolved(last.stats.outputs);
        context.download_device_buffer(
            resolved,
            candidate_resolved.data(),
            candidate_resolved.size() * sizeof(float));

        std::map<ProbeKey, double> reference_values;
        for (const auto& [key, reference_accum] : reference_probe) {
            reference_values[key] =
                reference_accum.second == 0U
                ? 0.0
                : double(reference_accum.first) /
                    (double(reference_accum.second) * 65535.0);
        }

        double squared = 0.0;
        std::size_t compared = 0;
        for (const auto& [key, reference_accum] : reference_probe) {
            const double reference_value = reference_values.at(key);
            const auto found = candidate_probe.find(key);
            if (found == candidate_probe.end()) {
                ++quality.missing_probes;
                continue;
            }
            const auto error = std::abs(found->second - reference_value);
            quality.radiance_max_abs_error =
                std::max(quality.radiance_max_abs_error, error);
            squared += error * error;
            ++compared;
        }
        for (const auto& [key, value] : candidate_probe) {
            (void)value;
            if (!reference_probe.contains(key)) ++quality.leaked_probes;
        }

        for (const auto& item : work_items) {
            if (item.ray_index != 0U ||
                item.output_id >= candidate_resolved.size()) {
                continue;
            }
            const ProbeKey key{
                item.probe_x,
                item.probe_y,
                item.probe_z,
                item.cascade,
            };
            const auto found = reference_probe.find(key);
            if (found == reference_probe.end() || found->second.second == 0U) {
                ++quality.resolved_output_mismatches;
                continue;
            }
            const double expected =
                double(found->second.first) /
                (double(found->second.second) * 65535.0);
            const auto error =
                std::abs(double(candidate_resolved[item.output_id]) - expected);
            if (error > 1.0e-4) {
                ++quality.resolved_output_mismatches;
            }
            quality.radiance_max_abs_error =
                std::max(quality.radiance_max_abs_error, error);
            squared += error * error;
            ++compared;
        }

        quality.radiance_rms_error =
            compared == 0U
            ? std::numeric_limits<double>::infinity()
            : std::sqrt(squared / double(compared));

        if (have_quality_history) {
            std::map<ProbeKey, bool> temporal_keys;
            for (const auto& [key, value] : previous_reference_probe) {
                (void)value;
                temporal_keys[key] = true;
            }
            for (const auto& [key, value] : reference_values) {
                (void)value;
                temporal_keys[key] = true;
            }
            for (const auto& [key, value] : previous_candidate_probe) {
                (void)value;
                temporal_keys[key] = true;
            }
            for (const auto& [key, value] : candidate_probe) {
                (void)value;
                temporal_keys[key] = true;
            }

            double temporal_squared = 0.0;
            std::size_t temporal_count = 0U;
            const auto value_or_zero =
                [](const std::map<ProbeKey, double>& values,
                   const ProbeKey& key) {
                    const auto found = values.find(key);
                    return found == values.end() ? 0.0 : found->second;
                };
            for (const auto& [key, present] : temporal_keys) {
                (void)present;
                const auto reference_delta =
                    value_or_zero(reference_values, key) -
                    value_or_zero(previous_reference_probe, key);
                const auto candidate_delta =
                    value_or_zero(candidate_probe, key) -
                    value_or_zero(previous_candidate_probe, key);
                const auto error =
                    std::abs(candidate_delta - reference_delta);
                quality.temporal_max_abs_error =
                    std::max(quality.temporal_max_abs_error, error);
                temporal_squared += error * error;
                ++temporal_count;
            }
            quality.temporal_rms_error =
                temporal_count == 0U
                ? 0.0
                : std::sqrt(
                    temporal_squared / double(temporal_count));
        }

        quality.passed =
            quality.visibility_mismatches == 0U &&
            quality.producer_semantic_errors == 0U &&
            quality.hit_mismatches == 0U &&
            quality.traversal_runtime_errors == 0U &&
            quality.missing_probes == 0U &&
            quality.leaked_probes == 0U &&
            quality.stale_storage_slots == 0U &&
            quality.resolved_output_mismatches == 0U &&
            quality.radiance_max_abs_error <= 1.0e-4 &&
            quality.radiance_rms_error <= 1.0e-5 &&
            quality.temporal_max_abs_error <= 1.0e-4 &&
            quality.temporal_rms_error <= 1.0e-5 &&
            last.stats.storage_failures == 0U;

        previous_reference_probe = std::move(reference_values);
        previous_candidate_probe = candidate_probe;
        have_quality_history = true;

        context.destroy_buffer(reference_accum);
        context.destroy_buffer(reference_contributions);
        context.destroy_buffer(reference_hits);
        context.destroy_buffer(ordered);
        context.destroy_buffer(nodes);
        context.destroy_buffer(triangle);
        last.quality = quality;
        return quality;
    }
};

I001Runtime::I001Runtime(I001Options options)
    : impl_(std::make_unique<Impl>(std::move(options))) {}
I001Runtime::~I001Runtime() = default;

I001FrameResult I001Runtime::run_frame(bool target_state) {
    return impl_->run_frame(target_state);
}
I001Quality I001Runtime::validate_last_frame() {
    return impl_->validate_last_frame();
}
const I001Memory& I001Runtime::memory() const noexcept {
    return impl_->memory_stats;
}
const std::string& I001Runtime::device_name() const noexcept {
    return impl_->context.device_name();
}
const std::string& I001Runtime::driver_name() const noexcept {
    return impl_->context.driver_name();
}
const std::string& I001Runtime::driver_info() const noexcept {
    return impl_->context.driver_info();
}
std::uint32_t I001Runtime::api_version() const noexcept {
    return impl_->context.api_version();
}

} // namespace phos::gi::research::integration

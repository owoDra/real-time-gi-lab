#include "i001_runtime.hpp"

#include "i001_compute.hpp"

#include "../lane_a_split_rc/a001_runtime.hpp"
#include "../lane_a_split_rc/a001_scene.hpp"
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
#include "vk_init.hpp"

#include <algorithm>
#include <array>
#include <cmath>
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
    std::uint32_t reserved{};
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
           value == I001Variant::DepthReuseHwrt ||
           value == I001Variant::BoundedHwrt;
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
    const lane_b::B002Scene& scene) {
    std::vector<GpuTriangle> output;
    output.reserve(scene.triangles.size());
    for (const auto& triangle : scene.triangles) {
        output.push_back(lane_b::to_gpu_triangle(triangle));
    }
    return output;
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

[[nodiscard]] double slot_value(const HashSlotCpu& slot) noexcept {
    return slot.data[2] == 0U
        ? 0.0
        : double(slot.data[1]) /
              (double(slot.data[2]) * 65535.0);
}

} // namespace

const char* i001_variant_name(I001Variant value) noexcept {
    switch (value) {
    case I001Variant::VanillaSoftware: return "vanilla-software";
    case I001Variant::CombinedHwrt: return "combined-hwrt";
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
    }
    return "unknown";
}

I001Variant i001_parse_variant(const std::string& value) {
    if (value == "vanilla-software") return I001Variant::VanillaSoftware;
    if (value == "combined-hwrt") return I001Variant::CombinedHwrt;
    if (value == "combined-software") return I001Variant::CombinedSoftware;
    if (value == "depth-reuse-hwrt") return I001Variant::DepthReuseHwrt;
    if (value == "bounded-hwrt") return I001Variant::BoundedHwrt;
    throw std::runtime_error("unknown I001 variant: " + value);
}

I001Scenario i001_parse_scenario(const std::string& value) {
    if (value == "static") return I001Scenario::Static;
    if (value == "camera-motion") return I001Scenario::CameraMotion;
    if (value == "light-motion") return I001Scenario::LightMotion;
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

        settings.case_id = lane_a::A001Case::Static;
        settings.tile_width = 128;
        settings.tile_height = 72;
        settings.cascade_count = 4;
        settings.rays_per_probe = 8;
        params = lane_a::build_a001_params(a_scene, settings);

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

        storage_capacity = next_pow2(std::max(2U, params.limits[2] * 2U));
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
                 &owners, &depth, &surfaces, &quant_hash, &quant_order,
                 &quant_nodes, &software_order, &software_nodes, &triangle_buffer}) {
            context.destroy_buffer(*buffer);
        }
    }

    void prepare_candidate_traversal() {
        if (uses_hwrt(options.variant)) {
            hwrt = std::make_unique<B002HwrtTraversal>(
                context,
                b_scene.triangles,
                shader_path(PHOS_GI_LANE_B_SHADER_DIR, "lane_b_b002_hwrt.spv"));
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

            quant_nodes = context.upload_device_buffer(
                quant_payload.nodes.data(),
                quant_payload.nodes.size() * sizeof(lane_b::B003GpuQuantNode),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            quant_order = context.upload_device_buffer(
                quant_payload.ordered_primitives.data(),
                quant_payload.ordered_primitives.size() * sizeof(std::uint32_t),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            quant_hash = context.upload_device_buffer(
                quant_payload.hash_table.data(),
                quant_payload.hash_table.size() * sizeof(lane_b::GpuSegmentHashEntry),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
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
            context, shader_path(PHOS_GI_LANE_A_SHADER_DIR, "lane_a_producer.spv"), producer_bindings);

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
            const std::array<I001Binding, 4> bindings{{
                {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &rays},
                {1, VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR, nullptr, hwrt->top_level()},
                {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &hwrt->triangle_buffer()},
                {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &hits},
            }};
            traversal_stage = std::make_unique<I001ComputeStage>(
                context, shader_path(PHOS_GI_LANE_B_SHADER_DIR, "lane_b_b002_hwrt.spv"),
                bindings, sizeof(std::uint32_t));
        } else if (uses_quantized(options.variant)) {
            const std::array<I001Binding, 6> bindings{{
                {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &rays},
                {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &triangle_buffer},
                {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &quant_nodes},
                {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &quant_order},
                {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &quant_hash},
                {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &hits},
            }};
            traversal_stage = std::make_unique<I001ComputeStage>(
                context, shader_path(PHOS_GI_LANE_B_SHADER_DIR, "lane_b_b003_quantized_bvh8.spv"),
                bindings, sizeof(HierarchicalTraversalPush));
        } else {
            const std::array<I001Binding, 5> bindings{{
                {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &rays},
                {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &triangle_buffer},
                {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &software_nodes},
                {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &software_order},
                {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &hits},
            }};
            traversal_stage = std::make_unique<I001ComputeStage>(
                context, shader_path(PHOS_GI_LANE_B_SHADER_DIR, "lane_b_b002_software_bvh.spv"),
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
            if (uses_quantized(options.variant)) {
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
        memory_stats.stream_capacity_bytes = allocation(work);
        memory_stats.storage_capacity_bytes = allocation(storage_slots);
        memory_stats.peak_resident_bytes =
            memory_stats.persistent_bytes + memory_stats.transient_bytes + memory_stats.scratch_bytes;
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

        record_candidate_traversal(command);
        i001_compute_barrier(context, command);
        stamp(6);

        radiance_stage->record_indirect(command, indirect.buffer, 0);
        i001_compute_barrier(context, command);
        stamp(7);

        merge_stage->record_indirect(command, indirect.buffer, 0);
        i001_compute_barrier(context, command);
        stamp(8);

        const StoragePush storage_push{
            storage_capacity - 1U, kHashMaxProbe, frame_id, 0U};
        storage_update_stage->record_indirect(
            command, indirect.buffer, 0, &storage_push, sizeof(storage_push));
        i001_compute_barrier(context, command);
        stamp(9);

        const InvalidationPush invalidation_push{
            storage_capacity, frame_id, 0U, 0U};
        invalidation_stage->record(
            command, groups(storage_capacity), 1, 1,
            &invalidation_push, sizeof(invalidation_push));
        i001_compute_barrier(context, command);
        stamp(10);

        resolve_stage->record_indirect(
            command, indirect.buffer, 0, &storage_push, sizeof(storage_push));
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
        result.timings.traversal_us = timestamp_us(timestamps[5], timestamps[6], period);
        result.timings.radiance_us = timestamp_us(timestamps[6], timestamps[7], period);
        result.timings.merge_us = timestamp_us(timestamps[7], timestamps[8], period);
        result.timings.storage_update_us = timestamp_us(timestamps[8], timestamps[9], period);
        result.timings.invalidation_us = timestamp_us(timestamps[9], timestamps[10], period);
        result.timings.resolve_us = timestamp_us(timestamps[10], timestamps[11], period);
        result.timings.complete_gpu_us = timestamp_us(timestamps[0], timestamps[11], period);
        result.timings.incremental_gi_us =
            options.variant == I001Variant::DepthReuseHwrt
            ? timestamp_us(timestamps[1], timestamps[11], period)
            : result.timings.complete_gpu_us;

        result.stats.work_items = counter_values[0];
        result.stats.outputs = counter_values[1];
        result.stats.overflow = counter_values[2];
        result.stats.visible_owners = counter_values[3];
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
        const SoftwareTraversalPush push{
            work_count, reference_cpu.root(), 0U, 0U};
        reference_stage.record(
            command, groups(work_count), 1, 1, &push, sizeof(push));
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
        std::vector<HashSlotCpu> candidate_slots(storage_capacity);
        context.download_device_buffer(
            storage_slots, candidate_slots.data(), candidate_slots.size() * sizeof(HashSlotCpu));

        using OutputAccum = std::pair<std::uint64_t, std::uint32_t>;
        std::map<std::uint32_t, OutputAccum> per_output;
        std::map<ProbeKey, std::pair<std::uint64_t, std::uint32_t>> reference_probe;

        for (std::size_t index = 0; index < work_items.size(); ++index) {
            const auto& item = work_items[index];
            const auto hit = lane_b::from_gpu_hit(reference[index]);
            double value = 0.0;
            if (hit.hit) {
                const lane_b::Vec3 raw{item.dir_x, item.dir_y, item.dir_z};
                const auto direction = lane_b::normalize(raw);
                const lane_b::Vec3 origin{
                    item.probe_px + direction.x * item.interval_min,
                    item.probe_py + direction.y * item.interval_min,
                    item.probe_pz + direction.z * item.interval_min,
                };
                const auto point = origin + direction * hit.t;
                const lane_b::Vec3 light{
                    params.light_pos_interval[0],
                    params.light_pos_interval[1],
                    params.light_pos_interval[2],
                };
                const auto to_light = light - point;
                const auto distance2 = std::max(lane_b::dot(to_light, to_light), 1.0e-6F);
                const auto light_dir = to_light / std::sqrt(distance2);
                const auto normal = lane_b::normalize(hit.normal);
                const auto ndotl = std::max(0.0F, lane_b::dot(normal, light_dir));
                const auto scale = std::max(params.light_pos_interval[3], 1.0e-4F);
                const auto attenuation =
                    1.0F / (1.0F + distance2 / (scale * scale * 256.0F));
                value = std::clamp(
                    double(ndotl * attenuation) / double(1U << item.cascade),
                    0.0, 1.0);
            }
            const auto fixed = static_cast<std::uint32_t>(
                std::llround(value * 65535.0));
            auto& output = per_output[item.output_id];
            output.first += fixed;
            ++output.second;
        }

        for (const auto& item : work_items) {
            if (item.ray_index != 0U) continue;
            const auto found = per_output.find(item.output_id);
            if (found == per_output.end() || found->second.second == 0U) continue;
            const auto sample = static_cast<std::uint32_t>(
                (found->second.first + found->second.second / 2U) /
                found->second.second);
            auto& probe = reference_probe[{
                item.probe_x, item.probe_y, item.probe_z, item.cascade}];
            probe.first += sample;
            ++probe.second;
        }

        std::map<ProbeKey, double> candidate_probe;
        for (const auto& slot : candidate_slots) {
            if (slot.data[0] != 2U || slot.data[3] != frame_id) continue;
            candidate_probe[slot_key(slot)] = slot_value(slot);
        }

        double squared = 0.0;
        std::size_t compared = 0;
        for (const auto& [key, reference_accum] : reference_probe) {
            const double reference_value =
                reference_accum.second == 0U
                ? 0.0
                : double(reference_accum.first) /
                    (double(reference_accum.second) * 65535.0);
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
        quality.radiance_rms_error =
            compared == 0U
            ? std::numeric_limits<double>::infinity()
            : std::sqrt(squared / double(compared));
        quality.passed =
            quality.hit_mismatches == 0U &&
            quality.traversal_runtime_errors == 0U &&
            quality.missing_probes == 0U &&
            quality.leaked_probes == 0U &&
            quality.radiance_max_abs_error <= 1.0e-4 &&
            quality.radiance_rms_error <= 1.0e-5 &&
            last.stats.storage_failures == 0U;

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

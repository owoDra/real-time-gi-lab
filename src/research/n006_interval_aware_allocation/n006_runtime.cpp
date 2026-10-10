#include "n006_runtime.hpp"

// N006 is an integration experiment. Reuse the accepted N004/N002/N001
// implementation in this translation unit so the candidate can insert one
// prospective stage without changing historical renderer translation units.
#include "../lane_n_end_to_end_renderer/n004_runtime.cpp"

#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <limits>
#include <map>
#include <span>
#include <stdexcept>
#include <utility>
#include <vector>

namespace phos::gi::research::integration {
namespace {

struct N006GpuHashPush {
    std::uint32_t mask{};
    std::uint32_t max_probe{128U};
    std::uint32_t rays_per_probe{8U};
    std::uint32_t cascade_count{4U};
};
static_assert(sizeof(N006GpuHashPush) == 16U);

constexpr std::uint32_t kN006CanonicalCapacity = 8192U;
struct N006CanonicalPush {
    std::uint32_t mask{};
    std::uint32_t max_probe{128U};
    std::uint32_t rays_per_probe{8U};
    std::uint32_t capacity{kN006CanonicalCapacity};
};
struct N006CompactPush {
    std::uint32_t capacity{kN006CanonicalCapacity};
    std::uint32_t rays_per_probe{8U};
};
struct N006WeightPush {
    std::uint32_t key_mask{};
    std::uint32_t storage_mask{};
    std::uint32_t max_probe{128U};
    std::uint32_t frame_id{};
};
static_assert(sizeof(N006CanonicalPush) == 16U);
static_assert(sizeof(N006CompactPush) == 8U);
static_assert(sizeof(N006WeightPush) == 16U);

struct N006ExtraPush {
    std::uint32_t mode{};
    std::uint32_t owner_budget{};
    std::uint32_t extra_rays_per_probe{};
    std::uint32_t target_tile_id{};
    std::uint32_t target_cascade{};
};
static_assert(sizeof(N006ExtraPush) == 20U);

[[nodiscard]] bool n006_same_base_identity(
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

[[nodiscard]] bool n006_unit_direction(
    const LaneAWorkItemV1& item) noexcept {
    const double length2 =
        double(item.dir_x) * item.dir_x +
        double(item.dir_y) * item.dir_y +
        double(item.dir_z) * item.dir_z;
    return std::isfinite(length2) &&
        std::abs(length2 - 1.0) <= 2.0e-5;
}

} // namespace

struct N006Runtime::State {
    B002Buffer extra_stats{}, hash_keys{}, hash_stats{};
    B002Buffer canonical_reps{}, canonical_work{}, canonical_indirect{};
    B002Buffer canonical_multiplicity{};
    std::unique_ptr<I001ComputeStage> extra_stage;
    std::unique_ptr<I001ComputeStage> hash_stage;
    std::unique_ptr<I001ComputeStage> canonical_index_stage;
    std::unique_ptr<I001ComputeStage> canonical_setup_stage;
    std::unique_ptr<I001ComputeStage> canonical_compact_stage;
    std::unique_ptr<I001ComputeStage> canonical_copy_stage;
    std::unique_ptr<I001ComputeStage> canonical_apply_stage;
    std::unique_ptr<I001ComputeStage> canonical_weight_stage;
    // Optional P1j-B stages consume the compact GPU stream directly.
    std::unique_ptr<I001ComputeStage> direct_ray_stage;
    std::unique_ptr<I001ComputeStage> direct_radiance_stage;
    std::unique_ptr<I001ComputeStage> direct_storage_update_stage;
    std::unique_ptr<I001ComputeStage> direct_resolve_stage;
    std::unique_ptr<I001ComputeStage> direct_weight_stage;
    std::uint32_t hash_capacity{};
    bool direct_compact{};
};

N006Runtime::N006Runtime(
    I001Options options, bool p1j_lean_hash, bool p1j_direct_compact)
    : runtime_(std::move(options)),
      state_(std::make_unique<State>()) {
    if (p1j_direct_compact && !p1j_lean_hash) {
        throw std::runtime_error("N006 P1j-B direct compact requires lean hash");
    }
    state_->direct_compact = p1j_direct_compact;
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
        shader_path(PHOS_GI_N006_SHADER_DIR, "n006_extra_producer.spv"),
        bindings,
        sizeof(N006ExtraPush));

    const auto maximum_outputs = impl.params.limits[2];
    if (maximum_outputs == 0U || maximum_outputs >
        std::numeric_limits<std::uint32_t>::max() / 2U) {
        throw std::runtime_error("N006 hash capacity out of range");
    }
    // P1j-A is an opt-in, bounded capacity experiment only. Preserve the
    // accepted P1d/P1g/P1h/P1i hash allocations unless explicitly selected.
    // The canonical-representative capacity is still 8192 unique keys;
    // 32768 hash slots guarantee <=25% load at that accepted capacity.
    state_->hash_capacity = p1j_lean_hash
        ? 32768U
        : std::bit_ceil(maximum_outputs * 2U);
    state_->hash_keys = impl.context.create_device_buffer(
        VkDeviceSize(state_->hash_capacity) * sizeof(std::uint32_t),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    state_->hash_stats = impl.context.create_device_buffer(
        16U * sizeof(std::uint32_t),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    state_->canonical_multiplicity = impl.context.create_device_buffer(
        VkDeviceSize(state_->hash_capacity) * sizeof(std::uint32_t),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    const std::array<I001Binding, 4> hash_bindings{{
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.counters},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.work},
        {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_keys},
        {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_stats},
    }};
    state_->hash_stage = std::make_unique<I001ComputeStage>(
        impl.context,
        shader_path(PHOS_GI_N006_SHADER_DIR, "n006_probe_unique_hash.spv"),
        hash_bindings,
        sizeof(N006GpuHashPush));

    // Fixed-capacity, fail-closed P1g prototype. A separate scratch stream
    // avoids modifying the original work list while it is being compacted.
    state_->canonical_reps = impl.context.create_device_buffer(
        VkDeviceSize(kN006CanonicalCapacity) * sizeof(std::uint32_t),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    state_->canonical_work = impl.context.create_device_buffer(
        VkDeviceSize(kN006CanonicalCapacity) * impl.settings.rays_per_probe *
            sizeof(LaneAWorkItemV1),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    state_->canonical_indirect = impl.context.create_device_buffer(
        6U * sizeof(std::uint32_t),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT);
    const std::array<I001Binding, 6> index_bindings{{
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.counters},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.work},
        {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_keys},
        {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_stats},
        {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_reps},
        {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_multiplicity},
    }};
    state_->canonical_index_stage = std::make_unique<I001ComputeStage>(
        impl.context,
        shader_path(PHOS_GI_N006_SHADER_DIR, "n006_canonical_index.spv"),
        index_bindings, sizeof(N006CanonicalPush));
    const std::array<I001Binding, 2> setup_bindings{{
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_stats},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_indirect},
    }};
    state_->canonical_setup_stage = std::make_unique<I001ComputeStage>(
        impl.context,
        shader_path(PHOS_GI_N006_SHADER_DIR, "n006_canonical_setup.spv"),
        setup_bindings, sizeof(N006CompactPush));
    const std::array<I001Binding, 4> compact_bindings{{
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_stats},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_reps},
        {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.work},
        {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_work},
    }};
    state_->canonical_compact_stage = std::make_unique<I001ComputeStage>(
        impl.context,
        shader_path(PHOS_GI_N006_SHADER_DIR, "n006_canonical_compact.spv"),
        compact_bindings, sizeof(N006CompactPush));
    const std::array<I001Binding, 3> copy_bindings{{
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_stats},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_work},
        {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.work},
    }};
    state_->canonical_copy_stage = std::make_unique<I001ComputeStage>(
        impl.context,
        shader_path(PHOS_GI_N006_SHADER_DIR, "n006_canonical_copy.spv"),
        copy_bindings, sizeof(N006CompactPush));
    const std::array<I001Binding, 2> apply_bindings{{
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_stats},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.counters},
    }};
    state_->canonical_apply_stage = std::make_unique<I001ComputeStage>(
        impl.context,
        shader_path(PHOS_GI_N006_SHADER_DIR, "n006_canonical_apply.spv"),
        apply_bindings, sizeof(N006CompactPush));
    const std::array<I001Binding, 6> weight_bindings{{
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.counters},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.work},
        {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_keys},
        {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_multiplicity},
        {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.storage_slots},
        {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_stats},
    }};
    state_->canonical_weight_stage = std::make_unique<I001ComputeStage>(
        impl.context,
        shader_path(PHOS_GI_N006_SHADER_DIR, "n006_canonical_weight_storage.spv"),
        weight_bindings, sizeof(N006WeightPush));

    // P1j-B: duplicate ONLY the descriptor bindings whose shaders read work.
    // The original stages are retained for all current/historical frames.
    if (state_->direct_compact) {
        const std::array<I001Binding, 3> rays{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.counters},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_work},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.rays},
        }};
        state_->direct_ray_stage = std::make_unique<I001ComputeStage>(
            impl.context,
            shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_work_to_rays.spv"),
            rays);
        const std::array<I001Binding, 5> radiance{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.counters},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_work},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.hits},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.contributions},
            {4, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &impl.uniform},
        }};
        state_->direct_radiance_stage = std::make_unique<I001ComputeStage>(
            impl.context,
            shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_radiance.spv"),
            radiance);
        const std::array<I001Binding, 5> storage{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.counters},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_work},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.accum},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.storage_slots},
            {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.storage_stats},
        }};
        state_->direct_storage_update_stage = std::make_unique<I001ComputeStage>(
            impl.context,
            shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_storage_update.spv"),
            storage, sizeof(StoragePush));
        const std::array<I001Binding, 4> resolved{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.counters},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_work},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.storage_slots},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.resolved},
        }};
        state_->direct_resolve_stage = std::make_unique<I001ComputeStage>(
            impl.context,
            shader_path(PHOS_GI_INTEGRATION_SHADER_DIR, "i001_storage_resolve.spv"),
            resolved, sizeof(StoragePush));
        const std::array<I001Binding, 6> reweight{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.counters},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_work},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_keys},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->canonical_multiplicity},
            {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.storage_slots},
            {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &state_->hash_stats},
        }};
        state_->direct_weight_stage = std::make_unique<I001ComputeStage>(
            impl.context,
            shader_path(PHOS_GI_N006_SHADER_DIR, "n006_canonical_weight_storage.spv"),
            reweight, sizeof(N006WeightPush));
    }
}

N006Runtime::~N006Runtime() {
    if (!runtime_.impl_ || !state_) return;
    state_->extra_stage.reset();
    state_->hash_stage.reset();
    state_->canonical_index_stage.reset();
    state_->canonical_setup_stage.reset();
    state_->canonical_compact_stage.reset();
    state_->canonical_copy_stage.reset();
    state_->canonical_apply_stage.reset();
    state_->canonical_weight_stage.reset();
    state_->direct_ray_stage.reset();
    state_->direct_radiance_stage.reset();
    state_->direct_storage_update_stage.reset();
    state_->direct_resolve_stage.reset();
    state_->direct_weight_stage.reset();
    runtime_.impl_->context.destroy_buffer(state_->canonical_indirect);
    runtime_.impl_->context.destroy_buffer(state_->canonical_work);
    runtime_.impl_->context.destroy_buffer(state_->canonical_reps);
    runtime_.impl_->context.destroy_buffer(state_->canonical_multiplicity);
    runtime_.impl_->context.destroy_buffer(state_->hash_stats);
    runtime_.impl_->context.destroy_buffer(state_->hash_keys);
    runtime_.impl_->context.destroy_buffer(state_->extra_stats);
}

void N006Runtime::set_motion_fraction(float fraction) {
    runtime_.set_n004_motion_fraction(fraction);
}

N006FrameResult N006Runtime::run_frame(
    bool target_state,
    N006ExtraRequest request) {
    return run_candidate_frame(target_state, request);
}

N006FrameResult N006Runtime::run_candidate_frame(
    bool target_state,
    N006ExtraRequest request) {
    auto& impl = *runtime_.impl_;
    if (request.mode == N006ExtraMode::Targeted &&
        (request.owner_budget != 1U ||
         request.selected_cascade >= 4U ||
         request.selected_tile_id >= 320U * 180U)) {
        throw std::runtime_error("N006 targeted request requires one tile/cascade");
    }
    if (request.extra_rays_per_probe == 0U && request.owner_budget != 0U) {
        throw std::runtime_error("N006 active budget requires extra rays per probe");
    }

    ++impl.frame_id;
    auto dynamic_update = impl.update_dynamic_geometry(target_state);
#ifdef PHOS_GI_N006_SOFTWARE_PRIMARY
    if (target_state &&
        impl.options.variant == I001Variant::LaneEFinalSoftware) {
        const double primary_gpu_us = impl.n006_refresh_software_primary();
        dynamic_update.gpu_us += primary_gpu_us;
        dynamic_update.hierarchy_upload_gpu_us += primary_gpu_us;
    }
#endif
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
        fail("N006 command allocation");
    }

    auto begin = detail::make_vk_info<VkCommandBufferBeginInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (impl.context.vk().beginCommandBuffer(command, &begin) != VK_SUCCESS) {
        fail("N006 command begin");
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

    impl.producer_stage->record(command, groups(impl.params.counts[0]));
    i001_compute_barrier(impl.context, command);
    impl.clamp_stage->record(command, 1);
    i001_compute_barrier(impl.context, command);
    impl.finalize_stage->record(command, 1);
    i001_compute_barrier(impl.context, command);
    stamp(4);

    double extra_producer_gpu_us = 0.0;
    const bool active_extra =
        request.mode != N006ExtraMode::Current &&
        request.owner_budget != 0U;
    if (active_extra) {
        stamp(16);
        const N006ExtraPush push{
            static_cast<std::uint32_t>(request.mode),
            request.owner_budget,
            request.extra_rays_per_probe,
            request.selected_tile_id,
            request.selected_cascade,
        };
        state_->extra_stage->record(command, 1, 1, 1, &push, sizeof(push));
        i001_compute_barrier(impl.context, command);
        impl.finalize_stage->record(command, 1);
        i001_compute_barrier(impl.context, command);
        stamp(17);
    }

    if (request.canonical_probe_pilot &&
        (request.capture_hash_probe || active_extra ||
         request.mode != N006ExtraMode::Current ||
         impl.settings.rays_per_probe != 8U ||
         impl.settings.cascade_count != 4U)) {
        throw std::runtime_error("N006 P1g canonical pilot requires base current ray stream");
    }

    // Auxiliary P1d hash consumes the immutable base producer stream.
    // GPU time includes the hash clear, barriers, and insert dispatch.
    if (request.capture_hash_probe) {
        if (active_extra || request.mode != N006ExtraMode::Current) {
            throw std::runtime_error("N006 P1d hash only supports current mode");
        }
        // Queries 16/17 are normally reserved for the extra-ray stage. They
        // must be written even for hash-only runs before reading queries 0..19.
        stamp(16);
        stamp(17);
        stamp(18);
        impl.context.vk().cmdFillBuffer(
            command, state_->hash_keys.buffer, 0,
            state_->hash_keys.size, 0U);
        impl.context.vk().cmdFillBuffer(
            command, state_->hash_stats.buffer, 0,
            state_->hash_stats.size, 0U);
        i001_transfer_to_compute_barrier(impl.context, command);
        const N006GpuHashPush push{
            state_->hash_capacity - 1U,
            128U,
            impl.settings.rays_per_probe,
            impl.settings.cascade_count,
        };
        state_->hash_stage->record(
            command, groups(impl.params.limits[2]), 1U, 1U,
            &push, sizeof(push));
        i001_compute_barrier(impl.context, command);
        stamp(19);
    }

    const bool direct_canonical =
        request.canonical_probe_pilot && state_->direct_compact &&
        request.direct_compact_work;
    if (request.direct_compact_work &&
        (!state_->direct_compact || !request.canonical_probe_pilot)) {
        throw std::runtime_error("N006 direct work requires canonical ray stream and direct stage bindings");
    }
    if (request.canonical_probe_pilot) {
        // Three GPU-only phases: key discovery; compact representative rays
        // into nonaliasing scratch; copy back and update indirect counters.
        // All accepted renderer shaders see only the compact work prefix.
        // Query 16/17 are reserved for the later multiplicity restore pass.
        stamp(18);
        impl.context.vk().cmdFillBuffer(
            command, state_->hash_keys.buffer, 0,
            state_->hash_keys.size, 0U);
        impl.context.vk().cmdFillBuffer(
            command, state_->hash_stats.buffer, 0,
            state_->hash_stats.size, 0U);
        impl.context.vk().cmdFillBuffer(
            command, state_->canonical_multiplicity.buffer, 0,
            state_->canonical_multiplicity.size, 0U);
        i001_transfer_to_compute_barrier(impl.context, command);
        const N006CanonicalPush hash_push{
            state_->hash_capacity - 1U,
            128U,
            impl.settings.rays_per_probe,
            kN006CanonicalCapacity,
        };
        const N006CompactPush compact_push{
            kN006CanonicalCapacity, impl.settings.rays_per_probe};
        state_->canonical_index_stage->record(
            command, groups(impl.params.limits[2]), 1U, 1U,
            &hash_push, sizeof(hash_push));
        i001_compute_barrier(impl.context, command);
        state_->canonical_setup_stage->record(
            command, 1U, 1U, 1U, &compact_push, sizeof(compact_push));
        i001_compute_barrier(impl.context, command);
        state_->canonical_compact_stage->record_indirect(
            command, state_->canonical_indirect.buffer, 0U,
            &compact_push, sizeof(compact_push));
        i001_compute_barrier(impl.context, command);
        if (!direct_canonical) {
            state_->canonical_copy_stage->record_indirect(
                command, state_->canonical_indirect.buffer, 12U,
                &compact_push, sizeof(compact_push));
            i001_compute_barrier(impl.context, command);
        }
        state_->canonical_apply_stage->record(
            command, 1U, 1U, 1U, &compact_push, sizeof(compact_push));
        i001_compute_barrier(impl.context, command);
        impl.finalize_stage->record(command, 1U);
        i001_compute_barrier(impl.context, command);
        stamp(19);
    }

    (direct_canonical ? state_->direct_ray_stage.get() : impl.ray_stage.get())
        ->record_indirect(command, impl.indirect.buffer, 0);
    i001_compute_barrier(impl.context, command);
    stamp(5);

    if (uses_hwrt(impl.options.variant)) {
        i001_acceleration_to_compute_barrier(impl.context, command);
    }
    impl.record_candidate_traversal(command);
    i001_compute_barrier(impl.context, command);
    stamp(6);

    (direct_canonical ? state_->direct_radiance_stage.get()
                      : impl.radiance_stage.get())
        ->record_indirect(command, impl.indirect.buffer, 0);
    i001_compute_barrier(impl.context, command);
    stamp(7);

    impl.merge_stage->record_indirect(command, impl.indirect.buffer, 0);
    i001_compute_barrier(impl.context, command);
    stamp(8);

    const StoragePush storage_reserve_push{
        impl.storage_capacity - 1U, kHashMaxProbe, impl.frame_id, 0U};
    (direct_canonical ? state_->direct_storage_update_stage.get()
                      : impl.storage_update_stage.get())->record_indirect(
        command,
        impl.indirect.buffer,
        0,
        &storage_reserve_push,
        sizeof(storage_reserve_push));
    i001_compute_barrier(impl.context, command);

    const StoragePush storage_accumulate_push{
        impl.storage_capacity - 1U, kHashMaxProbe, impl.frame_id, 1U};
    (direct_canonical ? state_->direct_storage_update_stage.get()
                      : impl.storage_update_stage.get())->record_indirect(
        command,
        impl.indirect.buffer,
        0,
        &storage_accumulate_push,
        sizeof(storage_accumulate_push));
    i001_compute_barrier(impl.context, command);
    if (request.canonical_probe_pilot) {
        stamp(16);
        const N006WeightPush weight{
            state_->hash_capacity - 1U,
            impl.storage_capacity - 1U,
            kHashMaxProbe,
            impl.frame_id,
        };
        (direct_canonical ? state_->direct_weight_stage.get()
                          : state_->canonical_weight_stage.get())->record(
            command, groups(impl.params.limits[2]), 1U, 1U,
            &weight, sizeof(weight));
        i001_compute_barrier(impl.context, command);
        stamp(17);
    }
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
    (direct_canonical ? state_->direct_resolve_stage.get()
                      : impl.resolve_stage.get())->record_indirect(
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
        fail("N006 command end");
    }
    auto submit = detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &command;
    if (impl.context.vk().queueSubmit(
            impl.context.queue(), 1, &submit, impl.fence) != VK_SUCCESS) {
        fail("N006 submit");
    }
    if (impl.context.vk().waitForFences(
            1, &impl.fence, VK_TRUE, UINT64_MAX) != VK_SUCCESS) {
        fail("N006 fence wait");
    }

    std::array<std::uint64_t, 20> timestamps{};
    const auto timestamp_count =
        (request.capture_hash_probe || request.canonical_probe_pilot)
            ? 20U : (active_extra ? 18U : 16U);
    if (impl.context.vk().getQueryPoolResults(
            impl.query_pool,
            0,
            timestamp_count,
            sizeof(timestamps),
            timestamps.data(),
            sizeof(std::uint64_t),
            VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
        fail("N006 timestamp readback");
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
    // P1e prospective boundary: hash pass is a disjoint segment 4->19.
    // Its ray-prep segment is 19->5, not the old inclusive 4->5 P1d
    // measurement. Frozen P1d GPU evidence is deliberately unchanged.
    result.timings.ray_prepare_us =
        (request.capture_hash_probe || request.canonical_probe_pilot)
        ? timestamp_us(timestamps[19], timestamps[5], period)
        : (active_extra
            ? timestamp_us(timestamps[17], timestamps[5], period)
            : timestamp_us(timestamps[4], timestamps[5], period));
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

    N006ExtraStats extra{};
    extra.base_traced_rays =
        active_extra ? extra_values[0] : result.stats.work_items;
    extra.eligible_owner_count = active_extra ? extra_values[1] : 0U;
    extra.selected_owner_count = active_extra ? extra_values[2] : 0U;
    extra.extra_work_items = active_extra ? extra_values[3] : 0U;
    extra.extra_rays_requested =
        request.owner_budget * request.extra_rays_per_probe;
    extra.extra_rays_traced = extra.extra_work_items;
    extra.eligible_probe_count = extra.eligible_owner_count;
    extra.extra_probe_count = extra.selected_owner_count;
    extra.extra_probe_fraction = result.stats.visible_owners == 0U
        ? 0.0
        : double(extra.selected_owner_count) /
            (double(result.stats.visible_owners) * impl.settings.cascade_count);
    extra.extra_producer_gpu_us = extra_producer_gpu_us;
    if (request.capture_hash_probe) {
        std::array<std::uint32_t, 16> key_stats{};
        impl.context.download_device_buffer(
            state_->hash_stats, key_stats.data(), sizeof(key_stats));
        auto& probe = extra.gpu_hash_probe;
        probe.executed = true;
        probe.hash_slots = state_->hash_capacity;
        probe.scratch_bytes = state_->hash_keys.size + state_->hash_stats.size;
        probe.unique_keys = key_stats[0];
        probe.duplicate_outputs = key_stats[1];
        probe.invalid_keys = key_stats[2];
        probe.failed_inserts = key_stats[3];
        probe.collision_steps = key_stats[4];
        probe.complete_hash_gpu_us =
            timestamp_us(timestamps[4], timestamps[19], period);
        for (std::uint32_t cascade = 0U; cascade < 4U; ++cascade) {
            probe.unique_by_cascade[cascade] = key_stats[6U + cascade];
            probe.duplicate_by_cascade[cascade] = key_stats[10U + cascade];
        }
        if (probe.invalid_keys != 0U || probe.failed_inserts != 0U ||
            probe.unique_keys + probe.duplicate_outputs != result.stats.outputs ||
            probe.unique_keys !=
                probe.unique_by_cascade[0] + probe.unique_by_cascade[1] +
                probe.unique_by_cascade[2] + probe.unique_by_cascade[3] ||
            probe.duplicate_outputs !=
                probe.duplicate_by_cascade[0] + probe.duplicate_by_cascade[1] +
                probe.duplicate_by_cascade[2] + probe.duplicate_by_cascade[3]) {
            throw std::runtime_error("N006 P1d GPU unique-key hash counts invalid");
        }
    }

    if (request.canonical_probe_pilot) {
        std::array<std::uint32_t, 16> counters{};
        impl.context.download_device_buffer(
            state_->hash_stats, counters.data(), sizeof(counters));
        auto& data = extra.canonical;
        data.executed = true;
        data.copyback_executed = !direct_canonical;
        data.hash_slots = state_->hash_capacity;
        data.canonical_outputs = counters[0];
        data.duplicates = counters[1];
        data.invalid_keys = counters[2];
        data.failed_inserts = counters[3];
        data.collision_steps = counters[4];
        data.index_overflows = counters[5];
        data.owner_weight_errors = counters[14];
        data.weighted_owner_total = counters[15];
        data.owner_weight_storage_gpu_us =
            timestamp_us(timestamps[16], timestamps[17], period);
        data.original_outputs = counters[0] + counters[1];
        data.original_work_items =
            data.original_outputs * impl.settings.rays_per_probe;
        data.canonical_work_items = data.canonical_outputs *
            impl.settings.rays_per_probe;
        data.total_canonical_gpu_us =
            timestamp_us(timestamps[4], timestamps[19], period);
        data.scratch_bytes = state_->hash_keys.size + state_->hash_stats.size +
            state_->canonical_multiplicity.size +
            state_->canonical_reps.size + state_->canonical_work.size +
            state_->canonical_indirect.size;
        for (std::uint32_t cascade = 0U; cascade < 4U; ++cascade) {
            data.unique_by_cascade[cascade] = counters[6U + cascade];
        }
        if (data.invalid_keys != 0U || data.failed_inserts != 0U ||
            data.index_overflows != 0U || data.owner_weight_errors != 0U ||
            data.weighted_owner_total != data.original_outputs ||
            data.canonical_outputs > kN006CanonicalCapacity ||
            data.original_outputs != result.stats.visible_owners *
                impl.settings.cascade_count ||
            data.canonical_outputs != result.stats.outputs ||
            data.canonical_work_items != result.stats.work_items ||
            std::uint64_t(data.unique_by_cascade[0]) +
            data.unique_by_cascade[1] + data.unique_by_cascade[2] +
            data.unique_by_cascade[3] != data.canonical_outputs ||
            result.stats.storage_failures != 0U ||
            result.stats.overflow != 0U) {
            throw std::runtime_error(
                "N006 P1g canonical GPU counts/keys/capacity invalid");
        }
    }

    const auto total_work = result.stats.work_items;
    std::vector<LaneAWorkItemV1> work_items(total_work);
    if (total_work != 0U) {
        impl.context.download_device_buffer(
            direct_canonical ? state_->canonical_work : impl.work,
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
        (request.canonical_probe_pilot
            ? (total_work == result.stats.outputs *
                impl.settings.rays_per_probe)
            : (extra.base_traced_rays % (
                impl.settings.cascade_count *
                impl.settings.rays_per_probe) == 0U));
    if (base_count_valid && !request.canonical_probe_pilot) {
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

    if (base_count_valid && request.canonical_probe_pilot) {
        using Key = std::array<std::int32_t, 4>;
        std::map<Key, std::uint32_t> unique;
        bool valid = result.stats.work_items ==
            result.stats.outputs * impl.settings.rays_per_probe;
        const auto rays = impl.settings.rays_per_probe;
        for (std::uint32_t output = 0U; valid &&
             output < result.stats.outputs; ++output) {
            const auto& representative = work_items[output * rays];
            const Key key{
                representative.probe_x, representative.probe_y,
                representative.probe_z,
                static_cast<std::int32_t>(representative.cascade)};
            if (representative.cascade >= 4U ||
                !unique.emplace(key, output).second ||
                representative.tile_id >= tile_owners.size() ||
                tile_owners[representative.tile_id] != representative.surface_id) {
                valid = false;
                break;
            }
            for (std::uint32_t ray = 0U; ray < rays; ++ray) {
                const auto& item = work_items[output * rays + ray];
                if (item.ray_index != ray ||
                    item.output_id != output ||
                    item.probe_x != key[0] ||
                    item.probe_y != key[1] ||
                    item.probe_z != key[2] ||
                    item.cascade != representative.cascade ||
                    item.surface_id != representative.surface_id ||
                    item.tile_id != representative.tile_id ||
                    !n006_unit_direction(item) ||
                    ((item.dir_x > 0.0F) != ((ray & 1U) != 0U)) ||
                    ((item.dir_y > 0.0F) != ((ray & 2U) != 0U)) ||
                    ((item.dir_z > 0.0F) != ((ray & 4U) != 0U))) {
                    valid = false;
                    break;
                }
            }
        }
        extra.base_prefix_correct = valid &&
            unique.size() == result.stats.outputs;
    }

    bool extra_ok =
        base_count_valid &&
        total_work == extra.base_traced_rays + extra.extra_work_items &&
        extra.extra_work_items ==
            extra.selected_owner_count *
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
                !n006_unit_direction(item)) {
                extra_ok = false;
                break;
            }
            const auto& base = work_items[
                static_cast<std::size_t>(base_by_output[item.output_id])];
            if (!n006_same_base_identity(base, item)) {
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

    // Non-formal forensic readback only. The original N006 candidate produces
    // identical RGB on 11/12 probes; identify where integer quantization or
    // shared-probe averaging can erase the additional-ray contribution.
    if (active_extra && extra_ok && extra.extra_work_items != 0U &&
        request.mode == N006ExtraMode::Targeted) {
        N006InfluenceTrace trace{};
        const auto& selected = work_items.at(extra.base_traced_rays);
        if (selected.tile_id != request.selected_tile_id ||
            selected.cascade != request.selected_cascade ||
            selected.output_id >= result.stats.outputs) {
            throw std::runtime_error("N006 influence target work identity mismatch");
        }

        trace.tile_id = selected.tile_id;
        trace.cascade = selected.cascade;
        trace.output_id = selected.output_id;
        trace.probe_x = selected.probe_x;
        trace.probe_y = selected.probe_y;
        trace.probe_z = selected.probe_z;

        std::vector<std::array<std::uint32_t, 2>> contributions(total_work);
        impl.context.download_device_buffer(
            impl.contributions,
            contributions.data(),
            contributions.size() * sizeof(contributions[0]));

        std::vector<std::array<std::uint32_t, 2>> merged(result.stats.outputs);
        impl.context.download_device_buffer(
            impl.accum,
            merged.data(),
            merged.size() * sizeof(merged[0]));

        auto same_key = [&](const LaneAWorkItemV1& item) {
            return item.probe_x == trace.probe_x &&
                item.probe_y == trace.probe_y &&
                item.probe_z == trace.probe_z &&
                item.cascade == trace.cascade;
        };
        for (std::uint32_t index = 0U; index < total_work; ++index) {
            const auto& item = work_items[index];
            if (item.output_id != trace.output_id) continue;
            if (contributions[index][0] != trace.output_id) {
                throw std::runtime_error("N006 contribution output ID drift");
            }
            const auto value = contributions[index][1];
            if (value > 65535U) {
                throw std::runtime_error("N006 contribution exceeds 16-bit value");
            }
            if (index < extra.base_traced_rays) {
                ++trace.base_ray_count;
                trace.base_radiance_sum16 += value;
                if (value == 0U) ++trace.base_zero_rays;
            } else {
                ++trace.extra_ray_count;
                trace.extra_radiance_sum16 += value;
                if (value == 0U) ++trace.extra_zero_rays;
            }
        }
        if (trace.base_ray_count != impl.settings.rays_per_probe ||
            trace.extra_ray_count != request.extra_rays_per_probe) {
            throw std::runtime_error("N006 causal trace contribution count mismatch");
        }
        const auto merged_sum =
            trace.base_radiance_sum16 + trace.extra_radiance_sum16;
        const auto merged_count = trace.base_ray_count + trace.extra_ray_count;
        if (merged[trace.output_id][0] != merged_sum ||
            merged[trace.output_id][1] != merged_count) {
            throw std::runtime_error("N006 merged output disagrees with ray contributions");
        }
        const auto rounded_mean16 = [](std::uint64_t sum,
                                       std::uint32_t count) -> std::uint32_t {
            if (count == 0U) throw std::runtime_error("N006 zero sample count");
            return static_cast<std::uint32_t>((sum + count / 2U) / count);
        };
        trace.base_output_mean16 = rounded_mean16(
            trace.base_radiance_sum16, trace.base_ray_count);
        trace.target_output_mean16 = rounded_mean16(
            merged_sum, merged_count);

        for (std::uint32_t index = 0U; index < extra.base_traced_rays; ++index) {
            const auto& item = work_items[index];
            if (item.ray_index != 0U || !same_key(item)) continue;
            if (item.output_id >= merged.size()) {
                throw std::runtime_error("N006 other owner output out of range");
            }
            const auto& entry = merged[item.output_id];
            if (entry[1] == 0U) {
                throw std::runtime_error("N006 same-probe owner lacks merged output");
            }
            const auto sample_after = rounded_mean16(entry[0], entry[1]);
            const auto sample_before = item.output_id == trace.output_id
                ? trace.base_output_mean16
                : sample_after;
            trace.before_storage_sum16 += sample_before;
            trace.after_storage_sum16 += sample_after;
            ++trace.shared_probe_outputs;
        }
        if (trace.shared_probe_outputs == 0U) {
            throw std::runtime_error("N006 target probe has no storage owners");
        }
        trace.before_storage_mean16 =
            double(trace.before_storage_sum16) /
            double(trace.shared_probe_outputs);
        trace.after_storage_mean16 =
            double(trace.after_storage_sum16) /
            double(trace.shared_probe_outputs);

        std::vector<HashSlotCpu> slots(impl.storage_capacity);
        impl.context.download_device_buffer(
            impl.storage_slots, slots.data(), slots.size() * sizeof(slots[0]));
        std::uint32_t matches = 0U;
        for (const auto& slot : slots) {
            if (slot.key[0] != trace.probe_x ||
                slot.key[1] != trace.probe_y ||
                slot.key[2] != trace.probe_z ||
                slot.key[3] != static_cast<std::int32_t>(trace.cascade) ||
                slot.data[3] != impl.frame_id ||
                slot.data[2] == 0U) continue;
            trace.observed_storage_sum16 = slot.data[1];
            trace.observed_storage_outputs = slot.data[2];
            ++matches;
        }
        if (matches != 1U ||
            trace.observed_storage_sum16 != trace.after_storage_sum16 ||
            trace.observed_storage_outputs != trace.shared_probe_outputs) {
            throw std::runtime_error(
                "N006 storage probe aggregation differs from owner contributions");
        }
        trace.available = true;
        extra.influence_trace = trace;
    }

    return {result, extra};
}

N006FrameResult N006Runtime::run_topology_churn_frame(
    N006ExtraRequest request) {
    auto& impl = *runtime_.impl_;
    if (impl.options.variant != I001Variant::LaneEFinalHwrt ||
        impl.options.scenario != I001Scenario::DeformingControl) {
        throw std::runtime_error(
            "N006 topology frame requires LaneEFinalHwrt/deforming-control");
    }
    if (impl.geometry_is_target || !impl.hwrt || impl.moving.primitives.empty()) {
        throw std::runtime_error("N006 topology frame requires fresh dynamic source state");
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
        throw std::runtime_error("N006 topology replacement primitive-id overflow");
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
        throw std::runtime_error("N006 topology mutation schedule drifted");
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

N006OutputEquivalenceAudit N006Runtime::probe_output_equivalence_audit() {
    auto& impl = *runtime_.impl_;
    if (!impl.have_last) {
        throw std::runtime_error("N006 P1f requires a completed current frame");
    }
    const auto cascades = impl.settings.cascade_count;
    const auto rays = impl.settings.rays_per_probe;
    const auto work_count = impl.last.stats.work_items;
    const auto outputs = impl.last.stats.outputs;
    const auto owners = impl.last.stats.visible_owners;
    if (cascades != 4U || rays != 8U ||
        std::uint64_t(owners) * cascades != outputs ||
        std::uint64_t(outputs) * rays != work_count) {
        throw std::runtime_error("N006 P1f unexpected base-only stream cardinality");
    }
    std::vector<LaneAWorkItemV1> work(work_count);
    std::vector<std::array<std::uint32_t, 2>> merged(outputs);
    std::vector<HashSlotCpu> slots(impl.storage_capacity);
    impl.context.download_device_buffer(
        impl.work, work.data(), work.size() * sizeof(work[0]));
    impl.context.download_device_buffer(
        impl.accum, merged.data(), merged.size() * sizeof(merged[0]));
    impl.context.download_device_buffer(
        impl.storage_slots, slots.data(), slots.size() * sizeof(slots[0]));

    using Key = std::array<std::int32_t, 4>;
    struct KeyData {
        std::uint32_t first_sum{}, first_count{}, first_mean{}, owner_count{};
        std::uint32_t divergent_outputs{};
        bool divergent_means{};
        std::uint64_t sum_mean16{};
        std::uint32_t storage_matches{};
    };
    std::vector<std::map<Key, KeyData>> per_cascade(cascades);
    std::vector<bool> visited_output(outputs, false);
    N006OutputEquivalenceAudit audit{};
    audit.base_work_items = work_count;
    audit.owner_outputs = outputs;
    audit.visible_owners = owners;
    audit.rays_per_probe = rays;
    audit.cascade_count = cascades;
    audit.cascades.resize(cascades);
    for (std::uint32_t cascade = 0; cascade < cascades; ++cascade) {
        audit.cascades[cascade].cascade = cascade;
    }

    // Each owner emits a four-cascade, eight-ray base block. Only ray zero
    // is inspected because merged sums/counts belong to its output_id.
    for (std::uint32_t block_base = 0; block_base < work_count;
         block_base += cascades * rays) {
        for (std::uint32_t cascade = 0; cascade < cascades; ++cascade) {
            const auto& item = work[block_base + cascade * rays];
            if (item.cascade != cascade || item.ray_index != 0U ||
                item.output_id >= outputs ||
                visited_output[item.output_id]) {
                throw std::runtime_error("N006 P1f output identity invalid");
            }
            visited_output[item.output_id] = true;
            const auto [sum, count] = merged[item.output_id];
            if (count == 0U || count != rays ||
                std::uint64_t(sum) > std::uint64_t(count) * 65535U) {
                ++audit.cascades[cascade].zero_sample_outputs;
                throw std::runtime_error("N006 P1f invalid merged radiance samples");
            }
            // Exactly matches the accepted integer accumulation / rounding.
            const auto mean = (sum + count / 2U) / count;
            const Key key{item.probe_x, item.probe_y, item.probe_z,
                          static_cast<std::int32_t>(cascade)};
            auto [it, fresh] = per_cascade[cascade].try_emplace(
                key, KeyData{sum, count, mean, 0U, 0U, false, 0U, 0U});
            auto& group = it->second;
            if (!fresh) {
                if (sum != group.first_sum || count != group.first_count) {
                    ++group.divergent_outputs;
                }
                if (mean != group.first_mean) {
                    group.divergent_means = true;
                }
            }
            ++group.owner_count;
            group.sum_mean16 += mean;
            ++audit.cascades[cascade].owner_outputs;
        }
    }
    if (std::any_of(visited_output.begin(), visited_output.end(),
                    [](bool found) { return !found; })) {
        throw std::runtime_error("N006 P1f not every owner output was visited");
    }

    // The production storage shader must receive the exact per-owner means:
    // matching one canonical result cannot change the mean if all owners are
    // equal. Verify this against the GPU's actual frame-tagged hash slots.
    for (const auto& slot : slots) {
        if (slot.data[3] != impl.frame_id || slot.data[2] == 0U) {
            continue;
        }
        if (slot.key[3] < 0 || slot.key[3] >= static_cast<int>(cascades)) {
            throw std::runtime_error("N006 P1f invalid live storage cascade");
        }
        const auto cascade = static_cast<std::uint32_t>(slot.key[3]);
        const Key key{slot.key[0], slot.key[1], slot.key[2], slot.key[3]};
        const auto it = per_cascade[cascade].find(key);
        if (it == per_cascade[cascade].end()) {
            // Spatial slots created in a previous frame must not be counted as
            // if they were current; a live unknown key violates this contract.
            throw std::runtime_error("N006 P1f unexpected live GPU storage key");
        }
        auto& group = it->second;
        ++group.storage_matches;
        if (slot.data[1] != group.sum_mean16 ||
            slot.data[2] != group.owner_count) {
            ++audit.cascades[cascade].missing_or_bad_gpu_storage_keys;
        }
    }

    for (std::uint32_t cascade = 0; cascade < cascades; ++cascade) {
        auto& row = audit.cascades[cascade];
        row.unique_probe_keys =
            static_cast<std::uint32_t>(per_cascade[cascade].size());
        for (const auto& [key, group] : per_cascade[cascade]) {
            (void)key;
            if (group.owner_count > 1U) {
                ++row.shared_keys;
            }
            if (group.divergent_outputs > 0U) {
                ++row.divergent_merged_keys;
                row.divergent_owner_outputs += group.divergent_outputs;
            }
            if (group.divergent_means) {
                ++row.divergent_rounded_mean_keys;
            }
            if (group.storage_matches != 1U) {
                ++row.missing_or_bad_gpu_storage_keys;
            }
        }
    }
    audit.all_gpu_storage_slots_reconstructed =
        std::all_of(audit.cascades.begin(), audit.cascades.end(),
                    [](const auto& row) {
                        return row.missing_or_bad_gpu_storage_keys == 0U;
                    });
    return audit;
}

N006ProbeMultiplicityAudit N006Runtime::probe_multiplicity_audit() {
    auto& impl = *runtime_.impl_;
    if (!impl.have_last) {
        throw std::runtime_error("N006 multiplicity audit requires completed frame");
    }
    const auto cascades = impl.settings.cascade_count;
    const auto rays = impl.settings.rays_per_probe;
    const auto block = cascades * rays;
    const auto count = impl.last.stats.work_items;
    if (block == 0U || count != impl.last.stats.visible_owners * block ||
        count != impl.last.stats.outputs * rays ||
        count % block != 0U) {
        throw std::runtime_error("N006 multiplicity audit needs unmodified current-mode base stream");
    }
    std::vector<LaneAWorkItemV1> work(count);
    if (count != 0U) {
        impl.context.download_device_buffer(
            impl.work, work.data(), work.size() * sizeof(work[0]));
    }

    // For each shared probe key retain one representative 8-direction block,
    // then check whether later owners create precisely the same ray origins
    // and directions (surface/tile/output IDs intentionally excluded).
    using Key = std::array<std::int32_t, 4>;
    struct Group { std::uint32_t first{}, count{}; };
    std::vector<std::map<Key, Group>> keys(cascades);
    std::vector<bool> identical(cascades, true);
    for (std::uint32_t owner_base = 0U; owner_base < count;
         owner_base += block) {
        for (std::uint32_t cascade = 0U; cascade < cascades; ++cascade) {
            const auto offset = owner_base + cascade * rays;
            const auto& first = work[offset];
            if (first.cascade != cascade || first.ray_index != 0U) {
                throw std::runtime_error("N006 multiplicity base block layout invalid");
            }
            const Key key{first.probe_x, first.probe_y, first.probe_z,
                          static_cast<std::int32_t>(cascade)};
            auto [it, added] = keys[cascade].try_emplace(
                key, Group{offset, 0U});
            auto& group = it->second;
            if (!added) {
                const auto& representative = work[group.first];
                for (std::uint32_t ray = 0U; ray < rays; ++ray) {
                    const auto& item = work[offset + ray];
                    const auto& original = work[group.first + ray];
                    if (item.ray_index != ray ||
                        item.cascade != cascade ||
                        item.probe_x != representative.probe_x ||
                        item.probe_y != representative.probe_y ||
                        item.probe_z != representative.probe_z ||
                        item.interval_min != original.interval_min ||
                        item.interval_max != original.interval_max ||
                        item.probe_px != original.probe_px ||
                        item.probe_py != original.probe_py ||
                        item.probe_pz != original.probe_pz ||
                        item.dir_x != original.dir_x ||
                        item.dir_y != original.dir_y ||
                        item.dir_z != original.dir_z) {
                        identical[cascade] = false;
                    }
                }
            }
            ++group.count;
        }
    }

    N006ProbeMultiplicityAudit result{};
    result.base_work_items = count;
    result.visible_owners = impl.last.stats.visible_owners;
    result.rays_per_probe = rays;
    result.cascade_count = cascades;
    for (std::uint32_t cascade = 0U; cascade < cascades; ++cascade) {
        N006ProbeMultiplicityRow row{};
        row.cascade = cascade;
        row.owner_outputs = impl.last.stats.visible_owners;
        row.unique_probe_keys = static_cast<std::uint32_t>(keys[cascade].size());
        row.same_probe_ray_inputs_identical = identical[cascade];
        for (const auto& [key, group] : keys[cascade]) {
            (void)key;
            row.max_owner_outputs_per_key =
                std::max(row.max_owner_outputs_per_key, group.count);
            if (group.count > 1U) ++row.shared_keys;
        }
        row.duplicated_ray_inputs =
            std::uint64_t(row.owner_outputs - row.unique_probe_keys) * rays;
        result.cascades.push_back(row);
    }
    return result;
}

std::vector<std::uint32_t> N006Runtime::visible_tile_ids() {
    auto& impl = *runtime_.impl_;
    const std::uint32_t count =
        impl.params.counts[1] * impl.params.counts[2];
    std::vector<std::uint32_t> owners(count);
    impl.context.download_device_buffer(
        impl.owners,
        owners.data(),
        owners.size() * sizeof(owners[0]));
    std::vector<std::uint32_t> result;
    result.reserve(count);
    for (std::uint32_t tile = 0; tile < count; ++tile) {
        if (owners[tile] != 0xffffffffU) result.push_back(tile);
    }
    return result;
}

I001N004HitDiagnostics N006Runtime::n004_hit_diagnostics() {
    return runtime_.n004_hit_diagnostics();
}

I001RendererReadback N006Runtime::renderer_readback() {
    return runtime_.renderer_readback();
}

const std::string& N006Runtime::device_name() const noexcept {
    return runtime_.device_name();
}
const std::string& N006Runtime::driver_name() const noexcept {
    return runtime_.driver_name();
}
const std::string& N006Runtime::driver_info() const noexcept {
    return runtime_.driver_info();
}
std::uint32_t N006Runtime::api_version() const noexcept {
    return runtime_.api_version();
}
float N006Runtime::timestamp_period_ns() const noexcept {
    return runtime_.timestamp_period_ns();
}


namespace {

// One bounded diagnostic workload row; no atomics or writes to accepted
// output buffers. Each actual ray/pixel writes its own uvec4 slots.
[[nodiscard]] N006P1lB0Metric p1l_b0_metric(
    const std::vector<std::uint32_t>& raw,
    std::uint32_t count,
    std::uint32_t vectors_per_sample,
    std::uint32_t tuple,
    std::uint32_t component) {
    if (count == 0U || raw.size() !=
        std::size_t(count) * vectors_per_sample * 4U) {
        throw std::runtime_error("P1l-B0 malformed diagnostic sample count");
    }
    std::vector<std::uint32_t> values;
    values.reserve(count);
    N006P1lB0Metric out{};
    for (std::uint32_t i = 0U; i < count; ++i) {
        const auto v = raw[(std::size_t(i) * vectors_per_sample + tuple) * 4U + component];
        values.push_back(v);
        out.total += v;
        out.nonzero += (v != 0U) ? 1U : 0U;
        out.maximum = std::max(out.maximum, v);
    }
    std::sort(values.begin(), values.end());
    const auto percentile = [&](double fraction) {
        const auto rank = fraction * double(values.size() - 1U);
        const auto lo = static_cast<std::size_t>(rank);
        const auto hi = std::min(lo + 1U, values.size() - 1U);
        const double t = rank - double(lo);
        return double(values[lo]) * (1.0 - t) + double(values[hi]) * t;
    };
    out.mean = double(out.total) / double(count);
    out.p50 = percentile(0.50);
    out.p90 = percentile(0.90);
    out.p99 = percentile(0.99);
    return out;
}

} // namespace

N006P1lB0Profile N006Runtime::p1l_b0_work_counts() {
    auto& impl = *runtime_.impl_;
    if (impl.options.variant != I001Variant::LaneEFinalSoftware ||
        !impl.have_last ||
        impl.last.stats.work_items == 0U ||
        impl.last.stats.work_items > impl.params.limits[1] ||
        !lane_e_final_supported_scenario(impl.options.scenario)) {
        throw std::runtime_error(
            "P1l-B0 requires completed Lane-E-final software canonical frame");
    }
    const std::uint32_t pixels = impl.params.counts[1] * impl.params.counts[2];
    const std::uint32_t rays = impl.last.stats.work_items;
    N006P1lB0Profile report{};
    report.pixels = pixels;
    report.secondary_rays = rays;
    B002Buffer primary_counts{}, shadow_counts{}, secondary_counts{};
    B002Buffer primary_output{}, shadow_output{}, secondary_output{};

    const auto cleanup = [&]() noexcept {
        impl.context.destroy_buffer(secondary_output);
        impl.context.destroy_buffer(shadow_output);
        impl.context.destroy_buffer(primary_output);
        impl.context.destroy_buffer(secondary_counts);
        impl.context.destroy_buffer(shadow_counts);
        impl.context.destroy_buffer(primary_counts);
    };
    try {
        constexpr auto storage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
        primary_counts = impl.context.create_device_buffer(
            VkDeviceSize(pixels) * 4U * sizeof(std::uint32_t), storage);
        shadow_counts = impl.context.create_device_buffer(
            VkDeviceSize(pixels) * 8U * sizeof(std::uint32_t), storage);
        secondary_counts = impl.context.create_device_buffer(
            VkDeviceSize(rays) * 8U * sizeof(std::uint32_t), storage);
        primary_output = impl.context.create_device_buffer(
            impl.primary_hits.size, storage);
        shadow_output = impl.context.create_device_buffer(
            impl.image.size, storage);
        secondary_output = impl.context.create_device_buffer(
            impl.hits.size, storage);
        const std::array<I001Binding, 6> primary_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &primary_output},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.n006_primary_triangles},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.n006_primary_nodes},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.n006_primary_order},
            {4, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &impl.uniform},
            {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &primary_counts},
        }};
        const std::array<I001Binding, 8> shadow_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.primary_hits},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.storage_slots},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &shadow_output},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.n006_primary_triangles},
            {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.n006_primary_nodes},
            {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.n006_primary_order},
            {6, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &impl.uniform},
            {7, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &shadow_counts},
        }};
        const std::array<I001Binding, 9> secondary_bindings{{
            {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.rays},
            {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.triangle_buffer},
            {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.instance_nodes},
            {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.instance_order},
            {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.instance_hash},
            {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.instance_table},
            {6, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &secondary_output},
            {7, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl.counters},
            {8, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &secondary_counts},
        }};
        auto primary = std::make_unique<I001ComputeStage>(
            impl.context,
            shader_path(PHOS_GI_N006_SHADER_DIR, "n006_p1l_primary_count.spv"),
            primary_bindings);
        auto shadow = std::make_unique<I001ComputeStage>(
            impl.context,
            shader_path(PHOS_GI_N006_SHADER_DIR, "n006_p1l_composite_count.spv"),
            shadow_bindings, sizeof(StoragePush));
        auto secondary = std::make_unique<I001ComputeStage>(
            impl.context,
            shader_path(PHOS_GI_N006_SHADER_DIR, "n006_p1l_e003_count.spv"),
            secondary_bindings, sizeof(lane_e::E003TraversalPush));

        // N004 diagnostic also uses this pool and waits on the same fence.
        // B0 begins only after the normal measured GPU frame has completed.
        impl.context.vk().resetFences(1, &impl.fence);
        impl.context.vk().resetCommandPool(impl.command_pool, 0);
        VkCommandBuffer command{};
        auto allocate = detail::make_vk_info<VkCommandBufferAllocateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
        allocate.commandPool = impl.command_pool;
        allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        allocate.commandBufferCount = 1;
        if (impl.context.vk().allocateCommandBuffers(&allocate, &command) != VK_SUCCESS) {
            throw std::runtime_error("P1l-B0 command allocation failed");
        }
        auto begin = detail::make_vk_info<VkCommandBufferBeginInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
        begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        if (impl.context.vk().beginCommandBuffer(command, &begin) != VK_SUCCESS) {
            throw std::runtime_error("P1l-B0 command begin failed");
        }

        primary->record(command, (impl.params.counts[1] + 7U) / 8U,
                        (impl.params.counts[2] + 7U) / 8U);
        i001_compute_barrier(impl.context, command);

        const StoragePush composite_push{
            impl.storage_capacity - 1U, kHashMaxProbe, impl.frame_id, 0U};
        shadow->record(command, (impl.params.counts[1] + 7U) / 8U,
                       (impl.params.counts[2] + 7U) / 8U, 1U,
                       &composite_push, sizeof(composite_push));
        i001_compute_barrier(impl.context, command);

        lane_e::E003TraversalPush traversal_push{};
        traversal_push.values[0] = impl.params.limits[1];
        traversal_push.values[1] = static_cast<std::uint32_t>(
            impl.options.scenario == I001Scenario::DeformingControl
              ? impl.deforming_local_setup.instances.size()
              : impl.instance_quantized_payload.instances.size());
        secondary->record(command, groups(rays), 1U, 1U,
                          &traversal_push, sizeof(traversal_push));
        i001_compute_barrier(impl.context, command);
        if (impl.context.vk().endCommandBuffer(command) != VK_SUCCESS) {
            throw std::runtime_error("P1l-B0 command end failed");
        }
        auto submit = detail::make_vk_info<VkSubmitInfo>(
            VK_STRUCTURE_TYPE_SUBMIT_INFO);
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command;
        if (impl.context.vk().queueSubmit(
                impl.context.queue(), 1, &submit, impl.fence) != VK_SUCCESS ||
            impl.context.vk().waitForFences(
                1, &impl.fence, VK_TRUE, UINT64_MAX) != VK_SUCCESS) {
            throw std::runtime_error("P1l-B0 GPU submit/fence failed");
        }

        const auto download = [&](const B002Buffer& buffer, std::size_t length) {
            std::vector<std::uint32_t> values(length);
            impl.context.download_device_buffer(
                buffer, values.data(), length * sizeof(std::uint32_t));
            return values;
        };
        const auto primary_raw = download(primary_counts, std::size_t(pixels) * 4U);
        const auto shadow_raw = download(shadow_counts, std::size_t(pixels) * 8U);
        const auto secondary_raw = download(secondary_counts, std::size_t(rays) * 8U);

        // An instrumented shader is valid only if its output is BYTE IDENTICAL
        // to the separately rendered, uninstrumented GPU output. Neither
        // diagnostic can alter the accepted renderer storage or final image.
        const auto verify_equal = [&](const B002Buffer& accepted,
                                      const B002Buffer& instrumented,
                                      VkDeviceSize size, const char* label) {
            std::vector<std::uint8_t> left(static_cast<std::size_t>(size));
            std::vector<std::uint8_t> right(static_cast<std::size_t>(size));
            impl.context.download_device_buffer(accepted, left.data(), size);
            impl.context.download_device_buffer(instrumented, right.data(), size);
            if (left != right) {
                throw std::runtime_error(
                    std::string("P1l-B0 instrumented output divergence: ") + label);
            }
        };
        verify_equal(impl.primary_hits, primary_output,
                     VkDeviceSize(pixels) * sizeof(GpuHit), "primary");
        verify_equal(impl.image, shadow_output,
                     VkDeviceSize(pixels) * 4U * sizeof(float), "composite");
        verify_equal(impl.hits, secondary_output,
                     VkDeviceSize(rays) * sizeof(GpuHit), "secondary");

        for (std::uint32_t metric = 0U; metric < 4U; ++metric) {
            report.primary[metric] =
                p1l_b0_metric(primary_raw, pixels, 1U, 0U, metric);
        }
        for (std::uint32_t metric = 0U; metric < 8U; ++metric) {
            report.shadow[metric] = p1l_b0_metric(
                shadow_raw, pixels, 2U, metric / 4U, metric % 4U);
            report.secondary[metric] = p1l_b0_metric(
                secondary_raw, rays, 2U, metric / 4U, metric % 4U);
        }
        // Pipelines/descriptors must die before their B002Buffer allocations.
        secondary.reset();
        shadow.reset();
        primary.reset();
    } catch (...) {
        cleanup();
        throw;
    }
    cleanup();
    return report;
}

} // namespace phos::gi::research::integration

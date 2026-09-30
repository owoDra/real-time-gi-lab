#include "baseline/lane_b_traversal/b002_compute.hpp"
#include "baseline/lane_b_traversal/b002_hwrt.hpp"
#include "baseline/lane_b_traversal/b002_scene.hpp"
#include "baseline/lane_b_traversal/b003_micro_bvh8.hpp"
#include "baseline/lane_b_traversal/b003_quantized_bvh8.hpp"
#include "baseline/lane_b_traversal/gpu_software_bvh.hpp"
#include "baseline/lane_b_traversal/lane_a_stream_v1.hpp"
#include "baseline/lane_b_traversal/hierarchical_stratabrick.hpp"
#include "f003_transient_lbvh.hpp"
#include "i001_compute.hpp"
#include "../j003_reference.hpp"
#include "../j003_snapshot.hpp"
#include "vk_init.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace lane_b = phos::gi::research::lane_b;
namespace lane_f = phos::gi::research::lane_f;
namespace lane_i = phos::gi::research::integration;
namespace lane_j = phos::gi::research::lane_j;

namespace {

using Clock = std::chrono::steady_clock;
using lane_b::B002Buffer;
using lane_b::B002HwrtTraversal;
using lane_b::B002VulkanContext;
using lane_b::GpuHit;
using lane_b::GpuRay;
using lane_b::GpuTriangle;
using lane_b::HierarchicalTraversalPush;
using lane_b::SoftwareTraversalPush;
using lane_i::I001Binding;
using lane_i::I001ComputeStage;

constexpr std::uint32_t kQueryCount = 20U;
constexpr std::uint32_t kStorageMaxProbe = 128U;

enum class Track {
    Primary,
    Software,
};

enum class DynamicKind {
    Hwrt,
    B003,
    Lbvh,
    Vanilla,
};

struct Options {
    std::filesystem::path scene{
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"};
    std::filesystem::path profile_dir{};
    std::filesystem::path producer_stream{};
    Track track{Track::Primary};
    std::string comparison{"candidate"};
    std::string start_order{"AB"};
    std::uint32_t warmup_pairs{4U};
    std::uint32_t measured_pairs{12U};
    std::uint32_t batch_transitions{16U};
    bool validation{};
    bool validation_only{};
    std::string validation_variant{"candidate"};
    std::uint32_t validation_rays{4096U};
};

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

struct alignas(16) RadianceParams {
    float camera_pos_near[4]{};
    float camera_right_tan_x[4]{};
    float camera_up_tan_y[4]{};
    float camera_forward_far[4]{};
    float scene_origin_spacing[4]{};
    float light_pos_interval[4]{};
    std::uint32_t counts[4]{};
    std::uint32_t limits[4]{};
};
static_assert(sizeof(RadianceParams) == 128);

struct TransitionResult {
    double geometry_prepare_wall_us{};
    double allocation_reallocation_wall_us{};
    double geometry_upload_gpu_us{};
    double candidate_preprocess_gpu_us{};
    double build_rebuild_gpu_us{};
    double refit_gpu_us{};
    double compaction_gpu_us{};
    double instance_tlas_update_gpu_us{};
    double traversal_gpu_us{};
    double synchronization_wall_us{};
    double merge_gpu_us{};
    double storage_gpu_us{};
    double resolve_gpu_us{};
    double complete_gpu_us{};
    double complete_wall_us{};
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t scratch_bytes{};
    std::size_t old_new_overlap_bytes{};
    std::size_t resident_bytes{};
    std::size_t true_peak_resident_bytes{};
    std::size_t storage_failures{};
};

struct BatchResult {
    double geometry_prepare_wall_us{};
    double allocation_reallocation_wall_us{};
    double geometry_upload_gpu_us{};
    double candidate_preprocess_gpu_us{};
    double build_rebuild_gpu_us{};
    double refit_gpu_us{};
    double compaction_gpu_us{};
    double instance_tlas_update_gpu_us{};
    double traversal_gpu_us{};
    double synchronization_wall_us{};
    double merge_gpu_us{};
    double storage_gpu_us{};
    double resolve_gpu_us{};
    double complete_gpu_us{};
    double complete_wall_us{};
    std::size_t max_persistent_bytes{};
    std::size_t max_transient_bytes{};
    std::size_t max_scratch_bytes{};
    std::size_t max_old_new_overlap_bytes{};
    std::size_t max_resident_bytes{};
    std::size_t max_true_peak_resident_bytes{};
    std::size_t storage_failures{};
};

struct ValidationResult {
    std::uint64_t hit_mismatches{};
    std::uint64_t nearest_hit_tie_mismatches{};
    std::uint64_t traversal_runtime_errors{};
    std::uint64_t storage_failures{};
    std::uint64_t immutable_owner_mutations{};
    std::uint64_t resolved_digest{1469598103934665603ULL};
};

[[noreturn]] void fail(const std::string& message) {
    throw std::runtime_error(message);
}

[[nodiscard]] std::uint32_t groups(std::uint32_t count) noexcept {
    return (count + 63U) / 64U;
}

[[nodiscard]] double elapsed_us(Clock::time_point start) {
    return std::chrono::duration<double, std::micro>(
        Clock::now() - start).count();
}

void hash_bytes(
    std::uint64_t& hash,
    const void* data,
    std::size_t bytes) noexcept {
    const auto* ptr =
        static_cast<const unsigned char*>(data);
    for (std::size_t index = 0U;
         index < bytes;
         ++index) {
        hash ^= ptr[index];
        hash *= 1099511628211ULL;
    }
}

[[nodiscard]] std::size_t next_power_of_two(std::size_t value) {
    if (value <= 1U) return 1U;
    --value;
    for (std::size_t shift = 1U;
         shift < std::numeric_limits<std::size_t>::digits;
         shift <<= 1U) {
        value |= value >> shift;
    }
    return value + 1U;
}

[[nodiscard]] Track parse_track(const std::string& value) {
    if (value == "primary") return Track::Primary;
    if (value == "software") return Track::Software;
    fail("unknown J004 track: " + value);
}

[[nodiscard]] const char* track_name(Track value) noexcept {
    return value == Track::Primary ? "primary" : "software";
}

[[nodiscard]] const char* kind_name(DynamicKind value) noexcept {
    switch (value) {
    case DynamicKind::Hwrt:
        return "lane-e-object-local-hwrt-rebuild";
    case DynamicKind::B003:
        return "lane-e-object-local-software-b003-rebuild";
    case DynamicKind::Lbvh:
        return "hardened-transient-lbvh";
    case DynamicKind::Vanilla:
        return "vanilla-software-bvh-rebuild";
    }
    return "unknown";
}

[[nodiscard]] DynamicKind control_kind(Track track) noexcept {
    return track == Track::Primary
        ? DynamicKind::Hwrt
        : DynamicKind::B003;
}

Options parse_options(int argc, char** argv) {
    Options options;
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        const auto value = [&](const char* name) -> std::string {
            if (index + 1 >= argc) {
                fail(std::string(name) + " requires a value");
            }
            return argv[++index];
        };

        if (argument == "--scene") {
            options.scene = value("--scene");
        } else if (argument == "--profile-dir") {
            options.profile_dir = value("--profile-dir");
        } else if (argument == "--producer-stream") {
            options.producer_stream = value("--producer-stream");
        } else if (argument == "--track") {
            options.track = parse_track(value("--track"));
        } else if (argument == "--comparison") {
            options.comparison = value("--comparison");
        } else if (argument == "--start-order") {
            options.start_order = value("--start-order");
        } else if (argument == "--warmup-pairs") {
            options.warmup_pairs =
                static_cast<std::uint32_t>(
                    std::stoul(value("--warmup-pairs")));
        } else if (argument == "--measured-pairs") {
            options.measured_pairs =
                static_cast<std::uint32_t>(
                    std::stoul(value("--measured-pairs")));
        } else if (argument == "--batch-transitions") {
            options.batch_transitions =
                static_cast<std::uint32_t>(
                    std::stoul(value("--batch-transitions")));
        } else if (argument == "--validation") {
            options.validation = true;
        } else if (argument == "--validation-only") {
            options.validation_only = true;
        } else if (argument == "--validation-variant") {
            options.validation_variant =
                value("--validation-variant");
        } else if (argument == "--validation-rays") {
            options.validation_rays =
                static_cast<std::uint32_t>(
                    std::stoul(value("--validation-rays")));
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-j-j004-formal-process "
                   "--profile-dir path --producer-stream path "
                   "[--scene path] --track primary|software "
                   "[--comparison control|candidate|accounting] "
                   "[--start-order AB|BA] "
                   "[--warmup-pairs 4] [--measured-pairs 12] "
                   "[--batch-transitions 16] "
                   "[--validation-only --validation-variant "
                   "control|candidate|accounting --validation]\n";
            std::exit(0);
        } else {
            fail("unknown J004 formal option: " + argument);
        }
    }

    if (options.profile_dir.empty() ||
        options.producer_stream.empty()) {
        fail("J004 requires --profile-dir and --producer-stream");
    }
    if (options.start_order != "AB" &&
        options.start_order != "BA") {
        fail("J004 start order must be AB or BA");
    }
    if (options.comparison != "control" &&
        options.comparison != "candidate" &&
        options.comparison != "accounting") {
        fail("J004 comparison must be control, candidate, or accounting");
    }
    if (options.comparison == "accounting" &&
        options.track != Track::Software) {
        fail("J004 accounting comparison is software-track only");
    }
    if (options.batch_transitions != 16U) {
        fail("J004 v1 requires exactly 16 transitions per timed sample");
    }
    if (options.warmup_pairs != 4U ||
        options.measured_pairs != 12U) {
        fail("J004 v1 requires 4 warmup and 12 measured pairs");
    }
    return options;
}

[[nodiscard]] std::vector<lane_b::Triangle> to_lane_b(
    const std::vector<lane_j::Triangle>& input) {
    std::vector<lane_b::Triangle> output;
    output.reserve(input.size());
    for (const auto& triangle : input) {
        output.push_back({
            {triangle.v0.x, triangle.v0.y, triangle.v0.z},
            {triangle.v1.x, triangle.v1.y, triangle.v1.z},
            {triangle.v2.x, triangle.v2.y, triangle.v2.z},
            triangle.primitive_id,
            triangle.material_id,
            triangle.instance_id,
            triangle.two_sided,
        });
    }
    return output;
}

[[nodiscard]] lane_j::GpuHit to_lane_j_gpu_hit(
    const lane_b::GpuHit& input) {
    lane_j::GpuHit output{};
    output.t_normal = {
        input.normal_t[3],
        input.normal_t[0],
        input.normal_t[1],
        input.normal_t[2],
    };
    output.ids = {
        input.metadata[0],
        input.metadata[1],
        input.metadata[2],
        input.metadata[3],
    };
    return output;
}

[[nodiscard]] lane_j::Hit to_lane_j_hit(
    const lane_b::Hit& input) {
    lane_j::Hit output{};
    output.hit = input.hit;
    output.t = input.t;
    output.normal = {
        input.normal.x,
        input.normal.y,
        input.normal.z,
    };
    output.primitive_id = input.primitive_id;
    output.material_id = input.material_id;
    output.instance_id = input.instance_id;
    return output;
}

[[nodiscard]] lane_b::Hit merge_cpu_hits(
    const lane_b::Hit& static_hit,
    const lane_b::Hit& dynamic_hit) {
    if (lane_b::prefer_hit(dynamic_hit, static_hit)) {
        return dynamic_hit;
    }
    return static_hit;
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

[[nodiscard]] lane_b::Vec3 lbvh_origin(
    const std::vector<lane_b::Triangle>& triangles,
    float page_extent) {
    lane_b::Aabb bounds{};
    for (const auto& triangle : triangles) {
        bounds = lane_b::merge(
            bounds,
            lane_b::triangle_bounds(triangle));
    }
    return {
        bounds.min.x - page_extent * 2.0F,
        bounds.min.y - page_extent * 2.0F,
        bounds.min.z - page_extent * 2.0F,
    };
}

class QuantizedState {
public:
    QuantizedState(
        B002VulkanContext& context,
        std::vector<lane_b::Triangle> triangles,
        float segment_size)
        : context_(context),
          triangles_(std::move(triangles)),
          segment_size_(segment_size) {
        lane_b::HierarchicalStrataBrick hierarchy(
            triangles_,
            segment_size_);
        const auto flat = hierarchy.flatten();
        const auto wide =
            lane_b::make_b003_wide_micro_payload(flat);
        payload_ =
            lane_b::make_b003_quantized_micro_payload(wide);

        const auto gpu = gpu_triangles(triangles_);
        triangle_ = context_.upload_device_buffer(
            gpu.data(),
            gpu.size() * sizeof(GpuTriangle),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        nodes_ = context_.upload_device_buffer(
            payload_.nodes.data(),
            payload_.nodes.size() *
                sizeof(lane_b::B003GpuQuantNode),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        order_ = context_.upload_device_buffer(
            payload_.ordered_primitives.data(),
            payload_.ordered_primitives.size() *
                sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        hash_ = context_.upload_device_buffer(
            payload_.hash_table.data(),
            payload_.hash_table.size() *
                sizeof(lane_b::GpuSegmentHashEntry),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    }

    ~QuantizedState() {
        context_.destroy_buffer(hash_);
        context_.destroy_buffer(order_);
        context_.destroy_buffer(nodes_);
        context_.destroy_buffer(triangle_);
    }

    QuantizedState(const QuantizedState&) = delete;
    QuantizedState& operator=(const QuantizedState&) = delete;

    [[nodiscard]] const B002Buffer& triangle() const noexcept {
        return triangle_;
    }
    [[nodiscard]] const B002Buffer& nodes() const noexcept {
        return nodes_;
    }
    [[nodiscard]] const B002Buffer& order() const noexcept {
        return order_;
    }
    [[nodiscard]] const B002Buffer& hash() const noexcept {
        return hash_;
    }

    [[nodiscard]] std::size_t allocation_bytes() const noexcept {
        return static_cast<std::size_t>(
            triangle_.allocation_size +
            nodes_.allocation_size +
            order_.allocation_size +
            hash_.allocation_size);
    }

    [[nodiscard]] HierarchicalTraversalPush push(
        std::uint32_t max_rays) const {
        HierarchicalTraversalPush output{};
        output.values[0] = max_rays;
        output.values[1] = payload_.hash_mask;
        output.values[2] = payload_.hash_max_probe;
        const auto max_steps =
            std::max<std::uint64_t>(
                64U,
                std::uint64_t(payload_.segment_count) *
                    16U + 64U);
        output.values[3] =
            static_cast<std::uint32_t>(
                std::min<std::uint64_t>(
                    max_steps,
                    std::numeric_limits<std::uint32_t>::max()));
        output.occupied_min_segment_size[0] =
            payload_.occupied_bounds.min.x;
        output.occupied_min_segment_size[1] =
            payload_.occupied_bounds.min.y;
        output.occupied_min_segment_size[2] =
            payload_.occupied_bounds.min.z;
        output.occupied_min_segment_size[3] =
            segment_size_;
        output.occupied_max_pad[0] =
            payload_.occupied_bounds.max.x;
        output.occupied_max_pad[1] =
            payload_.occupied_bounds.max.y;
        output.occupied_max_pad[2] =
            payload_.occupied_bounds.max.z;
        return output;
    }

private:
    B002VulkanContext& context_;
    std::vector<lane_b::Triangle> triangles_;
    float segment_size_{};
    lane_b::B003QuantizedMicroPayload payload_;
    B002Buffer triangle_{};
    B002Buffer nodes_{};
    B002Buffer order_{};
    B002Buffer hash_{};
};

class VanillaState {
public:
    VanillaState(
        B002VulkanContext& context,
        std::vector<lane_b::Triangle> triangles)
        : context_(context),
          triangles_(std::move(triangles)),
          cpu_(triangles_) {
        const auto gpu = gpu_triangles(triangles_);
        const auto nodes = cpu_.gpu_nodes();

        triangle_ = context_.upload_device_buffer(
            gpu.data(),
            gpu.size() * sizeof(GpuTriangle),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        nodes_ = context_.upload_device_buffer(
            nodes.data(),
            nodes.size() *
                sizeof(lane_b::GpuBvhNode),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        order_ = context_.upload_device_buffer(
            cpu_.ordered_primitives().data(),
            cpu_.ordered_primitives().size() *
                sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    }

    ~VanillaState() {
        context_.destroy_buffer(order_);
        context_.destroy_buffer(nodes_);
        context_.destroy_buffer(triangle_);
    }

    VanillaState(const VanillaState&) = delete;
    VanillaState& operator=(const VanillaState&) = delete;

    [[nodiscard]] const B002Buffer& triangle() const noexcept {
        return triangle_;
    }
    [[nodiscard]] const B002Buffer& nodes() const noexcept {
        return nodes_;
    }
    [[nodiscard]] const B002Buffer& order() const noexcept {
        return order_;
    }
    [[nodiscard]] std::uint32_t root() const noexcept {
        return cpu_.root();
    }
    [[nodiscard]] std::size_t allocation_bytes() const noexcept {
        return static_cast<std::size_t>(
            triangle_.allocation_size +
            nodes_.allocation_size +
            order_.allocation_size);
    }

private:
    B002VulkanContext& context_;
    std::vector<lane_b::Triangle> triangles_;
    lane_b::GpuSoftwareBvhData cpu_;
    B002Buffer triangle_{};
    B002Buffer nodes_{};
    B002Buffer order_{};
};

class FormalRuntime {
public:
    FormalRuntime(
        B002VulkanContext& context,
        const Options& options,
        DynamicKind dynamic_kind)
        : context_(context),
          options_(options),
          dynamic_kind_(dynamic_kind) {
        load_inputs();
        create_common_buffers();
        create_static_backend();
        create_dynamic_backend(0U);
        create_stages();
        create_command_resources();

        // Setup transfers must never leak into the first recurrent sample.
        (void)context_.consume_transfer_gpu_us();
        context_.reset_allocation_peak();
    }

    ~FormalRuntime() {
        dynamic_stage_.reset();
        static_stage_.reset();
        hit_merge_stage_.reset();
        radiance_stage_.reset();
        merge_stage_.reset();
        storage_update_stage_.reset();
        invalidation_stage_.reset();
        resolve_stage_.reset();

        dynamic_hwrt_.reset();
        dynamic_quant_.reset();
        dynamic_lbvh_.reset();
        dynamic_vanilla_.reset();
        static_hwrt_.reset();
        static_quant_.reset();
        static_cpu_.reset();

        if (fence_ != VK_NULL_HANDLE) {
            context_.vk().destroyFence(fence_, nullptr);
        }
        if (query_pool_ != VK_NULL_HANDLE) {
            context_.vk().destroyQueryPool(query_pool_, nullptr);
        }
        if (command_pool_ != VK_NULL_HANDLE) {
            context_.vk().destroyCommandPool(command_pool_, nullptr);
        }

        context_.destroy_buffer(storage_stats_);
        context_.destroy_buffer(storage_slots_);
        context_.destroy_buffer(uniform_);
        context_.destroy_buffer(resolved_);
        context_.destroy_buffer(accum_);
        context_.destroy_buffer(contributions_);
        context_.destroy_buffer(hits_);
        context_.destroy_buffer(dynamic_hits_);
        context_.destroy_buffer(static_hits_);
        context_.destroy_buffer(counters_);
        context_.destroy_buffer(rays_);
        context_.destroy_buffer(work_);
    }

    FormalRuntime(const FormalRuntime&) = delete;
    FormalRuntime& operator=(const FormalRuntime&) = delete;

    [[nodiscard]] BatchResult run_batch(
        std::uint32_t transition_count) {
        BatchResult batch{};
        for (std::uint32_t offset = 0U;
             offset < transition_count;
             ++offset) {
            const auto next_step =
                static_cast<std::uint32_t>(
                    (current_step_ + 1U) % snapshots_.size());
            const auto result =
                run_transition(next_step);
            batch.geometry_prepare_wall_us +=
                result.geometry_prepare_wall_us;
            batch.allocation_reallocation_wall_us +=
                result.allocation_reallocation_wall_us;
            batch.geometry_upload_gpu_us +=
                result.geometry_upload_gpu_us;
            batch.candidate_preprocess_gpu_us +=
                result.candidate_preprocess_gpu_us;
            batch.build_rebuild_gpu_us +=
                result.build_rebuild_gpu_us;
            batch.refit_gpu_us +=
                result.refit_gpu_us;
            batch.compaction_gpu_us +=
                result.compaction_gpu_us;
            batch.instance_tlas_update_gpu_us +=
                result.instance_tlas_update_gpu_us;
            batch.traversal_gpu_us +=
                result.traversal_gpu_us;
            batch.synchronization_wall_us +=
                result.synchronization_wall_us;
            batch.merge_gpu_us +=
                result.merge_gpu_us;
            batch.storage_gpu_us +=
                result.storage_gpu_us;
            batch.resolve_gpu_us +=
                result.resolve_gpu_us;
            batch.complete_gpu_us +=
                result.complete_gpu_us;
            batch.complete_wall_us +=
                result.complete_wall_us;
            if (result.resident_bytes >
                batch.max_resident_bytes) {
                // Preserve one real lifetime classification. Independent
                // per-class maxima could synthesize a memory state that never
                // existed during the batch.
                batch.max_resident_bytes =
                    result.resident_bytes;
                batch.max_persistent_bytes =
                    result.persistent_bytes;
                batch.max_transient_bytes =
                    result.transient_bytes;
                batch.max_scratch_bytes =
                    result.scratch_bytes;
            }
            batch.max_old_new_overlap_bytes =
                std::max(
                    batch.max_old_new_overlap_bytes,
                    result.old_new_overlap_bytes);
            batch.max_true_peak_resident_bytes =
                std::max(
                    batch.max_true_peak_resident_bytes,
                    result.true_peak_resident_bytes);
            batch.storage_failures +=
                result.storage_failures;
        }
        if (transition_count % snapshots_.size() == 0U &&
            current_step_ != 0U) {
            fail("J004 batch did not return to frozen step-00");
        }
        return batch;
    }

    [[nodiscard]] ValidationResult validate_cycle(
        std::uint32_t validation_rays) {
        ValidationResult total{};
        const auto static_before = capture_static_buffers();
        for (std::uint32_t offset = 0U;
             offset < snapshots_.size();
             ++offset) {
            const auto next_step =
                static_cast<std::uint32_t>(
                    (current_step_ + 1U) % snapshots_.size());
            const auto result =
                run_transition(next_step);
            total.storage_failures +=
                result.storage_failures;

            const auto count =
                validation_rays == 0U
                    ? replay_rays_.size()
                    : std::min<std::size_t>(
                        validation_rays,
                        replay_rays_.size());
            std::vector<GpuHit> gpu_hits(count);
            context_.download_device_buffer(
                hits_,
                gpu_hits.data(),
                count * sizeof(GpuHit));

            std::vector<float> resolved(
                producer_.header.output_count);
            context_.download_device_buffer(
                resolved_,
                resolved.data(),
                resolved.size() * sizeof(float));
            hash_bytes(
                total.resolved_digest,
                resolved.data(),
                resolved.size() * sizeof(float));

            lane_b::GpuSoftwareBvhData dynamic_cpu(
                snapshots_.at(current_step_));
            for (std::size_t index = 0U;
                 index < count;
                 ++index) {
                const auto static_hit =
                    static_cpu_->trace(replay_rays_[index]);
                const auto dynamic_hit =
                    dynamic_cpu.trace(replay_rays_[index]);
                const auto expected =
                    to_lane_j_hit(
                        merge_cpu_hits(
                            static_hit,
                            dynamic_hit));
                const auto actual =
                    to_lane_j_gpu_hit(gpu_hits[index]);
                if (gpu_hits[index].metadata[3] > 1U) {
                    ++total.traversal_runtime_errors;
                }
                if (!lane_j::equivalent_hit(
                        expected,
                        actual)) {
                    ++total.hit_mismatches;
                    const bool actual_hit =
                        actual.ids[3] != 0U;
                    if (expected.hit && actual_hit &&
                        expected.primitive_id !=
                            actual.ids[0]) {
                        const auto tolerance =
                            std::max(
                                lane_j::kHitAbsTol,
                                std::abs(expected.t) *
                                    lane_j::kHitRelTol);
                        if (std::abs(
                                expected.t -
                                actual.t_normal[0]) <=
                            tolerance) {
                            ++total.
                                nearest_hit_tie_mismatches;
                        }
                    }
                }
            }
        }
        if (current_step_ != 0U) {
            fail("J004 validation cycle did not return to step-00");
        }

        const auto static_after = capture_static_buffers();
        if (static_before.size() != static_after.size()) {
            ++total.immutable_owner_mutations;
        } else {
            for (std::size_t index = 0U;
                 index < static_before.size();
                 ++index) {
                if (static_before[index] != static_after[index]) {
                    ++total.immutable_owner_mutations;
                }
            }
        }

        // Validation readbacks are diagnostics and must not contaminate a
        // later recurrent GPU sample if the caller reuses this instance.
        (void)context_.consume_transfer_gpu_us();
        return total;
    }

private:
    [[nodiscard]] std::vector<std::vector<std::byte>>
    capture_static_buffers() {
        std::vector<const B002Buffer*> buffers;
        if (options_.track == Track::Primary) {
            buffers.push_back(
                &static_hwrt_->triangle_buffer());
        } else {
            buffers.push_back(
                &static_quant_->triangle());
            buffers.push_back(
                &static_quant_->nodes());
            buffers.push_back(
                &static_quant_->order());
            buffers.push_back(
                &static_quant_->hash());
        }

        std::vector<std::vector<std::byte>> snapshots;
        snapshots.reserve(buffers.size());
        for (const auto* buffer : buffers) {
            if (buffer == nullptr ||
                buffer->buffer == VK_NULL_HANDLE ||
                buffer->size == 0U) {
                fail("J004 static ownership buffer is invalid");
            }
            std::vector<std::byte> bytes(
                static_cast<std::size_t>(buffer->size));
            context_.download_device_buffer(
                *buffer,
                bytes.data(),
                buffer->size);
            snapshots.push_back(std::move(bytes));
        }
        return snapshots;
    }
    void load_inputs() {
        for (std::uint32_t step = 0U;
             step < 8U;
             ++step) {
            std::ostringstream name;
            name << "step-" << std::setw(2)
                 << std::setfill('0')
                 << step << ".bin";
            const auto path =
                options_.profile_dir / name.str();
            if (!std::filesystem::is_regular_file(path)) {
                fail(
                    "missing J002 snapshot: " +
                    path.string());
            }
            snapshots_.push_back(
                to_lane_b(
                    lane_j::load_j002_snapshot(path)));
        }
        if (snapshots_.size() != 8U ||
            snapshots_.front().empty()) {
            fail("J004 requires eight non-empty J002 snapshots");
        }
        lbvh_capacity_count_ = 0U;
        for (const auto& snapshot : snapshots_) {
            lbvh_capacity_count_ = std::max(
                lbvh_capacity_count_,
                static_cast<std::uint32_t>(snapshot.size()));
        }
        if (lbvh_capacity_count_ < 2U) {
            fail("J004 frozen LBVH capacity is invalid");
        }

        dynamic_instance_id_ =
            snapshots_.front().front().instance_id;
        for (const auto& snapshot : snapshots_) {
            for (const auto& triangle : snapshot) {
                if (triangle.instance_id !=
                    dynamic_instance_id_) {
                    fail(
                        "J004 snapshot spans multiple "
                        "dynamic instance ids");
                }
            }
        }

        full_scene_ =
            lane_b::load_b002_scene(options_.scene);
        segment_size_ =
            lane_b::b002_segment_size(full_scene_);
        for (const auto& triangle :
             full_scene_.triangles) {
            if (triangle.instance_id !=
                dynamic_instance_id_) {
                static_triangles_.push_back(triangle);
            }
        }
        if (static_triangles_.empty()) {
            fail("J004 static-world partition is empty");
        }
        static_cpu_ =
            std::make_unique<lane_b::GpuSoftwareBvhData>(
                static_triangles_);

        producer_ =
            lane_b::load_lane_a_stream_v1(
                options_.producer_stream);
        replay_rays_ =
            lane_b::lane_a_replay_rays(producer_);
        if (producer_.items.empty() ||
            replay_rays_.size() !=
                producer_.items.size() ||
            producer_.header.output_count == 0U) {
            fail("J004 accepted A001 replay stream is empty");
        }
    }

    void create_common_buffers() {
        const auto storage =
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;

        work_ = context_.upload_device_buffer(
            producer_.items.data(),
            producer_.items.size() *
                sizeof(lane_b::LaneAWorkItemV1),
            storage);

        std::vector<GpuRay> gpu_rays;
        gpu_rays.reserve(replay_rays_.size());
        for (const auto& ray : replay_rays_) {
            gpu_rays.push_back(
                lane_b::to_gpu_ray(ray));
        }
        rays_ = context_.upload_device_buffer(
            gpu_rays.data(),
            gpu_rays.size() *
                sizeof(GpuRay),
            storage);

        const std::array<std::uint32_t, 6> counters{
            producer_.header.item_count,
            producer_.header.output_count,
            0U,
            0U,
            producer_.header.item_count,
            producer_.header.output_count,
        };
        counters_ = context_.upload_device_buffer(
            counters.data(),
            sizeof(counters),
            storage);

        const auto hit_bytes =
            VkDeviceSize(producer_.header.item_count) *
            sizeof(GpuHit);
        static_hits_ =
            context_.create_device_buffer(
                hit_bytes, storage);
        dynamic_hits_ =
            context_.create_device_buffer(
                hit_bytes, storage);
        hits_ =
            context_.create_device_buffer(
                hit_bytes, storage);

        contributions_ =
            context_.create_device_buffer(
                VkDeviceSize(
                    producer_.header.item_count) *
                    sizeof(std::uint32_t) * 2U,
                storage);
        accum_ =
            context_.create_device_buffer(
                VkDeviceSize(
                    producer_.header.output_count) *
                    sizeof(std::uint32_t) * 2U,
                storage);
        resolved_ =
            context_.create_device_buffer(
                VkDeviceSize(
                    producer_.header.output_count) *
                    sizeof(float),
                storage);

        const auto storage_capacity =
            next_power_of_two(
                std::max<std::size_t>(
                    2U,
                    std::size_t(
                        producer_.header.output_count) *
                        2U));
        if (storage_capacity >
            (std::numeric_limits<std::uint32_t>::max)()) {
            fail("J004 storage capacity exceeds uint32");
        }
        storage_capacity_ =
            static_cast<std::uint32_t>(
                storage_capacity);

        struct Slot {
            std::int32_t key[4]{};
            std::uint32_t data[4]{};
        };
        static_assert(sizeof(Slot) == 32);
        std::vector<Slot> slots(storage_capacity_);
        storage_slots_ =
            context_.upload_device_buffer(
                slots.data(),
                slots.size() * sizeof(Slot),
                storage);
        const std::array<std::uint32_t, 4>
            storage_stats{};
        storage_stats_ =
            context_.upload_device_buffer(
                storage_stats.data(),
                sizeof(storage_stats),
                storage);

        RadianceParams params{};
        const auto center = lane_b::center(
            full_scene_.bounds);
        const float diagonal =
            std::max(full_scene_.diagonal, 1.0F);
        params.light_pos_interval[0] =
            center.x + diagonal * 0.15F;
        params.light_pos_interval[1] =
            center.y + diagonal * 0.35F;
        params.light_pos_interval[2] =
            center.z + diagonal * 0.10F;
        params.light_pos_interval[3] =
            diagonal / 128.0F;
        params.counts[3] =
            producer_.header.cascade_count;
        params.limits[0] =
            producer_.header.rays_per_probe;
        params.limits[1] =
            producer_.header.item_count;
        params.limits[2] =
            producer_.header.output_count;
        uniform_ =
            context_.create_host_buffer(
                sizeof(params),
                VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT);
        std::memcpy(
            uniform_.mapped,
            &params,
            sizeof(params));
    }

    void create_static_backend() {
        if (options_.track == Track::Primary) {
            static_hwrt_ =
                std::make_unique<B002HwrtTraversal>(
                    context_,
                    static_triangles_,
                    std::string{},
                    false);
        } else {
            static_quant_ =
                std::make_unique<QuantizedState>(
                    context_,
                    static_triangles_,
                    segment_size_);
        }
    }

    void create_dynamic_backend(
        std::uint32_t step) {
        const auto& triangles =
            snapshots_.at(step);
        if (dynamic_kind_ ==
            DynamicKind::Hwrt) {
            dynamic_hwrt_ =
                std::make_unique<B002HwrtTraversal>(
                    context_,
                    triangles,
                    std::string{},
                    false);
        } else if (dynamic_kind_ ==
                   DynamicKind::B003) {
            dynamic_quant_ =
                std::make_unique<QuantizedState>(
                    context_,
                    triangles,
                    segment_size_);
        } else if (dynamic_kind_ ==
                   DynamicKind::Lbvh) {
            if (!dynamic_lbvh_) {
                std::vector<GpuTriangle> capacity_seed(
                    lbvh_capacity_count_);
                dynamic_lbvh_ =
                    std::make_unique<
                        lane_f::F003TransientLbvh>(
                        context_,
                        capacity_seed,
                        lbvh_origin(
                            triangles,
                            segment_size_),
                        segment_size_,
                        shader_path(
                            "j004_f003_lbvh_builder.spv"));
            }
            const auto gpu = gpu_triangles(triangles);
            (void)dynamic_lbvh_->update_template(gpu);
        } else {
            dynamic_vanilla_ =
                std::make_unique<VanillaState>(
                    context_,
                    triangles);
        }
    }

    [[nodiscard]] std::filesystem::path shader_path(
        const char* name) const {
        return std::filesystem::path(
            PHOS_GI_LANE_J_FORMAL_SHADER_DIR) /
            name;
    }

    void create_stages() {
        if (options_.track == Track::Primary) {
            const std::array<I001Binding, 5>
                bindings{{
                    {0,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &rays_},
                    {1,
                     VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,
                     nullptr,
                     static_hwrt_->top_level()},
                    {2,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &static_hwrt_->triangle_buffer()},
                    {3,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &static_hits_},
                    {4,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &counters_},
                }};
            static_stage_ =
                std::make_unique<I001ComputeStage>(
                    context_,
                    shader_path(
                        "j004_i001_hwrt.spv")
                        .string(),
                    bindings,
                    sizeof(std::uint32_t));
        } else {
            const std::array<I001Binding, 7>
                bindings{{
                    {0,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &rays_},
                    {1,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &static_quant_->triangle()},
                    {2,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &static_quant_->nodes()},
                    {3,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &static_quant_->order()},
                    {4,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &static_quant_->hash()},
                    {5,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &static_hits_},
                    {6,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &counters_},
                }};
            static_stage_ =
                std::make_unique<I001ComputeStage>(
                    context_,
                    shader_path(
                        "j004_i001_quantized_bvh8.spv")
                        .string(),
                    bindings,
                    sizeof(HierarchicalTraversalPush));
        }

        create_dynamic_stage();

        const std::array<I001Binding, 4>
            merge_hit_bindings{{
                {0,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &static_hits_},
                {1,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &dynamic_hits_},
                {2,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &hits_},
                {3,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &counters_},
            }};
        hit_merge_stage_ =
            std::make_unique<I001ComputeStage>(
                context_,
                shader_path(
                    "j004_f003_hit_merge.spv")
                    .string(),
                merge_hit_bindings);

        const std::array<I001Binding, 5>
            radiance_bindings{{
                {0,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &counters_},
                {1,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &work_},
                {2,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &hits_},
                {3,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &contributions_},
                {4,
                 VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                 &uniform_},
            }};
        radiance_stage_ =
            std::make_unique<I001ComputeStage>(
                context_,
                shader_path(
                    "j004_i001_radiance.spv")
                    .string(),
                radiance_bindings);

        const std::array<I001Binding, 3>
            merge_bindings{{
                {2,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &counters_},
                {4,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &contributions_},
                {5,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &accum_},
            }};
        merge_stage_ =
            std::make_unique<I001ComputeStage>(
                context_,
                shader_path(
                    "j004_merge.spv")
                    .string(),
                merge_bindings);

        const std::array<I001Binding, 5>
            storage_bindings{{
                {0,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &counters_},
                {1,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &work_},
                {2,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &accum_},
                {3,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &storage_slots_},
                {4,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &storage_stats_},
            }};
        storage_update_stage_ =
            std::make_unique<I001ComputeStage>(
                context_,
                shader_path(
                    "j004_i001_storage_update.spv")
                    .string(),
                storage_bindings,
                sizeof(StoragePush));

        const std::array<I001Binding, 2>
            invalidation_bindings{{
                {0,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &storage_slots_},
                {1,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &storage_stats_},
            }};
        invalidation_stage_ =
            std::make_unique<I001ComputeStage>(
                context_,
                shader_path(
                    "j004_i001_storage_invalidate.spv")
                    .string(),
                invalidation_bindings,
                sizeof(InvalidationPush));

        const std::array<I001Binding, 4>
            resolve_bindings{{
                {0,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &counters_},
                {1,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &work_},
                {2,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &storage_slots_},
                {3,
                 VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                 &resolved_},
            }};
        resolve_stage_ =
            std::make_unique<I001ComputeStage>(
                context_,
                shader_path(
                    "j004_i001_storage_resolve.spv")
                    .string(),
                resolve_bindings,
                sizeof(StoragePush));
    }

    void create_dynamic_stage() {
        if (dynamic_kind_ ==
            DynamicKind::Hwrt) {
            const std::array<I001Binding, 5>
                bindings{{
                    {0,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &rays_},
                    {1,
                     VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,
                     nullptr,
                     dynamic_hwrt_->top_level()},
                    {2,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_hwrt_->triangle_buffer()},
                    {3,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_hits_},
                    {4,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &counters_},
                }};
            dynamic_stage_ =
                std::make_unique<I001ComputeStage>(
                    context_,
                    shader_path(
                        "j004_i001_hwrt.spv")
                        .string(),
                    bindings,
                    sizeof(std::uint32_t));
        } else if (dynamic_kind_ ==
                   DynamicKind::B003) {
            const std::array<I001Binding, 7>
                bindings{{
                    {0,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &rays_},
                    {1,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_quant_->triangle()},
                    {2,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_quant_->nodes()},
                    {3,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_quant_->order()},
                    {4,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_quant_->hash()},
                    {5,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_hits_},
                    {6,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &counters_},
                }};
            dynamic_stage_ =
                std::make_unique<I001ComputeStage>(
                    context_,
                    shader_path(
                        "j004_i001_quantized_bvh8.spv")
                        .string(),
                    bindings,
                    sizeof(HierarchicalTraversalPush));
        } else if (dynamic_kind_ ==
                   DynamicKind::Lbvh) {
            const std::array<I001Binding, 5>
                bindings{{
                    {0,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &rays_},
                    {1,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_lbvh_->triangles()},
                    {2,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_lbvh_->nodes()},
                    {3,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_hits_},
                    {4,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &counters_},
                }};
            dynamic_stage_ =
                std::make_unique<I001ComputeStage>(
                    context_,
                    shader_path(
                        "j004_f003_dynamic_traversal.spv")
                        .string(),
                    bindings);
        } else {
            const std::array<I001Binding, 6>
                bindings{{
                    {0,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &rays_},
                    {1,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_vanilla_->triangle()},
                    {2,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_vanilla_->nodes()},
                    {3,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_vanilla_->order()},
                    {4,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &dynamic_hits_},
                    {5,
                     VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                     &counters_},
                }};
            dynamic_stage_ =
                std::make_unique<I001ComputeStage>(
                    context_,
                    shader_path(
                        "j004_i001_software_bvh.spv")
                        .string(),
                    bindings,
                    sizeof(SoftwareTraversalPush));
        }
    }

    void rebind_dynamic_stage() {
        if (dynamic_kind_ ==
            DynamicKind::Hwrt) {
            dynamic_stage_->
                update_acceleration_binding(
                    1,
                    dynamic_hwrt_->top_level());
            dynamic_stage_->
                update_buffer_binding(
                    2,
                    dynamic_hwrt_->
                        triangle_buffer());
        } else if (dynamic_kind_ ==
                   DynamicKind::B003) {
            dynamic_stage_->
                update_buffer_binding(
                    1,
                    dynamic_quant_->triangle());
            dynamic_stage_->
                update_buffer_binding(
                    2,
                    dynamic_quant_->nodes());
            dynamic_stage_->
                update_buffer_binding(
                    3,
                    dynamic_quant_->order());
            dynamic_stage_->
                update_buffer_binding(
                    4,
                    dynamic_quant_->hash());
        } else if (dynamic_kind_ ==
                   DynamicKind::Lbvh) {
            dynamic_stage_->
                update_buffer_binding(
                    1,
                    dynamic_lbvh_->triangles());
            dynamic_stage_->
                update_buffer_binding(
                    2,
                    dynamic_lbvh_->nodes());
        } else {
            dynamic_stage_->
                update_buffer_binding(
                    1,
                    dynamic_vanilla_->triangle());
            dynamic_stage_->
                update_buffer_binding(
                    2,
                    dynamic_vanilla_->nodes());
            dynamic_stage_->
                update_buffer_binding(
                    3,
                    dynamic_vanilla_->order());
        }
    }

    [[nodiscard]] std::size_t dynamic_persistent_bytes() const noexcept {
        if (dynamic_hwrt_) {
            return dynamic_hwrt_->setup_stats().persistent_bytes;
        }
        if (dynamic_quant_) {
            return dynamic_quant_->allocation_bytes();
        }
        if (dynamic_vanilla_) {
            return dynamic_vanilla_->allocation_bytes();
        }
        if (dynamic_lbvh_) {
            return dynamic_lbvh_->memory().persistent_bytes;
        }
        return 0U;
    }

    [[nodiscard]] std::size_t logical_scratch_bytes() const noexcept {
        std::size_t bytes = 0U;
        if (static_hwrt_) {
            bytes += static_hwrt_->setup_stats().scratch_bytes;
        }
        if (dynamic_hwrt_) {
            bytes += dynamic_hwrt_->setup_stats().scratch_bytes;
        }
        if (dynamic_lbvh_) {
            bytes += dynamic_lbvh_->memory().scratch_bytes;
        }
        return bytes;
    }

    [[nodiscard]] std::size_t logical_transient_bytes() const noexcept {
        const auto allocation = [](const B002Buffer& buffer) {
            return static_cast<std::size_t>(buffer.allocation_size);
        };
        std::size_t bytes =
            allocation(counters_) +
            allocation(static_hits_) +
            allocation(dynamic_hits_) +
            allocation(hits_) +
            allocation(contributions_) +
            allocation(accum_) +
            allocation(resolved_) +
            allocation(storage_stats_);
        if (dynamic_lbvh_) {
            bytes += dynamic_lbvh_->memory().transient_bytes;
        }
        return bytes;
    }

    void create_command_resources() {
        auto pool_info =
            detail::make_vk_info<
                VkCommandPoolCreateInfo>(
                VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
        pool_info.flags =
            VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        pool_info.queueFamilyIndex =
            context_.queue_family();
        if (context_.vk().createCommandPool(
                &pool_info,
                nullptr,
                &command_pool_) != VK_SUCCESS) {
            fail("J004 command pool creation failed");
        }

        auto query_info =
            detail::make_vk_info<
                VkQueryPoolCreateInfo>(
                VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
        query_info.queryType =
            VK_QUERY_TYPE_TIMESTAMP;
        query_info.queryCount =
            kQueryCount;
        if (context_.vk().createQueryPool(
                &query_info,
                nullptr,
                &query_pool_) != VK_SUCCESS) {
            fail("J004 query pool creation failed");
        }

        auto fence_info =
            detail::make_vk_info<
                VkFenceCreateInfo>(
                VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
        if (context_.vk().createFence(
                &fence_info,
                nullptr,
                &fence_) != VK_SUCCESS) {
            fail("J004 fence creation failed");
        }
    }

    void record_static_traversal(
        VkCommandBuffer command) {
        if (options_.track ==
            Track::Primary) {
            const auto ray_count =
                producer_.header.item_count;
            static_stage_->record(
                command,
                groups(ray_count),
                1U,
                1U,
                &ray_count,
                sizeof(ray_count));
        } else {
            const auto push =
                static_quant_->push(
                    producer_.header.item_count);
            static_stage_->record(
                command,
                groups(
                    producer_.header.item_count),
                1U,
                1U,
                &push,
                sizeof(push));
        }
    }

    void record_dynamic_traversal(
        VkCommandBuffer command) {
        if (dynamic_kind_ ==
            DynamicKind::Hwrt) {
            const auto ray_count =
                producer_.header.item_count;
            dynamic_stage_->record(
                command,
                groups(ray_count),
                1U,
                1U,
                &ray_count,
                sizeof(ray_count));
        } else if (dynamic_kind_ ==
                   DynamicKind::B003) {
            const auto push =
                dynamic_quant_->push(
                    producer_.header.item_count);
            dynamic_stage_->record(
                command,
                groups(
                    producer_.header.item_count),
                1U,
                1U,
                &push,
                sizeof(push));
        } else if (dynamic_kind_ ==
                   DynamicKind::Lbvh) {
            dynamic_stage_->record(
                command,
                groups(
                    producer_.header.item_count));
        } else {
            const SoftwareTraversalPush push{
                producer_.header.item_count,
                dynamic_vanilla_->root(),
                0U,
                0U,
            };
            dynamic_stage_->record(
                command,
                groups(
                    producer_.header.item_count),
                1U,
                1U,
                &push,
                sizeof(push));
        }
    }

    [[nodiscard]] TransitionResult run_transition(
        std::uint32_t next_step) {
        if (next_step >= snapshots_.size()) {
            fail("J004 next topology step out of range");
        }

        const auto wall_start = Clock::now();
        // Diagnostic readbacks are outside the recurring boundary. Discard
        // their transfer accumulator before starting the next transition.
        (void)context_.consume_transfer_gpu_us();
        context_.reset_allocation_peak();

        const auto old_dynamic_persistent =
            dynamic_persistent_bytes();

        auto old_hwrt =
            std::move(dynamic_hwrt_);
        auto old_quant =
            std::move(dynamic_quant_);
        auto old_vanilla =
            std::move(dynamic_vanilla_);

        const auto prepare_start = Clock::now();
        create_dynamic_backend(next_step);
        const auto geometry_prepare_wall_us =
            elapsed_us(prepare_start);
        const auto new_dynamic_persistent =
            dynamic_persistent_bytes();

        double external_build_gpu_us = 0.0;
        if (dynamic_hwrt_) {
            external_build_gpu_us +=
                dynamic_hwrt_->
                    setup_stats().blas_build_us;
            external_build_gpu_us +=
                dynamic_hwrt_->
                    setup_stats().tlas_build_us;
        }

        const double transfer_gpu_us =
            context_.consume_transfer_gpu_us();
        const auto overlap_peak =
            context_.peak_allocation_bytes();
        const auto old_new_overlap_bytes =
            dynamic_kind_ == DynamicKind::Lbvh
                ? 0U
                : old_dynamic_persistent +
                    new_dynamic_persistent;

        const auto realloc_start = Clock::now();
        rebind_dynamic_stage();

        // The queue is idle before every transition. Once descriptors point at
        // the replacement backend, the previous backend is no longer needed.
        old_hwrt.reset();
        old_quant.reset();
        old_vanilla.reset();
        const auto allocation_reallocation_wall_us =
            elapsed_us(realloc_start);

        context_.vk().resetFences(
            1,
            &fence_);
        context_.vk().resetCommandPool(
            command_pool_,
            0);

        VkCommandBuffer command{};
        auto allocation =
            detail::make_vk_info<
                VkCommandBufferAllocateInfo>(
                VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
        allocation.commandPool =
            command_pool_;
        allocation.level =
            VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        allocation.commandBufferCount = 1;
        if (context_.vk().allocateCommandBuffers(
                &allocation,
                &command) != VK_SUCCESS) {
            fail("J004 command allocation failed");
        }

        auto begin =
            detail::make_vk_info<
                VkCommandBufferBeginInfo>(
                VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
        begin.flags =
            VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        if (context_.vk().beginCommandBuffer(
                command,
                &begin) != VK_SUCCESS) {
            fail("J004 command begin failed");
        }

        context_.vk().cmdResetQueryPool(
            command,
            query_pool_,
            0,
            kQueryCount);
        const auto stamp = [&](std::uint32_t slot) {
            context_.vk().cmdWriteTimestamp(
                command,
                VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
                query_pool_,
                slot);
        };

        stamp(0U);
        context_.vk().cmdFillBuffer(
            command,
            accum_.buffer,
            0,
            accum_.size,
            0U);
        context_.vk().cmdFillBuffer(
            command,
            resolved_.buffer,
            0,
            resolved_.size,
            0U);
        context_.vk().cmdFillBuffer(
            command,
            storage_stats_.buffer,
            0,
            storage_stats_.size,
            0U);
        lane_i::i001_transfer_to_compute_barrier(
            context_,
            command);
        stamp(1U);

        if (dynamic_kind_ ==
            DynamicKind::Lbvh) {
            dynamic_lbvh_->record_build(
                command,
                0.0F,
                query_pool_,
                2U);
            lane_i::i001_compute_barrier(
                context_,
                command);
        } else {
            // Keep the fixed query layout complete without inventing builder
            // time for controls that rebuild outside this command buffer.
            for (std::uint32_t slot = 2U;
                 slot <= 9U;
                 ++slot) {
                stamp(slot);
            }
        }
        stamp(10U);

        record_static_traversal(command);
        lane_i::i001_compute_barrier(
            context_,
            command);
        stamp(11U);

        record_dynamic_traversal(command);
        lane_i::i001_compute_barrier(
            context_,
            command);
        stamp(12U);

        hit_merge_stage_->record(
            command,
            groups(
                producer_.header.item_count));
        lane_i::i001_compute_barrier(
            context_,
            command);
        stamp(13U);

        radiance_stage_->record(
            command,
            groups(
                producer_.header.item_count));
        lane_i::i001_compute_barrier(
            context_,
            command);
        stamp(14U);

        merge_stage_->record(
            command,
            groups(
                producer_.header.item_count));
        lane_i::i001_compute_barrier(
            context_,
            command);
        stamp(15U);

        ++frame_id_;
        const StoragePush reserve_push{
            storage_capacity_ - 1U,
            kStorageMaxProbe,
            frame_id_,
            0U,
        };
        storage_update_stage_->record(
            command,
            groups(
                producer_.header.item_count),
            1U,
            1U,
            &reserve_push,
            sizeof(reserve_push));
        lane_i::i001_compute_barrier(
            context_,
            command);
        stamp(16U);

        const StoragePush accumulate_push{
            storage_capacity_ - 1U,
            kStorageMaxProbe,
            frame_id_,
            1U,
        };
        storage_update_stage_->record(
            command,
            groups(
                producer_.header.item_count),
            1U,
            1U,
            &accumulate_push,
            sizeof(accumulate_push));
        lane_i::i001_compute_barrier(
            context_,
            command);
        stamp(17U);

        const InvalidationPush invalidate_push{
            storage_capacity_,
            frame_id_,
            0U,
            0U,
        };
        invalidation_stage_->record(
            command,
            groups(storage_capacity_),
            1U,
            1U,
            &invalidate_push,
            sizeof(invalidate_push));
        lane_i::i001_compute_barrier(
            context_,
            command);
        stamp(18U);

        const StoragePush resolve_push{
            storage_capacity_ - 1U,
            kStorageMaxProbe,
            frame_id_,
            0U,
        };
        resolve_stage_->record(
            command,
            groups(
                producer_.header.item_count),
            1U,
            1U,
            &resolve_push,
            sizeof(resolve_push));
        lane_i::i001_compute_barrier(
            context_,
            command);
        stamp(19U);

        if (context_.vk().endCommandBuffer(
                command) != VK_SUCCESS) {
            fail("J004 command end failed");
        }

        auto submit =
            detail::make_vk_info<
                VkSubmitInfo>(
                VK_STRUCTURE_TYPE_SUBMIT_INFO);
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command;
        const auto sync_start = Clock::now();
        if (context_.vk().queueSubmit(
                context_.queue(),
                1,
                &submit,
                fence_) != VK_SUCCESS) {
            fail("J004 queue submit failed");
        }
        if (context_.vk().waitForFences(
                1,
                &fence_,
                VK_TRUE,
                UINT64_MAX) != VK_SUCCESS) {
            fail("J004 fence wait failed");
        }
        const auto synchronization_wall_us =
            elapsed_us(sync_start);

        std::array<std::uint64_t, kQueryCount>
            timestamps{};
        if (context_.vk().getQueryPoolResults(
                query_pool_,
                0,
                kQueryCount,
                sizeof(timestamps),
                timestamps.data(),
                sizeof(std::uint64_t),
                VK_QUERY_RESULT_64_BIT |
                    VK_QUERY_RESULT_WAIT_BIT)
            != VK_SUCCESS) {
            fail("J004 timestamp readback failed");
        }

        const auto gpu_us = [&](std::uint32_t first,
                                std::uint32_t last) {
            return double(
                timestamps[last] -
                timestamps[first]) *
                double(
                    context_.timestamp_period_ns()) /
                1000.0;
        };
        const double main_gpu_us =
            gpu_us(0U, 19U);
        const double builder_gpu_us =
            dynamic_kind_ == DynamicKind::Lbvh
                ? gpu_us(2U, 9U)
                : 0.0;
        const double traversal_gpu_us =
            gpu_us(10U, 12U);
        const double merge_gpu_us =
            gpu_us(12U, 15U);
        const double storage_gpu_us =
            gpu_us(0U, 1U) +
            gpu_us(15U, 18U);
        const double resolve_gpu_us =
            gpu_us(18U, 19U);

        // Capture the allocation peak before the diagnostic storage-stat
        // readback allocates staging memory. Diagnostic readback must never
        // inflate the formal true-peak residency.
        const auto boundary_peak =
            context_.peak_allocation_bytes();
        const auto live_bytes =
            context_.live_allocation_bytes();
        const auto scratch_bytes =
            logical_scratch_bytes();
        const auto transient_bytes =
            logical_transient_bytes();
        if (scratch_bytes + transient_bytes >
            live_bytes) {
            fail(
                "J004 allocation lifetime classes "
                "exceed live residency");
        }
        const auto persistent_bytes =
            live_bytes -
            scratch_bytes -
            transient_bytes;

        const auto wall_us =
            elapsed_us(wall_start);

        std::array<std::uint32_t, 4>
            storage_stats{};
        context_.download_device_buffer(
            storage_stats_,
            storage_stats.data(),
            sizeof(storage_stats));
        // Explicitly discard diagnostic transfer timing. The next transition
        // also resets the peak, but clearing here prevents accidental reuse.
        (void)context_.consume_transfer_gpu_us();

        current_step_ = next_step;

        TransitionResult result{};
        result.geometry_prepare_wall_us =
            geometry_prepare_wall_us;
        result.allocation_reallocation_wall_us =
            allocation_reallocation_wall_us;
        result.geometry_upload_gpu_us =
            transfer_gpu_us;
        result.candidate_preprocess_gpu_us = 0.0;
        result.build_rebuild_gpu_us =
            external_build_gpu_us +
            builder_gpu_us;
        result.refit_gpu_us = 0.0;
        result.compaction_gpu_us = 0.0;
        result.instance_tlas_update_gpu_us = 0.0;
        result.traversal_gpu_us =
            traversal_gpu_us;
        result.synchronization_wall_us =
            synchronization_wall_us;
        result.merge_gpu_us =
            merge_gpu_us;
        result.storage_gpu_us =
            storage_gpu_us;
        result.resolve_gpu_us =
            resolve_gpu_us;
        result.complete_gpu_us =
            transfer_gpu_us +
            external_build_gpu_us +
            main_gpu_us;
        result.complete_wall_us =
            wall_us;
        result.persistent_bytes =
            persistent_bytes;
        result.transient_bytes =
            transient_bytes;
        result.scratch_bytes =
            scratch_bytes;
        result.old_new_overlap_bytes =
            old_new_overlap_bytes;
        result.resident_bytes =
            live_bytes;
        result.true_peak_resident_bytes =
            std::max(
                overlap_peak,
                boundary_peak);
        result.storage_failures =
            storage_stats[3];
        return result;
    }

    B002VulkanContext& context_;
    Options options_;
    DynamicKind dynamic_kind_{};

    lane_b::B002Scene full_scene_;
    float segment_size_{};
    std::uint32_t dynamic_instance_id_{
        lane_b::kInvalidId};
    std::vector<lane_b::Triangle>
        static_triangles_;
    std::vector<
        std::vector<lane_b::Triangle>>
        snapshots_;
    lane_b::LaneAReplayStreamV1 producer_;
    std::vector<lane_b::Ray> replay_rays_;
    std::uint32_t current_step_{};
    std::uint32_t frame_id_{};
    std::uint32_t lbvh_capacity_count_{};
    std::uint32_t storage_capacity_{};

    std::unique_ptr<
        lane_b::GpuSoftwareBvhData>
        static_cpu_;
    std::unique_ptr<B002HwrtTraversal>
        static_hwrt_;
    std::unique_ptr<QuantizedState>
        static_quant_;

    std::unique_ptr<B002HwrtTraversal>
        dynamic_hwrt_;
    std::unique_ptr<QuantizedState>
        dynamic_quant_;
    std::unique_ptr<
        lane_f::F003TransientLbvh>
        dynamic_lbvh_;
    std::unique_ptr<VanillaState>
        dynamic_vanilla_;

    B002Buffer work_{};
    B002Buffer rays_{};
    B002Buffer counters_{};
    B002Buffer static_hits_{};
    B002Buffer dynamic_hits_{};
    B002Buffer hits_{};
    B002Buffer contributions_{};
    B002Buffer accum_{};
    B002Buffer resolved_{};
    B002Buffer uniform_{};
    B002Buffer storage_slots_{};
    B002Buffer storage_stats_{};

    std::unique_ptr<I001ComputeStage>
        static_stage_;
    std::unique_ptr<I001ComputeStage>
        dynamic_stage_;
    std::unique_ptr<I001ComputeStage>
        hit_merge_stage_;
    std::unique_ptr<I001ComputeStage>
        radiance_stage_;
    std::unique_ptr<I001ComputeStage>
        merge_stage_;
    std::unique_ptr<I001ComputeStage>
        storage_update_stage_;
    std::unique_ptr<I001ComputeStage>
        invalidation_stage_;
    std::unique_ptr<I001ComputeStage>
        resolve_stage_;

    VkCommandPool command_pool_{
        VK_NULL_HANDLE};
    VkQueryPool query_pool_{
        VK_NULL_HANDLE};
    VkFence fence_{VK_NULL_HANDLE};
};

[[nodiscard]] DynamicKind validation_kind(
    const Options& options) {
    if (options.validation_variant ==
        "control") {
        return control_kind(options.track);
    }
    if (options.validation_variant ==
        "candidate") {
        return DynamicKind::Lbvh;
    }
    if (options.validation_variant ==
        "accounting") {
        return DynamicKind::Vanilla;
    }
    fail(
        "unknown J004 validation variant: " +
        options.validation_variant);
}

[[nodiscard]] std::filesystem::path artifact_root() {
    if (const char* value =
            std::getenv(
                "PHOS_RESEARCH_ARTIFACT_DIR");
        value != nullptr &&
        *value != '\0') {
        return value;
    }
    return "out/research/"
           "lane-j-topology-backend-alternatives/"
           "004-formal-crossover/manual-process";
}

void write_device(
    const std::filesystem::path& root,
    const B002VulkanContext& context) {
    std::ofstream out(
        root / "j004-device.json");
    if (!out) {
        fail("cannot create J004 device file");
    }
    out
        << "{\n"
        << "  \"device\": \""
        << context.device_name()
        << "\",\n"
        << "  \"driver_name\": \""
        << context.driver_name()
        << "\",\n"
        << "  \"driver_info\": \""
        << context.driver_info()
        << "\",\n"
        << "  \"api_version\": "
        << context.api_version()
        << ",\n"
        << "  \"driver_version\": "
        << context.driver_version()
        << ",\n"
        << "  \"vendor_id\": "
        << context.vendor_id()
        << ",\n"
        << "  \"device_id\": "
        << context.device_id()
        << ",\n"
        << "  \"timestamp_period_ns\": "
        << context.timestamp_period_ns()
        << "\n"
        << "}\n";
}

void write_validation(
    const std::filesystem::path& root,
    const Options& options,
    DynamicKind kind,
    const ValidationResult& result) {
    std::ofstream out(
        root / "j004-validation.json");
    if (!out) {
        fail("cannot create J004 validation file");
    }
    const bool passed =
        result.hit_mismatches == 0U &&
        result.nearest_hit_tie_mismatches == 0U &&
        result.traversal_runtime_errors == 0U &&
        result.storage_failures == 0U &&
        result.immutable_owner_mutations == 0U;
    out
        << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"track\": \""
        << track_name(options.track)
        << "\",\n"
        << "  \"variant\": \""
        << kind_name(kind)
        << "\",\n"
        << "  \"validation_ray_prefix_count\": "
        << options.validation_rays
        << ",\n"
        << "  \"hit_mismatch_count\": "
        << result.hit_mismatches
        << ",\n"
        << "  \"nearest_hit_tie_mismatch_count\": "
        << result.nearest_hit_tie_mismatches
        << ",\n"
        << "  \"traversal_runtime_error_count\": "
        << result.traversal_runtime_errors
        << ",\n"
        << "  \"storage_failure_count\": "
        << result.storage_failures
        << ",\n"
        << "  \"immutable_owner_mutation_count\": "
        << result.immutable_owner_mutations
        << ",\n"
        << "  \"visibility_mismatch_count\": 0,\n"
        << "  \"producer_semantic_error_count\": 0,\n"
        << "  \"workload_identity_match\": true,\n"
        << "  \"resolved_digest\": "
        << result.resolved_digest
        << ",\n"
        << "  \"passed\": "
        << (passed ? "true" : "false")
        << "\n"
        << "}\n";
}

void write_sample_row(
    std::ofstream& out,
    const char* phase,
    std::uint32_t pair_index,
    const char* order,
    const char* role,
    DynamicKind kind,
    const BatchResult& result) {
    out
        << phase << ","
        << pair_index << ","
        << order << ","
        << role << ","
        << kind_name(kind) << ","
        << std::setprecision(12)
        << result.geometry_prepare_wall_us << ","
        << result.allocation_reallocation_wall_us << ","
        << result.geometry_upload_gpu_us << ","
        << result.candidate_preprocess_gpu_us << ","
        << result.build_rebuild_gpu_us << ","
        << result.refit_gpu_us << ","
        << result.compaction_gpu_us << ","
        << result.instance_tlas_update_gpu_us << ","
        << result.traversal_gpu_us << ","
        << result.synchronization_wall_us << ","
        << result.merge_gpu_us << ","
        << result.storage_gpu_us << ","
        << result.resolve_gpu_us << ","
        << result.complete_gpu_us << ","
        << result.complete_gpu_us << ","
        << result.complete_wall_us << ","
        << result.complete_wall_us << ","
        << result.max_persistent_bytes << ","
        << result.max_transient_bytes << ","
        << result.max_scratch_bytes << ","
        << result.max_old_new_overlap_bytes << ","
        << result.max_true_peak_resident_bytes << ","
        << result.max_resident_bytes << ","
        << result.max_true_peak_resident_bytes << ","
        << result.storage_failures
        << "\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto options =
            parse_options(argc, argv);
        const auto root = artifact_root();
        std::filesystem::create_directories(root);

        if (options.validation_only) {
            B002VulkanContext context(
                options.validation,
                lane_b::kB002TargetDeviceName,
                true);
            write_device(root, context);
            const auto kind =
                validation_kind(options);
            FormalRuntime runtime(
                context,
                options,
                kind);
            const auto validation =
                runtime.validate_cycle(
                    options.validation_rays);
            write_validation(
                root,
                options,
                kind,
                validation);

            const bool passed =
                validation.hit_mismatches == 0U &&
                validation.nearest_hit_tie_mismatches == 0U &&
                validation.traversal_runtime_errors == 0U &&
                validation.storage_failures == 0U &&
                validation.immutable_owner_mutations == 0U;
            std::cout
                << "J004 validation "
                << track_name(options.track)
                << "/"
                << kind_name(kind)
                << ": "
                << (passed ? "PASS" : "FAIL")
                << "\n";
            return passed ? 0 : 2;
        }

        // One fresh host process owns two independent Vulkan contexts. This
        // keeps A/B memory/lifetime accounting independent while preserving
        // same-process, same-device and counterbalanced sequential execution.
        B002VulkanContext context_a(
            false,
            lane_b::kB002TargetDeviceName,
            true);
        B002VulkanContext context_b(
            false,
            lane_b::kB002TargetDeviceName,
            true);
        if (context_a.device_name() != context_b.device_name() ||
            context_a.driver_name() != context_b.driver_name() ||
            context_a.driver_info() != context_b.driver_info() ||
            context_a.api_version() != context_b.api_version() ||
            context_a.driver_version() != context_b.driver_version() ||
            context_a.vendor_id() != context_b.vendor_id() ||
            context_a.device_id() != context_b.device_id() ||
            context_a.timestamp_period_ns() !=
                context_b.timestamp_period_ns()) {
            fail("J004 paired contexts have inconsistent device provenance");
        }
        write_device(root, context_a);

        const auto a_kind =
            control_kind(options.track);
        const auto b_kind =
            options.comparison == "control"
                ? a_kind
                : (options.comparison == "accounting"
                    ? DynamicKind::Vanilla
                    : DynamicKind::Lbvh);

        FormalRuntime runtime_a(
            context_a,
            options,
            a_kind);
        FormalRuntime runtime_b(
            context_b,
            options,
            b_kind);

        std::ofstream samples(
            root / "j004-samples.csv");
        if (!samples) {
            fail("cannot create J004 sample CSV");
        }
        samples
            << "phase,pair_index,order,role,variant,"
               "geometry_prepare_wall_us,"
               "allocation_reallocation_wall_us,"
               "geometry_upload_gpu_us,"
               "candidate_preprocess_gpu_us,"
               "build_rebuild_gpu_us,"
               "refit_gpu_us,compaction_gpu_us,"
               "instance_tlas_update_gpu_us,"
               "traversal_gpu_us,synchronization_wall_us,"
               "merge_gpu_us,storage_gpu_us,resolve_gpu_us,"
               "complete_gpu_us,gpu_us,"
               "complete_update_wall_us,complete_wall_us,"
               "persistent_bytes,transient_bytes,scratch_bytes,"
               "old_new_overlap_bytes,true_peak_resident_bytes,"
               "max_resident_bytes,max_true_peak_resident_bytes,"
               "storage_failures\n";

        const auto total_pairs =
            options.warmup_pairs +
            options.measured_pairs;
        for (std::uint32_t pair = 0U;
             pair < total_pairs;
             ++pair) {
            const bool base_ab =
                options.start_order == "AB";
            const bool pair_ab =
                (pair % 2U == 0U)
                    ? base_ab
                    : !base_ab;
            const char* order =
                pair_ab ? "AB" : "BA";
            const char* phase =
                pair < options.warmup_pairs
                    ? "warmup"
                    : "measured";
            const auto pair_index =
                pair < options.warmup_pairs
                    ? pair
                    : pair -
                        options.warmup_pairs;

            auto run_a = [&] {
                const auto result =
                    runtime_a.run_batch(
                        options.batch_transitions);
                if (result.storage_failures !=
                    0U) {
                    fail(
                        "J004 role A storage failure");
                }
                write_sample_row(
                    samples,
                    phase,
                    pair_index,
                    order,
                    "A",
                    a_kind,
                    result);
            };
            auto run_b = [&] {
                const auto result =
                    runtime_b.run_batch(
                        options.batch_transitions);
                if (result.storage_failures !=
                    0U) {
                    fail(
                        "J004 role B storage failure");
                }
                write_sample_row(
                    samples,
                    phase,
                    pair_index,
                    order,
                    "B",
                    b_kind,
                    result);
            };

            if (pair_ab) {
                run_a();
                run_b();
            } else {
                run_b();
                run_a();
            }
            samples.flush();
        }

        std::cout
            << "J004 formal process complete: "
            << track_name(options.track)
            << "/"
            << options.comparison
            << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "J004 formal process fatal: "
            << error.what()
            << "\n";
        return 1;
    }
}

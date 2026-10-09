#pragma once

#include <cstdint>
#include <array>
#include <memory>
#include <vector>

#include "../lane_n_end_to_end_renderer/n001_runtime.hpp"

namespace phos::gi::research::integration {

enum class N006ExtraMode : std::uint32_t {
    Current = 0,
    Uniform = 1,
    Targeted = 2,
};

struct N006ExtraRequest {
    N006ExtraMode mode{N006ExtraMode::Current};
    std::uint32_t owner_budget{};
    float depth_threshold{0.01F}; // Reserved for compatibility with N005 diagnostics.
    std::uint32_t extra_rays_per_probe{4U};
    std::uint32_t selected_tile_id{0xffffffffU};
    std::uint32_t selected_cascade{0xffffffffU};
    bool capture_hash_probe{};
    bool canonical_probe_pilot{};
};

// Debug readback for N006-only causal-chain diagnostics, never a scheduler signal.
struct N006InfluenceTrace {
    bool available{};
    std::uint32_t tile_id{};
    std::uint32_t cascade{};
    std::uint32_t output_id{};
    std::int32_t probe_x{}, probe_y{}, probe_z{};
    std::uint32_t base_ray_count{}, extra_ray_count{};
    std::uint64_t base_radiance_sum16{}, extra_radiance_sum16{};
    std::uint32_t base_zero_rays{}, extra_zero_rays{};
    std::uint32_t base_output_mean16{}, target_output_mean16{};
    std::uint32_t shared_probe_outputs{};
    std::uint64_t before_storage_sum16{}, after_storage_sum16{};
    double before_storage_mean16{}, after_storage_mean16{};
    std::uint64_t observed_storage_sum16{};
    std::uint32_t observed_storage_outputs{};
};

// Counts exact-input repeat groups in the existing base work stream.
// This is a non-timed forensic diagnostic; it does not deduplicate GPU work.
struct N006ProbeMultiplicityRow {
    std::uint32_t cascade{};
    std::uint32_t owner_outputs{};
    std::uint32_t unique_probe_keys{};
    std::uint32_t max_owner_outputs_per_key{};
    std::uint32_t shared_keys{};
    std::uint64_t duplicated_ray_inputs{};
    bool same_probe_ray_inputs_identical{true};
};

struct N006ProbeMultiplicityAudit {
    std::uint32_t base_work_items{};
    std::uint32_t visible_owners{};
    std::uint32_t rays_per_probe{};
    std::uint32_t cascade_count{};
    std::vector<N006ProbeMultiplicityRow> cascades;
};

// P1f forensic data from a completed, unchanged current-mode GPU frame.
// Divergent outputs are observed, never silently canonicalized.
struct N006OutputEquivalenceRow {
    std::uint32_t cascade{};
    std::uint32_t unique_probe_keys{};
    std::uint32_t owner_outputs{};
    std::uint32_t shared_keys{};
    std::uint32_t divergent_merged_keys{};
    std::uint32_t divergent_owner_outputs{};
    std::uint32_t divergent_rounded_mean_keys{};
    std::uint32_t zero_sample_outputs{};
    std::uint32_t missing_or_bad_gpu_storage_keys{};
};

struct N006OutputEquivalenceAudit {
    std::uint32_t base_work_items{};
    std::uint32_t owner_outputs{};
    std::uint32_t visible_owners{};
    std::uint32_t rays_per_probe{};
    std::uint32_t cascade_count{};
    bool all_gpu_storage_slots_reconstructed{};
    std::vector<N006OutputEquivalenceRow> cascades;
};

// Measured overhead of an auxiliary GPU hash on the unmodified base output
// stream; this does NOT deduplicate rays or estimate an attainable speedup.
struct N006GpuHashProbe {
    bool executed{};
    std::uint32_t hash_slots{};
    std::uint32_t unique_keys{};
    std::uint32_t duplicate_outputs{};
    std::uint32_t invalid_keys{};
    std::uint32_t failed_inserts{};
    std::uint32_t collision_steps{};
    std::array<std::uint32_t, 4> unique_by_cascade{};
    std::array<std::uint32_t, 4> duplicate_by_cascade{};
    std::uint64_t scratch_bytes{};
    double complete_hash_gpu_us{};
};

struct N006CanonicalStats {
    bool executed{};
    std::uint32_t original_work_items{};
    std::uint32_t original_outputs{};
    std::uint32_t canonical_work_items{};
    std::uint32_t canonical_outputs{};
    std::uint32_t duplicates{};
    std::uint32_t invalid_keys{};
    std::uint32_t failed_inserts{};
    std::uint32_t index_overflows{};
    std::uint32_t collision_steps{};
    std::array<std::uint32_t, 4> unique_by_cascade{};
    std::uint64_t scratch_bytes{};
    double total_canonical_gpu_us{};
    double owner_weight_storage_gpu_us{};
    std::uint32_t owner_weight_errors{};
    std::uint32_t weighted_owner_total{};
};

struct N006ExtraStats {
    std::uint32_t base_traced_rays{};
    std::uint32_t extra_rays_requested{};
    std::uint32_t extra_rays_traced{};
    std::uint32_t extra_work_items{};
    std::uint32_t eligible_owner_count{};
    std::uint32_t selected_owner_count{};
    std::uint32_t eligible_probe_count{};
    std::uint32_t extra_probe_count{};
    double extra_probe_fraction{};
    double extra_producer_gpu_us{};
    bool base_prefix_correct{};
    bool extra_work_correct{};
    N006InfluenceTrace influence_trace{};
    N006GpuHashProbe gpu_hash_probe{};
    N006CanonicalStats canonical{};
};

struct N006FrameResult {
    I001FrameResult frame;
    N006ExtraStats extra;
};

class N006Runtime {
public:
    explicit N006Runtime(I001Options options);
    ~N006Runtime();

    N006Runtime(const N006Runtime&) = delete;
    N006Runtime& operator=(const N006Runtime&) = delete;

    void set_motion_fraction(float fraction);
    [[nodiscard]] N006FrameResult run_frame(
        bool target_state,
        N006ExtraRequest request);
    [[nodiscard]] N006FrameResult run_topology_churn_frame(
        N006ExtraRequest request);

    [[nodiscard]] std::vector<std::uint32_t> visible_tile_ids();
    [[nodiscard]] N006ProbeMultiplicityAudit probe_multiplicity_audit();
    [[nodiscard]] N006OutputEquivalenceAudit probe_output_equivalence_audit();
    [[nodiscard]] I001N004HitDiagnostics n004_hit_diagnostics();
    [[nodiscard]] I001RendererReadback renderer_readback();

    [[nodiscard]] const std::string& device_name() const noexcept;
    [[nodiscard]] const std::string& driver_name() const noexcept;
    [[nodiscard]] const std::string& driver_info() const noexcept;
    [[nodiscard]] std::uint32_t api_version() const noexcept;
    [[nodiscard]] float timestamp_period_ns() const noexcept;

private:
    struct State;
    I001Runtime runtime_;
    std::unique_ptr<State> state_;

    [[nodiscard]] N006FrameResult run_candidate_frame(
        bool target_state,
        N006ExtraRequest request);
};

} // namespace phos::gi::research::integration

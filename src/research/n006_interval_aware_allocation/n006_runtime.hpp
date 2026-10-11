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
    bool direct_compact_work{}; // P1k per-frame three-arm selector; requires opt-in stages.
    bool p1l_b1_near_first{}; // N006 isolated near-first software primary arm.
    bool p1m0_pretrace_coverage{}; // Opt-in N006-only placement/cost probe.
    bool p1m1_canonical_key_intervention{}; // Single-key causal ray preflight.
    std::uint32_t p1m1_selected_token{}; // Frozen canonical packed key.
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
    bool copyback_executed{true};
    std::uint32_t hash_slots{};
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

struct N006CanonicalM1Trace {
    bool executed{};
    std::uint32_t selected_token{};
    std::uint32_t output_id{};
    std::uint32_t base_ray_count{};
    std::uint32_t extra_ray_count{};
    std::uint64_t base_radiance_sum16{};
    std::uint64_t extra_radiance_sum16{};
    std::uint32_t baseline_mean16{};
    std::uint32_t candidate_mean16{};
    std::uint32_t merged_sample_count{};
    double extra_injection_gpu_us{};
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
    N006CanonicalM1Trace canonical_m1{};
};

struct N006FrameResult {
    I001FrameResult frame;
    N006ExtraStats extra;
};

// N006 P1l-B0 diagnostic only: count-only work, NEVER timing performance.
// Slots are documented in the P1l-B0 protocol and serialized by N006 main.
struct N006P1lB0Metric {
    std::uint64_t total{};
    double mean{};
    double p50{};
    double p90{};
    double p99{};
    std::uint32_t maximum{};
    std::uint32_t nonzero{};
};
struct N006P1lB0Profile {
    std::uint32_t pixels{};
    std::uint32_t secondary_rays{};
    std::array<N006P1lB0Metric, 4> primary{};
    std::array<N006P1lB0Metric, 8> shadow{};
    std::array<N006P1lB0Metric, 8> secondary{};
};

// B1b is diagnostic-only: raw GPU outputs of each independent arm MUST be
// byte-identical to the accepted original primary hit buffer.
struct N006P1lB1bDifference {
    std::int64_t signed_total{};
    double mean{};
    double p50{};
    double p90{};
    double p99{};
    std::int64_t minimum{};
    std::int64_t maximum{};
    std::uint32_t fewer{};
    std::uint32_t equal{};
    std::uint32_t more{};
};
struct N006P1lB1bProfile {
    std::uint32_t pixels{};
    std::array<N006P1lB0Metric, 4> original{};
    std::array<N006P1lB0Metric, 4> near_first{};
    std::array<N006P1lB1bDifference, 2> delta{};
};



// P1m0: post-render, read-only key-lookup diagnostic. Not predictor evidence.
struct N006P1m0KeyRow {
    std::uint32_t token{};
    std::uint32_t consumer_pixels{};
    std::uint32_t producer_owner_outputs{};
};
struct N006P1m0Coverage {
    // True only after the same frame's pre-secondary and postframe per-slot
    // coverage counters/statistics are bit-identical. Extra GPU time is NOT
    // part of the previously accepted uninstrumented timing baseline.
    bool pretrace_executed{};
    bool pretrace_slot_byte_equal{};
    bool pretrace_stats_byte_equal{};
    double pretrace_clear_and_count_gpu_us{};
    std::uint64_t pretrace_scratch_bytes{};
    std::uint32_t hash_capacity{};
    std::uint32_t valid_primary_pixels{};
    std::uint32_t lookup_attempts{};
    std::uint32_t matched_lookups{};
    std::uint32_t absent_keys{};
    std::uint32_t invalid_keys{};
    std::uint32_t probe_exhaustions{};
    std::uint32_t uint32_overflows{};
    std::uint32_t invalid_launch{};
    std::uint32_t canonical_keys{};
    std::uint32_t keys_with_consumers{};
    std::uint32_t max_consumer_pixels{};
    std::array<std::uint64_t, 4> consumer_lookups_by_cascade{};
    std::array<std::uint32_t, 4> keys_with_consumers_by_cascade{};
    std::vector<N006P1m0KeyRow> key_rows; // sorted by token, includes zeros
};

class N006Runtime {
public:
    explicit N006Runtime(I001Options options, bool p1j_lean_hash = false,
                         bool p1j_direct_compact = false,
                         bool p1l_b1_enabled = false,
                         bool p1l_b1c_axis_proxy = false,
                         bool p1m0_pretrace_enabled = false,
                         bool p1m1_canonical_extra_enabled = false);
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
    // Separate compute-only command after an uninstrumented frame has finished
    // and its PFM/correctness evidence has been captured. Software backend only.
    [[nodiscard]] N006P1lB0Profile p1l_b0_work_counts();
    // Requires the last successful frame to use canonical probe mode; records
    // all consumer counts after the accepted image and GPU timestamps.
    [[nodiscard]] N006P1m0Coverage p1m0_consumer_coverage();
    // B1b runs both independent primary count shaders AFTER a measured frame.
    // Only count outputs, not instrumented GPU shader time.
    [[nodiscard]] N006P1lB1bProfile p1l_b1b_work_counts();
    // Exact bytes used only for same-state B1 preflight and timed-frame audit.
    [[nodiscard]] std::vector<std::uint8_t> p1l_b1_primary_hit_bytes();
    [[nodiscard]] double p1l_b1c_pack_cpu_us() const noexcept;
    [[nodiscard]] std::uint64_t p1l_b1c_packed_nodes() const noexcept;

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

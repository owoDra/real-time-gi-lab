#pragma once

#include <cstdint>
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
    std::uint32_t before_storage_mean16{}, after_storage_mean16{};
    std::uint64_t observed_storage_sum16{};
    std::uint32_t observed_storage_outputs{};
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

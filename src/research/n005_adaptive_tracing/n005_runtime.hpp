#pragma once

#include <cstdint>
#include <memory>

#include "../lane_n_end_to_end_renderer/n001_runtime.hpp"

namespace phos::gi::research::integration {

enum class N005ExtraMode : std::uint32_t {
    Current = 0,
    Uniform = 1,
    Adaptive = 2,
};

struct N005ExtraRequest {
    N005ExtraMode mode{N005ExtraMode::Current};
    std::uint32_t owner_budget{};
    float depth_threshold{0.01F};
    std::uint32_t extra_rays_per_probe{4U};
};

struct N005ExtraStats {
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
};

struct N005FrameResult {
    I001FrameResult frame;
    N005ExtraStats extra;
};

class N005Runtime {
public:
    explicit N005Runtime(I001Options options);
    ~N005Runtime();

    N005Runtime(const N005Runtime&) = delete;
    N005Runtime& operator=(const N005Runtime&) = delete;

    void set_motion_fraction(float fraction);
    [[nodiscard]] N005FrameResult run_frame(
        bool target_state,
        N005ExtraRequest request);
    [[nodiscard]] N005FrameResult run_topology_churn_frame(
        N005ExtraRequest request);

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

    [[nodiscard]] N005FrameResult run_candidate_frame(
        bool target_state,
        N005ExtraRequest request);
};

} // namespace phos::gi::research::integration

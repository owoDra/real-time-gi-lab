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

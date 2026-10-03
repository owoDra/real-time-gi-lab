#pragma once
#include "a001_scene.hpp"
#include "stream_schema.hpp"
#include "vk_context.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <vector>

namespace phos::gi::lane_a {

enum class A001Case { Static, CameraMotion, LightMotion };
const char* case_name(A001Case value);

struct A001Settings {
    A001Case case_id{A001Case::Static};
    std::uint32_t tile_width{128};
    std::uint32_t tile_height{72};
    std::uint32_t cascade_count{4};
    std::uint32_t rays_per_probe{8};
    std::uint32_t frame_id{};
    // N004 control surface. Defaults preserve every historical A001/N001-N003
    // target exactly: CameraMotion and LightMotion still use their full frozen
    // target state unless N004 prospectively requests an intermediate fraction.
    float camera_motion_fraction{1.0F};
    float light_motion_fraction{1.0F};
};

struct alignas(16) A001ParamsGpu {
    float camera_pos_near[4]{};
    float camera_right_tan_x[4]{};
    float camera_up_tan_y[4]{};
    float camera_forward_far[4]{};
    float scene_origin_spacing[4]{};
    float light_pos_interval[4]{};
    std::uint32_t counts[4]{};
    std::uint32_t limits[4]{};
};
static_assert(sizeof(A001ParamsGpu) == 128);

struct A001Timings {
    double visibility_depth_us{};
    double visibility_owner_us{};
    double producer_emit_us{};
    double finalize_us{};
    double producer_total_us{};
    double gather_us{};
    double merge_us{};
    double resolve_us{};
    double end_to_end_us{};
};

struct A001Memory {
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t resident_bytes{};
    std::size_t max_stream_bytes{};
};

struct A001Readback {
    std::array<std::uint32_t, 4> counters{};
    std::vector<std::uint32_t> tile_owner;
    std::vector<SplitRcWorkItemV1> work_items;
    std::vector<float> resolved;
};

A001ParamsGpu build_a001_params(const SceneSurfaceSet& scene, const A001Settings& settings);

class A001Runtime {
public:
    A001Runtime(VulkanContext& context, const SceneSurfaceSet& scene, const A001ParamsGpu& params);
    ~A001Runtime();
    A001Runtime(const A001Runtime&) = delete;
    A001Runtime& operator=(const A001Runtime&) = delete;

    A001Timings measure(std::uint32_t iterations);
    A001Readback readback();
    [[nodiscard]] A001Memory memory() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace phos::gi::lane_a

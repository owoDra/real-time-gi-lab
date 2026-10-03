// N004 links an isolated wrapper around the accepted A001 implementation.
// The macro renames only the parameter-builder symbol in this translation unit;
// all A001 runtime methods remain the accepted implementation. N001-N003 keep
// compiling the original source directly and are therefore unaffected.
#define build_a001_params build_a001_params_n004_original
#include "imported/lane_a_split_rc/a001_runtime.cpp"
#undef build_a001_params

#include <algorithm>
#include <cmath>

namespace phos::gi::lane_a {
namespace {

struct N004Vec3 {
    float x{};
    float y{};
    float z{};
};

[[nodiscard]] N004Vec3 add(N004Vec3 a, N004Vec3 b) noexcept {
    return {a.x + b.x, a.y + b.y, a.z + b.z};
}
[[nodiscard]] N004Vec3 sub(N004Vec3 a, N004Vec3 b) noexcept {
    return {a.x - b.x, a.y - b.y, a.z - b.z};
}
[[nodiscard]] N004Vec3 mul(N004Vec3 a, float s) noexcept {
    return {a.x * s, a.y * s, a.z * s};
}
[[nodiscard]] float dot(N004Vec3 a, N004Vec3 b) noexcept {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}
[[nodiscard]] N004Vec3 cross(N004Vec3 a, N004Vec3 b) noexcept {
    return {
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    };
}
[[nodiscard]] N004Vec3 normalize(N004Vec3 value) noexcept {
    const float len = std::sqrt(dot(value, value));
    return len > 1.0e-12F ? mul(value, 1.0F / len) : N004Vec3{};
}

[[nodiscard]] N004Vec3 camera_position(const A001ParamsGpu& params) noexcept {
    return {
        params.camera_pos_near[0],
        params.camera_pos_near[1],
        params.camera_pos_near[2],
    };
}

void write_camera_basis(
    A001ParamsGpu& params,
    N004Vec3 eye,
    N004Vec3 center) {
    const auto forward = normalize(sub(center, eye));
    auto right = normalize(cross(forward, {0.0F, 1.0F, 0.0F}));
    if (dot(right, right) < 1.0e-10F) right = {1.0F, 0.0F, 0.0F};
    const auto up = normalize(cross(right, forward));

    params.camera_pos_near[0] = eye.x;
    params.camera_pos_near[1] = eye.y;
    params.camera_pos_near[2] = eye.z;
    params.camera_right_tan_x[0] = right.x;
    params.camera_right_tan_x[1] = right.y;
    params.camera_right_tan_x[2] = right.z;
    params.camera_up_tan_y[0] = up.x;
    params.camera_up_tan_y[1] = up.y;
    params.camera_up_tan_y[2] = up.z;
    params.camera_forward_far[0] = forward.x;
    params.camera_forward_far[1] = forward.y;
    params.camera_forward_far[2] = forward.z;
}

} // namespace

A001ParamsGpu build_a001_params(
    const SceneSurfaceSet& scene,
    const A001Settings& settings) {
    // Full-fraction behavior is byte-for-byte the historical builder result.
    // This shortcut is important for N001-N003 equivalence checks and for N004
    // abrupt cases that intentionally reuse the frozen target state.
    const float fraction =
        settings.case_id == A001Case::CameraMotion
            ? settings.camera_motion_fraction
            : settings.case_id == A001Case::LightMotion
                ? settings.light_motion_fraction
                : 1.0F;
    const float t = std::clamp(fraction, 0.0F, 1.0F);
    if (settings.case_id == A001Case::Static || t >= 1.0F) {
        return build_a001_params_n004_original(scene, settings);
    }

    auto target_settings = settings;
    target_settings.camera_motion_fraction = 1.0F;
    target_settings.light_motion_fraction = 1.0F;
    auto target = build_a001_params_n004_original(scene, target_settings);

    auto source_settings = settings;
    source_settings.case_id = A001Case::Static;
    auto source = build_a001_params_n004_original(scene, source_settings);

    if (settings.case_id == A001Case::CameraMotion) {
        const auto source_eye = camera_position(source);
        const auto target_eye = camera_position(target);
        const auto eye = add(mul(source_eye, 1.0F - t), mul(target_eye, t));
        const N004Vec3 center{
            0.5F * (scene.min_position[0] + scene.max_position[0]),
            0.5F * (scene.min_position[1] + scene.max_position[1]),
            0.5F * (scene.min_position[2] + scene.max_position[2]),
        };
        write_camera_basis(target, eye, center);
        return target;
    }

    for (int axis = 0; axis < 3; ++axis) {
        target.light_pos_interval[axis] =
            source.light_pos_interval[axis] * (1.0F - t) +
            target.light_pos_interval[axis] * t;
    }
    return target;
}

} // namespace phos::gi::lane_a

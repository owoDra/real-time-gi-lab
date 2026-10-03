#include "n001_reference.hpp"

#include "imported/lane_b_traversal/software_bvh.hpp"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <thread>
#include <vector>

namespace phos::gi::research::integration {
namespace {

namespace lane_b = phos::gi::research::lane_b;

constexpr double kPi = 3.1415926535897932384626433832795;
constexpr double kLumaR = 0.2126;
constexpr double kLumaG = 0.7152;
constexpr double kLumaB = 0.0722;

struct Accum {
    double r{};
    double g{};
    double b{};
};

[[nodiscard]] std::uint64_t splitmix64(std::uint64_t& state) noexcept {
    state += 0x9e3779b97f4a7c15ULL;
    auto value = state;
    value = (value ^ (value >> 30U)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27U)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31U);
}

[[nodiscard]] double random01(std::uint64_t& state) noexcept {
    return double(splitmix64(state) >> 11U) * (1.0 / 9007199254740992.0);
}

[[nodiscard]] lane_b::Vec3 camera_direction(
    const lane_a::A001ParamsGpu& params,
    std::uint32_t x,
    std::uint32_t y,
    std::uint32_t width,
    std::uint32_t height) {
    const auto nx =
        2.0F * (float(x) + 0.5F) / float(width) - 1.0F;
    const auto ny =
        1.0F - 2.0F * (float(y) + 0.5F) / float(height);
    const lane_b::Vec3 forward{
        params.camera_forward_far[0],
        params.camera_forward_far[1],
        params.camera_forward_far[2],
    };
    const lane_b::Vec3 right{
        params.camera_right_tan_x[0],
        params.camera_right_tan_x[1],
        params.camera_right_tan_x[2],
    };
    const lane_b::Vec3 up{
        params.camera_up_tan_y[0],
        params.camera_up_tan_y[1],
        params.camera_up_tan_y[2],
    };
    return lane_b::normalize(
        forward +
        right * (nx * params.camera_right_tan_x[3]) +
        up * (ny * params.camera_up_tan_y[3]));
}

[[nodiscard]] lane_b::Vec3 face_forward(
    lane_b::Vec3 normal,
    lane_b::Vec3 incoming_direction) noexcept {
    normal = lane_b::normalize(normal);
    if (lane_b::dot(normal, incoming_direction * -1.0F) < 0.0F) {
        normal = normal * -1.0F;
    }
    return normal;
}

[[nodiscard]] lane_b::Vec3 cosine_direction(
    lane_b::Vec3 normal,
    double u1,
    double u2) noexcept {
    const float radius = std::sqrt(float(u1));
    const float phi = float(2.0 * kPi * u2);
    const float x = radius * std::cos(phi);
    const float y = radius * std::sin(phi);
    const float z = std::sqrt(std::max(0.0F, 1.0F - radius * radius));

    const lane_b::Vec3 helper =
        std::abs(normal.z) < 0.999F
        ? lane_b::Vec3{0.0F, 0.0F, 1.0F}
        : lane_b::Vec3{1.0F, 0.0F, 0.0F};
    const auto tangent = lane_b::normalize(lane_b::cross(helper, normal));
    const auto bitangent = lane_b::cross(normal, tangent);
    return lane_b::normalize(
        tangent * x + bitangent * y + normal * z);
}

[[nodiscard]] double direct_lambert(
    const lane_b::SoftwareBvh& bvh,
    const lane_a::A001ParamsGpu& params,
    lane_b::Vec3 position,
    lane_b::Vec3 normal) {
    const lane_b::Vec3 light{
        params.light_pos_interval[0],
        params.light_pos_interval[1],
        params.light_pos_interval[2],
    };
    const auto light_vector = light - position;
    const float distance2 = lane_b::dot(light_vector, light_vector);
    if (!std::isfinite(distance2) || distance2 <= 1.0e-12F) return 0.0;

    const float distance = std::sqrt(distance2);
    const auto light_direction = light_vector / distance;
    const float cosine = std::max(0.0F, lane_b::dot(normal, light_direction));
    if (cosine <= 0.0F) return 0.0;

    const float epsilon = std::max(
        lane_b::kRayTMin * 8.0F,
        params.camera_pos_near[3] * 0.02F);
    const float tmax = distance - std::max(
        lane_b::kRayTMin * 16.0F,
        params.camera_pos_near[3] * 0.04F);
    if (tmax > lane_b::kRayTMin) {
        const auto blocker = bvh.trace({
            position + normal * epsilon,
            light_direction,
            tmax,
        });
        if (blocker.hit) return 0.0;
    }

    const float scale = std::max(params.light_pos_interval[3], 1.0e-6F);
    const float attenuation =
        (scale * scale) / (scale * scale + distance2);
    return double(cosine * attenuation) / kPi;
}

[[nodiscard]] double trace_path(
    const lane_b::SoftwareBvh& bvh,
    const lane_a::A001ParamsGpu& params,
    lane_b::Ray ray,
    std::uint32_t max_bounces,
    std::uint64_t& rng) {
    double radiance = 0.0;
    double throughput = 1.0;

    for (std::uint32_t bounce = 0; bounce < max_bounces; ++bounce) {
        const auto hit = bvh.trace(ray);
        if (!hit.hit) break;

        const auto position = ray.origin + ray.direction * hit.t;
        const auto normal = face_forward(hit.normal, ray.direction);
        radiance += throughput * direct_lambert(
            bvh, params, position, normal);

        if (bounce + 1U >= max_bounces) break;

        // Constant-white Lambertian + cosine-weighted importance sampling:
        // f*cos/pdf = 1, so throughput stays unchanged until the path escapes.
        const auto next_direction = cosine_direction(
            normal, random01(rng), random01(rng));
        const float epsilon = std::max(
            lane_b::kRayTMin * 8.0F,
            params.camera_pos_near[3] * 0.02F);
        ray = {
            position + normal * epsilon,
            next_direction,
            params.camera_forward_far[3],
        };
    }
    return radiance;
}

void render_range(
    const I001RendererReadback& frame,
    const lane_b::SoftwareBvh& bvh,
    std::vector<Accum>& accumulation,
    std::uint32_t sample_begin,
    std::uint32_t sample_end,
    std::uint32_t max_bounces,
    std::uint64_t seed) {
    if (sample_begin >= sample_end) return;

    std::atomic<std::uint32_t> next_row{0U};
    const auto worker_count = std::max(
        1U, std::thread::hardware_concurrency());
    std::vector<std::thread> workers;
    workers.reserve(worker_count);

    for (std::uint32_t worker = 0; worker < worker_count; ++worker) {
        workers.emplace_back([&] {
            for (;;) {
                const auto y = next_row.fetch_add(1U);
                if (y >= frame.height) return;
                for (std::uint32_t x = 0; x < frame.width; ++x) {
                    const auto pixel =
                        std::size_t(y) * frame.width + x;
                    auto& sum = accumulation[pixel];

                    for (std::uint32_t sample = sample_begin;
                         sample < sample_end;
                         ++sample) {
                        std::uint64_t rng =
                            seed ^
                            (std::uint64_t(pixel) + 1ULL) *
                                0xd6e8feb86659fd93ULL ^
                            (std::uint64_t(sample) + 1ULL) *
                                0xa5a3564e27f8862bULL;
                        const auto direction = camera_direction(
                            frame.params, x, y, frame.width, frame.height);
                        const lane_b::Ray ray{
                            {
                                frame.params.camera_pos_near[0],
                                frame.params.camera_pos_near[1],
                                frame.params.camera_pos_near[2],
                            },
                            direction,
                            frame.params.camera_forward_far[3],
                        };
                        const auto value = trace_path(
                            bvh, frame.params, ray, max_bounces, rng);
                        sum.r += value;
                        sum.g += value;
                        sum.b += value;
                    }
                }
            }
        });
    }
    for (auto& worker : workers) worker.join();
}

[[nodiscard]] double percentile(
    std::vector<double>& values,
    double fraction) {
    if (values.empty()) return 0.0;
    std::sort(values.begin(), values.end());
    const double position = fraction * double(values.size() - 1U);
    const auto lo = std::size_t(std::floor(position));
    const auto hi = std::size_t(std::ceil(position));
    if (lo == hi) return values[lo];
    const double weight = position - double(lo);
    return values[lo] * (1.0 - weight) + values[hi] * weight;
}

struct ReplicateDelta {
    double p99_abs{};
    double p99_relative{};
};

[[nodiscard]] ReplicateDelta compare_replicates(
    const std::vector<Accum>& a,
    const std::vector<Accum>& b,
    std::uint32_t spp,
    double relative_floor) {
    std::vector<double> absolute;
    std::vector<double> relative;
    absolute.reserve(a.size());
    relative.reserve(a.size());
    const double inv = 1.0 / double(spp);

    for (std::size_t i = 0; i < a.size(); ++i) {
        const double ay =
            (a[i].r * kLumaR + a[i].g * kLumaG + a[i].b * kLumaB) * inv;
        const double by =
            (b[i].r * kLumaR + b[i].g * kLumaG + b[i].b * kLumaB) * inv;
        const double delta = std::abs(ay - by);
        const double reference = 0.5 * (std::abs(ay) + std::abs(by));
        absolute.push_back(delta);
        relative.push_back(delta / std::max(reference, relative_floor));
    }

    return {
        percentile(absolute, 0.99),
        percentile(relative, 0.99),
    };
}

} // namespace

N001ReferenceResult n001_render_reference(
    const I001RendererReadback& frame,
    const N001ReferenceSettings& settings) {
    if (frame.width == 0U || frame.height == 0U) {
        throw std::runtime_error("N001 reference received an empty frame");
    }
    if (frame.image_rgba.size() !=
        std::size_t(frame.width) * frame.height * 4U) {
        throw std::runtime_error("N001 renderer readback dimensions are inconsistent");
    }
    if (settings.min_spp == 0U ||
        settings.max_spp < settings.min_spp ||
        settings.max_spp % settings.min_spp != 0U ||
        settings.max_diffuse_bounces == 0U) {
        throw std::runtime_error("N001 reference settings are invalid");
    }

    lane_b::SoftwareBvh bvh(frame.triangles);
    const auto pixel_count = std::size_t(frame.width) * frame.height;
    std::vector<Accum> replicate_a(pixel_count);
    std::vector<Accum> replicate_b(pixel_count);

    std::uint32_t completed = 0U;
    N001ReferenceResult result{};
    for (std::uint32_t target = settings.min_spp;
         target <= settings.max_spp;
         target *= 2U) {
        render_range(
            frame, bvh, replicate_a, completed, target,
            settings.max_diffuse_bounces, settings.seed_a);
        render_range(
            frame, bvh, replicate_b, completed, target,
            settings.max_diffuse_bounces, settings.seed_b);
        completed = target;

        const auto delta = compare_replicates(
            replicate_a, replicate_b, completed,
            settings.relative_luminance_floor);
        result.spp = completed;
        result.replicate_p99_abs_luminance = delta.p99_abs;
        result.replicate_p99_relative_luminance = delta.p99_relative;
        result.converged =
            delta.p99_abs <= settings.p99_abs_luminance_max &&
            delta.p99_relative <= settings.p99_relative_luminance_max;
        if (result.converged || target == settings.max_spp) break;
        if (target > settings.max_spp / 2U) break;
    }

    result.rgb.resize(pixel_count * 3U);
    const double inv = 1.0 / (2.0 * double(result.spp));
    for (std::size_t pixel = 0; pixel < pixel_count; ++pixel) {
        result.rgb[pixel * 3U + 0U] = float(
            (replicate_a[pixel].r + replicate_b[pixel].r) * inv);
        result.rgb[pixel * 3U + 1U] = float(
            (replicate_a[pixel].g + replicate_b[pixel].g) * inv);
        result.rgb[pixel * 3U + 2U] = float(
            (replicate_a[pixel].b + replicate_b[pixel].b) * inv);
    }
    return result;
}

} // namespace phos::gi::research::integration

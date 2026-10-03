#include "n001_reference.hpp"
#include "n001_runtime.hpp"

#include <bit>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace fs = std::filesystem;
namespace lane_n = phos::gi::research::integration;

namespace {

struct FrameSpec {
    std::uint32_t index;
    lane_n::I001Scenario scenario;
    const char* name;
};

constexpr FrameSpec kFrames[] = {
    {0U, lane_n::I001Scenario::Static, "static"},
    {1U, lane_n::I001Scenario::CameraMotion, "camera-motion"},
    {2U, lane_n::I001Scenario::LightMotion, "light-motion"},
    {3U, lane_n::I001Scenario::MovingRigid, "moving-rigid"},
    {4U, lane_n::I001Scenario::DeformingControl, "stable-topology-deforming"},
};

[[nodiscard]] std::string escape_json(std::string_view value) {
    std::ostringstream out;
    for (const unsigned char ch : value) {
        switch (ch) {
        case '"': out << "\\\""; break;
        case '\\': out << "\\\\"; break;
        case '\b': out << "\\b"; break;
        case '\f': out << "\\f"; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default:
            if (ch < 0x20U) {
                out << "\\u"
                    << std::hex << std::setw(4) << std::setfill('0')
                    << unsigned(ch)
                    << std::dec << std::setfill(' ');
            } else {
                out << char(ch);
            }
        }
    }
    return out.str();
}

void write_pfm(
    const fs::path& path,
    std::uint32_t width,
    std::uint32_t height,
    const std::vector<float>& rgb) {
    static_assert(std::endian::native == std::endian::little);
    if (rgb.size() != std::size_t(width) * height * 3U) {
        throw std::runtime_error("PFM RGB payload size mismatch");
    }
    for (const auto value : rgb) {
        if (!std::isfinite(value)) {
            throw std::runtime_error("PFM payload contains non-finite radiance");
        }
    }

    fs::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("could not open PFM output");
    out << "PF\n" << width << ' ' << height << "\n-1.0\n";
    const auto row_floats = std::size_t(width) * 3U;
    for (std::uint32_t y = height; y-- > 0U;) {
        const auto* row = rgb.data() + std::size_t(y) * row_floats;
        out.write(
            reinterpret_cast<const char*>(row),
            std::streamsize(row_floats * sizeof(float)));
    }
    if (!out) throw std::runtime_error("PFM write failed");
}

[[nodiscard]] std::vector<float> rgb_from_rgba(
    const lane_n::I001RendererReadback& frame) {
    const auto pixels = std::size_t(frame.width) * frame.height;
    if (frame.image_rgba.size() != pixels * 4U) {
        throw std::runtime_error("renderer RGBA payload size mismatch");
    }
    std::vector<float> rgb(pixels * 3U);
    for (std::size_t pixel = 0; pixel < pixels; ++pixel) {
        rgb[pixel * 3U + 0U] = frame.image_rgba[pixel * 4U + 0U];
        rgb[pixel * 3U + 1U] = frame.image_rgba[pixel * 4U + 1U];
        rgb[pixel * 3U + 2U] = frame.image_rgba[pixel * 4U + 2U];
    }
    return rgb;
}

struct FrozenTiming {
    double renderer_prerequisite{};
    double frame_init_visibility{};
    double producer{};
    double ray_prepare{};
    double geometry_prepare_upload{};
    double acceleration_structure_maintenance{};
    double traversal{};
    double gather{};
    double radiance_storage{};
    double merge_resolve{};
    double synchronization{};
    double complete_gi{};
    double complete_renderer{};
};

[[nodiscard]] FrozenTiming freeze_timing(
    const lane_n::I001FrameTimings& t) {
    FrozenTiming out{};
    out.renderer_prerequisite = t.primary_visibility_us;
    out.frame_init_visibility =
        t.renderer_depth_us + t.frame_init_us + t.visibility_reuse_us;
    out.producer = t.producer_us;
    out.ray_prepare = t.ray_prepare_us;
    out.geometry_prepare_upload =
        t.surface_update_gpu_us +
        t.geometry_transfer_gpu_us +
        t.instance_transfer_gpu_us;
    out.acceleration_structure_maintenance =
        t.blas_update_us + t.tlas_update_us + t.hierarchy_upload_gpu_us;
    out.traversal = t.traversal_us;
    out.gather = t.radiance_us;
    out.radiance_storage = t.storage_update_us + t.invalidation_us;
    out.merge_resolve = t.merge_us + t.resolve_us;
    out.complete_gi = t.complete_gpu_us;
    out.complete_renderer = t.complete_renderer_gpu_us;

    const double accounted =
        out.renderer_prerequisite +
        out.frame_init_visibility +
        out.producer +
        out.ray_prepare +
        out.geometry_prepare_upload +
        out.acceleration_structure_maintenance +
        out.traversal +
        out.gather +
        out.radiance_storage +
        out.merge_resolve;
    const double remainder = out.complete_gi - accounted;
    if (remainder < -2.0) {
        throw std::runtime_error(
            "N002 complete-GI timing buckets exceed the measured boundary");
    }
    out.synchronization = std::max(0.0, remainder);
    return out;
}

[[nodiscard]] std::string frame_json(
    const FrameSpec& spec,
    const lane_n::I001FrameResult& measured,
    const lane_n::I001Quality& quality,
    const lane_n::N001ReferenceResult& reference,
    const lane_n::I001Memory& memory,
    double reference_wall_seconds) {
    const auto timing = freeze_timing(measured.timings);
    if (!quality.passed) {
        throw std::runtime_error(
            std::string("N002 accepted-pipeline correctness failed for ") +
            spec.name);
    }

    std::ostringstream out;
    out << std::setprecision(17);
    out << "    {\n"
        << "      \"frame\": " << spec.index << ",\n"
        << "      \"scenario\": \"" << spec.name << "\",\n"
        << "      \"output_hdr\": \"frames/output-"
        << std::setw(3) << std::setfill('0') << spec.index << ".pfm\",\n"
        << "      \"reference_hdr\": \"frames/reference-"
        << std::setw(3) << std::setfill('0') << spec.index << ".pfm\",\n"
        << std::setfill(' ')
        << "      \"reference\": {\n"
        << "        \"spp\": " << reference.spp << ",\n"
        << "        \"converged\": "
        << (reference.converged ? "true" : "false") << ",\n"
        << "        \"replicate_p99_abs_luminance\": "
        << reference.replicate_p99_abs_luminance << ",\n"
        << "        \"replicate_p99_relative_luminance\": "
        << reference.replicate_p99_relative_luminance << ",\n"
        << "        \"wall_seconds\": " << reference_wall_seconds << "\n"
        << "      },\n"
        << "      \"quality\": {\n"
        << "        \"passed\": " << (quality.passed ? "true" : "false") << ",\n"
        << "        \"visibility_mismatches\": " << quality.visibility_mismatches << ",\n"
        << "        \"producer_semantic_errors\": " << quality.producer_semantic_errors << ",\n"
        << "        \"hit_mismatches\": " << quality.hit_mismatches << ",\n"
        << "        \"traversal_runtime_errors\": " << quality.traversal_runtime_errors << ",\n"
        << "        \"missing_probes\": " << quality.missing_probes << ",\n"
        << "        \"leaked_probes\": " << quality.leaked_probes << ",\n"
        << "        \"stale_storage_slots\": " << quality.stale_storage_slots << ",\n"
        << "        \"resolved_output_mismatches\": " << quality.resolved_output_mismatches << ",\n"
        << "        \"storage_failures\": " << measured.stats.storage_failures << "\n"
        << "      },\n"
        << "      \"timing_us\": {\n"
        << "        \"complete_gi_gpu\": " << timing.complete_gi << ",\n"
        << "        \"complete_renderer_gpu\": " << timing.complete_renderer << ",\n"
        << "        \"stages\": {\n"
        << "          \"renderer_prerequisite_attributable_to_gi\": " << timing.renderer_prerequisite << ",\n"
        << "          \"frame_init_visibility\": " << timing.frame_init_visibility << ",\n"
        << "          \"producer\": " << timing.producer << ",\n"
        << "          \"ray_prepare\": " << timing.ray_prepare << ",\n"
        << "          \"geometry_prepare_upload\": " << timing.geometry_prepare_upload << ",\n"
        << "          \"acceleration_structure_maintenance\": " << timing.acceleration_structure_maintenance << ",\n"
        << "          \"traversal\": " << timing.traversal << ",\n"
        << "          \"gather\": " << timing.gather << ",\n"
        << "          \"radiance_storage\": " << timing.radiance_storage << ",\n"
        << "          \"merge_resolve\": " << timing.merge_resolve << ",\n"
        << "          \"synchronization\": " << timing.synchronization << "\n"
        << "        }\n"
        << "      },\n"
        << "      \"memory_bytes\": {\n"
        << "        \"persistent\": " << memory.persistent_bytes << ",\n"
        << "        \"transient\": " << memory.transient_bytes << ",\n"
        << "        \"scratch\": " << memory.scratch_bytes << ",\n"
        << "        \"old_new_overlap\": 0,\n"
        << "        \"true_lifetime_peak\": " << memory.peak_resident_bytes << ",\n"
        << "        \"radiance_storage_persistent\": " << memory.storage_capacity_bytes << ",\n"
        << "        \"producer_stream_capacity\": " << memory.stream_capacity_bytes << ",\n"
        << "        \"image_transient\": " << memory.image_bytes << "\n"
        << "      }\n"
        << "    }";
    return out.str();
}

void write_runtime_json(
    const fs::path& path,
    std::string_view device_name,
    std::string_view driver_name,
    std::string_view driver_info,
    std::uint32_t api_version,
    float timestamp_period_ns,
    const std::vector<std::string>& frame_json) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("could not open N002 runtime JSON");
    out << std::setprecision(17);
    out << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"phase\": \"core-baseline\",\n"
        << "  \"device\": {\n"
        << "    \"name\": \"" << escape_json(device_name) << "\",\n"
        << "    \"driver_name\": \"" << escape_json(driver_name) << "\",\n"
        << "    \"driver_info\": \"" << escape_json(driver_info) << "\",\n"
        << "    \"api_version\": " << api_version << ",\n"
        << "    \"timestamp_period_ns\": " << timestamp_period_ns << "\n"
        << "  },\n"
        << "  \"frames\": [\n";
    for (std::size_t index = 0; index < frame_json.size(); ++index) {
        out << frame_json[index];
        if (index + 1U != frame_json.size()) out << ',';
        out << '\n';
    }
    out << "  ]\n}\n";
}

} // namespace

int main(int argc, char** argv) {
    fs::path scene =
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf";
    fs::path artifact_dir;

    for (int i = 1; i < argc; ++i) {
        const std::string_view arg = argv[i];
        if (arg == "--scene" && i + 1 < argc) {
            scene = argv[++i];
        } else if (arg == "--artifact-dir" && i + 1 < argc) {
            artifact_dir = argv[++i];
        } else {
            std::cerr << "usage: phos-n002 --artifact-dir PATH [--scene PATH]\n";
            return 2;
        }
    }
    if (artifact_dir.empty()) {
        std::cerr << "--artifact-dir is required\n";
        return 2;
    }

    try {
        fs::create_directories(artifact_dir / "frames");
        std::vector<std::string> frames;
        std::string device_name;
        std::string driver_name;
        std::string driver_info;
        std::uint32_t api_version = 0U;
        float timestamp_period_ns = 0.0F;

        for (const auto& spec : kFrames) {
            lane_n::I001Options options{};
            options.scene = scene;
            options.variant = lane_n::I001Variant::LaneEFinalHwrt;
            options.scenario = spec.scenario;
            options.validation = true;

            lane_n::I001Runtime runtime(options);
            if (device_name.empty()) {
                device_name = runtime.device_name();
                driver_name = runtime.driver_name();
                driver_info = runtime.driver_info();
                api_version = runtime.api_version();
                timestamp_period_ns = runtime.timestamp_period_ns();
                std::cout << "GPU: " << device_name << '\n';
            } else if (runtime.device_name() != device_name ||
                       runtime.driver_name() != driver_name ||
                       runtime.driver_info() != driver_info ||
                       runtime.api_version() != api_version) {
                throw std::runtime_error(
                    "N002 device/driver changed between playback frames");
            }

            (void)runtime.run_frame(false);
            const auto warmup_quality = runtime.validate_last_frame();
            if (!warmup_quality.passed) {
                throw std::runtime_error(
                    std::string("N002 warm-up correctness failed for ") + spec.name);
            }

            const auto measured = runtime.run_frame(true);
            const auto quality = runtime.validate_last_frame();
            auto readback = runtime.renderer_readback();

            auto output_rgb = rgb_from_rgba(readback);
            std::ostringstream index;
            index << std::setw(3) << std::setfill('0') << spec.index;
            write_pfm(
                artifact_dir / "frames" / ("output-" + index.str() + ".pfm"),
                readback.width,
                readback.height,
                output_rgb);

            const auto reference_start = std::chrono::steady_clock::now();
            const auto reference = lane_n::n001_render_reference(readback);
            const auto reference_seconds =
                std::chrono::duration<double>(
                    std::chrono::steady_clock::now() - reference_start).count();
            write_pfm(
                artifact_dir / "frames" / ("reference-" + index.str() + ".pfm"),
                readback.width,
                readback.height,
                reference.rgb);

            frames.push_back(frame_json(
                spec,
                measured,
                quality,
                reference,
                runtime.memory(),
                reference_seconds));

            std::cout
                << "N002 frame " << spec.index << " " << spec.name
                << ": GI=" << measured.timings.complete_gpu_us
                << "us renderer=" << measured.timings.complete_renderer_gpu_us
                << "us reference=" << reference.spp
                << "spp converged=" << (reference.converged ? "yes" : "no")
                << '\n';
        }

        write_runtime_json(
            artifact_dir / "n002-runtime.json",
            device_name,
            driver_name,
            driver_info,
            api_version,
            timestamp_period_ns,
            frames);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "N002 ERROR: " << error.what() << '\n';
        return 1;
    }
}

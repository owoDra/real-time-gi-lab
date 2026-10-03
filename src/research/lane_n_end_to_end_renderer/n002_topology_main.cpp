#include "n001_reference.hpp"
#include "n001_runtime.hpp"

#include <algorithm>
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
        throw std::runtime_error("N002 topology PFM RGB payload size mismatch");
    }
    for (const auto value : rgb) {
        if (!std::isfinite(value)) {
            throw std::runtime_error(
                "N002 topology PFM contains non-finite radiance");
        }
    }
    fs::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("could not open N002 topology PFM");
    out << "PF\n" << width << ' ' << height << "\n-1.0\n";
    const auto row_floats = std::size_t(width) * 3U;
    for (std::uint32_t y = height; y-- > 0U;) {
        const auto* row = rgb.data() + std::size_t(y) * row_floats;
        out.write(
            reinterpret_cast<const char*>(row),
            std::streamsize(row_floats * sizeof(float)));
    }
    if (!out) throw std::runtime_error("N002 topology PFM write failed");
}

[[nodiscard]] std::vector<float> rgb_from_rgba(
    const lane_n::I001RendererReadback& frame) {
    const auto pixels = std::size_t(frame.width) * frame.height;
    if (frame.image_rgba.size() != pixels * 4U) {
        throw std::runtime_error("N002 topology renderer RGBA size mismatch");
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
            "N002 topology timing buckets exceed complete GI boundary");
    }
    out.synchronization = std::max(0.0, remainder);
    return out;
}

[[nodiscard]] std::string frame_json(
    const lane_n::I001FrameResult& measured,
    const lane_n::I001Quality& quality,
    const lane_n::N001ReferenceResult& reference,
    double reference_wall_seconds) {
    if (!quality.passed) {
        throw std::runtime_error("N002 topology accepted-pipeline correctness failed");
    }
    if (measured.stats.topology_mutations != 1U ||
        measured.stats.backend_rebuilds != 1U) {
        throw std::runtime_error(
            "N002 topology frame did not exercise exactly one mutation/rebuild transition");
    }
    if (measured.stats.topology_replaced_primitives == 0U ||
        measured.stats.topology_replaced_primitives !=
            (measured.stats.moved_primitives + 1U) / 2U) {
        throw std::runtime_error(
            "N002 topology frame did not exercise the frozen 50% churn schedule");
    }
    if (measured.memory.old_new_overlap_bytes == 0U) {
        throw std::runtime_error(
            "N002 topology frame did not record old/new object-local overlap");
    }

    const auto timing = freeze_timing(measured.timings);
    const auto& memory = measured.memory;
    std::ostringstream out;
    out << std::setprecision(17);
    out << "    {\n"
        << "      \"frame\": 5,\n"
        << "      \"scenario\": \"topology-changing-high-churn\",\n"
        << "      \"output_hdr\": \"frames/output-005.pfm\",\n"
        << "      \"reference_hdr\": \"frames/reference-005.pfm\",\n"
        << "      \"reference\": {\n"
        << "        \"spp\": " << reference.spp << ",\n"
        << "        \"converged\": " << (reference.converged ? "true" : "false") << ",\n"
        << "        \"replicate_p99_abs_luminance\": "
        << reference.replicate_p99_abs_luminance << ",\n"
        << "        \"replicate_p99_relative_luminance\": "
        << reference.replicate_p99_relative_luminance << ",\n"
        << "        \"wall_seconds\": " << reference_wall_seconds << "\n"
        << "      },\n"
        << "      \"quality\": {\n"
        << "        \"passed\": true,\n"
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
        << "      \"topology\": {\n"
        << "        \"mutations\": " << measured.stats.topology_mutations << ",\n"
        << "        \"backend_rebuilds\": " << measured.stats.backend_rebuilds << ",\n"
        << "        \"partition_primitives\": " << measured.stats.moved_primitives << ",\n"
        << "        \"replaced_primitives\": " << measured.stats.topology_replaced_primitives << "\n"
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
        << "        \"old_new_overlap\": " << memory.old_new_overlap_bytes << ",\n"
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
    const lane_n::I001Runtime& runtime,
    std::string_view frame) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("could not open N002 topology runtime JSON");
    out << std::setprecision(17)
        << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"phase\": \"topology-baseline\",\n"
        << "  \"device\": {\n"
        << "    \"name\": \"" << escape_json(runtime.device_name()) << "\",\n"
        << "    \"driver_name\": \"" << escape_json(runtime.driver_name()) << "\",\n"
        << "    \"driver_info\": \"" << escape_json(runtime.driver_info()) << "\",\n"
        << "    \"api_version\": " << runtime.api_version() << ",\n"
        << "    \"timestamp_period_ns\": " << runtime.timestamp_period_ns() << "\n"
        << "  },\n"
        << "  \"frames\": [\n"
        << frame << '\n'
        << "  ]\n"
        << "}\n";
}

[[nodiscard]] lane_n::I001Options topology_options(const fs::path& scene) {
    lane_n::I001Options options{};
    options.scene = scene;
    options.variant = lane_n::I001Variant::LaneEFinalHwrt;
    options.scenario = lane_n::I001Scenario::DeformingControl;
    options.validation = true;
    return options;
}

} // namespace

int main(int argc, char** argv) {
    fs::path scene =
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf";
    fs::path artifact_dir;
    for (int index = 1; index < argc; ++index) {
        const std::string_view arg = argv[index];
        if (arg == "--scene" && index + 1 < argc) {
            scene = argv[++index];
        } else if (arg == "--artifact-dir" && index + 1 < argc) {
            artifact_dir = argv[++index];
        } else {
            std::cerr
                << "usage: phos-n002-topology --artifact-dir PATH [--scene PATH]\n";
            return 2;
        }
    }
    if (artifact_dir.empty()) {
        std::cerr << "--artifact-dir is required\n";
        return 2;
    }

    try {
        fs::create_directories(artifact_dir / "frames");

        // Fresh runtime warm-up: it must exercise the same topology mutation
        // and object-local rebuild, but its timing is never retained.
        {
            lane_n::I001Runtime warmup(topology_options(scene));
            (void)warmup.run_frame(false);
            const auto source_quality = warmup.validate_last_frame();
            if (!source_quality.passed) {
                throw std::runtime_error(
                    "N002 topology source-state correctness failed");
            }
            const auto warmup_result = warmup.run_topology_churn_frame();
            const auto warmup_quality = warmup.validate_last_frame();
            if (!warmup_quality.passed ||
                warmup_result.stats.backend_rebuilds != 1U) {
                throw std::runtime_error(
                    "N002 topology warm-up rebuild correctness failed");
            }
        }

        // Fresh measured runtime so the recorded transition includes one real
        // topology mutation/rebuild rather than a post-warm-up steady state.
        lane_n::I001Runtime runtime(topology_options(scene));
        (void)runtime.run_frame(false);
        const auto source_quality = runtime.validate_last_frame();
        if (!source_quality.passed) {
            throw std::runtime_error(
                "N002 topology measured source-state correctness failed");
        }

        const auto measured = runtime.run_topology_churn_frame();
        const auto quality = runtime.validate_last_frame();
        const auto readback = runtime.renderer_readback();
        const auto output_rgb = rgb_from_rgba(readback);
        write_pfm(
            artifact_dir / "frames/output-005.pfm",
            readback.width,
            readback.height,
            output_rgb);

        const auto reference_start = std::chrono::steady_clock::now();
        const auto reference = lane_n::n001_render_reference(readback);
        const auto reference_seconds = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - reference_start).count();
        write_pfm(
            artifact_dir / "frames/reference-005.pfm",
            readback.width,
            readback.height,
            reference.rgb);

        const auto json = frame_json(
            measured,
            quality,
            reference,
            reference_seconds);
        write_runtime_json(
            artifact_dir / "n002-topology-runtime.json",
            runtime,
            json);

        std::cout
            << "N002 topology-changing-high-churn: GI="
            << measured.timings.complete_gpu_us
            << "us renderer="
            << measured.timings.complete_renderer_gpu_us
            << "us overlap="
            << measured.memory.old_new_overlap_bytes
            << "B peak="
            << measured.memory.peak_resident_bytes
            << "B reference="
            << reference.spp
            << "spp converged="
            << (reference.converged ? "yes" : "no")
            << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "N002 TOPOLOGY ERROR: " << error.what() << '\n';
        return 1;
    }
}

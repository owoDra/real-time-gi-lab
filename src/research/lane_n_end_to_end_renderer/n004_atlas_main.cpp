#include "n001_reference.hpp"
#include "n001_runtime.hpp"

#include <bit>
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

[[nodiscard]] std::vector<float> rgb_from_rgba(
    const lane_n::I001RendererReadback& frame) {
    const auto pixels = std::size_t(frame.width) * frame.height;
    if (frame.image_rgba.size() != pixels * 4U) {
        throw std::runtime_error("N004 RGBA payload size mismatch");
    }
    std::vector<float> rgb(pixels * 3U);
    for (std::size_t pixel = 0; pixel < pixels; ++pixel) {
        rgb[pixel * 3U + 0U] = frame.image_rgba[pixel * 4U + 0U];
        rgb[pixel * 3U + 1U] = frame.image_rgba[pixel * 4U + 1U];
        rgb[pixel * 3U + 2U] = frame.image_rgba[pixel * 4U + 2U];
    }
    return rgb;
}

void write_pfm(
    const fs::path& path,
    std::uint32_t width,
    std::uint32_t height,
    const std::vector<float>& rgb) {
    static_assert(std::endian::native == std::endian::little);
    if (rgb.size() != std::size_t(width) * height * 3U) {
        throw std::runtime_error("N004 PFM payload size mismatch");
    }
    fs::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("could not open N004 PFM");
    out << "PF\n" << width << ' ' << height << "\n-1.0\n";
    const auto row_floats = std::size_t(width) * 3U;
    for (std::uint32_t y = height; y-- > 0U;) {
        const auto* row = rgb.data() + std::size_t(y) * row_floats;
        out.write(
            reinterpret_cast<const char*>(row),
            std::streamsize(row_floats * sizeof(float)));
    }
    if (!out) throw std::runtime_error("N004 PFM write failed");
}

[[nodiscard]] std::string frame_name(std::uint32_t index) {
    std::ostringstream out;
    out << "frames/current-" << std::setw(3) << std::setfill('0')
        << index << ".pfm";
    return out.str();
}

void write_timing(
    std::ostream& out,
    const lane_n::I001FrameTimings& t,
    int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << std::setprecision(17)
        << pad << "{\n"
        << pad << "  \"complete_gi_gpu\": " << t.complete_gpu_us << ",\n"
        << pad << "  \"complete_renderer_gpu\": " << t.complete_renderer_gpu_us << ",\n"
        << pad << "  \"dynamic_update_wall\": " << t.dynamic_update_wall_us << ",\n"
        << pad << "  \"geometry_prepare_cpu\": " << t.geometry_prepare_cpu_us << ",\n"
        << pad << "  \"geometry_transfer_gpu\": " << t.geometry_transfer_gpu_us << ",\n"
        << pad << "  \"instance_transfer_gpu\": " << t.instance_transfer_gpu_us << ",\n"
        << pad << "  \"blas_update_gpu\": " << t.blas_update_us << ",\n"
        << pad << "  \"tlas_update_gpu\": " << t.tlas_update_us << ",\n"
        << pad << "  \"traversal_gpu\": " << t.traversal_us << "\n"
        << pad << "}";
}

void write_stats(
    std::ostream& out,
    const lane_n::I001FrameStats& s,
    int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << pad << "{\n"
        << pad << "  \"work_items\": " << s.work_items << ",\n"
        << pad << "  \"outputs\": " << s.outputs << ",\n"
        << pad << "  \"overflow\": " << s.overflow << ",\n"
        << pad << "  \"visible_owners\": " << s.visible_owners << ",\n"
        << pad << "  \"moved_primitives\": " << s.moved_primitives << ",\n"
        << pad << "  \"topology_mutations\": " << s.topology_mutations << ",\n"
        << pad << "  \"topology_replaced_primitives\": " << s.topology_replaced_primitives << ",\n"
        << pad << "  \"backend_rebuilds\": " << s.backend_rebuilds << ",\n"
        << pad << "  \"storage_allocations\": " << s.storage_allocations << ",\n"
        << pad << "  \"storage_updates\": " << s.storage_updates << ",\n"
        << pad << "  \"storage_invalidations\": " << s.storage_invalidations << ",\n"
        << pad << "  \"storage_failures\": " << s.storage_failures << "\n"
        << pad << "}";
}

void write_memory(
    std::ostream& out,
    const lane_n::I001Memory& m,
    int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << pad << "{\n"
        << pad << "  \"persistent\": " << m.persistent_bytes << ",\n"
        << pad << "  \"transient\": " << m.transient_bytes << ",\n"
        << pad << "  \"scratch\": " << m.scratch_bytes << ",\n"
        << pad << "  \"old_new_overlap\": " << m.old_new_overlap_bytes << ",\n"
        << pad << "  \"true_lifetime_peak\": " << m.peak_resident_bytes << ",\n"
        << pad << "  \"radiance_storage_persistent\": " << m.storage_capacity_bytes << ",\n"
        << pad << "  \"producer_stream_capacity\": " << m.stream_capacity_bytes << ",\n"
        << pad << "  \"image_transient\": " << m.image_bytes << "\n"
        << pad << "}";
}

struct FrameEvidence {
    lane_n::I001FrameResult result;
    lane_n::I001RendererReadback readback;
    std::string image_path;
};

} // namespace

int main(int argc, char** argv) {
    fs::path scene;
    fs::path artifact_dir;
    std::string scenario_name = "static";
    std::uint32_t source_warmup_frames = 32U;
    std::uint32_t target_frames = 1U;
    bool topology = false;
    bool one_bounce_reference = false;

    for (int index = 1; index < argc; ++index) {
        const std::string_view arg = argv[index];
        if (arg == "--scene" && index + 1 < argc) {
            scene = argv[++index];
        } else if (arg == "--artifact-dir" && index + 1 < argc) {
            artifact_dir = argv[++index];
        } else if (arg == "--scenario" && index + 1 < argc) {
            scenario_name = argv[++index];
        } else if (arg == "--source-warmup-frames" && index + 1 < argc) {
            source_warmup_frames = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--target-frames" && index + 1 < argc) {
            target_frames = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--topology") {
            topology = true;
        } else if (arg == "--one-bounce-reference") {
            one_bounce_reference = true;
        } else {
            std::cerr << "usage: phos-n004-atlas --artifact-dir PATH --scene PATH "
                         "[--scenario NAME] [--source-warmup-frames N] "
                         "[--target-frames N] [--topology] [--one-bounce-reference]\n";
            return 2;
        }
    }
    if (artifact_dir.empty() || scene.empty() || source_warmup_frames == 0U || target_frames == 0U) {
        std::cerr << "invalid N004 atlas arguments\n";
        return 2;
    }

    try {
        const auto scenario = lane_n::i001_parse_scenario(scenario_name);
        lane_n::I001Options options{};
        options.scene = scene;
        options.variant = lane_n::I001Variant::LaneEFinalHwrt;
        options.scenario = scenario;
        options.validation = true;
        lane_n::I001Runtime runtime(options);

        (void)runtime.run_frame(false);
        if (!runtime.validate_last_frame().passed) {
            throw std::runtime_error("N004 source correctness failed");
        }
        for (std::uint32_t index = 1; index < source_warmup_frames; ++index) {
            (void)runtime.run_frame(false);
        }

        fs::create_directories(artifact_dir / "frames");
        std::vector<FrameEvidence> frames;
        frames.reserve(target_frames);
        for (std::uint32_t index = 0; index < target_frames; ++index) {
            lane_n::I001FrameResult result{};
            if (index == 0U && topology) {
                result = runtime.run_topology_churn_frame();
            } else {
                result = runtime.run_frame(true);
            }
            const auto quality = runtime.validate_last_frame();
            if (!quality.passed || result.stats.storage_failures != 0U || result.stats.overflow != 0U) {
                throw std::runtime_error("N004 target correctness/capacity failed");
            }
            auto readback = runtime.renderer_readback();
            const auto path = frame_name(index);
            write_pfm(
                artifact_dir / path,
                readback.width,
                readback.height,
                rgb_from_rgba(readback));
            frames.push_back({result, std::move(readback), path});
        }

        lane_n::N001ReferenceSettings reference_settings{};
        const auto reference = lane_n::n001_render_reference(frames.front().readback, reference_settings);
        if (!reference.converged) {
            throw std::runtime_error("N004 8-bounce reference did not converge");
        }
        const std::string reference_path = "frames/reference-8bounce.pfm";
        write_pfm(
            artifact_dir / reference_path,
            frames.front().readback.width,
            frames.front().readback.height,
            reference.rgb);

        lane_n::N001ReferenceResult reference_one{};
        std::string reference_one_path;
        if (one_bounce_reference) {
            reference_settings.max_diffuse_bounces = 1U;
            reference_one = lane_n::n001_render_reference(frames.front().readback, reference_settings);
            if (!reference_one.converged) {
                throw std::runtime_error("N004 1-bounce reference did not converge");
            }
            reference_one_path = "frames/reference-1bounce.pfm";
            write_pfm(
                artifact_dir / reference_one_path,
                frames.front().readback.width,
                frames.front().readback.height,
                reference_one.rgb);
        }

        std::ofstream out(artifact_dir / "n004-evidence.json");
        if (!out) throw std::runtime_error("could not open N004 evidence JSON");
        out << std::setprecision(17)
            << "{\n"
            << "  \"schema_version\": 1,\n"
            << "  \"protocol_version\": \"n004-atlas-evidence-v1\",\n"
            << "  \"scenario\": \"" << scenario_name << "\",\n"
            << "  \"topology\": " << (topology ? "true" : "false") << ",\n"
            << "  \"source_warmup_frames\": " << source_warmup_frames << ",\n"
            << "  \"probe_spacing_world\": " << frames.front().readback.params.scene_origin_spacing[3] << ",\n"
            << "  \"device\": {\n"
            << "    \"name\": \"" << runtime.device_name() << "\",\n"
            << "    \"driver_name\": \"" << runtime.driver_name() << "\",\n"
            << "    \"driver_info\": \"" << runtime.driver_info() << "\",\n"
            << "    \"api_version\": " << runtime.api_version() << ",\n"
            << "    \"timestamp_period_ns\": " << runtime.timestamp_period_ns() << "\n"
            << "  },\n"
            << "  \"reference\": {\n"
            << "    \"path\": \"" << reference_path << "\",\n"
            << "    \"spp\": " << reference.spp << ",\n"
            << "    \"converged\": true,\n"
            << "    \"replicate_p99_abs_luminance\": " << reference.replicate_p99_abs_luminance << ",\n"
            << "    \"replicate_p99_relative_luminance\": " << reference.replicate_p99_relative_luminance << "\n"
            << "  },\n";
        if (one_bounce_reference) {
            out << "  \"reference_one_bounce\": {\n"
                << "    \"path\": \"" << reference_one_path << "\",\n"
                << "    \"spp\": " << reference_one.spp << ",\n"
                << "    \"converged\": true,\n"
                << "    \"replicate_p99_abs_luminance\": " << reference_one.replicate_p99_abs_luminance << ",\n"
                << "    \"replicate_p99_relative_luminance\": " << reference_one.replicate_p99_relative_luminance << "\n"
                << "  },\n";
        }
        out << "  \"frames\": [\n";
        for (std::size_t index = 0; index < frames.size(); ++index) {
            const auto& frame = frames[index];
            out << "    {\n"
                << "      \"index\": " << index << ",\n"
                << "      \"image\": \"" << frame.image_path << "\",\n"
                << "      \"timing_us\": ";
            write_timing(out, frame.result.timings, 6);
            out << ",\n      \"stats\": ";
            write_stats(out, frame.result.stats, 6);
            out << ",\n      \"memory_bytes\": ";
            write_memory(out, frame.result.memory, 6);
            out << "\n    }";
            if (index + 1U != frames.size()) out << ',';
            out << '\n';
        }
        out << "  ]\n}\n";
        if (!out) throw std::runtime_error("N004 evidence JSON write failed");

        std::cout << "N004 atlas evidence: " << artifact_dir << '\n'
                  << "scenario=" << scenario_name
                  << " target_frames=" << target_frames
                  << " reference_spp=" << reference.spp << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "N004 atlas failure: " << error.what() << '\n';
        return 1;
    }
}

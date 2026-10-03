#include "n001_reference.hpp"
#include "n001_runtime.hpp"

#include <algorithm>
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

[[nodiscard]] std::vector<float> rgb_from_rgba(const lane_n::I001RendererReadback& frame) {
    const auto pixels = std::size_t(frame.width) * frame.height;
    if (frame.image_rgba.size() != pixels * 4U) throw std::runtime_error("N004 RGBA payload size mismatch");
    std::vector<float> rgb(pixels * 3U);
    for (std::size_t pixel = 0; pixel < pixels; ++pixel) {
        for (std::size_t channel = 0; channel < 3U; ++channel) {
            rgb[pixel * 3U + channel] = frame.image_rgba[pixel * 4U + channel];
        }
    }
    return rgb;
}

void write_pfm(const fs::path& path, std::uint32_t width, std::uint32_t height, const std::vector<float>& rgb) {
    static_assert(std::endian::native == std::endian::little);
    if (rgb.size() != std::size_t(width) * height * 3U) throw std::runtime_error("N004 PFM payload size mismatch");
    fs::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("could not open N004 PFM");
    out << "PF\n" << width << ' ' << height << "\n-1.0\n";
    const auto row_floats = std::size_t(width) * 3U;
    for (std::uint32_t y = height; y-- > 0U;) {
        const auto* row = rgb.data() + std::size_t(y) * row_floats;
        out.write(reinterpret_cast<const char*>(row), std::streamsize(row_floats * sizeof(float)));
    }
    if (!out) throw std::runtime_error("N004 PFM write failed");
}

[[nodiscard]] std::string indexed_path(const char* prefix, std::uint32_t index) {
    std::ostringstream out;
    out << "frames/" << prefix << '-' << std::setw(3) << std::setfill('0') << index << ".pfm";
    return out.str();
}

[[nodiscard]] std::vector<float> parse_fractions(const std::string& raw) {
    std::vector<float> values;
    std::stringstream stream(raw);
    std::string token;
    while (std::getline(stream, token, ',')) {
        if (token.empty()) throw std::runtime_error("N004 motion fraction contains an empty item");
        const float value = std::stof(token);
        if (!(value >= 0.0F && value <= 1.0F)) throw std::runtime_error("N004 motion fraction outside [0,1]");
        values.push_back(value);
    }
    return values;
}

void write_timing(std::ostream& out, const lane_n::I001FrameTimings& t, int indent) {
    const std::string p(static_cast<std::size_t>(indent), ' ');
    out << std::setprecision(17) << p << "{\n"
        << p << "  \"complete_gi_gpu\": " << t.complete_gpu_us << ",\n"
        << p << "  \"complete_renderer_gpu\": " << t.complete_renderer_gpu_us << ",\n"
        << p << "  \"dynamic_update_wall\": " << t.dynamic_update_wall_us << ",\n"
        << p << "  \"geometry_prepare_cpu\": " << t.geometry_prepare_cpu_us << ",\n"
        << p << "  \"geometry_transfer_gpu\": " << t.geometry_transfer_gpu_us << ",\n"
        << p << "  \"instance_transfer_gpu\": " << t.instance_transfer_gpu_us << ",\n"
        << p << "  \"blas_update_gpu\": " << t.blas_update_us << ",\n"
        << p << "  \"tlas_update_gpu\": " << t.tlas_update_us << ",\n"
        << p << "  \"traversal_gpu\": " << t.traversal_us << "\n" << p << "}";
}

void write_stats(std::ostream& out, const lane_n::I001FrameStats& s, int indent) {
    const std::string p(static_cast<std::size_t>(indent), ' ');
    out << p << "{\n"
        << p << "  \"work_items\": " << s.work_items << ",\n"
        << p << "  \"outputs\": " << s.outputs << ",\n"
        << p << "  \"overflow\": " << s.overflow << ",\n"
        << p << "  \"visible_owners\": " << s.visible_owners << ",\n"
        << p << "  \"moved_primitives\": " << s.moved_primitives << ",\n"
        << p << "  \"topology_mutations\": " << s.topology_mutations << ",\n"
        << p << "  \"topology_replaced_primitives\": " << s.topology_replaced_primitives << ",\n"
        << p << "  \"backend_rebuilds\": " << s.backend_rebuilds << ",\n"
        << p << "  \"storage_allocations\": " << s.storage_allocations << ",\n"
        << p << "  \"storage_updates\": " << s.storage_updates << ",\n"
        << p << "  \"storage_invalidations\": " << s.storage_invalidations << ",\n"
        << p << "  \"storage_failures\": " << s.storage_failures << "\n" << p << "}";
}

void write_memory(std::ostream& out, const lane_n::I001Memory& m, int indent) {
    const std::string p(static_cast<std::size_t>(indent), ' ');
    out << p << "{\n"
        << p << "  \"persistent\": " << m.persistent_bytes << ",\n"
        << p << "  \"transient\": " << m.transient_bytes << ",\n"
        << p << "  \"scratch\": " << m.scratch_bytes << ",\n"
        << p << "  \"old_new_overlap\": " << m.old_new_overlap_bytes << ",\n"
        << p << "  \"true_lifetime_peak\": " << m.peak_resident_bytes << ",\n"
        << p << "  \"radiance_storage_persistent\": " << m.storage_capacity_bytes << ",\n"
        << p << "  \"producer_stream_capacity\": " << m.stream_capacity_bytes << ",\n"
        << p << "  \"image_transient\": " << m.image_bytes << "\n" << p << "}";
}

struct FrameEvidence {
    lane_n::I001FrameResult result;
    lane_n::I001RendererReadback readback;
    std::string image_path;
    float motion_fraction{1.0F};
};

struct ReferenceMeta {
    std::string path;
    std::uint32_t spp{};
    double p99_abs{};
    double p99_relative{};
};

[[nodiscard]] ReferenceMeta render_reference(
    const lane_n::I001RendererReadback& readback,
    lane_n::N001ReferenceSettings settings,
    const fs::path& artifact_dir,
    const std::string& relative_path) {
    const auto result = lane_n::n001_render_reference(readback, settings);
    if (!result.converged) throw std::runtime_error("N004 reference did not converge");
    write_pfm(artifact_dir / relative_path, readback.width, readback.height, result.rgb);
    return {relative_path, result.spp, result.replicate_p99_abs_luminance, result.replicate_p99_relative_luminance};
}

void write_reference(std::ostream& out, const ReferenceMeta& ref, int indent) {
    const std::string p(static_cast<std::size_t>(indent), ' ');
    out << std::setprecision(17) << p << "{\n"
        << p << "  \"path\": \"" << ref.path << "\",\n"
        << p << "  \"spp\": " << ref.spp << ",\n"
        << p << "  \"converged\": true,\n"
        << p << "  \"replicate_p99_abs_luminance\": " << ref.p99_abs << ",\n"
        << p << "  \"replicate_p99_relative_luminance\": " << ref.p99_relative << "\n" << p << "}";
}

} // namespace

int main(int argc, char** argv) {
    fs::path scene;
    fs::path artifact_dir;
    std::string scenario_name = "static";
    std::uint32_t source_warmup_frames = 32U;
    std::uint32_t target_frames = 1U;
    bool topology = false;
    bool one_bounce_reference = false;
    std::string motion_fraction_text;

    for (int index = 1; index < argc; ++index) {
        const std::string_view arg = argv[index];
        if (arg == "--scene" && index + 1 < argc) scene = argv[++index];
        else if (arg == "--artifact-dir" && index + 1 < argc) artifact_dir = argv[++index];
        else if (arg == "--scenario" && index + 1 < argc) scenario_name = argv[++index];
        else if (arg == "--source-warmup-frames" && index + 1 < argc) source_warmup_frames = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        else if (arg == "--target-frames" && index + 1 < argc) target_frames = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        else if (arg == "--motion-fractions" && index + 1 < argc) motion_fraction_text = argv[++index];
        else if (arg == "--topology") topology = true;
        else if (arg == "--one-bounce-reference") one_bounce_reference = true;
        else {
            std::cerr << "usage: phos-n004-atlas --artifact-dir PATH --scene PATH [--scenario NAME] "
                         "[--source-warmup-frames N] [--target-frames N] [--motion-fractions CSV] "
                         "[--topology] [--one-bounce-reference]\n";
            return 2;
        }
    }
    if (artifact_dir.empty() || scene.empty() || source_warmup_frames == 0U || target_frames == 0U) {
        std::cerr << "invalid N004 atlas arguments\n";
        return 2;
    }

    try {
        auto fractions = motion_fraction_text.empty() ? std::vector<float>{} : parse_fractions(motion_fraction_text);
        if (!fractions.empty() && fractions.size() != target_frames) {
            throw std::runtime_error("N004 motion fraction count must match target frames");
        }
        if (fractions.empty()) fractions.assign(target_frames, 1.0F);

        const auto scenario = lane_n::i001_parse_scenario(scenario_name);
        lane_n::I001Options options{};
        options.scene = scene;
        options.variant = lane_n::I001Variant::LaneEFinalHwrt;
        options.scenario = scenario;
        options.validation = true;
        lane_n::I001Runtime runtime(options);

        (void)runtime.run_frame(false);
        if (!runtime.validate_last_frame().passed) throw std::runtime_error("N004 source correctness failed");
        for (std::uint32_t index = 1; index < source_warmup_frames; ++index) (void)runtime.run_frame(false);

        fs::create_directories(artifact_dir / "frames");
        std::vector<FrameEvidence> frames;
        frames.reserve(target_frames);
        for (std::uint32_t index = 0; index < target_frames; ++index) {
            runtime.set_n004_motion_fraction(fractions[index]);
            lane_n::I001FrameResult result{};
            if (index == 0U && topology) result = runtime.run_topology_churn_frame();
            else result = runtime.run_frame(true);
            const auto quality = runtime.validate_last_frame();
            if (!quality.passed || result.stats.storage_failures != 0U || result.stats.overflow != 0U) {
                throw std::runtime_error("N004 target correctness/capacity failed");
            }
            auto readback = runtime.renderer_readback();
            const auto path = indexed_path("current", index);
            write_pfm(artifact_dir / path, readback.width, readback.height, rgb_from_rgba(readback));
            frames.push_back({result, std::move(readback), path, fractions[index]});
        }

        const bool varying_state = !std::all_of(
            fractions.begin(), fractions.end(),
            [&](float value) { return value == fractions.front(); });
        lane_n::N001ReferenceSettings settings{};
        std::vector<ReferenceMeta> references;
        references.reserve(frames.size());
        if (varying_state) {
            for (std::uint32_t index = 0; index < frames.size(); ++index) {
                references.push_back(render_reference(
                    frames[index].readback, settings, artifact_dir,
                    indexed_path("reference-8bounce", index)));
            }
        } else {
            const auto shared = render_reference(
                frames.front().readback, settings, artifact_dir,
                "frames/reference-8bounce.pfm");
            references.assign(frames.size(), shared);
        }

        ReferenceMeta reference_one{};
        if (one_bounce_reference) {
            settings.max_diffuse_bounces = 1U;
            reference_one = render_reference(
                frames.front().readback, settings, artifact_dir,
                "frames/reference-1bounce.pfm");
        }

        std::ofstream out(artifact_dir / "n004-evidence.json");
        if (!out) throw std::runtime_error("could not open N004 evidence JSON");
        out << std::setprecision(17)
            << "{\n  \"schema_version\": 1,\n"
            << "  \"protocol_version\": \"n004-atlas-evidence-v2\",\n"
            << "  \"scenario\": \"" << scenario_name << "\",\n"
            << "  \"topology\": " << (topology ? "true" : "false") << ",\n"
            << "  \"source_warmup_frames\": " << source_warmup_frames << ",\n"
            << "  \"probe_spacing_world\": " << frames.front().readback.params.scene_origin_spacing[3] << ",\n"
            << "  \"device\": {\n"
            << "    \"name\": \"" << runtime.device_name() << "\",\n"
            << "    \"driver_name\": \"" << runtime.driver_name() << "\",\n"
            << "    \"driver_info\": \"" << runtime.driver_info() << "\",\n"
            << "    \"api_version\": " << runtime.api_version() << ",\n"
            << "    \"timestamp_period_ns\": " << runtime.timestamp_period_ns() << "\n  },\n";
        if (one_bounce_reference) {
            out << "  \"reference_one_bounce\": ";
            write_reference(out, reference_one, 2);
            out << ",\n";
        }
        out << "  \"frames\": [\n";
        for (std::size_t index = 0; index < frames.size(); ++index) {
            const auto& frame = frames[index];
            out << "    {\n"
                << "      \"index\": " << index << ",\n"
                << "      \"motion_fraction\": " << frame.motion_fraction << ",\n"
                << "      \"image\": \"" << frame.image_path << "\",\n"
                << "      \"reference\": ";
            write_reference(out, references[index], 6);
            out << ",\n      \"timing_us\": ";
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
                  << "scenario=" << scenario_name << " target_frames=" << target_frames
                  << " varying_state=" << (varying_state ? "yes" : "no") << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "N004 atlas failure: " << error.what() << '\n';
        return 1;
    }
}

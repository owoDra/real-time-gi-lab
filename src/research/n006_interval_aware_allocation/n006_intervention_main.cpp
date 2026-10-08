#include "n006_runtime.hpp"
#include "../lane_n_end_to_end_renderer/n001_reference.hpp"

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

[[nodiscard]] std::vector<float> rgb_from_rgba(
    const lane_n::I001RendererReadback& frame) {
    const auto pixels = std::size_t(frame.width) * frame.height;
    if (frame.image_rgba.size() != pixels * 4U) {
        throw std::runtime_error("N006 RGBA payload size mismatch");
    }
    std::vector<float> rgb(pixels * 3U);
    for (std::size_t pixel = 0; pixel < pixels; ++pixel) {
        for (std::size_t channel = 0; channel < 3U; ++channel) {
            rgb[pixel * 3U + channel] = frame.image_rgba[pixel * 4U + channel];
        }
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
        throw std::runtime_error("N006 PFM payload size mismatch");
    }
    fs::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("could not open N006 PFM");
    out << "PF\n" << width << ' ' << height << "\n-1.0\n";
    const auto row_floats = std::size_t(width) * 3U;
    for (std::uint32_t y = height; y-- > 0U;) {
        const auto* row = rgb.data() + std::size_t(y) * row_floats;
        out.write(
            reinterpret_cast<const char*>(row),
            std::streamsize(row_floats * sizeof(float)));
    }
    if (!out) throw std::runtime_error("N006 PFM write failed");
}

[[nodiscard]] std::string indexed_path(
    const char* prefix,
    std::uint32_t index) {
    std::ostringstream out;
    out << "frames/" << prefix << '-' << std::setw(3) << std::setfill('0')
        << index << ".pfm";
    return out.str();
}

template <typename T>
[[nodiscard]] std::vector<T> parse_csv(const std::string& raw) {
    std::vector<T> values;
    std::stringstream stream(raw);
    std::string token;
    while (std::getline(stream, token, ',')) {
        if (token.empty()) {
            throw std::runtime_error("N006 CSV contains an empty item");
        }
        if constexpr (std::is_same_v<T, float>) {
            values.push_back(std::stof(token));
        } else {
            values.push_back(static_cast<T>(std::stoul(token)));
        }
    }
    return values;
}

[[nodiscard]] lane_n::N006ExtraMode parse_mode(std::string_view value) {
    if (value == "current") return lane_n::N006ExtraMode::Current;
    if (value == "uniform-extra-rays") return lane_n::N006ExtraMode::Uniform;
    if (value == "targeted-extra-rays") return lane_n::N006ExtraMode::Targeted;
    throw std::runtime_error("unknown N006 mode");
}

[[nodiscard]] const char* mode_name(lane_n::N006ExtraMode value) noexcept {
    switch (value) {
    case lane_n::N006ExtraMode::Current: return "current";
    case lane_n::N006ExtraMode::Uniform: return "uniform-extra-rays";
    case lane_n::N006ExtraMode::Targeted: return "targeted-extra-rays";
    }
    return "unknown";
}

struct ReferenceMeta {
    std::string path;
    std::uint32_t spp{};
    double p99_abs{};
    double p99_relative{};
};

[[nodiscard]] ReferenceMeta render_reference(
    const lane_n::I001RendererReadback& readback,
    const fs::path& artifact_dir,
    const std::string& relative_path) {
    const auto result = lane_n::n001_render_reference(readback, {});
    if (!result.converged) {
        throw std::runtime_error("N006 reference did not converge");
    }
    write_pfm(
        artifact_dir / relative_path,
        readback.width,
        readback.height,
        result.rgb);
    return {
        relative_path,
        result.spp,
        result.replicate_p99_abs_luminance,
        result.replicate_p99_relative_luminance,
    };
}

void write_reference(
    std::ostream& out,
    const ReferenceMeta& reference) {
    out << std::setprecision(17)
        << "{\"path\":\"" << reference.path << "\","
        << "\"spp\":" << reference.spp << ','
        << "\"converged\":true,"
        << "\"replicate_p99_abs_luminance\":" << reference.p99_abs << ','
        << "\"replicate_p99_relative_luminance\":" << reference.p99_relative
        << '}';
}

void write_timing(
    std::ostream& out,
    const lane_n::I001FrameTimings& t,
    double extra_producer_gpu_us) {
    out << std::setprecision(17)
        << "{\"complete_gi_gpu\":" << t.complete_gpu_us << ','
        << "\"complete_renderer_gpu\":" << t.complete_renderer_gpu_us << ','
        << "\"extra_producer_gpu\":" << extra_producer_gpu_us << ','
        << "\"producer_gpu\":" << t.producer_us << ','
        << "\"ray_prepare_gpu\":" << t.ray_prepare_us << ','
        << "\"traversal_gpu\":" << t.traversal_us << ','
        << "\"radiance_gpu\":" << t.radiance_us << ','
        << "\"merge_gpu\":" << t.merge_us << ','
        << "\"storage_update_gpu\":" << t.storage_update_us << ','
        << "\"resolve_gpu\":" << t.resolve_us << ','
        << "\"dynamic_update_wall\":" << t.dynamic_update_wall_us << ','
        << "\"geometry_transfer_gpu\":" << t.geometry_transfer_gpu_us << ','
        << "\"instance_transfer_gpu\":" << t.instance_transfer_gpu_us << ','
        << "\"blas_update_gpu\":" << t.blas_update_us << ','
        << "\"tlas_update_gpu\":" << t.tlas_update_us
        << '}';
}

void write_stats(
    std::ostream& out,
    const lane_n::I001FrameStats& s) {
    out << "{\"work_items\":" << s.work_items << ','
        << "\"outputs\":" << s.outputs << ','
        << "\"overflow\":" << s.overflow << ','
        << "\"visible_owners\":" << s.visible_owners << ','
        << "\"moved_primitives\":" << s.moved_primitives << ','
        << "\"topology_mutations\":" << s.topology_mutations << ','
        << "\"topology_replaced_primitives\":" << s.topology_replaced_primitives << ','
        << "\"backend_rebuilds\":" << s.backend_rebuilds << ','
        << "\"storage_allocations\":" << s.storage_allocations << ','
        << "\"storage_updates\":" << s.storage_updates << ','
        << "\"storage_invalidations\":" << s.storage_invalidations << ','
        << "\"storage_failures\":" << s.storage_failures
        << '}';
}

void write_memory(
    std::ostream& out,
    const lane_n::I001Memory& m) {
    out << "{\"persistent\":" << m.persistent_bytes << ','
        << "\"transient\":" << m.transient_bytes << ','
        << "\"scratch\":" << m.scratch_bytes << ','
        << "\"old_new_overlap\":" << m.old_new_overlap_bytes << ','
        << "\"true_lifetime_peak\":" << m.peak_resident_bytes << ','
        << "\"radiance_storage_persistent\":" << m.storage_capacity_bytes << ','
        << "\"producer_stream_capacity\":" << m.stream_capacity_bytes << ','
        << "\"image_transient\":" << m.image_bytes
        << '}';
}

void write_extra(
    std::ostream& out,
    const lane_n::N006ExtraStats& e) {
    out << std::setprecision(17)
        << "{\"base_traced_rays\":" << e.base_traced_rays << ','
        << "\"extra_rays_requested\":" << e.extra_rays_requested << ','
        << "\"extra_rays_traced\":" << e.extra_rays_traced << ','
        << "\"extra_work_items\":" << e.extra_work_items << ','
        << "\"eligible_owner_count\":" << e.eligible_owner_count << ','
        << "\"selected_owner_count\":" << e.selected_owner_count << ','
        << "\"eligible_probe_count\":" << e.eligible_probe_count << ','
        << "\"extra_probe_count\":" << e.extra_probe_count << ','
        << "\"extra_probe_fraction\":" << e.extra_probe_fraction << ','
        << "\"extra_producer_gpu_us\":" << e.extra_producer_gpu_us << ','
        << "\"base_prefix_correct\":" << (e.base_prefix_correct ? "true" : "false") << ','
        << "\"extra_work_correct\":" << (e.extra_work_correct ? "true" : "false")
        << ",\"influence_trace\":{"
        << "\"available\":" << (e.influence_trace.available ? "true" : "false");
    if (e.influence_trace.available) {
        const auto& trace = e.influence_trace;
        out << ",\"tile_id\":" << trace.tile_id
            << ",\"cascade\":" << trace.cascade
            << ",\"output_id\":" << trace.output_id
            << ",\"probe_x\":" << trace.probe_x
            << ",\"probe_y\":" << trace.probe_y
            << ",\"probe_z\":" << trace.probe_z
            << ",\"base_ray_count\":" << trace.base_ray_count
            << ",\"extra_ray_count\":" << trace.extra_ray_count
            << ",\"base_radiance_sum16\":" << trace.base_radiance_sum16
            << ",\"extra_radiance_sum16\":" << trace.extra_radiance_sum16
            << ",\"base_zero_rays\":" << trace.base_zero_rays
            << ",\"extra_zero_rays\":" << trace.extra_zero_rays
            << ",\"base_output_mean16\":" << trace.base_output_mean16
            << ",\"target_output_mean16\":" << trace.target_output_mean16
            << ",\"shared_probe_outputs\":" << trace.shared_probe_outputs
            << ",\"before_storage_sum16\":" << trace.before_storage_sum16
            << ",\"after_storage_sum16\":" << trace.after_storage_sum16
            << ",\"before_storage_mean16\":" << trace.before_storage_mean16
            << ",\"after_storage_mean16\":" << trace.after_storage_mean16
            << ",\"observed_storage_sum16\":" << trace.observed_storage_sum16
            << ",\"observed_storage_outputs\":" << trace.observed_storage_outputs;
    }
    out << "}}";
}

void write_hit(
    std::ostream& out,
    const lane_n::I001N004HitDiagnostics& d) {
    out << "{\"strict_mismatches\":" << d.strict_mismatches << ','
        << "\"surface_tie_equivalent_mismatches\":"
        << d.surface_tie_equivalent_mismatches << ','
        << "\"substantive_mismatches\":" << d.substantive_mismatches
        << '}';
}

struct FrameEvidence {
    lane_n::N006FrameResult result;
    lane_n::I001N004HitDiagnostics hits;    lane_n::I001RendererReadback readback;
    std::string image_path;
    float motion_fraction{};
    std::uint32_t owner_budget{};
    bool internal_correctness{};
};

[[nodiscard]] bool frame_correct(
    const lane_n::N006FrameResult& result,
    const lane_n::I001N004HitDiagnostics& hits) noexcept {
    return result.extra.base_prefix_correct &&
        result.extra.extra_work_correct &&
        hits.substantive_mismatches == 0U &&
        result.frame.stats.overflow == 0U &&
        result.frame.stats.storage_failures == 0U;
}

} // namespace

int main(int argc, char** argv) {
    fs::path scene;
    fs::path artifact_dir;
    std::string scenario_name = "static";
    std::string mode_text = "current";
    std::string motion_fraction_text;
    std::string owner_budget_text;
    std::uint32_t source_warmup_frames = 32U;
    std::uint32_t target_frames = 1U;
    float depth_threshold = 0.01F;
    std::uint32_t extra_rays_per_probe = 4U;
    std::uint32_t selected_tile_id = 0xffffffffU;
    std::uint32_t selected_cascade = 0xffffffffU;
    bool topology = false;
    bool skip_reference = false;
    bool capture_visible_tiles = false;

    for (int index = 1; index < argc; ++index) {
        const std::string_view arg = argv[index];
        if (arg == "--scene" && index + 1 < argc) scene = argv[++index];
        else if (arg == "--artifact-dir" && index + 1 < argc) artifact_dir = argv[++index];
        else if (arg == "--scenario" && index + 1 < argc) scenario_name = argv[++index];
        else if (arg == "--mode" && index + 1 < argc) mode_text = argv[++index];
        else if (arg == "--source-warmup-frames" && index + 1 < argc) {
            source_warmup_frames = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--target-frames" && index + 1 < argc) {
            target_frames = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--motion-fractions" && index + 1 < argc) {
            motion_fraction_text = argv[++index];
        } else if (arg == "--owner-budgets" && index + 1 < argc) {
            owner_budget_text = argv[++index];
        } else if (arg == "--depth-threshold" && index + 1 < argc) {
            depth_threshold = std::stof(argv[++index]);
        } else if (arg == "--extra-rays-per-probe" && index + 1 < argc) {
            extra_rays_per_probe = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--selected-tile-id" && index + 1 < argc) {
            selected_tile_id = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--selected-cascade" && index + 1 < argc) {
            selected_cascade = static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else if (arg == "--topology") topology = true;
        else if (arg == "--skip-reference") skip_reference = true;
        else if (arg == "--capture-visible-tiles") capture_visible_tiles = true;
        else {
            std::cerr
                << "usage: phos-n006-candidate --artifact-dir PATH --scene PATH "
                   "--scenario NAME --mode current|targeted-extra-rays "
                   "--owner-budgets CSV [--motion-fractions CSV] [--topology] "
                   "[--source-warmup-frames N] [--target-frames N] "
                   "[--depth-threshold F] [--extra-rays-per-probe N] "
                   "[--selected-tile-id N --selected-cascade N] [--skip-reference]\n";
            return 2;
        }
    }

    try {
        if (artifact_dir.empty() || scene.empty() || source_warmup_frames == 0U ||
            target_frames == 0U) {
            throw std::runtime_error("invalid N006 candidate arguments");
        }
        const auto mode = parse_mode(mode_text);
        auto fractions = motion_fraction_text.empty()
            ? std::vector<float>(target_frames, 1.0F)
            : parse_csv<float>(motion_fraction_text);
        auto budgets = owner_budget_text.empty()
            ? std::vector<std::uint32_t>(target_frames, 0U)
            : parse_csv<std::uint32_t>(owner_budget_text);
        if (fractions.size() != target_frames || budgets.size() != target_frames) {
            throw std::runtime_error("N006 schedule length must match target frames");
        }
        if (mode == lane_n::N006ExtraMode::Targeted &&
            (selected_tile_id >= 320U * 180U || selected_cascade >= 4U ||
             !std::all_of(budgets.begin(), budgets.end(),
                 [](auto value) { return value == 1U; }))) {
            throw std::runtime_error("N006 targeted mode requires tile 0..57599, cascade 0..3 and owner budget 1 per frame");
        }
        for (const auto fraction : fractions) {
            if (!(fraction >= 0.0F && fraction <= 1.0F)) {
                throw std::runtime_error("N006 motion fraction outside [0,1]");
            }
        }
        if (mode == lane_n::N006ExtraMode::Current &&
            std::any_of(budgets.begin(), budgets.end(), [](auto value) { return value != 0U; })) {
            throw std::runtime_error("N006 current mode must use zero owner budgets");
        }

        lane_n::I001Options options{};
        options.scene = scene;
        options.variant = lane_n::I001Variant::LaneEFinalHwrt;
        options.scenario = lane_n::i001_parse_scenario(scenario_name);
        options.validation = true;
        lane_n::N006Runtime runtime(options);

        const lane_n::N006ExtraRequest current_request{};
        auto source = runtime.run_frame(false, current_request);
        const auto source_hits = runtime.n004_hit_diagnostics();
        const bool source_correct = frame_correct(source, source_hits);
        for (std::uint32_t index = 1; index < source_warmup_frames; ++index) {
            (void)runtime.run_frame(false, current_request);
        }

        fs::create_directories(artifact_dir / "frames");
        std::vector<FrameEvidence> frames;
        frames.reserve(target_frames);
        for (std::uint32_t index = 0; index < target_frames; ++index) {
            runtime.set_motion_fraction(fractions[index]);
            const lane_n::N006ExtraRequest request{
                mode,
                budgets[index],
                depth_threshold,
                extra_rays_per_probe,
                selected_tile_id,
                selected_cascade,
            };
            lane_n::N006FrameResult result =
                (index == 0U && topology)
                ? runtime.run_topology_churn_frame(request)
                : runtime.run_frame(true, request);
            const auto hits = runtime.n004_hit_diagnostics();
            auto readback = runtime.renderer_readback();
            const auto image_path = indexed_path("candidate", index);
            write_pfm(
                artifact_dir / image_path,
                readback.width,
                readback.height,
                rgb_from_rgba(readback));
            frames.push_back({
                result,
                hits,
                std::move(readback),
                image_path,
                fractions[index],
                budgets[index],
                frame_correct(result, hits),
            });
        }

        if (capture_visible_tiles) {
            const auto tiles = runtime.visible_tile_ids();
            std::ofstream visible_file(artifact_dir / "n006-visible-tiles.json");
            if (!visible_file) throw std::runtime_error("N006 visible tile capture file open failed");
            visible_file << "{\"schema_version\":1,\"width\":320,\"height\":180,\"tile_ids\":[";
            for (std::size_t i = 0; i < tiles.size(); ++i) {
                if (i != 0U) visible_file << ',';
                visible_file << tiles[i];
            }
            visible_file << "]}\n";
            if (!visible_file) throw std::runtime_error("N006 visible tile capture write failed");
        }

        const bool varying_state = !std::all_of(
            fractions.begin(),
            fractions.end(),
            [&](float value) { return value == fractions.front(); });
        std::vector<ReferenceMeta> references;
        if (!skip_reference) {
            references.reserve(frames.size());
            if (varying_state) {
                for (std::uint32_t index = 0; index < frames.size(); ++index) {
                    references.push_back(render_reference(
                        frames[index].readback,
                        artifact_dir,
                        indexed_path("reference-8bounce", index)));
                }
            } else {
                const auto shared = render_reference(
                    frames.front().readback,
                    artifact_dir,
                    "frames/reference-8bounce.pfm");
                references.assign(frames.size(), shared);
            }
        }

        std::ofstream out(artifact_dir / "n006-candidate-evidence.json");
        if (!out) throw std::runtime_error("could not open N006 evidence JSON");
        out << std::setprecision(17)
            << "{\n"
            << "  \"schema_version\":1,\n"
            << "  \"protocol_version\":\"n006-p1-intervention-v1\",\n"
            << "  \"mode\":\"" << mode_name(mode) << "\",\n"
            << "  \"scenario\":\"" << scenario_name << "\",\n"
            << "  \"topology\":" << (topology ? "true" : "false") << ",\n"
            << "  \"source_warmup_frames\":" << source_warmup_frames << ",\n"
            << "  \"depth_threshold\":" << depth_threshold << ",\n"
            << "  \"extra_rays_per_probe\":" << extra_rays_per_probe << ",\n"
            << "  \"selected_tile_id\":" << selected_tile_id << ",\n"
            << "  \"selected_cascade\":" << selected_cascade << ",\n"
            << "  \"reference_generation\":\""
            << (skip_reference ? "skipped" : "rendered") << "\",\n"
            << "  \"source\":{\"internal_correctness\":"
            << (source_correct ? "true" : "false") << ",\"extra\":";
        write_extra(out, source.extra);
        out << ",\"hit_diagnostics\":";
        write_hit(out, source_hits);
        out << "},\n"
            << "  \"device\":{\"name\":\"" << runtime.device_name()
            << "\",\"driver_name\":\"" << runtime.driver_name()
            << "\",\"driver_info\":\"" << runtime.driver_info()
            << "\",\"api_version\":" << runtime.api_version()
            << ",\"timestamp_period_ns\":" << runtime.timestamp_period_ns()
            << "},\n"
            << "  \"frames\":[\n";
        for (std::size_t index = 0; index < frames.size(); ++index) {
            const auto& frame = frames[index];
            out << "    {\"index\":" << index
                << ",\"motion_fraction\":" << frame.motion_fraction
                << ",\"owner_budget\":" << frame.owner_budget
                << ",\"internal_correctness\":"
                << (frame.internal_correctness ? "true" : "false")
                << ",\"image\":\"" << frame.image_path << "\",\"reference\":";
            if (skip_reference) out << "null";
            else write_reference(out, references[index]);
            out << ",\"hit_diagnostics\":";
            write_hit(out, frame.hits);
            out << ",\"timing_us\":";
            write_timing(
                out,
                frame.result.frame.timings,
                frame.result.extra.extra_producer_gpu_us);
            out << ",\"stats\":";
            write_stats(out, frame.result.frame.stats);
            out << ",\"memory_bytes\":";
            write_memory(out, frame.result.frame.memory);
            out << ",\"extra\":";
            write_extra(out, frame.result.extra);
            out << '}';
            if (index + 1U != frames.size()) out << ',';
            out << '\n';
        }
        out << "  ]\n}\n";
        if (!out) throw std::runtime_error("N006 evidence write failed");

        const bool all_correct = source_correct && std::all_of(
            frames.begin(), frames.end(),
            [](const auto& frame) { return frame.internal_correctness; });
        std::cout << "N006 P2 candidate evidence: " << artifact_dir << '\n'
                  << "mode=" << mode_name(mode)
                  << " scenario=" << scenario_name
                  << " correctness=" << (all_correct ? "pass" : "FAIL")
                  << '\n';
        return all_correct ? 0 : 3;
    } catch (const std::exception& error) {
        std::cerr << "N006 candidate failure: " << error.what() << '\n';
        return 1;
    }
}
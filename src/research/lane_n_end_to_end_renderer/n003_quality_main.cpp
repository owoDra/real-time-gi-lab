#include "n001_reference.hpp"
#include "n001_runtime.hpp"

#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstring>
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

struct ScenarioSpec {
    std::uint32_t index;
    const char* name;
    lane_n::I001Scenario scenario;
    bool topology;
};

constexpr std::array<ScenarioSpec, 6> kScenarios{{
    {0U, "static", lane_n::I001Scenario::Static, false},
    {1U, "camera-motion", lane_n::I001Scenario::CameraMotion, false},
    {2U, "light-motion", lane_n::I001Scenario::LightMotion, false},
    {3U, "moving-rigid", lane_n::I001Scenario::MovingRigid, false},
    {4U, "stable-topology-deforming", lane_n::I001Scenario::DeformingControl, false},
    {5U, "topology-changing-high-churn", lane_n::I001Scenario::DeformingControl, true},
}};

enum class Role { Current, Vanilla };

struct RoleEvidence {
    lane_n::I001RendererReadback readback;
    lane_n::I001FrameStats stats;
    lane_n::I001Quality quality;
    std::string device_name;
    std::string driver_name;
    std::string driver_info;
    std::uint32_t api_version{};
    float timestamp_period_ns{};
};

[[nodiscard]] lane_n::I001Options options_for(
    const fs::path& scene,
    const ScenarioSpec& spec) {
    lane_n::I001Options options{};
    options.scene = scene;
    options.variant = lane_n::I001Variant::LaneEFinalHwrt;
    options.scenario = spec.scenario;
    options.validation = true;
    return options;
}

[[nodiscard]] RoleEvidence run_role(
    const fs::path& scene,
    const ScenarioSpec& spec,
    Role role,
    std::uint32_t source_warmup_frames) {
    lane_n::I001Runtime runtime(options_for(scene, spec));
    if (role == Role::Vanilla) {
        runtime.configure_n003_vanilla_software_baseline();
    }

    (void)runtime.run_frame(false);
    if (!runtime.validate_last_frame().passed) {
        throw std::runtime_error("N003 quality source correctness failed");
    }
    for (std::uint32_t index = 1; index < source_warmup_frames; ++index) {
        (void)runtime.run_frame(false);
    }

    lane_n::I001FrameResult measured{};
    if (spec.topology) {
        measured = role == Role::Current
            ? runtime.run_topology_churn_frame()
            : runtime.run_n003_vanilla_topology_churn_frame();
    } else {
        measured = runtime.run_frame(true);
    }
    const auto quality = runtime.validate_last_frame();
    if (!quality.passed || measured.stats.storage_failures != 0U) {
        throw std::runtime_error("N003 quality target correctness failed");
    }

    return {
        runtime.renderer_readback(),
        measured.stats,
        quality,
        runtime.device_name(),
        runtime.driver_name(),
        runtime.driver_info(),
        runtime.api_version(),
        runtime.timestamp_period_ns(),
    };
}

void require_same_device(const RoleEvidence& a, const RoleEvidence& b) {
    if (a.device_name != b.device_name || a.driver_name != b.driver_name ||
        a.driver_info != b.driver_info || a.api_version != b.api_version ||
        a.timestamp_period_ns != b.timestamp_period_ns) {
        throw std::runtime_error("N003 quality device provenance mismatch");
    }
}

[[nodiscard]] bool same_vec(
    phos::gi::research::lane_b::Vec3 a,
    phos::gi::research::lane_b::Vec3 b) {
    return a.x == b.x && a.y == b.y && a.z == b.z;
}

void require_same_scene_state(
    const ScenarioSpec& spec,
    const RoleEvidence& current,
    const RoleEvidence& vanilla) {
    const auto& a = current.readback;
    const auto& b = vanilla.readback;
    if (a.width != b.width || a.height != b.height ||
        std::memcmp(&a.params, &b.params, sizeof(a.params)) != 0 ||
        a.surfaces.size() != b.surfaces.size() ||
        a.triangles.size() != b.triangles.size()) {
        throw std::runtime_error(
            std::string("N003 quality scene-state header mismatch for ") + spec.name);
    }
    for (std::size_t index = 0; index < a.surfaces.size(); ++index) {
        if (std::memcmp(
                &a.surfaces[index], &b.surfaces[index],
                sizeof(a.surfaces[index])) != 0) {
            throw std::runtime_error(
                std::string("N003 quality surface mismatch for ") + spec.name);
        }
    }
    for (std::size_t index = 0; index < a.triangles.size(); ++index) {
        const auto& x = a.triangles[index];
        const auto& y = b.triangles[index];
        if (!same_vec(x.v0, y.v0) || !same_vec(x.v1, y.v1) ||
            !same_vec(x.v2, y.v2) ||
            x.primitive_id != y.primitive_id ||
            x.material_id != y.material_id ||
            x.instance_id != y.instance_id ||
            x.two_sided != y.two_sided) {
            throw std::runtime_error(
                std::string("N003 quality triangle mismatch for ") + spec.name);
        }
    }
}

[[nodiscard]] std::vector<float> rgb_from_rgba(
    const lane_n::I001RendererReadback& frame) {
    const auto pixels = std::size_t(frame.width) * frame.height;
    if (frame.image_rgba.size() != pixels * 4U) {
        throw std::runtime_error("N003 quality RGBA payload size mismatch");
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
        throw std::runtime_error("N003 quality PFM payload size mismatch");
    }
    fs::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("could not open N003 quality PFM");
    out << "PF\n" << width << ' ' << height << "\n-1.0\n";
    const auto row_floats = std::size_t(width) * 3U;
    for (std::uint32_t y = height; y-- > 0U;) {
        const auto* row = rgb.data() + std::size_t(y) * row_floats;
        out.write(
            reinterpret_cast<const char*>(row),
            std::streamsize(row_floats * sizeof(float)));
    }
    if (!out) throw std::runtime_error("N003 quality PFM write failed");
}

[[nodiscard]] std::string frame_name(const char* prefix, std::uint32_t index) {
    std::ostringstream out;
    out << "frames/" << prefix << '-' << std::setw(3) << std::setfill('0')
        << index << ".pfm";
    return out.str();
}

} // namespace

int main(int argc, char** argv) {
    fs::path scene =
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf";
    fs::path artifact_dir;
    std::uint32_t source_warmup_frames = 32U;

    for (int index = 1; index < argc; ++index) {
        const std::string_view arg = argv[index];
        if (arg == "--scene" && index + 1 < argc) {
            scene = argv[++index];
        } else if (arg == "--artifact-dir" && index + 1 < argc) {
            artifact_dir = argv[++index];
        } else if (arg == "--source-warmup-frames" && index + 1 < argc) {
            source_warmup_frames =
                static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else {
            std::cerr << "usage: phos-n003-quality --artifact-dir PATH "
                         "[--scene PATH] [--source-warmup-frames N]\n";
            return 2;
        }
    }
    if (artifact_dir.empty() || source_warmup_frames == 0U) {
        std::cerr << "invalid N003 quality arguments\n";
        return 2;
    }

    try {
        fs::create_directories(artifact_dir / "frames");
        std::vector<std::string> frame_json;
        std::string device_name;
        std::string driver_name;
        std::string driver_info;
        std::uint32_t api_version{};
        float timestamp_period_ns{};

        for (const auto& spec : kScenarios) {
            auto current = run_role(
                scene, spec, Role::Current, source_warmup_frames);
            auto vanilla = run_role(
                scene, spec, Role::Vanilla, source_warmup_frames);
            require_same_device(current, vanilla);
            require_same_scene_state(spec, current, vanilla);

            if (device_name.empty()) {
                device_name = current.device_name;
                driver_name = current.driver_name;
                driver_info = current.driver_info;
                api_version = current.api_version;
                timestamp_period_ns = current.timestamp_period_ns;
            } else if (device_name != current.device_name ||
                       driver_name != current.driver_name ||
                       driver_info != current.driver_info ||
                       api_version != current.api_version ||
                       timestamp_period_ns != current.timestamp_period_ns) {
                throw std::runtime_error(
                    "N003 quality device changed between scenarios");
            }

            const auto current_rgb = rgb_from_rgba(current.readback);
            const auto vanilla_rgb = rgb_from_rgba(vanilla.readback);
            const auto reference = lane_n::n001_render_reference(current.readback);
            if (!reference.converged) {
                throw std::runtime_error(
                    std::string("N003 quality reference did not converge for ") +
                    spec.name);
            }

            const auto current_path = frame_name("current", spec.index);
            const auto vanilla_path = frame_name("vanilla", spec.index);
            const auto reference_path = frame_name("reference", spec.index);
            write_pfm(
                artifact_dir / current_path,
                current.readback.width, current.readback.height, current_rgb);
            write_pfm(
                artifact_dir / vanilla_path,
                vanilla.readback.width, vanilla.readback.height, vanilla_rgb);
            write_pfm(
                artifact_dir / reference_path,
                current.readback.width, current.readback.height, reference.rgb);

            std::ostringstream entry;
            entry << std::setprecision(17)
                  << "    {\n"
                  << "      \"frame\": " << spec.index << ",\n"
                  << "      \"scenario\": \"" << spec.name << "\",\n"
                  << "      \"current_hdr\": \"" << current_path << "\",\n"
                  << "      \"vanilla_hdr\": \"" << vanilla_path << "\",\n"
                  << "      \"reference_hdr\": \"" << reference_path << "\",\n"
                  << "      \"scene_state_identical\": true,\n"
                  << "      \"current_internal_correctness\": true,\n"
                  << "      \"vanilla_internal_correctness\": true,\n"
                  << "      \"reference\": {\n"
                  << "        \"spp\": " << reference.spp << ",\n"
                  << "        \"converged\": true,\n"
                  << "        \"replicate_p99_abs_luminance\": "
                  << reference.replicate_p99_abs_luminance << ",\n"
                  << "        \"replicate_p99_relative_luminance\": "
                  << reference.replicate_p99_relative_luminance << "\n"
                  << "      }\n"
                  << "    }";
            frame_json.push_back(entry.str());
            std::cout << "N003 quality " << spec.name
                      << ": reference=" << reference.spp << "spp converged=yes\n";
        }

        std::ofstream out(artifact_dir / "n003-quality-evidence.json");
        if (!out) throw std::runtime_error("could not open N003 quality evidence JSON");
        out << std::setprecision(17)
            << "{\n"
            << "  \"schema_version\": 1,\n"
            << "  \"protocol_version\": \"current-vs-vanilla-quality-v1\",\n"
            << "  \"source_warmup_frames\": " << source_warmup_frames << ",\n"
            << "  \"device\": {\n"
            << "    \"name\": \"" << device_name << "\",\n"
            << "    \"driver_name\": \"" << driver_name << "\",\n"
            << "    \"driver_info\": \"" << driver_info << "\",\n"
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
        if (!out) throw std::runtime_error("N003 quality evidence write failed");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "N003 quality failure: " << error.what() << '\n';
        return 1;
    }
}

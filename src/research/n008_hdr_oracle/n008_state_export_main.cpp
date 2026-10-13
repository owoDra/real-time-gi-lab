// N008 CPU-only frame-state exporter. Reproduces the N-series Renderer target
// state (world-space triangles + A001 params) for a regime WITHOUT Vulkan, using
// verbatim-extracted Renderer code (see generate_state_exporter.py). Output uses
// the N007 state format so it can be byte-compared with GPU-run captures.
#include "a001_runtime.hpp"
#include "a001_scene.hpp"
#include "b002_scene.hpp"
#include "hierarchical_stratabrick.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

#include "n008_state_extracted.hpp"

namespace fs = std::filesystem;
namespace lane_a = phos::gi::lane_a;
namespace lane_b = phos::gi::research::lane_b;

namespace {

template <class T> void raw(std::ofstream& out, const T& v) { out.write(reinterpret_cast<const char*>(&v), sizeof v); }

// Re-statement of the N002 frozen topology churn (n002_runtime.cpp
// run_topology_churn_frame); the generator asserts these source lines verbatim.
void topology_churn(lane_b::B002Scene& b_scene, const n008_extracted_n001::MovingSelection& moving) {
    std::uint32_t max_primitive_id = 0U;
    for (const auto& triangle : b_scene.triangles)
        if (triangle.primitive_id != lane_b::kInvalidId) max_primitive_id = std::max(max_primitive_id, triangle.primitive_id);
    const float amplitude = std::max(moving.delta_x, lane_b::b002_segment_size(b_scene) * 0.04F);
    for (std::size_t local = 0; local < moving.primitives.size(); ++local) {
        auto& triangle = b_scene.triangles.at(moving.primitives[local]);
        if ((local & 1U) == 0U) {
            const float sign = ((local >> 1U) & 1U) == 0U ? 1.0F : -1.0F;
            const float scale = 1.0F + float(local % 5U) * 0.125F;
            triangle.v0.y += sign * amplitude * 0.50F * scale;
            triangle.v1.z += sign * amplitude * 0.35F * scale;
            triangle.v2.x -= sign * amplitude * 0.20F * scale;
            triangle.primitive_id = max_primitive_id + 1U + static_cast<std::uint32_t>(local);
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        fs::path scene, out;
        std::string regime;
        std::uint32_t frame_id = 2;
        for (int i = 1; i < argc; ++i) {
            const std::string a = argv[i];
            if (i + 1 >= argc) throw std::runtime_error("missing value for " + a);
            if (a == "--scene") scene = argv[++i];
            else if (a == "--out") out = argv[++i];
            else if (a == "--regime") regime = argv[++i];
            else if (a == "--frame-id") frame_id = std::uint32_t(std::stoul(argv[++i]));
            else throw std::runtime_error("unknown argument " + a);
        }
        auto a_scene = lane_a::load_scene_surface_samples(scene);
        auto b_scene = lane_b::load_b002_scene(scene);
        if (a_scene.samples.size() != b_scene.triangles.size())
            throw std::runtime_error("A001/B002 primitive identity diverged");

        lane_a::A001Settings settings;
        settings.tile_width = 320U;
        settings.tile_height = 180U;
        settings.cascade_count = 4;
        settings.rays_per_probe = 8;
        settings.case_id = lane_a::A001Case::Static;
        n008_extracted_n001::MovingSelection moving{};
        if (regime == "static") {
        } else if (regime == "camera-motion") {
            settings.case_id = lane_a::A001Case::CameraMotion;
        } else if (regime == "light-motion") {
            settings.case_id = lane_a::A001Case::LightMotion;
        } else if (regime == "moving-rigid") {
            moving = n008_extracted_n001::choose_moving_selection(b_scene);
            b_scene.triangles = n008_extracted_n001::translated_geometry(b_scene.triangles, moving.primitives, moving.delta_x);
        } else if (regime == "deforming") {
            moving = n008_extracted_n001::choose_deforming_selection(b_scene);
            b_scene.triangles = n008_extracted_n001::deformed_geometry(b_scene.triangles, moving.primitives, moving.delta_x);
        } else if (regime == "topology-churn") {
            moving = n008_extracted_n001::choose_deforming_selection(b_scene);
            topology_churn(b_scene, moving);
        } else {
            throw std::runtime_error("regime must be static|camera-motion|light-motion|moving-rigid|deforming|topology-churn");
        }
        // Params come from the frozen source-state A001 bounds (never updated after motion).
        const auto base = n008_extracted_a001::build_a001_params(a_scene, settings);
        settings.frame_id = frame_id;
        auto params = n008_extracted_a001::build_a001_params(a_scene, settings);
        params.limits[1] = base.limits[1];
        params.limits[2] = base.limits[2];

        fs::create_directories(out);
        std::ofstream geometry(out / "geometry-state.bin", std::ios::binary), frame(out / "frame-state.bin", std::ios::binary);
        const std::uint32_t version = 1, ntri = std::uint32_t(b_scene.triangles.size());
        raw(geometry, version); raw(geometry, ntri);
        for (const auto& t : b_scene.triangles) {
            for (const auto& v : {t.v0, t.v1, t.v2}) { raw(geometry, v.x); raw(geometry, v.y); raw(geometry, v.z); }
            raw(geometry, t.primitive_id); raw(geometry, t.material_id); raw(geometry, t.instance_id);
            const std::uint32_t sided = t.two_sided ? 1U : 0U;
            raw(geometry, sided);
        }
        const char magic[12] = {'N', '0', '0', '7', '-', 'S', 'T', 'A', 'T', 'E', '1', '\0'};
        frame.write(magic, sizeof magic);
        const std::uint32_t w = 320, h = 180;
        raw(frame, w); raw(frame, h); raw(frame, params);
        if (!geometry || !frame) throw std::runtime_error("state write failed");
        std::cout << "{\"regime\":\"" << regime << "\",\"triangles\":" << ntri << ",\"moving_instance\":" << moving.instance_id
                  << ",\"moving_primitives\":" << moving.primitives.size() << ",\"delta_x\":" << moving.delta_x
                  << ",\"membership_changes\":" << moving.membership_changes << ",\"extracted_sources\":[";
        for (std::size_t i = 0; i < std::size(kN008ExtractedSources); ++i)
            std::cout << (i ? "," : "") << "[\"" << kN008ExtractedSources[i][0] << "\",\"" << kN008ExtractedSources[i][1] << "\"]";
        std::cout << "]}\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "n008_state_export: " << e.what() << "\n";
        return 1;
    }
}

// N009 scene contract C1 (opt-in research overlay; the default Renderer is unchanged).
//
// Included only by the generated N009 copies of the pinned A001/B002 loaders and
// of a001_runtime.cpp (scripts/research/n009_scene_contract/generate_overlay.py):
//   * glTF node world transforms are applied to mesh POSITION data;
//   * the authored glTF camera (first camera node of the default scene) is the
//     Renderer camera; the point light comes from a preregistered contract file
//     named by PHOS_N009_CONTRACT;
//   * BF-P: every triangle is two-sided for every ray type (set by the loader).
// Scenes without an authored camera keep the A001 camera/light formula.
#pragma once

#include <fastgltf/tools.hpp>
#include <fastgltf/types.hpp>

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

namespace n009 {

struct AuthoredCamera {
    bool present = false;
    float eye[3]{}, right[3]{}, up[3]{}, forward[3]{};
    float yfov = 0.0F;
};

inline AuthoredCamera& authored_camera() {
    static AuthoredCamera camera;
    return camera;
}

struct Contract {
    float authored_eye[3]{};
    float camera_motion_offset[3]{};
    float light_base[3]{};
    float light_motion[3]{};
};

[[nodiscard]] inline float n009_length3(const float* v) {
    return std::sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
}

// Reads the preregistered contract file; fail-closed when it is missing or when
// it was written for a different authored camera.
[[nodiscard]] inline const Contract& contract() {
    static const Contract value = [] {
        const char* path = std::getenv("PHOS_N009_CONTRACT");
        if (!path || !*path)
            throw std::runtime_error("N009: authored camera present but PHOS_N009_CONTRACT is not set");
        std::ifstream in(path);
        std::string magic;
        int version = 0;
        if (!(in >> magic >> version) || magic != "n009contract" || version != 1)
            throw std::runtime_error("N009: bad contract header");
        Contract c{};
        bool seen[4]{};
        std::string key;
        while (in >> key) {
            float* dst = key == "authored_eye" ? c.authored_eye
                       : key == "camera_motion_offset" ? c.camera_motion_offset
                       : key == "light_base" ? c.light_base
                       : key == "light_motion" ? c.light_motion : nullptr;
            if (!dst) throw std::runtime_error("N009: unknown contract key " + key);
            if (!(in >> dst[0] >> dst[1] >> dst[2])) throw std::runtime_error("N009: bad contract value " + key);
            seen[dst == c.authored_eye ? 0 : dst == c.camera_motion_offset ? 1 : dst == c.light_base ? 2 : 3] = true;
        }
        for (bool s : seen)
            if (!s) throw std::runtime_error("N009: incomplete contract");
        const auto& cam = authored_camera();
        for (int i = 0; i < 3; ++i)
            if (std::fabs(cam.eye[i] - c.authored_eye[i]) > 1.0e-3F)
                throw std::runtime_error("N009: contract was written for a different authored camera");
        return c;
    }();
    return value;
}

// World transform per mesh of the default scene. Every mesh must be instanced by
// exactly one node so primitive/instance identities stay one-to-one with the
// pinned loaders. Records the first authored camera as a side effect.
[[nodiscard]] inline std::vector<fastgltf::math::fmat4x4> mesh_world_transforms(const fastgltf::Asset& asset) {
    std::vector<fastgltf::math::fmat4x4> world(asset.meshes.size());
    std::vector<int> uses(asset.meshes.size(), 0);
    if (asset.scenes.empty()) throw std::runtime_error("N009: glTF has no scene");
    const std::size_t scene = asset.defaultScene.has_value() ? asset.defaultScene.value() : 0U;
    AuthoredCamera camera{};
    fastgltf::iterateSceneNodes(asset, scene, fastgltf::math::fmat4x4(),
        [&](const fastgltf::Node& node, const fastgltf::math::fmat4x4& m) {
            if (node.meshIndex.has_value()) {
                world.at(node.meshIndex.value()) = m;
                ++uses.at(node.meshIndex.value());
            }
            if (node.cameraIndex.has_value() && !camera.present) {
                const auto& cam = asset.cameras.at(node.cameraIndex.value());
                const auto* perspective = std::get_if<fastgltf::Camera::Perspective>(&cam.camera);
                if (!perspective) throw std::runtime_error("N009: authored camera is not perspective");
                camera.present = true;
                camera.yfov = perspective->yfov;
                for (int i = 0; i < 3; ++i) {
                    camera.eye[i] = m[3][i];
                    camera.right[i] = m[0][i];
                    camera.up[i] = m[1][i];
                    camera.forward[i] = -m[2][i];
                }
                for (float* v : {camera.right, camera.up, camera.forward}) {
                    const float len = n009_length3(v);
                    if (!(len > 0.0F)) throw std::runtime_error("N009: degenerate authored camera basis");
                    for (int i = 0; i < 3; ++i) v[i] /= len;
                }
            }
        });
    for (std::size_t mesh = 0; mesh < uses.size(); ++mesh)
        if (uses[mesh] != 1)
            throw std::runtime_error("N009: mesh " + std::to_string(mesh) + " is not instanced exactly once");
    authored_camera() = camera;
    return world;
}

[[nodiscard]] inline fastgltf::math::fvec3 apply(const fastgltf::math::fmat4x4& m, fastgltf::math::fvec3 p) {
    const float x = p.x(), y = p.y(), z = p.z();
    return {m[0][0] * x + m[1][0] * y + m[2][0] * z + m[3][0],
            m[0][1] * x + m[1][1] * y + m[2][1] * z + m[3][1],
            m[0][2] * x + m[1][2] * y + m[2][2] * z + m[3][2]};
}

}  // namespace n009

#version 450

layout(local_size_x = 256) in;

struct SurfaceSample {
    vec4 position;
    vec4 normal;
};

layout(std430, set = 0, binding = 0) readonly buffer Surfaces { SurfaceSample surfaces[]; };
layout(std430, set = 0, binding = 1) readonly buffer TileDepth { uint tile_depth[]; };
layout(std430, set = 0, binding = 2) buffer VisibleSurface { uint visible_surface[]; };
layout(std430, set = 0, binding = 7) readonly buffer Config {
    vec4 eye;
    vec4 camera_right;
    vec4 camera_up;
    vec4 camera_forward;
    vec4 camera;
    uvec4 grid;
    uvec4 rc;
    vec4 rc_params;
    vec4 light;
} cfg;

bool project_point(vec3 position, out uint tile, out float depth) {
    vec3 rel = position - cfg.eye.xyz;
    depth = dot(rel, cfg.camera_forward.xyz);
    if (depth < cfg.camera.z || depth > cfg.camera.w) {
        return false;
    }

    float ndc_x = dot(rel, cfg.camera_right.xyz) / (depth * cfg.camera.x * cfg.camera.y);
    float ndc_y = dot(rel, cfg.camera_up.xyz) / (depth * cfg.camera.x);
    if (abs(ndc_x) > 1.0 || abs(ndc_y) > 1.0) {
        return false;
    }

    uint x = min(cfg.grid.x - 1u, uint((ndc_x * 0.5 + 0.5) * float(cfg.grid.x)));
    uint y = min(cfg.grid.y - 1u, uint((-ndc_y * 0.5 + 0.5) * float(cfg.grid.y)));
    tile = y * cfg.grid.x + x;
    return true;
}

void main() {
    uint surface_id = gl_GlobalInvocationID.x;
    if (surface_id >= cfg.grid.z) {
        return;
    }

    uint tile;
    float depth;
    if (!project_point(surfaces[surface_id].position.xyz, tile, depth)) {
        return;
    }

    if (floatBitsToUint(depth) == tile_depth[tile]) {
        // Tie-break deterministically without sorting the produced work.
        atomicMin(visible_surface[tile], surface_id);
    }
}

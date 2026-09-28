#version 450

layout(local_size_x = 256) in;

layout(std430, set = 0, binding = 2) readonly buffer VisibleSurface { uint visible_surface[]; };
layout(std430, set = 0, binding = 5) readonly buffer CascadeRadiance { vec4 cascade_radiance[]; };
layout(std430, set = 0, binding = 6) buffer ResolvedRadiance { vec4 resolved[]; };
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

void main() {
    uint tile = gl_GlobalInvocationID.x;
    uint tile_count = cfg.grid.x * cfg.grid.y;
    if (tile >= tile_count) {
        return;
    }

    if (visible_surface[tile] == 0xffffffffu) {
        resolved[tile] = vec4(0.0);
        return;
    }

    vec3 weighted = vec3(0.0);
    float weight_sum = 0.0;
    for (uint cascade = 0u; cascade < cfg.rc.x; ++cascade) {
        float weight = exp2(-float(cascade));
        weighted += cascade_radiance[tile * cfg.rc.x + cascade].xyz * weight;
        weight_sum += weight;
    }
    resolved[tile] = vec4(weighted / max(weight_sum, 1e-8), 1.0);
}

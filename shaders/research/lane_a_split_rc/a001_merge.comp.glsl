#version 450

layout(local_size_x = 256) in;

layout(std430, set = 0, binding = 2) readonly buffer VisibleSurface { uint visible_surface[]; };
layout(std430, set = 0, binding = 4) readonly buffer GatherRadiance { vec4 gathered[]; };
layout(std430, set = 0, binding = 5) buffer CascadeRadiance { vec4 cascade_radiance[]; };
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
    uint output_id = gl_GlobalInvocationID.x;
    if (output_id >= cfg.rc.w) {
        return;
    }

    uint cascade_count = cfg.rc.x;
    uint rays_per_probe = cfg.rc.y;
    uint tile = output_id / cascade_count;
    uint cascade = output_id - tile * cascade_count;

    if (visible_surface[tile] == 0xffffffffu) {
        cascade_radiance[output_id] = vec4(0.0);
        return;
    }

    uint base = (tile * cascade_count + cascade) * rays_per_probe;
    vec3 sum = vec3(0.0);
    for (uint ray = 0u; ray < rays_per_probe; ++ray) {
        sum += gathered[base + ray].xyz;
    }
    cascade_radiance[output_id] = vec4(sum / float(rays_per_probe), 1.0);
}

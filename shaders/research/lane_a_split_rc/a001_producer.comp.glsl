#version 450

layout(local_size_x = 256) in;

const uint WORK_ITEM_VALID = 1u;

struct SurfaceSample {
    vec4 position;
    vec4 normal;
};

struct WorkItem {
    uvec4 identity;
    vec4 origin_interval;
    vec4 direction_interval;
    uvec4 output_identity;
};

layout(std430, set = 0, binding = 0) readonly buffer Surfaces { SurfaceSample surfaces[]; };
layout(std430, set = 0, binding = 2) readonly buffer VisibleSurface { uint visible_surface[]; };
layout(std430, set = 0, binding = 3) buffer WorkItems { WorkItem work_items[]; };
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

vec3 hemisphere_direction(vec3 normal, uint ray_index, uint ray_count) {
    vec3 n = normalize(normal);
    vec3 helper = abs(n.y) < 0.999 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0);
    vec3 tangent = normalize(cross(helper, n));
    vec3 bitangent = cross(n, tangent);

    float u = (float(ray_index) + 0.5) / float(ray_count);
    float radial = sqrt(u);
    float phi = 6.28318530718 * fract((float(ray_index) + 0.5) * 0.61803398875);
    vec3 local = vec3(cos(phi) * radial, sin(phi) * radial, sqrt(max(0.0, 1.0 - u)));
    return normalize(tangent * local.x + bitangent * local.y + n * local.z);
}

void main() {
    uint item_index = gl_GlobalInvocationID.x;
    if (item_index >= cfg.rc.z) {
        return;
    }

    uint rays_per_probe = cfg.rc.y;
    uint cascade_count = cfg.rc.x;
    uint per_probe = cascade_count * rays_per_probe;
    uint tile = item_index / per_probe;
    uint within_probe = item_index - tile * per_probe;
    uint cascade = within_probe / rays_per_probe;
    uint ray_index = within_probe - cascade * rays_per_probe;

    uint surface_id = visible_surface[tile];
    if (surface_id == 0xffffffffu) {
        work_items[item_index].identity = uvec4(cfg.grid.w, tile, cascade, ray_index);
        work_items[item_index].origin_interval = vec4(0.0);
        work_items[item_index].direction_interval = vec4(0.0);
        work_items[item_index].output_identity = uvec4(tile * cascade_count + cascade, 0xffffffffu, tile, 0u);
        return;
    }

    SurfaceSample surface = surfaces[surface_id];
    vec3 n = normalize(surface.normal.xyz);
    float t_max = cfg.rc_params.x * pow(cfg.rc_params.y, float(cascade));
    float t_min = cascade == 0u ? 0.0 : cfg.rc_params.x * pow(cfg.rc_params.y, float(cascade - 1u));

    WorkItem item;
    item.identity = uvec4(cfg.grid.w, tile, cascade, ray_index);
    item.origin_interval = vec4(surface.position.xyz + n * cfg.rc_params.z, t_min);
    item.direction_interval = vec4(hemisphere_direction(n, ray_index, rays_per_probe), t_max);
    item.output_identity = uvec4(tile * cascade_count + cascade, surface_id, tile, WORK_ITEM_VALID);
    work_items[item_index] = item;
}

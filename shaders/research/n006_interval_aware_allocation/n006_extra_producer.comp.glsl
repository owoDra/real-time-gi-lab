#version 460
// P1-only causal intervention: one screen-visible owner x one cascade.
// Does not implement a runtime scheduling policy.
layout(local_size_x = 1) in;

struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};
layout(std430, binding = 0) readonly buffer DepthBuffer { uint depth_bits[]; } depth_buffer;
layout(std430, binding = 1) readonly buffer OwnerBuffer { uint owner_ids[]; } owner_buffer;
layout(std430, binding = 2) buffer CounterBuffer { uint data[]; } counters;
layout(std430, binding = 3) buffer WorkBuffer { WorkItem items[]; } work;
layout(std430, binding = 4) buffer N006Stats { uint data[]; } stats;
layout(std140, binding = 5) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;
layout(push_constant) uniform Push {
    uint mode;
    uint owner_budget;
    uint extra_rays_per_probe;
    uint target_tile_id;
    uint target_cascade;
} pc;
const uint MODE_TARGETED = 2u;
const uint INVALID_OWNER = 0xffffffffu;
const float PI = 3.14159265358979323846;

uint mix32(uint x) {
    x ^= x >> 16u;
    x *= 0x7feb352du;
    x ^= x >> 15u;
    x *= 0x846ca68bu;
    x ^= x >> 16u;
    return x;
}
vec3 extra_direction(WorkItem item, uint ordinal) {
    uint h0 = mix32(uint(item.probe_x) * 0x9e3779b9u ^
                    uint(item.probe_y) * 0x85ebca6bu ^
                    uint(item.probe_z) * 0xc2b2ae35u ^
                    item.cascade * 0x27d4eb2du ^
                    ordinal * 0x165667b1u);
    uint h1 = mix32(h0 ^ 0xa511e9b3u);
    float u = (float(h0) + 0.5) / 4294967296.0;
    float v = (float(h1) + 0.5) / 4294967296.0;
    float z = 1.0 - 2.0 * u;
    float r = sqrt(max(0.0, 1.0 - z * z));
    float phi = 2.0 * PI * v;
    return vec3(r * cos(phi), r * sin(phi), z);
}
void main() {
    if (gl_GlobalInvocationID.x != 0u) return;
    uint base_count = counters.data[0];
    uint rays_per_owner = p.counts.w * p.limits.x;
    stats.data[0] = base_count;
    stats.data[1] = 0u;
    stats.data[2] = 0u;
    stats.data[3] = 0u;
    if (pc.mode != MODE_TARGETED || pc.owner_budget != 1u ||
        rays_per_owner == 0u ||
        pc.target_cascade >= p.counts.w ||
        pc.target_tile_id >= p.counts.y * p.counts.z ||
        owner_buffer.owner_ids[pc.target_tile_id] == INVALID_OWNER) return;
    uint total_owners = base_count / rays_per_owner;
    for (uint owner = 0u; owner < total_owners; ++owner) {
        uint owner_base = owner * rays_per_owner;
        WorkItem source = work.items[owner_base + pc.target_cascade * p.limits.x];
        if (source.tile_id != pc.target_tile_id) continue;
        stats.data[1] = 1u;
        if (base_count + pc.extra_rays_per_probe > p.limits.y) {
            counters.data[2] = 1u;
            return;
        }
        for (uint extra = 0u; extra < pc.extra_rays_per_probe; ++extra) {
            WorkItem item = source;
            item.ray_index = p.limits.x + extra;
            vec3 direction = extra_direction(item, extra);
            item.dir_x = direction.x;
            item.dir_y = direction.y;
            item.dir_z = direction.z;
            work.items[base_count + extra] = item;
        }
        stats.data[2] = 1u;
        stats.data[3] = pc.extra_rays_per_probe;
        counters.data[0] = base_count + pc.extra_rays_per_probe;
        return;
    }
}

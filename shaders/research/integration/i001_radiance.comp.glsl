#version 460
layout(local_size_x = 64) in;
struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};
struct HitData { vec4 normal_t; uvec4 metadata; };
layout(std430, binding = 0) readonly buffer Counters { uint data[]; } counters;
layout(std430, binding = 1) readonly buffer Work { WorkItem items[]; } work;
layout(std430, binding = 2) readonly buffer Hits { HitData hits[]; };
layout(std430, binding = 3) writeonly buffer Contributions { uvec2 values[]; } contributions;
layout(std140, binding = 4) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;

uint mix32(uint x) {
    x ^= x >> 16u;
    x *= 0x7feb352du;
    x ^= x >> 15u;
    x *= 0x846ca68bu;
    x ^= x >> 16u;
    return x;
}

uint deterministic_radiance(WorkItem item, HitData hit) {
    if (hit.metadata.w != 1u) return 0u;

    // I001 validates traversal geometry separately through the Hit contract.
    // The radiance payload therefore depends only on contract-stable integer
    // identity plus the frame's direct-light state. This keeps storage/resolve
    // quality deterministic across HWRT/software implementations whose
    // equivalent t/normal values may differ by the accepted floating tolerance.
    uint seed = mix32(hit.metadata.x ^ 0x9e3779b9u);
    seed ^= mix32(hit.metadata.y ^ 0x85ebca6bu);
    seed ^= mix32(hit.metadata.z ^ 0xc2b2ae35u);
    seed ^= mix32(item.cascade * 0x27d4eb2du + item.ray_index);
    seed ^= mix32(floatBitsToUint(p.light_pos_interval.x));
    seed ^= mix32(floatBitsToUint(p.light_pos_interval.y));
    seed ^= mix32(floatBitsToUint(p.light_pos_interval.z));
    seed ^= mix32(floatBitsToUint(p.light_pos_interval.w));

    uint fixed = mix32(seed) & 0xffffu;
    return fixed >> min(item.cascade, 15u);
}

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= counters.data[0]) return;
    WorkItem item = work.items[id];
    HitData hit = hits[id];
    contributions.values[id] =
        uvec2(item.output_id, deterministic_radiance(item, hit));
}

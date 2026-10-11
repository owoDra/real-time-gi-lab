#version 460
// N006 P1m1a ONLY. Single canonical probe-key intervention, not a scheduler.
// The entire existing 8-ray compact prefix remains unchanged in place.
// Append four deterministic P1a directions, all with the existing output_id.
layout(local_size_x = 1) in;
struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};
layout(std430, binding = 0) buffer Counters { uint data[]; } counters;
layout(std430, binding = 1) buffer Work { WorkItem items[]; } work;
layout(std430, binding = 2) buffer Stats { uint data[]; } stats;
layout(std140, binding = 3) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;
layout(push_constant) uniform Push {
    uint selected_token;
    uint rays_per_probe;
    uint extra_rays;
    uint capacity;
} pc;
const uint INVALID = 0xffffffffu;
const float PI = 3.14159265358979323846;
uint mix32(uint x) {
    x ^= x >> 16u; x *= 0x7feb352du;
    x ^= x >> 15u; x *= 0x846ca68bu;
    x ^= x >> 16u; return x;
}
uint pack_key(ivec4 key) {
    if (any(lessThan(key, ivec4(0))) ||
        any(greaterThan(key, ivec4(1023,1023,1023,3)))) return INVALID;
    uint value = uint(key.x) | (uint(key.y) << 10u) |
                 (uint(key.z) << 20u) | (uint(key.w) << 30u);
    return value >= 0xfffffffeu ? INVALID : value + 1u;
}
// Verbatim deterministic P1a direction rule; ray ordinal is 0,1,2,3.
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
    uint outputs = counters.data[1];
    stats.data[0] = base_count;
    stats.data[1] = 0u;
    stats.data[2] = 0u;
    stats.data[3] = INVALID;
    stats.data[4] = pc.selected_token;
    stats.data[5] = 0u;
    if (pc.selected_token == 0u || pc.selected_token == INVALID ||
        pc.rays_per_probe != 8u || pc.extra_rays != 4u ||
        outputs == 0u || outputs > pc.capacity ||
        base_count != outputs * pc.rays_per_probe ||
        base_count + pc.extra_rays < base_count ||
        base_count + pc.extra_rays > p.limits.y) {
        stats.data[5] = 1u;
        return;
    }
    // Exactly one canonical output per probe key. Bounded one-time scan is
    // correctness preflight only; this serial scan is NEVER a proposed P2 scheduler.
    for (uint output_id = 0u; output_id < outputs; ++output_id) {
        WorkItem original = work.items[output_id * pc.rays_per_probe];
        if (original.ray_index != 0u || original.output_id != output_id ||
            original.cascade >= 4u) {
            stats.data[5] = 2u;
            return;
        }
        uint token = pack_key(ivec4(
            original.probe_x, original.probe_y, original.probe_z,
            int(original.cascade)));
        if (token == INVALID) {
            stats.data[5] = 3u;
            return;
        }
        if (token != pc.selected_token) continue;
        if (stats.data[1] != 0u) {
            stats.data[5] = 4u;
            return;
        }
        stats.data[1] = 1u;
        stats.data[3] = output_id;
        for (uint extra = 0u; extra < pc.extra_rays; ++extra) {
            WorkItem item = original;
            item.ray_index = pc.rays_per_probe + extra;
            vec3 direction = extra_direction(item, extra);
            item.dir_x = direction.x;
            item.dir_y = direction.y;
            item.dir_z = direction.z;
            work.items[base_count + extra] = item;
        }
    }
    if (stats.data[1] != 1u) {
        stats.data[5] = 5u;
        return;
    }
    counters.data[0] = base_count + pc.extra_rays;
    counters.data[4] = counters.data[0];
    stats.data[2] = pc.extra_rays;
}

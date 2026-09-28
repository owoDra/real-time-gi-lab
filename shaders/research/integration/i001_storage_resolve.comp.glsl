#version 460
layout(local_size_x = 64) in;
struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};
struct Slot { ivec4 key; uvec4 data; };
layout(std430, binding = 0) readonly buffer Counters { uint data[]; } counters;
layout(std430, binding = 1) readonly buffer Work { WorkItem items[]; } work;
layout(std430, binding = 2) readonly buffer Slots { Slot values[]; } slots;
layout(std430, binding = 3) writeonly buffer Resolved { float values[]; } resolved;
layout(push_constant) uniform Push {
    uint mask; uint max_probe; uint frame_id; uint reserved;
} pc;
const uint FULL = 2u;
uint mix32(uint x) {
    x ^= x >> 16u; x *= 0x7feb352du;
    x ^= x >> 15u; x *= 0x846ca68bu;
    x ^= x >> 16u; return x;
}
uint hash_key(ivec4 key) {
    uint h = mix32(uint(key.x));
    h ^= mix32(uint(key.y) ^ 0x9e3779b9u);
    h ^= mix32(uint(key.z) ^ 0x85ebca6bu);
    h ^= mix32(uint(key.w) ^ 0xc2b2ae35u);
    return mix32(h);
}
void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= counters.data[0]) return;
    WorkItem item = work.items[id];
    if (item.ray_index != 0u) return;
    ivec4 key = ivec4(
        item.probe_x, item.probe_y, item.probe_z, int(item.cascade));
    uint slot = hash_key(key) & pc.mask;
    for (uint probe = 0u; probe < pc.max_probe; ++probe) {
        Slot candidate = slots.values[slot];
        if (candidate.data.x == 0u) break;
        if (candidate.data.x == FULL &&
            candidate.data.w == pc.frame_id &&
            all(equal(candidate.key, key))) {
            resolved.values[item.output_id] =
                candidate.data.z == 0u ? 0.0 :
                float(candidate.data.y) /
                (float(candidate.data.z) * 65535.0);
            return;
        }
        slot = (slot + 1u) & pc.mask;
    }
    resolved.values[item.output_id] = 0.0;
}

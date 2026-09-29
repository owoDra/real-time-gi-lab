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
const uint EMPTY = 0u;
const uint TOMBSTONE = 0xffffffffu;

uint pack_key(ivec4 key) {
    if (key.x < 0 || key.x > 1023 ||
        key.y < 0 || key.y > 1023 ||
        key.z < 0 || key.z > 1023 ||
        key.w < 0 || key.w > 3) {
        return TOMBSTONE;
    }
    uint packed =
        uint(key.x) |
        (uint(key.y) << 10u) |
        (uint(key.z) << 20u) |
        (uint(key.w) << 30u);
    if (packed >= 0xfffffffeu) return TOMBSTONE;
    return packed + 1u;
}

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= counters.data[0]) return;
    WorkItem item = work.items[id];
    if (item.ray_index != 0u) return;

    ivec4 key = ivec4(
        item.probe_x, item.probe_y, item.probe_z, int(item.cascade));
    uint token = pack_key(key);
    if (token == TOMBSTONE) {
        resolved.values[item.output_id] = 0.0;
        return;
    }

    uint slot = token * 0x9e3779b9u;
    slot ^= slot >> 16u;
    slot &= pc.mask;
    for (uint probe = 0u; probe < pc.max_probe; ++probe) {
        Slot candidate = slots.values[slot];
        if (candidate.data.x == EMPTY) break;
        if (candidate.data.x == token &&
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

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
layout(std430, binding = 2) readonly buffer Accum { uvec2 values[]; } accum;
layout(std430, binding = 3) buffer Slots { Slot values[]; } slots;
layout(std430, binding = 4) buffer StorageCounters { uint data[]; } stats;
layout(push_constant) uniform Push {
    uint mask; uint max_probe; uint frame_id; uint reserved;
} pc;
const uint EMPTY = 0u;
const uint LOCKED = 1u;
const uint FULL = 2u;
const uint TOMBSTONE = 3u;
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
bool same_key(ivec4 a, ivec4 b) { return all(equal(a, b)); }

uint acquire_slot(ivec4 key) {
    uint slot = hash_key(key) & pc.mask;
    for (uint probe = 0u; probe < pc.max_probe; ++probe) {
        for (uint spin = 0u; spin < 64u; ++spin) {
            uint state = slots.values[slot].data.x;
            if (state == LOCKED) continue;
            if (state == FULL) {
                if (!same_key(slots.values[slot].key, key)) break;
                if (slots.values[slot].data.w != pc.frame_id) {
                    if (atomicCompSwap(
                            slots.values[slot].data.x,
                            FULL,
                            LOCKED) != FULL) {
                        continue;
                    }
                    slots.values[slot].data.y = 0u;
                    slots.values[slot].data.z = 0u;
                    slots.values[slot].data.w = pc.frame_id;
                    memoryBarrierBuffer();
                    atomicExchange(slots.values[slot].data.x, FULL);
                }
                return slot;
            }
            if (state == EMPTY || state == TOMBSTONE) {
                if (atomicCompSwap(
                        slots.values[slot].data.x,
                        state,
                        LOCKED) != state) {
                    continue;
                }
                slots.values[slot].key = key;
                slots.values[slot].data.y = 0u;
                slots.values[slot].data.z = 0u;
                slots.values[slot].data.w = pc.frame_id;
                memoryBarrierBuffer();
                atomicExchange(slots.values[slot].data.x, FULL);
                atomicAdd(stats.data[0], 1u);
                return slot;
            }
            break;
        }
        slot = (slot + 1u) & pc.mask;
    }
    atomicAdd(stats.data[3], 1u);
    return 0xffffffffu;
}

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= counters.data[0]) return;
    WorkItem item = work.items[id];
    if (item.ray_index != 0u) return;
    uvec2 merged = accum.values[item.output_id];
    if (merged.y == 0u) return;
    uint sample_value = (merged.x + merged.y / 2u) / merged.y;
    ivec4 key = ivec4(
        item.probe_x, item.probe_y, item.probe_z, int(item.cascade));
    uint slot = acquire_slot(key);
    if (slot == 0xffffffffu) return;
    atomicAdd(slots.values[slot].data.y, sample_value);
    atomicAdd(slots.values[slot].data.z, 1u);
    atomicAdd(stats.data[1], 1u);
}

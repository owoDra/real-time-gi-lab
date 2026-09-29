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
    uint mask; uint max_probe; uint frame_id; uint phase;
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

    // 0 is EMPTY and 0xffffffff is TOMBSTONE. I001's producer contract keeps
    // coordinates far below the only packed values that would alias these
    // sentinels; reject them explicitly instead of silently colliding.
    if (packed >= 0xfffffffeu) return TOMBSTONE;
    return packed + 1u;
}

uint reserve_slot(ivec4 key, uint token) {
    uint slot = token * 0x9e3779b9u;
    slot ^= slot >> 16u;
    slot &= pc.mask;

    for (uint probe = 0u; probe < pc.max_probe; ++probe) {
        uint candidate = slots.values[slot].data.x;
        if (candidate == token) return slot;

        if (candidate == EMPTY || candidate == TOMBSTONE) {
            uint old = atomicCompSwap(
                slots.values[slot].data.x,
                candidate,
                token);
            if (old == candidate) {
                slots.values[slot].key = key;
                atomicAdd(stats.data[0], 1u);
                return slot;
            }
            if (old == token) return slot;
        }
        slot = (slot + 1u) & pc.mask;
    }
    return TOMBSTONE;
}

uint find_slot(ivec4 key, uint token) {
    uint slot = token * 0x9e3779b9u;
    slot ^= slot >> 16u;
    slot &= pc.mask;

    for (uint probe = 0u; probe < pc.max_probe; ++probe) {
        uint candidate = slots.values[slot].data.x;
        if (candidate == EMPTY) break;
        if (candidate == token && all(equal(slots.values[slot].key, key))) {
            return slot;
        }
        slot = (slot + 1u) & pc.mask;
    }
    return TOMBSTONE;
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
        atomicAdd(stats.data[3], 1u);
        return;
    }

    if (pc.phase == 0u) {
        uint slot = reserve_slot(key, token);
        if (slot == TOMBSTONE) {
            atomicAdd(stats.data[3], 1u);
            return;
        }

        // Reservation and accumulation are separate dispatches. Exactly one
        // invocation advances the frame tag and resets the accumulator, while
        // the dispatch barrier guarantees the reset completes before phase 1.
        uint previous = atomicExchange(
            slots.values[slot].data.w,
            pc.frame_id);
        if (previous != pc.frame_id) {
            atomicExchange(slots.values[slot].data.y, 0u);
            atomicExchange(slots.values[slot].data.z, 0u);
        }
        return;
    }

    uint slot = find_slot(key, token);
    if (slot == TOMBSTONE || slots.values[slot].data.w != pc.frame_id) {
        atomicAdd(stats.data[3], 1u);
        return;
    }

    uvec2 merged = accum.values[item.output_id];
    if (merged.y == 0u) return;
    uint sample_value = (merged.x + merged.y / 2u) / merged.y;
    atomicAdd(slots.values[slot].data.y, sample_value);
    atomicAdd(slots.values[slot].data.z, 1u);
    atomicAdd(stats.data[1], 1u);
}

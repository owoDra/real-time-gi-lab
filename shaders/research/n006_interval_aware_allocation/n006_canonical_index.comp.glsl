#version 460
// P1g: one representative owner-cascade output per spatial probe key.
layout(local_size_x = 64) in;
struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};
layout(std430, binding = 0) readonly buffer Counters { uint data[]; } counters;
layout(std430, binding = 1) readonly buffer Work { WorkItem items[]; } work;
layout(std430, binding = 2) buffer Keys { uint values[]; } keys;
layout(std430, binding = 3) buffer Stats { uint data[]; } stats;
layout(std430, binding = 4) buffer Reps { uint indices[]; } representatives;
layout(push_constant) uniform Push {
    uint mask; uint max_probe; uint rays_per_probe; uint capacity;
} pc;
uint mix32(uint x) {
    x ^= x >> 16u; x *= 0x7feb352du;
    x ^= x >> 15u; x *= 0x846ca68bu;
    x ^= x >> 16u; return x;
}
uint pack_key(ivec4 key) {
    if (any(lessThan(key, ivec4(0))) ||
        any(greaterThan(key, ivec4(1023,1023,1023,3)))) return 0xffffffffu;
    uint value = uint(key.x) | (uint(key.y) << 10u) |
                 (uint(key.z) << 20u) | (uint(key.w) << 30u);
    return value >= 0xfffffffeu ? 0xffffffffu : value + 1u;
}
void main() {
    uint owner_output = gl_GlobalInvocationID.x;
    uint work_index = owner_output * pc.rays_per_probe;
    if (work_index >= counters.data[0]) return;
    WorkItem item = work.items[work_index];
    if (item.ray_index != 0u || item.cascade >= 4u) {
        atomicAdd(stats.data[2], 1u);
        return;
    }
    uint token = pack_key(ivec4(item.probe_x, item.probe_y,
                                 item.probe_z, int(item.cascade)));
    if (token == 0xffffffffu) {
        atomicAdd(stats.data[2], 1u);
        return;
    }
    uint slot = mix32(token) & pc.mask;
    for (uint attempt = 0u; attempt < pc.max_probe; ++attempt) {
        uint old = atomicCompSwap(keys.values[slot], 0u, token);
        if (old == 0u) {
            uint index = atomicAdd(stats.data[0], 1u);
            if (index < pc.capacity) {
                representatives.indices[index] = owner_output;
                atomicAdd(stats.data[6u + item.cascade], 1u);
            } else {
                atomicAdd(stats.data[5], 1u);
            }
            return;
        }
        if (old == token) {
            atomicAdd(stats.data[1], 1u);
            return;
        }
        atomicAdd(stats.data[4], 1u);
        slot = (slot + 1u) & pc.mask;
    }
    atomicAdd(stats.data[3], 1u);
}
#version 460
// N006 P1d ONLY: diagnostic hash of existing owner-cascade ray-0 inputs.
// Does not alter work, output IDs, trace count or renderer's final image.
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
layout(push_constant) uniform Push {
    uint mask;
    uint max_probe;
    uint rays_per_probe;
    uint cascade_count;
} pc;
const uint INVALID = 0xffffffffu;

uint mix32(uint x) {
    x ^= x >> 16u;
    x *= 0x7feb352du;
    x ^= x >> 15u;
    x *= 0x846ca68bu;
    x ^= x >> 16u;
    return x;
}
uint pack_key(ivec4 key) {
    if (any(lessThan(key, ivec4(0))) ||
        any(greaterThan(key, ivec4(1023, 1023, 1023, 3)))) {
        return INVALID;
    }
    uint packed = uint(key.x) | (uint(key.y) << 10u) |
                  (uint(key.z) << 20u) | (uint(key.w) << 30u);
    if (packed >= 0xfffffffeu) return INVALID;
    return packed + 1u;
}
void main() {
    const uint output_block = gl_GlobalInvocationID.x;
    if (pc.rays_per_probe == 0u || pc.cascade_count != 4u) return;
    const uint work_id = output_block * pc.rays_per_probe;
    if (work_id >= counters.data[0]) return;
    WorkItem item = work.items[work_id];
    if (item.ray_index != 0u || item.cascade >= 4u) {
        atomicAdd(stats.data[2], 1u);
        return;
    }
    const uint token = pack_key(ivec4(
        item.probe_x, item.probe_y, item.probe_z, int(item.cascade)));
    if (token == INVALID) {
        atomicAdd(stats.data[2], 1u);
        return;
    }
    uint slot = mix32(token) & pc.mask;
    for (uint attempts = 0u; attempts < pc.max_probe; ++attempts) {
        const uint existing = atomicCompSwap(keys.values[slot], 0u, token);
        if (existing == 0u) {
            atomicAdd(stats.data[0], 1u);
            atomicAdd(stats.data[6u + item.cascade], 1u);
            atomicAdd(stats.data[4], attempts);
            return;
        }
        if (existing == token) {
            atomicAdd(stats.data[1], 1u);
            atomicAdd(stats.data[10u + item.cascade], 1u);
            atomicAdd(stats.data[4], attempts);
            return;
        }
        slot = (slot + 1u) & pc.mask;
    }
    atomicAdd(stats.data[3], 1u);
}

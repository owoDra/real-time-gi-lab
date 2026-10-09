#version 460
// P1g-only: restore the original summed-owner integer storage numerator
// and denominator after tracing only one canonical 8-ray sample per key.
// This retains accepted composite float32 normalization exactly.
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
layout(std430, binding = 2) readonly buffer KeyTokens { uint values[]; } keys;
layout(std430, binding = 3) readonly buffer Multiplicity { uint counts[]; } multiplicity;
layout(std430, binding = 4) buffer StorageSlots { Slot values[]; } storage;
layout(std430, binding = 5) buffer Stats { uint data[]; } stats;
layout(push_constant) uniform Push {
    uint key_mask;
    uint storage_mask;
    uint max_probe;
    uint frame_id;
} pc;
const uint INVALID = 0xffffffffu;
uint mix32(uint x) {
    x ^= x >> 16u; x *= 0x7feb352du;
    x ^= x >> 15u; x *= 0x846ca68bu;
    x ^= x >> 16u; return x;
}
uint pack_key(ivec4 key) {
    if (any(lessThan(key, ivec4(0))) ||
        any(greaterThan(key, ivec4(1023, 1023, 1023, 3)))) return INVALID;
    uint v = uint(key.x) | (uint(key.y) << 10u) |
             (uint(key.z) << 20u) | (uint(key.w) << 30u);
    return v >= 0xfffffffeu ? INVALID : v + 1u;
}
void fail() { atomicAdd(stats.data[14], 1u); }
void main() {
    uint output_id = gl_GlobalInvocationID.x;
    if (output_id >= counters.data[1]) return;
    WorkItem work_item = work.items[output_id * 8u];
    if (work_item.output_id != output_id ||
        work_item.ray_index != 0u) {
        fail(); return;
    }
    ivec4 key = ivec4(work_item.probe_x, work_item.probe_y,
                      work_item.probe_z, int(work_item.cascade));
    uint token = pack_key(key);
    if (token == INVALID) { fail(); return; }

    uint hash_index = mix32(token) & pc.key_mask;
    uint owner_count = 0u;
    for (uint attempt = 0u; attempt < pc.max_probe; ++attempt) {
        uint found = keys.values[hash_index];
        if (found == token) {
            owner_count = multiplicity.counts[hash_index];
            break;
        }
        if (found == 0u) break;
        hash_index = (hash_index + 1u) & pc.key_mask;
    }
    if (owner_count == 0u) { fail(); return; }

    uint storage_index = mix32(token) & pc.storage_mask;
    for (uint attempt = 0u; attempt < pc.max_probe; ++attempt) {
        Slot slot = storage.values[storage_index];
        if (slot.data.x == 0u) break;
        if (slot.data.x == token &&
            slot.data.w == pc.frame_id &&
            all(equal(slot.key, key))) {
            // After canonical storage accumulation exactly one owner exists
            // at this key. Multiply integer counters before composite runs.
            if (slot.data.z != 1u ||
                (owner_count != 0u && slot.data.y > 0xffffffffu / owner_count)) {
                fail(); return;
            }
            storage.values[storage_index].data.y = slot.data.y * owner_count;
            storage.values[storage_index].data.z = owner_count;
            atomicAdd(stats.data[15], owner_count);
            return;
        }
        storage_index = (storage_index + 1u) & pc.storage_mask;
    }
    fail();
}

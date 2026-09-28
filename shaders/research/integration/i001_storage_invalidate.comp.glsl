#version 460
layout(local_size_x = 64) in;
struct Slot { ivec4 key; uvec4 data; };
layout(std430, binding = 0) buffer Slots { Slot values[]; } slots;
layout(std430, binding = 1) buffer StorageCounters { uint data[]; } stats;
layout(push_constant) uniform Push {
    uint slot_count; uint frame_id; uint reserved0; uint reserved1;
} pc;
const uint FULL = 2u;
const uint TOMBSTONE = 3u;
void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= pc.slot_count) return;
    if (slots.values[id].data.x != FULL ||
        slots.values[id].data.w == pc.frame_id) return;
    if (atomicCompSwap(slots.values[id].data.x, FULL, TOMBSTONE) == FULL) {
        slots.values[id].data.y = 0u;
        slots.values[id].data.z = 0u;
        atomicAdd(stats.data[2], 1u);
    }
}

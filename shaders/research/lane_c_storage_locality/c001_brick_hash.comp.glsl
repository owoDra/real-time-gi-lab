#version 450
layout(local_size_x = 256) in;
struct Unit { uint cascade; uint x; uint y; uint z; };
struct Address { uint probe_key; uint brick_key; uint local_index; uint payload; };
layout(std430, binding = 0) readonly buffer Inputs { Unit inputs[]; };
layout(std430, binding = 1) readonly buffer Addresses { Address addresses[]; };
layout(std430, binding = 2) buffer DirectoryKeys { uint keys[]; };
layout(std430, binding = 3) buffer DirectoryValues { uint values[]; };
layout(std430, binding = 4) buffer Payloads { uint payloads[]; };
layout(std430, binding = 5) writeonly buffer Outputs { uint outputs[]; };
layout(std430, binding = 6) buffer Counters { uint counters[]; };
layout(std430, binding = 7) buffer B7 { uint b7[]; };
layout(push_constant) uniform Push {
    uint count; uint op; uint mask; uint max_probe;
    uint brick_edge; uint clip_x; uint clip_y; uint clip_z;
} pc;
const uint TOMBSTONE = 0xffffffffu;
uint mix32(uint x) {
    x ^= x >> 16; x *= 0x7feb352du; x ^= x >> 15;
    x *= 0x846ca68bu; x ^= x >> 16; return x;
}
uint brick_key(Unit b) {
    return (((b.cascade * pc.clip_z + b.z) * pc.clip_y + b.y) * pc.clip_x + b.x) + 1u;
}
uint find_slot(uint key) {
    uint slot = mix32(key) & pc.mask;
    for (uint probe = 0u; probe < pc.max_probe; ++probe) {
        const uint candidate = keys[slot];
        if (candidate == key) return slot;
        if (candidate == 0u) break;
        slot = (slot + 1u) & pc.mask;
    }
    return 0xffffffffu;
}
uint reserve_slot(uint key) {
    uint slot = mix32(key) & pc.mask;
    for (uint probe = 0u; probe < pc.max_probe; ++probe) {
        uint candidate = keys[slot];
        if (candidate == key) return slot;
        if (candidate == 0u || candidate == TOMBSTONE) {
            const uint old = atomicCompSwap(keys[slot], candidate, key);
            if (old == candidate || old == key) return slot;
        }
        slot = (slot + 1u) & pc.mask;
    }
    atomicAdd(counters[1], 1u);
    return 0xffffffffu;
}
void main() {
    const uint i = gl_GlobalInvocationID.x;
    if (i >= pc.count) return;
    if (pc.op == 0u) {
        const uint slot = reserve_slot(brick_key(inputs[i]));
        if (slot == 0xffffffffu) return;
        if (values[slot] == 0u) values[slot] = atomicAdd(counters[0], 1u) + 1u;
        return;
    }
    if (pc.op == 5u) {
        const uint slot = find_slot(brick_key(inputs[i]));
        if (slot != 0xffffffffu) { values[slot] = 0u; atomicExchange(keys[slot], TOMBSTONE); }
        return;
    }
    const Address a = addresses[i];
    const uint slot = find_slot(a.brick_key);
    if (slot == 0xffffffffu || values[slot] == 0u) {
        if (pc.op == 2u) outputs[i] = 0u; else atomicAdd(counters[1], 1u);
        return;
    }
    const uint physical = values[slot] - 1u;
    const uint payload_index = physical * pc.brick_edge * pc.brick_edge * pc.brick_edge + a.local_index;
    if (pc.op == 1u) payloads[payload_index] = a.payload;
    else if (pc.op == 2u) outputs[i] = payloads[payload_index];
    else if (pc.op == 3u) payloads[payload_index] = a.payload ^ 0xa5a5a5a5u;
    else if (pc.op == 4u) payloads[payload_index] = 0u;
}

#version 450
layout(local_size_x = 256) in;
struct Address { uint probe_key; uint brick_key; uint local_index; uint payload; };
layout(std430, binding = 0) readonly buffer B0 { uint b0[]; };
layout(std430, binding = 1) readonly buffer Addresses { Address addresses[]; };
layout(std430, binding = 2) buffer Keys { uint keys[]; };
layout(std430, binding = 3) buffer B3 { uint b3[]; };
layout(std430, binding = 4) buffer Payloads { uint payloads[]; };
layout(std430, binding = 5) writeonly buffer Outputs { uint outputs[]; };
layout(std430, binding = 6) buffer Counters { uint counters[]; };
layout(std430, binding = 7) buffer B7 { uint b7[]; };
layout(push_constant) uniform Push {
    uint count; uint op; uint mask; uint max_probe;
    uint brick_edge; uint clip_x; uint clip_y; uint clip_z;
} pc;

const uint TOMBSTONE = 0xffffffffu;
const uint TARGET = 0x80000000u;
const uint KEY_MASK = 0x7fffffffu;

uint mix32(uint x) {
    x ^= x >> 16; x *= 0x7feb352du; x ^= x >> 15;
    x *= 0x846ca68bu; x ^= x >> 16; return x;
}
uint base_key(uint x) { return x & KEY_MASK; }

uint find_slot(uint key) {
    uint slot = mix32(key) & pc.mask;
    for (uint probe = 0u; probe < pc.max_probe; ++probe) {
        const uint candidate = keys[slot];
        if (candidate != TOMBSTONE && base_key(candidate) == key) return slot;
        if (candidate == 0u) break;
        slot = (slot + 1u) & pc.mask;
    }
    return 0xffffffffu;
}

void mark_target(uint key) {
    uint slot = mix32(key) & pc.mask;
    for (uint probe = 0u; probe < pc.max_probe; ++probe) {
        const uint candidate = keys[slot];
        if (candidate != TOMBSTONE && base_key(candidate) == key) {
            atomicOr(keys[slot], TARGET);
            return;
        }
        if (candidate == 0u || candidate == TOMBSTONE) {
            const uint old = atomicCompSwap(keys[slot], candidate, key | TARGET);
            if (old == candidate) return;
            if (old != TOMBSTONE && base_key(old) == key) {
                atomicOr(keys[slot], TARGET);
                return;
            }
        }
        slot = (slot + 1u) & pc.mask;
    }
    atomicAdd(counters[1], 1u);
}

void main() {
    const uint i = gl_GlobalInvocationID.x;
    if (i >= pc.count) return;

    if (pc.op == 14u) {
        const uint candidate = keys[i];
        if (candidate == 0u || candidate == TOMBSTONE) return;
        if ((candidate & TARGET) != 0u) {
            atomicAnd(keys[i], KEY_MASK);
        } else {
            payloads[i] = 0u;
            atomicExchange(keys[i], TOMBSTONE);
            atomicAdd(counters[2], 1u);
        }
        return;
    }

    const Address a = addresses[i];
    if (a.payload == 0u) {
        if (pc.op == 16u) outputs[i] = 0u;
        return;
    }

    if (pc.op == 13u) {
        mark_target(a.probe_key);
        return;
    }

    const uint slot = find_slot(a.probe_key);
    if (slot == 0xffffffffu) {
        if (pc.op == 16u) {
            outputs[i] = 0u;
            return;
        }
        atomicAdd(counters[1], 1u);
        return;
    }
    if (pc.op == 15u) atomicExchange(payloads[slot], a.payload);
    else if (pc.op == 16u) outputs[i] = payloads[slot];
}

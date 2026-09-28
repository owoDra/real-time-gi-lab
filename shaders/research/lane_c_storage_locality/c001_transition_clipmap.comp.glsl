#version 450
layout(local_size_x = 256) in;
struct Address { uint probe_key; uint brick_key; uint local_index; uint payload; };
layout(std430, binding = 0) readonly buffer B0 { uint b0[]; };
layout(std430, binding = 1) readonly buffer Addresses { Address addresses[]; };
layout(std430, binding = 2) buffer Pages { uint pages[]; };
layout(std430, binding = 3) buffer Tags { uint tags[]; };
layout(std430, binding = 4) buffer Payloads { uint payloads[]; };
layout(std430, binding = 5) writeonly buffer Outputs { uint outputs[]; };
layout(std430, binding = 6) buffer Counters { uint counters[]; };
layout(std430, binding = 7) buffer FreeList { uint free_list[]; };
layout(push_constant) uniform Push {
    uint count; uint op; uint mask; uint max_probe;
    uint brick_edge; uint clip_x; uint clip_y; uint clip_z;
} pc;

const uint TARGET = 0x80000000u;
const uint TAG_MASK = 0x7fffffffu;
const uint INIT = 0xffffffffu;

uint brick_tag(Address a) {
    return ((a.probe_key - 1u) /
        (pc.brick_edge * pc.brick_edge * pc.brick_edge)) + 1u;
}
void clear_physical(uint physical) {
    const uint cells = pc.brick_edge * pc.brick_edge * pc.brick_edge;
    const uint base = physical * cells;
    for (uint local = 0u; local < cells; ++local) payloads[base + local] = 0u;
}
uint claim_physical() {
    const uint claim = atomicAdd(counters[3], 1u);
    const uint available = atomicAdd(counters[2], 0u);
    if (claim < available) return free_list[available - 1u - claim];
    return atomicAdd(counters[0], 1u);
}

void main() {
    const uint i = gl_GlobalInvocationID.x;
    if (i >= pc.count) return;

    if (pc.op == 14u) {
        const uint tag = tags[i];
        if (tag == 0u) return;
        if ((tag & TARGET) != 0u) {
            atomicAnd(tags[i], TAG_MASK);
            return;
        }
        const uint mapped = pages[i];
        if (mapped != 0u && mapped != INIT) {
            const uint free_index = atomicAdd(counters[2], 1u);
            free_list[free_index] = mapped - 1u;
        }
        pages[i] = 0u;
        tags[i] = 0u;
        return;
    }
    if (pc.op == 16u) {
        if (i == 0u) {
            const uint available = atomicAdd(counters[2], 0u);
            const uint claimed = atomicAdd(counters[3], 0u);
            counters[2] = claimed < available ? available - claimed : 0u;
            counters[3] = 0u;
        }
        return;
    }

    const Address a = addresses[i];
    if (a.payload == 0u) {
        if (pc.op == 18u) outputs[i] = 0u;
        return;
    }
    const uint slot = a.brick_key - 1u;
    const uint desired = brick_tag(a);
    if (desired >= TAG_MASK) {
        atomicAdd(counters[1], 1u);
        return;
    }

    if (pc.op == 13u) {
        for (;;) {
            const uint current = atomicAdd(tags[slot], 0u);
            if (current == INIT) continue;
            if ((current & TAG_MASK) == desired && current != 0u) {
                atomicOr(tags[slot], TARGET);
                return;
            }
            if (current == 0u) {
                const uint old = atomicCompSwap(tags[slot], 0u, desired | TARGET);
                if (old == 0u) return;
                continue;
            }
            const uint old = atomicCompSwap(tags[slot], current, INIT);
            if (old != current) continue;
            const uint mapped = pages[slot];
            if (mapped != 0u && mapped != INIT) clear_physical(mapped - 1u);
            memoryBarrierBuffer();
            tags[slot] = desired | TARGET;
            return;
        }
    }

    if (pc.op == 15u) {
        if ((tags[slot] & TAG_MASK) != desired) {
            atomicAdd(counters[1], 1u);
            return;
        }
        uint mapped = pages[slot];
        if (mapped == 0u) {
            const uint old = atomicCompSwap(pages[slot], 0u, INIT);
            if (old == 0u) {
                const uint physical = claim_physical();
                if (physical >= pc.max_probe) {
                    atomicAdd(counters[1], 1u);
                    atomicExchange(pages[slot], 0u);
                    return;
                }
                atomicExchange(pages[slot], physical + 1u);
                return;
            }
            mapped = old;
        }
        while (mapped == INIT) mapped = atomicAdd(pages[slot], 0u);
        return;
    }

    const uint mapped = pages[slot];
    if (mapped == 0u || mapped == INIT || (tags[slot] & TAG_MASK) != desired) {
        if (pc.op == 18u) {
            outputs[i] = 0u;
            return;
        }
        atomicAdd(counters[1], 1u);
        return;
    }
    const uint physical = mapped - 1u;
    const uint payload_index =
        physical * pc.brick_edge * pc.brick_edge * pc.brick_edge + a.local_index;
    if (pc.op == 17u) atomicExchange(payloads[payload_index], a.payload);
    else if (pc.op == 18u) outputs[i] = payloads[payload_index];
}

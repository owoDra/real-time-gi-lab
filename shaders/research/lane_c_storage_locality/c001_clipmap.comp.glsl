#version 450
layout(local_size_x = 256) in;
struct Unit { uint cascade; uint x; uint y; uint z; };
struct Address { uint probe_key; uint brick_key; uint local_index; uint payload; };
layout(std430, binding = 0) readonly buffer Inputs { Unit inputs[]; };
layout(std430, binding = 1) readonly buffer Addresses { Address addresses[]; };
layout(std430, binding = 2) buffer PageTable { uint pages[]; };
layout(std430, binding = 3) buffer B3 { uint b3[]; };
layout(std430, binding = 4) buffer Payloads { uint payloads[]; };
layout(std430, binding = 5) writeonly buffer Outputs { uint outputs[]; };
layout(std430, binding = 6) buffer Counters { uint counters[]; };
layout(std430, binding = 7) buffer FreeList { uint free_list[]; };
layout(push_constant) uniform Push {
    uint count; uint op; uint mask; uint max_probe;
    uint brick_edge; uint clip_x; uint clip_y; uint clip_z;
} pc;
uint take_physical() {
    for (;;) {
        const uint count = atomicAdd(counters[2], 0u);
        if (count == 0u) return atomicAdd(counters[0], 1u);
        const uint old = atomicCompSwap(counters[2], count, count - 1u);
        if (old == count) return free_list[count - 1u];
    }
}
uint claim_reclaimed_physical() {
    const uint claim = atomicAdd(counters[3], 1u);
    const uint available = atomicAdd(counters[2], 0u);
    if (claim >= available) {
        atomicAdd(counters[1], 1u);
        return 0xffffffffu;
    }
    return free_list[available - 1u - claim];
}
void finalize_reclaimed_batch() {
    const uint available = atomicAdd(counters[2], 0u);
    const uint claimed = atomicAdd(counters[3], 0u);
    if (claimed > available) {
        atomicAdd(counters[1], 1u);
        return;
    }
    counters[2] = available - claimed;
    counters[3] = 0u;
}
uint page_of(Unit b) {
    return (((b.cascade * pc.clip_z + b.z) * pc.clip_y + b.y) * pc.clip_x + b.x);
}
void main() {
    const uint i = gl_GlobalInvocationID.x;
    if (i >= pc.count) return;
    if (pc.op >= 8u && pc.op <= 12u) {
        const Address a = addresses[i];
        if (a.payload == 0u) {
            if (pc.op == 12u) outputs[i] = 0u;
            return;
        }
        const uint page = a.brick_key - 1u;
        if (pc.op == 8u) {
            const uint old = atomicCompSwap(pages[page], 0u, 0xffffffffu);
            if (old == 0u) {
                const uint physical = atomicAdd(counters[0], 1u);
                if (physical >= pc.max_probe) {
                    atomicAdd(counters[1], 1u);
                    atomicExchange(pages[page], 0u);
                } else {
                    atomicExchange(pages[page], physical + 1u);
                }
            }
            return;
        }
        const uint mapped = pages[page];
        if (mapped == 0u || mapped == 0xffffffffu) {
            atomicAdd(counters[1], 1u);
            return;
        }
        const uint physical = mapped - 1u;
        const uint payload_index =
            physical * pc.brick_edge * pc.brick_edge * pc.brick_edge + a.local_index;
        if (pc.op == 9u) atomicExchange(payloads[payload_index], a.payload);
        else if (pc.op == 10u) atomicExchange(payloads[payload_index], a.payload ^ 0xa5a5a5a5u);
        else if (pc.op == 11u) atomicExchange(payloads[payload_index], 0u);
        else if (pc.op == 12u) outputs[i] = payloads[payload_index];
        return;
    }
    if (pc.op == 0u) {
        const uint page = page_of(inputs[i]);
        if (pages[page] == 0u) pages[page] = take_physical() + 1u;
        return;
    }
    if (pc.op == 6u) {
        const uint page = page_of(inputs[i]);
        if (pages[page] == 0u) {
            const uint physical = claim_reclaimed_physical();
            if (physical != 0xffffffffu) pages[page] = physical + 1u;
        }
        return;
    }
    if (pc.op == 7u) {
        if (i == 0u) finalize_reclaimed_batch();
        return;
    }
    if (pc.op == 5u) {
        const uint page = page_of(inputs[i]);
        const uint mapped = pages[page];
        if (mapped != 0u) {
            const uint free_index = atomicAdd(counters[2], 1u);
            free_list[free_index] = mapped - 1u;
            pages[page] = 0u;
        }
        return;
    }
    const Address a = addresses[i];
    const uint mapped = pages[a.brick_key - 1u];
    if (mapped == 0u) {
        if (pc.op == 2u) outputs[i] = 0u; else atomicAdd(counters[1], 1u);
        return;
    }
    const uint physical = mapped - 1u;
    const uint payload_index = physical * pc.brick_edge * pc.brick_edge * pc.brick_edge + a.local_index;
    if (pc.op == 1u) payloads[payload_index] = a.payload;
    else if (pc.op == 2u) outputs[i] = payloads[payload_index];
    else if (pc.op == 3u) payloads[payload_index] = a.payload ^ 0xa5a5a5a5u;
    else if (pc.op == 4u) payloads[payload_index] = 0u;
}

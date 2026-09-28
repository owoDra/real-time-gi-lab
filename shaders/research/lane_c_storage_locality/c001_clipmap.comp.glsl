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
layout(std430, binding = 7) buffer B7 { uint b7[]; };
layout(push_constant) uniform Push {
    uint count; uint op; uint mask; uint max_probe;
    uint brick_edge; uint clip_x; uint clip_y; uint clip_z;
} pc;
uint page_of(Unit b) {
    return (((b.cascade * pc.clip_z + b.z) * pc.clip_y + b.y) * pc.clip_x + b.x);
}
void main() {
    const uint i = gl_GlobalInvocationID.x;
    if (i >= pc.count) return;
    if (pc.op == 0u) {
        const uint page = page_of(inputs[i]);
        if (pages[page] == 0u) pages[page] = atomicAdd(counters[0], 1u) + 1u;
        return;
    }
    if (pc.op == 5u) { pages[page_of(inputs[i])] = 0u; return; }
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

#version 450
layout(local_size_x = 256) in;
struct Probe { uint cascade; uint x; uint y; uint z; };
struct Address { uint probe_key; uint brick_key; uint local_index; uint payload; };
layout(std430, binding = 0) readonly buffer Inputs { Probe probes[]; };
layout(std430, binding = 1) writeonly buffer Addresses { Address addresses[]; };
layout(std430, binding = 2) buffer B2 { uint b2[]; };
layout(std430, binding = 3) buffer B3 { uint b3[]; };
layout(std430, binding = 4) buffer B4 { uint b4[]; };
layout(std430, binding = 5) buffer B5 { uint b5[]; };
layout(std430, binding = 6) buffer B6 { uint b6[]; };
layout(std430, binding = 7) buffer B7 { uint b7[]; };
layout(push_constant) uniform Push {
    uint count; uint op; uint mask; uint max_probe;
    uint brick_edge; uint clip_x; uint clip_y; uint clip_z;
} pc;
uint mix32(uint x) {
    x ^= x >> 16; x *= 0x7feb352du; x ^= x >> 15;
    x *= 0x846ca68bu; x ^= x >> 16;
    return x == 0u ? 1u : x;
}
void main() {
    const uint i = gl_GlobalInvocationID.x;
    if (i >= pc.count) return;
    const Probe p = probes[i];
    const uint edge = pc.brick_edge;
    const uint bx = p.x / edge, by = p.y / edge, bz = p.z / edge;
    const uint lx = p.x - bx * edge, ly = p.y - by * edge, lz = p.z - bz * edge;
    const uint local = lx + edge * (ly + edge * lz);
    const uint page = (((p.cascade * pc.clip_z + bz) * pc.clip_y + by) * pc.clip_x + bx);
    const uint key = page * edge * edge * edge + local + 1u;
    Address a;
    a.probe_key = key;
    a.payload = mix32(key ^ 0x9e3779b9u);
    if (pc.op == 0u) { a.brick_key = 0u; a.local_index = 0u; }
    else { a.brick_key = page + 1u; a.local_index = local; }
    addresses[i] = a;
}

#version 460
layout(local_size_x = 256) in;

struct Query { uint key; uint page_id; uint local_index; uint pad; };
layout(std430, set = 0, binding = 0) readonly buffer Queries { Query q[]; } queries;
layout(std430, set = 0, binding = 1) readonly buffer Keys { uint v[]; } keys;
layout(std430, set = 0, binding = 2) readonly buffer Payload { uint v[]; } payload;
layout(std430, set = 0, binding = 3) writeonly buffer Output { uint v[]; } output_data;
layout(push_constant) uniform Push {
    uint query_count;
    uint table_mask;
    uint lookup_limit;
    uint pad;
} pc;

uint mix32(uint x) {
    x ^= x >> 16;
    x *= 0x7feb352du;
    x ^= x >> 15;
    x *= 0x846ca68bu;
    x ^= x >> 16;
    return x == 0u ? 1u : x;
}

void main() {
    uint i = gl_GlobalInvocationID.x;
    if (i >= pc.query_count) return;

    uint key = queries.q[i].key;
    uint slot = mix32(key) & pc.table_mask;
    uint result = 0u;

    for (uint probe = 0u; probe < pc.lookup_limit; ++probe) {
        uint candidate = keys.v[slot];
        if (candidate == key) {
            result = payload.v[slot];
            break;
        }
        if (candidate == 0u) break;
        slot = (slot + 1u) & pc.table_mask;
    }

    output_data.v[i] = result;
}

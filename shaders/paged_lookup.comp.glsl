#version 460
layout(local_size_x = 256) in;

struct Query { uint key; uint page_id; uint local_index; uint pad; };
layout(std430, set = 0, binding = 0) readonly buffer Queries { Query q[]; } queries;
layout(std430, set = 0, binding = 1) readonly buffer PageTable { uint base[]; } page_table;
layout(std430, set = 0, binding = 2) readonly buffer Payload { uint v[]; } payload;
layout(std430, set = 0, binding = 3) writeonly buffer Output { uint v[]; } output_data;
layout(push_constant) uniform Push { uint query_count; uint page_size; uint mode; uint pad; } pc;

void main() {
    uint i = gl_GlobalInvocationID.x;
    if (i >= pc.query_count) return;
    Query query = queries.q[i];
    uint base = page_table.base[query.page_id];
    output_data.v[i] = payload.v[base + min(query.local_index, pc.page_size - 1u)];
}

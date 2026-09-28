#version 460
layout(local_size_x = 256) in;

struct Query { uint key; uint page_id; uint local_index; uint pad; };
layout(std430, set = 0, binding = 0) readonly buffer Queries { Query q[]; } queries;
layout(std430, set = 0, binding = 1) readonly buffer Offsets { uint v[]; } offsets;
layout(std430, set = 0, binding = 2) buffer Cursors { uint v[]; } cursors;
layout(std430, set = 0, binding = 3) writeonly buffer GroupedQueries { Query q[]; } grouped;

layout(push_constant) uniform Push {
    uint query_count;
    uint page_count;
    uint unused0;
    uint unused1;
} pc;

void main() {
    uint i = gl_GlobalInvocationID.x;
    if (i >= pc.query_count) return;

    Query query = queries.q[i];
    if (query.page_id >= pc.page_count) return;

    uint dst = offsets.v[query.page_id] + atomicAdd(cursors.v[query.page_id], 1u);
    if (dst < pc.query_count) {
        grouped.q[dst] = query;
    }
}

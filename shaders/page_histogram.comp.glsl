#version 460
layout(local_size_x = 256) in;

struct Query { uint key; uint page_id; uint local_index; uint pad; };
layout(std430, set = 0, binding = 0) readonly buffer Queries { Query q[]; } queries;
layout(std430, set = 0, binding = 1) buffer Counts { uint v[]; } counts;

layout(push_constant) uniform Push {
    uint query_count;
    uint page_count;
    uint unused0;
    uint unused1;
} pc;

void main() {
    uint i = gl_GlobalInvocationID.x;
    if (i >= pc.query_count) return;

    uint page = queries.q[i].page_id;
    if (page < pc.page_count) {
        atomicAdd(counts.v[page], 1u);
    }
}

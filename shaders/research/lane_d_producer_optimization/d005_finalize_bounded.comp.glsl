#version 460
layout(local_size_x = 1) in;

layout(std430, set = 0, binding = 2) buffer CounterBuffer {
    uint data[];
} counters;
layout(std430, set = 0, binding = 7) buffer IndirectBuffer {
    uint data[];
} indirect_args;
layout(std140, set = 0, binding = 9) uniform Params {
    vec4 camera_pos_near;
    vec4 camera_right_tan_x;
    vec4 camera_up_tan_y;
    vec4 camera_forward_far;
    vec4 scene_origin_spacing;
    vec4 light_pos_interval;
    uvec4 counts;
    uvec4 limits;
} p;

void main() {
    uint owner_capacity = p.limits.z / p.counts.w;
    uint accepted_owners = min(counters.data[3], owner_capacity);

    uint output_count = accepted_owners * p.counts.w;
    uint work_count = output_count * p.limits.x;

    counters.data[0] = work_count;
    counters.data[1] = output_count;

    indirect_args.data[0] = (work_count + 63u) / 64u;
    indirect_args.data[1] = 1u;
    indirect_args.data[2] = 1u;
    indirect_args.data[3] = (output_count + 63u) / 64u;
    indirect_args.data[4] = 1u;
    indirect_args.data[5] = 1u;
}

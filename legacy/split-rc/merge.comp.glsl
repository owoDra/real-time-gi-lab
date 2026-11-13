#version 460
layout(local_size_x = 64) in;
layout(std430, set = 0, binding = 2) readonly buffer CounterBuffer { uint data[]; } counters;
layout(std430, set = 0, binding = 4) readonly buffer ContributionBuffer { uvec2 values[]; } contributions;
layout(std430, set = 0, binding = 5) buffer AccumBuffer { uvec2 values[]; } accum;
void main() {
    uint item_id = gl_GlobalInvocationID.x; if (item_id >= counters.data[0]) return;
    uvec2 contribution = contributions.values[item_id];
    atomicAdd(accum.values[contribution.x].x, contribution.y);
    atomicAdd(accum.values[contribution.x].y, 1u);
}

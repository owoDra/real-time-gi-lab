#version 460
// P1g: preserve visible owners, replace actual dispatched ray and output counts.
layout(local_size_x = 1) in;
layout(std430, binding = 0) readonly buffer Stats { uint data[]; } stats;
layout(std430, binding = 1) buffer Counters { uint data[]; } counters;
layout(push_constant) uniform Push { uint capacity; uint rays_per_probe; } pc;
void main() {
    uint count = min(stats.data[0], pc.capacity);
    counters.data[0] = count * pc.rays_per_probe;
    counters.data[1] = count;
    counters.data[4] = count * pc.rays_per_probe;
    counters.data[5] = count;
}
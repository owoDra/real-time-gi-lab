#version 460
// P1g GPU-side indirect dispatch for compact outputs and copied rays.
layout(local_size_x = 1) in;
layout(std430, binding = 0) readonly buffer Stats { uint data[]; } stats;
layout(std430, binding = 1) buffer Indirect { uint commands[]; } indirect_args;
layout(push_constant) uniform Push { uint capacity; uint rays_per_probe; } pc;
void main() {
    uint count = min(stats.data[0], pc.capacity);
    uint rays = count * pc.rays_per_probe;
    indirect_args.commands[0] = (count + 63u) / 64u;
    indirect_args.commands[1] = 1u;
    indirect_args.commands[2] = 1u;
    indirect_args.commands[3] = (rays + 63u) / 64u;
    indirect_args.commands[4] = 1u;
    indirect_args.commands[5] = 1u;
}
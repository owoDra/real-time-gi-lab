#version 460
layout(local_size_x = 1) in;
layout(std430, set = 0, binding = 2) readonly buffer CounterBuffer { uint data[]; } counters;
layout(std430, set = 0, binding = 7) buffer IndirectBuffer { uint data[]; } indirect_args;
void main() {
    indirect_args.data[0] = (counters.data[0] + 63u) / 64u; indirect_args.data[1] = 1u; indirect_args.data[2] = 1u;
    indirect_args.data[3] = (counters.data[1] + 63u) / 64u; indirect_args.data[4] = 1u; indirect_args.data[5] = 1u;
}

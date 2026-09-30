#version 450

layout(local_size_x = 256, local_size_y = 1, local_size_z = 1) in;

layout(set = 0, binding = 0, std430) readonly buffer InputBuffer {
    uint values[];
} input_buffer;

layout(set = 0, binding = 1, std430) buffer StateBuffer {
    uint values[];
} state_buffer;

layout(push_constant) uniform PushConstants {
    uint element_count;
    uint work_iterations;
    uint reserved0;
    uint reserved1;
} pc;

void main() {
    const uint index = gl_GlobalInvocationID.x;
    if (index >= pc.element_count) {
        return;
    }

    // work_iterations is a runtime push constant. Every loop iteration changes
    // state and selects the next storage-buffer read from that state, so the
    // controlled delta cannot be replaced by a compile-time constant result.
    const uint mask = pc.element_count - 1u;
    uint value = state_buffer.values[index] ^ (index * 0x85ebca6bu);
    for (uint iteration = 0u; iteration < pc.work_iterations; ++iteration) {
        const uint source_index =
            (value ^ (iteration * 0x9e3779b9u) ^ (index * 0xc2b2ae35u)) & mask;
        const uint source = input_buffer.values[source_index];
        value ^= source + 0x9e3779b9u + (value << 6u) + (value >> 2u);
        value = value * 1664525u + 1013904223u;
    }
    state_buffer.values[index] = value;
}

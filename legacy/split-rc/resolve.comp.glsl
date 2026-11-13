#version 460
layout(local_size_x = 64) in;
layout(std430, set = 0, binding = 2) readonly buffer CounterBuffer { uint data[]; } counters;
layout(std430, set = 0, binding = 5) readonly buffer AccumBuffer { uvec2 values[]; } accum;
layout(std430, set = 0, binding = 6) buffer ResolveBuffer { float values[]; } resolved;
void main() {
    uint output_id = gl_GlobalInvocationID.x; if (output_id >= counters.data[1]) return;
    uvec2 value = accum.values[output_id];
    resolved.values[output_id] = value.y == 0u ? 0.0 : float(value.x) / (float(value.y) * 65535.0);
}

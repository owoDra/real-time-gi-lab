#version 460
layout(local_size_x = 1) in;
layout(std430, binding = 0) buffer Counters { uint data[]; } counters;
layout(std140, binding = 1) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;
void main() {
    counters.data[4] = counters.data[0];
    counters.data[5] = counters.data[1];
    counters.data[0] = min(counters.data[0], p.limits.y);
    counters.data[1] = min(counters.data[1], p.limits.z);
}

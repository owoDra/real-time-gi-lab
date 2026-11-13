#version 460
layout(local_size_x = 64) in;
struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};
layout(std430, set = 0, binding = 2) readonly buffer CounterBuffer { uint data[]; } counters;
layout(std430, set = 0, binding = 3) readonly buffer WorkBuffer { WorkItem items[]; } work;
layout(std430, set = 0, binding = 4) buffer ContributionBuffer { uvec2 values[]; } contributions;
layout(std140, set = 0, binding = 9) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;
void main() {
    uint item_id = gl_GlobalInvocationID.x; if (item_id >= counters.data[0]) return;
    WorkItem item = work.items[item_id];
    vec3 to_light = normalize(p.light_pos_interval.xyz - vec3(item.probe_px, item.probe_py, item.probe_pz));
    float alignment = max(0.0, dot(vec3(item.dir_x, item.dir_y, item.dir_z), to_light));
    float value = clamp(alignment / float(1u << item.cascade), 0.0, 1.0);
    contributions.values[item_id] = uvec2(item.output_id, uint(round(value * 65535.0)));
}

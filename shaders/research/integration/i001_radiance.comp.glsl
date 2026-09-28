#version 460
layout(local_size_x = 64) in;
struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};
struct HitData { vec4 normal_t; uvec4 metadata; };
layout(std430, binding = 0) readonly buffer Counters { uint data[]; } counters;
layout(std430, binding = 1) readonly buffer Work { WorkItem items[]; } work;
layout(std430, binding = 2) readonly buffer Hits { HitData hits[]; };
layout(std430, binding = 3) writeonly buffer Contributions { uvec2 values[]; } contributions;
layout(std140, binding = 4) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;
void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= counters.data[0]) return;
    WorkItem item = work.items[id];
    HitData hit = hits[id];
    float value = 0.0;
    if (hit.metadata.w == 1u) {
        vec3 dir = normalize(vec3(item.dir_x, item.dir_y, item.dir_z));
        vec3 origin = vec3(item.probe_px, item.probe_py, item.probe_pz) +
            dir * item.interval_min;
        vec3 point = origin + dir * hit.normal_t.w;
        vec3 to_light = p.light_pos_interval.xyz - point;
        float distance2 = max(dot(to_light, to_light), 1.0e-6);
        vec3 l = to_light * inversesqrt(distance2);
        float ndotl = max(0.0, dot(normalize(hit.normal_t.xyz), l));
        float scale = max(p.light_pos_interval.w, 1.0e-4);
        float attenuation = 1.0 / (1.0 + distance2 / (scale * scale * 256.0));
        value = clamp(
            ndotl * attenuation / float(1u << item.cascade),
            0.0,
            1.0);
    }
    contributions.values[id] =
        uvec2(item.output_id, uint(round(value * 65535.0)));
}

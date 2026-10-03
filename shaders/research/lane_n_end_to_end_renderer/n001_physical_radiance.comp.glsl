#version 460
layout(local_size_x = 64) in;

const float PI = 3.14159265358979323846;

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

float point_light_lambert(vec3 position, vec3 geometric_normal, vec3 incoming_direction) {
    vec3 normal = normalize(geometric_normal);
    if (dot(normal, -incoming_direction) < 0.0) normal = -normal;
    vec3 to_light = p.light_pos_interval.xyz - position;
    float distance2 = dot(to_light, to_light);
    if (distance2 <= 1.0e-12) return 0.0;
    vec3 light_direction = to_light * inversesqrt(distance2);
    float cosine = max(0.0, dot(normal, light_direction));
    float scale = max(p.light_pos_interval.w, 1.0e-6);
    float attenuation = (scale * scale) / (scale * scale + distance2);
    return cosine * attenuation / PI;
}

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= counters.data[0]) return;
    WorkItem item = work.items[id];
    HitData hit = hits[id];
    float value = 0.0;
    if (hit.metadata.w == 1u && !isnan(hit.normal_t.w) && !isinf(hit.normal_t.w)) {
        vec3 direction = normalize(vec3(item.dir_x, item.dir_y, item.dir_z));
        vec3 probe = vec3(item.probe_px, item.probe_py, item.probe_pz);
        vec3 position = probe + direction * (item.interval_min + hit.normal_t.w);
        value = point_light_lambert(position, hit.normal_t.xyz, direction);
    }
    uint fixed_value = uint(round(clamp(value, 0.0, 1.0) * 65535.0));
    contributions.values[id] = uvec2(item.output_id, fixed_value);
}

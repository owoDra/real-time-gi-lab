#version 460
layout(local_size_x = 64) in;
struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};
struct RayData { vec4 origin_tmax; vec4 direction_pad; };
layout(std430, binding = 0) readonly buffer Counters { uint data[]; } counters;
layout(std430, binding = 1) readonly buffer Work { WorkItem items[]; } work;
layout(std430, binding = 2) writeonly buffer Rays { RayData rays[]; };
void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= counters.data[0]) return;
    WorkItem item = work.items[id];
    vec3 raw = vec3(item.dir_x, item.dir_y, item.dir_z);
    float len = length(raw);
    RayData ray;
    ray.origin_tmax = vec4(0.0);
    ray.direction_pad = vec4(0.0);
    if (len > 1.0e-8 &&
        item.interval_min >= 0.0 &&
        item.interval_max > item.interval_min) {
        vec3 dir = raw / len;
        vec3 probe = vec3(item.probe_px, item.probe_py, item.probe_pz);
        ray.origin_tmax = vec4(
            probe + dir * item.interval_min,
            item.interval_max - item.interval_min);
        ray.direction_pad = vec4(dir, 0.0);
    }
    rays[id] = ray;
}

#version 460
// P1g: copy exact existing 8-ray input block into a compact canonical stream.
layout(local_size_x = 64) in;
struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};
layout(std430, binding = 0) readonly buffer Stats { uint data[]; } stats;
layout(std430, binding = 1) readonly buffer Reps { uint indices[]; } reps;
layout(std430, binding = 2) readonly buffer Original { WorkItem items[]; } original;
layout(std430, binding = 3) buffer Compact { WorkItem items[]; } compact;
layout(push_constant) uniform Push { uint capacity; uint rays_per_probe; } pc;
void main() {
    uint canonical = gl_GlobalInvocationID.x;
    if (canonical >= stats.data[0] || canonical >= pc.capacity) return;
    uint old_base = reps.indices[canonical] * pc.rays_per_probe;
    uint new_base = canonical * pc.rays_per_probe;
    for (uint ray = 0u; ray < pc.rays_per_probe; ++ray) {
        WorkItem item = original.items[old_base + ray];
        item.output_id = canonical;
        compact.items[new_base + ray] = item;
    }
}
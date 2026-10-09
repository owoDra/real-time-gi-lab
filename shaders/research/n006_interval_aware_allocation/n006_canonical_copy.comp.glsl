#version 460
// P1g: GPU indirect copyback, after compaction; no source/target data races.
layout(local_size_x = 64) in;
struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};
layout(std430, binding = 0) readonly buffer Stats { uint data[]; } stats;
layout(std430, binding = 1) readonly buffer Compact { WorkItem items[]; } compact;
layout(std430, binding = 2) buffer Work { WorkItem items[]; } work;
layout(push_constant) uniform Push { uint capacity; uint rays_per_probe; } pc;
void main() {
    uint index = gl_GlobalInvocationID.x;
    if (index >= min(stats.data[0], pc.capacity) * pc.rays_per_probe) return;
    work.items[index] = compact.items[index];
}
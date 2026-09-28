#version 460
layout(local_size_x = 64) in;

struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};

layout(std430, set = 0, binding = 0) readonly buffer SurfaceBuffer {
    vec4 positions[];
} surfaces;
layout(std430, set = 0, binding = 2) buffer CounterBuffer {
    uint data[];
} counters;
layout(std430, set = 0, binding = 3) buffer WorkBuffer {
    WorkItem items[];
} work;
layout(std430, set = 0, binding = 8) readonly buffer TileOwnerBuffer {
    uint surface_ids[];
} owners;
layout(std140, set = 0, binding = 9) uniform Params {
    vec4 camera_pos_near;
    vec4 camera_right_tan_x;
    vec4 camera_up_tan_y;
    vec4 camera_forward_far;
    vec4 scene_origin_spacing;
    vec4 light_pos_interval;
    uvec4 counts;
    uvec4 limits;
} p;

vec3 ray_direction(uint ray) {
    const float v = 0.5773502691896258;
    return vec3(
        (ray & 1u) != 0u ? v : -v,
        (ray & 2u) != 0u ? v : -v,
        (ray & 4u) != 0u ? v : -v);
}

void main() {
    uint tile_id = gl_GlobalInvocationID.x;
    uint tile_count = p.counts.y * p.counts.z;
    if (tile_id >= tile_count) {
        return;
    }

    uint surface_id = owners.surface_ids[tile_id];
    if (surface_id == 0xffffffffu) {
        return;
    }

    vec3 position = surfaces.positions[surface_id].xyz;

    uint output_base = atomicAdd(counters.data[1], p.counts.w);
    uint block_count = p.counts.w * p.limits.x;
    uint work_base = atomicAdd(counters.data[0], block_count);
    atomicAdd(counters.data[3], 1u);

    if (output_base + p.counts.w > p.limits.z ||
        work_base + block_count > p.limits.y) {
        atomicExchange(counters.data[2], 1u);
        return;
    }

    for (uint cascade = 0u; cascade < p.counts.w; ++cascade) {
        float spacing = p.scene_origin_spacing.w * float(1u << cascade);
        ivec3 probe = ivec3(
            floor((position - p.scene_origin_spacing.xyz) / spacing));
        vec3 probe_position =
            p.scene_origin_spacing.xyz +
            (vec3(probe) + vec3(0.5)) * spacing;

        float interval_max =
            p.light_pos_interval.w * float(1u << cascade);
        float interval_min =
            cascade > 0u
                ? p.light_pos_interval.w * float(1u << (cascade - 1u))
                : 0.0;

        uint output_id = output_base + cascade;
        for (uint ray = 0u; ray < p.limits.x; ++ray) {
            uint item_id =
                work_base + cascade * p.limits.x + ray;
            vec3 direction = ray_direction(ray);

            WorkItem item;
            item.probe_x = probe.x;
            item.probe_y = probe.y;
            item.probe_z = probe.z;
            item.cascade = cascade;
            item.ray_index = ray;
            item.output_id = output_id;
            item.surface_id = surface_id;
            item.tile_id = tile_id;
            item.interval_min = interval_min;
            item.interval_max = interval_max;
            item.dir_x = direction.x;
            item.dir_y = direction.y;
            item.dir_z = direction.z;
            item.probe_px = probe_position.x;
            item.probe_py = probe_position.y;
            item.probe_pz = probe_position.z;
            work.items[item_id] = item;
        }
    }
}

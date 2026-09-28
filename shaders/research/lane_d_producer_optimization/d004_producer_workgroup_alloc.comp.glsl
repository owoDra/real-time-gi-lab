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
layout(std430, set = 0, binding = 1) readonly buffer TileDepthBuffer {
    uint depth_bits[];
} tiles;
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

shared uint scan_values[64];
shared uint group_output_base;
shared uint group_work_base;
shared uint group_overflow;

bool project_surface(vec3 position, out uint tile_id, out float depth) {
    vec3 rel = position - p.camera_pos_near.xyz;
    depth = dot(rel, p.camera_forward_far.xyz);
    if (depth < p.camera_pos_near.w || depth > p.camera_forward_far.w) {
        return false;
    }

    float nx =
        dot(rel, p.camera_right_tan_x.xyz) /
        (depth * p.camera_right_tan_x.w);
    float ny =
        dot(rel, p.camera_up_tan_y.xyz) /
        (depth * p.camera_up_tan_y.w);
    if (abs(nx) > 1.0 || abs(ny) > 1.0) {
        return false;
    }

    uint x = min(
        p.counts.y - 1u,
        uint(max(0.0, (nx * 0.5 + 0.5) * float(p.counts.y))));
    uint y = min(
        p.counts.z - 1u,
        uint(max(0.0, (ny * 0.5 + 0.5) * float(p.counts.z))));
    tile_id = y * p.counts.y + x;
    return true;
}

vec3 ray_direction(uint ray) {
    const float v = 0.5773502691896258;
    return vec3(
        (ray & 1u) != 0u ? v : -v,
        (ray & 2u) != 0u ? v : -v,
        (ray & 4u) != 0u ? v : -v);
}

void main() {
    uint local_id = gl_LocalInvocationID.x;
    uint surface_id = gl_GlobalInvocationID.x;

    vec3 position = vec3(0.0);
    uint tile_id = 0u;
    float depth = 0.0;
    bool visible = false;

    if (surface_id < p.counts.x) {
        position = surfaces.positions[surface_id].xyz;
        if (project_surface(position, tile_id, depth)) {
            visible =
                floatBitsToUint(depth) == tiles.depth_bits[tile_id] &&
                owners.surface_ids[tile_id] == surface_id;
        }
    }

    scan_values[local_id] = visible ? 1u : 0u;
    barrier();

    for (uint offset = 1u; offset < 64u; offset <<= 1u) {
        uint addend =
            local_id >= offset
                ? scan_values[local_id - offset]
                : 0u;
        barrier();
        scan_values[local_id] += addend;
        barrier();
    }

    uint visible_count = scan_values[63];
    uint local_prefix =
        visible ? scan_values[local_id] - 1u : 0u;

    if (local_id == 0u) {
        group_output_base = 0u;
        group_work_base = 0u;
        group_overflow = 0u;

        if (visible_count > 0u) {
            uint block_count = p.counts.w * p.limits.x;
            uint output_count = visible_count * p.counts.w;
            uint work_count = visible_count * block_count;

            group_output_base =
                atomicAdd(counters.data[1], output_count);
            group_work_base =
                atomicAdd(counters.data[0], work_count);
            atomicAdd(counters.data[3], visible_count);

            if (group_output_base + output_count > p.limits.z ||
                group_work_base + work_count > p.limits.y) {
                atomicExchange(counters.data[2], 1u);
                group_overflow = 1u;
            }
        }
    }
    barrier();

    if (!visible || group_overflow != 0u) {
        return;
    }

    uint block_count = p.counts.w * p.limits.x;
    uint output_base =
        group_output_base + local_prefix * p.counts.w;
    uint work_base =
        group_work_base + local_prefix * block_count;

    for (uint cascade = 0u; cascade < p.counts.w; ++cascade) {
        float spacing =
            p.scene_origin_spacing.w * float(1u << cascade);
        ivec3 probe = ivec3(
            floor(
                (position - p.scene_origin_spacing.xyz) /
                spacing));
        vec3 probe_position =
            p.scene_origin_spacing.xyz +
            (vec3(probe) + vec3(0.5)) * spacing;

        float interval_max =
            p.light_pos_interval.w * float(1u << cascade);
        float interval_min =
            cascade > 0u
                ? p.light_pos_interval.w *
                    float(1u << (cascade - 1u))
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

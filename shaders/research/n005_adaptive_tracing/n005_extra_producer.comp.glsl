#version 460
layout(local_size_x = 128) in;

struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};

layout(std430, binding = 0) readonly buffer DepthBuffer { uint depth_bits[]; } depth_buffer;
layout(std430, binding = 1) readonly buffer OwnerBuffer { uint owner_ids[]; } owner_buffer;
layout(std430, binding = 2) buffer CounterBuffer { uint data[]; } counters;
layout(std430, binding = 3) buffer WorkBuffer { WorkItem items[]; } work;
layout(std430, binding = 4) buffer N005Stats { uint data[]; } stats;
layout(std140, binding = 5) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;

layout(push_constant) uniform Push {
    uint mode;
    uint owner_budget;
    uint extra_rays_per_probe;
    float depth_threshold;
} pc;

const uint MODE_CURRENT = 0u;
const uint MODE_UNIFORM = 1u;
const uint MODE_ADAPTIVE = 2u;
const uint INVALID_OWNER = 0xffffffffu;
const uint LOCAL_SIZE = 128u;
const float PI = 3.14159265358979323846;

shared uint scan_values[128];
shared uint base_work_shared;
shared uint base_owner_count_shared;
shared uint block_count_shared;
shared uint total_eligible_shared;
shared uint selected_target_shared;
shared uint extra_per_owner_shared;
shared uint running_eligible_shared;
shared uint capacity_ok_shared;

bool valid_depth(uint tile) {
    if (owner_buffer.owner_ids[tile] == INVALID_OWNER) return false;
    float value = uintBitsToFloat(depth_buffer.depth_bits[tile]);
    return !isnan(value) && !isinf(value) && value > 0.0;
}

float relative_delta(float a, float b) {
    return abs(a - b) / max(max(abs(a), abs(b)), 1.0e-6);
}

float depth_discontinuity(uint tile) {
    uint width = p.counts.y;
    uint height = p.counts.z;
    uint x = tile % width;
    uint y = tile / width;
    float center = uintBitsToFloat(depth_buffer.depth_bits[tile]);
    float score = 0.0;

    if (x > 0u && valid_depth(tile - 1u)) {
        score = max(score, relative_delta(center, uintBitsToFloat(depth_buffer.depth_bits[tile - 1u])));
    }
    if (x + 1u < width && valid_depth(tile + 1u)) {
        score = max(score, relative_delta(center, uintBitsToFloat(depth_buffer.depth_bits[tile + 1u])));
    }
    if (y > 0u && valid_depth(tile - width)) {
        score = max(score, relative_delta(center, uintBitsToFloat(depth_buffer.depth_bits[tile - width])));
    }
    if (y + 1u < height && valid_depth(tile + width)) {
        score = max(score, relative_delta(center, uintBitsToFloat(depth_buffer.depth_bits[tile + width])));
    }
    return score;
}

uint mix32(uint x) {
    x ^= x >> 16u;
    x *= 0x7feb352du;
    x ^= x >> 15u;
    x *= 0x846ca68bu;
    x ^= x >> 16u;
    return x;
}

vec3 extra_direction(WorkItem item, uint ordinal) {
    uint h0 = mix32(uint(item.probe_x) * 0x9e3779b9u ^
                    uint(item.probe_y) * 0x85ebca6bu ^
                    uint(item.probe_z) * 0xc2b2ae35u ^
                    item.cascade * 0x27d4eb2du ^
                    ordinal * 0x165667b1u);
    uint h1 = mix32(h0 ^ 0xa511e9b3u);
    float u = (float(h0) + 0.5) / 4294967296.0;
    float v = (float(h1) + 0.5) / 4294967296.0;
    float z = 1.0 - 2.0 * u;
    float r = sqrt(max(0.0, 1.0 - z * z));
    float phi = 2.0 * PI * v;
    return vec3(r * cos(phi), r * sin(phi), z);
}

bool owner_is_eligible(uint owner_index, uint block_count) {
    WorkItem first = work.items[owner_index * block_count];
    if (!valid_depth(first.tile_id)) return false;
    if (pc.mode == MODE_UNIFORM) return true;
    if (pc.mode == MODE_ADAPTIVE) {
        return depth_discontinuity(first.tile_id) >= pc.depth_threshold;
    }
    return false;
}

void main() {
    if (gl_WorkGroupID.x != 0u) return;

    uint lane = gl_LocalInvocationID.x;
    if (lane == 0u) {
        uint base_work = counters.data[0];
        uint block_count = p.counts.w * p.limits.x;
        base_work_shared = base_work;
        block_count_shared = block_count;
        base_owner_count_shared = block_count == 0u ? 0u : base_work / block_count;
        total_eligible_shared = 0u;
        selected_target_shared = 0u;
        extra_per_owner_shared = 0u;
        running_eligible_shared = 0u;
        capacity_ok_shared = 1u;
        stats.data[0] = base_work;
        stats.data[1] = 0u;
        stats.data[2] = 0u;
        stats.data[3] = 0u;
    }
    barrier();

    if (pc.mode == MODE_CURRENT || pc.owner_budget == 0u ||
        block_count_shared == 0u || base_owner_count_shared == 0u) {
        return;
    }

    // Pass 1: count eligible owners in parallel. This preserves the exact
    // eligibility predicate from the frozen serial P2 implementation.
    uint local_eligible = 0u;
    for (uint owner_index = lane;
         owner_index < base_owner_count_shared;
         owner_index += LOCAL_SIZE) {
        if (owner_is_eligible(owner_index, block_count_shared)) {
            ++local_eligible;
        }
    }
    atomicAdd(total_eligible_shared, local_eligible);
    barrier();

    if (lane == 0u) {
        uint eligible = total_eligible_shared;
        uint selected_target = min(pc.owner_budget, eligible);
        uint extra_per_owner = p.counts.w * pc.extra_rays_per_probe;
        uint required = selected_target * extra_per_owner;
        selected_target_shared = selected_target;
        extra_per_owner_shared = extra_per_owner;
        stats.data[1] = eligible;
        if (base_work_shared + required > p.limits.y) {
            counters.data[2] = 1u;
            capacity_ok_shared = 0u;
        }
    }
    barrier();

    if (capacity_ok_shared == 0u || selected_target_shared == 0u) {
        return;
    }

    // Pass 2: scan eligibility in owner-order chunks. The exclusive eligible
    // rank reproduces the frozen serial rank exactly. The selected output slot
    // is derived from that rank, so parallel lanes never contend for a slot.
    for (uint chunk_start = 0u;
         chunk_start < base_owner_count_shared;
         chunk_start += LOCAL_SIZE) {
        uint owner_index = chunk_start + lane;
        bool eligible_flag = owner_index < base_owner_count_shared &&
            owner_is_eligible(owner_index, block_count_shared);
        uint flag = eligible_flag ? 1u : 0u;
        scan_values[lane] = flag;
        barrier();

        for (uint offset = 1u; offset < LOCAL_SIZE; offset <<= 1u) {
            uint add = lane >= offset ? scan_values[lane - offset] : 0u;
            barrier();
            scan_values[lane] += add;
            barrier();
        }

        if (eligible_flag) {
            uint eligible_rank =
                running_eligible_shared + scan_values[lane] - 1u;
            uint before =
                (eligible_rank * selected_target_shared) /
                total_eligible_shared;
            uint after =
                ((eligible_rank + 1u) * selected_target_shared) /
                total_eligible_shared;
            if (after != before) {
                uint selected_ordinal = after - 1u;
                uint owner_base = owner_index * block_count_shared;
                uint append_base =
                    base_work_shared +
                    selected_ordinal * extra_per_owner_shared;
                for (uint cascade = 0u; cascade < p.counts.w; ++cascade) {
                    WorkItem source =
                        work.items[owner_base + cascade * p.limits.x];
                    for (uint extra = 0u;
                         extra < pc.extra_rays_per_probe;
                         ++extra) {
                        WorkItem item = source;
                        item.ray_index = p.limits.x + extra;
                        vec3 direction = extra_direction(item, extra);
                        item.dir_x = direction.x;
                        item.dir_y = direction.y;
                        item.dir_z = direction.z;
                        uint local =
                            cascade * pc.extra_rays_per_probe + extra;
                        work.items[append_base + local] = item;
                    }
                }
            }
        }

        barrier();
        if (lane == 0u) {
            running_eligible_shared += scan_values[LOCAL_SIZE - 1u];
        }
        barrier();
    }

    if (lane == 0u) {
        uint extra_work = selected_target_shared * extra_per_owner_shared;
        stats.data[2] = selected_target_shared;
        stats.data[3] = extra_work;
        counters.data[0] = base_work_shared + extra_work;
    }
}

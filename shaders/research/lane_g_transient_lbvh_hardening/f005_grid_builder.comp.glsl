#version 460
#extension GL_KHR_shader_subgroup_basic : require
#extension GL_KHR_shader_subgroup_ballot : require

layout(local_size_x = 256) in;

struct GpuTriangle {
    vec4 v0;
    vec4 v1;
    vec4 v2;
    uvec4 metadata;
};

layout(std430, binding = 0) readonly buffer TemplateTriangles { GpuTriangle template_triangles[]; };
layout(std430, binding = 1) buffer WorkingTriangles { GpuTriangle triangles[]; };
layout(std430, binding = 2) buffer AabbMin { vec4 aabb_min[]; };
layout(std430, binding = 3) buffer AabbMax { vec4 aabb_max[]; };
layout(std430, binding = 4) buffer OverlapCounts { uint overlap_counts[]; };
layout(std430, binding = 5) buffer Offsets { uint offsets[]; };
layout(std430, binding = 6) buffer PairsA { uvec4 pairs_a[]; };
layout(std430, binding = 7) buffer PairsB { uvec4 pairs_b[]; };
layout(std430, binding = 8) buffer BlockHistogram { uint block_histogram[]; };
layout(std430, binding = 9) buffer BlockOffsets { uint block_offsets[]; };
layout(std430, binding = 10) buffer DigitBase { uint digit_base[]; };
layout(std430, binding = 11) buffer CellRanges { uvec4 cell_ranges[]; };
layout(std430, binding = 12) buffer MacroRanges { uvec4 macro_ranges[]; };
layout(std430, binding = 13) buffer Counters { uint counters[]; };
layout(std430, binding = 14) buffer IndirectArgs { uint indirect_args[]; };
layout(std430, binding = 15) buffer Stats { uint stats[]; };

layout(push_constant) uniform Push {
    uint mode;
    uint count;
    uint pair_capacity;
    uint pass_index;
    vec4 origin_page_extent;
    vec4 input_delta;
    uvec4 grid_params;
} pc;

const uint MODE_INPUT = 0u;
const uint MODE_OVERLAP = 1u;
const uint MODE_SCAN = 2u;
const uint MODE_EMIT = 3u;
const uint MODE_HISTOGRAM = 4u;
const uint MODE_RADIX_PREFIX = 5u;
const uint MODE_SCATTER = 6u;
const uint MODE_RANGES = 7u;
const uint MACRO_LIMIT = 1024u;

shared uint histogram_shared[16];
shared uint subgroup_counts[64 * 16];

uint expand10(uint v) {
    v &= 0x000003ffu;
    v = (v | (v << 16u)) & 0x030000ffu;
    v = (v | (v << 8u)) & 0x0300f00fu;
    v = (v | (v << 4u)) & 0x030c30c3u;
    v = (v | (v << 2u)) & 0x09249249u;
    return v;
}

uint morton3d10(uvec3 v) {
    return expand10(v.x) |
        (expand10(v.y) << 1u) |
        (expand10(v.z) << 2u);
}

float cell_extent() {
    return pc.origin_page_extent.w / float(pc.grid_params.x);
}

bool cell_range_for(
    vec3 lo,
    vec3 hi,
    out ivec3 cell_lo,
    out ivec3 cell_hi) {
    float extent = cell_extent();
    vec3 relative_lo =
        (lo - pc.origin_page_extent.xyz) / extent;
    vec3 relative_hi =
        (hi - pc.origin_page_extent.xyz) / extent;
    cell_lo = ivec3(floor(relative_lo));
    cell_hi = ivec3(floor(relative_hi));

    int global_limit =
        int(MACRO_LIMIT * pc.grid_params.x);
    bool valid =
        all(greaterThanEqual(cell_lo, ivec3(0))) &&
        all(lessThan(cell_hi, ivec3(global_limit)));
    if (!valid) {
        atomicOr(counters[3], 1u);
        atomicOr(stats[8], 1u);
        cell_lo = clamp(
            cell_lo, ivec3(0), ivec3(global_limit - 1));
        cell_hi = clamp(
            cell_hi, ivec3(0), ivec3(global_limit - 1));
    }
    return valid;
}

uvec4 make_pair(
    ivec3 global_cell,
    uint primitive) {
    int local_count = int(pc.grid_params.x);
    ivec3 macro_i = global_cell / local_count;
    ivec3 local_i = global_cell -
        macro_i * local_count;
    return uvec4(
        morton3d10(uvec3(macro_i)),
        morton3d10(uvec3(local_i)),
        primitive,
        0u);
}

uvec4 read_pair(uint index) {
    return (pc.pass_index & 1u) == 0u
        ? pairs_a[index]
        : pairs_b[index];
}

void write_pair(uint index, uvec4 value) {
    if ((pc.pass_index & 1u) == 0u) {
        pairs_b[index] = value;
    } else {
        pairs_a[index] = value;
    }
}

uint pair_digit(uvec4 pair) {
    if (pc.pass_index < 3u) {
        return (pair.y >> (pc.pass_index * 4u)) & 15u;
    }
    uint shift = (pc.pass_index - 3u) * 4u;
    return (pair.x >> shift) & 15u;
}

void main() {
    uint id = gl_GlobalInvocationID.x;

    if (pc.mode == MODE_INPUT) {
        if (id >= pc.count) return;
        GpuTriangle triangle = template_triangles[id];
        triangle.v0.xyz += pc.input_delta.xyz;
        triangle.v1.xyz += pc.input_delta.xyz;
        triangle.v2.xyz += pc.input_delta.xyz;
        triangles[id] = triangle;
        return;
    }

    if (pc.mode == MODE_OVERLAP) {
        if (id >= pc.count) return;
        GpuTriangle triangle = triangles[id];
        vec3 lo = min(
            triangle.v0.xyz,
            min(triangle.v1.xyz, triangle.v2.xyz));
        vec3 hi = max(
            triangle.v0.xyz,
            max(triangle.v1.xyz, triangle.v2.xyz));
        aabb_min[id] = vec4(lo, 0.0);
        aabb_max[id] = vec4(hi, 0.0);

        ivec3 cell_lo;
        ivec3 cell_hi;
        cell_range_for(lo, hi, cell_lo, cell_hi);
        uvec3 span = uvec3(cell_hi - cell_lo + ivec3(1));
        uint references = span.x * span.y * span.z;
        overlap_counts[id] = references;
        atomicMax(stats[1], references);

        int local_count = int(pc.grid_params.x);
        ivec3 macro_lo = cell_lo / local_count;
        ivec3 macro_hi = cell_hi / local_count;
        atomicMin(counters[4], uint(macro_lo.x));
        atomicMin(counters[5], uint(macro_lo.y));
        atomicMin(counters[6], uint(macro_lo.z));
        atomicMax(counters[7], uint(macro_hi.x));
        atomicMax(counters[8], uint(macro_hi.y));
        atomicMax(counters[9], uint(macro_hi.z));
        return;
    }

    if (pc.mode == MODE_SCAN) {
        if (id != 0u) return;
        uint running = 0u;
        for (uint primitive = 0u;
             primitive < pc.count;
             ++primitive) {
            offsets[primitive] = running;
            uint references = overlap_counts[primitive];
            if (references > pc.pair_capacity - min(running, pc.pair_capacity)) {
                counters[3] = 1u;
                stats[8] = 1u;
                running = pc.pair_capacity;
            } else {
                running += references;
            }
        }
        counters[0] = min(running, pc.pair_capacity);
        stats[0] = counters[0];
        indirect_args[0] =
            (counters[0] + 255u) / 256u;
        indirect_args[1] = 1u;
        indirect_args[2] = 1u;
        return;
    }

    if (pc.mode == MODE_EMIT) {
        if (id >= pc.count) return;
        ivec3 cell_lo;
        ivec3 cell_hi;
        cell_range_for(
            aabb_min[id].xyz,
            aabb_max[id].xyz,
            cell_lo,
            cell_hi);
        uint cursor = offsets[id];
        for (int z = cell_lo.z; z <= cell_hi.z; ++z) {
            for (int y = cell_lo.y; y <= cell_hi.y; ++y) {
                for (int x = cell_lo.x; x <= cell_hi.x; ++x) {
                    if (cursor >= pc.pair_capacity) {
                        atomicOr(counters[3], 1u);
                        atomicOr(stats[8], 1u);
                        return;
                    }
                    pairs_a[cursor++] =
                        make_pair(ivec3(x, y, z), id);
                }
            }
        }
        return;
    }

    if (pc.mode == MODE_HISTOGRAM) {
        if (gl_LocalInvocationID.x < 16u) {
            histogram_shared[gl_LocalInvocationID.x] = 0u;
        }
        barrier();

        uint pair_count = counters[0];
        if (id < pair_count) {
            atomicAdd(
                histogram_shared[pair_digit(read_pair(id))],
                1u);
        }
        barrier();

        if (gl_LocalInvocationID.x < 16u) {
            uint block = gl_WorkGroupID.x;
            block_histogram[
                block * 16u + gl_LocalInvocationID.x] =
                histogram_shared[gl_LocalInvocationID.x];
        }
        return;
    }

    if (pc.mode == MODE_RADIX_PREFIX) {
        uint lane = gl_LocalInvocationID.x;
        uint pair_count = counters[0];
        uint blocks = (pair_count + 255u) / 256u;
        if (lane < 16u) {
            uint running = 0u;
            for (uint block = 0u; block < blocks; ++block) {
                uint index = block * 16u + lane;
                uint value = block_histogram[index];
                block_offsets[index] = running;
                running += value;
            }
            histogram_shared[lane] = running;
        }
        barrier();
        if (lane < 16u) {
            uint base = 0u;
            for (uint digit = 0u; digit < lane; ++digit) {
                base += histogram_shared[digit];
            }
            digit_base[lane] = base;
        }
        return;
    }

    if (pc.mode == MODE_SCATTER) {
        uint pair_count = counters[0];
        bool is_active = id < pair_count;
        uvec4 pair = uvec4(0u);
        uint digit = 0u;
        if (is_active) {
            pair = read_pair(id);
            digit = pair_digit(pair);
        }

        uint rank_in_subgroup = 0u;
        for (uint d = 0u; d < 16u; ++d) {
            uvec4 mask =
                subgroupBallot(is_active && digit == d);
            if (subgroupElect()) {
                subgroup_counts[
                    gl_SubgroupID * 16u + d] =
                    subgroupBallotBitCount(mask);
            }
            if (is_active && digit == d) {
                rank_in_subgroup =
                    subgroupBallotExclusiveBitCount(mask);
            }
        }
        barrier();

        if (is_active) {
            uint local_rank = rank_in_subgroup;
            for (uint subgroup = 0u;
                 subgroup < gl_SubgroupID;
                 ++subgroup) {
                local_rank += subgroup_counts[
                    subgroup * 16u + digit];
            }
            uint block = gl_WorkGroupID.x;
            uint target =
                digit_base[digit] +
                block_offsets[block * 16u + digit] +
                local_rank;
            write_pair(target, pair);
        }
        return;
    }

    if (pc.mode == MODE_RANGES) {
        if (id != 0u) return;
        uint pair_count = counters[0];
        if (pair_count == 0u) {
            counters[1] = 0u;
            counters[2] = 0u;
            stats[6] = 0u;
            stats[7] = 0u;
            return;
        }

        uint cell_count = 0u;
        uint macro_count = 0u;
        uint cell_begin = 0u;
        uint macro_cell_begin = 0u;
        uvec4 first = pairs_b[0];
        uint current_macro = first.x;
        uint current_local = first.y;

        for (uint cursor = 1u; cursor <= pair_count; ++cursor) {
            bool at_end = cursor == pair_count;
            uvec4 pair = at_end ? uvec4(0u) : pairs_b[cursor];
            bool next_cell =
                at_end ||
                pair.x != current_macro ||
                pair.y != current_local;
            if (!next_cell) continue;

            cell_ranges[cell_count] = uvec4(
                current_macro,
                current_local,
                cell_begin,
                cursor - cell_begin);
            ++cell_count;

            bool next_macro =
                at_end || pair.x != current_macro;
            if (next_macro) {
                macro_ranges[macro_count] = uvec4(
                    current_macro,
                    macro_cell_begin,
                    cell_count - macro_cell_begin,
                    0u);
                ++macro_count;
                macro_cell_begin = cell_count;
            }

            if (!at_end) {
                current_macro = pair.x;
                current_local = pair.y;
                cell_begin = cursor;
            }
        }

        counters[1] = cell_count;
        counters[2] = macro_count;
        stats[6] = cell_count;
        stats[7] = macro_count;
        return;
    }
}

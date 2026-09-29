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

struct GpuBvhNode {
    vec4 bounds_min;
    vec4 bounds_max;
    uvec4 data;
};

layout(std430, binding = 0) readonly buffer TemplateTriangles { GpuTriangle template_triangles[]; };
layout(std430, binding = 1) buffer WorkingTriangles { GpuTriangle triangles[]; };
layout(std430, binding = 2) buffer AabbMin { vec4 aabb_min[]; };
layout(std430, binding = 3) buffer AabbMax { vec4 aabb_max[]; };
layout(std430, binding = 4) buffer KeysA { uvec4 keys_a[]; };
layout(std430, binding = 5) buffer KeysB { uvec4 keys_b[]; };
layout(std430, binding = 6) buffer BlockHistogram { uint block_histogram[]; };
layout(std430, binding = 7) buffer BlockOffsets { uint block_offsets[]; };
layout(std430, binding = 8) buffer DigitBase { uint digit_base[]; };
layout(std430, binding = 9) coherent buffer Nodes { GpuBvhNode nodes[]; };
layout(std430, binding = 10) coherent buffer ReadyCounters { uint ready[]; };

layout(push_constant) uniform Push {
    uint mode;
    uint count;
    uint template_count;
    uint pass_index;
    vec4 origin_page_extent;
} pc;

const uint INVALID_ID = 0xffffffffu;
const uint MODE_INPUT = 0u;
const uint MODE_AABB = 1u;
const uint MODE_MORTON = 2u;
const uint MODE_HISTOGRAM = 3u;
const uint MODE_PREFIX = 4u;
const uint MODE_SCATTER = 5u;
const uint MODE_TOPOLOGY = 6u;
const uint MODE_BOUNDS = 7u;

shared uint histogram_shared[16];
shared uint subgroup_counts[32 * 16];

uint expand10(uint v) {
    v &= 0x000003ffu;
    v = (v | (v << 16u)) & 0x030000ffu;
    v = (v | (v << 8u)) & 0x0300f00fu;
    v = (v | (v << 4u)) & 0x030c30c3u;
    v = (v | (v << 2u)) & 0x09249249u;
    return v;
}

uint morton3d10(uvec3 v) {
    return expand10(v.x) | (expand10(v.y) << 1u) | (expand10(v.z) << 2u);
}

uvec4 read_key(uint index) {
    return (pc.pass_index & 1u) == 0u ? keys_a[index] : keys_b[index];
}

void write_key(uint index, uvec4 value) {
    if ((pc.pass_index & 1u) == 0u) {
        keys_b[index] = value;
    } else {
        keys_a[index] = value;
    }
}

uint digit_of(uvec4 key) {
    uint word = pc.pass_index < 8u ? key.y : key.x;
    uint shift = (pc.pass_index & 7u) * 4u;
    return (word >> shift) & 15u;
}

int common_prefix(int i, int j) {
    if (j < 0 || j >= int(pc.count)) return -1;
    uvec4 a = keys_a[i];
    uvec4 b = keys_a[j];
    uint x = a.x ^ b.x;
    if (x != 0u) return 31 - findMSB(x);
    x = a.y ^ b.y;
    if (x != 0u) return 32 + 31 - findMSB(x);
    x = a.z ^ b.z;
    if (x != 0u) return 64 + 31 - findMSB(x);
    return 96;
}

int find_split(int first, int last) {
    int common_bits = common_prefix(first, last);
    int split = first;
    int step = last - first;
    do {
        step = (step + 1) >> 1;
        int candidate = split + step;
        if (candidate < last && common_prefix(first, candidate) > common_bits) {
            split = candidate;
        }
    } while (step > 1);
    return split;
}

void main() {
    uint id = gl_GlobalInvocationID.x;

    if (pc.mode == MODE_INPUT) {
        if (id >= pc.count) return;
        uint source = id % pc.template_count;
        uint group = id / pc.template_count;
        uint gx = group & 31u;
        uint gy = (group >> 5u) & 31u;
        uint gz = group >> 10u;
        float spacing = pc.origin_page_extent.w * 1.5;
        vec3 delta = vec3(gx, gy, gz) * spacing;
        GpuTriangle t = template_triangles[source];
        t.v0.xyz += delta;
        t.v1.xyz += delta;
        t.v2.xyz += delta;
        t.metadata.x = id;
        triangles[id] = t;
        return;
    }

    if (pc.mode == MODE_AABB) {
        if (id >= pc.count) return;
        GpuTriangle t = triangles[id];
        vec3 lo = min(t.v0.xyz, min(t.v1.xyz, t.v2.xyz));
        vec3 hi = max(t.v0.xyz, max(t.v1.xyz, t.v2.xyz));
        aabb_min[id] = vec4(lo, 0.0);
        aabb_max[id] = vec4(hi, 0.0);
        return;
    }

    if (pc.mode == MODE_MORTON) {
        if (id >= pc.count) return;
        vec3 centroid = 0.5 * (aabb_min[id].xyz + aabb_max[id].xyz);
        vec3 page_pos = (centroid - pc.origin_page_extent.xyz) / pc.origin_page_extent.w;
        ivec3 page_i = ivec3(floor(page_pos));
        page_i = clamp(page_i, ivec3(0), ivec3(1023));
        vec3 local = clamp(fract(page_pos), vec3(0.0), vec3(0.999999));
        uvec3 local_q = uvec3(local * 1024.0);
        keys_a[id] = uvec4(
            morton3d10(uvec3(page_i)),
            morton3d10(local_q),
            id,
            0u);
        return;
    }

    if (pc.mode == MODE_HISTOGRAM) {
        if (gl_LocalInvocationID.x < 16u) histogram_shared[gl_LocalInvocationID.x] = 0u;
        barrier();
        if (id < pc.count) {
            atomicAdd(histogram_shared[digit_of(read_key(id))], 1u);
        }
        barrier();
        if (gl_LocalInvocationID.x < 16u) {
            uint block = gl_WorkGroupID.x;
            block_histogram[block * 16u + gl_LocalInvocationID.x] =
                histogram_shared[gl_LocalInvocationID.x];
        }
        return;
    }

    if (pc.mode == MODE_PREFIX) {
        uint lane = gl_LocalInvocationID.x;
        uint blocks = (pc.count + 255u) / 256u;
        if (lane < 16u) {
            uint running = 0u;
            for (uint block = 0u; block < blocks; ++block) {
                uint index = block * 16u + lane;
                uint count = block_histogram[index];
                block_offsets[index] = running;
                running += count;
            }
            histogram_shared[lane] = running;
        }
        barrier();
        if (lane < 16u) {
            uint base = 0u;
            for (uint d = 0u; d < lane; ++d) base += histogram_shared[d];
            digit_base[lane] = base;
        }
        return;
    }

    if (pc.mode == MODE_SCATTER) {
        uint digit = 0u;
        bool active = id < pc.count;
        uvec4 key = uvec4(0u);
        if (active) {
            key = read_key(id);
            digit = digit_of(key);
        }

        uint rank_in_subgroup = 0u;
        for (uint d = 0u; d < 16u; ++d) {
            uvec4 mask = subgroupBallot(active && digit == d);
            if (subgroupElect()) {
                subgroup_counts[gl_SubgroupID * 16u + d] =
                    subgroupBallotBitCount(mask);
            }
            if (active && digit == d) {
                rank_in_subgroup = subgroupBallotExclusiveBitCount(mask);
            }
        }
        barrier();

        if (active) {
            uint local_rank = rank_in_subgroup;
            for (uint sg = 0u; sg < gl_SubgroupID; ++sg) {
                local_rank += subgroup_counts[sg * 16u + digit];
            }
            uint block = gl_WorkGroupID.x;
            uint target = digit_base[digit] +
                block_offsets[block * 16u + digit] + local_rank;
            write_key(target, key);
        }
        return;
    }

    if (pc.mode == MODE_TOPOLOGY) {
        if (pc.count <= 1u || id >= pc.count - 1u) return;
        int i = int(id);
        int right_delta = common_prefix(i, i + 1);
        int left_delta = common_prefix(i, i - 1);
        int direction = right_delta >= left_delta ? 1 : -1;
        int min_delta = common_prefix(i, i - direction);

        int max_length = 2;
        while (common_prefix(i, i + max_length * direction) > min_delta) {
            max_length <<= 1;
        }

        int length = 0;
        for (int step = max_length >> 1; step >= 1; step >>= 1) {
            if (common_prefix(i, i + (length + step) * direction) > min_delta) {
                length += step;
            }
        }

        int j = i + length * direction;
        int first = min(i, j);
        int last = max(i, j);
        int split = find_split(first, last);

        uint leaf_base = pc.count - 1u;
        uint left = split == first ? leaf_base + uint(split) : uint(split);
        uint right = split + 1 == last
            ? leaf_base + uint(split + 1)
            : uint(split + 1);

        // Do not overwrite data.z here: the parent invocation may already
        // have published this internal node's parent concurrently.
        nodes[id].data.x = left;
        nodes[id].data.y = right;
        nodes[id].data.w = INVALID_ID;
        nodes[left].data.z = id;
        nodes[right].data.z = id;
        return;
    }

    if (pc.mode == MODE_BOUNDS) {
        if (id >= pc.count) return;
        uint leaf = (pc.count - 1u) + id;
        nodes[leaf].bounds_min = aabb_min[id];
        nodes[leaf].bounds_max = aabb_max[id];
        nodes[leaf].data.x = INVALID_ID;
        nodes[leaf].data.y = INVALID_ID;
        nodes[leaf].data.w = keys_a[id].z;
        memoryBarrierBuffer();

        uint current = leaf;
        uint parent = nodes[current].data.z;
        while (parent != INVALID_ID) {
            uint old = atomicAdd(ready[parent], 1u);
            if (old == 0u) return;
            memoryBarrierBuffer();
            uint left = nodes[parent].data.x;
            uint right = nodes[parent].data.y;
            nodes[parent].bounds_min = vec4(
                min(nodes[left].bounds_min.xyz, nodes[right].bounds_min.xyz),
                0.0);
            nodes[parent].bounds_max = vec4(
                max(nodes[left].bounds_max.xyz, nodes[right].bounds_max.xyz),
                0.0);
            memoryBarrierBuffer();
            current = parent;
            parent = nodes[current].data.z;
        }
        return;
    }
}

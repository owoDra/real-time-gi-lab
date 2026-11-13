#version 460

layout(local_size_x = 64) in;

const uint INVALID_ID = 0xffffffffu;
const uint WIDE_LEAF_BIT = 0x80000000u;
const uint WIDE_COUNT_MASK = 0x70000000u;
const uint WIDE_COUNT_SHIFT = 28u;
const uint WIDE_BEGIN_MASK = 0x0fffffffu;
const float RAY_T_MIN = 1.0e-4;
const float HIT_ABS_TOL = 2.0e-4;
const float HIT_REL_TOL = 2.0e-5;

struct RayData {
    vec4 origin_tmax;
    vec4 direction_pad;
};
struct TriangleData {
    vec4 v0;
    vec4 v1;
    vec4 v2;
    uvec4 metadata;
};
struct QuantChild {
    uvec4 packed;
};
struct QuantNode {
    vec4 origin;
    vec4 scale;
    uvec4 metadata;
    QuantChild children[8];
};
struct SegmentHashEntry {
    ivec4 coord;
    uvec4 metadata;
};
struct InstanceData {
    vec4 world_min;
    vec4 world_max;
    vec4 translation;
    vec4 local_min_segment_size;
    vec4 local_max_pad;
    uvec4 hash;
};
struct HitData {
    vec4 normal_t;
    uvec4 metadata;
};

layout(std430, binding = 0) readonly buffer Rays {
    RayData rays[];
};
layout(std430, binding = 1) readonly buffer Triangles {
    TriangleData triangles[];
};
layout(std430, binding = 2) readonly buffer QuantNodes {
    QuantNode nodes[];
};
layout(std430, binding = 3) readonly buffer Ordered {
    uint ordered[];
};
layout(std430, binding = 4) readonly buffer SegmentHash {
    SegmentHashEntry segment_hash_table[];
};
layout(std430, binding = 5) readonly buffer Instances {
    InstanceData instances[];
};
layout(std430, binding = 6) writeonly buffer Hits {
    HitData hits[];
};
layout(std430, binding = 7) readonly buffer Counters {
    uint data[];
} counters;

layout(push_constant) uniform Push {
    uvec4 values; // max rays, instance count, reserved, reserved
} pc;

uint mix32(uint value) {
    value ^= value >> 16u;
    value *= 0x7feb352du;
    value ^= value >> 15u;
    value *= 0x846ca68bu;
    value ^= value >> 16u;
    return value;
}

uint hash_segment(ivec3 key) {
    uint x = mix32(uint(key.x));
    uint y = mix32(uint(key.y) ^ 0x9e3779b9u);
    uint z = mix32(uint(key.z) ^ 0x85ebca6bu);
    return mix32(x ^ (y << 1u) ^ (z << 2u));
}

uint lookup_segment(
    InstanceData instance,
    ivec3 key) {
    uint slot =
        hash_segment(key) & instance.hash.y;
    for (uint probe = 0u;
         probe < instance.hash.z;
         ++probe) {
        SegmentHashEntry entry =
            segment_hash_table[
                instance.hash.x + slot];
        if (entry.metadata.x == INVALID_ID) {
            return INVALID_ID;
        }
        if (all(equal(entry.coord.xyz, key))) {
            return entry.metadata.x;
        }
        slot =
            (slot + 1u) & instance.hash.y;
    }
    return INVALID_ID;
}

bool ray_aabb_bounds(
    vec3 origin,
    vec3 direction,
    float tmax,
    vec3 bounds_min,
    vec3 bounds_max,
    out float enter,
    out float exit) {
    enter = RAY_T_MIN;
    exit = tmax;
    for (int axis = 0; axis < 3; ++axis) {
        float o = origin[axis];
        float d = direction[axis];
        float mn = bounds_min[axis];
        float mx = bounds_max[axis];
        if (abs(d) < 1.0e-8) {
            if (o < mn || o > mx) return false;
            continue;
        }
        float a = (mn - o) / d;
        float b = (mx - o) / d;
        if (a > b) {
            float tmp = a;
            a = b;
            b = tmp;
        }
        enter = max(enter, a);
        exit = min(exit, b);
        if (enter > exit) return false;
    }
    return true;
}

void decode_child(
    vec3 node_origin,
    vec3 node_scale,
    QuantChild child,
    out vec3 bounds_min,
    out vec3 bounds_max) {
    uvec3 qmin = uvec3(
        child.packed.x & 0xffffu,
        child.packed.y & 0xffffu,
        child.packed.z & 0xffffu);
    uvec3 qmax = uvec3(
        child.packed.x >> 16u,
        child.packed.y >> 16u,
        child.packed.z >> 16u);
    bounds_min =
        node_origin +
        node_scale * vec3(qmin);
    bounds_max =
        node_origin +
        node_scale * vec3(qmax);
}

bool prefer_hit(
    float t,
    uint primitive,
    float best_t,
    uint best_primitive,
    bool has_best) {
    if (!has_best) return true;
    float tolerance =
        max(HIT_ABS_TOL, abs(best_t) * HIT_REL_TOL);
    return t < best_t - tolerance ||
        (abs(t - best_t) <= tolerance &&
         primitive < best_primitive);
}

bool intersect_triangle(
    TriangleData triangle,
    vec3 origin,
    vec3 direction,
    float ray_tmax,
    float best_t,
    out float t,
    out vec3 normal) {
    vec3 e1 = triangle.v1.xyz - triangle.v0.xyz;
    vec3 e2 = triangle.v2.xyz - triangle.v0.xyz;
    vec3 p = cross(direction, e2);
    float det = dot(e1, p);
    bool two_sided = triangle.metadata.w != 0u;
    if (two_sided ? abs(det) < 1.0e-8 : det <= 1.0e-8) {
        return false;
    }

    float inv = 1.0 / det;
    vec3 tv = origin - triangle.v0.xyz;
    float u = dot(tv, p) * inv;
    if (u < 0.0 || u > 1.0) return false;
    vec3 q = cross(tv, e1);
    float v = dot(direction, q) * inv;
    if (v < 0.0 || u + v > 1.0) return false;

    t = dot(e2, q) * inv;
    float tolerance =
        max(HIT_ABS_TOL, abs(best_t) * HIT_REL_TOL);
    if (t < RAY_T_MIN ||
        t > ray_tmax ||
        t > best_t + tolerance) {
        return false;
    }
    normal = normalize(cross(e1, e2));
    return true;
}

void trace_leaf(
    uint token,
    vec3 origin,
    vec3 direction,
    float ray_tmax,
    inout HitData output_hit,
    inout float best_t,
    inout uint best_primitive,
    inout bool has_best) {
    uint begin = token & WIDE_BEGIN_MASK;
    uint count =
        ((token & WIDE_COUNT_MASK) >>
         WIDE_COUNT_SHIFT) + 1u;
    for (uint offset = 0u;
         offset < count;
         ++offset) {
        uint primitive_index =
            ordered[begin + offset];
        TriangleData triangle =
            triangles[primitive_index];
        float candidate_t;
        vec3 candidate_normal;
        if (intersect_triangle(
                triangle,
                origin,
                direction,
                ray_tmax,
                has_best ? best_t : ray_tmax,
                candidate_t,
                candidate_normal) &&
            prefer_hit(
                candidate_t,
                triangle.metadata.x,
                best_t,
                best_primitive,
                has_best)) {
            has_best = true;
            best_t = candidate_t;
            best_primitive = triangle.metadata.x;
            output_hit.normal_t =
                vec4(candidate_normal, candidate_t);
            output_hit.metadata =
                uvec4(
                    triangle.metadata.x,
                    triangle.metadata.y,
                    triangle.metadata.z,
                    1u);
        }
    }
}

void trace_segment(
    uint root,
    vec3 origin,
    vec3 direction,
    float ray_tmax,
    inout HitData output_hit,
    inout float best_t,
    inout uint best_primitive,
    inout bool has_best) {
    uint stack_token[64];
    float stack_enter[64];
    uint stack_size = 0u;
    stack_token[stack_size] = root;
    stack_enter[stack_size] = RAY_T_MIN;
    ++stack_size;

    while (stack_size != 0u) {
        --stack_size;
        uint token = stack_token[stack_size];
        float token_enter =
            stack_enter[stack_size];

        if (has_best) {
            float tolerance =
                max(
                    HIT_ABS_TOL,
                    abs(best_t) * HIT_REL_TOL);
            if (token_enter >
                best_t + tolerance) {
                continue;
            }
        }

        if ((token & WIDE_LEAF_BIT) != 0u) {
            trace_leaf(
                token,
                origin,
                direction,
                ray_tmax,
                output_hit,
                best_t,
                best_primitive,
                has_best);
            continue;
        }

        vec3 node_origin =
            nodes[token].origin.xyz;
        vec3 node_scale =
            nodes[token].scale.xyz;
        uint axis =
            nodes[token].metadata.x;
        bool positive =
            direction[int(axis)] >= 0.0;

        for (uint ordinal = 0u;
             ordinal < 8u;
             ++ordinal) {
            uint slot =
                positive
                ? 7u - ordinal
                : ordinal;
            QuantChild child =
                nodes[token].children[slot];
            uint child_token =
                child.packed.w;
            if (child_token == INVALID_ID) {
                continue;
            }

            vec3 child_min;
            vec3 child_max;
            decode_child(
                node_origin,
                node_scale,
                child,
                child_min,
                child_max);

            float enter;
            float exit;
            if (!ray_aabb_bounds(
                    origin,
                    direction,
                    has_best ? best_t : ray_tmax,
                    child_min,
                    child_max,
                    enter,
                    exit)) {
                continue;
            }

            if (stack_size + 1u > 64u) {
                output_hit.metadata.w = 2u;
                return;
            }
            stack_token[stack_size] =
                child_token;
            stack_enter[stack_size] =
                enter;
            ++stack_size;
        }
    }
}

float next_boundary_t(
    vec3 origin,
    vec3 direction,
    ivec3 cell,
    int axis,
    int step,
    float segment_size) {
    if (step == 0) {
        return uintBitsToFloat(0x7f800000u);
    }
    float cell_axis =
        float(
            cell[axis] +
            (step > 0 ? 1 : 0));
    float boundary =
        cell_axis * segment_size;
    return
        (boundary - origin[axis]) /
        direction[axis];
}

float step_delta(
    float direction,
    float segment_size) {
    return abs(direction) < 1.0e-8
        ? uintBitsToFloat(0x7f800000u)
        : segment_size / abs(direction);
}

void trace_instance(
    InstanceData instance,
    vec3 world_origin,
    vec3 direction,
    float ray_tmax,
    inout HitData output_hit,
    inout float best_t,
    inout uint best_primitive,
    inout bool has_best) {
    float world_enter;
    float world_exit;
    if (!ray_aabb_bounds(
            world_origin,
            direction,
            has_best ? best_t : ray_tmax,
            instance.world_min.xyz,
            instance.world_max.xyz,
            world_enter,
            world_exit)) {
        return;
    }

    vec3 origin =
        world_origin -
        instance.translation.xyz;
    float segment_size =
        instance.local_min_segment_size.w;

    float enter;
    float exit;
    if (!ray_aabb_bounds(
            origin,
            direction,
            has_best ? best_t : ray_tmax,
            instance.local_min_segment_size.xyz,
            instance.local_max_pad.xyz,
            enter,
            exit)) {
        return;
    }

    enter = max(enter, RAY_T_MIN);
    exit = min(
        exit,
        has_best ? best_t : ray_tmax);
    if (enter > exit) return;

    const float boundary_bias = 1.0e-4;
    vec3 start =
        origin +
        direction *
            (enter + boundary_bias);
    ivec3 cell =
        ivec3(
            floor(start / segment_size));
    ivec3 step =
        ivec3(
            direction.x > 0.0 ? 1 :
                (direction.x < 0.0 ? -1 : 0),
            direction.y > 0.0 ? 1 :
                (direction.y < 0.0 ? -1 : 0),
            direction.z > 0.0 ? 1 :
                (direction.z < 0.0 ? -1 : 0));

    float next_x =
        next_boundary_t(
            origin,
            direction,
            cell,
            0,
            step.x,
            segment_size);
    float next_y =
        next_boundary_t(
            origin,
            direction,
            cell,
            1,
            step.y,
            segment_size);
    float next_z =
        next_boundary_t(
            origin,
            direction,
            cell,
            2,
            step.z,
            segment_size);
    float delta_x =
        step_delta(
            direction.x,
            segment_size);
    float delta_y =
        step_delta(
            direction.y,
            segment_size);
    float delta_z =
        step_delta(
            direction.z,
            segment_size);

    float cursor = enter;
    for (uint iteration = 0u;
         iteration < instance.hash.w &&
         cursor <= exit;
         ++iteration) {
        uint root =
            lookup_segment(instance, cell);
        if (root != INVALID_ID) {
            trace_segment(
                root,
                origin,
                direction,
                ray_tmax,
                output_hit,
                best_t,
                best_primitive,
                has_best);
            if (output_hit.metadata.w == 2u) {
                return;
            }
            if (has_best &&
                best_t <=
                    cursor + HIT_ABS_TOL) {
                break;
            }
        }

        float next_t =
            min(
                min(next_x, next_y),
                min(next_z, exit));
        if (has_best &&
            best_t <=
                next_t + HIT_ABS_TOL) {
            break;
        }
        if (next_t >= exit) break;

        if (next_x <= next_y &&
            next_x <= next_z) {
            cell.x += step.x;
            cursor = next_x;
            next_x += delta_x;
        } else if (next_y <= next_z) {
            cell.y += step.y;
            cursor = next_y;
            next_y += delta_y;
        } else {
            cell.z += step.z;
            cursor = next_z;
            next_z += delta_z;
        }

        if (iteration + 1u ==
            instance.hash.w) {
            output_hit.metadata.w = 3u;
        }
    }
}

void main() {
    uint ray_id =
        gl_GlobalInvocationID.x;
    if (ray_id >= counters.data[0] ||
        ray_id >= pc.values.x) {
        return;
    }

    RayData ray = rays[ray_id];
    HitData output_hit;
    output_hit.normal_t =
        vec4(
            0.0,
            0.0,
            0.0,
            uintBitsToFloat(
                0x7f800000u));
    output_hit.metadata =
        uvec4(
            INVALID_ID,
            INVALID_ID,
            INVALID_ID,
            0u);

    float direction_length =
        length(ray.direction_pad.xyz);
    if ((isnan(direction_length) ||
         isinf(direction_length)) ||
        direction_length <= 1.0e-8 ||
        (isnan(ray.origin_tmax.w) ||
         isinf(ray.origin_tmax.w)) ||
        ray.origin_tmax.w <= RAY_T_MIN) {
        hits[ray_id] = output_hit;
        return;
    }

    vec3 world_origin =
        ray.origin_tmax.xyz;
    vec3 direction =
        ray.direction_pad.xyz /
        direction_length;
    float best_t =
        ray.origin_tmax.w;
    uint best_primitive =
        INVALID_ID;
    bool has_best = false;

    for (uint instance_index = 0u;
         instance_index < pc.values.y;
         ++instance_index) {
        InstanceData instance =
            instances[instance_index];
        float segment_size =
            instance.local_min_segment_size.w;
        if ((isnan(segment_size) ||
             isinf(segment_size)) ||
            segment_size <= 0.0) {
            output_hit.metadata.w = 3u;
            break;
        }

        trace_instance(
            instance,
            world_origin,
            direction,
            ray.origin_tmax.w,
            output_hit,
            best_t,
            best_primitive,
            has_best);
        if (output_hit.metadata.w > 1u) {
            break;
        }
    }

    hits[ray_id] = output_hit;
}

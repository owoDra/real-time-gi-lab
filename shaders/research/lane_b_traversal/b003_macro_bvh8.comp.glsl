#version 460

layout(local_size_x = 64) in;

const uint INVALID_ID = 0xffffffffu;
const uint MACRO_SEGMENT = 0u;
const uint MACRO_INTERNAL = 1u;
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
struct BvhNode {
    vec4 bounds_min;
    vec4 bounds_max;
    uvec4 data;
};
struct MacroChild {
    vec4 bounds_min;
    vec4 bounds_max;
    uvec4 data;
};
struct MacroNode {
    MacroChild children[8];
};
struct HitData {
    vec4 normal_t;
    uvec4 metadata;
};

layout(std430, binding = 0) readonly buffer Rays { RayData rays[]; };
layout(std430, binding = 1) readonly buffer Triangles { TriangleData triangles[]; };
layout(std430, binding = 2) readonly buffer Nodes { BvhNode nodes[]; };
layout(std430, binding = 3) readonly buffer Ordered { uint ordered[]; };
layout(std430, binding = 4) readonly buffer MacroNodes { MacroNode macro_nodes[]; };
layout(std430, binding = 5) writeonly buffer Hits { HitData hits[]; };

layout(push_constant) uniform Push {
    uvec4 values; // ray_count, macro_root, reserved, reserved
} pc;

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

bool ray_node(
    vec3 origin,
    vec3 direction,
    float tmax,
    BvhNode node) {
    float enter;
    float exit;
    return ray_aabb_bounds(
        origin,
        direction,
        tmax,
        node.bounds_min.xyz,
        node.bounds_max.xyz,
        enter,
        exit);
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
    if (two_sided
        ? abs(det) < 1.0e-8
        : det <= 1.0e-8) {
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

void trace_segment(
    uint root,
    vec3 origin,
    vec3 direction,
    float ray_tmax,
    inout HitData output_hit,
    inout float best_t,
    inout uint best_primitive,
    inout bool has_best) {
    uint stack[128];
    uint stack_size = 0u;
    stack[stack_size++] = root;

    while (stack_size != 0u) {
        uint node_id = stack[--stack_size];
        BvhNode node = nodes[node_id];
        // The Macro BVH indexes the segment cell, while this micro node uses
        // the actual triangle bounds. The root test is therefore required:
        // cell membership is only a coarse spatial admission gate.
        if (!ray_node(
                origin,
                direction,
                has_best ? best_t : ray_tmax,
                node)) {
            continue;
        }

        if (node.data.x == INVALID_ID) {
            for (uint offset = 0u;
                 offset < node.data.w;
                 ++offset) {
                uint primitive_index =
                    ordered[node.data.z + offset];
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
                    best_primitive =
                        triangle.metadata.x;
                    output_hit.normal_t =
                        vec4(
                            candidate_normal,
                            candidate_t);
                    output_hit.metadata =
                        uvec4(
                            triangle.metadata.x,
                            triangle.metadata.y,
                            triangle.metadata.z,
                            1u);
                }
            }
        } else {
            if (stack_size + 2u > 128u) {
                output_hit.metadata.w = 2u;
                return;
            }
            stack[stack_size++] = node.data.x;
            stack[stack_size++] = node.data.y;
        }
    }
}

void main() {
    uint ray_id = gl_GlobalInvocationID.x;
    if (ray_id >= pc.values.x) return;

    RayData ray = rays[ray_id];
    HitData output_hit;
    output_hit.normal_t =
        vec4(
            0.0,
            0.0,
            0.0,
            uintBitsToFloat(0x7f800000u));
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
        ray.origin_tmax.w <= RAY_T_MIN ||
        pc.values.y == INVALID_ID) {
        hits[ray_id] = output_hit;
        return;
    }

    vec3 origin = ray.origin_tmax.xyz;
    vec3 direction =
        ray.direction_pad.xyz / direction_length;
    float best_t = ray.origin_tmax.w;
    uint best_primitive = INVALID_ID;
    bool has_best = false;

    // Bit 31 tags a Macro BVH internal node. Segment-root indices and
    // macro-node indices are both far below 2^31 in this experiment.
    const uint MACRO_STACK_INTERNAL = 0x80000000u;
    const uint MACRO_STACK_INDEX_MASK = 0x7fffffffu;

    // The CPU builder computes the worst all-children DFS frontier and the
    // harness rejects payloads that would exceed this fixed capacity.
    uint macro_stack[32];
    uint macro_stack_size = 0u;
    macro_stack[macro_stack_size++] =
        pc.values.y | MACRO_STACK_INTERNAL;

    while (macro_stack_size != 0u) {
        uint encoded =
            macro_stack[--macro_stack_size];
        bool is_internal =
            (encoded & MACRO_STACK_INTERNAL) != 0u;
        uint reference =
            encoded & MACRO_STACK_INDEX_MASK;

        if (!is_internal) {
            trace_segment(
                reference,
                origin,
                direction,
                ray.origin_tmax.w,
                output_hit,
                best_t,
                best_primitive,
                has_best);
            if (output_hit.metadata.w == 2u) {
                hits[ray_id] = output_hit;
                return;
            }
            continue;
        }

        uint axis =
            macro_nodes[reference].children[0].data.z;
        bool positive =
            direction[int(axis)] >= 0.0;

        // Children are stored low-to-high along the builder's split axis.
        // Push far-to-near so LIFO pops the approximate near child first.
        for (uint ordinal = 0u;
             ordinal < 8u;
             ++ordinal) {
            uint slot =
                positive
                ? 7u - ordinal
                : ordinal;
            MacroChild child =
                macro_nodes[reference].children[slot];
            if (child.data.x == INVALID_ID) {
                continue;
            }

            float enter;
            float exit;
            if (!ray_aabb_bounds(
                    origin,
                    direction,
                    has_best
                        ? best_t
                        : ray.origin_tmax.w,
                    child.bounds_min.xyz,
                    child.bounds_max.xyz,
                    enter,
                    exit)) {
                continue;
            }

            uint child_encoded;
            if (child.data.y == MACRO_SEGMENT) {
                child_encoded = child.data.x;
            } else if (
                child.data.y == MACRO_INTERNAL) {
                child_encoded =
                    child.data.x |
                    MACRO_STACK_INTERNAL;
            } else {
                output_hit.metadata.w = 4u;
                hits[ray_id] = output_hit;
                return;
            }

            if (macro_stack_size + 1u > 32u) {
                output_hit.metadata.w = 3u;
                hits[ray_id] = output_hit;
                return;
            }
            macro_stack[macro_stack_size++] =
                child_encoded;
        }
    }

    hits[ray_id] = output_hit;
}

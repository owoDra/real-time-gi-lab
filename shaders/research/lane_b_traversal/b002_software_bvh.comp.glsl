#version 460

layout(local_size_x = 64) in;

const uint INVALID_ID = 0xffffffffu;
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
struct HitData {
    vec4 normal_t;
    uvec4 metadata;
};

layout(std430, binding = 0) readonly buffer Rays { RayData rays[]; };
layout(std430, binding = 1) readonly buffer Triangles { TriangleData triangles[]; };
layout(std430, binding = 2) readonly buffer Nodes { BvhNode nodes[]; };
layout(std430, binding = 3) readonly buffer Ordered { uint ordered[]; };
layout(std430, binding = 4) writeonly buffer Hits { HitData hits[]; };

layout(push_constant) uniform Push {
    uint ray_count;
    uint root;
    uint reserved0;
    uint reserved1;
} pc;

bool ray_aabb(vec3 origin, vec3 direction, float tmax, BvhNode node) {
    float lo = RAY_T_MIN;
    float hi = tmax;
    for (int axis = 0; axis < 3; ++axis) {
        float o = origin[axis];
        float d = direction[axis];
        float mn = node.bounds_min[axis];
        float mx = node.bounds_max[axis];
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
        lo = max(lo, a);
        hi = min(hi, b);
        if (lo > hi) return false;
    }
    return true;
}

bool prefer_hit(float t, uint primitive, float best_t, uint best_primitive, bool has_best) {
    if (!has_best) return true;
    float tolerance = max(HIT_ABS_TOL, abs(best_t) * HIT_REL_TOL);
    return t < best_t - tolerance ||
        (abs(t - best_t) <= tolerance && primitive < best_primitive);
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
    if (two_sided ? abs(det) < 1.0e-8 : det <= 1.0e-8) return false;

    float inv = 1.0 / det;
    vec3 tv = origin - triangle.v0.xyz;
    float u = dot(tv, p) * inv;
    if (u < 0.0 || u > 1.0) return false;
    vec3 q = cross(tv, e1);
    float v = dot(direction, q) * inv;
    if (v < 0.0 || u + v > 1.0) return false;

    t = dot(e2, q) * inv;
    float tolerance = max(HIT_ABS_TOL, abs(best_t) * HIT_REL_TOL);
    if (t < RAY_T_MIN || t > ray_tmax || t > best_t + tolerance) return false;
    normal = normalize(cross(e1, e2));
    return true;
}

void main() {
    uint ray_id = gl_GlobalInvocationID.x;
    if (ray_id >= pc.ray_count) return;

    RayData ray = rays[ray_id];
    float direction_length = length(ray.direction_pad.xyz);
    HitData output_hit;
    output_hit.normal_t = vec4(0.0, 0.0, 0.0, uintBitsToFloat(0x7f800000u));
    output_hit.metadata = uvec4(INVALID_ID, INVALID_ID, INVALID_ID, 0u);

    if ((isnan(direction_length) || isinf(direction_length)) || direction_length <= 1.0e-8 ||
        (isnan(ray.origin_tmax.w) || isinf(ray.origin_tmax.w)) || ray.origin_tmax.w <= RAY_T_MIN ||
        pc.root == INVALID_ID) {
        hits[ray_id] = output_hit;
        return;
    }

    vec3 direction = ray.direction_pad.xyz / direction_length;
    vec3 origin = ray.origin_tmax.xyz;
    float best_t = ray.origin_tmax.w;
    uint best_primitive = INVALID_ID;
    bool has_best = false;

    uint stack[128];
    uint stack_size = 0u;
    stack[stack_size++] = pc.root;

    while (stack_size != 0u) {
        uint node_id = stack[--stack_size];
        BvhNode node = nodes[node_id];
        if (!ray_aabb(origin, direction, has_best ? best_t : ray.origin_tmax.w, node)) {
            continue;
        }

        if (node.data.x == INVALID_ID) {
            for (uint offset = 0u; offset < node.data.w; ++offset) {
                uint primitive_index = ordered[node.data.z + offset];
                TriangleData triangle = triangles[primitive_index];
                float candidate_t;
                vec3 candidate_normal;
                if (intersect_triangle(
                        triangle,
                        origin,
                        direction,
                        ray.origin_tmax.w,
                        has_best ? best_t : ray.origin_tmax.w,
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
                    output_hit.normal_t = vec4(candidate_normal, candidate_t);
                    output_hit.metadata = uvec4(
                        triangle.metadata.x,
                        triangle.metadata.y,
                        triangle.metadata.z,
                        1u);
                }
            }
        } else {
            if (stack_size + 2u > 128u) {
                output_hit.metadata.w = 2u;
                hits[ray_id] = output_hit;
                return;
            }
            stack[stack_size++] = node.data.x;
            stack[stack_size++] = node.data.y;
        }
    }

    hits[ray_id] = output_hit;
}

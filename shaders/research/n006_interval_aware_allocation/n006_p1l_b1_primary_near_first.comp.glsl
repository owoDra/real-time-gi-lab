#version 460

layout(local_size_x = 8, local_size_y = 8) in;

const uint INVALID_ID = 0xffffffffu;
const float RAY_T_MIN = 1.0e-4;
const float HIT_ABS_TOL = 2.0e-4;
const float HIT_REL_TOL = 2.0e-5;

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

layout(std430, binding = 0) writeonly buffer PrimaryHits { HitData hits[]; };
layout(std430, binding = 1) readonly buffer Triangles { TriangleData triangles[]; };
layout(std430, binding = 2) readonly buffer Nodes { BvhNode nodes[]; };
layout(std430, binding = 3) readonly buffer Ordered { uint ordered[]; };
layout(std140, binding = 4) uniform Params {
    vec4 camera_pos_near;
    vec4 camera_right_tan_x;
    vec4 camera_up_tan_y;
    vec4 camera_forward_far;
    vec4 scene_origin_spacing;
    vec4 light_pos_interval;
    uvec4 counts;
    uvec4 limits;
} p;

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
    vec3 q = cross(direction, e2);
    float det = dot(e1, q);
    bool two_sided = triangle.metadata.w != 0u;
    if (two_sided ? abs(det) < 1.0e-8 : det <= 1.0e-8) return false;

    float inv = 1.0 / det;
    vec3 tv = origin - triangle.v0.xyz;
    float u = dot(tv, q) * inv;
    if (u < 0.0 || u > 1.0) return false;
    vec3 r = cross(tv, e1);
    float v = dot(direction, r) * inv;
    if (v < 0.0 || u + v > 1.0) return false;

    t = dot(e2, r) * inv;
    float tolerance = max(HIT_ABS_TOL, abs(best_t) * HIT_REL_TOL);
    if (t < RAY_T_MIN || t > ray_tmax || t > best_t + tolerance) return false;
    normal = normalize(cross(e1, e2));
    return true;
}

void main() {
    uvec2 pixel = gl_GlobalInvocationID.xy;
    if (pixel.x >= p.counts.y || pixel.y >= p.counts.z) return;
    uint id = pixel.y * p.counts.y + pixel.x;

    float nx = (2.0 * (float(pixel.x) + 0.5) / float(p.counts.y)) - 1.0;
    float ny = 1.0 - (2.0 * (float(pixel.y) + 0.5) / float(p.counts.z));
    vec3 direction = normalize(
        p.camera_forward_far.xyz +
        p.camera_right_tan_x.xyz * (nx * p.camera_right_tan_x.w) +
        p.camera_up_tan_y.xyz * (ny * p.camera_up_tan_y.w));
    vec3 origin = p.camera_pos_near.xyz;
    float ray_tmax = p.camera_forward_far.w;

    HitData output_hit;
    output_hit.normal_t = vec4(0.0, 0.0, 0.0, uintBitsToFloat(0x7f800000u));
    output_hit.metadata = uvec4(INVALID_ID, INVALID_ID, INVALID_ID, 0u);

    float best_t = ray_tmax;
    uint best_primitive = INVALID_ID;
    bool has_best = false;
    uint stack[128];
    uint stack_size = 0u;
    stack[stack_size++] = 0u;

    while (stack_size != 0u) {
        uint node_id = stack[--stack_size];
        BvhNode node = nodes[node_id];
        if (!ray_aabb(origin, direction, has_best ? best_t : ray_tmax, node)) continue;

        if (node.data.x == INVALID_ID) {
            for (uint offset = 0u; offset < node.data.w; ++offset) {
                uint primitive_index = ordered[node.data.z + offset];
                TriangleData triangle = triangles[primitive_index];
                float candidate_t;
                vec3 candidate_normal;
                if (intersect_triangle(
                        triangle, origin, direction, ray_tmax,
                        has_best ? best_t : ray_tmax,
                        candidate_t, candidate_normal) &&
                    prefer_hit(candidate_t, triangle.metadata.x,
                               best_t, best_primitive, has_best)) {
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
                hits[id] = output_hit;
                return;
            }
            // P1l-B1a N006-only approximation: ray-projected center order.
            // Put estimated FAR child first so LIFO pops estimated NEAR.
            // Ties use the accepted right-first order (y before x).
            uint far_child = node.data.x;
            uint near_child = node.data.y;
            vec3 center_x = 0.5 * (nodes[node.data.x].bounds_min.xyz +
                                    nodes[node.data.x].bounds_max.xyz);
            vec3 center_y = 0.5 * (nodes[node.data.y].bounds_min.xyz +
                                    nodes[node.data.y].bounds_max.xyz);
            if (dot(center_x - origin, direction) <
                dot(center_y - origin, direction)) {
                near_child = node.data.x;
                far_child = node.data.y;
            }
            stack[stack_size++] = far_child;
            stack[stack_size++] = near_child;
        }
    }

    hits[id] = output_hit;
}

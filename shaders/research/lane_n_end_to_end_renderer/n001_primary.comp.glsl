#version 460
#extension GL_EXT_ray_query : require

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
struct HitData {
    vec4 normal_t;
    uvec4 metadata;
};

layout(std430, binding = 0) writeonly buffer PrimaryHits { HitData hits[]; };
layout(binding = 1) uniform accelerationStructureEXT top_level;
layout(std430, binding = 2) readonly buffer Triangles { TriangleData triangles[]; };
layout(std140, binding = 3) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;

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

    // N001 image memory is top-left. A001 producer tile coordinates remain
    // untouched; this renderer prerequisite is independent of producer order.
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

    rayQueryEXT query;
    rayQueryInitializeEXT(
        query, top_level, gl_RayFlagsNoOpaqueEXT, 0xffu,
        origin, RAY_T_MIN, direction, ray_tmax);

    float best_t = ray_tmax;
    uint best_primitive = INVALID_ID;
    bool has_best = false;

    while (rayQueryProceedEXT(query)) {
        if (rayQueryGetIntersectionTypeEXT(query, false) !=
            gl_RayQueryCandidateIntersectionTriangleEXT) continue;

        int candidate_index = rayQueryGetIntersectionPrimitiveIndexEXT(query, false);
        int instance_base = rayQueryGetIntersectionInstanceCustomIndexEXT(query, false);
        if (candidate_index < 0 || instance_base < 0) continue;

        TriangleData triangle = triangles[uint(instance_base) + uint(candidate_index)];
        vec3 object_origin = rayQueryGetIntersectionObjectRayOriginEXT(query, false);
        vec3 object_direction = rayQueryGetIntersectionObjectRayDirectionEXT(query, false);

        float candidate_t;
        vec3 candidate_normal;
        if (intersect_triangle(
                triangle, object_origin, object_direction, ray_tmax,
                has_best ? best_t : ray_tmax, candidate_t, candidate_normal) &&
            prefer_hit(candidate_t, triangle.metadata.x, best_t, best_primitive, has_best)) {
            has_best = true;
            best_t = candidate_t;
            best_primitive = triangle.metadata.x;
            mat4x3 object_to_world = rayQueryGetIntersectionObjectToWorldEXT(query, false);
            vec3 world_normal = normalize(object_to_world * vec4(candidate_normal, 0.0));
            output_hit.normal_t = vec4(world_normal, candidate_t);
            output_hit.metadata = uvec4(
                triangle.metadata.x, triangle.metadata.y, triangle.metadata.z, 1u);
        }
    }

    hits[id] = output_hit;
}

#version 460
#extension GL_EXT_ray_query : require

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
struct HitData {
    vec4 normal_t;
    uvec4 metadata;
};

layout(std430, binding = 0) readonly buffer Rays { RayData rays[]; };
layout(binding = 1) uniform accelerationStructureEXT top_level;
layout(std430, binding = 2) readonly buffer Triangles { TriangleData triangles[]; };
layout(std430, binding = 3) writeonly buffer Hits { HitData hits[]; };

layout(push_constant) uniform Push {
    uint ray_count;
} pc;

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

void main() {
    uint ray_id = gl_GlobalInvocationID.x;
    if (ray_id >= pc.ray_count) return;

    RayData ray = rays[ray_id];
    HitData output_hit;
    output_hit.normal_t =
        vec4(0.0, 0.0, 0.0, uintBitsToFloat(0x7f800000u));
    output_hit.metadata =
        uvec4(INVALID_ID, INVALID_ID, INVALID_ID, 0u);

    float direction_length = length(ray.direction_pad.xyz);
    if (isnan(direction_length) ||
        isinf(direction_length) ||
        direction_length <= 1.0e-8 ||
        isnan(ray.origin_tmax.w) ||
        isinf(ray.origin_tmax.w) ||
        ray.origin_tmax.w <= RAY_T_MIN) {
        hits[ray_id] = output_hit;
        return;
    }

    vec3 origin = ray.origin_tmax.xyz;
    vec3 direction =
        ray.direction_pad.xyz / direction_length;

    rayQueryEXT query;
    // Force triangles to non-opaque candidates and deliberately do not confirm
    // them. That exposes every hardware traversal candidate so Lane B can apply
    // the shared face/tie semantics itself rather than accepting API-specific
    // closest-hit behavior.
    rayQueryInitializeEXT(
        query,
        top_level,
        gl_RayFlagsNoOpaqueEXT,
        0xffu,
        origin,
        RAY_T_MIN,
        direction,
        ray.origin_tmax.w);

    float best_t = ray.origin_tmax.w;
    uint best_primitive = INVALID_ID;
    bool has_best = false;

    while (rayQueryProceedEXT(query)) {
        if (rayQueryGetIntersectionTypeEXT(query, false) !=
            gl_RayQueryCandidateIntersectionTriangleEXT) {
            continue;
        }

        int candidate_index =
            rayQueryGetIntersectionPrimitiveIndexEXT(
                query,
                false);
        int instance_base =
            rayQueryGetIntersectionInstanceCustomIndexEXT(
                query,
                false);
        if (candidate_index < 0 || instance_base < 0) continue;

        // instanceCustomIndex is the metadata base for this BLAS. The legacy
        // one-BLAS path uses base zero; Lane E E002 gives the rigid BLAS a
        // non-zero base after partitioning static and rigid metadata.
        TriangleData triangle =
            triangles[uint(instance_base) + uint(candidate_index)];

        // Candidate triangles are stored in BLAS/object space. Ray-query keeps
        // the parametric t invariant across spaces, so manual shared Hit
        // semantics must intersect against the candidate's object-space ray.
        vec3 object_origin =
            rayQueryGetIntersectionObjectRayOriginEXT(query, false);
        vec3 object_direction =
            rayQueryGetIntersectionObjectRayDirectionEXT(query, false);

        float candidate_t;
        vec3 candidate_normal;
        if (intersect_triangle(
                triangle,
                object_origin,
                object_direction,
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
            // E002 permits rigid transforms only, so transforming the local
            // geometric normal by the object-to-world linear part is exact.
            mat4x3 object_to_world =
                rayQueryGetIntersectionObjectToWorldEXT(query, false);
            vec3 world_normal =
                normalize(object_to_world * vec4(candidate_normal, 0.0));
            output_hit.normal_t =
                vec4(world_normal, candidate_t);
            output_hit.metadata = uvec4(
                triangle.metadata.x,
                triangle.metadata.y,
                triangle.metadata.z,
                1u);
        }
    }

    hits[ray_id] = output_hit;
}

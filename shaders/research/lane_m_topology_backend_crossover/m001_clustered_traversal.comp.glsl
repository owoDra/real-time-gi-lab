#version 460

layout(local_size_x = 64, local_size_y = 1, local_size_z = 1) in;

const uint INVALID_ID = 0xffffffffu;
const float RAY_T_MIN = 1.0e-4;
const float HIT_ABS_TOL = 2.0e-4;
const float HIT_REL_TOL = 2.0e-5;
const uint STACK_CAPACITY = 64u;

struct Ray {
    vec4 origin_tmax;
    vec4 direction;
};

struct Triangle {
    vec4 v0;
    vec4 v1;
    vec4 v2;
    uvec4 meta;
};

struct BvhNode {
    vec4 bounds_min;
    vec4 bounds_max;
    uvec4 meta;
};

struct Cluster {
    vec4 bounds_min;
    vec4 bounds_max;
    uvec4 meta;
};

struct Hit {
    vec4 normal_t;
    uvec4 metadata;
};

layout(std430, binding = 0) readonly buffer RayBuffer {
    Ray rays[];
};
layout(std430, binding = 1) readonly buffer TriangleBuffer {
    Triangle triangles[];
};
layout(std430, binding = 2) readonly buffer UpperBuffer {
    BvhNode upper_nodes[];
};
layout(std430, binding = 3) readonly buffer MicroBuffer {
    BvhNode micro_nodes[];
};
layout(std430, binding = 4) readonly buffer ClusterBuffer {
    Cluster clusters[];
};
layout(std430, binding = 5) writeonly buffer HitBuffer {
    Hit hits[];
};

layout(push_constant) uniform Push {
    uint ray_count;
    uint upper_root;
    uint upper_node_count;
    uint micro_node_count;
    uint cluster_count;
    uint triangle_count;
} push_data;

float hit_tolerance(float t) {
    return max(HIT_ABS_TOL, abs(t) * HIT_REL_TOL);
}

vec3 precise_cross(vec3 a, vec3 b) {
    precise float x = a.y * b.z - a.z * b.y;
    precise float y = a.z * b.x - a.x * b.z;
    precise float z = a.x * b.y - a.y * b.x;
    return vec3(x, y, z);
}

float precise_dot(vec3 a, vec3 b) {
    precise float xy = a.x * b.x + a.y * b.y;
    precise float z = a.z * b.z;
    precise float result = xy + z;
    return result;
}

bool hit_aabb(
    vec3 origin,
    vec3 direction,
    vec3 bounds_min,
    vec3 bounds_max,
    float limit) {
    float near_t = RAY_T_MIN;
    float far_t = limit;
    for (uint axis = 0u; axis < 3u; ++axis) {
        float o = origin[axis];
        float d = direction[axis];
        float lo = bounds_min[axis];
        float hi = bounds_max[axis];
        if (abs(d) <= 1.0e-20) {
            if (o < lo || o > hi) {
                return false;
            }
            continue;
        }
        float inverse = 1.0 / d;
        float a = (lo - o) * inverse;
        float b = (hi - o) * inverse;
        if (a > b) {
            float tmp = a;
            a = b;
            b = tmp;
        }
        near_t = max(near_t, a);
        far_t = min(far_t, b);
        if (near_t > far_t) {
            return false;
        }
    }
    return far_t >= RAY_T_MIN;
}

bool intersect_triangle(
    Triangle triangle,
    vec3 origin,
    vec3 direction,
    float ray_tmax,
    float best_t,
    out float distance,
    out vec3 normal) {
    precise vec3 e1 = triangle.v1.xyz - triangle.v0.xyz;
    precise vec3 e2 = triangle.v2.xyz - triangle.v0.xyz;
    precise vec3 p = precise_cross(direction, e2);
    precise float determinant = precise_dot(e1, p);
    bool two_sided = triangle.meta.w != 0u;
    if (two_sided) {
        if (abs(determinant) < 1.0e-8) {
            return false;
        }
    } else if (determinant <= 1.0e-8) {
        return false;
    }

    precise float inverse = 1.0 / determinant;
    precise vec3 tv = origin - triangle.v0.xyz;
    precise float u = precise_dot(tv, p) * inverse;
    if (u < 0.0 || u > 1.0) {
        return false;
    }
    precise vec3 q = precise_cross(tv, e1);
    precise float v = precise_dot(direction, q) * inverse;
    if (v < 0.0 || u + v > 1.0) {
        return false;
    }
    precise float exact_t = precise_dot(e2, q) * inverse;
    distance = exact_t;
    float tolerance = hit_tolerance(best_t);
    if (distance < RAY_T_MIN ||
        distance > ray_tmax ||
        distance > best_t + tolerance) {
        return false;
    }

    normal = normalize(cross(e1, e2));
    return true;
}

bool prefer_hit(
    float candidate_t,
    uint candidate_primitive,
    bool current_hit,
    float current_t,
    uint current_primitive) {
    if (!current_hit) {
        return true;
    }
    float tolerance = hit_tolerance(current_t);
    return candidate_t < current_t - tolerance ||
           (abs(candidate_t - current_t) <= tolerance &&
            candidate_primitive < current_primitive);
}

void fail_runtime(inout Hit result) {
    result.metadata = uvec4(INVALID_ID, INVALID_ID, INVALID_ID, 2u);
}

void main() {
    uint ray_index = gl_GlobalInvocationID.x;
    if (ray_index >= push_data.ray_count) {
        return;
    }

    Ray input_ray = rays[ray_index];
    vec3 origin = input_ray.origin_tmax.xyz;
    float ray_tmax = input_ray.origin_tmax.w;
    float direction_length = length(input_ray.direction.xyz);

    Hit result;
    result.normal_t = vec4(0.0, 0.0, 0.0, uintBitsToFloat(0x7f800000u));
    result.metadata = uvec4(INVALID_ID, INVALID_ID, INVALID_ID, 0u);

    if (isnan(direction_length) || isinf(direction_length) ||
        direction_length <= 1.0e-8 ||
        isnan(ray_tmax) || isinf(ray_tmax) ||
        ray_tmax <= RAY_T_MIN ||
        push_data.upper_root >= push_data.upper_node_count) {
        if (push_data.upper_root >= push_data.upper_node_count) {
            fail_runtime(result);
        }
        hits[ray_index] = result;
        return;
    }

    vec3 direction = input_ray.direction.xyz / direction_length;
    float best_t = ray_tmax;
    bool current_hit = false;

    uint upper_stack[STACK_CAPACITY];
    uint upper_size = 0u;
    upper_stack[upper_size++] = push_data.upper_root;

    while (upper_size > 0u) {
        uint node_index = upper_stack[--upper_size];
        if (node_index >= push_data.upper_node_count) {
            fail_runtime(result);
            break;
        }
        BvhNode node = upper_nodes[node_index];
        if (!hit_aabb(
                origin,
                direction,
                node.bounds_min.xyz,
                node.bounds_max.xyz,
                best_t + hit_tolerance(best_t))) {
            continue;
        }

        if (node.meta.w != 0u) {
            uint cluster_index = node.meta.z;
            if (cluster_index >= push_data.cluster_count) {
                fail_runtime(result);
                break;
            }
            Cluster cluster = clusters[cluster_index];
            uint micro_root = cluster.meta.x;
            if (micro_root >= push_data.micro_node_count) {
                fail_runtime(result);
                break;
            }

            uint micro_stack[STACK_CAPACITY];
            uint micro_size = 0u;
            micro_stack[micro_size++] = micro_root;
            while (micro_size > 0u) {
                uint micro_index = micro_stack[--micro_size];
                if (micro_index >= push_data.micro_node_count) {
                    fail_runtime(result);
                    micro_size = 0u;
                    upper_size = 0u;
                    break;
                }
                BvhNode micro = micro_nodes[micro_index];
                if (!hit_aabb(
                        origin,
                        direction,
                        micro.bounds_min.xyz,
                        micro.bounds_max.xyz,
                        best_t + hit_tolerance(best_t))) {
                    continue;
                }

                if (micro.meta.w != 0u) {
                    uint triangle_index = micro.meta.z;
                    if (triangle_index >= push_data.triangle_count) {
                        fail_runtime(result);
                        micro_size = 0u;
                        upper_size = 0u;
                        break;
                    }
                    Triangle triangle = triangles[triangle_index];
                    float candidate_t = 0.0;
                    vec3 candidate_normal = vec3(0.0);
                    bool intersected = intersect_triangle(
                        triangle,
                        origin,
                        direction,
                        ray_tmax,
                        best_t,
                        candidate_t,
                        candidate_normal);
                    if (intersected &&
                        prefer_hit(
                            candidate_t,
                            triangle.meta.x,
                            current_hit,
                            best_t,
                            result.metadata.x)) {
                        current_hit = true;
                        best_t = candidate_t;
                        result.normal_t = vec4(candidate_normal, candidate_t);
                        result.metadata = uvec4(
                            triangle.meta.x,
                            triangle.meta.y,
                            triangle.meta.z,
                            1u);
                    }
                    continue;
                }

                if (micro_size + 2u > STACK_CAPACITY) {
                    fail_runtime(result);
                    micro_size = 0u;
                    upper_size = 0u;
                    break;
                }
                micro_stack[micro_size++] = micro.meta.x;
                micro_stack[micro_size++] = micro.meta.y;
            }
            continue;
        }

        if (upper_size + 2u > STACK_CAPACITY) {
            fail_runtime(result);
            break;
        }
        upper_stack[upper_size++] = node.meta.x;
        upper_stack[upper_size++] = node.meta.y;
    }

    hits[ray_index] = result;
}

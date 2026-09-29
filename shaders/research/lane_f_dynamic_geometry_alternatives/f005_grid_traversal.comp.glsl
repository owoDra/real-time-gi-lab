#version 460

layout(local_size_x = 64) in;

const uint INVALID_ID = 0xffffffffu;
const float RAY_T_MIN = 1.0e-4;
const float HIT_ABS_TOL = 2.0e-4;
const float HIT_REL_TOL = 2.0e-5;
const float INF = uintBitsToFloat(0x7f800000u);
const uint DDA_GUARD = 4096u;

struct RayData { vec4 origin_tmax; vec4 direction_pad; };
struct TriangleData { vec4 v0; vec4 v1; vec4 v2; uvec4 metadata; };
struct HitData { vec4 normal_t; uvec4 metadata; };

layout(std430, binding = 0) readonly buffer Rays { RayData rays[]; };
layout(std430, binding = 1) readonly buffer Triangles { TriangleData triangles[]; };
layout(std430, binding = 2) readonly buffer Pairs { uvec4 pairs[]; };
layout(std430, binding = 3) readonly buffer CellRanges { uvec4 cell_ranges[]; };
layout(std430, binding = 4) readonly buffer MacroRanges { uvec4 macro_ranges[]; };
layout(std430, binding = 5) readonly buffer BuildCounters { uint build_counters[]; };
layout(std430, binding = 6) writeonly buffer DynamicHits { HitData hits[]; };
layout(std430, binding = 7) readonly buffer FrameCounters { uint frame_data[]; } frame_counters;
layout(std430, binding = 8) buffer GridStats { uint grid_stats[]; };

layout(push_constant) uniform Push {
    vec4 origin_page_extent;
    uvec4 grid_params;
} pc;

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

bool ray_box(
    vec3 origin,
    vec3 direction,
    vec3 lo,
    vec3 hi,
    float tmax,
    out float enter_t,
    out float exit_t) {
    float lo_t = RAY_T_MIN;
    float hi_t = tmax;
    for (int axis = 0; axis < 3; ++axis) {
        float d = direction[axis];
        if (abs(d) < 1.0e-8) {
            if (origin[axis] < lo[axis] ||
                origin[axis] > hi[axis]) {
                return false;
            }
            continue;
        }
        float a = (lo[axis] - origin[axis]) / d;
        float b = (hi[axis] - origin[axis]) / d;
        if (a > b) {
            float temp = a;
            a = b;
            b = temp;
        }
        lo_t = max(lo_t, a);
        hi_t = min(hi_t, b);
        if (lo_t > hi_t) return false;
    }
    enter_t = lo_t;
    exit_t = hi_t;
    return true;
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

bool find_macro(uint key, out uvec4 range) {
    uint count = build_counters[2];
    uint lo = 0u;
    uint hi = count;
    while (lo < hi) {
        uint mid = lo + (hi - lo) / 2u;
        uint value = macro_ranges[mid].x;
        if (value < key) lo = mid + 1u;
        else hi = mid;
    }
    if (lo < count && macro_ranges[lo].x == key) {
        range = macro_ranges[lo];
        return true;
    }
    range = uvec4(0u);
    return false;
}

bool find_cell(
    uvec4 macro_range,
    uint local_key,
    out uvec4 range) {
    uint lo = macro_range.y;
    uint hi = macro_range.y + macro_range.z;
    while (lo < hi) {
        uint mid = lo + (hi - lo) / 2u;
        uint value = cell_ranges[mid].y;
        if (value < local_key) lo = mid + 1u;
        else hi = mid;
    }
    uint end = macro_range.y + macro_range.z;
    if (lo < end && cell_ranges[lo].y == local_key) {
        range = cell_ranges[lo];
        return true;
    }
    range = uvec4(0u);
    return false;
}

void init_axis(
    float ray_origin,
    float ray_direction,
    float grid_origin,
    float extent,
    int coord,
    float current_t,
    out int step,
    out float next_t,
    out float delta_t) {
    if (ray_direction > 1.0e-8) {
        step = 1;
        float boundary =
            grid_origin + float(coord + 1) * extent;
        next_t =
            max(current_t, (boundary - ray_origin) / ray_direction);
        delta_t = extent / ray_direction;
    } else if (ray_direction < -1.0e-8) {
        step = -1;
        float boundary =
            grid_origin + float(coord) * extent;
        next_t =
            max(current_t, (boundary - ray_origin) / ray_direction);
        delta_t = -extent / ray_direction;
    } else {
        step = 0;
        next_t = INF;
        delta_t = INF;
    }
}

void main() {
    uint ray_id = gl_GlobalInvocationID.x;
    if (ray_id >= frame_counters.frame_data[0]) return;

    HitData output_hit;
    output_hit.normal_t = vec4(0.0, 0.0, 0.0, INF);
    output_hit.metadata =
        uvec4(INVALID_ID, INVALID_ID, INVALID_ID, 0u);

    if (build_counters[3] != 0u ||
        build_counters[0] > pc.grid_params.y) {
        output_hit.metadata.w = 2u;
        hits[ray_id] = output_hit;
        return;
    }

    RayData ray = rays[ray_id];
    float direction_length =
        length(ray.direction_pad.xyz);
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
    float best_t = ray.origin_tmax.w;
    uint best_primitive = INVALID_ID;
    bool has_best = false;

    uvec3 min_macro = uvec3(
        build_counters[4],
        build_counters[5],
        build_counters[6]);
    uvec3 max_macro = uvec3(
        build_counters[7],
        build_counters[8],
        build_counters[9]);
    if (any(greaterThan(min_macro, max_macro))) {
        hits[ray_id] = output_hit;
        return;
    }

    float page_extent = pc.origin_page_extent.w;
    float cell_extent =
        page_extent / float(pc.grid_params.x);
    vec3 grid_lo =
        pc.origin_page_extent.xyz +
        vec3(min_macro) * page_extent;
    vec3 grid_hi =
        pc.origin_page_extent.xyz +
        vec3(max_macro + uvec3(1u)) * page_extent;

    float entry_t;
    float exit_t;
    if (!ray_box(
            origin,
            direction,
            grid_lo,
            grid_hi,
            ray.origin_tmax.w,
            entry_t,
            exit_t)) {
        hits[ray_id] = output_hit;
        return;
    }

    uint visited_macro = 0u;
    uint visited_local = 0u;
    uint empty_steps = 0u;
    uint tested_refs = 0u;
    bool runtime_error = false;

    float current_t = entry_t;
    float sample_t =
        min(exit_t, current_t + max(1.0e-5, page_extent * 1.0e-6));
    vec3 sample_position =
        origin + direction * sample_t;
    ivec3 macro_coord = ivec3(
        floor(
            (sample_position - pc.origin_page_extent.xyz) /
            page_extent));
    macro_coord = clamp(
        macro_coord,
        ivec3(min_macro),
        ivec3(max_macro));

    ivec3 macro_step;
    vec3 macro_next;
    vec3 macro_delta;
    for (int axis = 0; axis < 3; ++axis) {
        int step;
        float next_t;
        float delta_t;
        init_axis(
            origin[axis],
            direction[axis],
            pc.origin_page_extent[axis],
            page_extent,
            macro_coord[axis],
            current_t,
            step,
            next_t,
            delta_t);
        macro_step[axis] = step;
        macro_next[axis] = next_t;
        macro_delta[axis] = delta_t;
    }

    for (uint macro_guard = 0u;
         macro_guard < DDA_GUARD;
         ++macro_guard) {
        if (any(lessThan(macro_coord, ivec3(min_macro))) ||
            any(greaterThan(macro_coord, ivec3(max_macro))) ||
            current_t > exit_t ||
            (has_best && current_t > best_t)) {
            break;
        }

        ++visited_macro;
        float macro_boundary_t =
            min(macro_next.x, min(macro_next.y, macro_next.z));
        float macro_end_t =
            min(exit_t, macro_boundary_t);
        if (has_best) macro_end_t = min(macro_end_t, best_t);

        uint macro_key =
            morton3d10(uvec3(macro_coord));
        uvec4 macro_range;
        bool macro_present =
            find_macro(macro_key, macro_range);
        if (!macro_present) {
            ++empty_steps;
        } else if (macro_end_t >= current_t) {
            vec3 macro_world_min =
                pc.origin_page_extent.xyz +
                vec3(macro_coord) * page_extent;
            float local_sample_t =
                min(
                    macro_end_t,
                    current_t +
                        max(1.0e-5, cell_extent * 1.0e-6));
            vec3 local_sample_position =
                origin + direction * local_sample_t;
            ivec3 local_coord = ivec3(
                floor(
                    (local_sample_position - macro_world_min) /
                    cell_extent));
            local_coord = clamp(
                local_coord,
                ivec3(0),
                ivec3(int(pc.grid_params.x) - 1));

            ivec3 local_step;
            vec3 local_next;
            vec3 local_delta;
            for (int axis = 0; axis < 3; ++axis) {
                int step;
                float next_t;
                float delta_t;
                init_axis(
                    origin[axis],
                    direction[axis],
                    macro_world_min[axis],
                    cell_extent,
                    local_coord[axis],
                    current_t,
                    step,
                    next_t,
                    delta_t);
                local_step[axis] = step;
                local_next[axis] = next_t;
                local_delta[axis] = delta_t;
            }

            float local_t = current_t;
            for (uint local_guard = 0u;
                 local_guard < DDA_GUARD;
                 ++local_guard) {
                if (any(lessThan(local_coord, ivec3(0))) ||
                    any(greaterThanEqual(
                        local_coord,
                        ivec3(int(pc.grid_params.x)))) ||
                    local_t > macro_end_t ||
                    (has_best && local_t > best_t)) {
                    break;
                }

                ++visited_local;
                uint local_key =
                    morton3d10(uvec3(local_coord));
                uvec4 cell_range;
                if (find_cell(
                        macro_range,
                        local_key,
                        cell_range)) {
                    uint begin = cell_range.z;
                    uint end = begin + cell_range.w;
                    for (uint cursor = begin;
                         cursor < end;
                         ++cursor) {
                        ++tested_refs;
                        uint primitive = pairs[cursor].z;
                        TriangleData triangle =
                            triangles[primitive];
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
                            best_primitive =
                                triangle.metadata.x;
                            output_hit.normal_t =
                                vec4(candidate_normal, candidate_t);
                            output_hit.metadata = uvec4(
                                triangle.metadata.x,
                                triangle.metadata.y,
                                triangle.metadata.z,
                                1u);
                        }
                    }
                } else {
                    ++empty_steps;
                }

                float next_boundary =
                    min(
                        local_next.x,
                        min(local_next.y, local_next.z));
                float advance_t =
                    min(macro_end_t, next_boundary);
                if (has_best) advance_t = min(advance_t, best_t);
                if (advance_t >= macro_end_t ||
                    (has_best && advance_t >= best_t)) {
                    local_t = advance_t;
                    break;
                }

                float epsilon =
                    max(1.0e-6, abs(next_boundary) * 1.0e-6);
                for (int axis = 0; axis < 3; ++axis) {
                    if (local_next[axis] <= next_boundary + epsilon) {
                        local_coord[axis] += local_step[axis];
                        local_next[axis] += local_delta[axis];
                    }
                }
                local_t = next_boundary;

                if (local_guard + 1u == DDA_GUARD) {
                    runtime_error = true;
                }
            }
        }

        if (macro_end_t >= exit_t ||
            (has_best && macro_end_t >= best_t)) {
            current_t = macro_end_t;
            break;
        }

        float next_boundary =
            min(
                macro_next.x,
                min(macro_next.y, macro_next.z));
        float epsilon =
            max(1.0e-6, abs(next_boundary) * 1.0e-6);
        for (int axis = 0; axis < 3; ++axis) {
            if (macro_next[axis] <= next_boundary + epsilon) {
                macro_coord[axis] += macro_step[axis];
                macro_next[axis] += macro_delta[axis];
            }
        }
        current_t = next_boundary;

        if (macro_guard + 1u == DDA_GUARD) {
            runtime_error = true;
        }
    }

    atomicAdd(grid_stats[2], visited_macro);
    atomicAdd(grid_stats[3], visited_local);
    atomicAdd(grid_stats[4], empty_steps);
    atomicAdd(grid_stats[5], tested_refs);

    if (runtime_error) {
        output_hit.normal_t = vec4(0.0, 0.0, 0.0, INF);
        output_hit.metadata =
            uvec4(INVALID_ID, INVALID_ID, INVALID_ID, 2u);
    }
    hits[ray_id] = output_hit;
}

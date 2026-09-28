#version 450

layout(local_size_x = 256) in;

const uint WORK_ITEM_VALID = 1u;

struct WorkItem {
    uvec4 identity;
    vec4 origin_interval;
    vec4 direction_interval;
    uvec4 output_identity;
};

layout(std430, set = 0, binding = 3) readonly buffer WorkItems { WorkItem work_items[]; };
layout(std430, set = 0, binding = 4) buffer GatherRadiance { vec4 gathered[]; };
layout(std430, set = 0, binding = 7) readonly buffer Config {
    vec4 eye;
    vec4 camera_right;
    vec4 camera_up;
    vec4 camera_forward;
    vec4 camera;
    uvec4 grid;
    uvec4 rc;
    vec4 rc_params;
    vec4 light;
} cfg;

vec3 evaluate_control_transport(WorkItem item) {
    vec3 direction = normalize(item.direction_interval.xyz);
    float sky_mix = clamp(direction.y * 0.5 + 0.5, 0.0, 1.0);
    vec3 sky = mix(vec3(0.025, 0.035, 0.055), vec3(0.30, 0.42, 0.62), sky_mix) * cfg.light.w;

    vec3 to_light = cfg.light.xyz - item.origin_interval.xyz;
    float distance_to_light = length(to_light);
    float t_min = item.origin_interval.w;
    float t_max = item.direction_interval.w;
    if (distance_to_light <= 1e-6 || distance_to_light < t_min || distance_to_light > t_max) {
        return sky;
    }

    vec3 light_direction = to_light / distance_to_light;
    float angular = max(dot(direction, light_direction), 0.0);
    float attenuation = 1.0 / (1.0 + 0.02 * distance_to_light * distance_to_light);
    vec3 direct = vec3(1.0, 0.82, 0.64) * (cfg.rc_params.w * angular * attenuation);
    return sky + direct;
}

void main() {
    uint item_index = gl_GlobalInvocationID.x;
    if (item_index >= cfg.rc.z) {
        return;
    }

    WorkItem item = work_items[item_index];
    if ((item.output_identity.w & WORK_ITEM_VALID) == 0u) {
        gathered[item_index] = vec4(0.0);
        return;
    }

    gathered[item_index] = vec4(evaluate_control_transport(item), 1.0);
}

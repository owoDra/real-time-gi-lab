#version 460
#extension GL_EXT_ray_query : require
layout(local_size_x = 8, local_size_y = 8) in;

const float PI = 3.14159265358979323846;
const uint EMPTY = 0u;
const uint TOMBSTONE = 0xffffffffu;
const float RAY_T_MIN = 1.0e-4;
struct HitData { vec4 normal_t; uvec4 metadata; };
struct Slot { ivec4 key; uvec4 data; };
layout(std430, binding = 0) readonly buffer PrimaryHits { HitData hits[]; };
layout(std430, binding = 1) readonly buffer Slots { Slot values[]; } slots;
layout(std430, binding = 2) writeonly buffer Image { vec4 pixels[]; } image;
layout(binding = 3) uniform accelerationStructureEXT top_level;
layout(std140, binding = 4) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;
layout(push_constant) uniform Push { uint storage_mask; uint storage_max_probe; uint frame_id; uint reserved; } pc;

uint mix32(uint x) { x ^= x >> 16u; x *= 0x7feb352du; x ^= x >> 15u; x *= 0x846ca68bu; x ^= x >> 16u; return x; }
uint pack_key(ivec4 key) {
    if (key.x < 0 || key.x > 1023 || key.y < 0 || key.y > 1023 || key.z < 0 || key.z > 1023 || key.w < 0 || key.w > 3) return TOMBSTONE;
    uint packed = uint(key.x) | (uint(key.y) << 10u) | (uint(key.z) << 20u) | (uint(key.w) << 30u);
    if (packed >= 0xfffffffeu) return TOMBSTONE;
    return packed + 1u;
}
float lookup_probe(ivec3 probe, uint cascade) {
    ivec4 key = ivec4(probe, int(cascade));
    uint token = pack_key(key);
    if (token == TOMBSTONE) return 0.0;
    uint slot = mix32(token) & pc.storage_mask;
    for (uint probe_index = 0u; probe_index < pc.storage_max_probe; ++probe_index) {
        Slot candidate = slots.values[slot];
        if (candidate.data.x == EMPTY) return 0.0;
        if (candidate.data.x == token && candidate.data.w == pc.frame_id && all(equal(candidate.key, key))) {
            return candidate.data.z == 0u ? 0.0 : float(candidate.data.y) / (float(candidate.data.z) * 65535.0);
        }
        slot = (slot + 1u) & pc.storage_mask;
    }
    return 0.0;
}
bool visible_to_light(vec3 position, vec3 normal, vec3 to_light, float distance_to_light) {
    vec3 origin = position + normal * max(RAY_T_MIN * 8.0, p.camera_pos_near.w * 0.02);
    float tmax = distance_to_light - max(RAY_T_MIN * 16.0, p.camera_pos_near.w * 0.04);
    if (tmax <= RAY_T_MIN) return true;
    rayQueryEXT query;
    rayQueryInitializeEXT(query, top_level, gl_RayFlagsNoOpaqueEXT, 0xffu, origin, RAY_T_MIN, to_light, tmax);
    while (rayQueryProceedEXT(query)) {
        if (rayQueryGetIntersectionTypeEXT(query, false) == gl_RayQueryCandidateIntersectionTriangleEXT) {
            // Shared renderer prerequisite: conservative direct-light occlusion.
            // GI traversal semantics remain the accepted Lane-B implementation.
            return false;
        }
    }
    return true;
}
void main() {
    uvec2 pixel = gl_GlobalInvocationID.xy;
    if (pixel.x >= p.counts.y || pixel.y >= p.counts.z) return;
    uint id = pixel.y * p.counts.y + pixel.x;
    HitData hit = hits[id];
    if (hit.metadata.w != 1u || isnan(hit.normal_t.w) || isinf(hit.normal_t.w)) {
        image.pixels[id] = vec4(0.0, 0.0, 0.0, 1.0); return;
    }
    float nx = (2.0 * (float(pixel.x) + 0.5) / float(p.counts.y)) - 1.0;
    float ny = 1.0 - (2.0 * (float(pixel.y) + 0.5) / float(p.counts.z));
    vec3 view_direction = normalize(p.camera_forward_far.xyz + p.camera_right_tan_x.xyz * (nx * p.camera_right_tan_x.w) + p.camera_up_tan_y.xyz * (ny * p.camera_up_tan_y.w));
    vec3 position = p.camera_pos_near.xyz + view_direction * hit.normal_t.w;
    vec3 normal = normalize(hit.normal_t.xyz);
    if (dot(normal, -view_direction) < 0.0) normal = -normal;
    vec3 light_vector = p.light_pos_interval.xyz - position;
    float distance2 = dot(light_vector, light_vector);
    float direct = 0.0;
    if (distance2 > 1.0e-12) {
        float distance_to_light = sqrt(distance2);
        vec3 light_direction = light_vector / distance_to_light;
        float cosine = max(0.0, dot(normal, light_direction));
        float scale = max(p.light_pos_interval.w, 1.0e-6);
        float attenuation = (scale * scale) / (scale * scale + distance2);
        if (cosine > 0.0 && visible_to_light(position, normal, light_direction, distance_to_light)) direct = cosine * attenuation / PI;
    }
    float indirect = 0.0;
    for (uint cascade = 0u; cascade < p.counts.w; ++cascade) {
        float spacing = p.scene_origin_spacing.w * float(1u << cascade);
        ivec3 probe = ivec3(floor((position - p.scene_origin_spacing.xyz) / spacing));
        indirect += lookup_probe(probe, cascade);
    }
    float radiance = direct + indirect;
    image.pixels[id] = vec4(radiance, radiance, radiance, 1.0);
}

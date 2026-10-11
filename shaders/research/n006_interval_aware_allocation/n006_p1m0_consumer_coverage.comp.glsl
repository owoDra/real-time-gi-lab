#version 460
// N006 P1m0, diagnostic ONLY. Consumer lookup attempts per canonical
// (probe xyz,cascade) key from accepted primary hits. Never changes GI work.
layout(local_size_x = 8, local_size_y = 8) in;

const uint INVALID = 0xffffffffu;
struct HitData { vec4 normal_t; uvec4 metadata; };
layout(std430, binding = 0) readonly buffer PrimaryHits { HitData hits[]; };
layout(std430, binding = 1) readonly buffer KeyTokens { uint values[]; } keys;
layout(std430, binding = 2) buffer ConsumerCounts { uint values[]; } consumers;
// [0]=valid pixels [1]=attempts [2]=matched [3]=absent(empty slot)
// [4]=invalid key [5]=bounded probe exhausted [6]=uint32 overflow
// [7]=invalid launch contract.
layout(std430, binding = 3) buffer ConsumerStats { uint data[]; } stats;
layout(std140, binding = 4) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;
layout(push_constant) uniform Push {
    uint key_mask;
    uint max_probe;
    uint hash_capacity;
    uint consumer_capacity;
} pc;

uint mix32(uint x) {
    x ^= x >> 16u; x *= 0x7feb352du;
    x ^= x >> 15u; x *= 0x846ca68bu;
    x ^= x >> 16u; return x;
}
uint pack_key(ivec4 key) {
    if (any(lessThan(key, ivec4(0))) ||
        any(greaterThan(key, ivec4(1023,1023,1023,3)))) return INVALID;
    uint value = uint(key.x) | (uint(key.y) << 10u) |
                 (uint(key.z) << 20u) | (uint(key.w) << 30u);
    return value >= 0xfffffffeu ? INVALID : value + 1u;
}
void main() {
    uvec2 pixel = gl_GlobalInvocationID.xy;
    if (pixel.x >= p.counts.y || pixel.y >= p.counts.z) return;
    if (pc.hash_capacity == 0u || pc.hash_capacity != pc.key_mask + 1u ||
        (pc.hash_capacity & pc.key_mask) != 0u ||
        pc.consumer_capacity < pc.hash_capacity ||
        pc.max_probe == 0u || pc.max_probe > pc.hash_capacity ||
        p.counts.w != 4u) {
        atomicAdd(stats.data[7], 1u);
        return;
    }
    uint id = pixel.y * p.counts.y + pixel.x;
    HitData hit = hits[id];
    if (hit.metadata.w != 1u || isnan(hit.normal_t.w) || isinf(hit.normal_t.w)) return;
    atomicAdd(stats.data[0], 1u);

    // Keep the *exact operation sequence* from accepted N001 composite.
    float nx = (2.0 * (float(pixel.x) + 0.5) / float(p.counts.y)) - 1.0;
    float ny = 1.0 - (2.0 * (float(pixel.y) + 0.5) / float(p.counts.z));
    vec3 view_direction = normalize(p.camera_forward_far.xyz + p.camera_right_tan_x.xyz * (nx * p.camera_right_tan_x.w) + p.camera_up_tan_y.xyz * (ny * p.camera_up_tan_y.w));
    vec3 position = p.camera_pos_near.xyz + view_direction * hit.normal_t.w;
    for (uint cascade = 0u; cascade < p.counts.w; ++cascade) {
        atomicAdd(stats.data[1], 1u);
        float spacing = p.scene_origin_spacing.w * float(1u << cascade);
        ivec3 probe = ivec3(floor((position - p.scene_origin_spacing.xyz) / spacing));
        uint token = pack_key(ivec4(probe, int(cascade)));
        if (token == INVALID) {
            atomicAdd(stats.data[4], 1u);
            continue;
        }
        uint slot = mix32(token) & pc.key_mask;
        bool resolved = false;
        for (uint attempt = 0u; attempt < pc.max_probe; ++attempt) {
            uint key = keys.values[slot];
            if (key == 0u) {
                atomicAdd(stats.data[3], 1u);
                resolved = true;
                break;
            }
            if (key == token) {
                uint previous = atomicAdd(consumers.values[slot], 1u);
                if (previous == INVALID) {
                    atomicAdd(stats.data[6], 1u);
                }
                atomicAdd(stats.data[2], 1u);
                resolved = true;
                break;
            }
            slot = (slot + 1u) & pc.key_mask;
        }
        if (!resolved) {
            atomicAdd(stats.data[5], 1u);
        }
    }
}

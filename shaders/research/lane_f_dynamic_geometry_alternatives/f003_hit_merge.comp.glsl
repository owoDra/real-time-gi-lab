#version 460

layout(local_size_x = 64) in;

const uint INVALID_ID = 0xffffffffu;
const float HIT_ABS_TOL = 2.0e-4;
const float HIT_REL_TOL = 2.0e-5;

struct HitData { vec4 normal_t; uvec4 metadata; };

layout(std430, binding = 0) readonly buffer StaticHits { HitData static_hits[]; };
layout(std430, binding = 1) readonly buffer DynamicHits { HitData dynamic_hits[]; };
layout(std430, binding = 2) writeonly buffer Hits { HitData hits[]; };
layout(std430, binding = 3) readonly buffer Counters { uint data[]; } counters;

bool prefer_dynamic(HitData a, HitData b) {
    bool a_hit = a.metadata.w == 1u;
    bool b_hit = b.metadata.w == 1u;
    if (!b_hit) return false;
    if (!a_hit) return true;
    float a_t = a.normal_t.w;
    float b_t = b.normal_t.w;
    float tolerance = max(HIT_ABS_TOL, abs(a_t) * HIT_REL_TOL);
    return b_t < a_t - tolerance ||
        (abs(b_t - a_t) <= tolerance && b.metadata.x < a.metadata.x);
}

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= counters.data[0]) return;

    HitData a = static_hits[id];
    HitData b = dynamic_hits[id];
    if (a.metadata.w > 1u || b.metadata.w > 1u) {
        HitData error_hit;
        error_hit.normal_t = vec4(0.0, 0.0, 0.0, uintBitsToFloat(0x7f800000u));
        error_hit.metadata = uvec4(INVALID_ID, INVALID_ID, INVALID_ID, 2u);
        hits[id] = error_hit;
        return;
    }
    hits[id] = prefer_dynamic(a, b) ? b : a;
}

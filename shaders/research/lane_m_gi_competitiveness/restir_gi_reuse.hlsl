//042 receiver-frame SDK ReSTIR GI reuse on actual 041 candidates.
// Official SDK headers are included unmodified; positions are converted from the
// owner's frame to the current receiver frame only at the SDK load boundary.
#include <Rtxdi/GI/ReSTIRGIParameters.h>
#include <Rtxdi/Utils/RandomSamplerState.hlsli>
#include <Rtxdi/Utils/Color.hlsli>
#include <Rtxdi/Utils/TypePacking.hlsli>

struct Candidate {
    float4 origin_pdf; float4 normal_status; float4 endpoint_primitive;
    float4 endpoint_normal; float4 radiance_trial; float4 direction_cosine;
    float4 primary_direct; uint4 flags;
};
struct RAB_Surface {
    float3 origin; float depth;
    float3 normal; uint primitive;
    uint valid; uint pad0; uint pad1; uint pad2;
};
struct Controls {
    float3 camera; float epsilon;
    float3 forward; uint width;
    uint height; uint pixels; uint unit; uint pad0;
    RTXDI_RuntimeParameters runtime;
    RTXDI_ReservoirBufferParameters reservoir;
    RTXDI_GITemporalResamplingParameters temporal;
    RTXDI_GISpatialResamplingParameters spatial;
};
[[vk::binding(0,0)]] RWStructuredBuffer<RTXDI_PackedGIReservoir> reservoirs;
[[vk::binding(1,0)]] RWStructuredBuffer<float4> owners;
[[vk::binding(2,0)]] StructuredBuffer<Candidate> candidates;
[[vk::binding(3,0)]] StructuredBuffer<float4> localEndpoints;
[[vk::binding(4,0)]] RWStructuredBuffer<RAB_Surface> surfaces;
[[vk::binding(5,0)]] StructuredBuffer<float2> neighborOffsets;
[[vk::binding(6,0)]] RaytracingAccelerationStructure topLevel;
[[vk::binding(7,0)]] RWStructuredBuffer<float4> shading;
[[vk::binding(8,0)]] RWStructuredBuffer<float4> frameImage;
[[vk::binding(9,0)]] StructuredBuffer<float4> producerImage;
[[vk::binding(10,0)]] StructuredBuffer<Controls> controlsBuffer;
[[vk::binding(11,0)]] RWStructuredBuffer<uint> diagnostics;
[[vk::binding(12,0)]] RWStructuredBuffer<uint> counters;
struct Push { uint variant; uint frameIndex; uint uniformRandom; uint reserved; };
[[vk::push_constant]] ConstantBuffer<Push> push;

static const uint TABLE = 16;
static const uint ERROR_LOOKUP = 1, ERROR_TABLE = 2, ERROR_NONFINITE = 4;
static float3 g_receiver;
static RTXDI_PackedGIReservoir g_last;
static uint g_count;
static uint g_error;
static uint g_loads;
static float3 g_positions[TABLE];
static float3 g_normals[TABLE];

struct ReceiverFrameView {
    RTXDI_PackedGIReservoir operator[](uint pointer) {
        RTXDI_PackedGIReservoir r = reservoirs[pointer];
        g_last = r;
        g_loads++;
        precise float3 shift = owners[pointer].xyz - g_receiver;
        precise float3 position = shift + r.position;
        r.position = position;
        if (g_count < TABLE) {
            g_positions[g_count] = position;
            g_normals[g_count] = RTXDI_DecodeNormalizedVectorFromSnorm2x16(r.packed_normal);
            g_count++;
        } else {
            g_error |= ERROR_TABLE;
        }
        return r;
    }
};
static ReceiverFrameView g_view;
#define RTXDI_GI_RESERVOIR_BUFFER g_view
#define RTXDI_ENABLE_STORE_RESERVOIR 0
#define RTXDI_NEIGHBOR_OFFSETS_BUFFER neighborOffsets
#define RTXDI_GI_ALLOWED_BIAS_CORRECTION RTXDI_BIAS_CORRECTION_RAY_TRACED

Controls controls() { return controlsBuffer[0]; }
RAB_Surface RAB_EmptySurface() { return (RAB_Surface)0; }
bool RAB_IsSurfaceValid(RAB_Surface s) { return s.valid != 0; }
RAB_Surface RAB_GetGBufferSurface(int2 p, bool previous) {
    Controls c = controls();
    if (any(p < 0) || p.x >= int(c.width) || p.y >= int(c.height)) return RAB_EmptySurface();
    uint i = uint(p.y) * c.width + uint(p.x);
    return surfaces[(previous ? c.pixels : 0) + i];
}
float3 RAB_GetSurfaceNormal(RAB_Surface s) { return s.normal; }
float3 RAB_GetSurfaceWorldPos(RAB_Surface s) { precise float3 p = s.origin - g_receiver; return p; }
float RAB_GetSurfaceLinearDepth(RAB_Surface s) { return s.depth; }
uint RAB_GetMaterial(RAB_Surface s) { return 0; }
bool RAB_AreMaterialsSimilar(uint a, uint b) { return true; }
int2 RAB_ClampSamplePositionIntoView(int2 p, bool previous) {
    Controls c = controls();
    int2 size = int2(c.width, c.height), period = 2 * size;
    p = (p % period + period) % period;
    return min(p, period - 1 - p);
}
bool sampleNormal(float3 p, out float3 n) {
    n = 0;
    for (uint i = 0; i < g_count; i++) {
        if (all(asuint(g_positions[i]) == asuint(p))) { n = g_normals[i]; return true; }
    }
    g_error |= ERROR_LOOKUP;
    return false;
}
float RAB_GetGISampleTargetPdfForSurface(float3 p, float3 radiance, RAB_Surface s) {
    if (!RAB_IsSurfaceValid(s)) return 0;
    float luminance = RTXDI_Luminance(max(radiance, 0));
    if (!(luminance > 0)) return 0;
    precise float3 receiver = RAB_GetSurfaceWorldPos(s);
    precise float3 d = p - receiver;
    float d2 = dot(d, d);
    if (!(d2 > 0)) return 0;
    float3 n;
    if (!sampleNormal(p, n)) return 0;
    if (!(dot(n, -d) > 0)) return 0;
    float cosine = max(0, dot(s.normal, d * rsqrt(d2)));
    return luminance * cosine / RTXDI_PI;
}
bool RAB_ValidateGISampleWithJacobian(inout float jacobian) {
    // Zero-contribution loads are counted trials, not geometric samples.
    if (g_last.weight == 0 || (g_last.packed_radiance >> 18) == 0) { jacobian = 1; return true; }
    if (jacobian > 10.0 || jacobian < 1 / 10.0) return false;
    jacobian = clamp(jacobian, 1 / 3.0, 3.0);
    return true;
}
bool visibleFrom(RAB_Surface v, float3 p) {
    precise float3 o = RAB_GetSurfaceWorldPos(v);
    precise float3 d = p - o;
    float dist = length(d);
    if (!(dist > 0)) return true;
    float tmax = dist * (1.0 - 1.0e-3) - controls().epsilon;
    if (!(tmax > 0)) return true;
    RayDesc ray; ray.Origin = v.origin; ray.Direction = d / dist; ray.TMin = 0; ray.TMax = tmax;
    RayQuery<RAY_FLAG_FORCE_NON_OPAQUE | RAY_FLAG_SKIP_PROCEDURAL_PRIMITIVES> q;
    q.TraceRayInline(topLevel, 0, 255, ray);
    while (q.Proceed()) {
        if (q.CandidateType() == CANDIDATE_NON_OPAQUE_TRIANGLE && q.CandidatePrimitiveIndex() != v.primitive) {
            q.CommitNonOpaqueTriangleHit(); q.Abort();
        }
    }
    return q.CommittedStatus() == COMMITTED_NOTHING;
}
bool RAB_GetConservativeVisibility(RAB_Surface s, float3 p) { return visibleFrom(s, p); }
bool RAB_GetTemporalConservativeVisibility(RAB_Surface current, RAB_Surface previous, float3 p) { return visibleFrom(previous, p); }
#include <Rtxdi/GI/TemporalResampling.hlsli>
#include <Rtxdi/GI/SpatialResampling.hlsli>

uint array(uint stage) { return push.variant * 3 + stage; }
void store(RTXDI_GIReservoir r, uint misc, uint2 px, uint stage, float3 owner) {
    Controls c = controls();
    uint pointer = RTXDI_ReservoirPositionToPointer(c.reservoir, px, array(stage));
    reservoirs[pointer] = RTXDI_PackGIReservoir(r, misc);
    owners[pointer] = float4(owner, 0);
}
void begin(RAB_Surface s) {
    g_receiver = s.origin; g_count = 0; g_error = 0; g_loads = 0;
    g_last = (RTXDI_PackedGIReservoir)0;
}
void finish(uint stage, uint pixel) {
    Controls c = controls();
    diagnostics[(stage * 2 + push.variant) * c.pixels + pixel] = g_error | (g_loads << 8) | (g_count << 16);
    if (g_error != 0) InterlockedOr(counters[0], g_error);
    InterlockedAdd(counters[1 + stage * 2 + push.variant], g_loads);
}

[numthreads(8,8,1)] void main(uint3 id : SV_DispatchThreadID) {
    Controls c = controls();
    if (id.x >= c.width || id.y >= c.height) return;
    uint2 px = id.xy;
    uint pixel = id.y * c.width + id.x;
#if STAGE == 0
    Candidate k = candidates[pixel];
    uint status = asuint(k.normal_status.w);
    RAB_Surface s = RAB_EmptySurface();
    if (status != 0) {
        s.origin = k.origin_pdf.xyz; s.normal = k.normal_status.xyz;
        s.depth = dot(k.primary_direct.xyz - c.camera, c.forward);
        s.primitive = asuint(k.endpoint_normal.w); s.valid = 1;
    }
    surfaces[pixel] = s;
    frameImage[pixel] = float4(k.primary_direct.w, producerImage[pixel].y, 0, 0);
    for (uint v = 0; v < 2; v++) {
        RTXDI_GIReservoir r = RTXDI_EmptyGIReservoir();
        uint misc = 0;
        if (status == 2) {
            r = RTXDI_MakeGIReservoir(localEndpoints[pixel].xyz, k.endpoint_normal.xyz, k.radiance_trial.xyz * float(c.unit), k.origin_pdf.w);
        } else if (status == 1 && v == 0) {
            // V1 explicit null trial: counted M=1, zero weight/radiance.
            r.position = k.normal_status.xyz; r.normal = -k.normal_status.xyz; r.M = 1;
            misc = 0x10000;
        }
        uint pointer = RTXDI_ReservoirPositionToPointer(c.reservoir, px, v * 3);
        reservoirs[pointer] = RTXDI_PackGIReservoir(r, misc);
        owners[pointer] = float4(s.origin, 0);
    }
#elif STAGE == 1 || STAGE == 2
    RAB_Surface s = surfaces[pixel];
    begin(s);
    RTXDI_GIReservoir r = RTXDI_EmptyGIReservoir();
    if (RAB_IsSurfaceValid(s)) {
        RTXDI_RuntimeParameters runtime = c.runtime; runtime.frameIndex = push.frameIndex;
        RTXDI_GIReservoir input = RTXDI_LoadGIReservoir(c.reservoir, px, array(STAGE - 1));
#if STAGE == 1
        RTXDI_RandomSamplerState rng = RTXDI_InitRandomSampler(px, push.frameIndex, RTXDI_GI_TEMPORAL_RESAMPLING_RANDOM_SEED);
        RTXDI_GITemporalResamplingParameters p = c.temporal; p.uniformRandomNumber = push.uniformRandom;
        r = RTXDI_GITemporalResampling(px, s, float3(0, 0, 0), array(2), input, rng, runtime, c.reservoir, p);
#else
        RTXDI_RandomSamplerState rng = RTXDI_InitRandomSampler(px, push.frameIndex, RTXDI_GI_SPATIAL_RESAMPLING_RANDOM_SEED);
        r = RTXDI_GISpatialResampling(px, s, array(1), input, rng, runtime, c.reservoir, c.spatial);
#endif
        if (!all(isfinite(r.position)) || !isfinite(r.weightSum) || !all(isfinite(r.radiance))) g_error |= ERROR_NONFINITE;
    }
    store(r, 0, px, STAGE, s.origin);
    finish(STAGE - 1, pixel);
#elif STAGE == 3
    RAB_Surface s = surfaces[pixel];
    begin(s);
    float indirect = 0, cosine = 0, hemisphere = 0, visible = 0;
    RTXDI_GIReservoir r = RTXDI_EmptyGIReservoir();
    if (RAB_IsSurfaceValid(s)) {
        r = RTXDI_LoadGIReservoir(c.reservoir, px, array(2));
        float d2 = dot(r.position, r.position);
        if (r.M != 0 && d2 > 0) {
            cosine = max(0, dot(s.normal, r.position * rsqrt(d2)));
            hemisphere = dot(r.normal, -r.position) > 0 ? 1 : 0;
            visible = visibleFrom(s, r.position) ? 1 : 0;
            if (hemisphere != 0 && visible != 0)
                indirect = RTXDI_Luminance(r.radiance) / float(c.unit) * (cosine / RTXDI_PI) * r.weightSum;
        }
        if (!isfinite(indirect)) g_error |= ERROR_NONFINITE;
    }
    shading[(push.variant * c.pixels + pixel) * 2] = float4(indirect, float(r.M), r.weightSum, cosine);
    shading[(push.variant * c.pixels + pixel) * 2 + 1] = float4(hemisphere, visible, float(r.age), 0);
    float4 image = frameImage[pixel];
    if (push.variant == 0) image.z = indirect; else image.w = indirect;
    frameImage[pixel] = image;
    finish(2, pixel);
#elif STAGE == 4
    surfaces[c.pixels + pixel] = surfaces[pixel];
#endif
}

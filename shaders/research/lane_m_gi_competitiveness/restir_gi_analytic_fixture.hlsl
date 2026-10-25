// 033 synthetic bridge only. No M001 scene geometry or real visibility.
#include <Rtxdi/GI/ReSTIRGIParameters.h>
#include <Rtxdi/Utils/RandomSamplerState.hlsli>

struct RAB_Surface {
    float3 position; float depth;
    float3 normal; uint material;
    uint valid; uint3 padding;
};
struct RawSecondary { float4 position_pdf; float4 normal; float4 radiance; };
[[vk::binding(0,0)]] RWStructuredBuffer<RTXDI_PackedGIReservoir> reservoirs;
[[vk::binding(1,0)]] StructuredBuffer<RAB_Surface> currentSurfaces;
[[vk::binding(2,0)]] StructuredBuffer<RAB_Surface> previousSurfaces;
[[vk::binding(3,0)]] StructuredBuffer<RawSecondary> secondary;
[[vk::binding(4,0)]] Buffer<float2> neighborOffsets;
[[vk::binding(5,0)]] RWStructuredBuffer<float4> results;
[[vk::binding(6,0)]] StructuredBuffer<RTXDI_GISpatialResamplingParameters> spatialParameters;
[[vk::binding(7,0)]] StructuredBuffer<RTXDI_GITemporalResamplingParameters> temporalParameters;
[[vk::binding(8,0)]] StructuredBuffer<RTXDI_GISpatioTemporalResamplingParameters> fusedParameters;
[[vk::binding(9,0)]] cbuffer Controls {
    uint width; uint height; uint frame; uint sourceIndex;
    RTXDI_RuntimeParameters runtimeParameters;
    RTXDI_ReservoirBufferParameters reservoirParameters; uint2 padding;
    float3 screenMotion; uint outputIndex;
};
#define RTXDI_GI_RESERVOIR_BUFFER reservoirs
#define RTXDI_NEIGHBOR_OFFSETS_BUFFER neighborOffsets
#define RTXDI_GI_ALLOWED_BIAS_CORRECTION RTXDI_BIAS_CORRECTION_RAY_TRACED

RAB_Surface RAB_EmptySurface() { return (RAB_Surface)0; }
bool RAB_IsSurfaceValid(RAB_Surface s) { return s.valid != 0 && s.depth > 0; }
RAB_Surface RAB_GetGBufferSurface(int2 p, bool previous) {
    if (any(p < 0) || p.x >= int(width) || p.y >= int(height)) return RAB_EmptySurface();
    uint i=uint(p.y)*width+uint(p.x);
    if (previous) return previousSurfaces[i];
    return currentSurfaces[i];
}
float3 RAB_GetSurfaceNormal(RAB_Surface s) { return s.normal; }
float3 RAB_GetSurfaceWorldPos(RAB_Surface s) { return s.position; }
float RAB_GetSurfaceLinearDepth(RAB_Surface s) { return s.depth; }
uint RAB_GetMaterial(RAB_Surface s) { return s.material; }
bool RAB_AreMaterialsSimilar(uint a, uint b) { return a==b; }
int2 RAB_ClampSamplePositionIntoView(int2 p, bool previous) {
    int2 size=int2(width,height), period=2*size;
    p=(p%period+period)%period;
    return min(p,period-1-p);
}
float RAB_GetGISampleTargetPdfForSurface(float3 p, float3 radiance, RAB_Surface s) {
    float3 d=p-s.position; float d2=dot(d,d);
    if (!RAB_IsSurfaceValid(s) || d2 <= 0) return 0;
    float cosine=max(0,dot(s.normal,d*rsqrt(d2)));
    return dot(max(radiance,0),float3(.2126,.7152,.0722))*cosine/RTXDI_PI;
}
bool RAB_ValidateGISampleWithJacobian(inout float jacobian) {
    if (!isfinite(jacobian) || jacobian < .1 || jacobian > 10) return false;
    jacobian=clamp(jacobian,1.0/3.0,3.0); return true;
}
bool RAB_GetConservativeVisibility(RAB_Surface s, float3 p) {
    // A bounded opaque square, open at the ray endpoints, in synthetic world space.
    float dz=p.z-s.position.z;
    if (abs(dz)<1e-12) return true;
    float t=(.5-s.position.z)/dz; float2 q=lerp(s.position.xy,p.xy,t);
    return !(t>1e-6 && t<1-1e-6 && all(abs(q)<.25));
}
bool RAB_GetTemporalConservativeVisibility(RAB_Surface current, RAB_Surface previous, float3 p) {
    // Analytic fixture has fixed geometry; use the explicitly previous receiver.
    return RAB_GetConservativeVisibility(previous,p);
}
#include <Rtxdi/GI/SpatioTemporalResampling.hlsli>

[numthreads(8,8,1)] void main(uint3 id:SV_DispatchThreadID) {
    if (id.x>=width || id.y>=height) return;
    uint pixel=id.y*width+id.x; RAB_Surface surface=currentSurfaces[pixel];
    RawSecondary raw=secondary[pixel];
    if (!all(isfinite(raw.position_pdf)) || !all(isfinite(raw.radiance.xyz)) ||
        raw.position_pdf.w<0 || any(raw.radiance.xyz<0)) {
        results[pixel*2]=float4(-1,-1,-1,-1);results[pixel*2+1]=float4(-1,-1,-1,-1);return;
    }
    // Black/miss candidates retain M=1 and zero weight; no skipped denominator.
    float pdf=raw.position_pdf.w;
    RTXDI_GIReservoir r=RTXDI_MakeGIReservoir(raw.position_pdf.xyz,raw.normal.xyz,raw.radiance.xyz,pdf);
    if (!RAB_IsSurfaceValid(surface)) r=RTXDI_EmptyGIReservoir();
    RTXDI_RandomSamplerState rng=RTXDI_InitRandomSampler(id.xy,frame,33+PASS);
#if PASS == 1 || PASS == 2
    RTXDI_GISpatialResamplingParameters p=spatialParameters[0];
    p.biasCorrectionMode=PASS==1 ? RTXDI_BIAS_CORRECTION_BASIC : RTXDI_BIAS_CORRECTION_RAY_TRACED;
    r=RTXDI_GISpatialResampling(id.xy,surface,sourceIndex,r,rng,runtimeParameters,reservoirParameters,p);
#elif PASS == 3 || PASS == 4
    RTXDI_GITemporalResamplingParameters p=temporalParameters[0];
    p.biasCorrectionMode=PASS==3 ? RTXDI_BIAS_CORRECTION_BASIC : RTXDI_BIAS_CORRECTION_RAY_TRACED;
    r=RTXDI_GITemporalResampling(id.xy,surface,screenMotion,sourceIndex,r,rng,runtimeParameters,reservoirParameters,p);
#elif PASS == 5
    RTXDI_GISpatioTemporalResamplingParameters p=fusedParameters[0];
    p.biasCorrectionMode=RTXDI_BIAS_CORRECTION_RAY_TRACED;
    r=RTXDI_GISpatioTemporalResampling(id.xy,surface,sourceIndex,screenMotion,r,rng,runtimeParameters,reservoirParameters,p);
#endif
    uint2 coordinate=RTXDI_PixelPosToReservoirPos(id.xy,runtimeParameters.activeCheckerboardField);
    RTXDI_StoreGIReservoir(r,reservoirParameters,coordinate,outputIndex);
    RTXDI_GIReservoir packed=RTXDI_UnpackGIReservoir(RTXDI_PackGIReservoir(r,0));
    float3 delta=r.position-surface.position; float d2=dot(delta,delta);
    float cosine=d2>0 ? max(0,dot(surface.normal,delta*rsqrt(d2))) : 0;
    bool hemisphere=dot(r.normal,surface.position-r.position)>0;
    bool visible=RAB_GetConservativeVisibility(surface,r.position);
    float3 shaded=hemisphere && visible ? r.radiance*(cosine/RTXDI_PI)*r.weightSum : 0;
    // Expose packing as well as final sample output; future runtime must audit errors.
    results[pixel*2]=float4(shaded,float(r.M));
    results[pixel*2+1]=float4(packed.radiance-r.radiance,packed.weightSum);
}

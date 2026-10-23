// Isolated M001 scene adapter. CPU compilation is not runtime qualification.
// Uses the separately pinned, unmodified RTXGI SDK under its original license.
#include "ddgi/Irradiance.hlsl"

struct Triangle { float4 v0; float4 v1; float4 v2; uint4 metadata; };
struct Frame {
    float4 camera_pos_near, camera_right_tan_x, camera_up_tan_y, camera_forward_far;
    float4 scene_origin_spacing, light_pos_interval;
    uint4 counts, limits;
};
[[vk::binding(0,0)]] StructuredBuffer<DDGIVolumeDescGPUPacked> Constants;
[[vk::binding(1,0)]] RWTexture2DArray<float4> RayData;
[[vk::binding(7,0)]] RaytracingAccelerationStructure Scene;
[[vk::binding(8,0)]] StructuredBuffer<Triangle> Geometry;
[[vk::binding(9,0)]] ConstantBuffer<Frame> frame;
[[vk::binding(10,0)]] RWStructuredBuffer<float4> Pixels;
[[vk::binding(11,0)]] Texture2DArray<float4> PreviousIrradiance;
[[vk::binding(12,0)]] Texture2DArray<float4> PreviousDistance;
[[vk::binding(13,0)]] Texture2DArray<float4> PreviousProbeData;
[[vk::binding(14,0)]] SamplerState BilinearSampler;
struct Push { uint previousReady, begin, count, reserved; };
[[vk::push_constant]] ConstantBuffer<Push> pc;
static const uint INVALID = 0xffffffffu;
static const float PI = 3.14159265358979323846;

float3 offset_position(float3 position, float3 normal) {
    int3 delta = (int3)(4.0 * normal);
    int3 signed_delta = int3(position.x < 0 ? -delta.x : delta.x,
                            position.y < 0 ? -delta.y : delta.y,
                            position.z < 0 ? -delta.z : delta.z);
    float3 shifted = asfloat(asint(position) + signed_delta);
    float3 small = position + normal * 1.e-7;
    return float3(abs(position.x) < 1.0/32.0 ? small.x : shifted.x,
                  abs(position.y) < 1.0/32.0 ? small.y : shifted.y,
                  abs(position.z) < 1.0/32.0 ? small.z : shifted.z);
}

bool trace(float3 origin, float3 direction, float far_t, uint ignore,
           out uint primitive, out float3 position, out float3 normal, out float hit_t) {
    RayDesc ray; ray.Origin=origin; ray.Direction=direction; ray.TMin=0; ray.TMax=far_t;
    RayQuery<RAY_FLAG_NONE> query;
    query.TraceRayInline(Scene, ignore == INVALID ? RAY_FLAG_FORCE_OPAQUE : RAY_FLAG_FORCE_NON_OPAQUE, 0xff, ray);
    while(query.Proceed()) {
        if(query.CandidateType() == CANDIDATE_NON_OPAQUE_TRIANGLE && query.CandidatePrimitiveIndex() != ignore)
            query.CommitNonOpaqueTriangleHit();
    }
    primitive=INVALID; position=0; normal=0; hit_t=far_t;
    if(query.CommittedStatus() != COMMITTED_TRIANGLE_HIT) return false;
    primitive=query.CommittedPrimitiveIndex();
    Triangle t=Geometry[primitive]; float2 b=query.CommittedTriangleBarycentrics();
    position=t.v0.xyz+b.x*(t.v1.xyz-t.v0.xyz)+b.y*(t.v2.xyz-t.v0.xyz);
    normal=normalize(cross(t.v1.xyz-t.v0.xyz,t.v2.xyz-t.v0.xyz));
    if(dot(normal,direction)>0) normal=-normal; // BF-P two-sided, no backface discard.
    hit_t=query.CommittedRayT();
    return true;
}

bool blocked(float3 origin, float3 direction, float far_t, uint self) {
    RayDesc ray; ray.Origin=origin; ray.Direction=direction; ray.TMin=0; ray.TMax=far_t;
    RayQuery<RAY_FLAG_FORCE_NON_OPAQUE> query;
    query.TraceRayInline(Scene,RAY_FLAG_NONE,0xff,ray);
    while(query.Proceed()) {
        if(query.CandidateType()==CANDIDATE_NON_OPAQUE_TRIANGLE && query.CandidatePrimitiveIndex()!=self) {
            query.Abort(); return true;
        }
    }
    return false;
}

float direct_light(float3 position,float3 normal,uint self) {
    float3 origin=offset_position(position,normal);
    float3 lv=frame.light_pos_interval.xyz-origin;
    float d2=dot(lv,lv), dist=sqrt(d2);
    if(dist<=0) return 0;
    float3 wi=lv/dist;
    float cosine=max(0,dot(normal,wi)), s=frame.light_pos_interval.w;
    if(cosine<=0 || blocked(origin,wi,dist*(1.0-2.e-7),self)) return 0;
    return cosine*s*s/(PI*(s*s+d2));
}

float3 irradiance(float3 position,float3 normal,float3 view,DDGIVolumeDescGPU volume) {
    DDGIVolumeResources resources;
    resources.probeIrradiance=PreviousIrradiance;
    resources.probeDistance=PreviousDistance;
    resources.probeData=PreviousProbeData;
    resources.bilinearSampler=BilinearSampler;
    return DDGIGetVolumeIrradiance(position,DDGIGetSurfaceBias(normal,view,volume),normal,volume,resources);
}

// Every invocation writes one named probe ray. Host must prove complete disjoint coverage.
// Each finite-depth stage reads only the previous stage's separate atlas.
[numthreads(64,1,1)]
void TraceProbes(uint3 tid:SV_DispatchThreadID) {
    if(tid.x>=pc.count) return;
    DDGIVolumeDescGPU volume=UnpackDDGIVolumeDescGPU(Constants[0]);
    uint index=pc.begin+tid.x;
    uint probes=volume.probeCounts.x*volume.probeCounts.y*volume.probeCounts.z;
    if(index>=probes*volume.probeNumRays) return;
    uint probe=index/volume.probeNumRays, ray=index%volume.probeNumRays;
    float3 origin=DDGIGetProbeWorldPosition(DDGIGetProbeCoords(probe,volume),volume);
    float3 direction=DDGIGetProbeRayDirection(ray,volume);
    uint3 texel=DDGIGetRayDataTexelCoords(ray,probe,volume);
    uint prim; float3 pos,normal; float hit_t;
    if(!trace(origin,direction,frame.camera_forward_far.w,INVALID,prim,pos,normal,hit_t)) {
        DDGIStoreProbeRayMiss(RayData,texel,volume,float3(0,0,0)); return;
    }
    float direct=direct_light(pos,normal,prim);
    float3 radiance=float3(direct,direct,direct);
    if(pc.previousReady!=0) radiance+=irradiance(pos,normal,direction,volume)/PI;
    // rho=1 and unclamped linear HDR. No sample-harness albedo/radiance clamp.
    DDGIStoreProbeRayFrontfaceHit(RayData,texel,volume,radiance,hit_t);
}

[numthreads(8,8,1)]
void GatherPixels(uint3 tid:SV_DispatchThreadID) {
    if(tid.x>=frame.counts.y || tid.y>=frame.counts.z) return;
    uint id=tid.y*frame.counts.y+tid.x;
    float nx=2.0*(float(tid.x)+.5)/float(frame.counts.y)-1.0;
    float ny=1.0-2.0*(float(tid.y)+.5)/float(frame.counts.z);
    float3 view=normalize(frame.camera_forward_far.xyz+nx*frame.camera_right_tan_x.w*frame.camera_right_tan_x.xyz+
                         ny*frame.camera_up_tan_y.w*frame.camera_up_tan_y.xyz);
    uint prim; float3 pos,normal; float hit_t;
    if(!trace(frame.camera_pos_near.xyz,view,frame.camera_forward_far.w,INVALID,prim,pos,normal,hit_t)) {
        Pixels[id]=float4(0,0,0,1); return;
    }
    float direct=direct_light(pos,normal,prim);
    DDGIVolumeDescGPU volume=UnpackDDGIVolumeDescGPU(Constants[0]);
    float indirect=pc.previousReady!=0 ? irradiance(pos,normal,view,volume).x/PI : 0;
    Pixels[id]=float4(direct,indirect,direct+indirect,1);
}

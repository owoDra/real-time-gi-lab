//037 actual GPU-produced finite suffixes. SDK algorithms remain unchanged.
#include <Rtxdi/GI/ReSTIRGIParameters.h>
struct Candidate {
    float4 origin_pdf; float4 normal_status; float4 endpoint_primitive;
    float4 endpoint_normal; float4 radiance_trial; float4 direction_cosine;
    float4 primary_direct; uint4 flags;
};
[[vk::binding(0,0)]] RWStructuredBuffer<RTXDI_PackedGIReservoir> reservoirs;
[[vk::binding(1,0)]] StructuredBuffer<Candidate> candidates;
[[vk::binding(2,0)]] RWStructuredBuffer<float4> results;
[[vk::binding(3,0)]] RaytracingAccelerationStructure topLevel;
struct Push { uint start; uint count; uint reserved0; uint reserved1; };
[[vk::push_constant]] ConstantBuffer<Push> push;
#define RTXDI_GI_RESERVOIR_BUFFER reservoirs
#include <Rtxdi/GI/Reservoir.hlsli>

bool visible(Candidate c) {
    float3 delta=c.endpoint_primitive.xyz-c.origin_pdf.xyz;
    float distance=length(delta);
    if (!(distance>0)) return false;
    RayDesc ray;ray.Origin=c.origin_pdf.xyz;ray.Direction=delta/distance;
    ray.TMin=0;ray.TMax=distance*(1.0-2.0e-7);
    RayQuery<RAY_FLAG_FORCE_NON_OPAQUE | RAY_FLAG_SKIP_PROCEDURAL_PRIMITIVES> q;
    q.TraceRayInline(topLevel,0,255,ray);
    while(q.Proceed()) {
        if(q.CandidateType()==CANDIDATE_NON_OPAQUE_TRIANGLE) {
            uint primitive=q.CandidatePrimitiveIndex();
            if(primitive!=asuint(c.endpoint_normal.w) && primitive!=asuint(c.endpoint_primitive.w)) {
                q.CommitNonOpaqueTriangleHit();q.Abort();
            }
        }
    }
    return q.CommittedStatus()==COMMITTED_NOTHING;
}
[numthreads(32,1,1)] void main(uint3 id:SV_DispatchThreadID) {
    if(id.x>=push.count)return;
    uint pixel=push.start+id.x;Candidate c=candidates[pixel];
    uint status=asuint(c.normal_status.w);
    RTXDI_GIReservoir r=RTXDI_EmptyGIReservoir();
#if PACKED
    r=RTXDI_UnpackGIReservoir(reservoirs[pixel]);
#else
    if(status==2)r=RTXDI_MakeGIReservoir(c.endpoint_primitive.xyz,c.endpoint_normal.xyz,c.radiance_trial.xyz,c.origin_pdf.w);
    reservoirs[pixel]=RTXDI_PackGIReservoir(r,0);
#endif
    float3 rgb=0;float cosine=0;bool hemi=false;bool clear=false;
    if(status==2) {
        float3 delta=r.position-c.origin_pdf.xyz;
        cosine=max(0,dot(c.normal_status.xyz,normalize(delta)));
        hemi=dot(r.normal,c.origin_pdf.xyz-r.position)>0;
        clear=visible(c);
        if(hemi&&clear)rgb=r.radiance*(cosine/RTXDI_PI)*r.weightSum;
    }
    uint slot=pixel*6+(PACKED?3:0);
    results[slot]=float4(rgb,float(r.M));
    results[slot+1]=float4(r.weightSum,cosine,hemi?1:0,clear?1:0);
    results[slot+2]=float4(c.primary_direct.www+rgb,1);
}

// M001/011. Standalone exact SDK border mapping, separated from interior blend.
// Sources are immutable interior texels in the same probe/layer. No barrier or
// interior write occurs in either entry. Host dispatches side x side x side.
[[vk::binding(2,0)]] RWTexture2DArray<float4> Irradiance;
[[vk::binding(3,0)]] RWTexture2DArray<float2> Distance;

bool border(uint2 p, uint n) {
    return p.x==0 || p.y==0 || p.x==n-1 || p.y==n-1;
}

uint2 interior_source(uint2 p, uint n) {
    bool corner=(p.x==0 || p.x==n-1) && (p.y==0 || p.y==n-1);
    if(corner) return uint2(p.x>0?1:n-2,p.y>0?1:n-2);
    if(p.x>0 && p.x<n-1) return uint2(n-1-p.x,p.y>0?p.y-1:1);
    return uint2(p.x>0?p.x-1:1,n-1-p.y);
}

[numthreads(8,8,1)]
void CopyIrradianceBorder(uint3 id:SV_DispatchThreadID,uint3 local:SV_GroupThreadID,uint3 group:SV_GroupID) {
    if(!border(local.xy,8)) return;
    uint3 source=uint3(group.xy*8+interior_source(local.xy,8),id.z);
    Irradiance[id]=Irradiance[source];
}

[numthreads(16,16,1)]
void CopyDistanceBorder(uint3 id:SV_DispatchThreadID,uint3 local:SV_GroupThreadID,uint3 group:SV_GroupID) {
    if(!border(local.xy,16)) return;
    uint3 source=uint3(group.xy*16+interior_source(local.xy,16),id.z);
    Distance[id]=Distance[source];
}

//024 full RGB physical rho1/zero-specular composition, direct unfiltered.
#include "NRD.hlsli"
[[vk::binding(0,0)]] StructuredBuffer<float4> rawPT;
[[vk::binding(1,0)]] Texture2D<float4> denoised;
[[vk::binding(2,0)]] RWStructuredBuffer<float4> finalRGB;
[numthreads(8,8,1)]
void main(uint3 id:SV_DispatchThreadID){if(id.x>=320||id.y>=180)return;uint p=id.y*320+id.x;
    float3 indirect=RELAX_BackEnd_UnpackRadiance(denoised.Load(int3(id.xy,0)));
    finalRGB[p]=float4(rawPT[p].x.xxx+indirect,1);
}

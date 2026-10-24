//023 guide conversion uses the pinned official NRD front-end helpers.
#include "NRD.hlsli"
struct Camera {float4 origin;float4 forward;float4 right;float4 up;float4 meta;};
[[vk::binding(0,0)]] StructuredBuffer<float4> rawPT;
[[vk::binding(1,0)]] StructuredBuffer<uint> primary;
[[vk::binding(2,0)]] StructuredBuffer<float2> secondary;
[[vk::binding(3,0)]] ConstantBuffer<Camera> camera;
[[vk::binding(4,0)]] RWTexture2D<float4> noisyDiffuse;
[[vk::binding(5,0)]] RWTexture2D<float4> normalRoughness;
[[vk::binding(6,0)]] RWTexture2D<float> viewZ;
[[vk::binding(7,0)]] RWTexture2D<float4> motion;
[[vk::binding(8,0)]] RWStructuredBuffer<uint> inputErrors;
[numthreads(8,8,1)]
void main(uint3 id:SV_DispatchThreadID){
    uint width=uint(camera.meta.z),height=uint(camera.meta.w);if(id.x>=width||id.y>=height)return;uint p=id.y*width+id.x;uint hit=primary[p*8+7];uint error=hit>1?1:0;
    float3 n=hit?asfloat(uint3(primary[p*8],primary[p*8+1],primary[p*8+2])):float3(0,0,1);
    float distance=secondary[p].y;float radiance=rawPT[p].y;
    error|=(!all(isfinite(n))||abs(dot(n,n)-1)>1e-4)?2:0;
    error|=(!isfinite(distance)||distance<0||distance>NRD_FP16_MAX)?4:0;
    error|=(!isfinite(radiance)||radiance<0||radiance>NRD_FP16_MAX)?8:0;
    float nx=2*(float(id.x)+.5)/float(width)-1,ny=1-2*(float(id.y)+.5)/float(height);
    float3 ray=normalize(camera.forward.xyz+nx*camera.right.w*camera.right.xyz+ny*camera.up.w*camera.up.xyz);
    float z=hit?asfloat(primary[p*8+3])*dot(ray,camera.forward.xyz):2*camera.forward.w;
    error|=(!isfinite(z)||z<=0||(hit&&z>camera.forward.w))?16:0;
    inputErrors[p]=error;normalRoughness[id.xy]=NRD_FrontEnd_PackNormalAndRoughness(n,1,0);
    noisyDiffuse[id.xy]=RELAX_FrontEnd_PackRadianceAndHitDist(radiance.xxx,distance,true);
    viewZ[id.xy]=z;motion[id.xy]=float4(0,0,0,0);
}

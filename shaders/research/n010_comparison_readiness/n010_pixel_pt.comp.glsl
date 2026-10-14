#version 460
#extension GL_EXT_ray_query : require
// Independent pixel path tracing: grey rho=1, opaque two-sided surfaces,
// point-light NEE, finite vertex count, black background. No RC/probe lookup.
layout(local_size_x=8, local_size_y=8) in;
struct Triangle { vec4 v0; vec4 v1; vec4 v2; uvec4 metadata; };
layout(std430,binding=0) writeonly buffer Image { vec4 pixels[]; };
layout(binding=1) uniform accelerationStructureEXT top_level;
layout(std430,binding=2) readonly buffer Geometry { Triangle triangles[]; };
layout(std140,binding=3) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;
layout(push_constant) uniform Push { uint spp; uint vertices; uint seed; uint reserved; } pc;
const float PI=3.14159265358979323846;
const uint INVALID=0xffffffffu;
uint rng;
uint mix32(uint x) { x^=x>>16u; x*=0x7feb352du; x^=x>>15u; x*=0x846ca68bu; return x^(x>>16u); }
float uniform01() { rng+=0x9e3779b9u; return (float(mix32(rng)>>8u)+0.5)/16777216.0; }
vec3 offset_position(vec3 position, vec3 normal) {
    // Four representable float steps in the outgoing normal direction;
    // small-coordinate fallback, independent of camera near/far clip.
    ivec3 delta=ivec3(4.0*normal);
    vec3 shifted=intBitsToFloat(floatBitsToInt(position)+mix(delta,-delta,lessThan(position,vec3(0))));
    return mix(shifted,position+normal*1.0e-7,lessThan(abs(position),vec3(1.0/32.0)));
}
bool trace(vec3 origin, vec3 direction, float far_t, uint ignore,
           out uint primitive, out vec3 position, out vec3 normal) {
    rayQueryEXT q;
    uint flags=ignore==INVALID ? gl_RayFlagsOpaqueEXT : gl_RayFlagsNoOpaqueEXT;
    rayQueryInitializeEXT(q,top_level,flags,0xffu,origin,0.0,direction,far_t);
    while(rayQueryProceedEXT(q)) {
        if(rayQueryGetIntersectionTypeEXT(q,false)==gl_RayQueryCandidateIntersectionTriangleEXT &&
           uint(rayQueryGetIntersectionPrimitiveIndexEXT(q,false))!=ignore)
            rayQueryConfirmIntersectionEXT(q);
    }
    if(rayQueryGetIntersectionTypeEXT(q,true)!=gl_RayQueryCommittedIntersectionTriangleEXT) return false;
    primitive=uint(rayQueryGetIntersectionPrimitiveIndexEXT(q,true));
    Triangle t=triangles[primitive];
    vec2 b=rayQueryGetIntersectionBarycentricsEXT(q,true);
    position=t.v0.xyz+b.x*(t.v1.xyz-t.v0.xyz)+b.y*(t.v2.xyz-t.v0.xyz);
    normal=normalize(cross(t.v1.xyz-t.v0.xyz,t.v2.xyz-t.v0.xyz));
    if(dot(normal,direction)>0.0) normal=-normal;
    return true;
}
bool blocked(vec3 origin,vec3 direction,float far_t,uint self) {
    rayQueryEXT q;
    rayQueryInitializeEXT(q,top_level,gl_RayFlagsNoOpaqueEXT,0xffu,origin,0.0,direction,far_t);
    while(rayQueryProceedEXT(q)) {
        if(rayQueryGetIntersectionTypeEXT(q,false)==gl_RayQueryCandidateIntersectionTriangleEXT &&
           uint(rayQueryGetIntersectionPrimitiveIndexEXT(q,false))!=self) {
            rayQueryTerminateEXT(q); return true;
        }
    }
    return false;
}
float direct_light(vec3 position,vec3 normal,uint self) {
    vec3 origin=offset_position(position,normal);
    vec3 lv=p.light_pos_interval.xyz-origin;
    float d2=dot(lv,lv), dist=sqrt(d2);
    if(dist<=0.0) return 0.0;
    vec3 wi=lv/dist;
    float cosine=max(0.0,dot(normal,wi)), s=p.light_pos_interval.w;
    if(cosine<=0.0 || blocked(origin,wi,dist*(1.0-2.0e-7),self)) return 0.0;
    return cosine*s*s/(PI*(s*s+d2));
}
vec3 cosine_direction(vec3 normal) {
    float u=uniform01(), angle=2.0*PI*uniform01();
    vec3 helper=abs(normal.z)<0.999 ? vec3(0,0,1) : vec3(0,1,0);
    vec3 tangent=normalize(cross(helper,normal)), bitangent=cross(normal,tangent);
    return normalize(sqrt(u)*(cos(angle)*tangent+sin(angle)*bitangent)+sqrt(1.0-u)*normal);
}
void main() {
    uvec2 px=gl_GlobalInvocationID.xy;
    if(px.x>=p.counts.y || px.y>=p.counts.z) return;
    uint id=px.y*p.counts.y+px.x;
    float nx=2.0*(float(px.x)+0.5)/float(p.counts.y)-1.0;
    float ny=1.0-2.0*(float(px.y)+0.5)/float(p.counts.z);
    vec3 view=normalize(p.camera_forward_far.xyz+nx*p.camera_right_tan_x.w*p.camera_right_tan_x.xyz+
                        ny*p.camera_up_tan_y.w*p.camera_up_tan_y.xyz);
    uint prim; vec3 pos,normal;
    if(!trace(p.camera_pos_near.xyz,view,p.camera_forward_far.w,INVALID,prim,pos,normal)) {
        pixels[id]=vec4(0,0,0,1); return;
    }
    float direct=direct_light(pos,normal,prim), sum_indirect=0.0;
    rng=mix32(pc.seed^mix32(id));
    for(uint sample_index=0u;sample_index<pc.spp;++sample_index) {
        vec3 origin=pos, n=normal; uint self=prim;
        float indirect=0.0;
        for(uint vertex=1u;vertex<pc.vertices;++vertex) {
            vec3 wi=cosine_direction(n), next_position,next_normal; uint next_primitive;
            if(!trace(offset_position(origin,n),wi,1.0e30,self,next_primitive,next_position,next_normal)) break;
            indirect+=direct_light(next_position,next_normal,next_primitive);
            origin=next_position; n=next_normal; self=next_primitive;
        }
        sum_indirect+=indirect;
    }
    float indirect=sum_indirect/float(pc.spp);
    pixels[id]=vec4(direct,indirect,direct+indirect,1);
}

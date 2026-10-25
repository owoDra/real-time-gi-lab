#version 460
#extension GL_EXT_ray_query : require
// 049 sequence roles PT / PTA / RTCV (ROLE 0/1/2, set at compile time).
// Transport is the unchanged n010 raw-PT estimator: grey rho=1, opaque two-sided
// surfaces, point-light NEE with soft falloff, finite vertex count, black background.
layout(local_size_x=32) in;
struct Triangle { vec4 v0; vec4 v1; vec4 v2; uvec4 metadata; };
struct Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
};
layout(std430,binding=0) writeonly buffer Image { vec4 pixels[]; };
layout(binding=1) uniform accelerationStructureEXT top_level;
layout(std430,binding=2) readonly buffer Geometry { Triangle triangles[]; };
layout(std140,binding=3) uniform Current { Params p; };
layout(binding=4) uniform accelerationStructureEXT previous_level;
layout(std430,binding=5) readonly buffer PreviousGeometry { Triangle previous_triangles[]; };
layout(std140,binding=6) uniform Previous { Params q; };
// anchor: [0]=position.xyz,triangle bits  [1]=normal.xyz,instance bits  [2]=b1,b2,direct,valid
layout(std430,binding=7) buffer Anchor { vec4 anchors[]; };
layout(std430,binding=8) readonly buffer PreviousAnchor { vec4 previous_anchors[]; };
// history: [0]=H,V,m1,m2  [1]=d2,n,valid,replays
layout(std430,binding=9) writeonly buffer History { vec4 history[]; };
layout(std430,binding=10) readonly buffer PreviousHistory { vec4 previous_history[]; };
// previous-frame replay-difference/sample-variance ratio per 16x16 tile (host reduced)
layout(std430,binding=11) readonly buffer TileRatio { float tile_ratio[]; };
// ROLE 3: A-SVGF-style normalized temporal gradient per 3x3 stratum (-1 = none)
layout(std430,binding=12) buffer Gradient { float gradient[]; };
// ROLE 4: per-pixel sample pass output (f1 mean, replay difference mean, previous pixel or -1, f1^2 mean)
layout(std430,binding=13) buffer Scratch { vec4 scratch[]; };
layout(push_constant) uniform Push { uint mode; uint seed; uint start; uint k; uint k_new; uint vertices; uint flags; uint n_max; uint ratio_bits; } pc;
const float PI=3.14159265358979323846;
const uint INVALID=0xffffffffu;
const uint GEOMETRY_CHANGED=1u, LIGHT_CHANGED=2u, CAMERA_CHANGED=4u, NO_HISTORY=8u;
const float BETA=0.125;
uint rng;
uint mix32(uint x) { x^=x>>16u; x*=0x7feb352du; x^=x>>15u; x*=0x846ca68bu; return x^(x>>16u); }
float uniform01() { rng+=0x9e3779b9u; return (float(mix32(rng)>>8u)+0.5)/16777216.0; }
vec3 offset_position(vec3 position, vec3 normal) {
    ivec3 delta=ivec3(4.0*normal);
    vec3 shifted=intBitsToFloat(floatBitsToInt(position)+mix(delta,-delta,lessThan(position,vec3(0))));
    return mix(shifted,position+normal*1.0e-7,lessThan(abs(position),vec3(1.0/32.0)));
}
bool trace_in(bool old, vec3 origin, vec3 direction, float far_t, uint ignore,
              out uint primitive, out vec3 position, out vec3 normal, out vec2 bary) {
    rayQueryEXT r;
    uint flags=ignore==INVALID ? gl_RayFlagsOpaqueEXT : gl_RayFlagsNoOpaqueEXT;
    if(old) rayQueryInitializeEXT(r,previous_level,flags,0xffu,origin,0.0,direction,far_t);
    else rayQueryInitializeEXT(r,top_level,flags,0xffu,origin,0.0,direction,far_t);
    while(rayQueryProceedEXT(r)) {
        if(rayQueryGetIntersectionTypeEXT(r,false)==gl_RayQueryCandidateIntersectionTriangleEXT &&
           uint(rayQueryGetIntersectionPrimitiveIndexEXT(r,false))!=ignore)
            rayQueryConfirmIntersectionEXT(r);
    }
    if(rayQueryGetIntersectionTypeEXT(r,true)!=gl_RayQueryCommittedIntersectionTriangleEXT) return false;
    primitive=uint(rayQueryGetIntersectionPrimitiveIndexEXT(r,true));
    Triangle t=old ? previous_triangles[primitive] : triangles[primitive];
    bary=rayQueryGetIntersectionBarycentricsEXT(r,true);
    position=t.v0.xyz+bary.x*(t.v1.xyz-t.v0.xyz)+bary.y*(t.v2.xyz-t.v0.xyz);
    normal=normalize(cross(t.v1.xyz-t.v0.xyz,t.v2.xyz-t.v0.xyz));
    if(dot(normal,direction)>0.0) normal=-normal;
    return true;
}
bool blocked_in(bool old, vec3 origin, vec3 direction, float far_t, uint self) {
    rayQueryEXT r;
    if(old) rayQueryInitializeEXT(r,previous_level,gl_RayFlagsNoOpaqueEXT,0xffu,origin,0.0,direction,far_t);
    else rayQueryInitializeEXT(r,top_level,gl_RayFlagsNoOpaqueEXT,0xffu,origin,0.0,direction,far_t);
    while(rayQueryProceedEXT(r)) {
        if(rayQueryGetIntersectionTypeEXT(r,false)==gl_RayQueryCandidateIntersectionTriangleEXT &&
           uint(rayQueryGetIntersectionPrimitiveIndexEXT(r,false))!=self) {
            rayQueryTerminateEXT(r); return true;
        }
    }
    return false;
}
float direct_light(bool old, vec4 light, vec3 position, vec3 normal, uint self) {
    vec3 origin=offset_position(position,normal);
    vec3 lv=light.xyz-origin;
    float d2=dot(lv,lv), dist=sqrt(d2);
    if(dist<=0.0) return 0.0;
    vec3 wi=lv/dist;
    float cosine=max(0.0,dot(normal,wi)), s=light.w;
    if(cosine<=0.0 || blocked_in(old,origin,wi,dist*(1.0-2.0e-7),self)) return 0.0;
    return cosine*s*s/(PI*(s*s+d2));
}
vec3 cosine_direction(vec3 normal, float u, float v) {
    float angle=2.0*PI*v;
    vec3 helper=abs(normal.z)<0.999 ? vec3(0,0,1) : vec3(0,1,0);
    vec3 tangent=normalize(cross(helper,normal)), bitangent=cross(normal,tangent);
    return normalize(sqrt(u)*(cos(angle)*tangent+sin(angle)*bitangent)+sqrt(1.0-u)*normal);
}
// One raw-PT indirect sample; the random stream is fixed by `stream`, so the
// same stream replays the same primary-sample-space path in another scene.
float path(bool old, vec4 light, vec3 position, vec3 normal, uint self, uint stream) {
    rng=stream; float indirect=0.0; vec3 origin=position, n=normal; uint s=self;
    for(uint vertex=1u;vertex<pc.vertices;++vertex) {
        float u=uniform01(), v=uniform01();
        vec3 wi=cosine_direction(n,u,v), next_position,next_normal; uint next_primitive; vec2 b;
        if(!trace_in(old,offset_position(origin,n),wi,1.0e30,s,next_primitive,next_position,next_normal,b)) break;
        indirect+=direct_light(old,light,next_position,next_normal,next_primitive);
        origin=next_position; n=next_normal; s=next_primitive;
    }
    return indirect;
}
// Shared-geometry replay: one traced path, next-event estimation for both lights.
vec2 path_shared(vec3 position, vec3 normal, uint self, uint stream) {
    rng=stream; vec2 indirect=vec2(0); vec3 origin=position, n=normal; uint s=self;
    for(uint vertex=1u;vertex<pc.vertices;++vertex) {
        float u=uniform01(), v=uniform01();
        vec3 wi=cosine_direction(n,u,v), next_position,next_normal; uint next_primitive; vec2 b;
        if(!trace_in(false,offset_position(origin,n),wi,1.0e30,s,next_primitive,next_position,next_normal,b)) break;
        indirect+=vec2(direct_light(false,p.light_pos_interval,next_position,next_normal,next_primitive),
                       direct_light(false,q.light_pos_interval,next_position,next_normal,next_primitive));
        origin=next_position; n=next_normal; s=next_primitive;
    }
    return indirect;
}
uint pixel_index() { return pc.start+gl_GlobalInvocationID.x; }
void primary(uint id) {
    uint w=p.counts.y, h=p.counts.z;
    uvec2 px=uvec2(id%w,id/w);
    float nx=2.0*(float(px.x)+0.5)/float(w)-1.0;
    float ny=1.0-2.0*(float(px.y)+0.5)/float(h);
    vec3 view=normalize(p.camera_forward_far.xyz+nx*p.camera_right_tan_x.w*p.camera_right_tan_x.xyz+
                        ny*p.camera_up_tan_y.w*p.camera_up_tan_y.xyz);
    uint prim; vec3 pos,normal; vec2 b;
    if(!trace_in(false,p.camera_pos_near.xyz,view,p.camera_forward_far.w,INVALID,prim,pos,normal,b)) {
        anchors[id*3u]=vec4(0); anchors[id*3u+1u]=vec4(0); anchors[id*3u+2u]=vec4(0); return;
    }
    float direct=direct_light(false,p.light_pos_interval,pos,normal,prim);
    anchors[id*3u]=vec4(pos,uintBitsToFloat(prim));
    anchors[id*3u+1u]=vec4(normal,uintBitsToFloat(triangles[prim].metadata.z));
    anchors[id*3u+2u]=vec4(b,direct,1.0);
}
// Previous-frame position x' of the same surface point (same triangle and barycentrics in the
// previous scene) and the previous pixel q whose stored anchor is coplanar with x' nearby; -1 if none.
int reproject(vec3 normal, uint prim, vec2 b, out vec3 xp, out vec3 np) {
    Triangle t=previous_triangles[prim];
    xp=t.v0.xyz+b.x*(t.v1.xyz-t.v0.xyz)+b.y*(t.v2.xyz-t.v0.xyz);
    np=normalize(cross(t.v1.xyz-t.v0.xyz,t.v2.xyz-t.v0.xyz));
    if(dot(np,normal)<0.0) np=-np;
    vec3 d=xp-q.camera_pos_near.xyz;
    float z=dot(d,q.camera_forward_far.xyz);
    if(z<=q.camera_pos_near.w) return -1;
    float sx=dot(d,q.camera_right_tan_x.xyz)/(z*q.camera_right_tan_x.w);
    float sy=dot(d,q.camera_up_tan_y.xyz)/(z*q.camera_up_tan_y.w);
    uint w=q.counts.y, h=q.counts.z;
    float fx=(sx+1.0)*0.5*float(w)-0.5, fy=(1.0-sy)*0.5*float(h)-0.5;
    int ix=int(floor(fx+0.5)), iy=int(floor(fy+0.5));
    if(ix<0||iy<0||ix>=int(w)||iy>=int(h)) return -1;
    uint j=uint(iy)*w+uint(ix);
    vec4 a0=previous_anchors[j*3u], a1=previous_anchors[j*3u+1u], a2=previous_anchors[j*3u+2u];
    if(a2.w!=1.0 || floatBitsToUint(a1.w)!=t.metadata.z) return -1;
    vec3 tn=np; if(dot(tn,a1.xyz)<0.0) tn=-tn;
    float footprint=2.0*z*q.camera_right_tan_x.w/float(w);
    if(dot(tn,a1.xyz)<0.999 || abs(dot(tn,a0.xyz-xp))>1.0e-3*footprint+1.0e-6*z || length(a0.xyz-xp)>2.0*footprint) return -1;
    return int(j);
}
void paths(uint id) {
    vec4 a0=anchors[id*3u], a1=anchors[id*3u+1u], a2=anchors[id*3u+2u];
    if(a2.w!=1.0) { pixels[id]=vec4(0,0,0,1); history[id*2u]=vec4(0); history[id*2u+1u]=vec4(0); return; }
    vec3 x=a0.xyz, n=a1.xyz; uint prim=floatBitsToUint(a0.w); float direct=a2.z;
    vec3 xp=x, np=n; int j=-1;
#if ROLE!=0
    if((pc.flags&NO_HISTORY)==0u) j=reproject(n,prim,a2.xy,xp,np);
#endif
    uint base=mix32(pc.seed^mix32(id));
    float H, v, m1, m2, d2, count, replays=0.0;
    if(j<0) {
        uint k=ROLE==0 ? pc.k : pc.k_new; float s=0.0, ss=0.0;
        for(uint i=0u;i<k;++i){ float f=path(false,p.light_pos_interval,x,n,prim,mix32(base+i)); s+=f; ss+=f*f; }
        H=s/float(k); m1=H; m2=ss/float(k); v=1.0/float(k); d2=0.0; count=1.0;
    } else {
        vec4 h0=previous_history[uint(j)*2u], h1=previous_history[uint(j)*2u+1u];
        float s1=0.0, s0=0.0, ss1=0.0, sd=0.0; uint k=pc.k;
#if ROLE==2
        // Replay the same primary-sample-space path from x' (the same surface point in the
        // previous scene). The sub-pixel shift between x' and the previous anchor is left to
        // reprojection: an anchor-shift replay was decorrelated (049 dev, replay ratio ~1%).
        vec3 y=xp, yn=np; uint yprim=prim;
        bool same_point=all(equal(y,x)) && (pc.flags&GEOMETRY_CHANGED)==0u;
        bool same=same_point && (pc.flags&LIGHT_CHANGED)==0u;
        for(uint i=0u;i<k;++i) {
            uint stream=mix32(base+i); float f1,f0;
            if(same) { f1=path(false,p.light_pos_interval,x,n,prim,stream); f0=f1; }
            else if(same_point) { vec2 f=path_shared(x,n,prim,stream); f1=f.x; f0=f.y; replays+=1.0; }
            else { f1=path(false,p.light_pos_interval,x,n,prim,stream); f0=path(true,q.light_pos_interval,y,yn,yprim,stream); replays+=1.0; }
            s1+=f1; s0+=f0; ss1+=f1*f1; sd+=(f1-f0)*(f1-f0);
        }
        float f1m=s1/float(k), f0m=s0/float(k);
        // Deterministic weight: per-pixel history variance v (units of the per-sample
        // variance) is propagated with the frame-global replay ratio r only, never with
        // this pixel's own samples (outlier-coupled weights are biased).
        uint tile=(id/p.counts.y/16u)*((p.counts.y+15u)/16u)+(id%p.counts.y)/16u;
        float r=same ? 0.0 : tile_ratio[tile];
        float hv=h0.y;
        float w=clamp((1.0-0.5*r)/(1.0+float(k)*hv),0.0,1.0-1.0/float(pc.n_max));
        H=f1m-w*(f0m-h0.x);
        v=((1.0-w)*(1.0-w)+w*r)/float(k)+w*w*hv;
        d2=sd/float(k);
#else
        for(uint i=0u;i<k;++i){ float f=path(false,p.light_pos_interval,x,n,prim,mix32(base+i)); s1+=f; ss1+=f*f; }
        float f1m=s1/float(k), prior=h1.y;
#if ROLE==3
        // A-SVGF anti-lag: the gradient of the surrounding 3x3 strata shortens the history.
        uint w=p.counts.y, h=p.counts.z, sw=(w+2u)/3u, sh=(h+2u)/3u; int cx=int((id%w)/3u), cy=int((id/w)/3u);
        float lsum=0.0, lnum=0.0;
        for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++){int gx=cx+dx, gy=cy+dy;
            if(gx<0||gy<0||gx>=int(sw)||gy>=int(sh))continue; float g=gradient[uint(gy)*sw+uint(gx)]; if(g>=0.0){lsum+=g;lnum+=1.0;}}
        float lambda=lnum>0.0 ? clamp(lsum/lnum,0.0,1.0) : 0.0;
        prior=prior*(1.0-lambda);
        float alpha=max(max(1.0/(prior+1.0),1.0/float(pc.n_max)),lambda);
#else
        float alpha=max(1.0/(prior+1.0),1.0/float(pc.n_max));
#endif
        H=mix(h0.x,f1m,alpha); v=0.0; d2=0.0;
#endif
        m1=mix(h0.z,s1/float(k),BETA); m2=mix(h0.w,ss1/float(k),BETA);
#if ROLE==3
        count=min(prior+1.0,float(pc.n_max));
#else
        count=min(h1.y+1.0,float(pc.n_max));
#endif
    }
    history[id*2u]=vec4(H,v,m1,m2); history[id*2u+1u]=vec4(d2,count,1.0,replays);
    float indirect=max(H,0.0);
    pixels[id]=vec4(direct,indirect,direct+indirect,1);
}

#if ROLE==4
#ifndef GAMMA
#define GAMMA 4.0
#endif
#ifndef RADIUS
#define RADIUS 4
#endif
// Sample pass: fresh samples and the replayed difference d = mean(f1-f0) (0 when nothing changed).
void samples(uint id) {
    vec4 a0=anchors[id*3u], a1=anchors[id*3u+1u], a2=anchors[id*3u+2u];
    if(a2.w!=1.0) { scratch[id]=vec4(0,0,-2,0); return; }
    vec3 x=a0.xyz, n=a1.xyz, xp=x, np=n; uint prim=floatBitsToUint(a0.w); int j=-1;
    if((pc.flags&NO_HISTORY)==0u) j=reproject(n,prim,a2.xy,xp,np);
    uint base=mix32(pc.seed^mix32(id)); float s1=0.0, sd=0.0, ss1=0.0;
    uint k=j<0 ? pc.k_new : pc.k;
    bool same_point=j>=0 && all(equal(xp,x)) && (pc.flags&GEOMETRY_CHANGED)==0u;
    bool same=j<0 || (same_point && (pc.flags&LIGHT_CHANGED)==0u);
    for(uint i=0u;i<k;++i) {
        uint stream=mix32(base+i); float f1,f0;
        if(same) { f1=path(false,p.light_pos_interval,x,n,prim,stream); f0=f1; }
        else if(same_point) { vec2 f=path_shared(x,n,prim,stream); f1=f.x; f0=f.y; }
        else { f1=path(false,p.light_pos_interval,x,n,prim,stream); f0=path(true,q.light_pos_interval,xp,np,prim,stream); }
        s1+=f1; sd+=f1-f0; ss1+=f1*f1;
    }
    scratch[id]=vec4(s1/float(k), same ? 0.0 : sd/float(k), float(j), ss1/float(k));
}
// Combine pass: geometry-aware box filter of the replay difference only (radiance is never
// filtered), then H = (1-w) f1 + w (H_{t-1} + filtered difference).
void combine(uint id) {
    vec4 a0=anchors[id*3u], a1=anchors[id*3u+1u], a2=anchors[id*3u+2u], c=scratch[id];
    if(a2.w!=1.0) { pixels[id]=vec4(0,0,0,1); history[id*2u]=vec4(0); history[id*2u+1u]=vec4(0); return; }
    float direct=a2.z, H, v, m1, m2, dd=0.0, count, replays=0.0;
    if(c.z<0.0) { H=c.x; m1=c.x; m2=c.w; v=1.0/float(pc.k_new); count=1.0; }
    else {
        uint j=uint(c.z); vec4 h0=previous_history[j*2u], h1=previous_history[j*2u+1u];
        uint w=p.counts.y, h=p.counts.z; int cx=int(id%w), cy=int(id/w);
        vec3 x=a0.xyz, n=a1.xyz; uint inst=floatBitsToUint(a1.w);
        float dist=length(x-p.camera_pos_near.xyz), tol=4.0*float(RADIUS)*dist*p.camera_right_tan_x.w/float(w);
        float sum=0.0, num=0.0, fsum=0.0; bool changed=false;
        for(int dy=-RADIUS;dy<=RADIUS;dy++)for(int dx=-RADIUS;dx<=RADIUS;dx++) {
            int ox=cx+dx, oy=cy+dy; if(ox<0||oy<0||ox>=int(w)||oy>=int(h)) continue;
            uint o=uint(oy)*w+uint(ox); vec4 co=scratch[o]; if(co.z<0.0) continue;
            vec4 b0=anchors[o*3u], b1=anchors[o*3u+1u];
            if(floatBitsToUint(b1.w)!=inst || dot(b1.xyz,n)<0.95 || abs(dot(n,b0.xyz-x))>tol) continue;
            sum+=co.y; fsum+=co.x; num+=1.0; changed=changed||co.y!=0.0;
        }
        float D=num>0.0 ? sum/num : c.y;
        uint tile=(id/w/16u)*((w+15u)/16u)+(id%w)/16u;
        bool moved=(pc.flags&(GEOMETRY_CHANGED|LIGHT_CHANGED))!=0u || !all(equal(a0.xyz,a0.xyz));
        float r=moved ? tile_ratio[tile] : 0.0, hv=h0.y;
        float wt=clamp((1.0-0.5*r)/(1.0+float(pc.k)*hv),0.0,1.0-1.0/float(pc.n_max));
        // A filtered difference is biased where the change has edges, and that bias is
        // amplified by w/(1-w) in the history; limit the history where the change is large.
        // Relative to the window mean of fresh samples, not to this pixel's own values
        // (weights coupled to a pixel's own samples are biased).
        float rel=num>0.0 ? abs(D)/max(fsum/num,1.0e-12) : 0.0;
        wt=min(wt,1.0-clamp(GAMMA*rel,0.0,1.0));
        H=(1.0-wt)*c.x+wt*(h0.x+D);
        v=((1.0-wt)*(1.0-wt)+wt*r)/float(pc.k)+wt*wt*hv;
        dd=moved ? D*D : 0.0; replays=moved ? 1.0 : 0.0;
        m1=mix(h0.z,c.x,BETA); m2=mix(h0.w,c.w,BETA); count=min(h1.y+1.0,float(pc.n_max));
    }
    history[id*2u]=vec4(H,v,m1,m2); history[id*2u+1u]=vec4(dd,count,1.0,replays);
    float indirect=max(H,0.0);
    pixels[id]=vec4(direct,indirect,direct+indirect,1);
}
#endif
#if ROLE==3
// One replayed sample at the centre pixel of each 3x3 stratum (A-SVGF temporal gradient).
void gradients(uint id) {
    uint w=p.counts.y, sw=(w+2u)/3u, sx=id%sw, sy=id/sw; if(sy>=(p.counts.z+2u)/3u) return;
    uint px=min(sx*3u+1u,w-1u), py=min(sy*3u+1u,p.counts.z-1u), c=py*w+px; gradient[id]=-1.0;
    vec4 a0=anchors[c*3u], a1=anchors[c*3u+1u], a2=anchors[c*3u+2u];
    if(a2.w!=1.0 || (pc.flags&NO_HISTORY)!=0u) return;
    vec3 x=a0.xyz, n=a1.xyz, xp, np; uint prim=floatBitsToUint(a0.w);
    if(reproject(n,prim,a2.xy,xp,np)<0) return;
    bool same_point=all(equal(xp,x)) && (pc.flags&GEOMETRY_CHANGED)==0u;
    if(same_point && (pc.flags&LIGHT_CHANGED)==0u) { gradient[id]=0.0; return; }
    uint stream=mix32(mix32(pc.seed^mix32(c))^0x5bd1e995u); float f1,f0;
    if(same_point){ vec2 f=path_shared(x,n,prim,stream); f1=f.x; f0=f.y; }
    else { f1=path(false,p.light_pos_interval,x,n,prim,stream); f0=path(true,q.light_pos_interval,xp,np,prim,stream); }
    float m=max(f1,f0); gradient[id]=m>0.0 ? abs(f1-f0)/m : 0.0;
}
#endif
void main() {
    if(gl_GlobalInvocationID.x>=128u) return;
    uint id=pixel_index();
    if(id>=p.counts.y*p.counts.z) return;
#if ROLE==3
    if(pc.mode==0u) primary(id); else if(pc.mode==1u) gradients(id); else paths(id);
#elif ROLE==4
    if(pc.mode==0u) primary(id); else if(pc.mode==1u) samples(id); else combine(id);
#else
    if(pc.mode==0u) primary(id); else paths(id);
#endif
}

#version 460
#extension GL_EXT_ray_query : require
// 049 sequence roles PT / PTA / RTCV (ROLE 0/1/2, set at compile time).
// Transport is the unchanged n010 raw-PT estimator: grey rho=1, opaque two-sided
// surfaces, point-light NEE with soft falloff, finite vertex count, black background.
layout(local_size_x=32) in;
// 049 development defaults (frozen for 050 by registration)
// Pixels per bounded dispatch (host CHUNK must match).
#ifndef CHUNK_PIXELS
#define CHUNK_PIXELS 4096
#endif
#ifndef BILINEAR
#define BILINEAR 1
#endif
#ifndef CAMERA_REPROJECT
#define CAMERA_REPROJECT 1
#endif
#ifndef N_CAM
#define N_CAM 16
#endif
#ifndef THIN_BOOST
#define THIN_BOOST 1
#endif
#ifndef RANGE_SIGMA
#define RANGE_SIGMA 25
#endif
#ifndef NUM_MIN
#define NUM_MIN 0
#endif
#ifndef LINEAR_D
#define LINEAR_D 1
#endif
#ifndef GEOM_NO_REPLAY
#define GEOM_NO_REPLAY 1
#endif
#ifndef GEOM_SPARSE
#define GEOM_SPARSE 1
#endif
#ifndef SHRINK
#define SHRINK 1
#endif
#ifndef SPARSE_REPLAY
#define SPARSE_REPLAY 1
#endif
#ifndef SPR_CROSS
#define SPR_CROSS 0
#endif
#ifndef SPR_GAIN
#define SPR_GAIN 4
#endif
#ifndef KSLOTS
#define KSLOTS (max(pc.k,pc.k_new))
#endif
#ifndef SPR_RADIUS
#define SPR_RADIUS 1
#endif
#ifndef ADAPTIVE
#define ADAPTIVE 0
#endif
#ifndef REPLAYS
#define REPLAYS 65536
#endif
#ifndef GAMMA
#define GAMMA 4.0
#endif
#ifndef RADIUS
#define RADIUS 4
#endif
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
layout(std430,binding=9) buffer History { vec4 history[]; };
layout(std430,binding=10) readonly buffer PreviousHistory { vec4 previous_history[]; };
// previous-frame replay-difference/sample-variance ratio per 16x16 tile (host reduced)
layout(std430,binding=11) buffer TileRatio { float tile_ratio[]; };
// ROLE 3: A-SVGF-style normalized temporal gradient per 3x3 stratum (-1 = none)
layout(std430,binding=12) buffer Gradient { float gradient[]; };
// ROLE 4: per-pixel sample pass output (f1 mean, replay difference mean, previous pixel or -1, f1^2 mean)
layout(std430,binding=13) buffer Scratch { vec4 scratch[]; };
// ROLE 5 (PTR): 022 hit records and sources for the unchanged 018/022 quadratic operator
layout(std430,binding=14) buffer Hits { uint hits[]; };
layout(std430,binding=15) buffer Sources { float sources[]; };
layout(std430,binding=16) readonly buffer Stages { float stages[]; };
// ROLE 6 (SPR): per-pixel path samples: [2i]=secondary vertex z, primitive bits  [2i+1]=normal at z (facing the pixel), tail radiance L(z)
layout(std430,binding=17) buffer PathSamples { vec4 path_samples[]; };
layout(push_constant) uniform Push { uint mode; uint seed; uint start; uint k; uint k_new; uint vertices; uint flags; uint n_max; uint ratio_bits; uint batch_begin; uint batch_count; } pc;
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
vec3 first_z, first_nz; uint first_p; bool first_hit;  // first vertex of the last current-scene path
float path(bool old, vec4 light, vec3 position, vec3 normal, uint self, uint stream) {
    rng=stream; float indirect=0.0; vec3 origin=position, n=normal; uint s=self; if(!old) first_hit=false;
    for(uint vertex=1u;vertex<pc.vertices;++vertex) {
        float u=uniform01(), v=uniform01();
        vec3 wi=cosine_direction(n,u,v), next_position,next_normal; uint next_primitive; vec2 b;
        if(!trace_in(old,offset_position(origin,n),wi,1.0e30,s,next_primitive,next_position,next_normal,b)) break;
        if(vertex==1u && !old){ first_z=next_position; first_nz=next_normal; first_p=next_primitive; first_hit=true; }
        indirect+=direct_light(old,light,next_position,next_normal,next_primitive);
        origin=next_position; n=next_normal; s=next_primitive;
    }
    return indirect;
}
// Shared-geometry replay: one traced path, next-event estimation for both lights.
vec2 path_shared(vec3 position, vec3 normal, uint self, uint stream) {
    rng=stream; vec2 indirect=vec2(0); vec3 origin=position, n=normal; uint s=self; first_hit=false;
    for(uint vertex=1u;vertex<pc.vertices;++vertex) {
        float u=uniform01(), v=uniform01();
        vec3 wi=cosine_direction(n,u,v), next_position,next_normal; uint next_primitive; vec2 b;
        if(!trace_in(false,offset_position(origin,n),wi,1.0e30,s,next_primitive,next_position,next_normal,b)) break;
        if(vertex==1u){ first_z=next_position; first_nz=next_normal; first_p=next_primitive; first_hit=true; }
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
        anchors[id*3u]=vec4(0); anchors[id*3u+1u]=vec4(0); anchors[id*3u+2u]=vec4(0);
#if ROLE==5
        for(uint a=0u;a<8u;a++) hits[id*8u+a]=0u; hits[id*8u+3u]=0x7f800000u; hits[id*8u+4u]=hits[id*8u+5u]=hits[id*8u+6u]=INVALID;
#endif
        return;
    }
#if ROLE==5
    hits[id*8u]=floatBitsToUint(normal.x); hits[id*8u+1u]=floatBitsToUint(normal.y); hits[id*8u+2u]=floatBitsToUint(normal.z);
    hits[id*8u+3u]=floatBitsToUint(length(pos-p.camera_pos_near.xyz));
    hits[id*8u+4u]=triangles[prim].metadata.x; hits[id*8u+5u]=triangles[prim].metadata.y; hits[id*8u+6u]=triangles[prim].metadata.z; hits[id*8u+7u]=1u;
#endif
    float direct=direct_light(false,p.light_pos_interval,pos,normal,prim);
    anchors[id*3u]=vec4(pos,uintBitsToFloat(prim));
    anchors[id*3u+1u]=vec4(normal,uintBitsToFloat(triangles[prim].metadata.z));
    anchors[id*3u+2u]=vec4(b,direct,1.0);
}
// Previous-frame position x' of the same surface point (same triangle and barycentrics in the
// previous scene) and the previous pixel q whose stored anchor is coplanar with x' nearby; -1 if none.
// Bilinear history taps around x' that pass the same validity test (filled by reproject).
uint bil_j[4]; float bil_w[4]; uint bil_n;
bool history_tap(uint j, Triangle t, vec3 np, vec3 xp, float footprint, float z) {
    vec4 a0=previous_anchors[j*3u], a1=previous_anchors[j*3u+1u], a2=previous_anchors[j*3u+2u];
    if(a2.w!=1.0 || floatBitsToUint(a1.w)!=t.metadata.z) return false;
    vec3 tn=np; if(dot(tn,a1.xyz)<0.0) tn=-tn;
    return !(dot(tn,a1.xyz)<0.999 || abs(dot(tn,a0.xyz-xp))>1.0e-3*footprint+1.0e-6*z || length(a0.xyz-xp)>2.0*footprint);
}
int reproject(vec3 normal, uint prim, vec2 b, out vec3 xp, out vec3 np) {
    Triangle t=previous_triangles[prim]; bil_n=0u;
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
    float footprint=2.0*z*q.camera_right_tan_x.w/float(w);
    if(!history_tap(j,t,np,xp,footprint,z)) return -1;
    int x0=int(floor(fx)), y0=int(floor(fy)); float ax=fx-float(x0), ay=fy-float(y0), total=0.0;
    for(int c=0;c<4;c++){int xx=x0+(c&1), yy=y0+(c>>1);
        if(xx<0||yy<0||xx>=int(w)||yy>=int(h)) continue; uint o=uint(yy)*w+uint(xx);
        float wt=((c&1)!=0?ax:1.0-ax)*((c>>1)!=0?ay:1.0-ay); if(wt<=0.0||!history_tap(o,t,np,xp,footprint,z)) continue;
        bil_j[bil_n]=o; bil_w[bil_n]=wt; bil_n++; total+=wt;}
    if(total>0.0){ for(uint c=0u;c<bil_n;c++) bil_w[c]/=total; } else { bil_j[0]=j; bil_w[0]=1.0; bil_n=1u; }
    return int(j);
}
// History at x': bilinear blend of the valid taps (BILINEAR) or the nearest valid pixel.
void history_at(int j, out vec4 h0, out vec4 h1) {
#if BILINEAR
    h0=vec4(0); h1=vec4(0);
    for(uint c=0u;c<bil_n;c++){ h0+=bil_w[c]*previous_history[bil_j[c]*2u]; h1+=bil_w[c]*previous_history[bil_j[c]*2u+1u]; }
#else
    h0=previous_history[uint(j)*2u]; h1=previous_history[uint(j)*2u+1u];
#endif
}
void paths(uint id) {
    vec4 a0=anchors[id*3u], a1=anchors[id*3u+1u], a2=anchors[id*3u+2u];
    if(a2.w!=1.0) { pixels[id]=vec4(0,0,0,1); history[id*2u]=vec4(0); history[id*2u+1u]=vec4(0); return; }
    vec3 x=a0.xyz, n=a1.xyz; uint prim=floatBitsToUint(a0.w); float direct=a2.z;
    vec3 xp=x, np=n; int j=-1;
#if ROLE!=0 && ROLE!=5
    if((pc.flags&NO_HISTORY)==0u) j=reproject(n,prim,a2.xy,xp,np);
#endif
    uint base=mix32(pc.seed^mix32(id));
    float H, v, m1, m2, d2, count, replays=0.0;
    if(j<0) {
        uint k=(ROLE==0||ROLE==5) ? pc.k : pc.k_new; float s=0.0, ss=0.0;
#if ROLE==0 || ROLE==5
        // Stateless roles accumulate large sample counts over several full-image batches
        // (one submission each) so every dispatch keeps the whole image in flight.
        if(pc.batch_begin>0u){ s=scratch[id].x; ss=scratch[id].y; }
        for(uint i=pc.batch_begin;i<min(pc.batch_begin+pc.batch_count,k);++i){ float f=path(false,p.light_pos_interval,x,n,prim,mix32(base+i)); s+=f; ss+=f*f; }
        if(pc.batch_begin+pc.batch_count<k){ scratch[id]=vec4(s,ss,0,0); return; }
#else
        for(uint i=0u;i<k;++i){ float f=path(false,p.light_pos_interval,x,n,prim,mix32(base+i)); s+=f; ss+=f*f; }
#endif
        H=s/float(k); m1=H; m2=ss/float(k); v=1.0/float(k); d2=0.0; count=1.0;
    } else {
        vec4 h0, h1; history_at(j,h0,h1);
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
#if ROLE==5
    sources[id]=H;
#endif
}
#if ROLE==5
void composite(uint id) { float direct=anchors[id*3u+2u].z, indirect=stages[2u*p.counts.y*p.counts.z+id]; pixels[id]=vec4(direct,indirect,direct+indirect,1); }
#endif

#if ROLE==4 || ROLE==7
// Sample pass: fresh samples and the replayed difference d = mean(f1-f0) (0 when nothing changed).
void samples(uint id) {
    vec4 a0=anchors[id*3u], a1=anchors[id*3u+1u], a2=anchors[id*3u+2u];
    if(a2.w!=1.0) { scratch[id]=vec4(0,0,-2,0); return; }
    vec3 x=a0.xyz, n=a1.xyz, xp=x, np=n; uint prim=floatBitsToUint(a0.w); int j=-1;
    if((pc.flags&NO_HISTORY)==0u) j=reproject(n,prim,a2.xy,xp,np);
    uint base=mix32(pc.seed^mix32(id)); float s1=0.0, sd=0.0, ss1=0.0;
    uint k=j<0 ? pc.k_new : pc.k; uint yprim=prim, boost=1u;
#if THIN_BOOST>1
    // Thin features detected in the previous frame (few coplanar neighbours) get THIN_BOOST x samples.
    if(j>=0 && previous_history[uint(j)*2u+1u].z>1.5) boost=uint(THIN_BOOST);
    k*=boost;
#endif
#if ADAPTIVE
    // Pixels whose propagated history variance v (previous frame, data-independent of this
    // pixel's samples) is still above 1/(2k) get up to 4x samples.
    if(j>=0){ float hv=previous_history[uint(j)*2u].y; boost=uint(clamp(ceil(2.0*hv*float(pc.k)),1.0,4.0)); k*=boost; }
#endif
#ifdef REPLAY_FROM_ANCHOR_Y
    // Replay from the previous pixel's anchor y (the point H_{t-1} estimates): the filtered
    // difference then also corrects the sub-pixel anchor shift under camera motion.
    if(j>=0){ vec4 b0=previous_anchors[uint(j)*3u], b1=previous_anchors[uint(j)*3u+1u]; xp=b0.xyz; np=b1.xyz; yprim=floatBitsToUint(b0.w); }
#endif
    bool same_point=j>=0 && all(equal(xp,x)) && (pc.flags&GEOMETRY_CHANGED)==0u;
    bool same=j<0 || (same_point && (pc.flags&LIGHT_CHANGED)==0u);
#if CAMERA_REPROJECT
    // Camera-only frames: the scene radiance did not change, so the history is reprojected
    // (bilinear) like established accumulation, without a replay (049 dev: anchor-shift
    // replays were too decorrelated to pay for their cost).
    if((pc.flags&(GEOMETRY_CHANGED|LIGHT_CHANGED))==0u) same=true;
#endif
#if GEOM_NO_REPLAY
    if((pc.flags&LIGHT_CHANGED)==0u) same=true;  // geometry changes: accumulate without replay
#endif
#if GEOM_SPARSE>1
    // Geometry-only changes: one pixel in GEOM_SPARSE (rotating pattern) replays; the filtered,
    // shrunk difference of the replaying pixels corrects and limits the history of its window.
    if((pc.flags&LIGHT_CHANGED)==0u && !same){
        bool replayer=((id%p.counts.y)+(id/p.counts.y)*3u+pc.seed)%uint(GEOM_SPARSE)==0u;
        if(!replayer){ boost|=4u; same=true; } }
#endif
    // The first REPLAYS samples are replayed (default: all). Replaying fewer was tried in 049
    // development and lost more quality than it saved cost.
    uint r=min(uint(REPLAYS),k);
#if SPARSE_REPLAY>1
    // Sparse replays: only one pixel in SPARSE_REPLAY (rotating pattern) replays; the filtered
    // difference D is formed from the replaying pixels only.
    bool replayer=((id%p.counts.y)+(id/p.counts.y)*3u+pc.seed)%uint(SPARSE_REPLAY)==0u;
    if(!replayer && !same){ boost|=4u; same=true; }
#endif
    for(uint i=0u;i<k;++i) {
        uint stream=mix32(base+i); float f1,f0;
        if(same || i>=r) { f1=path(false,p.light_pos_interval,x,n,prim,stream); f0=f1; }
        else if(same_point) { vec2 f=path_shared(x,n,prim,stream); f1=f.x; f0=f.y; }
        else { f1=path(false,p.light_pos_interval,x,n,prim,stream); f0=path(true,q.light_pos_interval,xp,np,yprim,stream); }
        s1+=f1; sd+=f1-f0; ss1+=f1*f1;
#if ROLE==7
        uint slot=(id*KSLOTS+i)*2u;
        if(first_hit){ path_samples[slot]=vec4(first_z,uintBitsToFloat(first_p)); path_samples[slot+1u]=vec4(first_nz,f1); }
        else { path_samples[slot]=vec4(0); path_samples[slot+1u]=vec4(0); }
#endif
    }
    scratch[id]=vec4(s1/float(k), same ? 0.0 : sd/float(r), j<0 ? -1.0 : float(uint(j)*8u+boost), ss1/float(k));
}
#if ROLE==7
float area_pdf7(vec3 y, vec3 ny, vec3 z, vec3 nz) {
    vec3 d=z-y; float d2=dot(d,d); if(d2<=0.0) return 0.0; vec3 w=d*inversesqrt(d2);
    float cy=dot(ny,w), cz=-dot(nz,w); return (cy>0.0 && cz>0.0) ? cy*cz/(3.14159265358979323846*d2) : 0.0;
}
// Spatial path reuse: multi-sample balance-heuristic estimate of this pixel's indirect from the
// current-scene paths of the coplanar neighbours, reconnected at their secondary vertex z
// (two-sided Lambert: L(z->x)=L(z->y) on the same side); one visibility ray per reused path.
// Other techniques' pdfs ignore their visibility to z (approximation). Replaces scratch.x.
void spr(uint id) {
    vec4 a0=anchors[id*3u], a1=anchors[id*3u+1u], a2=anchors[id*3u+2u]; vec4 c=scratch[id];
    if(a2.w!=1.0 || c.z<-1.5) return;
    vec3 x=a0.xyz, n=a1.xyz; uint inst=floatBitsToUint(a1.w), prim=floatBitsToUint(a0.w);
    uint w=p.counts.y, h=p.counts.z; int cx=int(id%w), cy=int(id/w);
    uint tech[(2*SPR_RADIUS+1)*(2*SPR_RADIUS+1)]; float tn[(2*SPR_RADIUS+1)*(2*SPR_RADIUS+1)]; uint nt=0u;
    for(int dy=-SPR_RADIUS;dy<=SPR_RADIUS;dy++)for(int dx=-SPR_RADIUS;dx<=SPR_RADIUS;dx++){int ox=cx+dx, oy=cy+dy;
#if SPR_CROSS
        if(dx!=0 && dy!=0) continue;  // cross neighbourhood: 1+4*SPR_RADIUS techniques
#endif
        if(ox<0||oy<0||ox>=int(w)||oy>=int(h)) continue; uint o=uint(oy)*w+uint(ox); vec4 b1=anchors[o*3u+1u]; vec4 so=scratch[o];
        if(anchors[o*3u+2u].w!=1.0 || so.z<-1.5 || floatBitsToUint(b1.w)!=inst || dot(b1.xyz,n)<0.95) continue;
        tech[nt]=o; tn[nt]=so.z<0.0 ? float(pc.k_new) : float(pc.k*((uint(so.z)%8u)&3u)); nt++;}
    float sum=0.0;
    for(uint t=0u;t<nt;t++){ uint o=tech[t];
        for(uint i=0u;i<uint(tn[t]);i++){ uint slot=(o*KSLOTS+i)*2u; vec4 s0=path_samples[slot], s1=path_samples[slot+1u];
            if(s0==vec4(0) && s1==vec4(0)) continue;
            vec3 z=s0.xyz, nz=s1.xyz; float px=area_pdf7(x,n,z,nz); if(px<=0.0) continue;
            vec3 d=z-x; float dist=length(d);
            if(o!=id && blocked_in(false,offset_position(x,n),d/dist,dist*(1.0-1.0e-4),prim)) continue;
            float den=0.0; for(uint u2=0u;u2<nt;u2++){ uint q2=tech[u2]; den+=tn[u2]*area_pdf7(anchors[q2*3u].xyz,anchors[q2*3u+1u].xyz,z,nz); }
            if(den>0.0) sum+=s1.w*px/den;
        } }
    scratch[id].x=sum;
}
#endif
// Combine pass: geometry-aware box filter of the replay difference only (radiance is never
// filtered), then H = (1-w) f1 + w (H_{t-1} + filtered difference).
void combine(uint id) {
    vec4 a0=anchors[id*3u], a1=anchors[id*3u+1u], a2=anchors[id*3u+2u], c=scratch[id];
    if(a2.w!=1.0) { pixels[id]=vec4(0,0,0,1); history[id*2u]=vec4(0); history[id*2u+1u]=vec4(0); return; }
    float direct=a2.z, H, v, m1, m2, dd=0.0, count, replays=0.0, thin_flag=1.0;
    if(c.z<0.0) { H=c.x; m1=c.x; m2=c.w; count=1.0;
#if ROLE==7
        v=1.0/(float(pc.k_new)*float(SPR_GAIN));
#else
        v=1.0/float(pc.k_new);
#endif
    }
    else {
        uint j=uint(c.z)/8u; float kp=float(pc.k*((uint(c.z)%8u)&3u));
#if ROLE==7
        float kp_fresh=kp*float(SPR_GAIN);  // reused fresh estimate counts as SPR_GAIN x samples
#else
        float kp_fresh=kp;
#endif
        vec4 h0=previous_history[j*2u], h1=previous_history[j*2u+1u];
        bool camera_only=(pc.flags&(GEOMETRY_CHANGED|LIGHT_CHANGED))==0u && (pc.flags&CAMERA_CHANGED)!=0u;
#if GEOM_NO_REPLAY && GEOM_SPARSE<=1
        bool geom_only=(pc.flags&LIGHT_CHANGED)==0u && (pc.flags&GEOMETRY_CHANGED)!=0u;
#else
        bool geom_only=false;
#endif
#if CAMERA_REPROJECT
        if(camera_only){ vec3 xp0,np0; if(reproject(a1.xyz,floatBitsToUint(a0.w),a2.xy,xp0,np0)>=0) history_at(int(j),h0,h1); }
#endif
#ifndef REPLAY_FROM_ANCHOR_Y
        // x' replays estimate the change at the same surface point; the history at x' is resampled.
        { vec3 xp0,np0; if(reproject(a1.xyz,floatBitsToUint(a0.w),a2.xy,xp0,np0)>=0) history_at(int(j),h0,h1); }
#endif
        uint w=p.counts.y, h=p.counts.z; int cx=int(id%w), cy=int(id/w);
        vec3 x=a0.xyz, n=a1.xyz; uint inst=floatBitsToUint(a1.w);
        float dist=length(x-p.camera_pos_near.xyz), tol=4.0*float(RADIUS)*dist*p.camera_right_tan_x.w/float(w);
        float sum=0.0, num=0.0, fsum=0.0, sq=0.0, w2=0.0; bool changed=false;
#if LINEAR_D
        // Local regression of the replay difference on the anchor shift (x - y) in the tangent
        // plane: d ~ a + g.(x - y). a estimates the scene change, g the spatial gradient, so each
        // pixel is corrected for its own sub-pixel shift instead of the window-mean shift.
        vec3 helper=abs(n.z)<0.999 ? vec3(0,0,1) : vec3(0,1,0), tu=normalize(cross(helper,n)), tv=cross(n,tu);
        float fp=max(2.0*dist*p.camera_right_tan_x.w/float(w),1.0e-12);
        float s00=0.0,s01=0.0,s02=0.0,s11=0.0,s12=0.0,s22=0.0,r0=0.0,r1=0.0,r2=0.0;
#endif
        // Nothing changed this frame: every difference is exactly zero, skip the filter.
        if((pc.flags&(GEOMETRY_CHANGED|LIGHT_CHANGED|CAMERA_CHANGED))!=0u)
        for(int dy=-RADIUS;dy<=RADIUS;dy++)for(int dx=-RADIUS;dx<=RADIUS;dx++) {
            int ox=cx+dx, oy=cy+dy; if(ox<0||oy<0||ox>=int(w)||oy>=int(h)) continue;
            uint o=uint(oy)*w+uint(ox); vec4 co=scratch[o]; if(co.z<0.0 || ((uint(co.z)%8u)&4u)!=0u) continue;
            vec4 b0=anchors[o*3u], b1=anchors[o*3u+1u];
            if(floatBitsToUint(b1.w)!=inst || dot(b1.xyz,n)<0.95 || abs(dot(n,b0.xyz-x))>tol) continue;
#if RANGE_SIGMA>0
            // Range weight from the previous-frame history (smooth): neighbours whose radiance
            // level differs strongly are unlikely to share this pixel's change.
            float hq=previous_history[(uint(co.z)/8u)*2u].x, hp=h0.x;
            float wr=exp(-abs(hq-hp)/(float(RANGE_SIGMA)*0.01*max(0.5*(abs(hq)+abs(hp)),1.0e-12)));
#else
            float wr=1.0;
#endif
            sum+=wr*co.y; fsum+=wr*co.x; num+=wr; sq+=wr*co.y*co.y; w2+=wr*wr; changed=changed||co.y!=0.0;
#if LINEAR_D
            vec3 sh=b0.xyz-previous_anchors[(uint(co.z)/8u)*3u].xyz; float u=dot(sh,tu)/fp, vv=dot(sh,tv)/fp;
            s00+=wr; s01+=wr*u; s02+=wr*vv; s11+=wr*u*u; s12+=wr*u*vv; s22+=wr*vv*vv; r0+=wr*co.y; r1+=wr*co.y*u; r2+=wr*co.y*vv;
#endif
        }
        float D=num>0.0 ? sum/num : c.y, A=D;
        // Thin features (few coplanar neighbours): the box mean is biased across a sharp change;
        // fall back to this pixel's own unbiased replay difference.
        bool thin=num<float(NUM_MIN); if(thin) thin_flag=2.0;
        if(thin){ D=c.y; A=c.y; }
#if LINEAR_D
        if(!thin && num>=6.0) {
            float lam=0.25*num; s11+=lam; s22+=lam;  // ridge on the gradient terms only
            float c00=s11*s22-s12*s12, c01=s02*s12-s01*s22, c02=s01*s12-s02*s11;
            float det=s00*c00+s01*c01+s02*c02;
            if(abs(det)>1.0e-20) {
                float ga=(r0*c00+r1*c01+r2*c02)/det;
                float gu=(r0*c01+r1*(s00*s22-s02*s02)+r2*(s01*s02-s00*s12))/det;
                float gv=(r0*c02+r1*(s01*s02-s00*s12)+r2*(s00*s11-s01*s01))/det;
                vec3 sh=x-previous_anchors[j*3u].xyz;
                A=ga; D=ga+gu*dot(sh,tu)/fp+gv*dot(sh,tv)/fp;
            }
        }
#endif
        uint tile=(id/w/16u)*((w+15u)/16u)+(id%w)/16u;
        bool moved=(pc.flags&(GEOMETRY_CHANGED|LIGHT_CHANGED|CAMERA_CHANGED))!=0u;
        float r=moved ? tile_ratio[tile] : 0.0, hv=h0.y;
#if SHRINK
        // Wiener shrinkage of the correction: where the filtered change is not significant
        // against its own noise, keep the history (accumulation-like lag) instead of injecting
        // the replay noise; significant changes are corrected in full.
        if(num>0.0 && !thin){ float m=sum/num, noise=max(sq/num-m*m,0.0)*w2/(num*num);
            float beta=D*D/(D*D+noise+1.0e-30); D*=beta; A*=beta; r*=beta*beta; }
#endif
#if CAMERA_REPROJECT
        if(camera_only) r=0.0;
#endif
        if(geom_only) r=0.0;
        // r: per-replay variance of the filtered difference in units of the per-sample variance;
        // with re replays per pixel this minimizes (1-w)^2/k + w r/re + w^2 v.
        float re=min(float(REPLAYS),kp);
        float wt=clamp((1.0-0.5*kp_fresh*r/re)/(1.0+kp_fresh*hv),0.0,1.0-1.0/float(pc.n_max));
        // A filtered difference is biased where the change has edges, and that bias is
        // amplified by w/(1-w) in the history; limit the history where the change is large.
        // Relative to the window mean of fresh samples, not to this pixel's own values
        // (weights coupled to a pixel's own samples are biased).
        float rel=num>0.0 ? abs(A)/max(fsum/num,1.0e-12) : 0.0;
        wt=min(wt,1.0-clamp(GAMMA*rel,0.0,1.0));
#if CAMERA_REPROJECT
        if(camera_only) wt=min(wt,1.0-1.0/float(N_CAM));  // reprojection drift bound, as in accumulation
#endif
        H=(1.0-wt)*c.x+wt*(h0.x+D);
        v=(1.0-wt)*(1.0-wt)/kp_fresh+wt*r/re+wt*wt*hv;
        dd=moved ? D*D : 0.0; replays=moved ? 1.0 : 0.0;
        m1=mix(h0.z,c.x,BETA); m2=mix(h0.w,c.w,BETA); count=min(h1.y+1.0,float(pc.n_max));
    }
    history[id*2u]=vec4(H,v,m1,m2); history[id*2u+1u]=vec4(dd,count,thin_flag,replays);
    float indirect=max(H,0.0);
    pixels[id]=vec4(direct,indirect,direct+indirect,1);
}
#endif

#if ROLE==6
#ifndef SPR_RADIUS
#define SPR_RADIUS 1
#endif
// Own paths: store the secondary vertex z and the tail estimate L(z) (all NEE from z onwards).
void spr_paths(uint id) {
    vec4 a0=anchors[id*3u], a1=anchors[id*3u+1u], a2=anchors[id*3u+2u]; uint k=pc.k;
    for(uint i=0u;i<k;++i){ path_samples[(id*k+i)*2u]=vec4(0); path_samples[(id*k+i)*2u+1u]=vec4(0); }
    if(a2.w!=1.0) return;
    vec3 x=a0.xyz, n=a1.xyz; uint prim=floatBitsToUint(a0.w); uint base=mix32(pc.seed^mix32(id));
    for(uint i=0u;i<k;++i){
        rng=mix32(base+i); float u=uniform01(), v=uniform01();
        vec3 wi=cosine_direction(n,u,v), z, nz; uint pz; vec2 b;
        if(!trace_in(false,offset_position(x,n),wi,1.0e30,prim,pz,z,nz,b)) continue;
        float tail=direct_light(false,p.light_pos_interval,z,nz,pz);
        if(pc.vertices>2u){ vec3 origin=z, nn=nz; uint sp=pz;
            for(uint vertex=2u;vertex<pc.vertices;++vertex){
                float uu=uniform01(), vv=uniform01(); vec3 w2=cosine_direction(nn,uu,vv), np2, nn2; uint p2; vec2 b2;
                if(!trace_in(false,offset_position(origin,nn),w2,1.0e30,sp,p2,np2,nn2,b2)) break;
                tail+=direct_light(false,p.light_pos_interval,np2,nn2,p2); origin=np2; nn=nn2; sp=p2; } }
        path_samples[(id*k+i)*2u]=vec4(z,uintBitsToFloat(pz)); path_samples[(id*k+i)*2u+1u]=vec4(nz,tail);
    }
}
float area_pdf(vec3 y, vec3 ny, vec3 z, vec3 nz) {
    vec3 d=z-y; float d2=dot(d,d); if(d2<=0.0) return 0.0; vec3 w=d*inversesqrt(d2);
    float cy=dot(ny,w), cz=-dot(nz,w); return (cy>0.0 && cz>0.0) ? cy*cz/(3.14159265358979323846*d2) : 0.0;
}
// Multi-sample balance-heuristic reuse of the neighbours' paths through their secondary vertex z
// (reconnection; two-sided Lambert so L(z->x)=L(z->y) on the same side). Other techniques'
// pdfs ignore their visibility to z (approximation, small bias near occluders).
void spr_reuse(uint id) {
    vec4 a0=anchors[id*3u], a1=anchors[id*3u+1u], a2=anchors[id*3u+2u];
    if(a2.w!=1.0){ pixels[id]=vec4(0,0,0,1); return; }
    vec3 x=a0.xyz, n=a1.xyz; uint inst=floatBitsToUint(a1.w), prim=floatBitsToUint(a0.w); float direct=a2.z;
    uint w=p.counts.y, h=p.counts.z; int cx=int(id%w), cy=int(id/w); uint k=pc.k;
    uint tech[(2*SPR_RADIUS+1)*(2*SPR_RADIUS+1)]; uint nt=0u;
    for(int dy=-SPR_RADIUS;dy<=SPR_RADIUS;dy++)for(int dx=-SPR_RADIUS;dx<=SPR_RADIUS;dx++){int ox=cx+dx, oy=cy+dy;
        if(ox<0||oy<0||ox>=int(w)||oy>=int(h)) continue; uint o=uint(oy)*w+uint(ox); vec4 b1=anchors[o*3u+1u];
        if(anchors[o*3u+2u].w!=1.0 || floatBitsToUint(b1.w)!=inst || dot(b1.xyz,n)<0.95) continue; tech[nt++]=o;}
    float sum=0.0;
    for(uint t=0u;t<nt;t++){ uint o=tech[t];
        for(uint i=0u;i<k;i++){ vec4 s0=path_samples[(o*k+i)*2u], s1=path_samples[(o*k+i)*2u+1u]; if(s1.w==0.0 && s0==vec4(0)) continue;
            vec3 z=s0.xyz, nz=s1.xyz; float L=s1.w;
            float px=area_pdf(x,n,z,nz); if(px<=0.0) continue;
            vec3 d=z-x; float dist=length(d);
            if(o!=id && blocked_in(false,offset_position(x,n),d/dist,dist*(1.0-1.0e-4),prim)) continue;
            float den=0.0; for(uint u2=0u;u2<nt;u2++){ uint q2=tech[u2]; den+=area_pdf(anchors[q2*3u].xyz,anchors[q2*3u+1u].xyz,z,nz); }
            sum+=L*px/den;  // F_x(z)/sum_l p_l(z), with F_x = L*G_x/pi = L*p_x(z); each technique has k samples
        } }
    float indirect=sum/float(k);
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

#if ROLE==2 || ROLE==4 || ROLE==7
// GPU reduction (one invocation per 16x16 tile) of this frame's replay-difference and sample
// variance into the ratio the next frame uses; tiles with <16 replayed pixels keep their value.
void ratios(uint t) {
    uint w=p.counts.y, h=p.counts.z, tx=(w+15u)/16u, ty=(h+15u)/16u; if(t>=tx*ty) return;
    uint x0=(t%tx)*16u, y0=(t/tx)*16u; float sd=0.0, sv=0.0, n=0.0;
    for(uint y=y0;y<min(y0+16u,h);y++)for(uint x=x0;x<min(x0+16u,w);x++){uint j=y*w+x; vec4 h0=history[j*2u], h1=history[j*2u+1u];
        if(h1.w>0.0){sd+=h1.x; sv+=max(h0.w-h0.z*h0.z,0.0); n+=1.0;}}
    if(n>=16.0 && sv>0.0) tile_ratio[t]=min(sd/sv,2.0);
}
#endif
void main() {
    if(gl_GlobalInvocationID.x>=uint(CHUNK_PIXELS)) return;
    uint id=pixel_index();
    if(id>=p.counts.y*p.counts.z) return;
#if ROLE==3
    if(pc.mode==0u) primary(id); else if(pc.mode==1u) gradients(id); else paths(id);
#elif ROLE==7
    if(pc.mode==0u) primary(id); else if(pc.mode==1u) samples(id); else if(pc.mode==2u) spr(id); else if(pc.mode==3u) combine(id); else ratios(id);
#elif ROLE==6
    if(pc.mode==0u) primary(id); else if(pc.mode==1u) spr_paths(id); else spr_reuse(id);
#elif ROLE==5
    if(pc.mode==0u) primary(id); else if(pc.mode==1u) paths(id); else composite(id);
#elif ROLE==4
    if(pc.mode==0u) primary(id); else if(pc.mode==1u) samples(id); else if(pc.mode==2u) combine(id); else ratios(id);
#elif ROLE==2
    if(pc.mode==0u) primary(id); else if(pc.mode==1u) paths(id); else ratios(id);
#else
    if(pc.mode==0u) primary(id); else paths(id);
#endif
}

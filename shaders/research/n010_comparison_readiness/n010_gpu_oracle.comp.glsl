#version 460
#extension GL_ARB_gpu_shader_fp64 : require
#extension GL_ARB_gpu_shader_int64 : require
// Experimental independent oracle port. Not eligible until Amendment 7 gates.
layout(local_size_x=64) in;
struct Triangle { dvec4 a,b,c,rho,emit,normal; };
struct Node { dvec4 lo,hi; }; // lo.w: first leaf index or right child; hi.w: count
struct Point { dvec4 position,intensity; };
struct Primary { dvec4 origin,normal,rho,direct,emit; u64vec4 counters; };
struct Stats { dvec4 sum[4]; dvec4 sum2[4]; u64vec4 counters; };
layout(std430,binding=0) readonly buffer Triangles { Triangle triangles[]; };
layout(std430,binding=1) readonly buffer Nodes { Node nodes[]; };
layout(std430,binding=2) readonly buffer Order { uint order[]; };
layout(std430,binding=3) readonly buffer Lights { Point points[]; };
layout(std430,binding=4) readonly buffer Net { uint net[]; };
layout(std430,binding=5) readonly buffer Primaries { Primary primary[]; };
layout(std430,binding=6) buffer Output { Stats stats[]; };
layout(std430,binding=7) readonly buffer Parameters { dvec4 physical; uvec4 sizes; uvec4 interval; uvec4 seedWords; };
layout(std430,binding=8) buffer Faults { uint faults; };
const uint MISS=0xffffffffu;
const double PI=3.14159265358979323846264338327950288LF;
double infinity() { return packDouble2x32(uvec2(0u,0x7ff00000u)); }
double dotd(dvec3 a,dvec3 b) { precise double value=(a.x*b.x+a.y*b.y)+a.z*b.z;return value; }
dvec3 crossd(dvec3 a,dvec3 b) { precise dvec3 value=dvec3(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x);return value; }
double lengthd(dvec3 a) { precise double value=sqrt(dotd(a,a));return value; }
dvec3 normalized(dvec3 a) { precise dvec3 value=a*(1.0LF/lengthd(a));return value; }
uint64_t mix64(uint64_t x) {
    x+=uint64_t(0x9e3779b97f4a7c15UL);
    x=(x^(x>>30))*uint64_t(0xbf58476d1ce4e5b9UL);
    x=(x^(x>>27))*uint64_t(0x94d049bb133111ebUL);
    return x^(x>>31);
}
double uniform01(uint pixel,uint sampleIndex,inout uint dim) {
    if(dim>=16u || sampleIndex>=262144u){atomicOr(faults,1u);return 0.5LF;}
    uint64_t seed=uint64_t(seedWords.x)|(uint64_t(seedWords.y)<<32);
    uint shift=uint(mix64(seed^mix64(uint64_t(pixel))^mix64(uint64_t(dim)+uint64_t(0x4e303130UL))));
    uint value=net[sampleIndex*16u+dim++]^shift;
    precise double result=(double(value)+0.5LF)*2.3283064365386962890625e-10LF;
    return result;
}
// Small-domain Taylor polynomials (sin degree 19, cos degree 20). The split
// pi/2 reduction uses a 33-bit head, binary64 tail and second residual.
// Numerical conformance against CPU libm is mandatory; no exact-byte claim.
dvec2 sincosd(double phi) {
    int q=int(floor(phi*0.63661977236758134308LF+0.5LF));
    precise double r=((phi-double(q)*1.57079632673412561417LF)-double(q)*6.07710050650619224932e-11LF)-double(q)*2.02226624879595063154e-21LF;
    precise double z=r*r;
    precise double s=r+r*z*(-1.0LF/6.0LF+z*(1.0LF/120.0LF+z*(-1.0LF/5040.0LF+z*(1.0LF/362880.0LF+z*(-1.0LF/39916800.0LF+z*(1.0LF/6227020800.0LF+z*(-1.0LF/1307674368000.0LF+z*(1.0LF/355687428096000.0LF+z*(-1.0LF/121645100408832000.0LF)))))))));
    precise double c=1.0LF+z*(-1.0LF/2.0LF+z*(1.0LF/24.0LF+z*(-1.0LF/720.0LF+z*(1.0LF/40320.0LF+z*(-1.0LF/3628800.0LF+z*(1.0LF/479001600.0LF+z*(-1.0LF/87178291200.0LF+z*(1.0LF/20922789888000.0LF+z*(-1.0LF/6402373705728000.0LF+z*(1.0LF/2432902008176640000.0LF))))))))));
    switch(q&3){case 0:return dvec2(s,c);case 1:return dvec2(c,-s);case 2:return dvec2(-s,-c);default:return dvec2(-c,s);}
}
dvec3 cosine_sample(dvec3 n,double u1,double u2) {
    precise double r=sqrt(u1),phi=2.0LF*PI*u2;
    dvec2 sc=sincosd(phi);
    precise double lx=r*sc.y,ly=r*sc.x,lz=sqrt(max(0.0LF,1.0LF-u1));
    double signbit=(unpackDouble2x32(n.z).y&0x80000000u)!=0u?-1.0LF:1.0LF;
    precise double a=-1.0LF/(signbit+n.z),b=n.x*n.y*a;
    precise dvec3 t=dvec3(1.0LF+signbit*n.x*n.x*a,signbit*b,-signbit*n.x);
    precise dvec3 s=dvec3(b,signbit+n.y*n.y*a,-n.y);
    precise dvec3 value=(t*lx+s*ly)+n*lz;
    return normalized(value);
}
struct Watertight { ivec3 axes; dvec3 scales,origin; };
Watertight watertight(dvec3 origin,dvec3 direction) {
    dvec3 ad=abs(direction);int kz=ad.x>ad.y?(ad.x>ad.z?0:2):(ad.y>ad.z?1:2);
    int kx=(kz+1)%3,ky=(kx+1)%3;
    if(direction[kz]<0.0LF){int tmp=kx;kx=ky;ky=tmp;}
    precise dvec3 scales=dvec3(direction[kx]/direction[kz],direction[ky]/direction[kz],1.0LF/direction[kz]);
    return Watertight(ivec3(kx,ky,kz),scales,origin);
}
double intersect(Watertight wr,Triangle tri) {
    precise dvec3 a=tri.a.xyz-wr.origin,b=tri.b.xyz-wr.origin,c=tri.c.xyz-wr.origin;
    int kx=wr.axes.x,ky=wr.axes.y,kz=wr.axes.z;
    precise double ax=a[kx]-wr.scales.x*a[kz],ay=a[ky]-wr.scales.y*a[kz];
    precise double bx=b[kx]-wr.scales.x*b[kz],by=b[ky]-wr.scales.y*b[kz];
    precise double cx=c[kx]-wr.scales.x*c[kz],cy=c[ky]-wr.scales.y*c[kz];
    precise double u=cx*by-cy*bx,v=ax*cy-ay*cx,w=bx*ay-by*ax;
    if((u<0.0LF||v<0.0LF||w<0.0LF)&&(u>0.0LF||v>0.0LF||w>0.0LF))return infinity();
    precise double det=(u+v)+w;if(det==0.0LF)return infinity();
    precise double scaled=(u*(wr.scales.z*a[kz])+v*(wr.scales.z*b[kz]))+w*(wr.scales.z*c[kz]);
    precise double t=scaled/det;return t>0.0LF?t:infinity();
}
bool slab(Node node,dvec3 origin,dvec3 inv,double tmin,double tmax) {
    precise double t0=tmin,t1=tmax;
    for(int axis=0;axis<3;++axis){
        precise double tn=(node.lo[axis]-origin[axis])*inv[axis],tf=(node.hi[axis]-origin[axis])*inv[axis];
        if(isnan(tn)||isnan(tf)){if(origin[axis]<node.lo[axis]||origin[axis]>node.hi[axis])return false;continue;}
        if(tn>tf){double tmp=tn;tn=tf;tf=tmp;}
        tf*=1.0LF+8.8817841970012523233890533447265625e-16LF;
        t0=max(t0,tn);t1=min(t1,tf);if(t0>t1)return false;
    }
    return true;
}
struct Hit { double t; uint tri; };
Hit trace(dvec3 origin,dvec3 direction,double tmin,double limit,uint ignore,bool shadow) {
    Hit best=Hit(limit,MISS);if(sizes.y==0u)return Hit(infinity(),MISS);
    Watertight wr=watertight(origin,direction);
    precise dvec3 inv=dvec3(1.0LF/direction.x,1.0LF/direction.y,1.0LF/direction.z);
    uint stack[128];int sp=1;stack[0]=0u;
    while(sp>0){
        uint ni=stack[--sp];Node node=nodes[ni];if(!slab(node,origin,inv,tmin,best.t))continue;
        uint count=uint(node.hi.w),first=uint(node.lo.w);
        if(count>0u){for(uint k=first;k<first+count;++k){
            uint id=order[k];double t=intersect(wr,triangles[id]);
            if(id==ignore || !(t<infinity()) || !(t>tmin) || t>best.t)continue;
            if(shadow){if(t<limit)return Hit(t,id);continue;}
            if(best.tri==MISS || t<best.t || (t==best.t&&id<best.tri))best=Hit(t,id);
        }}else{if(sp+2>128){atomicOr(faults,2u);return Hit(infinity(),MISS);}stack[sp++]=first;stack[sp++]=ni+1u;}
    }
    if(best.tri==MISS)best.t=infinity();return best;
}
dvec3 nudge(Triangle tri,dvec3 p) {
    dvec3 v[3]=dvec3[3](tri.a.xyz,tri.b.xyz,tri.c.xyz);
    precise double mind=infinity(),maxedge=0.0LF;
    for(int i=0;i<3;++i){dvec3 a=v[(i+1)%3],b=v[(i+2)%3];double len=lengthd(b-a);maxedge=max(maxedge,len);mind=min(mind,lengthd(crossd(b-a,p-a))/len);}
    if(mind>=physical.y)return p;
    precise double h=lengthd(crossd(tri.b.xyz-tri.a.xyz,tri.c.xyz-tri.a.xyz))/maxedge;
    precise double alpha=min(0.5LF,3.0LF*physical.y/h);
    precise dvec3 centre=((tri.a.xyz+tri.b.xyz)+tri.c.xyz)*(1.0LF/3.0LF);
    precise dvec3 value=p+(centre-p)*alpha;return value;
}
dvec3 direct_term(dvec3 origin,dvec3 n,uint self,inout u64vec4 counters) {
    precise dvec3 e=dvec3(0.0LF);
    for(uint j=0u;j<sizes.z;++j){
        precise dvec3 l=points[j].position.xyz-origin;double d2=dotd(l,l);if(!(d2>0.0LF))continue;
        precise double d=sqrt(d2);precise dvec3 wi=l*(1.0LF/d);double cosx=dotd(n,wi);if(cosx<=0.0LF)continue;
        counters.y+=uint64_t(1);
        precise double endpoint=d*(1.0LF-1e-12LF)-physical.x;
        if(trace(origin,wi,0.0LF,endpoint,self,true).tri!=MISS){counters.z+=uint64_t(1);continue;}
        precise double g=seedWords.z==0u?cosx/d2:cosx/(physical.z*physical.z+d2);
        e+=points[j].intensity.xyz*g;
    }
    return e;
}
void main() {
    uint pixel=gl_GlobalInvocationID.x;if(pixel>=sizes.x)return;
    Primary initial=primary[pixel];
    for(uint sampleIndex=interval.x;sampleIndex<interval.y;++sampleIndex){
        precise dvec3 indirect=dvec3(0.0LF);uint dim=0u;
        u64vec4 counters=initial.counters;
        if(initial.origin.w>0.0LF && sizes.w>1u){
            precise dvec3 origin=initial.origin.xyz,normal=initial.normal.xyz,throughput=initial.rho.xyz;
            uint ignore=uint(initial.normal.w);
            for(uint bounce=1u;bounce<sizes.w;++bounce){
                double u1=uniform01(pixel,sampleIndex,dim),u2=uniform01(pixel,sampleIndex,dim);
                precise dvec3 direction=cosine_sample(normal,u1,u2);
                Hit hit=trace(origin,direction,0.0LF,physical.w,ignore,false);if(hit.tri==MISS)break;
                Triangle tri=triangles[hit.tri];dvec3 ng=tri.normal.xyz;bool front=dotd(ng,direction)<0.0LF;
                if(!front && tri.rho.w==0.0LF){counters.w+=uint64_t(1);break;}
                normal=front?ng:-ng;
                precise dvec3 position=nudge(tri,origin+direction*hit.t);origin=position+normal*physical.x;
                precise dvec3 f=tri.rho.xyz/PI;if(all(equal(f,dvec3(0.0LF))))break;
                dvec3 e=direct_term(origin,normal,hit.tri,counters);
                indirect+=(throughput*f)*e;throughput*=tri.rho.xyz;ignore=hit.tri;
            }
        }
        precise dvec3 components[4]=dvec3[4](initial.emit.xyz,initial.direct.xyz,indirect,(initial.emit.xyz+initial.direct.xyz)+indirect);
        for(int k=0;k<4;++k){precise dvec3 square=components[k]*components[k];precise dvec3 s1=stats[pixel].sum[k].xyz+components[k];precise dvec3 s2=stats[pixel].sum2[k].xyz+square;stats[pixel].sum[k].xyz=s1;stats[pixel].sum2[k].xyz=s2;}
        stats[pixel].counters+=counters;
    }
}

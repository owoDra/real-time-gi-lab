// Plan110 draft execution backend. Replaces only the retained hybrid main.
// Requires its FP64/Int64 geometry, RNG, trig, nudge, visibility and NEE helpers.
// Every uncertain sample is flagged for complete CPU all-split recomputation.
// No reference eligibility, numerical-equivalence or speed claim from this source.
struct WholeRawGpu { uint tri; dvec3 point; };
struct WholeStateGpu { uint tri; dvec3 origin,normal; };
struct ScaledDensityGpu { double mantissa; int exponent; };

ScaledDensityGpu density_zero() { return ScaledDensityGpu(0.0LF,0); }
ScaledDensityGpu density_one() { return ScaledDensityGpu(0.5LF,1); }
bool finite_positive(double x) { return x>0.0LF && !isnan(x) && !isinf(x); }

ScaledDensityGpu density_times(ScaledDensityGpu a,double b) {
    if(a.mantissa==0.0LF)return a;
    if(!finite_positive(b)){pathAmbiguous=true;return density_zero();}
    int be,ce;
    double bm=frexp(b,be),cm=frexp(a.mantissa*bm,ce);
    return ScaledDensityGpu(cm,a.exponent+be+ce);
}

ScaledDensityGpu density_product(ScaledDensityGpu a,ScaledDensityGpu b) {
    if(a.mantissa==0.0LF || b.mantissa==0.0LF)return density_zero();
    int ce;double cm=frexp(a.mantissa*b.mantissa,ce);
    return ScaledDensityGpu(cm,a.exponent+b.exponent+ce);
}

bool density_less(ScaledDensityGpu a,ScaledDensityGpu b) {
    if(a.mantissa==0.0LF)return b.mantissa>0.0LF;
    if(b.mantissa==0.0LF)return false;
    return a.exponent<b.exponent || (a.exponent==b.exponent && a.mantissa<b.mantissa);
}

double density_ratio(ScaledDensityGpu a,ScaledDensityGpu b) {
    if(a.mantissa==0.0LF)return 0.0LF;
    if(b.mantissa==0.0LF){pathAmbiguous=true;return 0.0LF;}
    int delta=a.exponent-b.exponent;
    // Conservative execution fallback, not a sample rejection or scientific cut.
    if(delta < -1022 || delta > 1022){pathAmbiguous=true;return 0.0LF;}
    double r=ldexp(a.mantissa/b.mantissa,delta);
    if(!finite_positive(r)){pathAmbiguous=true;return 0.0LF;}
    return r;
}

WholeStateGpu whole_state_gpu(WholeRawGpu raw,dvec3 incoming) {
    Triangle t=triangles[raw.tri];dvec3 ng=t.normal.xyz;
    dvec3 normal=dotd(ng,incoming)<0.0LF?ng:-ng;
    return WholeStateGpu(raw.tri,nudge(t,raw.point)+normal*physical.x,normal);
}

bool possible_cpu_coincidence(uint aId,uint bId) {
    Triangle a=triangles[aId],b=triangles[bId];
    if(any(notEqual(a.rho,b.rho)) || any(notEqual(a.emit.xyz,b.emit.xyz)))return false;
    for(int j=0;j<3;++j) {
        if(a.a[j]==a.b[j] && a.a[j]==a.c[j] && a.a[j]==b.a[j] &&
           a.a[j]==b.b[j] && a.a[j]==b.c[j])return true;
    }
    return false;
}

ScaledDensityGpu density_edge(ScaledDensityGpu q,double pdf,double cosine,double d2) {
    return density_times(density_times(density_times(q,pdf),cosine),1.0LF/d2);
}

bool generate_whole_gpu(inout WholeStateGpu current,uint count,bool lightFirst,
                        double uniforms[14],double remap,inout uint dimension,
                        out WholeRawGpu vertices[7],inout ScaledDensityGpu sampled) {
    for(uint i=0u;i<count;++i) {
        double u=dimension==0u?remap:uniforms[dimension];++dimension;
        double v=uniforms[dimension++];bool sphere=lightFirst && i==0u;
        dvec3 direction;
        if(sphere) {
            double z=1.0LF-2.0LF*u,r=sqrt(max(0.0LF,1.0LF-z*z));
            dvec2 sc=sincosd(2.0LF*PI*v);direction=dvec3(r*sc.y,r*sc.x,z);
        } else direction=cosine_sample(current.normal,u,v);
        double pdf=sphere?1.0LF/(4.0LF*PI):max(0.0LF,dotd(current.normal,direction))/PI;
        Hit hit=trace(current.origin,direction,sphere?physical.x:0.0LF,
                      sphere?infinity():physical.w,current.tri,false);
        if(hit.tri==MISS)return false;
        double cosine=abs(dotd(triangles[hit.tri].normal.xyz,direction));
        if(cosine<1e-12LF || pdf<1e-12LF)pathAmbiguous=true;
        if(!finite_positive(pdf) || !finite_positive(cosine) || !finite_positive(hit.t)) {
            pathAmbiguous=true;return false;
        }
        sampled=density_edge(sampled,pdf,cosine,hit.t*hit.t);
        vertices[i]=WholeRawGpu(hit.tri,current.origin+direction*hit.t);
        current=whole_state_gpu(vertices[i],direction);
    }
    return true;
}

void whole_density_prefixes_gpu(WholeStateGpu current,WholeRawGpu path[7],uint count,
                               bool reverse,bool lightFirst,out ScaledDensityGpu cumulative[8],
                               out WholeStateGpu endpoint,inout dvec3 throughput,bool physicalForward) {
    for(uint i=0u;i<8u;++i)cumulative[i]=density_zero();
    cumulative[0]=density_one();ScaledDensityGpu q=density_one();endpoint=current;
    for(uint i=0u;i<count;++i) {
        WholeRawGpu target=path[reverse?count-1u-i:i];
        dvec3 delta=target.point-current.origin;double d2=dotd(delta,delta);
        if(!(d2>0.0LF))return;
        double distance=sqrt(d2);dvec3 direction=delta*(1.0LF/distance);
        bool sphere=lightFirst && i==0u;
        double pdf=sphere?1.0LF/(4.0LF*PI):max(0.0LF,dotd(current.normal,direction))/PI;
        if(!(pdf>0.0LF))return;
        Hit hit=trace(current.origin,direction,sphere?physical.x:0.0LF,
                      sphere?infinity():physical.w,current.tri,false);
        if(hit.tri==MISS)return;
        // Noncoincident occlusion is an ordinary zero in the CPU proposal too.
        // Its exact axis/material necessary conditions use only stored doubles.
        // Delegate possible CPU072/074 matches, including long-double interiors.
        if(hit.tri!=target.tri) {
            if(possible_cpu_coincidence(target.tri,hit.tri))pathAmbiguous=true;
            return;
        }
        dvec3 actual=current.origin+direction*hit.t;
        double error=lengthd(actual-target.point);
        double bound=5.684341886080801486968994140625e-14LF*
                     (1.0LF+lengthd(current.origin)+lengthd(target.point)+distance);
        // Stronger execution fallback than the CPU conditioned backward audit.
        // Both outputs still represent the same complete original scored sample.
        Triangle t=triangles[target.tri];
        double targetPlane=abs(dotd(t.normal.xyz,target.point-t.a.xyz));
        double actualPlane=abs(dotd(t.normal.xyz,actual-t.a.xyz));
        double cosine=abs(dotd(t.normal.xyz,direction));
        if(!finite_positive(d2) || isnan(error) || isinf(error) || error>bound ||
           targetPlane>bound || actualPlane>bound || error*cosine>bound)pathAmbiguous=true;
        if(!(cosine>0.0LF))return;
        if(cosine<1e-12LF || pdf<1e-12LF)pathAmbiguous=true;
        q=density_edge(q,pdf,cosine,d2);
        if(physicalForward) {
            if(t.rho.w==0.0LF && !(dotd(t.normal.xyz,direction)<0.0LF))throughput=dvec3(0.0LF);
            if(i+1u<count)throughput*=t.rho.xyz;
        }
        current=whole_state_gpu(target,direction);endpoint=current;cumulative[i+1u]=q;
    }
}

void main() {
    uint invocation=gl_GlobalInvocationID.x,slot=invocation/interval.z;
    uint sampleIndex=interval.x+invocation%interval.z;
    if(slot>=interval.w || sampleIndex>=interval.y)return;
    diagnosticSlot=slot;uint pixel=selected[slot];Primary initial=primary[pixel];
    {
        pathAmbiguous=false;diagnosticSample=sampleIndex;diagnosticBounce=1u;
        dvec3 indirect=dvec3(0.0LF);u64vec4 counters=initial.counters;
        if(initial.origin.w>0.0LF && sizes.w>1u) {
            double uniforms[14];uint dim=0u;
            for(uint d=0u;d<14u;++d)uniforms[d]=uniform01(pixel,sampleIndex,dim);
            WholeStateGpu primaryState=WholeStateGpu(uint(initial.normal.w),initial.origin.xyz,initial.normal.xyz);
            WholeStateGpu lightState=WholeStateGpu(MISS,points[0].position.xyz,dvec3(0.0LF));
            for(uint k=1u;k<sizes.w;++k) {
                diagnosticBounce=k;
                uint split=min(k,uint(double(k+1u)*uniforms[0])),eyeLength=k-split;
                double remap=double(k+1u)*uniforms[0]-double(split);uint dimension=0u;
                WholeRawGpu eye[7],light[7],path[7];
                WholeStateGpu eyeState=primaryState,photonState=lightState;
                ScaledDensityGpu sampled=density_one();
                if(!generate_whole_gpu(eyeState,eyeLength,false,uniforms,remap,dimension,eye,sampled) ||
                   !generate_whole_gpu(photonState,split,true,uniforms,remap,dimension,light,sampled))continue;
                if(dimension!=2u*k){pathAmbiguous=true;continue;}
                for(uint i=0u;i<eyeLength;++i)path[i]=eye[i];
                for(uint i=0u;i<split;++i)path[eyeLength+i]=light[split-1u-i];
                ScaledDensityGpu eyeQ[8],lightQ[8],q[8];WholeStateGpu endpoint,unusedEndpoint;
                dvec3 throughput=initial.rho.xyz,unusedThroughput=dvec3(1.0LF);
                whole_density_prefixes_gpu(primaryState,path,k,false,false,eyeQ,endpoint,throughput,true);
                whole_density_prefixes_gpu(lightState,path,k,true,true,lightQ,unusedEndpoint,unusedThroughput,false);
                for(uint j=0u;j<=k;++j)q[j]=density_product(eyeQ[k-j],lightQ[j]);
                double ownRatio=density_ratio(sampled,q[split]);
                if(abs(ownRatio-1.0LF)>1e-8LF)pathAmbiguous=true;
                if(q[0].mantissa==0.0LF)continue;
                ScaledDensityGpu largest=q[0];
                for(uint j=1u;j<=k;++j)if(density_less(largest,q[j]))largest=q[j];
                double sum=0.0LF;for(uint j=0u;j<=k;++j)sum+=density_ratio(q[j],largest);
                double weight=double(k+1u)*density_ratio(q[0],largest)/sum;
                if(isnan(weight) || isinf(weight) || weight<0.0LF || weight>double(k+1u))pathAmbiguous=true;
                if(all(equal(throughput,dvec3(0.0LF))))continue;
                dvec3 e=direct_term(endpoint.origin,endpoint.normal,endpoint.tri,counters);
                dvec3 reflected=triangles[endpoint.tri].rho.xyz/PI*e;
                reflected*=throughput;indirect+=weight*reflected;
            }
        }
        dvec3 components[4]=dvec3[4](initial.emit.xyz,initial.direct.xyz,indirect,
                                    (initial.emit.xyz+initial.direct.xyz)+indirect);
        uint pathIndex=slot*interval.z+sampleIndex-interval.x;
        for(int c=0;c<4;++c) {
            if(any(isnan(components[c])) || any(isinf(components[c])) || any(lessThan(components[c],dvec3(0.0LF))))pathAmbiguous=true;
            paths[pathIndex].components[c]=dvec4(components[c],0.0LF);
        }
        paths[pathIndex].counters=counters;pathFlags[pathIndex]=pathAmbiguous?1u:0u;
    }
}

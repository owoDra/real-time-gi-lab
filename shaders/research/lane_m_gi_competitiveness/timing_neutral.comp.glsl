#version 460
//044 architecture-neutral calibration work: a fixed-iteration dependent FMA chain per thread.
layout(local_size_x=64) in;
layout(std430,binding=0) buffer Output { float values[]; };
layout(push_constant) uniform Push { uint iterations; uint count; uint seed; uint reserved; } pc;
void main() {
    uint i=gl_GlobalInvocationID.x;
    if(i>=pc.count) return;
    float x=float((i^pc.seed)&1023u)*0.0009765625;
    for(uint k=0u;k<pc.iterations;k++) x=fma(x,0.99999994,0.0000001);
    values[i]=x;
}

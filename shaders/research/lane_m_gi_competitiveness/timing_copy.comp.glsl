#version 460
//044 ReSTIR V1 indirect (frame image .z) becomes the reconstruction source.
layout(local_size_x=64) in;
layout(std430,binding=0) readonly buffer Frame { vec4 frame[]; };
layout(std430,binding=1) writeonly buffer Sources { float sources[]; };
layout(push_constant) uniform Push { uint count; uint reserved0; uint reserved1; uint reserved2; } pc;
void main() {
    uint i=gl_GlobalInvocationID.x;
    if(i<pc.count) sources[i]=frame[i].z;
}

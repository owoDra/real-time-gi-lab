#version 460
//044 raw PT chunk accumulation: assign the first 64spp chunk, add later chunks.
layout(local_size_x=64) in;
layout(std430,binding=0) readonly buffer Image { vec4 image[]; };
layout(std430,binding=1) buffer Accumulated { vec4 accumulated[]; };
layout(push_constant) uniform Push { uint mode; uint count; uint chunks; uint reserved; } pc;
void main() {
    uint i=gl_GlobalInvocationID.x;
    if(i>=pc.count) return;
    vec4 value=image[i]/float(pc.chunks);
    accumulated[i]=pc.mode==0u ? value : accumulated[i]+value;
}

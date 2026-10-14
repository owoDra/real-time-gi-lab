#version 460
layout(local_size_x=64) in;
layout(std430,binding=0) writeonly buffer Scratch {uint value[];} scratch;
layout(push_constant) uniform Push {uint count;uint dose;} p;
void main() {
    uint id=gl_GlobalInvocationID.x;if(id>=p.count)return;
    uint x=id^0x4e303130u;
    for(uint j=0;j<p.dose;++j) {x=x*1664525u+1013904223u;x^=x>>13u;}
    scratch.value[id]=x;
}

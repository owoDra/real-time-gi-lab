#version 460
layout(local_size_x=64) in;
layout(std430,binding=0) buffer Scratch {uint value[];} scratch;
layout(std430,binding=1) buffer Progress {uint next[];} progress;
layout(push_constant) uniform Push {uint count;uint begin;uint end;} p;
void main() {
    uint id=gl_GlobalInvocationID.x;if(id>=p.count)return;
    if(p.begin>p.end || p.end-p.begin>65536u || p.end>100000000u ||
       (p.begin!=0u && progress.next[id]!=p.begin)) {
        progress.next[id]=0xffffffffu;return;
    }
    uint x=p.begin==0u ? id^0x4e303130u : scratch.value[id];
    for(uint j=p.begin;j<p.end;++j) {x=x*1664525u+1013904223u;x^=x>>13u;}
    scratch.value[id]=x;progress.next[id]=p.end;
}

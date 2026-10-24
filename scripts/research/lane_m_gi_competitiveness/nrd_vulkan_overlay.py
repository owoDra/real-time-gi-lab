"""024 reversible all-sample witnesses on the immutable023 physical producer."""
import nrd_source_contract as S
ROOT=S.ROOT


def producer(raw):
    old=S.producer(raw).decode();changes=[
      ('layout(std430,binding=6) writeonly buffer Secondary { vec2 secondary[]; };', 'layout(std430,binding=6) writeonly buffer Secondary { vec2 secondary[]; };\nlayout(std430,binding=7) writeonly buffer Origins { vec4 secondary_origins[]; };\nlayout(std430,binding=8) buffer Rays { vec4 secondary_rays[]; };\nlayout(std430,binding=9) writeonly buffer RayPrimitives { uint secondary_primitives[]; };'),
      ('        secondary[id]=vec2(0.0);','        secondary[id]=vec2(0.0);\n        secondary_origins[id]=vec4(0);\n        for(uint s=0u;s<pc.spp;s++){secondary_rays[id*pc.spp+s]=vec4(0);secondary_primitives[id*pc.spp+s]=INVALID;}'),
      ('    float secondary_sum=0.0;','    secondary_origins[id]=vec4(offset_position(pos,normal),0);\n    float secondary_sum=0.0;'),
      ('            if(!trace(offset_position(origin,n),wi,1.0e30,self,next_primitive,next_position,next_normal,continuation_t)) break;', '            if(vertex==1u){secondary_rays[id*pc.spp+sample_index]=vec4(wi,65504.0);secondary_primitives[id*pc.spp+sample_index]=INVALID;}\n            if(!trace(offset_position(origin,n),wi,1.0e30,self,next_primitive,next_position,next_normal,continuation_t)) break;'),
      ('            if(vertex==1u) first_secondary=clamp(continuation_t,0.0,65504.0);','            if(vertex==1u){first_secondary=clamp(continuation_t,0.0,65504.0);secondary_rays[id*pc.spp+sample_index].w=first_secondary;secondary_primitives[id*pc.spp+sample_index]=triangles[next_primitive].metadata.x;}')]
    text=old
    for a,b in changes:text=S.O.once(text,a,b)
    restored=text
    for a,b in reversed(changes):restored=S.O.once(restored,b,a)
    if restored!=old:raise ValueError('024 producer inverse differs')
    return text.encode()

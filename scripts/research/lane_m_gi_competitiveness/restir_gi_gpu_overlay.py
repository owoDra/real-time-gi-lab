"""037 reversible observations on the unchanged022 physical PT arithmetic."""
import integrated_pt_overlay as O

DECL = '''
struct Witness { vec4 origin_t; vec4 direction_direct; vec4 position_primitive; vec4 normal_kind; vec4 spawn_front; };
struct Candidate { vec4 origin_pdf; vec4 normal_status; vec4 endpoint_primitive; vec4 endpoint_normal; vec4 radiance_trial; vec4 direction_cosine; vec4 primary_direct; uvec4 flags; };
layout(std430,binding=6) buffer Witnesses { Witness witnesses[]; };
layout(std430,binding=7) buffer Candidates { Candidate candidates[]; };
void observe(uint index,vec3 origin,vec3 direction,bool hit,float t,uint primitive,vec3 position,vec3 normal,float direct) {
    Witness w;
    w.origin_t=vec4(origin,hit?t:0);w.direction_direct=vec4(direction,hit?direct:0);
    w.position_primitive=vec4(hit?position:vec3(0),uintBitsToFloat(hit?primitive:INVALID));
    w.normal_kind=vec4(hit?normal:vec3(0),uintBitsToFloat(hit?2u:1u));
    vec3 gn=hit?normalize(cross(triangles[primitive].v1.xyz-triangles[primitive].v0.xyz,triangles[primitive].v2.xyz-triangles[primitive].v0.xyz)):vec3(0);
    w.spawn_front=vec4(hit?offset_position(position,normal):vec3(0),uintBitsToFloat(hit&&dot(gn,direction)<=0?1u:0u));
    witnesses[index]=w;
}
'''


def producer(raw):
    original = O.producer(raw).decode()
    changes = [
        ('void main() {', DECL+'\nvoid main() {'),
        ('    uint prim; vec3 pos,normal; float primary_t;', '''    for(uint v=0u;v<pc.vertices;v++) witnesses[id*pc.vertices+v]=Witness(vec4(0),vec4(0),vec4(0),vec4(0),vec4(0));
    Candidate candidate=Candidate(vec4(0),vec4(0),vec4(0),vec4(0),vec4(0,0,0,1),vec4(0),vec4(0),uvec4(0));
    uint prim; vec3 pos,normal; float primary_t;'''),
        ('        pixels[id]=vec4(0,0,0,1); return;', '''        observe(id*pc.vertices,p.camera_pos_near.xyz,view,false,0,INVALID,vec3(0),vec3(0),0);
        candidates[id]=candidate;
        pixels[id]=vec4(0,0,0,1); return;'''),
        ('    rng=mix32(pc.seed^mix32(id));', '''    observe(id*pc.vertices,p.camera_pos_near.xyz,view,true,primary_t,prim,pos,normal,direct);
    candidate.origin_pdf.xyz=offset_position(pos,normal);candidate.normal_status=vec4(normal,uintBitsToFloat(1u));
    candidate.endpoint_normal.w=uintBitsToFloat(prim);candidate.primary_direct=vec4(pos,direct);
    rng=mix32(pc.seed^mix32(id));'''),
        ('            if(!trace(offset_position(origin,n),wi,1.0e30,self,next_primitive,next_position,next_normal,continuation_t)) break;', '''            observe(id*pc.vertices+vertex,offset_position(origin,n),wi,false,0,INVALID,vec3(0),vec3(0),0);
            if(vertex==1u){candidate.direction_cosine=vec4(wi,max(0,dot(n,wi)));candidate.origin_pdf.w=candidate.direction_cosine.w/PI;}
            if(!trace(offset_position(origin,n),wi,1.0e30,self,next_primitive,next_position,next_normal,continuation_t)) break;'''),
        ('            indirect+=direct_light(next_position,next_normal,next_primitive);', '''            float reflected=direct_light(next_position,next_normal,next_primitive);
            indirect+=reflected;
            observe(id*pc.vertices+vertex,offset_position(origin,n),wi,true,continuation_t,next_primitive,next_position,next_normal,reflected);
            if(vertex==1u){candidate.normal_status.w=uintBitsToFloat(2u);candidate.endpoint_primitive=vec4(next_position,uintBitsToFloat(next_primitive));candidate.endpoint_normal.xyz=next_normal;}'''),
        ('    sources[id]=indirect;', '''    candidate.radiance_trial.xyz=vec3(indirect);candidate.flags.x=rng;
    candidates[id]=candidate;
    sources[id]=indirect;'''),
    ]
    text=original
    for a,b in changes:text=O.once(text,a,b)
    restored=text
    for a,b in reversed(changes):restored=O.once(restored,b,a)
    if restored!=original:raise ValueError('037 producer inverse differs')
    return text.encode()

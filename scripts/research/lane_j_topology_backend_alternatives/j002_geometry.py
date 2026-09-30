from __future__ import annotations
from dataclasses import dataclass
import base64, hashlib, json, math, struct
from pathlib import Path
from typing import Sequence
from j002_contract import Triangle

INVALID_ID=0xffffffff
TRIANGLE_RECORD=struct.Struct("<9fIII?3x")
SNAPSHOT_MAGIC=b"PHOSJ2G1"
SNAPSHOT_HEADER=struct.Struct("<8sII32s")
_COMPONENT={5121:("B",1),5123:("H",2),5125:("I",4),5126:("f",4)}
_TYPE_COUNT={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}

def _f32(v): return struct.unpack("<f",struct.pack("<f",float(v)))[0]
def _sub(a,b): return (a[0]-b[0],a[1]-b[1],a[2]-b[2])
def _cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def _length(v): return math.sqrt(sum(x*x for x in v))
def centroid(t): return tuple((t.v0[i]+t.v1[i]+t.v2[i])/3.0 for i in range(3))

def _load_uri(base,uri):
    if uri.startswith("data:"):
        marker=";base64,"; pos=uri.find(marker)
        if pos<0: raise ValueError("only base64 data URIs are supported")
        return base64.b64decode(uri[pos+len(marker):])
    return (base/uri).read_bytes()

def _accessor(asset,buffers,index):
    acc=asset["accessors"][index]
    if "sparse" in acc: raise ValueError("sparse glTF accessors are not supported")
    view=asset["bufferViews"][acc["bufferView"]]
    ctype=int(acc["componentType"])
    if ctype not in _COMPONENT: raise ValueError("unsupported component type")
    fmt,cbytes=_COMPONENT[ctype]; n=_TYPE_COUNT[str(acc["type"])]
    elem=cbytes*n; stride=int(view.get("byteStride",elem))
    start=int(view.get("byteOffset",0))+int(acc.get("byteOffset",0))
    data=buffers[int(view["buffer"])]; unpack=struct.Struct("<"+fmt*n)
    out=[]
    for i in range(int(acc["count"])):
        off=start+i*stride
        if off+elem>len(data): raise ValueError("glTF accessor exceeds buffer")
        out.append(unpack.unpack_from(data,off))
    return out

def load_b002_compatible_gltf(path: Path):
    asset=json.loads(path.read_text(encoding="utf-8"))
    buffers=[_load_uri(path.parent,b["uri"]) for b in asset.get("buffers",[])]
    materials=asset.get("materials",[]); out=[]
    for mesh_index,mesh in enumerate(asset.get("meshes",[])):
        for primitive in mesh.get("primitives",[]):
            if int(primitive.get("mode",4))!=4: continue
            attrs=primitive.get("attributes",{})
            if "POSITION" not in attrs or "indices" not in primitive: continue
            positions=_accessor(asset,buffers,int(attrs["POSITION"]))
            indices=[int(v[0]) for v in _accessor(asset,buffers,int(primitive["indices"]))]
            material_id=INVALID_ID; two_sided=False
            if "material" in primitive:
                material_id=int(primitive["material"])
                if material_id>=len(materials): raise ValueError("invalid material")
                two_sided=bool(materials[material_id].get("doubleSided",False))
            for i in range(0,len(indices)-2,3):
                a=tuple(map(float,positions[indices[i]])); b=tuple(map(float,positions[indices[i+1]])); c=tuple(map(float,positions[indices[i+2]]))
                if _length(_cross(_sub(b,a),_sub(c,a)))<=1e-12: continue
                out.append(Triangle(tuple(map(_f32,a)),tuple(map(_f32,b)),tuple(map(_f32,c)),len(out),material_id,mesh_index,two_sided))
    if not out: raise ValueError("no non-degenerate triangles")
    return out

def select_representative_object(triangles,expected_count=796):
    groups={}
    for t in triangles: groups.setdefault(t.instance_id,[]).append(t)
    exact=[(i,g) for i,g in groups.items() if len(g)==expected_count]
    if not exact: raise ValueError(f"expected {expected_count}-triangle object")
    return list(min(exact,key=lambda p:p[0])[1])

def _mix32(v):
    v&=0xffffffff; v^=v>>16; v=(v*0x7feb352d)&0xffffffff; v^=v>>15; v=(v*0x846ca68b)&0xffffffff; v^=v>>16
    return v

def _bounds(ts):
    pts=[p for t in ts for p in (t.v0,t.v1,t.v2)]
    return tuple(min(p[a] for p in pts) for a in range(3)),tuple(max(p[a] for p in pts) for a in range(3))

def _morton10(p,mn,mx):
    def q(a):
        e=max(mx[a]-mn[a],1e-9); return max(0,min(1023,int((p[a]-mn[a])/e*1023+0.5)))
    def spread(v):
        r=0
        for bit in range(10): r|=((v>>bit)&1)<<(3*bit)
        return r
    x,y,z=q(0),q(1),q(2); return spread(x)|(spread(y)<<1)|(spread(z)<<2)

def derive_profile_base(source,target_count,seed,first_new_id=None):
    ranked=sorted(source,key=lambda t:(_mix32(t.primitive_id^seed),t.primitive_id))
    if target_count<=len(source): return list(ranked[:target_count])
    if first_new_id is None: raise ValueError("first_new_id required for expansion")
    mn,mx=_bounds(source); diag=max(math.dist(mn,mx),1.0); out=list(ranked); instance_id=source[0].instance_id
    for i in range(len(source),target_count):
        t=ranked[i%len(ranked)]; phase=_mix32(seed^i); s=.015*diag
        off=(((phase&15)-7.5)*s,(((phase>>4)&7)-3.5)*s*.5,(((phase>>7)&15)-7.5)*s)
        move=lambda v: tuple(_f32(v[a]+off[a]) for a in range(3))
        out.append(Triangle(move(t.v0),move(t.v1),move(t.v2),first_new_id+i-len(source),t.material_id,instance_id,t.two_sided))
    return out

def _selected_indices(ts,count,seed,locality):
    count=min(max(count,0),len(ts))
    if locality=="global": return sorted(range(len(ts)),key=lambda i:(_mix32(ts[i].primitive_id^seed),ts[i].primitive_id))[:count]
    if locality!="local": raise ValueError("unknown locality")
    mn,mx=_bounds(ts); order=sorted(range(len(ts)),key=lambda i:(_morton10(centroid(ts[i]),mn,mx),ts[i].primitive_id)); start=seed%len(order)
    return [order[(start+i)%len(order)] for i in range(count)]

def _mutated(t,pid,seed,ordinal):
    diag=max(math.dist(*_bounds([t])),1e-3)
    signed=lambda x: ((_mix32(x)&0xffff)/32767.5)-1.0
    base=seed^pid^(ordinal*0x9e3779b9); tr=(signed(base^1)*diag*.15,signed(base^2)*diag*.08,signed(base^3)*diag*.15)
    def vertex(v,slot): return tuple(_f32(v[a]+tr[a]+signed(base^(slot*17+a))*diag*.025) for a in range(3))
    return Triangle(vertex(t.v0,1),vertex(t.v1,2),vertex(t.v2,3),pid,t.material_id,t.instance_id,t.two_sided)

def triangle_bytes(t):
    return TRIANGLE_RECORD.pack(*(t.v0+t.v1+t.v2),t.primitive_id,t.material_id,t.instance_id,t.two_sided)

def snapshot_digest(ts):
    h=hashlib.sha256()
    for t in ts: h.update(triangle_bytes(t))
    return h.hexdigest()

@dataclass(frozen=True)
class Snapshot:
    index:int; primitive_count:int; topology_seed:int; replacement_count:int; locality:str
    triangles:tuple[Triangle,...]; inserted_ids:tuple[int,...]; removed_ids:tuple[int,...]
    replaced_old_ids:tuple[int,...]; replaced_new_ids:tuple[int,...]; snapshot_digest:str

def materialize_profile(base,steps,first_new_id=None):
    current=list(base); next_id=max(max(t.primitive_id for t in current)+1,first_new_id or 0)
    if len(current)!=int(steps[0].primitive_count): raise ValueError("base count mismatch")
    out=[Snapshot(0,len(current),int(steps[0].topology_seed),0,str(steps[0].locality),tuple(current),(),(),(),(),snapshot_digest(current))]
    for step in steps[1:]:
        seed=int(step.topology_seed); target=int(step.primitive_count); locality=str(step.locality)
        removed=[]; inserted=[]; rold=[]; rnew=[]
        if target<len(current):
            idx=set(_selected_indices(current,len(current)-target,seed^0x51a7,locality)); removed=[current[i].primitive_id for i in sorted(idx)]; current=[t for i,t in enumerate(current) if i not in idx]
        elif target>len(current):
            for ordinal in range(target-len(current)):
                t=base[_mix32(seed+ordinal)%len(base)]; n=_mutated(t,next_id,seed^0x1a57,ordinal); next_id+=1; current.append(n); inserted.append(n.primitive_id)
        for ordinal,index in enumerate(_selected_indices(current,min(int(step.replacement_count),len(current)),seed^0xbeef,locality)):
            old=current[index]; n=_mutated(old,next_id,seed^0xcafe,ordinal); next_id+=1; current[index]=n; rold.append(old.primitive_id); rnew.append(n.primitive_id)
        if len(current)!=target: raise AssertionError("target count drift")
        out.append(Snapshot(int(step.index),target,seed,int(step.replacement_count),locality,tuple(current),tuple(inserted),tuple(removed),tuple(rold),tuple(rnew),snapshot_digest(current)))
    return out

def write_snapshot(path,snapshot):
    payload=b"".join(triangle_bytes(t) for t in snapshot.triangles)
    path.write_bytes(SNAPSHOT_HEADER.pack(SNAPSHOT_MAGIC,1,len(snapshot.triangles),hashlib.sha256(payload).digest())+payload)

def read_snapshot(path):
    data=Path(path).read_bytes(); magic,version,count,digest=SNAPSHOT_HEADER.unpack_from(data,0); payload=data[SNAPSHOT_HEADER.size:]
    if magic!=SNAPSHOT_MAGIC or version!=1 or len(payload)!=count*TRIANGLE_RECORD.size or hashlib.sha256(payload).digest()!=digest: raise ValueError("invalid snapshot")
    out=[]
    for i in range(count):
        v=TRIANGLE_RECORD.unpack_from(payload,i*TRIANGLE_RECORD.size)
        out.append(Triangle(tuple(v[0:3]),tuple(v[3:6]),tuple(v[6:9]),int(v[9]),int(v[10]),int(v[11]),bool(v[12])))
    return out

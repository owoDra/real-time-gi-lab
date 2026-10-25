"""034 full-field analytic fixture/oracle. Not a physical M001 path tracer."""
from pathlib import Path
import struct
import numpy as np

PACKED=np.dtype([('position','<f4',3),('misc','<u4'),('radiance','<u4'),('weight','<f4'),('normal','<u4'),('unused','<f4')])
SURFACE=np.dtype([('position','<f4',3),('depth','<f4'),('normal','<f4',3),('material','<u4'),('valid','<u4'),('padding','<u4',3)])
F=np.float32;U=np.uint32;PI=F(3.1415926535);LUMA=np.array([.2126,.7152,.0722],dtype=F)
GUARD=256;DIMENSIONS=((17,9),(320,180))


def need(ok,message):
    if not ok:raise ValueError('034 '+message)


def layout(w,h):
    y,x=np.indices((h,w),dtype=U);row=((w+15)//16)*256;pitch=row*((h+15)//16)
    indices=(y//16*row+x//16*256+y%16*16+x%16).ravel()
    return pitch,row,indices


def build_fixtures(out,w,h,offsets):
    out=Path(out);out.mkdir();n=w*h;pitch,row,_=layout(w,h)
    with (out/'meta.u32').open('xb') as f:f.write(struct.pack('<II',w,h))
    need(len(offsets)==16384,'exact qualified offsets')
    for case in range(8):
        folder=out/f'fixture-{case}';folder.mkdir()
        surface=np.zeros(n,SURFACE);surface['position'][:,0]=0 if case==3 else 1;surface['depth']=1
        surface['normal'][:,2]=1;surface['material']=0xffffffff;surface['valid']=1
        previous=surface.copy()
        if case==5:previous[:]=np.zeros(1,SURFACE)
        if case==6:previous['material']=0
        raw=np.zeros((n,3,4),F);raw[:,0,:3]=surface['position']+np.array([0,0,1],F);raw[:,0,3]=0 if case==2 else F(1)/PI
        raw[:,1,2]=1 if case==4 else -1
        value=np.zeros(n,F) if case==2 else F(1)+np.arange(n,dtype=U)%4 if case==1 else np.ones(n,F)
        raw[:,2,:3]=value[:,None]
        # SDK structures and HLSL cbuffer layout are independently rechecked at CPU preparation.
        age=1 if case==7 else 30
        spatial=struct.pack('<ffIfIIII',.1,.6,2,32.,1,0,0,0)
        temporal=struct.pack('<ffIIIIII',.1,.6,8,1,1,age,0,0)
        fused=struct.pack('<ffIIfIIIIIII',.1,.6,3,2,32.,8,1,age,0,0,0,0)
        controls=bytearray(80);struct.pack_into('<IIII',controls,0,w,h,0,0);struct.pack_into('<IIII',controls,16,8191,0,0,0)
        struct.pack_into('<IIII',controls,32,row,pitch,0,0);struct.pack_into('<I',controls,76,1)
        buffers=[bytes(pitch*64),surface.tobytes(),previous.tobytes(),raw.tobytes(),offsets,bytes((n*2+64)*16),spatial,temporal,fused,bytes(controls)]
        for binding,data in enumerate(buffers):
            with (folder/f'binding-{binding}.bin').open('xb') as f:f.write(data)
    return dict(width=w,height=h,pixels=n,pitch=pitch,fixtures=8,guard_bytes=GUARD,controls_bytes=80)


def decode(code):
    code=np.asarray(code,U);le=code>>18;y=np.exp2((le.astype(F)+F(.5))/F(409.6)-F(20))
    uv=np.stack(((code>>9)&511,code&511),axis=-1).astype(F);uv=(uv+F(.5))/F(820)
    inv=F(1)/(F(6)*uv[...,0]-F(16)*uv[...,1]+F(12));x=F(9)*uv[...,0]*inv;cy=F(4)*uv[...,1]*inv
    scale=y/cy;xyz=np.stack((scale*x,y,scale*(F(1)-x-cy)),axis=-1)
    matrix=np.array([[3.240969941904522,-1.537383177570094,-.4986107602930032],[-.9692436362808803,1.875967501507721,.04155505740717569],[.05563007969699373,-.2039769588889765,1.056971514242878]],F)
    rgb=np.maximum(xyz@matrix.T,F(0));return np.where((le!=0)[...,None],rgb,F(0))


def spread(x):
    x=x.astype(U);x=(x|(x<<8))&0x00ff00ff;x=(x|(x<<4))&0x0f0f0f0f;x=(x|(x<<2))&0x33333333;return (x|(x<<1))&0x55555555


def jenkins(x):
    x=np.asarray(x,U).copy()
    x=(x+U(0x7ed55d16))+(x<<12);x=(x^U(0xc761c23c))^(x>>19);x=(x+U(0x165667b1))+(x<<5)
    x=(x+U(0xd3a2646c))^(x<<9);x=(x+U(0xfd7046c5))+(x<<3);return (x^U(0xb55a4f09))^(x>>16)


class Random:
    def __init__(self,w,h,frame,variant):
        y,x=np.indices((h,w),dtype=U);morton=spread(x.ravel())|(spread(y.ravel())<<1)
        self.seed=jenkins(morton)+U(frame+(33+variant)*31);self.index=np.ones(w*h,U)
    def next(self,mask=None):
        k=self.index*U(0xcc9e2d51);k=((k<<15)|(k>>17))*U(0x1b873593);v=self.seed^k
        v=((v<<13)|(v>>19))*U(5)+U(0xe6546b64);v^=U(4);v^=v>>16;v*=U(0x85ebca6b);v^=v>>13;v*=U(0xc2b2ae35);v^=v>>16
        self.index+=U(1) if mask is None else np.asarray(mask,U)
        return (v&0x7fffff).astype(F)/F(8388608)


def neighbors(w,h,start,offset,table):
    y,x=np.indices((h,w),dtype=np.int32);d=(table[(start+offset)&8191]*F(32)).astype(np.int32)
    xy=np.stack((x.ravel(),y.ravel()),axis=-1)+d
    size=np.array([w,h],np.int32);xy=(xy%(2*size)+2*size)%(2*size);xy=np.minimum(xy,2*size-1-xy)
    return xy[:,1]*w+xy[:,0]


def candidates(source,raw,w,h,case,variant,frame,offsets):
    """Exact fixed-fixture candidate pools; no assertion of reservoir choice probabilities."""
    n=w*h;rgb=raw[:,2,:3];initial_weight=np.where(raw[:,0,3]>0,F(1)/np.maximum(raw[:,0,3],F(1e-20)),F(0))
    pool=[dict(rgb=rgb,weight=initial_weight,m=np.ones(n,U),age=np.zeros(n,U),valid=np.ones(n,bool),origin='current')]
    if variant==0:return pool
    rng=Random(w,h,frame,variant);first=rng.next()
    table=np.frombuffer(offsets,np.int8).reshape(8192,2).astype(F)/F(127)
    valid_geometry=case!=4;previous=case not in (5,6);age_limit=1 if case==7 else 30
    def add(index,temporal=False,fused=False):
        data=source[index];valid=np.full(n,valid_geometry,bool)
        age=(data['misc']>>8)&255;m=data['misc']&255
        if temporal or fused:
            valid&=previous
            valid&=(age<age_limit) if fused else (age+1<=age_limit)
            age=age+1;m=np.minimum(m,8)
        pool.append(dict(rgb=decode(data['radiance']),weight=data['weight'],m=m,age=age,valid=valid,origin='neighbor'))
    if variant in (1,2):
        start=(first*F(8191)).astype(np.int32)
        for i in range(2):add(neighbors(w,h,start,i,table))
    elif variant in (3,4):add(np.arange(n),temporal=True)
    else:
        start=(rng.next()*F(8191)).astype(np.int32);add(np.arange(n),fused=True)
        for i in (6,7):add(neighbors(w,h,start,i,table),fused=True)
    return pool


def expected_candidates(pool,case,variant):
    m=np.zeros(len(pool[0]['m']),U);sum_weights=np.zeros(len(m),F)
    for c in pool:
        valid=c['valid'];target=np.sum(c['rgb']*LUMA,axis=1,dtype=F)/PI
        m+=np.where(valid,c['m'],0).astype(U);sum_weights+=np.where(valid,target*c['weight']*c['m'].astype(F),F(0))
    result=[];traced=variant in (2,4,5)
    for c in pool:
        target=np.sum(c['rgb']*LUMA,axis=1,dtype=F)/PI
        if case==3 and traced:
            weight=np.divide(sum_weights,target,out=np.zeros_like(target),where=target>0)
            if c['origin']!='current':weight[:]=0
        else:weight=np.divide(sum_weights,target*m.astype(F),out=np.zeros_like(target),where=target>0)
        if variant==0:weight=c['weight']
        shaded=c['rgb']*(F(1)/PI)*weight[:,None]
        if case in (2,3,4):shaded[:]=0
        result.append(dict(rgb=c['rgb'],shaded=shaded,weight=weight,age=c['age'],valid=c['valid']))
    return m,result

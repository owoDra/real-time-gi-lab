#!/usr/bin/env python3
"""049/050 deterministic frame-sequence generator in the N007 state format.

A base exported state is animated per frame by a camera orbit, a light orbit,
a rigid instance transform and/or a vertex deformation of one instance."""
import json
import math
from pathlib import Path
import struct
import numpy as np

MAGIC=b'N007-STATE1\0'
REGIMES=('static','camera','light','rigid','deform','combined')


def read(state):
    state=Path(state);g=(state/'geometry-state.bin').read_bytes();f=(state/'frame-state.bin').read_bytes()
    ver,n=struct.unpack_from('<2I',g,0);assert ver==1 and len(g)==8+52*n and f[:12]==MAGIC and len(f)==148
    rec=np.frombuffer(g,dtype=np.dtype([('v','<f4',(9,)),('meta','<u4',(4,))]),offset=8).copy()
    params=np.frombuffer(f,dtype='<f4',count=24,offset=20).reshape(6,4).copy()
    return dict(rec=rec,frame=bytearray(f),params=params)


def write(out,base,verts,params):
    out.mkdir(parents=True);rec=base['rec'].copy();rec['v']=verts.reshape(-1,9).astype('<f4')
    (out/'geometry-state.bin').write_bytes(struct.pack('<2I',1,len(rec))+rec.tobytes())
    f=bytearray(base['frame']);f[20:116]=params.astype('<f4').tobytes();(out/'frame-state.bin').write_bytes(bytes(f))


def rot_y(angle):
    c,s=math.cos(angle),math.sin(angle);return np.array([[c,0,s],[0,1,0],[-s,0,c]])


def moving_instance(base,chosen=None):
    """Explicit instance, else the second-largest by triangle count (the largest is the static environment)."""
    if chosen is not None:return int(chosen)
    inst,count=np.unique(base['rec']['meta'][:,2],return_counts=True);order=np.argsort(-count,kind='stable')
    return int(inst[order[1]]) if len(inst)>1 else int(inst[0])


def frame(base,regime,t,speed,instance=None):
    verts=base['rec']['v'].reshape(-1,3,3).astype(np.float64);p=base['params'].astype(np.float64).copy()
    lo,hi=verts.reshape(-1,3).min(0),verts.reshape(-1,3).max(0);center=(lo+hi)/2;extent=float(np.linalg.norm(hi-lo))
    if regime in ('camera','combined'):
        pos=p[0,:3];fwd=p[3,:3];dist=float(np.linalg.norm(center-pos));pivot=pos+fwd*dist;r=rot_y(math.radians(0.5*speed*t))
        p[0,:3]=pivot+r@(pos-pivot)
        for row in (1,2,3):p[row,:3]=r@p[row,:3]
    if regime in ('light','combined'):
        light=p[5,:3];r=rot_y(math.radians(1.0*speed*t));p[5,:3]=center+r@(light-center)
    if regime in ('rigid','combined'):
        m=base['rec']['meta'][:,2]==moving_instance(base,instance);c=verts[m].reshape(-1,3).mean(0)
        r=rot_y(math.radians(1.5*speed*t));shift=np.array([0.02*extent*math.sin(2*math.pi*speed*t/48),0,0])
        verts[m]=(verts[m]-c)@r.T+c+shift
    if regime=='deform':
        m=base['rec']['meta'][:,2]==moving_instance(base,instance);v=verts[m];lo_i,hi_i=v.reshape(-1,3).min(0),v.reshape(-1,3).max(0);size=float(np.linalg.norm(hi_i-lo_i))
        phase=2*math.pi*(v[...,0]-lo_i[0])/max(size,1e-6)+2*math.pi*speed*t/32
        v[...,1]+=0.03*size*np.sin(phase)*((v[...,1]-lo_i[1])/max(hi_i[1]-lo_i[1],1e-6));verts[m]=v
    return verts,p


def generate(state,out,regime,frames,speed=1.0,instance=None):
    assert regime in REGIMES;out=Path(out);assert not out.exists();base=read(state);out.mkdir(parents=True)
    for t in range(frames):
        verts,p=frame(base,regime,t,speed,instance);write(out/f'{t:04d}',base,verts,p)
    (out/'sequence.json').write_text(json.dumps(dict(state=str(state),regime=regime,frames=frames,speed=speed,moving_instance=moving_instance(base,instance)),indent=1)+'\n')
    return out


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('state');ap.add_argument('out');ap.add_argument('--regime',choices=REGIMES,required=True)
    ap.add_argument('--frames',type=int,required=True);ap.add_argument('--speed',type=float,default=1.0);ap.add_argument('--instance',type=int);a=ap.parse_args()
    print(generate(a.state,a.out,a.regime,a.frames,a.speed,a.instance))

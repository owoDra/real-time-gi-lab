#!/usr/bin/env python3
"""049 development runs (disclosed dev only): proxy references, role runs and gate scores."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'out/research/lane-m-gi-competitiveness'
BUILD=BASE/'rtcv-dev-build';SEQ=BASE/'rtcv-dev-sequences';RUNS=BASE/'rtcv-dev-runs'
N=57600


def run(seq,out,role,k,frames,capture,depth,seed=1,k_new=4,n_max=64,ref_spp=0,build=BUILD):
    if out.exists():return out
    cmd=[str(build/'rtcv-sequence'),'--capture','--sequence',str(seq),'--frames',str(frames),'--out',str(out),'--vertices',str(depth),'--shaders',str(build),'--role',role,
         '--k',str(k),'--k-new',str(k_new),'--n-max',str(n_max),'--capture',','.join(map(str,capture)),'--seed',str(seed),'--ref-spp',str(ref_spp)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode!=0:raise RuntimeError(f'{out.name}: {r.stderr[-400:]}')
    return out


def image(out,f):return np.fromfile(out/f'frame-{f:04d}.f32','<f4').reshape(N,2).astype(float)


def reference(seq,depth,frames,capture,spp=16384,seeds=4):
    outs=[run(seq,RUNS/f'ref-{seq.name}-b{depth}-s{s}',"PT",1,frames,capture,depth,seed=1000+s,ref_spp=spp) for s in range(seeds)]
    return {f:np.mean([image(o,f) for o in outs],axis=0) for f in capture}


def metrics(img,ref):
    out={}
    for name,g,r in (('indirect',img[:,1],ref[:,1]),('total',img.sum(1),ref.sum(1))):
        e=g-r;out[name]=dict(nrmse=math.sqrt(float(np.mean(e*e)))/math.sqrt(float(np.mean(r*r))),bias=float(e.sum()/r.sum()))
    out['pass']=out['total']['nrmse']<=.05 and out['indirect']['nrmse']<=.10 and abs(out['indirect']['bias'])<=.05
    return out


def timing(out):
    rows=[json.loads(l) for l in (out/'frames.jsonl').read_text().splitlines()]
    return rows


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--seqs',nargs='+',required=True);ap.add_argument('--depth',type=int,default=8);ap.add_argument('--frames',type=int,default=64)
    ap.add_argument('--capture',default='0,16,32,48,63');ap.add_argument('--roles',nargs='+',default=['PT:1','PTA:1','RTCV:1']);ap.add_argument('--tag',default='v1')
    ap.add_argument('--n-max',type=int,default=64);ap.add_argument('--k-new',type=int,default=4);ap.add_argument('--build',default=str(BUILD));a=ap.parse_args()
    RUNS.mkdir(exist_ok=True);cap=[int(x) for x in a.capture.split(',')];build=Path(a.build)
    for name in a.seqs:
        seq=SEQ/name;ref=reference(seq,a.depth,a.frames,cap)
        for spec in a.roles:
            role,k,*rest=spec.split(':');nm=int(rest[0]) if rest else a.n_max
            out=run(seq,RUNS/f'{a.tag}-{name}-b{a.depth}-{role}-k{k}-n{nm}',role,int(k),a.frames,cap,a.depth,n_max=nm,k_new=a.k_new,build=build)
            t=timing(out);us=np.mean([r['render_gpu_us']+r['as_gpu_us'] for r in t[1:]])
            row=[];ok=True
            for f in cap:
                m=metrics(image(out,f),ref[f]);ok&=m['pass'] if f>=cap[2] else True
                row.append(f"{f}:{m['indirect']['nrmse']:.3f}/{m['indirect']['bias']:+.3f}{'P' if m['pass'] else 'F'}")
            print(f'{name:14s} {role:5s} k={k:>4s} n={nm:4d} us={us:8.1f} warm_pass={ok!s:5s}',' '.join(row),flush=True)

#!/usr/bin/env python3
"""050/M003: unseen heldout sequences, reference qualification, role ladders and scoring."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import m002_states as M2
import rtcv_sequences as Q

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'out/research/lane-m-gi-competitiveness'
EXP=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments'
OUT=BASE/'m003-states-v1';SEQ=BASE/'m003-sequences-v1';REFS=BASE/'m003-references-v1';RUNS=BASE/'m003-runs-v1'
N010=ROOT/'research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json'
R1VIEW=ROOT/'out/research/n010-comparison-readiness/full-corpus-r1-view-v1'
sys.path.insert(0,str(ROOT/'scripts/research/n008_hdr_oracle'));import n008lib as L
FRAMES=192;SPEED=0.5;SMALL_EVAL=(160,191);SPONZA_EVAL=(191,)
SCENES={'N1':('world','dense',None),'N2':('world','vertical-tall',None),'N3':('leak','thick',0.29),'N4':('leak','grazing',0.25),'N5':('leak','enclosed',0.21)}
REGIMES=('static','camera','light','rigid','deform')
SPONZA={'SC1':'C1','SC2':'C2','SC3':'C3','SC4':'C4','SC5':'C5','SC6':'C6'}
LADDERS={'PT':[(k,1) for k in (64,128,256,512,1024,2048,4096)],'PTR':[(k,1) for k in (4,16,64,256)],
         'PTA':[(4,256),(16,32),(16,16),(64,16),(64,8),(256,8),(256,4)],'PTG':[(4,256),(16,256),(64,256)],
         'RTCVF':[(k,256) for k in (4,8,16,32,64)]}
K_NEW=32;SEED=1


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,why):
    if not ok:raise ValueError('050 '+why)


def scenes():
    """Unseen procedural scenes (CPU exporter, M001/M002 contract) and their sequences; Sponza
    transitions from the N010 lock026 source states to the locked targets."""
    need(not OUT.exists() and not SEQ.exists(),'exclusive M003 states');OUT.mkdir();SEQ.mkdir();m=M2.factory();g=OUT/'gltf'
    manifest=dict(schema='m003-states/1',factory_sha256=sha(M2.FACTORY),exporter_sha256=sha(M2.EXPORTER),contract_sha256=sha(M2.CONTRACT),frames=FRAMES,speed=SPEED,scenes={},sequences={})
    for name,(family,kind,thickness) in SCENES.items():
        groups=m.leak_scene(kind,thickness) if family=='leak' else m.world_scene(kind)
        gltf=m.write_gltf(g,'M003-'+name,groups);info=M2.export(gltf,OUT/name,'static')
        manifest['scenes'][name]=dict(family=family,kind=kind,thickness=thickness,gltf_sha256=sha(gltf),exporter=info,state=L.read_state(OUT/name)['sha256'])
        inst=Q.m003_instance(OUT/name)
        for regime in REGIMES:
            out=SEQ/f'{name}-{regime}';Q.generate(OUT/name,out,regime,FRAMES,SPEED,inst)
            manifest['sequences'][out.name]=dict(scene=name,regime=regime,moving_instance=inst,eval=list(SMALL_EVAL))
    lock=json.loads(N010.read_text())['cells']
    for name,cell in SPONZA.items():
        spec=lock[cell];target=ROOT/spec['state_directory'];out=SEQ/name
        if 'source_directory' in spec:Q.transition(ROOT/spec['source_directory'],target,out,FRAMES)
        else:
            out.mkdir()
            for t in range(FRAMES):
                d=out/f'{t:04d}';d.mkdir()
                for f in ('geometry-state.bin','frame-state.bin'):(d/f).write_bytes((target/f).read_bytes())
        last=L.read_state(out/f'{FRAMES-1:04d}');need(last['sha256']==spec['state_sha256'],'Sponza final frame equals the locked target '+name)
        manifest['sequences'][name]=dict(scene='sponza',n010_cell=cell,scenario=spec.get('scenario','static'),eval=list(SPONZA_EVAL))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=1)+'\n');return manifest


def cells():
    """Reference cells: one per small sequence and evaluated frame."""
    man=json.loads((OUT/'manifest.json').read_text());out={}
    for name,s in man['sequences'].items():
        if s['scene']=='sponza':continue
        for f in s['eval']:out[f'{name}-f{f}']=SEQ/name/f'{f:04d}'
    return out


def lock():
    p=OUT/'lock.json';need(not p.exists(),'exclusive lock')
    c={k:dict(state_directory=str(v.relative_to(ROOT)),state_sha256=L.read_state(v)['sha256']) for k,v in cells().items()}
    p.write_text(json.dumps(dict(cells=c),indent=1)+'\n');return p


def qualify(cell):
    REFS.mkdir(exist_ok=True);out=REFS/f'{cell}-result.json';need(not out.exists(),'one qualification per cell')
    run=subprocess.run([sys.executable,str(ROOT/'scripts/research/n010_comparison_readiness/qualify_references.py'),'--lock',str(OUT/'lock.json'),'--validation',str(M2.VALIDATION),'--cells',cell,'--work',str(REFS),'--output',str(out)],capture_output=True,text=True)
    (REFS/f'{cell}-qualify.log').write_text(run.stdout+run.stderr);need(run.returncode==0,'qualification '+cell)


def reference(seq,frame,depth):
    """Admitted four-seed luminance mean (N010 RQMC oracle), or None if not eligible."""
    man=json.loads((OUT/'manifest.json').read_text())['sequences'][seq]
    if man['scene']=='sponza':
        d=R1VIEW/f"{man['n010_cell']}_T_B{depth}";q=json.loads((d/'qualification.json').read_text())
        rule='original' if q['classification']=='STATISTICALLY_ELIGIBLE' else 'R1' if (d/'r1-eligibility.json').exists() and json.loads((d/'r1-eligibility.json').read_text())['classification']=='R1_STATISTICALLY_ELIGIBLE' else None
        state=L.read_state(SEQ/seq/f'{frame:04d}')
        need(q['state_sha256']==state['sha256'],'Sponza reference state equals the sequence frame')
    else:
        d=REFS/f'{seq}-f{frame}_T_B{depth}';q=json.loads((d/'qualification.json').read_text())
        rule='original' if q['classification']=='STATISTICALLY_ELIGIBLE' else None
    if rule is None:return None,dict(directory=str(d),classification=q['classification'])
    level=q['levels'][-1]['spp'];means=np.mean([L.read_sidecar(d/f'o.n{level}.s{i}.f64')['mean'] for i in range(4)],axis=0)
    lum=np.array([0.2126,0.7152,0.0722])
    return {k:means[...,L.COMPONENTS.index(k),:].reshape(-1,3)@lum for k in ('direct','indirect','total')},dict(directory=str(d),classification=q['classification'],rule=rule,spp=level)


def metrics(direct,indirect,ref):
    out={}
    for name,g in (('direct',direct),('indirect',indirect),('total',direct+indirect)):
        r=ref[name].ravel().astype(float);e=g.ravel().astype(float)-r
        out[name]=dict(nrmse=math.sqrt(float(np.mean(e*e)))/math.sqrt(float(np.mean(r*r))),signed_sum_bias=float(e.sum()/r.sum()))
    out['pass']=out['total']['nrmse']<=.05 and out['indirect']['nrmse']<=.10 and abs(out['indirect']['signed_sum_bias'])<=.05
    return out


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['scenes','lock','qualify']);ap.add_argument('--cell');a=ap.parse_args()
    if a.mode=='scenes':print(json.dumps({k:v for k,v in scenes()['sequences'].items()},indent=0)[:2000])
    elif a.mode=='lock':print(lock())
    else:qualify(a.cell)

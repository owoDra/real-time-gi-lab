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
LADDERS={'PT':[(k,1) for k in (16,64,128,256,512,1024,2048,4096)],'PTR':[(k,1) for k in (4,16,64,256)],
         'PTA':[(k,n) for k in (1,2,4,8,16,32,64,128) for n in (4,8,16,64,256)],'PTG':[(k,256) for k in (1,2,4,8,16,32,64,128)],
         'RTCVS':[(k,256) for k in (1,2,4,8,16,32,64)]}
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


BUILD=BASE/'m003-build-v1';CAL=BASE/'m003-calibration-v1';TIMING=BASE/'m003-timing-v1'
CANDIDATE='RTCVS';SETTLE=156;MEASURED=32


def committed():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    need(subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='research-lane-m-gi-competitiveness','research branch')
    own=[EXP/'050-m003-rtcvf-unseen-heldout-validation.md',Path(__file__).resolve(),Path(Q.__file__).resolve(),ROOT/'scripts/research/lane_m_gi_competitiveness/m003_build.py',
         ROOT/'src/research/lane_m_gi_competitiveness/rtcv_sequence_gpu.cpp',ROOT/'shaders/research/lane_m_gi_competitiveness/rtcv_sequence.comp.glsl']
    for f in own:need(subprocess.check_output(['git','show',head+':'+str(f.relative_to(ROOT))],cwd=ROOT)==f.read_bytes(),'commit all 050 sources before use '+f.name)
    return head


def build():
    head=committed();need(not BUILD.exists(),'exclusive build');import m003_build as MB
    r=MB.build(BUILD);r['source_commit']=head;(BUILD/'result.json').write_text(json.dumps(r,indent=1)+'\n');need(r['all_pass'],'build');return r


def targets():
    """(sequence, depth, evaluated frames) for every M003 target, in fixed order."""
    man=json.loads((OUT/'manifest.json').read_text())['sequences'];rows=[]
    for name,s in man.items():
        for depth in (2,8):rows.append((name,depth,tuple(s['eval'])))
    return rows


def run(seq,role,k,n,depth,frames_eval,out,stateless_skip):
    need(not out.exists(),'exclusive run '+out.name)
    cmd=[str(BUILD/'rtcv-sequence'),'--capture','--sequence',str(SEQ/seq),'--frames',str(FRAMES),'--out',str(out),'--vertices',str(depth),'--shaders',str(BUILD),
         '--role',role,'--k',str(k),'--k-new',str(K_NEW),'--n-max',str(n),'--capture',','.join(map(str,frames_eval)),'--seed',str(SEED),'--ref-spp','0','--stateless-skip','1' if stateless_skip else '0']
    p=subprocess.run(cmd,capture_output=True,text=True);(out.parent/(out.name+'.stderr')).write_text(p.stderr)
    need(p.returncode==0,f'run {out.name}: {p.stderr[-300:]}');return out


def image(out,f):return np.fromfile(out/f'frame-{f:04d}.f32','<f4').reshape(-1,2).astype(float)


def ladders(only=None):
    """Quality ladders of every in-harness role on every eligible target (one fixed seed)."""
    head=committed();need(json.loads((BUILD/'result.json').read_text())['all_pass'],'build');RUNS.mkdir(exist_ok=True)
    out=RUNS/'ladders.jsonl';done=set()
    if out.exists():done={(r['seq'],r['depth'],r['role'],r['k'],r['n']) for r in map(json.loads,out.read_text().splitlines())}
    roles=[(r,LADDERS[r]) for r in (CANDIDATE,'PT','PTR','PTA','PTG')]
    for seq,depth,ev in targets():
        if only and seq not in only:continue
        refs={f:reference(seq,f,depth) for f in ev}
        if any(r[0] is None for r in refs.values()):
            if (seq,depth,'REF',0,0) not in done:
                with out.open('a') as f:f.write(json.dumps(dict(seq=seq,depth=depth,role='REF',k=0,n=0,decision='REFERENCE_INELIGIBLE',refs={str(k):v[1] for k,v in refs.items()},source_commit=head))+'\n')
            continue
        for role,ladder in roles:
            for k,n in ladder:
                if (seq,depth,role,k,n) in done:continue
                o=run(seq,role,k,n,depth,ev,RUNS/f'{seq}-b{depth}-{role}-k{k}-n{n}',role in ('PT','PTR'))
                ms={f:metrics(image(o,f)[:,0],image(o,f)[:,1],refs[f][0]) for f in ev}
                frames=[json.loads(l) for l in (o/'frames.jsonl').read_text().splitlines()]
                row=dict(seq=seq,depth=depth,role=role,k=k,n=n,metrics={str(f):m for f,m in ms.items()},quality_pass=all(m['pass'] for m in ms.values()),
                         gpu_us_descriptive=float(np.mean([r['render_gpu_us']+r['as_gpu_us'] for r in frames if r['render_gpu_us']>0][-32:])),refs={str(f):refs[f][1] for f in ev},source_commit=head)
                with out.open('a') as f:f.write(json.dumps(row)+'\n')
                print('050',seq,depth,role,k,n,row['quality_pass'],flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['scenes','lock','qualify','build','ladders']);ap.add_argument('--cell');a=ap.parse_args()
    if a.mode=='scenes':print(json.dumps({k:v for k,v in scenes()['sequences'].items()},indent=0)[:2000])
    elif a.mode=='lock':print(lock())
    elif a.mode=='build':print(build()['all_pass'])
    elif a.mode=='ladders':ladders()
    else:qualify(a.cell)

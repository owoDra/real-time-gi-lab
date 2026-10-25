#!/usr/bin/env python3
"""046/M002: build, positive control, ladder captures, scoring and 045-protocol timing on new targets."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import numpy as np
import frame_timing_bridge as T
import m002_states as M

Q,G,C=T.Q,T.G,T.C
ROOT,BASE,EXP=T.ROOT,T.BASE,T.EXP
OWN=[EXP/'046-m002-new-heldout-and-dynamic-validation.md',EXP/'046a-capture-details-and-positive-control.md',T.CPP,*T.GLSL,Path(T.__file__),Path(__file__).resolve(),Path(M.__file__)]
CAPTURES=BASE/'m002-captures-v1';CONTROL=BASE/'m002-positive-control-v2'
REFUSED_CONTROL=BASE/'m002-positive-control-v1'  # quiet-gate refusal before any GPU work (reference oracles active)
PT_LADDER=(16,64,256,1024);PTR_LADDER=(4,16,64)
read,sha,need=T.read,T.sha,T.need
T.PREP=BASE/'m002-cpu-build-v2';T.CAL=BASE/'m002-calibration-v1'
CAPTURE_PREP=BASE/'m002-cpu-build-v1'  # positive control and ladders used this build (pins predate the control-root edit)


def committed():
    head=Q.git('rev-parse','HEAD');need(Q.git('branch','--show-current')=='research-lane-m-gi-competitiveness','research branch')
    for anchor in ('f4e9434e','d3313085'):subprocess.run(['git','merge-base','--is-ancestor',anchor,head],cwd=ROOT,check=True)
    for p in OWN:need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'commit all046 sources before use '+p.name)
    return head
T.committed=committed;T.OWN=OWN


def targets():
    return [(cell,depth) for cell in M.CELLS for depth in (2,8)]


def reference(cell,depth):
    d=M.REFS/f'{cell}_T_B{depth}';q=read(d/'qualification.json')
    if q['classification']!='STATISTICALLY_ELIGIBLE':return None,d,q
    level=q['levels'][-1];G.rehash({str(d/k):v for k,v in level['all_payload_sha256'].items()})
    sys.path.insert(0,str(ROOT/'scripts/research/n008_hdr_oracle'));import n008lib as L
    means=np.mean([L.read_sidecar(d/f"o.n{level['spp']}.s{i}.f64")['mean'] for i in range(4)],axis=0)
    return {k:means[...,L.COMPONENTS.index(k),:]@Q.R.LUMA for k in ('direct','indirect','total')},d,q


def capture(state,depth,role,spp,root):
    import integrated_pt_process as P
    need(not root.exists(),'exclusive capture, no retry');P.quiet();root.mkdir(parents=True)
    args=[str(T.PREP/'frame-timing'),'--capture','--state',str(state),'--out',str(root/'capture'),'--vertices',str(depth),'--shaders',str(T.PREP),'--offsets',str(Q.OFFSETS),'--role',role,'--spp',str(spp)]
    row=G.guard(args,root,'native');j=read(root/'capture/complete.json');need(j['complete'] and j['aggregate_reserved_at_teardown']==0,'complete capture')
    image=np.fromfile(root/'capture/image.f32','<f4').reshape(Q.R.N,2);need(np.isfinite(image).all() and (image>=0).all(),'finite nonnegative capture')
    return image,row


def score(image,ref):return Q.score(image[:,0],image[:,1].astype(float),ref)


def control():
    head=committed();need(read(T.PREP/'result.json')['all_pass'],'preparation');need(not CONTROL.exists(),'one control');CONTROL.mkdir()
    r=dict(schema='m002-positive-control/1',source_commit=head,complete=False,all_pass=False,rows=[])
    try:
        r['effective_parent']=C.limits();state=G.source_state('H01',2,{});ref,_=Q.reference('H01',2)
        for role,spp in (('PT_REF',256),('PTR',16)):
            image,row=capture(state,2,role,spp,CONTROL/f'{role}-{spp}');m=score(image,ref);r['rows'].append(dict(role=role,spp=spp,metrics=m,quality_pass=Q.passes(m),process=row))
        need(all(x['quality_pass'] for x in r['rows']),'positive control passes');r.update(complete=True,all_pass=True,classification='CAPTURE_POSITIVE_CONTROL_PASS')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(CONTROL,r)


def ladders():
    head=committed();need(read(CONTROL/'result.json')['all_pass'],'positive control before targets');out=CAPTURES/'result.json';need(not out.exists(),'one ladder campaign')
    CAPTURES.mkdir(exist_ok=True);r=dict(schema='m002-ladders/1',source_commit=head,complete=False,all_pass=False,targets=[])
    try:
        r['effective_parent']=C.limits()
        for cell,depth in targets():
            ref,directory,q=reference(cell,depth);row=dict(cell=cell,depth=depth,reference_directory=str(directory),reference_classification=q['classification'],reference_spp=q['levels'][-1]['spp'],rungs=[])
            if ref is None:row['decision']='REFERENCE_INELIGIBLE';r['targets'].append(row);continue
            state=M.OUT/cell
            for role,ladder in (('PT_REF',PT_LADDER),('PTR',PTR_LADDER)):
                first=None
                for spp in ladder:
                    image,proc=capture(state,depth,role,spp,CAPTURES/f'{cell.lower()}-b{depth}/{role}-{spp}');m=score(image,ref)
                    row['rungs'].append(dict(role=role,spp=spp,metrics=m,quality_pass=Q.passes(m),pid=proc['pid']))
                    if Q.passes(m):first=spp;break
                row['pt_first_pass' if role=='PT_REF' else 'ptr_first_pass']=first
            r['targets'].append(row);print('046',cell,depth,row.get('pt_first_pass'),row.get('ptr_first_pass'),flush=True)
        r.update(complete=True,all_pass=True,classification='M002_LADDERS_COMPLETE')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(CAPTURES,r)


def timing(cell,depth):
    head=committed();lad=read(CAPTURES/'result.json');t=next(x for x in lad['targets'] if x['cell']==cell and x['depth']==depth)
    ref,recon=t.get('pt_first_pass'),t.get('ptr_first_pass');need(ref and recon,'matched pair exists');cal=read(T.CAL/'result.json');need(cal['all_pass'],'calibration')
    root=BASE/f'm002-timing-{cell.lower()}-b{depth}-v1';need(not root.exists(),'one campaign');root.mkdir();import integrated_pt_process as P
    r=dict(schema='m002-timing/1',source_commit=head,cell=cell,depth=depth,reference_spp=ref,recon_spp=recon,complete=False,all_pass=False,processes=[])
    try:
        r['effective_parent']=C.limits();state=M.OUT/cell
        for k in range(T.PROCESSES):
            P.quiet();pr=T.process_root(root,k);pr.mkdir()
            args=[str(T.PREP/'frame-timing'),'--target','--state',str(state),'--out',str(pr/'capture'),'--vertices',str(depth),'--shaders',str(T.PREP),'--offsets',str(Q.OFFSETS),'--process',str(k),'--reference-spp',str(ref),'--recon-spp',str(recon),'--measured',str(T.MEASURED)]
            row=T.native(args,pr,'native');j=read(pr/'capture/complete.json');need(j['complete'] and j['measured_pairs']==T.MEASURED and j['aggregate_reserved_at_teardown']==0,'complete process');r['processes'].append(dict(process=k,native=row))
        stats=T.campaign([T.process_root(root,k) for k in range(T.PROCESSES)],['T1','T2','T3','T4']);mde=cal['decision']['minimum_detectable_effect']
        threshold=None if mde is None or not cal['decision']['control_pass'] else math.log(1+mde)
        r.update(statistics=stats,t1=T.candidate_decision(stats['T1'],None if threshold is None else max(threshold,math.log(1.2))),buffers=read(T.process_root(root,0)/'capture/buffers.json'),
                 true_peak_owned_bytes=read(T.process_root(root,0)/'capture/allocation-ledger.json')['true_peak_owned_bytes'],complete=True,all_pass=True,classification='M002_TIMING_COMPLETE')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(root,r)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['build','calibrate','control','ladders','timing']);ap.add_argument('--cell');ap.add_argument('--depth',type=int);a=ap.parse_args()
    sys.exit({'build':T.build,'calibrate':T.calibrate,'control':control,'ladders':ladders}[a.mode]() if a.mode!='timing' else timing(a.cell,a.depth))

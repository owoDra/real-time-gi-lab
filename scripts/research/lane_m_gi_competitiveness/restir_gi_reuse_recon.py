#!/usr/bin/env python3
"""043 CPU screen: 042 ReSTIR/PT frames through the fixed 018/022 quadratic reconstruction."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import restir_gi_reuse_bridge as Q
import surface_quadratic_filter as S

G,C,R=Q.G,Q.C,Q.R
ROOT,BASE=Q.ROOT,Q.BASE
PROTOCOLS=[Q.EXP/'043-restir-reuse-quadratic-reconstruction-cpu-screen.md',Q.EXP/'043a-reconstruction-control-bound.md']
OWN=[*PROTOCOLS,Path(__file__).resolve(),Path(S.__file__),Path(S.B.__file__),Path(__file__).with_name('test_restir_gi_reuse_recon.py')]
OUT=BASE/'m001-restir043-cpu-screen-v1'
need,read,sha=Q.need,Q.read,Q.sha


def committed():
    head=Q.git('rev-parse','HEAD');need(Q.git('branch','--show-current')=='research-lane-m-gi-competitiveness','research branch')
    for anchor in ('7e68617b','50186de8','3149970f'):subprocess.run(['git','merge-base','--is-ancestor',anchor,head],cwd=ROOT,check=True)
    for p in OWN:need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'commit all043 sources before use '+p.name)
    return head


def archive022(cell,depth,pins):
    root=BASE/f'm001-integrated022-gpu-{cell.lower()}-b{depth}-v1';j=read(root/'result.json');need(j['complete'] and j['valid'],'admitted022 capture')
    for name in ('coefficients.f32','hits.u32','sources.f32','stages.f32','unclipped.f32'):
        key='capture/'+name;need(sha(root/key)==j['payload_sha256'][key],'022 payload identity '+name);pins[str(root/key)]=j['payload_sha256'][key]
    pins[str(root/'result.json')]=sha(root/'result.json')
    load=lambda name,shape:np.fromfile(root/'capture'/name,'<f4').reshape(shape)
    return dict(coefficients=load('coefficients.f32',(3,25,180,320)).astype(float),hits=np.fromfile(root/'capture/hits.u32','<u4').reshape(R.N,8),
                sources=load('sources.f32',(180,320)),stages=load('stages.f32',(3,180,320)),unclipped=load('unclipped.f32',(3,180,320)))


def control(a):
    """043a: CPU reuse of the 018 filter reproduces the archived 022 GPU stages within the 022 stage bound."""
    stages,unclipped,_=S.reconstruct(a['sources'].astype(float),a['coefficients']);previous=a['sources'].astype(float);worst=0.
    for k in range(3):
        scale=max(float(np.abs(previous).max()),1e-20)
        for cpu,gpu in ((unclipped[k],a['unclipped'][k]),(stages[k],a['stages'][k])):
            need(np.allclose(cpu,gpu,rtol=2e-5,atol=2e-7*scale),'043a reused filter reproduces022 stage');worst=max(worst,float(np.max(np.abs(cpu-gpu)/(2e-7*scale+2e-5*np.abs(gpu)))))
        previous=a['stages'][k].astype(float)
    return worst


def recon(indirect,coefficients):
    stages,unclipped,clipping=S.reconstruct(np.asarray(indirect,float).reshape(180,320),coefficients);return stages[-1],clipping


def evaluate(images,coefficients,ref):
    """images: (4,64,N,4). Returns all prespecified rows; every reconstructed frame is scored."""
    direct=images[0,0,:,0];rows=[];streams=[];clip=[]
    for s in range(4):
        row=dict(stream=s)
        for method,c in (('v1_null_trial',2),('pt',1)):
            per={}
            for f in [0,*range(48,64)]:
                out,cl=recon(images[s,f,:,c],coefficients);m=Q.score(direct,out.ravel(),ref);per[f]=m;clip.append(dict(stream=s,frame=f,method=method,stages=cl))
                rows.append(dict(stream=s,frame=f,method=method,metrics=m,quality_pass=Q.passes(m)))
            row[f'r1_{method}']=dict(cold_pass=Q.passes(per[0]),warm_pass=all(Q.passes(per[f]) for f in range(48,64)),warm_frames_passing=sum(Q.passes(per[f]) for f in range(48,64)),
                                     cold_indirect_nrmse=per[0]['indirect']['nrmse'],warm_indirect_nrmse_mean=float(np.mean([per[f]['indirect']['nrmse'] for f in range(48,64)])),
                                     warm_total_nrmse_mean=float(np.mean([per[f]['total']['nrmse'] for f in range(48,64)])))
            row[f'r1_{method}']['joint_pass']=row[f'r1_{method}']['cold_pass'] and row[f'r1_{method}']['warm_pass']
            out,cl=recon(images[s,:,:,c].astype(float).mean(axis=0),coefficients);m=Q.score(direct,out.ravel(),ref);check=Q.fsum_metrics(out,ref['indirect'])
            need(math.isclose(check['nrmse'],m['indirect']['nrmse'],rel_tol=1e-9),'independent fsum metric');row[f'r2_{method}']=dict(metrics=m,quality_pass=Q.passes(m),clipping=cl)
        streams.append(row)
    out,cl=recon(ref['indirect'],coefficients);rb=Q.score(ref['direct'].ravel(),out.ravel(),ref)
    return dict(streams=streams,r1_target_pass=all(r['r1_v1_null_trial']['joint_pass'] for r in streams),r1_pt_target_pass=all(r['r1_pt']['joint_pass'] for r in streams),
                r2_streams_passing={m:sum(r[f'r2_{m}']['quality_pass'] for r in streams) for m in ('v1_null_trial','pt')},reference_bias=dict(metrics=rb,quality_pass=Q.passes(rb),clipping=cl)),rows,clip


def worker(root):
    need(C.state()==Q.NUMERIC,'numeric worker envelope');need(not root.exists(),'exclusive worker');root.mkdir();C.write(root/'effective-worker.json',dict(pid=os.getpid(),effective=C.state()))
    r=dict(schema='m001-restir043-numeric-worker/1',source_commit=committed(),complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',pid=os.getpid(),targets=[])
    try:
        for cell,depth in Q.TARGETS:
            pins={};case=Q.case_root(cell,depth);j=G.pin_archive(case/'result.json',pins);need(j['classification']=='REUSE_CASE_AUDIT_PASS','published042 case');G.pin_archive(case/'audit/result.json',pins)
            a=archive022(cell,depth,pins);worst=control(a);capture=case/'capture'
            for s in range(4):
                for f in R.RECORD:need(np.fromfile(capture/f'stream-{s}/frame-{f}/hits.u32','<u4').reshape(R.N,8).tobytes()==a['hits'].tobytes(),'042 primary hits bit-identical to022')
            images=np.stack([np.fromfile(capture/f'stream-{s}/frames.f32','<f4').reshape(64,R.N,4) for s in range(4)])
            ref,directory=Q.reference(cell,depth,pins);summary,rows,clip=evaluate(images,a['coefficients'],ref);G.rehash(pins)
            tag=f'{cell.lower()}-b{depth}'
            with (root/f'{tag}-frames.json').open('x') as out:json.dump(rows,out)
            with (root/f'{tag}-clipping.json').open('x') as out:json.dump(clip,out)
            r['targets'].append(dict(cell=cell,depth=depth,control_stage_bound_max_ratio=worst,hits_identical_records=12,input_sha256=pins,**summary))
            print('043',cell,depth,'R1',summary['r1_target_pass'],'R1-PT',summary['r1_pt_target_pass'],'R2',summary['r2_streams_passing'],flush=True)
        need(C.state()==Q.NUMERIC,'numeric profile unchanged')
        r.update(complete=True,all_pass=True,classification='RECONSTRUCTION_SCREEN_SCORED',r1_targets_passing=sum(t['r1_target_pass'] for t in r['targets']),r1_pt_targets_passing=sum(t['r1_pt_target_pass'] for t in r['targets']))
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(root,r)


def run():
    head=committed();need(not OUT.exists(),'exclusive043');OUT.mkdir()
    r=dict(schema='m001-restir043-cpu-screen/1',source_commit=head,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',gpu_executed=False,rows=[])
    try:
        r['effective_parent']=C.limits()
        r['rows'].append(dict(label='contracts',process=G.guard([sys.executable,'-m','unittest','discover','-s',Path(__file__).parent,'-p','test_restir_gi_reuse_recon.py','-v'],OUT,'contracts')))
        r['numeric_process']=G.guard([sys.executable,Path(__file__).resolve(),'worker','--root',OUT/'audit'],OUT,'numeric',1200,1800);a=read(OUT/'audit/result.json')
        need(a['all_pass'] and a['pid']==r['numeric_process']['pid'] and len(a['targets'])==6,'supervised six-target screen')
        r.update(complete=True,all_pass=True,classification='RECONSTRUCTION_SCREEN_COMPLETE',numeric_audit=a)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(OUT,r)


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='mode',required=True);sub.add_parser('run')
    p=sub.add_parser('worker');p.add_argument('--root',type=Path,required=True);args=parser.parse_args()
    sys.exit(run() if args.mode=='run' else worker(args.root))

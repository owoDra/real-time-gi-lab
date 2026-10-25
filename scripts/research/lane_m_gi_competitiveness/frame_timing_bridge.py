#!/usr/bin/env python3
"""044 calibrated AB/BA GPU timing: preparation, neutral calibration, six target campaigns, analysis."""
import argparse
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import numpy as np
import restir_gi_reuse_bridge as Q

G,C,I,S=Q.G,Q.C,Q.I,Q.S
ROOT,BASE,EXP=Q.ROOT,Q.BASE,Q.EXP
PROTOCOLS=[EXP/n for n in ('044-calibrated-matched-quality-and-equal-cost-timing.md','044a-timing-development-disclosure.md','044b-calibration-boundary-sizes.md','044c-equal-cost-comparator.md')]
CPP=I.SOURCE/'frame_timing_gpu.cpp';GLSL=[I.SHADERS/f'timing_{n}.comp.glsl' for n in ('accumulate','copy','neutral')]
OWN=[*PROTOCOLS,CPP,*GLSL,Path(__file__).resolve(),Path(__file__).with_name('test_frame_timing_bridge.py')]
PREP=BASE/'m001-timing044-cpu-build-v1';CAL=BASE/'m001-timing044-calibration-v1'
REUSED={'integrated_producer.spv':Q.OLD022,'surface_quadratic_device.spv':Q.OLD022,'integrated_composite.spv':Q.OLD022,'physical_producer.spv':Q.OLD041,**{f'reuse_s{s}.spv':Q.PREP for s in range(5)}}
SIZES=dict(tiny=(1,600),short=(1,4400),multi=(16,1100));DELTAS=(0,5,10,20);PROCESSES=8;WARMUP=4;MEASURED=12
RUNGS={('H01',2):(256,16),('H01',8):(1024,64),('H02',2):(256,64),('H02',8):(1024,64),('H03',2):(256,64),('H03',8):(1024,64)}
L102,L103,L105=math.log(1.02),math.log(1.03),math.log(1.05)
need,read,sha=Q.need,Q.read,Q.sha


def committed():
    head=Q.git('rev-parse','HEAD');need(Q.git('branch','--show-current')=='research-lane-m-gi-competitiveness','research branch')
    for anchor in ('1f900a16','712a2907','5bf2dc2e','357208bb'):subprocess.run(['git','merge-base','--is-ancestor',anchor,head],cwd=ROOT,check=True)
    for p in OWN:need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'commit all044 sources before use '+p.name)
    return head


def comparison_stats(rows):
    """rows: measured pair records of one comparison in one process."""
    x=np.array([r['log_b_over_a'] for r in rows]);ab=np.array([r['log_b_over_a'] for r in rows if r['order']=='AB']);ba=np.array([r['log_b_over_a'] for r in rows if r['order']=='BA'])
    need(len(x)==MEASURED and len(ab)>0 and len(ba)>0 and np.isfinite(x).all(),'complete measured AB/BA pairs')
    return dict(median=float(np.median(x)),order_bias=float(abs(np.median(ab)-np.median(ba))),values=x.tolist())


def campaign(processes,names):
    """Fresh-process statistics per comparison from each process's pairs.jsonl."""
    out={}
    for name in names:
        per=[]
        for root in processes:
            rows=[json.loads(l) for l in (root/'capture/pairs.jsonl').read_text().splitlines()];rows=[r for r in rows if r['comparison']==name]
            need(len(rows)==WARMUP+MEASURED and [r['pair'] for r in rows]==list(range(WARMUP+MEASURED)),'complete pair sequence '+name)
            per.append(comparison_stats([r for r in rows if not r['warmup']]))
        medians=np.array([p['median'] for p in per]);values=np.concatenate([p['values'] for p in per]);effect=float(np.median(medians))
        sign=np.sign(effect) if effect!=0 else 1.
        out[name]=dict(effect=effect,ratio=math.exp(effect),process_medians=medians.tolist(),span=float(medians.max()-medians.min()),max_order_bias=max(p['order_bias'] for p in per),
                       same_sign_pair_fraction=float(np.mean(np.sign(values)==sign)),pairs=len(values))
    return out


def calibration_decision(stats):
    sizes={}
    for size in SIZES:
        c=stats[f'{size}-plus0'];envelope=max(abs(m) for m in c['process_medians'])
        control=all(abs(m)<=L102 for m in c['process_medians']) and c['span']<=L103 and c['max_order_bias']<=L102
        resolved={}
        for d in DELTAS[1:]:
            s=stats[f'{size}-plus{d}'];resolved[d]=control and min(s['process_medians'])>envelope and s['span']<=L105 and s['max_order_bias']<=L103 and s['same_sign_pair_fraction']>=.75
        sizes[size]=dict(control_pass=control,envelope=envelope,resolved=resolved)
    passing=[d for d in DELTAS[1:] if all(sizes[s]['resolved'][d] for s in SIZES)]
    return dict(sizes=sizes,control_pass=all(v['control_pass'] for v in sizes.values()),minimum_detectable_effect=(min(passing)/100 if passing else None))


def candidate_decision(s,threshold):
    if threshold is None:return 'TIMING_INCONCLUSIVE'
    m=np.array(s['process_medians']);ok=s['span']<=L105 and s['max_order_bias']<=L103 and s['same_sign_pair_fraction']>=.75
    if ok and (m<0).all() and s['effect']<=-threshold:return 'FASTER'
    if ok and (m>0).all() and s['effect']>=threshold:return 'SLOWER'
    return 'INCONCLUSIVE'


def native(command,root,label):
    return G.guard(command,root,label,120,180)


def build():
    head=committed();need(not PREP.exists() and shutil.disk_usage(BASE).free>=16*1024**3,'exclusive044 preparation');pins={str(p):sha(p) for p in [*OWN,Path(C.__file__),Path(G.__file__),Path(Q.__file__),Path(sys.executable),I.GLSLANG,I.VAL]}
    old022=G.pin_archive(Q.OLD022/'result.json',pins);G.pin_archive(Q.OLD041/'result.json',pins);prep042=G.pin_archive(Q.PREP/'result.json',pins);need(prep042['all_pass'],'qualified042 preparation')
    for cell,depth in Q.TARGETS:G.source_state(cell,depth,pins)
    pins[str(Q.OFFSETS)]=sha(Q.OFFSETS);PREP.mkdir();C.write(PREP/'inputs-before.json',dict(source_commit=head,input_sha256=pins))
    r=dict(schema='m001-timing044-cpu-preparation/1',source_commit=head,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',gpu_executed=False,input_sha256=pins,rows=[],compiled_dependency_sha256={})
    try:
        r['effective_parent']=C.limits();os.chdir(I.BUILD);os.environ.update(VK_ICD_FILENAMES='/044-no-gpu.json',VK_DRIVER_FILES='/044-no-gpu.json')
        for name,folder in REUSED.items():
            shutil.copyfile(folder/name,PREP/name);need(sha(PREP/name)==read(folder/'result.json')['payload_sha256'][name],'exact reused SPIR-V '+name)
        command=list(next(x['command'] for x in old022['rows'] if x['label']=='host-compile'))
        for flag,value in (('-c',CPP),('-o',PREP/'host.o'),('-MT',PREP/'host.o'),('-MF',PREP/'host.d')):command[command.index(flag)+1]=str(value)
        rows=[('host-compile',command)];command=list(next(x['command'] for x in old022['rows'] if x['label']=='host-link'))
        command=[str(PREP/'host.o') if x==str(Q.OLD022/'host.o') else '-Wl,--dependency-file='+str(PREP/'link.d') if x.startswith('-Wl,--dependency-file=') else x for x in command]
        command[command.index('-o')+1]=str(PREP/'frame-timing');rows.append(('host-link',command))
        for src in GLSL:
            stem=src.name.split('.')[0];rows.extend([(stem+'-compile',[I.GLSLANG,'-V','--target-env','vulkan1.3',src,'-o',PREP/(stem+'.spv')]),(stem+'-validate',[I.VAL,'--target-env','vulkan1.3',PREP/(stem+'.spv')]),(stem+'-disassemble',[I.VAL.parent/'spirv-dis',PREP/(stem+'.spv'),'-o',PREP/(stem+'.spvasm')])])
        rows.append(('new-python-contracts',[sys.executable,'-m','unittest','discover','-s',Path(__file__).parent,'-p','test_frame_timing_bridge.py','-v']))
        for cell,depth in Q.TARGETS:
            ref,recon=RUNGS[(cell,depth)];state=G.source_state(cell,depth,pins)
            rows.append((f'cpu-{cell.lower()}-b{depth}',[PREP/'frame-timing','--cpu-check','--state',state,'--out',PREP/f'cpu-{cell.lower()}-b{depth}','--vertices',depth,'--shaders',PREP,'--offsets',Q.OFFSETS,'--process',0,'--reference-spp',ref,'--recon-spp',recon]))
        for label,args in rows:print('044',label,'START',flush=True);r['rows'].append(dict(label=label,process=G.guard(args,PREP,label)));print('044',label,'PASS',flush=True)
        for name in shlex.split((PREP/'host.d').read_text().replace('\\\n',' '))[1:]:
            file=Path(name);file=file if file.is_absolute() else I.BUILD/file
            if file.is_file():r['compiled_dependency_sha256'][str(file)]=sha(file)
        G.rehash(pins);r.update(complete=True,all_pass=True,classification='CPU_TIMING_PREPARATION_PASS',reused_spirv=sorted(REUSED),new_glsl=3,native_cpu_input_checks=6)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(PREP,r)


def process_root(base,k):return base/f'process-{k}'


def calibrate():
    head=committed();prep=G.pin_archive(PREP/'result.json',{});need(prep['all_pass'],'preparation before GPU');need(not CAL.exists(),'exclusive calibration, no rerun');CAL.mkdir()
    import integrated_pt_process as P
    r=dict(schema='m001-timing044-calibration/1',source_commit=head,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',processes=[],sizes={k:dict(submits=v[0],base=v[1]) for k,v in SIZES.items()})
    try:
        r['effective_parent']=C.limits()
        for k in range(PROCESSES):
            P.quiet();root=process_root(CAL,k);root.mkdir()
            args=[str(PREP/'frame-timing'),'--calibration','--out',str(root/'capture'),'--shaders',str(PREP),'--process',str(k),'--tiny',str(SIZES['tiny'][1]),'--short',str(SIZES['short'][1]),'--multi',str(SIZES['multi'][1])]
            print('044 calibration process',k,'START',flush=True);row=native(args,root,'native');j=read(root/'capture/complete.json')
            need(j['complete'] and j['comparisons']==12 and j['aggregate_reserved_at_teardown']==0,'complete calibration process');r['processes'].append(dict(process=k,native=row,complete=j))
        stats=campaign([process_root(CAL,k) for k in range(PROCESSES)],[f'{s}-plus{d}' for s in SIZES for d in DELTAS])
        r.update(statistics=stats,decision=calibration_decision(stats),complete=True,all_pass=True,classification='CALIBRATION_COMPLETE')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(CAL,r)


def target_root(cell,depth):return BASE/f'm001-timing044-{cell.lower()}-b{depth}-v1'


def quality_inputs(cell,depth):
    """Published per-frame indirect NRMSE: 043 RSR warm mean; 018 single-image reconstruction rows."""
    a=read(ROOT/'research/lanes/lane-m-gi-competitiveness/results/250-restir-reconstruction-cpu-screen.json');t=next(x for x in a['targets'] if x['cell']==cell and x['depth']==depth)
    q=read(ROOT/'research/lanes/lane-m-gi-competitiveness/results/112-surface-quadratic-reconstruction-six-targets-raw-replay.json');rec=next(x for x in q['records'] if x['cell']==cell and x['depth']==depth)
    rows={x['name']:x for x in rec['audit']['independent']}
    return dict(RSR=float(np.mean([s['warm_indirect_nrmse_mean'] for s in t['r1_v1']])),PT1R=rows['n1']['indirect_nrmse'],PT4R=rows['n4']['indirect_nrmse'],PT16R=rows['n16']['indirect_nrmse'])


def target(cell,depth):
    head=committed();root=target_root(cell,depth);need(not root.exists(),'one exclusive target campaign, no rerun')
    cal=G.pin_archive(CAL/'result.json',{});need(cal['all_pass'],'calibration completed before targets')
    for c,b in Q.TARGETS[:Q.TARGETS.index((cell,depth))]:need(read(target_root(c,b)/'result.json')['all_pass'],'previous target complete')
    pins={};state=G.source_state(cell,depth,pins);ref,recon=RUNGS[(cell,depth)];root.mkdir()
    import integrated_pt_process as P
    r=dict(schema='m001-timing044-target/1',source_commit=head,cell=cell,depth=depth,reference_spp=ref,recon_spp=recon,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',processes=[])
    try:
        r['effective_parent']=C.limits()
        for k in range(PROCESSES):
            P.quiet();pr=process_root(root,k);pr.mkdir()
            args=[str(PREP/'frame-timing'),'--target','--state',str(state),'--out',str(pr/'capture'),'--vertices',str(depth),'--shaders',str(PREP),'--offsets',str(Q.OFFSETS),'--process',str(k),'--reference-spp',str(ref),'--recon-spp',str(recon)]
            print('044',cell,depth,'process',k,'START',flush=True);row=native(args,pr,'native');j=read(pr/'capture/complete.json')
            need(j['complete'] and j['comparisons']==4 and j['aggregate_reserved_at_teardown']==0,'complete target process')
            for name in ('geometry-state.bin','frame-state.bin'):need((pr/'capture'/name).read_bytes()==(state/name).read_bytes(),'exact state')
            r['processes'].append(dict(process=k,native=row,complete=j))
        stats=campaign([process_root(root,k) for k in range(PROCESSES)],['T1','T2','T3','T4']);mde=cal['decision']['minimum_detectable_effect']
        threshold=None if mde is None or not cal['decision']['control_pass'] else math.log(1+mde);quality=quality_inputs(cell,depth)
        decisions={'T1':candidate_decision(stats['T1'],None if threshold is None else max(threshold,math.log(1.2)))}
        for name,comparator in (('T2','PT1R'),('T3','PT4R'),('T4','PT16R')):
            d=candidate_decision(stats[name],threshold);rsr_better=quality['RSR']<quality[comparator]
            dominance='RSR_DOMINATES' if d!='SLOWER' and rsr_better and d!='TIMING_INCONCLUSIVE' else (comparator+'_DOMINATES' if d!='FASTER' and not rsr_better and d!='TIMING_INCONCLUSIVE' else 'TRADEOFF_OR_INCONCLUSIVE')
            decisions[name]=dict(cost=d,rsr_relative_cost=stats[name]['ratio'],dominance=dominance)
        buffers=read(process_root(root,0)/'capture/buffers.json');ledger=read(process_root(root,0)/'capture/allocation-ledger.json')
        r.update(statistics=stats,decisions=decisions,quality_inputs=quality,threshold_log=threshold,buffers=buffers,true_peak_owned_bytes=ledger['true_peak_owned_bytes'],complete=True,all_pass=True,classification='TARGET_TIMING_COMPLETE')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(root,r)


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='mode',required=True);sub.add_parser('build');sub.add_parser('calibrate')
    p=sub.add_parser('target');p.add_argument('--cell',choices=['H01','H02','H03'],required=True);p.add_argument('--depth',type=int,choices=[2,8],required=True)
    args=parser.parse_args()
    sys.exit(build() if args.mode=='build' else calibrate() if args.mode=='calibrate' else target(args.cell,args.depth))

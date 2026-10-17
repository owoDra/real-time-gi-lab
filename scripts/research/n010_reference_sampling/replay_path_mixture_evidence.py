#!/usr/bin/env python3
"""Post-hoc metadata, math and termination replay for path-mixture evidence215-220."""
import hashlib
import itertools
import json
import os
from pathlib import Path
import resource
import subprocess
import numpy as np
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

NAMES={215:'215-whole-path-geometric-support-diagnosis.json',216:'216-coincident-predicate-witness.json',217:'217-whole-path-axis-cosine-diagnosis.json',218:'218-all-split-path-mixture-diagnosis.json',219:'219-bounded-all-split-furnace-control.json',220:'220-bounded-all-split-furnace-control.json'}
TARGET=D.RESULTS/'221-posthoc-path-mixture-evidence-replay.json'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if TARGET.exists():raise ValueError('refuse existing posthoc replay')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(60,)*2)
    inputs={str(Path(__file__).resolve()):sha(__file__)};results={};receipts=[];verified={}
    for number,name in NAMES.items():
        p=D.RESULTS/name;inputs[str(p)]=sha(p);r=json.loads(p.read_text());results[number]=r
        if 'ACQUIRING' in r['classification']:raise ValueError('result is not terminal')
        for key in ('input_sha256','payload_sha256'):
            for filename,h in r.get(key,{}).items():
                if filename in verified and verified[filename]!=h:raise ValueError('conflicting immutable input')
                if filename not in verified and sha(filename)!=h:raise ValueError('immutable identity changed: '+filename)
                verified[filename]=h
        for filename in r.get('payload_sha256',{}):
            if not filename.endswith('.resources.json'):continue
            rec=json.loads(Path(filename).read_text());proc=Path('/proc')/str(rec['pid'])/'stat'
            if proc.exists():
                state=proc.read_text().rsplit(')',1)[1].split()
                if int(state[19])==rec['start_ticks'] and state[0]!='Z':raise ValueError('owned native/compile process still live')
            if len(rec['affinity'])!=1 or rec['nice']!=15:raise ValueError('low-load receipt changed')
            receipts.append(dict(result=number,pid=rec['pid'],start_ticks=rec['start_ticks'],terminal=True,cpu_limits=rec['cpu']))
    if results[215]['complete'] or results[219]['complete']:raise ValueError('failed prototype/compile became complete')
    proof193=json.loads((D.RESULTS/'193-selected-bounce-path-diagnosis.json').read_text())
    original=next(v for v in proof193['variants'] if v['variant']=='original')
    old_header=next(Path(p) for p in original['payload_sha256'] if p.endswith('.hpp'))
    old_data=json.loads(next(Path(p) for p in original['payload_sha256'] if p.endswith('/data.json')).read_text())
    replay=[];control_audits=[]
    for number in (217,218):
        r=results[number]
        if not r['complete']:raise ValueError('complete numerical prototype required')
        data_path=next(Path(p) for p in r['payload_sha256'] if p.endswith('/data.json'))
        rows=json.loads(data_path.read_text());pixels=[tuple(p) for p in r['pixels']];metrics=[]
        for row in rows:
            prior=next(v for v in old_data if all(v[k]==row[k] for k in ('x','y','seed')))
            if np.array(row['mean']+row['second'],dtype='<f8').tobytes()!=np.array(prior['mean']+prior['second'],dtype='<f8').tobytes():raise ValueError('original moments changed')
            if np.array(row['mean'][:6],dtype='<f8').tobytes()!=np.array(row['mixture_mean'][:6],dtype='<f8').tobytes():raise ValueError('deterministic components changed')
        for prefix in ('','mixture_'):
            m=np.array([[next(row[prefix+'mean'] for row in rows if (row['x'],row['y'],row['seed'])==(x,y,seed)) for x,y in pixels] for seed in r['seeds']]).reshape(4,8,4,3)
            sec=np.array([[next(row[prefix+'second'] for row in rows if (row['x'],row['y'],row['seed'])==(x,y,seed)) for x,y in pixels] for seed in r['seeds']]).reshape(4,8,4,3)
            lum=m[:,:,2,:]@np.array([.2126,.7152,.0722])
            metrics.append(dict(max_pairwise_indirect_p99=max(float(np.quantile(np.abs(lum[i]-lum[j]),.99)) for i,j in itertools.combinations(range(4),2)),indirect_replicate_variance_sum=float(np.var(lum,axis=0,ddof=1).sum()),mean_path_variance_sum=float(np.maximum(sec[:,:,2,0]-m[:,:,2,0]**2,0).mean(0).sum())))
        ratios={k:metrics[1][k]/metrics[0][k] for k in metrics[0]}
        if ratios!=r['mixture_over_original']:raise ValueError('independent decision replay differs')
        promising=ratios['max_pairwise_indirect_p99']<=.75 and ratios['indirect_replicate_variance_sum']<=.5625
        if promising!=r['diagnostic_promising']:raise ValueError('unchanged prospective decision differs')
        inc=D.HERE/('whole_path_axis_cosine.inc' if number==217 else 'all_split_path_mixture.inc')
        header=next(Path(p) for p in r['payload_sha256'] if p.endswith('.hpp'));anchor='    // One camera sample; writes per-component radiance.'
        if D.once(header.read_text(),inc.read_text()+'\n'+anchor,anchor)!=old_header.read_text():raise ValueError('physical header source inverse differs')
        audit=dict(result=number,coincident_matches=sum(v['audit']['coincident_matches'] for v in rows),alternative_ray_checks=sum(v['audit']['alternative_ray_checks'] for v in rows),alternative_direct_checks=sum(v['audit']['alternative_direct_checks'] for v in rows))
        for key in ('max_own_log_error','max_target_error_fraction','max_unconditioned_target_error_fraction','max_coincident_normal_difference'):
            audit[key]=max(v['audit'][key] for v in rows)
        control_audits.append(audit);replay.append(dict(result=number,ratios=ratios,promising=promising,original_moments_and_deterministic_bits_exact=True,physical_source_inverse_exact=True))
    furnace=results[220]
    if not furnace['complete']:raise ValueError('bounded furnace incomplete')
    furnace_rows=json.loads(next(Path(p) for p in furnace['payload_sha256'] if p.endswith('/data.json')).read_text())
    bounds=furnace['furnace_geometry']['single_depth_envelope'];checks=[]
    for depth in (1,7):
        values={}
        for variant in ('mixture','iid'):
            vals=np.array([r[variant+'_depth_mean'][0] if depth==1 else r[variant+'_total_mean'] for r in furnace_rows]).reshape(8,4).mean(1)
            target=depth/np.pi;lower=depth*bounds[0]-.002*target;upper=depth*bounds[1]+.002*target
            checks.append(dict(kind='analytic_furnace',depth=depth,variant=variant,target=target,lower=lower,upper=upper,minimum=float(vals.min()),maximum=float(vals.max()),pass_=bool(((vals>=lower)&(vals<=upper)).all())))
            values[variant]=vals
        rel=float(abs(values['mixture'].mean()/values['iid'].mean()-1));nr=float(np.sqrt(np.mean((values['mixture']-values['iid'])**2)/np.mean(values['iid']**2)))
        checks.append(dict(kind='independent_iid',depth=depth,relative_mean_difference=rel,nrmse=nr,pass_=rel<=.002 and nr<=.01))
    if checks!=furnace['checks'] or all(v['pass_'] for v in checks)!=furnace['all_pass']:raise ValueError('furnace decision replay differs')
    if not all(r['dark_exact_zero'] for r in furnace_rows):raise ValueError('dark zero control differs')
    header220=next(Path(p) for p in furnace['payload_sha256'] if p.endswith('.hpp'))
    header218=next(Path(p) for p in results[218]['payload_sha256'] if p.endswith('.hpp'))
    if header220.read_bytes()!=header218.read_bytes():raise ValueError('physical-control method differs')
    for p,h in verified.items():
        if sha(p)!=h:raise ValueError('payload changed during replay')
    output=dict(schema='n010-posthoc-path-mixture-evidence-replay/1',complete=True,gpu_run=False,reference_admission=False,classification='POSTHOC_IDENTITIES_DECISIONS_AND_TERMINATION_REPLAYED_NO_ADMISSION',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),input_sha256=inputs,verified_payloads=verified,receipts=receipts,prototype_replay=replay,numerical_audits=control_audits,bounded_furnace_checks_replayed=True,
        scope='post-hoc replay only; numerical support approximation and all-state/full-suite/whole-frame/timing readiness remain unproved',tests='NOT_RUN; independent scientific evidence replay only')
    TARGET.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n');print(json.dumps({'complete':True,'payloads':len(verified),'receipts':len(receipts),'prototypes':replay,'audits':control_audits},indent=2))

if __name__=='__main__':main()

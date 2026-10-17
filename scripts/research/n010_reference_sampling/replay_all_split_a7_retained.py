#!/usr/bin/env python3
"""Plan084: close analysis crash, reuse identical A7 native payloads, no retry."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import numpy as np
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

OUTPUT=D.RESULTS/'231-posthoc-original-a7-retained-control.json'
FAILED=D.RESULTS/'230-all-split-original-a7-full-control.json'
WORK=D.OUT/'all-split-original-a7-v2'
PLAN=D.RESULTS.parent/'experiments/084-a7-retained-acquisition-analysis-repair.md'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if OUTPUT.exists():raise ValueError('refuse existing retained replay')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(220,)*2)
    D.checked(Path(__file__));D.checked(PLAN)
    D.checked(D.HERE/'validate_all_split_a7_full_repaired.py')
    pilot=json.loads(D.checked(D.RESULTS/'229-all-split-original-a7-cost-pilot.json'))
    if not pilot['complete'] or not pilot['cost_pass']:raise ValueError('actual cost229 required')
    for p,h in pilot['input_sha256'].items():D.checked(Path(p),h)
    for p,h in pilot['payload_sha256'].items():D.checked(Path(p),h)
    failed=json.loads(FAILED.read_text())
    if failed['complete'] or failed['classification']!='ORIGINAL_FULL_A7_ACQUIRING':raise ValueError('original unsealed analysis crash state required')
    snap=WORK/'full/control-unsealed-at-analysis-crash.json'
    if snap.exists():raise ValueError('refuse existing crash snapshot')
    snap.write_bytes(FAILED.read_bytes())
    rec=json.loads(D.checked(WORK/'full/native.resources.json'))
    p=Path('/proc')/str(rec['pid'])/'stat'
    if p.exists():
        state=p.read_text().rsplit(')',1)[1].split()
        if int(state[19])==rec['start_ticks'] and state[0]!='Z':raise ValueError('same native still live; do not relabel')
    if rec['cpu']!=[220,220] or rec['address_space']!=[4*1024**3]*2 or len(rec['affinity'])!=1 or rec['nice']!=15:raise ValueError('actual retained native limits differ')
    failed.update(classification='TERMINAL_ANALYSIS_METADATA_FAILURE_NATIVE_PAYLOADS_COMPLETE',failure='Observed controlling-process KeyError geometry_hash_match after native return and analytic calculation; native not retried',
        native_payloads_complete=True,native_returncode_capture='NOT_RETAINED_SEPARATELY; driver reached analytic stage after its zero-returncode guard',elapsed='NOT_RETAINED',child_cpu_seconds='NOT_RETAINED',
        native_pid_start_confirmed_terminal=True,payload_sha256={str(p):sha(p) for p in WORK.rglob('*') if p.is_file()})
    FAILED.write_text(json.dumps(failed,indent=2,allow_nan=False)+'\n');D.checked(FAILED)
    for p,h in failed['payload_sha256'].items():D.checked(Path(p),h)
    sys.path.insert(0,str(D.HERE.parent/'n010_comparison_readiness'));import validate_sampler as V
    for p in (Path(V.__file__),Path(V.P.__file__),Path(V.L.__file__)):D.checked(p)
    result=dict(schema='n010-posthoc-original-a7-retained-control/1',complete=False,all_pass=False,gpu_run=False,native_reexecuted=False,reference_admission=False,
        classification='POSTHOC_SAME_ACQUISITION_ANALYSIS',input_sha256=D.INPUTS,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        analysis_receipt=dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS))),tests='NOT_RUN; post-hoc same native acquisition analytic/iid replay')
    try:
        original=D.OUT/'sampler-validation-v1/rqmc';scene=original/'A7.n008';D.checked(scene)
        proof=json.loads(D.checked(D.RESULTS/'022-cached-oracle-equivalence.json'));prior=next(r for r in proof['rows'] if r['name']=='A7')
        original_meta=json.loads(D.checked(original/'A7.meta.json',prior['original_metadata_sha256']))
        if sha(scene)!=prior['scene_sha256']:raise ValueError('original scene identity differs')
        fresh=json.loads(D.checked(WORK/'full/A7.meta.json'))
        if fresh!=json.loads(D.checked(WORK/'full/native.stdout')):raise ValueError('metadata differs from actual native stdout')
        if any(fresh[k]!=original_meta[k] for k in ('scene_sha256','geometry_sha256','width','height','seeds','spp')) or fresh['spp']!=8192 or fresh['seeds']!=list(D.SEEDS):raise ValueError('native scope differs')
        rows=[V.L.read_sidecar(WORK/f'full/A7.s{i}.f64')for i in range(4)]
        old=[V.L.read_sidecar(original/f'A7.s{i}.f64')for i in range(4)]
        for p in prior['payloads']:D.checked(original/('A7'+p['payload']),p['old_sha256'])
        if any(new[k][...,:2,:].tobytes()!=prior[k][...,:2,:].tobytes() for new,prior in zip(rows,old) for k in ('mean','m2')):raise ValueError('original same-count deterministic bits differ')
        if (WORK/'full/A7.hits').read_bytes()!=(original/'A7.hits').read_bytes():raise ValueError('primary hits differ')
        if any(not(np.isfinite(r[k]).all() and (r[k]>=0).all())for r in rows for k in ('mean','m2')):raise ValueError('nonfinite/negative data')
        if any(r['seed']!=s or r['spp']!=8192 for r,s in zip(rows,D.SEEDS)):raise ValueError('sidecar seed/count differs')
        for r in fresh['runs']:
            a=r['all_split']
            if a['own_checks']!=a['component_attempts']-a['component_nulls'] or a['max_own_log_error']>1e-6 or a['max_conditioned_error_fraction']>1:raise ValueError('native proposal audit failed')
        means=np.stack([r['mean']for r in rows]);data=dict(mean=means.mean(0),se=means.std(0,ddof=1)/2,per_seed=rows,meta=fresh)
        def replay(res,sc,out,name,spp):
            if name!='A7' or spp!=8192 or sc.text()!=scene.read_text():raise ValueError('analytic input differs')
            m=dict(fresh);m.update(name=name,geometry_hash_match=m['geometry_sha256']==sc.geometry_sha256())
            if not m['geometry_hash_match']:raise ValueError('authored analytic geometry hash differs')
            m['run_counters']=[{k:r[k]for k in ('seed','primary_hits','shadow_tests','shadow_blocked','backface_absorbed')}for r in fresh['runs']]
            res.runs.append(m);return data
        V.P.render=replay;V.P.check_stat=V.analytic_gate;V.P.STAT_SPP=8192
        physical=V.P.control_a7(WORK/'analytic-replay').to_json()
        iid_proof=json.loads(D.checked(D.RESULTS/'009-iid-precision-confirmation.json'));iid_row=next(r for r in iid_proof['iid_crosscheck'] if r['name']=='A7')
        prefix=D.ROOT/Path(iid_row['command'][iid_row['command'].index('--out')+1])
        for p,h in iid_row['payload_sha256'].items():D.checked(prefix.parent/p,h)
        iid=[V.L.read_sidecar(Path(str(prefix)+f'.s{i}.f64'))for i in range(4)]
        if any(r['seed']!=s or r['spp']!=16384 for r,s in zip(iid,D.SEEDS)):raise ValueError('iid identity differs')
        g=data['mean'][...,2,:];ref=np.stack([r['mean']for r in iid]).mean(0)[...,2,:]
        relative=np.abs(g.mean((0,1))-ref.mean((0,1)))/np.abs(ref.mean((0,1)));nr=float(np.sqrt(np.mean((g-ref)**2)/np.mean(ref**2)))
        cross=dict(per_channel_mean_relative_difference=relative.tolist(),nrmse=nr,pass_=bool((relative<=.002).all() and nr<=.01))
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(complete=True,all_pass=bool(physical['pass'] and cross['pass_']),classification='POSTHOC_SAME_A7_FULL_ANALYTIC_IID_COMPLETE_NO_ADMISSION',physical_checks=physical,independent_iid=cross,original_deterministic_primary_bits_exact=True,
            scope='Same230 full8192 acquisition; original A7 only, total10of17 full scenes, no entire-suite/state/prefix/corpus readiness')
    except (ValueError,OSError,KeyError,AssertionError) as e:result.update(classification='POSTHOC_ANALYSIS_FAILURE_RETAINED',failure=str(e))
    OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result.get(k) for k in ('complete','all_pass','classification','failure','independent_iid')},indent=2));raise SystemExit(0 if result['all_pass'] else 2)

if __name__=='__main__':main()

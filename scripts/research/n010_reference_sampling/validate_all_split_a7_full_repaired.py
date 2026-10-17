#!/usr/bin/env python3
"""Plan083: original same-count pilot baseline, unchanged full A7 physical gates."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import numpy as np
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK=D.OUT/'all-split-original-a7-v2'
PILOT=D.RESULTS/'229-all-split-original-a7-cost-pilot.json'
FINAL=D.RESULTS/'230-all-split-original-a7-full-control.json'
PLAN=D.RESULTS.parent/'experiments/083-a7-pilot-same-count-baseline-amendment.md'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if WORK.exists() or PILOT.exists() or FINAL.exists():raise ValueError('refuse existing A7 acquisition')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    D.checked(Path(__file__));D.checked(PLAN);D.checked(Path(D.__file__))
    D.checked(D.HERE/'validate_all_split_a7_full.py')
    D.checked(D.RESULTS.parent/'experiments/082-original-a7-cost-pilot-and-full-physical-control.md')
    failed=json.loads(D.checked(D.RESULTS/'227-all-split-original-a7-cost-pilot.json'))
    if failed['complete'] or failed['failure']!='deterministic field bits differ':raise ValueError('actual227 guard failure required')
    for p,h in failed['payload_sha256'].items():D.checked(Path(p),h)
    sys.path.insert(0,str(D.HERE.parent/'n010_comparison_readiness'))
    import validate_sampler as V
    for p in (Path(V.__file__),Path(V.P.__file__),Path(V.L.__file__)):D.checked(p)
    controls=json.loads(D.checked(D.RESULTS/'226-all-split-full-deterministic-controls.json'))
    build=json.loads(D.checked(D.RESULTS/'224-all-split-exporter-build.json'))
    if not controls['complete'] or not controls['all_pass'] or not build['complete'] or not build['all_pass']:raise ValueError('preceding actual controls/build required')
    for p,h in build['payload_sha256'].items():D.checked(Path(p),h)
    binary=D.OUT/'all-split-exporter-v1/n010_all_split_oracle';original=D.OUT/'sampler-validation-v1/rqmc';scene=original/'A7.n008';net=D.OUT/'sobol16x262144.bin';D.checked(net)
    cached=json.loads(D.checked(D.RESULTS/'022-cached-oracle-equivalence.json'));prior=next(r for r in cached['rows'] if r['name']=='A7')
    meta=json.loads(D.checked(original/'A7.meta.json',prior['original_metadata_sha256']));D.checked(scene,prior['scene_sha256'])
    for p in prior['payloads']:D.checked(original/('A7'+p['payload']),p['old_sha256'])
    iid_proof=json.loads(D.checked(D.RESULTS/'009-iid-precision-confirmation.json'));iid_row=next(r for r in iid_proof['iid_crosscheck'] if r['name']=='A7')
    iid_prefix=D.ROOT/Path(iid_row['command'][iid_row['command'].index('--out')+1])
    for p,h in iid_row['payload_sha256'].items():D.checked(iid_prefix.parent/p,h)
    if meta['spp']!=8192 or meta['seeds']!=list(D.SEEDS) or iid_row['iid_spp']!=16384:raise ValueError('original counts differ')
    WORK.mkdir()
    def run(spp,label,result,outfile):
        folder=WORK/label;folder.mkdir();prefix=folder/'A7';receipt=folder/'native.resources.json'
        command=[str(binary),'--net',str(net),'--scene',str(scene),'--out',str(prefix),'--seeds',','.join(map(str,D.SEEDS)),'--spp',str(spp),'--threads','1']
        result['command']=command;outfile.write_text(json.dumps(result,indent=2)+'\n')
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU,(220,)*2)
            receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
        before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic()
        try:proc=subprocess.run(command,capture_output=True,text=True,timeout=300,preexec_fn=limits)
        except subprocess.TimeoutExpired as e:
            (folder/'native.stdout').write_bytes(e.stdout or b'');(folder/'native.stderr').write_bytes(e.stderr or b'');raise ValueError('elapsed guard; no retry') from e
        result['elapsed']=time.monotonic()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN)
        result['child_cpu_seconds']=(after.ru_utime+after.ru_stime)-(before.ru_utime+before.ru_stime);result['returncode']=proc.returncode
        (folder/'native.stdout').write_text(proc.stdout);(folder/'native.stderr').write_text(proc.stderr)
        rec=json.loads(D.checked(receipt))
        if rec['cpu']!=[220,220] or rec['address_space']!=[4*1024**3]*2 or len(rec['affinity'])!=1 or rec['nice']!=15:raise ValueError('actual resource limits differ')
        if proc.returncode:raise ValueError('native failure; no retry')
        fresh=json.loads(proc.stdout);(folder/'A7.meta.json').write_text(json.dumps(fresh,indent=2)+'\n')
        if any(fresh[k]!=meta[k] for k in ('scene_sha256','geometry_sha256','width','height','seeds')) or fresh['spp']!=spp:raise ValueError('actual scene/seed/count identity differs')
        runs=[V.L.read_sidecar(Path(str(prefix)+f'.s{i}.f64')) for i in range(4)]
        reference=[V.L.read_sidecar((WORK/'pilot-original'/f'A7.s{i}.f64') if label=='pilot' else original/f'A7.s{i}.f64') for i in range(4)]
        if any(np.asarray(r[k])[...,:2,:].tobytes()!=np.asarray(o[k])[...,:2,:].tobytes() for r,o in zip(runs,reference) for k in ('mean','m2')):raise ValueError('deterministic field bits differ')
        if prefix.with_suffix('.hits').read_bytes()!=(original/'A7.hits').read_bytes():raise ValueError('primary hit bytes differ')
        if any(not(np.isfinite(r[k]).all() and (r[k]>=0).all()) for r in runs for k in ('mean','m2')):raise ValueError('nonfinite/negative full outputs')
        if any(a['all_split']['own_checks']!=a['all_split']['component_attempts']-a['all_split']['component_nulls'] or a['all_split']['max_own_log_error']>1e-6 or a['all_split']['max_conditioned_error_fraction']>1 for a in fresh['runs']):raise ValueError('actual proposal audit failed')
        return runs,fresh
    def seal(result,outfile):
        result['payload_sha256']={str(p):sha(p) for p in WORK.rglob('*') if p.is_file()};outfile.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    def original_baseline(result):
        folder=WORK/'pilot-original';folder.mkdir();original_binary=D.ROOT/'build/n010-cpu/n010_cached_oracle'
        D.checked(original_binary,cached['cached_binary_sha256'])
        command=[str(original_binary),'--net',str(net),'--scene',str(scene),'--out',str(folder/'A7'),'--seeds',','.join(map(str,D.SEEDS)),'--spp','64','--threads','1']
        receipt=folder/'native.resources.json'
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU,(220,)*2)
            receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
        start=time.monotonic();proc=subprocess.run(command,capture_output=True,text=True,timeout=300,preexec_fn=limits)
        (folder/'native.stdout').write_text(proc.stdout);(folder/'native.stderr').write_text(proc.stderr)
        result['original_same_count_baseline']=dict(command=command,returncode=proc.returncode,elapsed=time.monotonic()-start)
        rec=json.loads(D.checked(receipt))
        if rec['cpu']!=[220,220] or rec['address_space']!=[4*1024**3]*2 or len(rec['affinity'])!=1 or rec['nice']!=15:raise ValueError('actual original baseline limits differ')
        if proc.returncode:raise ValueError('original same-count baseline failed; no retry')
        actual=json.loads(proc.stdout)
        if actual['spp']!=64 or any(actual[k]!=meta[k] for k in ('scene_sha256','geometry_sha256','width','height','seeds')):raise ValueError('original baseline identity differs')
    pilot=dict(schema='n010-all-split-original-a7-cost/1',complete=False,cost_pass=False,gpu_run=False,reference_admission=False,classification='COST_PILOT_ACQUIRING_NO_PHYSICAL_DECISION',input_sha256=dict(D.INPUTS),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),spp=64,tests='NOT_RUN; cost-only scientific pilot')
    try:
        PILOT.write_text(json.dumps(pilot,indent=2)+'\n')
        original_baseline(pilot)
        run(64,'pilot',pilot,PILOT)
        pilot.update(complete=True,estimated_full_cpu=128*pilot['child_cpu_seconds'],estimated_full_elapsed=128*pilot['elapsed'])
        pilot.update(cost_pass=pilot['estimated_full_cpu']<=160 and pilot['estimated_full_elapsed']<=220,classification='COST_ONLY_PILOT_COMPLETE_NOT_PHYSICAL_ADMISSION')
    except (ValueError,OSError,subprocess.SubprocessError) as e:pilot.update(classification='COST_PILOT_FAILURE_PARTIALS_RETAINED',failure=str(e))
    pilot['input_sha256']=dict(D.INPUTS);seal(pilot,PILOT)
    print(json.dumps({k:pilot.get(k) for k in ('complete','cost_pass','estimated_full_cpu','estimated_full_elapsed','failure')},indent=2),flush=True)
    if not pilot['cost_pass']:raise SystemExit(2)
    D.checked(PILOT)
    final=dict(schema='n010-all-split-original-a7-full-control/1',complete=False,all_pass=False,gpu_run=False,reference_admission=False,classification='ORIGINAL_FULL_A7_ACQUIRING',input_sha256=dict(D.INPUTS),source_commit=pilot['source_commit'],spp=8192,tests='NOT_RUN; original full scientific analytic/iid control')
    try:
        runs,fresh=run(8192,'full',final,FINAL)
        means=np.stack([r['mean'] for r in runs]);data=dict(mean=means.mean(0),se=means.std(0,ddof=1)/2,per_seed=runs,meta=fresh)
        def replay(res,sc,out,name,spp):
            if name!='A7' or spp!=8192 or sc.text()!=scene.read_text():raise ValueError('original analytic scene/count changed')
            m=dict(fresh);m['run_counters']=[{k:r[k] for k in ('seed','primary_hits','shadow_tests','shadow_blocked','backface_absorbed')}for r in fresh['runs']];res.runs.append(m);return data
        V.P.render=replay;V.P.check_stat=V.analytic_gate;V.P.STAT_SPP=8192
        physical=V.P.control_a7(WORK/'analytic').to_json()
        iid=[V.L.read_sidecar(Path(str(iid_prefix)+f'.s{i}.f64')) for i in range(4)]
        if any(r['seed']!=s or r['spp']!=16384 for r,s in zip(iid,D.SEEDS)):raise ValueError('independent iid identity differs')
        g=data['mean'][...,2,:];r=np.stack([v['mean'] for v in iid]).mean(0)[...,2,:]
        rel=np.abs(g.mean((0,1))-r.mean((0,1)))/np.abs(r.mean((0,1)));nr=float(np.sqrt(np.mean((g-r)**2)/np.mean(r**2)))
        cross=dict(per_channel_mean_relative_difference=rel.tolist(),nrmse=nr,pass_=bool((rel<=.002).all() and nr<=.01))
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        final.update(complete=True,all_pass=bool(physical['pass'] and cross['pass_']),classification='ORIGINAL_FULL_A7_ANALYTIC_IID_COMPLETE_NO_ADMISSION',physical_checks=physical,independent_iid=cross,deterministic_component_bits_and_primary_records_exact=True,
            scope='Original full A7 RGB B2 control only; with225/22610of17 full scenes, remaining controls/state/prefix/feasibility not attested')
    except (ValueError,OSError,subprocess.SubprocessError,AssertionError) as e:final.update(classification='FULL_CONTROL_FAILURE_PARTIALS_RETAINED',failure=str(e))
    final['input_sha256']=dict(D.INPUTS);seal(final,FINAL)
    print(json.dumps({k:final.get(k) for k in ('complete','all_pass','classification','failure','independent_iid')},indent=2))
    raise SystemExit(0 if final['all_pass'] else 2)

if __name__=='__main__':main()

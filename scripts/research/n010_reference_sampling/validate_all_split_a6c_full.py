#!/usr/bin/env python3
"""Plan086: one bounded original A6c full acquisition; never a retry/queue."""
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

WORK=D.OUT/'all-split-original-a6c-full-v1'
OUTPUT=D.RESULTS/'234-all-split-original-a6c-full-physical-control.json'
PLAN=D.RESULTS.parent/'experiments/086-original-a6c-full-physical-control.md'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing original full A6c')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    for p in (Path(__file__),PLAN,Path(D.__file__),D.HERE/'run_primary_direction_sequence.py'):D.checked(p)
    pilot=json.loads(D.checked(D.RESULTS/'232-all-split-original-a6c-cpu-cost.json'));replay=json.loads(D.checked(D.RESULTS/'233-posthoc-all-split-general-controls-replay.json'))
    build=json.loads(D.checked(D.RESULTS/'224-all-split-exporter-build.json'))
    if not pilot['complete'] or not replay['complete'] or not build['complete'] or not build['all_pass']:raise ValueError('actual A6c sizing/control/build required')
    for p,h in build['payload_sha256'].items():D.checked(Path(p),h)
    original=D.OUT/'sampler-validation-v1/rqmc';proof=json.loads(D.checked(D.RESULTS/'022-cached-oracle-equivalence.json'));prior=next(r for r in proof['rows']if r['name']=='A6c')
    meta=json.loads(D.checked(original/'A6c.meta.json',prior['original_metadata_sha256']));scene=original/'A6c.n008';D.checked(scene,prior['scene_sha256'])
    for p in prior['payloads']:D.checked(original/('A6c'+p['payload']),p['old_sha256'])
    if meta['spp']!=8192 or meta['seeds']!=list(D.SEEDS):raise ValueError('original control schedule differs')
    net=D.OUT/'sobol16x262144.bin';D.checked(net);binary=D.OUT/'all-split-exporter-v1/n010_all_split_oracle'
    sys.path.insert(0,str(D.HERE.parent/'n010_comparison_readiness'));import validate_sampler as V
    for p in (Path(V.__file__),Path(V.P.__file__),Path(V.L.__file__)):D.checked(p)
    WORK.mkdir();prefix=WORK/'A6c';receipt=WORK/'native.resources.json'
    command=[str(binary),'--net',str(net),'--scene',str(scene),'--out',str(prefix),'--seeds',','.join(map(str,D.SEEDS)),'--spp','8192','--threads','1']
    result=dict(schema='n010-all-split-original-a6c-full-physical-control/1',complete=False,all_pass=False,gpu_run=False,reference_admission=False,
        classification='ORIGINAL_FULL_A6C_NATIVE_ACQUIRING',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),input_sha256=D.INPUTS,
        command=command,native_limits=dict(cpu_seconds=3600,elapsed_seconds=5400,address_space_bytes=4*1024**3,affinity=sorted(os.sched_getaffinity(0)),nice=15),
        scheduling='One native only; no automatic subsequent-control queue',tests='NOT_RUN; original full scientific physical control')
    def save():OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(3600,)*2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
    try:
        before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic()
        try:proc=subprocess.run(command,capture_output=True,text=True,timeout=5400,preexec_fn=limits)
        except subprocess.TimeoutExpired as e:
            (WORK/'native.stdout').write_bytes(e.stdout or b'');(WORK/'native.stderr').write_bytes(e.stderr or b'');raise ValueError('full native elapsed guard; no retry') from e
        elapsed=time.monotonic()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN)
        (WORK/'native.stdout').write_text(proc.stdout);(WORK/'native.stderr').write_text(proc.stderr)
        result.update(returncode=proc.returncode,elapsed=elapsed,child_cpu_seconds=(after.ru_utime+after.ru_stime)-(before.ru_utime+before.ru_stime),classification='ORIGINAL_FULL_A6C_NATIVE_TERMINAL_ANALYSIS_PENDING')
        result['payload_sha256']={str(p):sha(p)for p in WORK.iterdir()if p.is_file()};save()
        actual=json.loads(D.checked(receipt))
        if actual['cpu']!=[3600,3600] or actual['address_space']!=[4*1024**3]*2 or len(actual['affinity'])!=1 or actual['nice']!=15:raise ValueError('actual native resource scope differs')
        if proc.returncode:raise ValueError('full native failure; no retry')
        resource.setrlimit(resource.RLIMIT_CPU,(220,)*2)
        fresh=json.loads(proc.stdout);(WORK/'A6c.meta.json').write_text(json.dumps(fresh,indent=2)+'\n')
        if any(fresh[k]!=meta[k]for k in ('scene_sha256','geometry_sha256','width','height','spp','seeds')):raise ValueError('actual scene/count/seed differs')
        rows=[V.L.read_sidecar(Path(str(prefix)+f'.s{i}.f64'))for i in range(4)]
        old=[V.L.read_sidecar(original/f'A6c.s{i}.f64')for i in range(4)]
        if any(a[k][...,:2,:].tobytes()!=b[k][...,:2,:].tobytes()for a,b in zip(rows,old)for k in ('mean','m2')):raise ValueError('original deterministic mean/second bits differ')
        if prefix.with_suffix('.hits').read_bytes()!=(original/'A6c.hits').read_bytes():raise ValueError('original primary hits differ')
        if any(not(np.isfinite(r[k]).all() and (r[k]>=0).all())for r in rows for k in ('mean','m2')):raise ValueError('nonfinite/negative full outputs')
        if any(r['seed']!=s or r['spp']!=8192 for r,s in zip(rows,D.SEEDS)):raise ValueError('sidecar identity differs')
        for r in fresh['runs']:
            a=r['all_split']
            if r['primary_hits']!=128*96*8192 or a['own_checks']!=a['component_attempts']-a['component_nulls'] or a['max_own_log_error']>1e-6 or a['max_conditioned_error_fraction']>1:raise ValueError('full primary/proposal audit failed')
        authored,v,f=V.P.sphere_scene((.9,.6,.3),(.3,.2,-.1),(2,2,2),2)
        if authored.text()!=scene.read_text() or authored.geometry_sha256()!=fresh['geometry_sha256']:raise ValueError('independent original authored control differs')
        direct,allowance,indirect,bounds=V.P.sphere_expected(authored,(.9,.6,.3),(.3,.2,-.1),(2,2,2),2,(v,f))
        means=np.stack([r['mean']for r in rows]);data=dict(mean=means.mean(0),se=means.std(0,ddof=1)/2,per_seed=rows,meta=fresh)
        control=V.P.Result('A6c','Original full finite-depth colored sphere control')
        m=dict(fresh);m.update(name='A6c',geometry_hash_match=True);control.runs.append(m);control.notes['A6c_mesh']=bounds;control.notes['A6c_expected_indirect']=indirect
        mask=np.ones(direct.shape[:2],bool)
        V.analytic_gate(control,'A6c',data,'direct',direct,mask,tau=0,allowance=allowance)
        V.analytic_gate(control,'A6c',data,'indirect',indirect,mask,tau=.002)
        physical=control.to_json()
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(complete=True,all_pass=physical['pass'],classification='ORIGINAL_FULL_A6C_PHYSICAL_COMPLETE_NO_ADMISSION',physical_checks=physical,
            deterministic_component_bits_primary_exact=True,native_metadata=fresh,
            scope='Original full A6c only; total11of17 ifPASS, other physical/independence/state/prefix/full-frame qualification remain')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as e:result.update(classification='ORIGINAL_FULL_A6C_FAILURE_PARTIALS_RETAINED',failure=str(e))
    result['payload_sha256']={str(p):sha(p)for p in WORK.iterdir()if p.is_file()};save()
    print(json.dumps({k:result.get(k)for k in ('complete','all_pass','classification','failure','elapsed','child_cpu_seconds')},indent=2));raise SystemExit(0 if result['all_pass']else 2)

if __name__=='__main__':main()

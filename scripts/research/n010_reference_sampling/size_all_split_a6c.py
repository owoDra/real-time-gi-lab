#!/usr/bin/env python3
"""Plan085: original A6c scene, low-count whole-frame CPU cost, no admission."""
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

WORK=D.OUT/'all-split-original-a6c-cost-v1'
OUTPUT=D.RESULTS/'232-all-split-original-a6c-cpu-cost.json'
PLAN=D.RESULTS.parent/'experiments/085-original-a6c-cpu-cost-pilot.md'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing cost pilot')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    for p in (Path(__file__),PLAN,Path(D.__file__)):D.checked(p)
    full=json.loads(D.checked(D.RESULTS/'231-posthoc-original-a7-retained-control.json'))
    build=json.loads(D.checked(D.RESULTS/'224-all-split-exporter-build.json'))
    if not full['complete'] or not full['all_pass'] or not build['complete'] or not build['all_pass']:raise ValueError('actual original full A7/exporter proof required')
    for p,h in build['payload_sha256'].items():D.checked(Path(p),h)
    original=D.OUT/'sampler-validation-v1/rqmc';proof=json.loads(D.checked(D.RESULTS/'022-cached-oracle-equivalence.json'));prior=next(v for v in proof['rows'] if v['name']=='A6c')
    meta=json.loads(D.checked(original/'A6c.meta.json',prior['original_metadata_sha256']));scene=original/'A6c.n008';D.checked(scene,prior['scene_sha256'])
    for p in prior['payloads']:D.checked(original/('A6c'+p['payload']),p['old_sha256'])
    net=D.OUT/'sobol16x262144.bin';D.checked(net);binary=D.OUT/'all-split-exporter-v1/n010_all_split_oracle'
    if meta['spp']!=8192 or meta['seeds']!=list(D.SEEDS):raise ValueError('original scope differs')
    WORK.mkdir();receipt=WORK/'native.resources.json';prefix=WORK/'A6c'
    command=[str(binary),'--net',str(net),'--scene',str(scene),'--out',str(prefix),'--seeds',','.join(map(str,D.SEEDS)),'--spp','8','--threads','1']
    result=dict(schema='n010-all-split-original-a6c-cpu-cost/1',complete=False,gpu_run=False,reference_admission=False,physical_control_decision='NOT_APPLICABLE_COST_ONLY',classification='CPU_COST_PILOT_ACQUIRING',input_sha256=D.INPUTS,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),command=command,tests='NOT_RUN; whole-frame cost-only scientific pilot')
    def save():OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(60,)*2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
    try:
        before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic()
        try:proc=subprocess.run(command,capture_output=True,text=True,timeout=90,preexec_fn=limits)
        except subprocess.TimeoutExpired as e:
            (WORK/'native.stdout').write_bytes(e.stdout or b'');(WORK/'native.stderr').write_bytes(e.stderr or b'');raise ValueError('elapsed guard; no retry') from e
        elapsed=time.monotonic()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN);cpu=(after.ru_utime+after.ru_stime)-(before.ru_utime+before.ru_stime)
        (WORK/'native.stdout').write_text(proc.stdout);(WORK/'native.stderr').write_text(proc.stderr)
        result.update(returncode=proc.returncode,elapsed=elapsed,child_cpu_seconds=cpu);save()
        actual=json.loads(D.checked(receipt))
        if actual['cpu']!=[60,60] or actual['address_space']!=[4*1024**3]*2 or len(actual['affinity'])!=1 or actual['nice']!=15:raise ValueError('actual limits differ')
        if proc.returncode:raise ValueError('native failure; no retry')
        fresh=json.loads(proc.stdout)
        if any(fresh[k]!=meta[k] for k in ('scene_sha256','geometry_sha256','width','height','seeds')) or fresh['spp']!=8:raise ValueError('cost scope differs')
        sys.path.insert(0,str(D.HERE.parent/'n008_hdr_oracle'));import n008lib as L
        D.checked(Path(L.__file__))
        rows=[L.read_sidecar(Path(str(prefix)+f'.s{i}.f64'))for i in range(4)]
        if any(not(np.isfinite(r[k]).all() and (r[k]>=0).all())for r in rows for k in ('mean','m2')):raise ValueError('nonfinite/negative pilot')
        if any(r[k][...,:2,:].tobytes()!=rows[0][k][...,:2,:].tobytes()for r in rows for k in ('mean','m2')):raise ValueError('same-count deterministic seed fields differ')
        if prefix.with_suffix('.hits').read_bytes()!=(original/'A6c.hits').read_bytes():raise ValueError('original primary hit bits differ')
        for run in fresh['runs']:
            a=run['all_split']
            if run['primary_hits']!=128*96*8 or a['own_checks']!=a['component_attempts']-a['component_nulls'] or a['max_own_log_error']>1e-6 or a['max_conditioned_error_fraction']>1:raise ValueError('pilot primary/proposal audit failed')
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(complete=True,classification='CPU_COST_PILOT_COMPLETE_NO_PHYSICAL_OR_REFERENCE_ADMISSION',estimated_original8192_cpu=1024*cpu,estimated_original8192_elapsed=1024*elapsed,
            estimates='Conservative scaling of this8sample setup+output+work; planning only, no whole-run ETA or scientific acceptance',native_metadata=fresh,full_acquisition='NOT_RUN_NOT_QUEUED')
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as e:result.update(classification='COST_PILOT_FAILURE_PARTIALS_RETAINED',failure=str(e))
    result['payload_sha256']={str(p):sha(p) for p in WORK.iterdir() if p.is_file()};save()
    print(json.dumps({k:result.get(k) for k in ('complete','classification','failure','child_cpu_seconds','elapsed','estimated_original8192_cpu','estimated_original8192_elapsed')},indent=2))
    raise SystemExit(0 if result['complete'] else 2)

if __name__=='__main__':main()

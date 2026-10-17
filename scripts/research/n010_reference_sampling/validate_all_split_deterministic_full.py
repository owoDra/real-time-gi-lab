#!/usr/bin/env python3
"""Plan081: remaining original full deterministic controls, no accuracy changes."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK=D.OUT/'all-split-full-deterministic-v1'
OUTPUT=D.RESULTS/'226-all-split-full-deterministic-controls.json'
PLAN=D.RESULTS.parent/'experiments/081-all-split-original-deterministic-full-controls.md'
NAMES=('A2','A2b','A4a','A4b','A8_authored','A8_frozen','A8_stale_rest_pose')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing original controls')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    D.checked(Path(__file__));D.checked(PLAN);D.checked(Path(D.__file__))
    D.checked(D.HERE/'validate_all_split_sidedness_full.py')
    prior=json.loads(D.checked(D.RESULTS/'225-all-split-full-sidedness-controls.json'))
    if not prior['complete'] or not prior['all_pass']:raise ValueError('prior225 full controls required')
    build=json.loads(D.checked(D.RESULTS/'224-all-split-exporter-build.json'))
    if not build['complete'] or not build['all_pass']:raise ValueError('actual exporter build required')
    for p,h in build['payload_sha256'].items():D.checked(Path(p),h)
    binary=D.OUT/'all-split-exporter-v1/n010_all_split_oracle';D.checked(binary)
    proof=json.loads(D.checked(D.RESULTS/'022-cached-oracle-equivalence.json'))
    if not proof['complete'] or not proof['all_pass']:raise ValueError('original immutable controls required')
    original=D.OUT/'sampler-validation-v1/rqmc';net=D.OUT/'sobol16x262144.bin';D.checked(net)
    controls={}
    for name in NAMES:
        row=next(r for r in proof['rows'] if r['name']==name)
        meta=json.loads(D.checked(original/(name+'.meta.json'),row['original_metadata_sha256']))
        D.checked(original/(name+'.n008'),row['scene_sha256'])
        for p in row['payloads']:D.checked(original/(name+p['payload']),p['old_sha256'])
        if meta['seeds']!=list(D.SEEDS) or meta['spp']!=64:raise ValueError('original controls differ')
        controls[name]=(row,meta)
    WORK.mkdir()
    result=dict(schema='n010-all-split-full-deterministic-controls/1',complete=False,all_pass=False,gpu_run=False,reference_admission=False,
        classification='ORIGINAL_FULL_DETERMINISTIC_CONTROLS_ACQUIRING',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),input_sha256=D.INPUTS,
        scope='Seven original full deterministic scenes; plus225 nine of17, not stochastic indirect/range/full-suite proof',names=list(NAMES),rows=[],tests='NOT_RUN; original scientific full-frame controls only')
    def save():OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()
    try:
        for name in NAMES:
            old,meta=controls[name];prefix=WORK/name;receipt=WORK/(name+'.resources.json')
            command=[str(binary),'--net',str(net),'--scene',str(original/(name+'.n008')),'--out',str(prefix),'--seeds',','.join(map(str,D.SEEDS)),'--spp',str(meta['spp']),'--threads','1']
            row=dict(name=name,command=command,pass_=False);result['rows'].append(row);save()
            def limits():
                resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(220,)*2)
                receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
            start=time.monotonic()
            try:proc=subprocess.run(command,capture_output=True,text=True,timeout=300,preexec_fn=limits)
            except subprocess.TimeoutExpired as e:
                (WORK/(name+'.stdout')).write_bytes(e.stdout or b'');(WORK/(name+'.stderr')).write_bytes(e.stderr or b'');raise ValueError('elapsed guard, no retry') from e
            (WORK/(name+'.stdout')).write_text(proc.stdout);(WORK/(name+'.stderr')).write_text(proc.stderr)
            row.update(returncode=proc.returncode,elapsed=time.monotonic()-start);save()
            rec=json.loads(D.checked(receipt))
            if rec['cpu']!=[220,220] or rec['address_space']!=[4*1024**3]*2 or len(rec['affinity'])!=1 or rec['nice']!=15:raise ValueError('actual limits differ')
            if proc.returncode:raise ValueError('native failure; no retry')
            fresh=json.loads(proc.stdout);(WORK/(name+'.meta.json')).write_text(json.dumps(fresh,indent=2)+'\n')
            if any(fresh[k]!=meta[k] for k in ('scene_sha256','geometry_sha256','width','height','spp','seeds')):raise ValueError('actual scene/seed/count identity differs')
            payloads=[]
            for p in old['payloads']:
                actual=prefix.parent/(name+p['payload']);h=sha(actual)
                payloads.append(dict(payload=p['payload'],sha256=h,original_sha256=p['old_sha256'],byte_identical=h==p['old_sha256']))
            fields=('seed','primary_hits','backface_absorbed')
            counter_exact=all(all(new[k]==prior[k] for k in fields) for new,prior in zip(fresh['runs'],meta['runs']))
            if len(fresh['runs'])!=4:raise ValueError('full four seeds missing')
            audits=[r['all_split'] for r in fresh['runs']]
            if not all(a['auxiliary_primary_primes']==128*96 and a['own_checks']==a['component_attempts']-a['component_nulls'] and a['max_own_log_error']<=1e-6 and a['max_conditioned_error_fraction']<=1 for a in audits):raise ValueError('proposal audit failed in original controls')
            row.update(pass_=all(p['byte_identical'] for p in payloads) and counter_exact,payloads=payloads,original_primary_hit_absorption_counters_exact=counter_exact,
                audit_receipts=audits,full_frame=[fresh['width'],fresh['height']],seeds=fresh['seeds'],spp=fresh['spp'])
            save()
            if not row['pass_']:raise ValueError('original full output/counter mismatch')
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(complete=True,all_pass=True,classification='SEVEN_ORIGINAL_FULL_CONTROLS_BYTE_EXACT_PASS_NO_ADMISSION')
    except (ValueError,OSError,subprocess.SubprocessError) as e:result.update(classification='CONTROL_FAILURE_PARTIALS_RETAINED',failure=str(e))
    result['payload_sha256']={str(p):sha(p) for p in WORK.iterdir() if p.is_file()};save()
    print(json.dumps({k:result.get(k) for k in ('complete','all_pass','classification','failure')},indent=2))
    raise SystemExit(0 if result['all_pass'] else 2)

if __name__=='__main__':main()

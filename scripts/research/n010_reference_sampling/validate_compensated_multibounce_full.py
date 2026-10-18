#!/usr/bin/env python3
"""Plan144: one original full analytic/IID physical control for compensated geometry."""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import numpy as np
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

PLAN=D.RESULTS.parent/'experiments/144-compensated-full-a7-a6c-controls.md'


def start_ticks(pid):
    try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
    except FileNotFoundError:return None


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--name',choices=('A7','A6c'),required=True)
    name=ap.parse_args().name
    number,cpu_limit,elapsed_limit=(486,220,300) if name=='A7' else (487,3600,5400)
    work=D.OUT/f'compensated-{name.lower()}-full-v1'
    output=D.RESULTS/f'{number}-compensated-{name.lower()}-full-control.json'
    if work.exists() or output.exists():raise ValueError('refuse existing full control; no retry')
    require_no_other_research_worker()
    os.sched_setaffinity(0,{31});os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))])!=D.checked(path):
            raise ValueError('commit exact source/recipe before acquisition')
    for path in (Path(D.__file__),D.HERE/'run_primary_direction_sequence.py'):
        D.checked(path)
    for filename in ('483-compensated-sealed-dark-full-control.json','484-compensated-sealed-lit-full-control.json'):
        prerequisite=json.loads(D.checked(D.RESULTS/filename))
        if not (prerequisite['complete'] and prerequisite['all_pass']):
            raise ValueError('candidate full sealed physical PASS required')
        for group in ('input_sha256','payload_sha256'):
            for path,digest in prerequisite[group].items():D.checked(Path(path),digest)
    if name=='A6c':
        previous=json.loads(D.checked(D.RESULTS/'486-compensated-a7-full-control.json'))
        if not (previous['complete'] and previous['all_pass']):raise ValueError('candidate full A7 PASS required')
        for group in ('input_sha256','payload_sha256'):
            for path,digest in previous[group].items():D.checked(Path(path),digest)
    build=json.loads(D.checked(D.RESULTS/'452-compensated-full-exporter-build.json'))
    if not (build['complete'] and build['build_valid']):raise ValueError('exact candidate build452 required')
    for path,digest in build['payload_sha256'].items():D.checked(Path(path),digest)
    binary=D.OUT/'compensated-full-deterministic-v1/build/n010_compensated_exporter'
    D.checked(binary)
    proof=json.loads(D.checked(D.RESULTS/'022-cached-oracle-equivalence.json'))
    prior=next(r for r in proof['rows'] if r['name']==name)
    original=D.OUT/'sampler-validation-v1/rqmc'
    scene=original/(name+'.n008');D.checked(scene,prior['scene_sha256'])
    meta=json.loads(D.checked(original/(name+'.meta.json'),prior['original_metadata_sha256']))
    for payload in prior['payloads']:D.checked(original/(name+payload['payload']),payload['old_sha256'])
    if (meta['width'],meta['height'],meta['spp'],meta['seeds'])!=(128,96,8192,list(D.SEEDS)):
        raise ValueError('original full-control identity differs')
    net=D.OUT/'sobol16x262144.bin';D.checked(net)
    sys.path.insert(0,str(D.HERE.parent/'n010_comparison_readiness'))
    import validate_sampler as V
    for path in (Path(V.__file__),Path(V.P.__file__),Path(V.L.__file__)):D.checked(path)
    if name=='A7':
        authored=V.P.build_a7(2)
    else:
        authored,vertices,faces=V.P.sphere_scene((.9,.6,.3),(.3,.2,-.1),(2,2,2),2)
    if authored.text()!=scene.read_text() or authored.geometry_sha256()!=meta['geometry_sha256']:
        raise ValueError('independent original authored scene differs')
    work.mkdir()
    prefix=work/name;receipt=work/'native.resources.json'
    command=[str(binary),'--net',str(net),'--scene',str(scene),'--out',str(prefix),
        '--seeds',','.join(map(str,D.SEEDS)),'--spp','8192','--threads','1']
    result=dict(schema='n010-compensated-multibounce-full-control/1',name=name,complete=False,
        all_pass=False,gpu_run=False,reference_admission=False,accepted_timing=False,
        numerical_variant='compensated-raw-target-v1',source_commit=commit,input_sha256=D.INPUTS,
        command=command,classification='COMPENSATED_MULTIBOUNCE_FULL_NATIVE_ACQUIRING',
        native_limits=dict(cpu_seconds=cpu_limit,elapsed_seconds=elapsed_limit,address_space_bytes=4*1024**3,affinity=[31],nice=15),
        scheduling='One explicit original full control only; no retry or subsequent task queue',
        tests='NOT_RUN; full scientific analytic/IID control only')

    def save():
        output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

    def hashes():
        return {str(p):D.sha(p) for p in work.iterdir() if p.is_file()}

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(cpu_limit,)*2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(),pgid=os.getpgrp(),start_ticks=start_ticks(os.getpid()),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
            elapsed_limit_seconds=elapsed_limit,command=command))+'\n')

    save()
    try:
        require_no_other_research_worker()
        for path,digest in list(D.INPUTS.items()):D.checked(Path(path),digest)
        before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic()
        with (work/'native.stdout').open('wb') as out,(work/'native.stderr').open('wb') as err:
            child=subprocess.Popen(command,cwd=D.ROOT,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits)
            result['native_pid']=child.pid;save()
            try:code=child.wait(timeout=elapsed_limit)
            except subprocess.TimeoutExpired:
                actual=json.loads(receipt.read_text())
                if (actual['pid'],actual['pgid'],actual['start_ticks'])!=(child.pid,child.pid,start_ticks(child.pid)):
                    raise ValueError('owned native identity differs; refuse signalling')
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait(timeout=5);code='ELAPSED_GUARD_PARTIALS_RETAINED'
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        result.update(returncode=code,elapsed_seconds=time.monotonic()-start,
            child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            classification='COMPENSATED_MULTIBOUNCE_NATIVE_TERMINAL_ANALYSIS_PENDING',payload_sha256=hashes())
        save()
        actual=json.loads(D.checked(receipt))
        if (actual['pid']!=child.pid or actual['pgid']!=child.pid or type(actual['start_ticks']) is not int
                or actual['cpu']!=[cpu_limit]*2 or actual['address_space']!=[4*1024**3]*2
                or actual['affinity']!=[31] or actual['nice']!=15 or actual['command']!=command
                or code!=0 or result['elapsed_seconds']>=elapsed_limit or result['child_cpu_seconds']>cpu_limit):
            raise ValueError('native/resource failure; no retry')
        result['terminal_identity_verified']=True
        resource.setrlimit(resource.RLIMIT_CPU,(220,)*2)
        fresh=json.loads((work/'native.stdout').read_text())
        (work/(name+'.meta.json')).write_text(json.dumps(fresh,indent=2)+'\n')
        if any(fresh[k]!=meta[k] for k in ('scene_sha256','geometry_sha256','width','height','spp','seeds')):
            raise ValueError('actual original full scene/count/seeds differ')
        rows=[V.L.read_sidecar(Path(str(prefix)+f'.s{i}.f64')) for i in range(4)]
        old=[V.L.read_sidecar(original/f'{name}.s{i}.f64') for i in range(4)]
        for row,baseline,seed in zip(rows,old,D.SEEDS):
            if (row['width'],row['height'],row['spp'],row['seed'])!=(128,96,8192,seed):
                raise ValueError('sidecar full identity differs')
            for key in ('mean','m2'):
                if not (np.isfinite(row[key]).all() and (row[key]>=0).all()):
                    raise ValueError('sidecar finite/nonnegative guard failed')
                if row[key][...,:2,:].tobytes()!=baseline[key][...,:2,:].tobytes():
                    raise ValueError('original deterministic bits differ')
        if prefix.with_suffix('.hits').read_bytes()!=(original/(name+'.hits')).read_bytes():
            raise ValueError('original primary-hit bytes differ')
        if len(fresh['runs'])!=4:raise ValueError('four full original seeds missing')
        for run,baseline in zip(fresh['runs'],meta['runs']):
            audit=run['all_split']
            if (run['seed']!=baseline['seed'] or run['primary_hits']!=baseline['primary_hits']
                    or audit['own_checks']!=audit['component_attempts']-audit['component_nulls']
                    or not np.isfinite([audit['max_own_log_error'],audit['max_conditioned_error_fraction'],audit['max_unconditioned_error_fraction']]).all()
                    or audit['max_own_log_error']>1e-6 or audit['max_conditioned_error_fraction']>1):
                raise ValueError('original primary/proposal numerical guard failed')
        for i in range(4):
            for component in ('emission','direct','indirect','total'):
                image=V.L.read_pfm(Path(str(prefix)+f'.s{i}.{component}.pfm'))
                if not (np.isfinite(image).all() and (image>=0).all()):
                    raise ValueError('component image finite/nonnegative guard failed')
        means=np.stack([r['mean'] for r in rows])
        data=dict(mean=means.mean(0),se=means.std(0,ddof=1)/2,per_seed=rows,meta=fresh)

        def derived(sc):
            m=dict(fresh,name=name,geometry_hash_match=fresh['geometry_sha256']==sc.geometry_sha256(),
                run_counters=[{k:r[k] for k in ('seed','primary_hits','shadow_tests','shadow_blocked','backface_absorbed')} for r in fresh['runs']])
            if not m['geometry_hash_match']:raise ValueError('independent analytic geometry differs')
            return m

        if name=='A7':
            def replay(res,sc,out,tag,spp):
                if tag!='A7' or spp!=8192 or sc.text()!=scene.read_text():raise ValueError('original analytic input differs')
                res.runs.append(derived(sc))
                return data
            V.P.render=replay;V.P.check_stat=V.analytic_gate;V.P.STAT_SPP=8192
            physical=V.P.control_a7(work/'analytic-replay').to_json()
            iid_proof=json.loads(D.checked(D.RESULTS/'009-iid-precision-confirmation.json'))
            iid_row=next(r for r in iid_proof['iid_crosscheck'] if r['name']=='A7')
            iid_prefix=D.ROOT/Path(iid_row['command'][iid_row['command'].index('--out')+1])
            for path,digest in iid_row['payload_sha256'].items():D.checked(iid_prefix.parent/path,digest)
            iid=[V.L.read_sidecar(Path(str(iid_prefix)+f'.s{i}.f64')) for i in range(4)]
            if any((r['width'],r['height'],r['spp'],r['seed'])!=(128,96,16384,seed) for r,seed in zip(iid,D.SEEDS)):
                raise ValueError('original independent IID identity differs')
            got=data['mean'][...,2,:];ref=np.stack([r['mean'] for r in iid]).mean(0)[...,2,:]
            rel=np.abs(got.mean((0,1))-ref.mean((0,1)))/np.abs(ref.mean((0,1)))
            nr=float(np.sqrt(np.mean((got-ref)**2)/np.mean(ref**2)))
            cross=dict(per_channel_mean_relative_difference=rel.tolist(),nrmse=nr,pass_=bool((rel<=.002).all() and nr<=.01))
            result['independent_iid']=cross
            accepted=bool(physical['pass'] and cross['pass_'])
        else:
            direct,allowance,indirect,bounds=V.P.sphere_expected(authored,(.9,.6,.3),(.3,.2,-.1),(2,2,2),2,(vertices,faces))
            control=V.P.Result('A6c','Original full finite-depth colored sphere control')
            control.runs.append(derived(authored));control.notes['A6c_mesh']=bounds;control.notes['A6c_expected_indirect']=indirect
            mask=np.ones(direct.shape[:2],bool)
            V.analytic_gate(control,'A6c',data,'direct',direct,mask,tau=0,allowance=allowance)
            V.analytic_gate(control,'A6c',data,'indirect',indirect,mask,tau=.002)
            physical=control.to_json();accepted=bool(physical['pass'])
        for path,digest in list(D.INPUTS.items()):D.checked(Path(path),digest)
        result.update(complete=True,all_pass=accepted,physical_checks=physical,native_metadata=fresh,
            deterministic_component_bits_primary_exact=True,
            classification='COMPENSATED_ORIGINAL_FULL_ANALYTIC_CONTROL_COMPLETE_NO_REFERENCE_ADMISSION',
            scope='One original full candidate artifact only; no global bias/state/prefix/reference admission')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(classification='COMPENSATED_MULTIBOUNCE_FULL_FAILURE_PARTIALS_RETAINED',failure=str(error))
    result['payload_sha256']=hashes();save()
    print(json.dumps({k:result.get(k) for k in ('name','complete','all_pass','classification','failure','elapsed_seconds','child_cpu_seconds')},indent=2))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__=='__main__':
    main()

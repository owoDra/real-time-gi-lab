#!/usr/bin/env python3
"""Plan163: one full C1 execution-equivalence native; always one CPU core."""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

import numpy as np
import compensated_reference_chain as P
from compensated_reference_chain import D,Q,require_no_other_research_worker
import prepare_thread_private_reference as B

PLAN = D.RESULTS.parent/'experiments/163-thread-private-full-frame-equivalence-pilot.md'
BASE = D.OUT/'thread-private-equivalence-v1'
SUMMARY = D.RESULTS/'625-thread-private-full-frame-equivalence-summary.json'


def paths(step):return D.RESULTS/f'{623 if step == "baseline" else 624}-thread-private-{step}-equivalence.json',BASE/step
def write(path,value,fresh=False):
    with path.open('x' if fresh else 'w') as stream:stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def bind(path):
    result = json.loads(D.checked(path))
    if not result['complete']:raise ValueError('terminal prerequisite required')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in result.get(group,{}).items():D.checked(Path(name),digest)
    return result


def compare(left,right):
    for suffix in ('.hits','.s0.f64','.s0.emission.pfm','.s0.direct.pfm','.s0.indirect.pfm','.s0.total.pfm'):
        if Path(left['prefix']+suffix).read_bytes() != Path(right['prefix']+suffix).read_bytes():
            raise ValueError('full native binary payload differs: '+suffix)
    lm,rm = left['native_metadata'],right['native_metadata']
    if {k:v for k,v in lm.items() if k != 'runs'} != {k:v for k,v in rm.items() if k != 'runs'}:
        raise ValueError('full physical/native metadata differs')
    omit = ('prefix','cpu_seconds_diagnostic')
    if ({k:v for k,v in lm['runs'][0].items() if k not in omit} !=
            {k:v for k,v in rm['runs'][0].items() if k not in omit}):
        raise ValueError('complete actual scored/proposal audit metadata differs')


def start_ticks(pid):
    try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
    except FileNotFoundError:return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--step',choices=('baseline','candidate'));mode.add_argument('--summarize',action='store_true')
    args = parser.parse_args()
    require_no_other_research_worker()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):raise ValueError('one numerical thread required')
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),B.PLAN,Path(B.__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))]) != D.checked(path):
            raise ValueError('commit exact163/162 source/recipe first')
    # The existing source must not be edited or its live worker displaced.
    current = bind(D.RESULTS/'490-compensated-full-a6a-seed1.json')
    if not current['seed_integrity_pass'] or not current['terminal_identity_verified']:raise ValueError('actual145 seed1 terminal integrity required')
    build,prep = bind(B.BUILD),bind(B.PREP)
    original = bind(D.RESULTS/'452-compensated-full-exporter-build.json')
    if not build['build_valid'] or not prep['source_preparation_valid'] or not original['build_valid']:
        raise ValueError('actual452/621/622 builds/source required')
    if args.summarize:
        if SUMMARY.exists():raise ValueError('fresh equivalence summary required')
        resource.setrlimit(resource.RLIMIT_CPU,(120,120));signal.alarm(180)
        left,right = (bind(paths(step)[0]) for step in ('baseline','candidate'))
        if not all(row['all_pass'] and row['terminal_identity_verified'] for row in (left,right)):
            raise ValueError('two actual terminal passing equivalence records required')
        compare(left,right)
        result = dict(schema='n010-thread-private-equivalence-summary/1',complete=True,all_pass=True,
            source_commit=commit,input_sha256=D.INPUTS,records=[str(paths(step)[0]) for step in ('baseline','candidate')],
            classification='FULL_C1_16SPP_ONE_SEED_SINGLE_CORE_THREAD_EQUIVALENCE_ONLY',gpu_run=False,
            actual_affinity=[31],thread_counts=[1,4],all_six_payload_bytes_and_exported_audits_exact=True,
            accepted_timing=False,reference_admission=False,tests='NOT_RUN; retained scientific pair replay only')
        write(SUMMARY,result,True);signal.alarm(0);print(result['classification']);return 0
    output,work = paths(args.step)
    if output.exists() or work.exists():raise ValueError('fresh step required; no retry')
    left = None
    if args.step == 'candidate':
        left = bind(paths('baseline')[0])
        if not left['all_pass'] or not left['terminal_identity_verified']:raise ValueError('terminal baseline integrity required')
    locked = json.loads(D.checked(D.RESULTS/'016-corpus-state-lock.json'))['cells']['C1']
    state = Q.L.read_state(D.ROOT/locked['state_directory'])
    if state['sha256'] != locked['state_sha256']:raise ValueError('canonical C1 state differs')
    scene = Q.scene_for_state(state,8)
    legacy = bind(next(D.RESULTS.glob('371-*.json')))
    legacy_command = legacy['attempts'][0]['command']
    scene_path = Path(legacy_command[legacy_command.index('--scene')+1])
    if D.checked(scene_path).decode() != scene.text() or (scene.width,scene.height) != (320,180):
        raise ValueError('exact original371 full C1 physical scene required')
    slot = next(row for row in json.loads(D.checked(D.RESULTS/'078-all-state-cpu-port-controls.json'))['rows']
        if (row['cell'],row['vertices']) == ('C1',8))
    canonical_hits = D.checked(Path(slot['directory'])/'o.hits',slot['payload_sha256']['o.hits'])
    canonical_moments = Path(slot['directory'])/'o.s0.f64'
    D.checked(canonical_moments,slot['payload_sha256']['o.s0.f64'])
    binary = Path(original['command'][-1]) if args.step == 'baseline' else Path(prep['rows'][0]['binary'])
    expected = original['payload_sha256'][str(binary)] if args.step == 'baseline' else build['payload_sha256'][str(binary)]
    D.checked(binary,expected);D.checked(Q.NET)
    work.mkdir(parents=True);prefix = work/'o';receipt = work/'native.resources.json'
    threads = 1 if args.step == 'baseline' else 4
    command = [str(binary),'--net',str(Q.NET),'--scene',str(scene_path),'--out',str(prefix),
        '--seeds',str(D.SEEDS[0]),'--spp','16','--threads',str(threads)]
    result = dict(schema='n010-thread-private-equivalence-step/1',complete=False,all_pass=False,step=args.step,
        source_commit=commit,input_sha256=D.INPUTS,command=command,prefix=str(prefix),resource_receipt=str(receipt),
        threads=threads,actual_affinity=[31],classification='EQUIVALENCE_NATIVE_ACQUIRING',
        accepted_timing=False,reference_admission=False,gpu_run=False,
        tests='NOT_RUN; one registered full-frame scientific execution-equivalence native')
    def save():write(output,result)
    def payloads():return {str(p):D.sha(p) for p in work.iterdir() if p.is_file()}
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(300,300))
        write(receipt,dict(pid=os.getpid(),pgid=os.getpgrp(),start_ticks=start_ticks(os.getpid()),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),elapsed_limit_seconds=420),True)
    write(output,result,True)
    try:
        for name,digest in list(D.INPUTS.items()):D.checked(Path(name),digest)
        require_no_other_research_worker()
        before = resource.getrusage(resource.RUSAGE_CHILDREN);started = time.monotonic()
        with (work/'native.stdout').open('wb') as stdout,(work/'native.stderr').open('wb') as stderr:
            child = subprocess.Popen(command,cwd=D.ROOT,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=limits)
            result['native_pid'] = child.pid;save()
            try:code = child.wait(timeout=420)
            except subprocess.TimeoutExpired:
                own = json.loads(receipt.read_text())
                if ((own['pid'],own['pgid'],own['start_ticks']) != (child.pid,child.pid,start_ticks(child.pid))
                        or own['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()):
                    raise ValueError('owned equivalence native changed; refuse signalling')
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait(timeout=5);code='ELAPSED_GUARD_PARTIALS_RETAINED'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        result.update(complete=True,returncode=code,elapsed_seconds=time.monotonic()-started,
            child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            payload_sha256=payloads(),classification='EQUIVALENCE_NATIVE_TERMINAL_ANALYSIS_PENDING');save()
        own = json.loads(D.checked(receipt))
        if (code != 0 or own['pid'] != child.pid or own['pgid'] != child.pid or type(own['start_ticks']) is not int
                or own['start_ticks'] <= 0 or own['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                or own['command'] != command or own['affinity'] != [31] or own['nice'] != 15
                or own['cpu'] != [300,300] or own['address_space'] != [4*1024**3]*2
                or own['elapsed_limit_seconds'] != 420
                or result['elapsed_seconds'] >= 420 or result['child_cpu_seconds'] > 300):
            raise ValueError('actual native/resource failure')
        result['terminal_identity_verified'] = True
        resource.setrlimit(resource.RLIMIT_CPU,(120,120));signal.alarm(180)
        meta = json.loads((work/'native.stdout').read_text());run = meta['runs'][0]
        if ((meta['width'],meta['height'],meta['spp']) != (320,180,16) or meta['seeds'] != [D.SEEDS[0]]
                or len(meta['runs']) != 1 or meta['scene_sha256'] != D.sha(scene_path)
                or meta['geometry_sha256'] != scene.geometry_sha256()):raise ValueError('full physical/count/seed identity differs')
        data = Q.L.read_sidecar(Path(str(prefix)+'.s0.f64'))
        if (data['width'],data['height'],data['seed'],data['spp']) != (320,180,D.SEEDS[0],16):raise ValueError('full f64 header differs')
        if any(not np.isfinite(data[key]).all() or (data[key]<0).any() for key in ('mean','m2')):
            raise ValueError('nonfinite/negative full f64 moments')
        prior = Q.L.read_sidecar(canonical_moments)
        if (prior['width'],prior['height'],prior['seed'],prior['spp']) != (320,180,D.SEEDS[0],16):
            raise ValueError('canonical deterministic moment header differs')
        for key in ('mean','m2'):
            if not np.array_equal(data[key][...,:2,:].view(np.uint64),prior[key][...,:2,:].view(np.uint64)):
                raise ValueError('original deterministic full-frame moment bits differ')
        for j,name in enumerate(Q.L.COMPONENTS):
            image = Q.L.read_pfm(Path(str(prefix)+f'.s0.{name}.pfm'))
            if image.shape != (180,320,3) or not np.array_equal(image,data['mean'][...,j,:].astype(np.float32)):
                raise ValueError('complete PFM/sidecar identity differs')
        if Path(str(prefix)+'.hits').read_bytes() != canonical_hits:raise ValueError('original full primary records differ')
        audit = run['all_split']
        if (audit['own_checks'] != audit['component_attempts']-audit['component_nulls']
                or not np.isfinite([audit['max_own_log_error'],audit['max_conditioned_error_fraction'],audit['max_unconditioned_error_fraction']]).all()
                or audit['max_own_log_error']>1e-6 or audit['max_conditioned_error_fraction']>1):
            raise ValueError('original own/conditioned numerical or interval checks differ')
        result['native_metadata'] = meta
        if left is not None:compare(left,result)
        for name,digest in list(D.INPUTS.items()):D.checked(Path(name),digest)
        result.update(all_pass=True,classification='FULL_C1_SINGLE_CORE_EXECUTION_EQUIVALENCE_STEP_PASS',
            all_six_payload_bytes_and_exported_audits_exact=left is not None)
    except (ValueError,OSError,KeyError,IndexError,TypeError,AssertionError,subprocess.SubprocessError) as error:
        result.update(complete=True,all_pass=False,failure=str(error),classification='EQUIVALENCE_FAILURE_PARTIALS_RETAINED')
    result['payload_sha256'] = payloads();save();signal.alarm(0)
    print(json.dumps({k:result.get(k) for k in ('classification','all_pass','step','elapsed_seconds','failure')},indent=2))
    return 0 if result['all_pass'] else 2


if __name__ == '__main__':raise SystemExit(main())

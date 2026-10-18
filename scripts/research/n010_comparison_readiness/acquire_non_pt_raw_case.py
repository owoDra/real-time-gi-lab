#!/usr/bin/env python3
"""Plan153: describe the seven remaining cases or acquire exactly one."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import non_pt_raw_provenance as N
from non_pt_raw_provenance import C, P, R
from acquire_continuation_quality_case import identity_environment
from build_raw_query_pilots import quiet

PLAN = R.RESULTS.parent/'experiments/153-one-full-non-pt-trajectory-per-invocation.md'
DESCRIPTION = R.RESULTS/'521-bounded-non-pt-acquisition-description.json'
CASES = tuple(b for b in N.SCOPE if b != 'static-C7-dense-rc')


def start_ticks(pid):
    try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
    except FileNotFoundError:return None


def write(path, value, fresh=False):
    with path.open('x' if fresh else 'w') as stream:
        stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def prepare():
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    sources = {PLAN,N.PLAN,Path(__file__).resolve(),Path(N.__file__).resolve()}
    for module in tuple(sys.modules.values()):
        name = getattr(module,'__file__',None)
        if name and Path(name).resolve().is_relative_to(R.ROOT/'scripts/research'):
            sources.add(Path(name).resolve())
    for path in sorted(sources):
        C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))]) == R.checked(path),
            'commit exact acquisition/intake/registrations before dispatch')
    description = C.read(R.RESULTS/'511-full-non-pt-raw-intake-description.json')
    build, lock = C.read(N.BUILD),C.read(N.LOCK)
    C.require(description['complete'] and description['non_pt_count'] == 8
        and description['new_trajectory_commands'] == 7 and build['complete'] and build['build_valid'],
        'fixed511 commands and actual506 private build required')
    for proof in (description,build):
        for group in ('input_sha256','payload_sha256'):
            for name,digest in proof.get(group,{}).items():R.checked(name,digest)
    rows = [r for r in description['rows'] if r['boundary_id'] in CASES]
    C.require(len(rows) == 7 and {r['boundary_id'] for r in rows} == set(CASES),
        'full seven remaining non-PT cases differ')
    for row in rows:
        command = row['command']
        capture = Path(command[command.index('--out')+1])
        C.require(command == N.command(row['boundary_id'],capture,build,lock),
            'registered511 command changed')
    return commit,rows,build,lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--describe',action='store_true')
    mode.add_argument('--case',choices=CASES)
    args = parser.parse_args()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    C.require(all(os.environ.get(k) == '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')),
        'one numerical thread required')
    # A live scientific worker must be rejected before creating any case file.
    if not args.describe:quiet()
    commit,rows,build,lock = prepare()
    if args.describe:
        C.require(not DESCRIPTION.exists(), 'fresh command description required')
        tree = ast.parse(Path(__file__).read_text())
        result = dict(schema='n010-bounded-non-pt-acquisition-description/1',complete=True,
            classification='SEVEN_SINGLE_CASE_ACQUISITION_COMMANDS_SOURCE_ONLY',source_commit=commit,
            input_sha256=R.INPUTS,rows=rows,allowed_cases=list(CASES),
            source_ast_sha256=hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest(),
            first_intended_case='static-C7-hwrt',native_executed=False,gpu_run=False,
            raw_evidence_replayed=False,accepted_timing=False,reference_admission=False,
            limits=dict(cpu_seconds=120,elapsed_seconds=180,affinity=[31],nice=15,
                native_address_space='unlimited Vulkan virtual mappings; owned cap8GiB',
                analysis_address_space_bytes=2*1024**3),
            tests='NOT_RUN; source/AST/command/full input identities only')
        R.unchanged();write(DESCRIPTION,result,True)
        print(result['classification']);return 0
    row = next(r for r in rows if r['boundary_id'] == args.case)
    output = Path(row['future_result'])
    command = row['command']
    capture = Path(command[command.index('--out')+1])
    work = capture.parent
    C.require(not output.exists() and not work.exists(), 'refuse existing native/result/partials; no retry')
    cell,role,dynamic = N.identity(args.case)
    spec = lock['cells'][cell]
    for directory in (spec['state_directory'],spec['source_directory'] if dynamic else spec['state_directory']):
        for name in ('geometry-state.bin','frame-state.bin'):R.checked(R.ROOT/directory/name)
    if role != 'dense-rc':R.checked(N.CONTRACT)
    env = os.environ.copy()
    # Clear inherited experimental switches; retain the host's Vulkan wrapper environment.
    for key in list(env):
        if key.startswith('PHOS_'):del env[key]
    env.update(row['environment_switches'])
    receipt = work/'native.resources.json'
    result = dict(schema='n010-bounded-non-pt-raw-pilot/1',complete=False,
        classification='ONE_FULL_NON_PT_NATIVE_ACQUIRING',source_commit=commit,
        boundary_id=args.case,cell=cell,role=role,dynamic=dynamic,command=command,
        environment=identity_environment(),environment_switches=row['environment_switches'],
        input_sha256=R.INPUTS,execution_evidence_valid=False,quality_evidence_valid=False,
        accepted_timing=False,reference_admission=False,gpu_run=True,
        tests='NOT_RUN; exactly one registered full descriptive scientific trajectory')
    def payloads():
        paths = [p for p in capture.rglob('*') if p.is_file()]
        paths += [work/name for name in ('raw-queries.jsonl','native.resources.json','native.stdout','native.stderr')]
        return {str(p):P.sha(p) for p in paths if p.exists()}
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(120,120))
        resource.setrlimit(resource.RLIMIT_AS,(resource.RLIM_INFINITY,)*2)
        write(receipt,dict(pid=os.getpid(),pgid=os.getpgrp(),start_ticks=start_ticks(os.getpid()),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            elapsed_limit_seconds=180),True)
    # Acquisition is manual and serial; an idle percentage is never a trigger.
    quiet();R.unchanged()
    work.mkdir(parents=True);write(output,result,True)
    try:
        before = resource.getrusage(resource.RUSAGE_CHILDREN);started = time.monotonic()
        with (work/'native.stdout').open('wb') as stdout,(work/'native.stderr').open('wb') as stderr:
            child = subprocess.Popen(command,cwd=R.ROOT,env=env,stdout=stdout,stderr=stderr,
                start_new_session=True,preexec_fn=limits)
            result['native_pid'] = child.pid;write(output,result)
            try:code = child.wait(timeout=180)
            except subprocess.TimeoutExpired:
                owned = json.loads(receipt.read_text())
                C.require((owned['pid'],owned['pgid'],owned['start_ticks']) ==
                    (child.pid,child.pid,start_ticks(child.pid)), 'owned native identity differs; refuse signalling')
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait(timeout=5);code = 'ELAPSED_GUARD_PARTIALS_RETAINED'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        result.update(complete=True,native_returncode=code,elapsed_seconds=time.monotonic()-started,
            child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            classification='FULL_NON_PT_NATIVE_TERMINAL_ANALYSIS_PENDING',payload_sha256=payloads())
        write(output,result)
        # Immutable native snapshot is the replay input, not the mutable output.
        native_record = work/'native-record.json'
        write(native_record,result,True)
        C.require(code == 0, 'native failed; retain partials and stop without retry')
        resource.setrlimit(resource.RLIMIT_CPU,(120,120))
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
        signal.alarm(180)
        proof = N.verify_capture(native_record,args.case)
        result.update(execution_evidence_valid=True,validation=proof,
            classification='FULL_NON_PT_RAW_EXECUTION_VALID_QUALITY_REPLAY_PENDING',
            timing_precision='TIMING_INCONCLUSIVE',quality_evidence_valid=False,
            quality_status='NOT_SCORED; both eligible transports/full images required before handoff')
        R.unchanged()
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(complete=True,classification='NON_PT_RAW_PILOT_FAILURE_PARTIALS_RETAINED',failure=str(error))
    result['payload_sha256'] = payloads()
    write(output,result);signal.alarm(0)
    print(json.dumps({k:result.get(k) for k in ('classification','boundary_id','execution_evidence_valid',
        'quality_evidence_valid','native_returncode','elapsed_seconds','failure')},indent=2))
    return 0 if result['execution_evidence_valid'] else 2


if __name__ == '__main__':raise SystemExit(main())

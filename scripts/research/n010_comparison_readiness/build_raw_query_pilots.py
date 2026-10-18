#!/usr/bin/env python3
"""Plan149: describe or compile exactly the private raw-query pilot fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import signal
import subprocess
import sys
import time

import prepare_raw_query_pilots as P
sys.path.insert(0,str(P.ROOT/'scripts/research/n010_reference_sampling'))
from build_continuation_pixel_pt import quiet

PLAN = P.RESULTS.parent/'experiments/149-build-private-raw-query-pilots.md'
DESCRIPTION = P.RESULTS/'505-raw-query-pilot-build-description.json'
OUTPUT = P.RESULTS/'506-raw-query-pilot-build.json'


def start_ticks(pid):
    try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
    except FileNotFoundError:return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--describe',action='store_true');args = ap.parse_args()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    output = DESCRIPTION if args.describe else OUTPUT
    if output.exists():raise ValueError('refuse existing output; no overwrite/retry')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for p in (Path(__file__).resolve(),PLAN,Path(P.__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(p.relative_to(P.ROOT))]) != P.checked(p):
            raise ValueError('commit exact private builder/recipe before execution')
    prep = json.loads(P.checked(P.OUTPUT))
    if not (prep['complete'] and prep['source_preparation_valid'] and prep['whole_source_inverses_exact']
            and prep['runtime_entire_file_byte_identical_to184'] and prep['dense_gpu_lambda_byte_identical_to184']
            and prep['all_shader_bytes_unchanged'] and not prep['compiled']):
        raise ValueError('complete unchanged504 source preparation required')
    for group in ('input_sha256','payload_sha256'):
        for path,digest in prep[group].items():P.checked(path,digest)
    stages = prep['stages']
    if len(stages) != 8:raise ValueError('exact eight-stage private build required')
    if args.describe:
        result = dict(schema='n010-raw-query-pilot-build-description/1',complete=True,
            classification='PRIVATE_COMPILER_COMMAND_METADATA_ONLY',source_commit=commit,
            stages=stages,binaries=prep['binaries'],input_sha256=P.INPUTS,
            native_compilers_launched=0,gpu_run=False,tests='NOT_RUN; command metadata only')
        with output.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(result['classification']);return 0
    quiet()
    control = json.loads(P.checked(P.RESULTS/'487-compensated-a6c-full-control.json'))
    if not (control['complete'] and control['all_pass'] and control['terminal_identity_verified']):
        raise ValueError('actual terminal candidate487 physical PASS required')
    for group in ('input_sha256','payload_sha256'):
        for path,digest in control[group].items():P.checked(path,digest)
    description = json.loads(P.checked(DESCRIPTION))
    if description['stages'] != stages or description['binaries'] != prep['binaries']:
        raise ValueError('commands differ from frozen505')
    if P.FUTURE_BUILD.exists():raise ValueError('refuse existing build/partials; no retry')
    P.FUTURE_BUILD.mkdir()
    result = dict(schema='n010-raw-query-pilot-build/1',complete=False,build_valid=False,
        classification='PRIVATE_RAW_QUERY_BUILD_IN_PROGRESS',source_commit=commit,
        input_sha256=P.INPUTS,attempts=[],binaries=prep['binaries'],gpu_run=False,
        accepted_timing=False,reference_admission=False,tests='NOT_RUN; private compilation only')

    def save():OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    def unchanged():
        for path,digest in list(P.INPUTS.items()):P.checked(path,digest)
    save()
    try:
        for stage in stages:
            quiet();unchanged()
            if str(Path(stage['command'][0]).resolve()) != stage['compiler_realpath']:
                raise ValueError('compiler symlink changed')
            receipt = P.FUTURE_BUILD/(stage['label']+'.resources.json')
            def limits():
                resource.setrlimit(resource.RLIMIT_CPU,(120,120))
                receipt.write_text(json.dumps(dict(pid=os.getpid(),pgid=os.getpgrp(),
                    start_ticks=start_ticks(os.getpid()),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
                    elapsed_limit_seconds=180,command=stage['command'],cwd=stage['cwd']))+'\n')
            row = dict(stage,terminal=False,receipt=str(receipt))
            result['attempts'].append(row);save()
            before = resource.getrusage(resource.RUSAGE_CHILDREN);started = time.monotonic()
            with (P.FUTURE_BUILD/(stage['label']+'.stdout')).open('wb') as out,(P.FUTURE_BUILD/(stage['label']+'.stderr')).open('wb') as err:
                child = subprocess.Popen(stage['command'],cwd=stage['cwd'],stdout=out,stderr=err,
                    start_new_session=True,preexec_fn=limits)
                row['pid'] = child.pid;save()
                try:code = child.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    owned = json.loads(receipt.read_text())
                    if (owned['pid'],owned['pgid'],owned['start_ticks']) != (child.pid,child.pid,start_ticks(child.pid)):
                        raise ValueError('owned compiler identity differs; refuse signalling')
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    child.wait(timeout=5);code='TIMEOUT_PARTIALS_RETAINED'
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            row.update(terminal=True,returncode=code,elapsed_seconds=time.monotonic()-started,
                child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
            save()
            actual = json.loads(P.checked(receipt))
            if (code != 0 or actual['pid'] != child.pid or actual['pgid'] != child.pid
                    or type(actual['start_ticks']) is not int or actual['cpu'] != [120,120]
                    or actual['address_space'] != [4*1024**3]*2 or actual['affinity'] != [31] or actual['nice'] != 15
                    or actual['command'] != stage['command'] or actual['cwd'] != stage['cwd']
                    or row['elapsed_seconds'] >= 180 or row['child_cpu_seconds'] > 120):
                raise ValueError('private compiler/resource failure; no subsequent stage')
            if '-c' in stage['command']:
                depfile = Path(stage['produced']).with_suffix('.d')
                for name in shlex.split(depfile.read_text().replace('\\\n',' ').split(':',1)[1]):
                    path = Path(name);P.checked(path if path.is_absolute() else Path(stage['cwd'])/path)
            raw = P.checked(stage['produced'])
            if not raw.startswith(b'\x7fELF'):raise ValueError('private output is not ELF')
            if stage['label'].endswith('-link') and not os.access(stage['produced'],os.X_OK):
                raise ValueError('private binary is not executable')
            unchanged()
        result.update(build_valid=True,classification='PRIVATE_RAW_QUERY_BUILD_COMPLETE_RUNTIME_NOT_RUN')
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='PRIVATE_RAW_QUERY_BUILD_FAILURE_PARTIALS_RETAINED')
    result.update(complete=True,payload_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in P.FUTURE_BUILD.rglob('*') if p.is_file()})
    save();print(result['classification']);return 0 if result['build_valid'] else 2


if __name__ == '__main__':raise SystemExit(main())

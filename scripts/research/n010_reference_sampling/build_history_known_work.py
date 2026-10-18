#!/usr/bin/env python3
"""Plan135: describe or build only the private history-preserving PT fixture."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import signal
import subprocess
import time

import build_continuation_pixel_pt as B

ROOT,RESULTS,checked,unchanged,INPUTS=B.ROOT,B.RESULTS,B.checked,B.unchanged,B.INPUTS
PLAN=RESULTS.parent/'experiments/135-bounded-history-known-work.md'
SOURCE=ROOT/'out/research/n010-comparison-readiness/history-known-work-source-v1'
WORK=SOURCE.with_name('history-known-work-build-v1')
DESCRIPTION=RESULTS/'430-history-known-work-build-description.json'
OUTPUT=RESULTS/'431-history-known-work-build.json'
PT=B.WORK/'shaders/n010_pixel_pt.spv'


def commands():
    prep=json.loads(checked(RESULTS/'428-history-known-work-source-prepare.json'))
    if not (prep['complete'] and prep['source_preparation_valid'] and not prep['compiled']
            and prep['whole_host_inverse_exact'] and prep['pt_shader_byte_identical_to405']
            and prep['original_history_update_seed_flow_byte_identical']
            and prep['known_work_recurrence_body_byte_identical']):
        raise ValueError('complete source428 required')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in prep[group].items():checked(name,digest)
    checked(PT)
    rows=B.commands()  # Ninja command/dependency inspection only; no compiler.
    planned=[]
    for old in rows:
        row=dict(old)
        args=[arg.replace(str(B.SOURCE),str(SOURCE)).replace(str(B.WORK),str(WORK))
              for arg in old['command']]
        if old['label']=='shader':
            args=[a.replace(str(SOURCE/'continuation_pixel_pt.comp.glsl'),
                            str(SOURCE/'n010_history_neutral_work.comp.glsl')) for a in args]
            args[args.index('-o')+1]=str(WORK/'shaders/n010_history_neutral_work.spv')
            produced=WORK/'shaders/n010_history_neutral_work.spv'
        elif old['label']=='host':
            args=[a.replace(str(SOURCE/'continuation_pixel_pt.cpp'),
                            str(SOURCE/'history_known_work_pixel_pt.cpp')) for a in args]
            produced=WORK/'continuation_pixel_pt.o'
        else:
            args[args.index('-o')+1]=str(WORK/'phos-n010-history-known-work-pixel-pt')
            produced=WORK/'phos-n010-history-known-work-pixel-pt'
        row.update(command=args,produced=str(produced))
        planned.append(row)
    if [r['label'] for r in planned]!=['shader','host','link']:
        raise ValueError('exact private three-stage build required')
    return planned


def process_start(pid):
    try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
    except FileNotFoundError:return None


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--describe',action='store_true')
    args=ap.parse_args()
    os.sched_setaffinity(0,{31})
    priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    output=DESCRIPTION if args.describe else OUTPUT
    if output.exists():raise ValueError('refuse existing output; no overwrite/retry')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))])!=checked(path):
            raise ValueError('commit exact builder/plan before use')
    planned=commands();unchanged()
    if args.describe:
        result=dict(schema='n010-history-known-work-build-description/1',complete=True,
            source_commit=commit,classification='PRIVATE_BUILD_COMMAND_METADATA_ONLY',stages=planned,
            native_compilers_launched=0,gpu_run=False,all_pass=False,input_sha256=INPUTS,
            unchanged_pt_spirv_source=str(PT),unchanged_pt_spirv_sha256=hashlib.sha256(PT.read_bytes()).hexdigest(),
            tests='NOT_RUN; Ninja command/dependency inspection only')
        with output.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(result['classification']);return 0
    B.quiet()
    control=json.loads(checked(RESULTS/'261-wide8-original-a6a-seed2.json'))
    if not control['complete'] or not control['seed_integrity_pass']:
        raise ValueError('terminal integrity-PASS261 required; no waiting or compiler queue')
    described=json.loads(checked(DESCRIPTION))
    if described['stages']!=planned:raise ValueError('actual commands differ from frozen430 description')
    if WORK.exists():raise ValueError('refuse existing build/partials; no retry')
    if shutil.disk_usage(WORK.parent).free<2*1024**3:raise ValueError('2GiB disk guard')
    WORK.mkdir();(WORK/'shaders').mkdir()
    shutil.copyfile(PT,WORK/'shaders/n010_pixel_pt.spv')
    if checked(WORK/'shaders/n010_pixel_pt.spv')!=checked(PT):raise ValueError('PT SPIR-V copy differs')
    result=dict(schema='n010-history-known-work-build/1',complete=False,build_valid=False,all_pass=False,
        gpu_run=False,accepted_timing=False,reference_admission=False,source_commit=commit,
        input_sha256=INPUTS,attempts=[],pt_spirv_byte_identical_to401=True,
        classification='PRIVATE_HISTORY_KNOWN_WORK_BUILD_IN_PROGRESS',tests='NOT_RUN; private compilation only')
    def save():OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()
    try:
        for stage in planned:
            B.quiet();unchanged()
            if str(Path(stage['command'][0]).resolve())!=stage['compiler_realpath']:
                raise ValueError('compiler symlink changed')
            receipt=WORK/(stage['label']+'.resources.json')
            def limits():
                resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
                receipt.write_text(json.dumps(dict(pid=os.getpid(),pgid=os.getpgrp(),
                    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    start_ticks=process_start(os.getpid()),cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
                    address_space=list(resource.getrlimit(resource.RLIMIT_AS)),affinity=sorted(os.sched_getaffinity(0)),
                    nice=os.getpriority(os.PRIO_PROCESS,0),elapsed_limit_seconds=180,
                    command=stage['command'],cwd=stage['cwd']))+'\n')
            row=dict(stage,terminal=False,receipt=str(receipt));result['attempts'].append(row);save()
            started=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
            with (WORK/(stage['label']+'.stdout')).open('wb') as out,(WORK/(stage['label']+'.stderr')).open('wb') as err:
                child=subprocess.Popen(stage['command'],cwd=stage['cwd'],stdout=out,stderr=err,
                    start_new_session=True,preexec_fn=limits)
                row['pid']=child.pid;save()
                try:code=child.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    owned=json.loads(receipt.read_text())
                    if (owned['pid'],owned['pgid'],owned['start_ticks'])!=(child.pid,child.pid,process_start(child.pid)):
                        raise ValueError('owned compiler identity differs; refuse signalling')
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    child.wait(timeout=5);code='TIMEOUT_PARTIALS_RETAINED'
            after=resource.getrusage(resource.RUSAGE_CHILDREN)
            row.update(terminal=True,returncode=code,elapsed_seconds=time.monotonic()-started,
                child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
            save();actual=json.loads(checked(receipt))
            if (code!=0 or actual['pid']!=child.pid or actual['pgid']!=child.pid or type(actual['start_ticks']) is not int
                    or actual['cpu']!=[120,120] or actual['address_space']!=[4*1024**3]*2
                    or actual['affinity']!=[31] or actual['nice']!=15 or actual['command']!=stage['command']
                    or actual['cwd']!=stage['cwd'] or row['elapsed_seconds']>=180 or row['child_cpu_seconds']>120):
                raise ValueError('compiler/resources failed; no following stage')
            if stage['label']=='host':
                depfile=(WORK/'continuation_pixel_pt.d').read_text().replace('\\\n',' ')
                for name in shlex.split(depfile.split(':',1)[1]):
                    path=Path(name);checked(path if path.is_absolute() else B.BUILD/path)
            raw=checked(stage['produced'])
            magic=b'\x03\x02\x23\x07' if stage['label']=='shader' else b'\x7fELF'
            if not raw.startswith(magic):raise ValueError('private compiler output format differs')
            if stage['label']=='link' and not os.access(stage['produced'],os.X_OK):
                raise ValueError('private output not executable')
            if str(Path(stage['command'][0]).resolve())!=stage['compiler_realpath']:
                raise ValueError('compiler symlink changed during stage')
            unchanged()
        result.update(build_valid=True,all_pass=True,classification='PRIVATE_HISTORY_KNOWN_WORK_BUILD_COMPLETE_RUNTIME_NOT_RUN')
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='PRIVATE_HISTORY_KNOWN_WORK_BUILD_FAILURE_RETAINED')
    result.update(complete=True,payload_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in WORK.rglob('*') if p.is_file()})
    save();print(result['classification']);return 0 if result['build_valid'] else 2


if __name__=='__main__':raise SystemExit(main())

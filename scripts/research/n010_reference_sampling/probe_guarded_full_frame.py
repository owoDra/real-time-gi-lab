#!/usr/bin/env python3
"""Plan124: one guarded whole-frame capture against retained371, no queue."""
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import textwrap
import time

import probe_batched_full_frame_hybrid as P
from build_tiled_pixel_pt import quiet

D = P.D
PLAN = D.RESULTS.parent/'experiments/124-guarded-full-frame-conformance.md'
WORK = D.OUT/'guarded-full-frame-conformance-v1'
OUTPUT = D.RESULTS/'393-guarded-full-frame-conformance.json'
CANDIDATE = D.OUT/'early-density-route-diagnostic-v1/build'


def prior(number, suffix):
    data = json.loads(D.checked(D.RESULTS/f'{number}-{suffix}.json'))
    if not data['complete']:
        raise ValueError('terminal prerequisite required')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in data[group].items():
            D.checked(Path(name),digest)
    return data


def validator():
    source = D.checked(Path(P.__file__)).decode()
    begin = "            directory=work/'gpu';meta=json.loads("
    end = "        if sum(p.stat().st_size for p in WORK.rglob('*')"
    if source.count(begin) != 1 or source.count(end) != 1:
        raise ValueError('parent validation anchors differ')
    raw = source[source.index(begin):source.index(end)]
    body = textwrap.dedent(raw)
    generated = 'def validate(work,build,scene,net,old_hits,old_meta,result):\n'+textwrap.indent(body,'    ')
    parsed = ast.parse(generated).body[0].body
    if [ast.dump(x,include_attributes=False) for x in parsed] != [
            ast.dump(x,include_attributes=False) for x in ast.parse(body).body]:
        raise ValueError('complete parent validator AST differs')
    namespace = vars(P).copy()
    exec(compile(generated,'<exact-plan115-gpu-validation>','exec'),namespace)
    return namespace['validate'], raw


def main():
    if OUTPUT.exists() or WORK.exists():
        raise ValueError('refuse existing393/work; no retry')
    quiet()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:
        os.nice(15-priority)
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN,Path(__file__).with_name('build_tiled_pixel_pt.py')):
        D.checked(path)
        frozen = subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))])
        if frozen != path.read_bytes():
            raise ValueError('commit exact driver/plan/quiet check before acquisition')
    candidate = prior(381,'early-density-route-build')
    guarded = prior(383,'early-density-route-guarded')
    if (not candidate['step_valid'] or not guarded['step_valid']
            or not guarded['validation']['all16_corrected_scored_and_proposal_counts_exact']
            or not guarded['validation']['old_new_raw_paths_bit_exact']):
        raise ValueError('registered focused conformance required')
    prior(390,'tiled-pixel-pt-build')
    prior(395,'tiled-pt-first-capture-failure')
    cpu = P.prior('cpu')
    command = cpu['attempts'][0]['command']
    scene,net = (Path(command[command.index(flag)+1]) for flag in ('--scene','--net'))
    old_meta = json.loads(D.checked(scene.parent/'n8192.meta.json'))
    old_hits = D.checked(scene.parent/'o.n8192.hits')
    validate,raw = validator()
    if shutil.disk_usage(D.OUT).free < 2*1024**3:
        raise ValueError('2GiB disk guard; no native')
    WORK.mkdir()
    (WORK/'original-validator-body.py.txt').write_text(raw)
    command = ['bash',str(D.ROOT/'scripts/run_with_vulkan.sh'),str(CANDIDATE/'probe'),
        str(scene),str(net),str(CANDIDATE/'full.spv'),'305419896','16','16','512',
        'full','0','-',str(WORK/'gpu'),'1']
    D.checked(D.ROOT/'scripts/run_with_vulkan.sh')
    result = dict(schema='n010-guarded-full-frame-conformance/1',complete=False,
        conformance_valid=False,all_pass=False,accepted_timing=False,reference_admission=False,
        gpu_run=True,source_commit=commit,input_sha256=D.INPUTS,attempts=[],
        parent_validator_body_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        parent_validator_ast_exact=True,classification='GUARDED_FULL_FRAME_ACQUIRING',
        tests='NOT_RUN; registered all-pixel scientific conformance only')

    def save():
        OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

    receipt = WORK/'native.resources.json'

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(120,120))
        receipt.write_text(json.dumps(dict(pid=os.getpid(),pgid=os.getpgrp(),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
            elapsed_limit_seconds=180,command=command))+'\n')

    row = dict(command=command,resource_receipt=str(receipt),terminal=False)
    result['attempts'].append(row)
    save()
    try:
        quiet()
        started = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        with (WORK/'native.stdout').open('wb') as out,(WORK/'native.stderr').open('wb') as err:
            native = subprocess.Popen(command,cwd=D.ROOT,stdout=out,stderr=err,
                                      start_new_session=True,preexec_fn=limits)
            row['pid'] = native.pid
            save()
            try:
                code = native.wait(timeout=180)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(native.pid,signal.SIGKILL)
                except ProcessLookupError:
                    pass
                native.wait(timeout=5)
                code = 'TIMEOUT_PARTIALS_RETAINED'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        row.update(terminal=True,returncode=code,elapsed_seconds=time.monotonic()-started,
            child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
        save()
        actual = json.loads(D.checked(receipt))
        if (code != 0 or actual['pid'] != native.pid or actual['pgid'] != native.pid
                or actual['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                or actual['cpu'] != [120,120] or actual['address_space'] != [4*1024**3]*2
                or actual['affinity'] != [31] or actual['nice'] != 15 or actual['command'] != command):
            raise ValueError('native/resource failure; retain partials')
        validate(WORK,dict(backend_id=candidate['validation']['backend_id']),scene,net,old_hits,old_meta,result)
        if sum(p.stat().st_size for p in WORK.rglob('*') if p.is_file()) > 1024**3:
            raise ValueError('retained work exceeds1GiB')
        for name,digest in list(D.INPUTS.items()):
            D.checked(Path(name),digest)
        result.update(conformance_valid=True,classification='GUARDED_FULL_FRAME_CONFORMANCE_PASS_NO_ADMISSION')
    except (ValueError,OSError,KeyError,StopIteration,AssertionError,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='GUARDED_FULL_FRAME_FAILURE_RETAINED')
    result['complete'] = True
    result['payload_sha256'] = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in WORK.rglob('*') if p.is_file()}
    save()
    print(result['classification'])
    return 0 if result['conformance_valid'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

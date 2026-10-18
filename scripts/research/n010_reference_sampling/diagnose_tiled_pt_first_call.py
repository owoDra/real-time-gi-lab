#!/usr/bin/env python3
"""Plan125: explicit source, host/link, or ONE first-tile Vulkan trace."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time

from build_tiled_pixel_pt import quiet

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
BASE = ROOT/'out/research/n010-comparison-readiness'
WORK = BASE/'tiled-pt-first-call-diagnostic-v1'
PLAN = RESULTS.parent/'experiments/125-tiled-pt-first-call-diagnostic.md'
STEPS = ('prepare','build','probe')
INPUTS = {}


def checked(path, expected=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('input differs: '+str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != digest:
        raise ValueError('input changed: '+str(path))
    INPUTS[str(path)] = digest
    return raw


def unchanged():
    for path,digest in list(INPUTS.items()):
        checked(path,digest)


def location(step):
    return RESULTS/f'{396+STEPS.index(step)}-tiled-pt-first-call-{step}.json'


def prior(path, valid=None):
    data = json.loads(checked(path))
    if not data['complete'] or (valid and not data[valid]):
        raise ValueError('valid terminal prerequisite required')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in data.get(group,{}).items():
            checked(name,digest)
    return data


def edit_source(original):
    old = 'void check(VkResult result) { if(result!=VK_SUCCESS) throw std::runtime_error("Vulkan operation failed"); }'
    new = '''void check_record(VkResult result,const char* operation,int line) {
    std::cerr<<"VK_CHECK "<<line<<" "<<int(result)<<" "<<operation<<std::endl;
    if(result!=VK_SUCCESS) throw std::runtime_error("Vulkan operation failed");
}
#define check(operation) check_record((operation),#operation,__LINE__)'''
    anchor = '                pixel_begin+=count;'
    stop = '''                if(pixel_begin==0)throw std::runtime_error("DIAGNOSTIC_FIRST_TILE_COMPLETE_NO_IMAGE");
'''+anchor
    if original.count(old) != 1 or original.count(anchor) != 1:
        raise ValueError('unique original host anchors required')
    generated = original.replace(old,new).replace(anchor,stop)
    if generated.replace(stop,anchor).replace(new,old) != original:
        raise ValueError('whole host inverse differs')
    return generated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--step',choices=STEPS,required=True)
    step = parser.parse_args().step
    output,work = location(step),WORK/step
    if output.exists() or work.exists():
        raise ValueError('refuse existing part; no retry')
    quiet()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:
        os.nice(15-priority)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN,Path(__file__).with_name('build_tiled_pixel_pt.py')):
        raw = checked(path)
        if raw != subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))]):
            raise ValueError('commit exact source/policy before any step')
    build = prior(RESULTS/'390-tiled-pixel-pt-build.json','build_valid')
    prior(RESULTS/'393-guarded-full-frame-conformance.json','conformance_valid')
    failed = prior(RESULTS/'395-tiled-pt-first-capture-failure.json')
    if failed['numerical_replay_valid'] or failed['native_returncode'] != 1:
        raise ValueError('retain exact395 failure')
    original = BASE/'tiled-pixel-pt-source-v1/tiled_pixel_pt.cpp'
    shader = BASE/'tiled-pixel-pt-build-v1/shaders/n010_pixel_pt.spv'
    checked(shader,build['payload_sha256'][str(shader)])
    if step != 'prepare':
        prior(location('prepare'),'step_valid')
    if step == 'probe':
        prior(location('build'),'step_valid')
    if shutil.disk_usage(BASE).free < 2*1024**3:
        raise ValueError('2GiB disk guard; no native')
    work.mkdir(parents=True)
    result = dict(schema='n010-tiled-pt-first-call-diagnostic/1',step=step,
        complete=False,step_valid=False,all_pass=False,accepted_timing=False,reference_admission=False,
        source_commit=commit,input_sha256=INPUTS,attempts=[],gpu_run=step=='probe',
        classification='FIRST_CALL_DIAGNOSTIC_IN_PROGRESS',
        tests='NOT_RUN; post-hoc source/build/first-tile scientific diagnosis only')

    def save():
        output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

    def native(command,label,cpu_limit,elapsed_limit,address_limit,cwd):
        receipt = work/(label+'.resources.json')
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU,(cpu_limit,cpu_limit))
            resource.setrlimit(resource.RLIMIT_AS,(address_limit,address_limit))
            receipt.write_text(json.dumps(dict(pid=os.getpid(),pgid=os.getpgrp(),
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
                elapsed_limit_seconds=elapsed_limit,command=command,cwd=str(cwd)))+'\n')
        row = dict(command=command,label=label,terminal=False,resource_receipt=str(receipt))
        result['attempts'].append(row)
        save()
        quiet()
        unchanged()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        started = time.monotonic()
        with (work/(label+'.stdout')).open('wb') as out,(work/(label+'.stderr')).open('wb') as err:
            proc = subprocess.Popen(command,cwd=cwd,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits)
            row['pid'] = proc.pid
            save()
            try:
                code = proc.wait(timeout=elapsed_limit)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5)
                code = 'TIMEOUT_PARTIALS_RETAINED'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        row.update(terminal=True,returncode=code,elapsed_seconds=time.monotonic()-started,
            child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
        save()
        actual = json.loads(checked(receipt))
        if (actual['pid'] != proc.pid or actual['pgid'] != proc.pid or actual['start_ticks'] <= 0
                or actual['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                or actual['cpu'] != [cpu_limit]*2 or actual['address_space'] != [address_limit]*2
                or actual['affinity'] != [31] or actual['nice'] != 15
                or actual['command'] != command or actual['cwd'] != str(cwd)):
            raise ValueError('native resource identity differs')
        if (label != 'gpu' and code != 0) or (label == 'gpu' and code != 1):
            raise ValueError('native did not reach expected bounded diagnostic exit')

    save()
    try:
        if step == 'prepare':
            generated = edit_source(checked(original).decode())
            (work/'first_call.cpp').write_text(generated)
            result['validation'] = dict(whole_host_inverse_exact=True,shader_unchanged=True,
                shader_sha256=INPUTS[str(shader)],first_tile_only=True)
        elif step == 'build':
            host = next(row for row in build['attempts'] if row['label']=='host')
            link = next(row for row in build['attempts'] if row['label']=='link')
            command = list(host['command'])
            old_object = command[command.index('-o')+1]
            for flag,value in (('-c',WORK/'prepare/first_call.cpp'),('-o',work/'first_call.o'),
                               ('-MT',work/'first_call.o'),('-MF',work/'first_call.d')):
                command[command.index(flag)+1] = str(value)
            native(command,'host',120,180,4*1024**3,host['cwd'])
            checked(work/'first_call.o')
            command = list(link['command'])
            if command.count(old_object) != 1:
                raise ValueError('exact original object substitution required')
            command = [str(work/'first_call.o') if word==old_object else word for word in command]
            command[command.index('-o')+1] = str(work/'first_call')
            command = ['-Wl,--dependency-file='+str(work/'first_call.link.d')
                       if word.startswith('-Wl,--dependency-file=') else word for word in command]
            native(command,'link',120,180,4*1024**3,link['cwd'])
            if not checked(work/'first_call').startswith(b'\x7fELF'):
                raise ValueError('private diagnostic ELF required')
            result['validation'] = dict(host_link_complete=True,shader_unchanged=True,runtime_not_run=True)
        else:
            command = list(failed['command'])
            command[2] = str(WORK/'build/first_call')
            command[command.index('--out')+1] = str(work/'capture')
            native(command,'gpu',10,5,resource.RLIM_INFINITY,ROOT)
            stderr = checked(work/'gpu.stderr').decode()
            source_lines = checked(WORK/'prepare/first_call.cpp').decode().splitlines()
            trace = []
            for line in stderr.splitlines():
                if not line.startswith('VK_CHECK '):
                    continue
                _,site,code,operation = line.split(' ',3)
                site,code = int(site),int(code)
                if not 1 <= site <= len(source_lines) or operation not in source_lines[site-1]:
                    raise ValueError('trace source site differs')
                trace.append(dict(line=site,result=code,operation=operation,source=source_lines[site-1]))
            failed_calls = [row for row in trace if row['result'] != 0]
            if not trace or len(failed_calls)>1 or (failed_calls and trace[-1] != failed_calls[0]):
                raise ValueError('incomplete or inconsistent call trace')
            tiles = work/'capture/tile-timings.jsonl'
            rows = [json.loads(x) for x in checked(tiles).splitlines()]
            if len(rows)>1:
                raise ValueError('more than the first tile ran')
            if failed_calls:
                outcome = 'OBSERVED_VULKAN_CALL_FAILURE_NO_RETROACTIVE_ATTRIBUTION'
            elif 'DIAGNOSTIC_FIRST_TILE_COMPLETE_NO_IMAGE' in stderr and len(rows)==1:
                outcome = 'FIRST_TILE_COMPLETE_ORIGINAL395_FAILURE_NOT_REPRODUCED'
            elif 'tile time/receipt guard; partials retained' in stderr:
                outcome = 'COMPLETED_TILE_OPERATIONAL_STOP_NO_VULKAN_CALL_FAILURE'
            else:
                raise ValueError('bounded stop lacks an identified diagnostic outcome')
            ledger = json.loads(checked(work/'capture/allocation-ledger.json'))
            result['validation'] = dict(outcome=outcome,trace=trace,failed_calls=failed_calls,
                completed_tile_receipts=rows,owned_ledger=ledger,
                scope='First tile only; no complete image, numerical, timing or accepted-memory conclusion')
        unchanged()
        result.update(step_valid=True,classification='FIRST_CALL_DIAGNOSTIC_STEP_COMPLETE_NO_ADMISSION')
    except (OSError,ValueError,KeyError,IndexError,StopIteration,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='FIRST_CALL_DIAGNOSTIC_FAILURE_RETAINED')
    result['complete'] = True
    result['payload_sha256'] = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in work.rglob('*') if p.is_file()}
    save()
    print(result['classification'])
    return 0 if result['step_valid'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

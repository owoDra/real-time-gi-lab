#!/usr/bin/env python3
"""Plan130: describe a bounded PT case or manually acquire exactly one native."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

import continuation_quality_provenance as C
from continuation_quality_provenance import R,P
from build_tiled_pixel_pt import quiet

PLAN = R.RESULTS.parent/'experiments/130-manual-continuation-quality-cases.md'
LOCK = R.RESULTS/'026-dynamic-execution-state-lock.json'
VIEW = R.RESULTS/'067-recovery-reference-view.json'
PARTS = R.BASE/'continuation-quality-cases-v1'
PUBLISHED = R.RESULTS/'continuation-quality-cases'
LEGACY = ('013-c7-pt-cohort-pilot.json','024-c8-pt-quality-ladder.json',
          '025-c9-pt-quality-ladder.json','031-c1-b2-pt-quality-ladder.json')


def cases():
    rows = {}
    for cell in ('C1','C7','C8','C9'):
        for vertices in (2,8):
            for spp in C.BUDGETS:
                rows[f'static-{cell}-B{vertices}-n{spp}'] = (cell,vertices,spp,False)
    for cell in sorted(C.DYNAMIC,key=lambda c:int(c[1:])):
        for vertices,spp in ((2,256),(8,1024)):
            rows[f'dynamic-{cell}-B{vertices}-n{spp}'] = (cell,vertices,spp,True)
    return rows


def describe(name):
    cell,vertices,spp,dynamic = cases()[name]
    lock = C.read(LOCK)
    view = C.read(VIEW)
    spec = lock['cells'][cell]
    part = PARTS/name
    command = ['bash',str(R.ROOT/'scripts/run_with_vulkan.sh'),
        str(R.BUILD/'phos-n010-continuation-pixel-pt'),'--state',
        str((R.ROOT/spec['source_directory' if dynamic else 'state_directory']).resolve())]
    if dynamic:
        command += ['--target-state',str((R.ROOT/spec['state_directory']).resolve())]
    command += ['--out',str(part/'capture'),'--family','pixel-pt','--spp',str(spp),
        '--vertices',str(vertices),'--seed','305419896','--frames','5' if dynamic else '1',
        '--tile-pixels','4096','--sample-chunk','16','--pause-us','2000']
    cells = ([('C1' if cell in {'C2','C3','C4','C5','C6'} else 'C7'),cell]
             if dynamic else [cell])
    refs = []
    for ref_cell in cells:
        directory = Path(view['work'])/f'{ref_cell}_T_B{vertices}'
        qpath = directory/'qualification.json'
        q = C.read(qpath) if qpath.is_file() else None
        refs.append(dict(cell=ref_cell,transport=f'T_B{vertices}',directory=str(directory),
            classification=q['classification'] if q else 'MISSING',
            qualification_sha256=hashlib.sha256(qpath.read_bytes()).hexdigest() if q else None,
            metadata_only=True,physical_proof_replayed=False))
    retained = (402 if cell=='C1' else 403) if not dynamic and cell in ('C1','C7') and vertices==8 and spp==1024 else None
    return dict(case=name,cell=cell,vertices=vertices,spp=spp,dynamic=dynamic,
        frames=5 if dynamic else 1,command=command,part=str(part),
        result=str(PUBLISHED/(name+'.json')),references=refs,
        retained_capture=retained,native_run_permitted_by_scope=retained is None,
        native_executed=False,reference_view=VIEW.name,
        coverage_classification='COMMAND_DESCRIPTION_NOT_EXECUTION_OR_EVIDENCE_ADMISSION')


def references_before_launch(description):
    lock = C.read(LOCK)
    view = C.read(VIEW)
    C.require(set(lock['cells']) == {f'C{i}' for i in range(1,13)}
        and len(view['rows']) == 24 and {r['name'] for r in view['rows']} ==
        {f'C{i}_T_B{v}' for i in range(1,13) for v in (2,8)}, 'full026/067 map required')
    physical = P.physical_proof(R.INPUTS)
    R.checked(P.Q.BINARY,physical['binary_sha256'])
    R.checked(P.Q.NET,physical['sobol_table_sha256'])
    for ref in description['references']:
        entry = next(r for r in view['rows'] if r['name']==f"{ref['cell']}_T_B{description['vertices']}")
        directory = Path(ref['directory'])
        C.require(directory.is_symlink() and str(directory.resolve()) == entry['target'],
                  'fixed reference scheduling target changed')
        P.verify_reference(directory,ref['cell'],description['vertices'],lock['cells'][ref['cell']],R.INPUTS)
    return Path(view['work'])


def identity_environment():
    env = dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        kernel=os.uname().release,opengl_driver_root=str(Path('/run/opengl-driver').resolve()),
        variables={k:os.environ.get(k) for k in ('VK_ICD_FILENAMES','VK_DRIVER_FILES',
            'AMD_VULKAN_ICD','RADV_PERFTEST','RADV_DEBUG')},drm_devices={})
    for device in Path('/sys/class/drm').glob('renderD*/device'):
        env['drm_devices'][str(device)] = dict(pci=str(device.resolve()),
            **{k:(device/k).read_text().strip() for k in ('vendor','device','revision')})
    C.require(any(d['vendor']=='0x1002' for d in env['drm_devices'].values()), 'AMD render device required')
    return env


def native_payloads(part):
    files = [p for p in (part/'capture').rglob('*') if p.is_file()]
    files += [part/name for name in ('native.resources.json','native.stdout','native.stderr')
              if (part/name).is_file()]
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def acquire(description):
    C.require(description['retained_capture'] is None, 'reuse retained402/403 read-only; no duplicate capture')
    quiet()
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),Path(C.__file__).resolve(),PLAN):
        C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))])
                  == R.checked(path), 'commit exact driver/component/recipe before native acquisition')
    part,output = Path(description['part']),Path(description['result'])
    C.require(not part.exists() and not output.exists(), 'existing case/partials/result; no overwrite/retry')
    R.inputs('C7')
    signal.alarm(180)
    references = references_before_launch(description)
    C.require(shutil.disk_usage(R.BASE).free >= 2*1024**3, '2GiB free disk operational guard')
    for module in tuple(sys.modules.values()):
        filename = getattr(module,'__file__',None)
        if filename and Path(filename).resolve().is_relative_to(R.ROOT/'scripts/research'):
            R.checked(filename)
    quiet()
    R.unchanged()
    signal.alarm(0)
    environment = identity_environment()
    part.mkdir(parents=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    command = description['command']
    record = dict(schema='n010-continuation-quality-part/1',cell=description['cell'],
        case=description['case'],complete=False,execution_evidence_valid=False,
        quality_evidence_valid=False,all_pass=False,accepted_timing=False,reference_admission=False,
        gpu_run=True,source_commit=commit,input_sha256=dict(R.INPUTS),environment=environment,
        command=command,classification='SINGLE_NATIVE_CASE_IN_PROGRESS',
        tests='NOT_RUN; one manually selected scientific quality/history acquisition only')

    def save():
        data = json.dumps(record,indent=2,allow_nan=False)+'\n'
        (part/'record.json').write_text(data)
        output.write_text(data)

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(120,120))
        resource.setrlimit(resource.RLIMIT_AS,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
        (part/'native.resources.json').write_text(json.dumps(dict(pid=os.getpid(),pgid=os.getpgrp(),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
            elapsed_limit_seconds=180,command=command))+'\n')

    save()
    native = None
    try:
        quiet()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        started = time.monotonic()
        with (part/'native.stdout').open('wb') as out,(part/'native.stderr').open('wb') as err:
            native = subprocess.Popen(command,cwd=R.ROOT,stdout=out,stderr=err,
                                      start_new_session=True,preexec_fn=limits)
            record['pid'] = native.pid
            record['native_start_ticks'] = int(Path(f'/proc/{native.pid}/stat').read_text().rsplit(')',1)[1].split()[19])
            save()
            try:
                code = native.wait(timeout=180)
            except subprocess.TimeoutExpired:
                try:
                    actual = Path(f'/proc/{native.pid}/stat').read_text().rsplit(')',1)[1].split()
                    C.require(int(actual[19]) == record['native_start_ticks'], 'PID reuse; refuse group termination')
                    os.killpg(native.pid,signal.SIGKILL)
                except (FileNotFoundError,ProcessLookupError):
                    pass
                native.wait(timeout=5)
                code = 'TIMEOUT_PARTIALS_RETAINED'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        record.update(native_returncode=code,elapsed_seconds=time.monotonic()-started,
            child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            child_peak_rss_kib=after.ru_maxrss,complete=True,payload_sha256=native_payloads(part),
            classification='NATIVE_TERMINAL_PROOF_PENDING')
        save()
        C.require(code == 0, 'native failed/timed out; retain partials, no next case')
        # Vulkan native mappings stay unlimited. Bound only this now-CPU-only
        # proof stage after the single child has terminated; no following child.
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
        signal.alarm(180)
        proof = C.verify_capture(output,LOCK,description['cell'],description['vertices'],description['spp'],
            dynamic=description['dynamic'],references=references,score_work=part/'quality')
        record.update(execution_evidence_valid=True,quality_evidence_valid=True,validation=proof,
            quality_payload_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((part/'quality').rglob('*')) if p.is_file()},
            # The outer record is finalized below. A final consumer hashes it
            # externally and replays it; never save a stale self-referential
            # digest of its earlier PROOF_PENDING serialization as an input.
            proof_input_sha256={p:h for p,h in R.INPUTS.items()
                if p not in {str(output.resolve()),str((part/'record.json').resolve())}},
            classification='VALID_SINGLE_CASE_QUALITY_RESULTS_RETAINED')
    except (OSError,ValueError,KeyError,IndexError,subprocess.SubprocessError) as error:
        if native is not None and native.poll() is None:
            actual = Path(f'/proc/{native.pid}/stat').read_text().rsplit(')',1)[1].split()
            C.require(int(actual[19]) == record['native_start_ticks'], 'PID reuse; refuse group termination')
            os.killpg(native.pid,signal.SIGKILL)
            native.wait(timeout=5)
        record.update(complete=True,failure=str(error),payload_sha256=native_payloads(part),
                      classification='CASE_FAILURE_PARTIALS_RETAINED_NO_NEXT_CASE')
    save()
    signal.alarm(0)
    print(record['classification'])
    return 0 if record['quality_evidence_valid'] else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    modes = ap.add_mutually_exclusive_group(required=True)
    modes.add_argument('--describe',choices=cases())
    modes.add_argument('--run',choices=cases())
    modes.add_argument('--inventory',action='store_true')
    args = ap.parse_args()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:
        os.nice(15-priority)
    C.require(all(os.environ.get(k)=='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')),
              'one numerical thread required before NumPy import')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    def deadline(signum,frame):
        raise TimeoutError('registered180s CPU-only proof/preflight deadline')
    signal.signal(signal.SIGALRM,deadline)
    if args.inventory:
        for path in (Path(__file__).resolve(),Path(C.__file__).resolve(),PLAN):
            R.checked(path)
        legacy = {}
        for name in LEGACY:
            path = R.RESULTS/name
            data = C.read(path)
            legacy[name] = dict(complete=data['complete'],cell=data['cell'],
                rows=[dict(vertices=r['vertices'],spp=r['spp']) for r in data['rows']],
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                metadata_only=True,raw_proof_replayed=False)
        print(json.dumps(dict(schema='n010-manual-continuation-quality-description/1',
            source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            native_executed=False,compiler_executed=False,all_pass=False,
            cases=[describe(name) for name in cases()],legacy_ladder_metadata=legacy,
            input_sha256=R.INPUTS,tests='NOT_RUN; metadata description only'),indent=2))
        return 0
    description = describe(args.run or args.describe)
    if args.describe:
        print(json.dumps(description,indent=2))
        return 0
    return acquire(description)


if __name__ == '__main__':
    raise SystemExit(main())

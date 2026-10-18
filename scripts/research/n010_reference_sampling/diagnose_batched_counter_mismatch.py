#!/usr/bin/env python3
"""Plan116 post-hoc CPU-only count localization, never GPU/reference admission."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import time

import cover_wide8_original_controls as C
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

PLAN=D.RESULTS.parent/'experiments/116-posthoc-batched-counter-localization.md'
WORK=D.OUT/'posthoc-batched-counter-localization-v1'


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--step',choices=('build','scan'),required=True);step=ap.parse_args().step
    output=D.RESULTS/f'{375 if step=="build" else 376}-posthoc-batched-counter-{step}.json';work=WORK/step
    if output.exists() or work.exists():raise ValueError('refuse existing diagnostic step; no retry')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    for p in (Path(__file__).resolve(),PLAN,Path(C.__file__),Path(D.__file__),D.HERE/'run_primary_direction_sequence.py'):D.checked(p)
    original=C.pinned_result('254');cpu=C.pinned_result('371');failed=C.pinned_result('372')
    if not original['all_pass'] or not cpu['all_pass'] or failed['all_pass'] or failed['failure']!='full-frame independent scored counts differ':raise ValueError('required terminal115 outcome absent')
    for proof in (cpu,failed):
        for p,h in proof['input_sha256'].items():D.checked(Path(p),h)
    base=D.OUT/'wide8-cpu-bvh-v1';header=base/'n010_rqmc_oracle.hpp';source=D.HERE/'batched_counter_scan.cpp'
    D.checked(header,original['payload_sha256'][str(header)]);D.checked(source)
    data=D.OUT/'batched-full-frame-hybrid-pilot-v1';binary=WORK/'build/n010_counter_scan'
    work.mkdir(parents=True)
    if step=='build':
        (work/header.name).write_bytes(header.read_bytes());(work/'scan.cpp').write_bytes(source.read_bytes())
        command=['c++','-mavx512f','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread','-I',str(D.ROOT/'src/research/n008_hdr_oracle'),str(work/'scan.cpp'),'-o',str(binary)]
    else:
        build=C.pinned_result('375')
        if not build['all_pass']:raise ValueError('successful frozen diagnostic compiler required')
        original_command=cpu['attempts'][0]['command'];net=Path(original_command[original_command.index('--net')+1]);scene=Path(original_command[original_command.index('--scene')+1])
        gpu=data/'gpu/gpu/gpu.stats';baseline=data/'cpu/o.s0.f64'
        D.checked(gpu,failed['payload_sha256'][str(gpu)]);D.checked(baseline,cpu['payload_sha256'][str(baseline)])
        command=[str(binary),str(net),str(scene),str(gpu),str(baseline),str(work/'scan.json')]
    result=dict(schema='n010-posthoc-batched-counter-localization/1',step=step,complete=False,all_pass=False,diagnostic_valid=False,
        classification='POST_HOC_CPU_DIAGNOSTIC_ACQUIRING',gpu_run=False,reference_admission=False,accepted_timing=False,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),input_sha256=D.INPUTS,attempts=[],tests='NOT_RUN; post-hoc scientific CPU diagnosis only')
    def save():output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    receipt=work/'native.resources.json'
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(120,)*2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
    row=dict(command=command,resource_receipt=str(receipt),terminal=False,cpu_limit=120,elapsed_limit=180);result['attempts'].append(row);save()
    try:
        started=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            child=subprocess.run(command,capture_output=True,timeout=180,preexec_fn=limits);stdout,stderr=child.stdout,child.stderr;row.update(terminal=True,returncode=child.returncode)
        except subprocess.TimeoutExpired as error:
            stdout,stderr=error.stdout or b'',error.stderr or b'';row.update(terminal=True,returncode='NOT_EXPOSED_BY_TIMEOUTEXPIRED',failure='ELAPSED_GUARD_NO_RETRY')
        after=resource.getrusage(resource.RUSAGE_CHILDREN);row.update(elapsed_seconds=time.monotonic()-started,child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
        (work/'native.stdout').write_bytes(stdout);(work/'native.stderr').write_bytes(stderr);save();actual=json.loads(D.checked(receipt))
        if row['returncode']!=0 or actual['cpu']!=[120]*2 or actual['address_space']!=[4*1024**3]*2 or actual['affinity']!=[31] or actual['nice']!=15:raise ValueError('diagnostic native/resource failure')
        if step=='scan':
            scan=json.loads(D.checked(work/'scan.json'));meta=json.loads((data/'cpu/native.stdout').read_text())['runs'][0];gpu_meta=json.loads((data/'gpu/gpu/gpu.json').read_text())
            keys=('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')
            if (not scan['complete'] or not scan['all_cpu_mean_moment_bits_exact'] or scan['pixel_count']!=57600
                    or scan['cpu_counters']!=[meta[k] for k in keys] or scan['gpu_counters']!=[gpu_meta[k] for k in keys]
                    or scan['cpu_audit']!={k:meta['all_split'][k] for k in scan['cpu_audit']}
                    or scan['differing_pixels']!=len(scan['rows']) or not scan['rows']):raise ValueError('diagnostic reconstruction/global identity failed')
            result.update(differing_pixels=scan['differing_pixels'],differing_pixel_indices=[r['pixel'] for r in scan['rows']],cpu_counters=scan['cpu_counters'],gpu_counters=scan['gpu_counters'])
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(diagnostic_valid=True,all_pass=step=='build',classification='POST_HOC_CPU_BUILD_PASS' if step=='build' else 'POST_HOC_CPU_SCAN_COMPLETE_GPU_COUNT_FAILURE_RETAINED')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='POST_HOC_CPU_DIAGNOSTIC_FAILURE_RETAINED')
    result['complete']=True;result['payload_sha256']={str(p):C.sha(p) for p in work.rglob('*') if p.is_file()};save()
    print(json.dumps({k:result.get(k) for k in ('complete','all_pass','diagnostic_valid','classification','failure','differing_pixel_indices')}));raise SystemExit(0 if result['diagnostic_valid'] else 2)


if __name__=='__main__':main()

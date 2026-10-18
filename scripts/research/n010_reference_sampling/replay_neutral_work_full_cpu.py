#!/usr/bin/env python3
"""Plan135: post-hoc complete CPU integer witness for all retained185 scratches."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

import numpy as np
from build_continuation_pixel_pt import checked,unchanged,INPUTS,ROOT,RESULTS

PLAN=RESULTS.parent/'experiments/135-bounded-history-known-work.md'
OUTPUT=RESULTS/'429-retained-neutral-work-full-cpu-replay.json'


def main():
    os.sched_setaffinity(0,{31})
    priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    if any(os.environ.get(k)!='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):
        raise ValueError('one numerical thread required')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
    signal.alarm(180);start,cpu=time.monotonic(),time.process_time()
    if OUTPUT.exists():raise ValueError('refuse existing429; no overwrite/retry')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))])!=checked(path):
            raise ValueError('commit exact recipe/driver before replay')
    shader=ROOT/'shaders/research/n010_comparison_readiness/n010_neutral_work.comp.glsl'
    revised=ROOT/'shaders/research/n010_comparison_readiness/n010_history_neutral_work.comp.glsl'
    for path in (shader,revised,ROOT/'src/research/n010_comparison_readiness/neutral_work_verify.cpp'):
        checked(path)
    old=json.loads(checked(RESULTS/'185-deferred-image-calibration-sizing.json'))
    expected={'C1-'+r for r in ('hwrt','software','pt-B2','pt-B8','dense-rc')}
    expected|={'C7-'+r for r in ('hwrt','software','pt-B2','pt-B8','dense-rc')}
    expected|={c+'-'+r for c in ('C6','C12') for r in ('hwrt','pt-B2','pt-B8')}
    if not old['complete'] or not old['all_pass'] or len(old['rows'])!=16 or {r['boundary']['id'] for r in old['rows']}!=expected:
        raise ValueError('complete original sixteen sizing boundaries required')
    words=np.arange(16384,dtype='<u4')^np.uint32(0x4e303130)
    temporary=np.empty_like(words)
    golden={0:hashlib.sha256(words.tobytes()).hexdigest()}
    for iteration in range(1,262145):
        np.multiply(words,np.uint32(1664525),out=words)
        np.add(words,np.uint32(1013904223),out=words)
        np.right_shift(words,np.uint32(13),out=temporary)
        np.bitwise_xor(words,temporary,out=words)
        if iteration in (65536,262144):golden[iteration]=hashlib.sha256(words.tobytes()).hexdigest()
    rows=[]
    for boundary in old['rows']:
        block=boundary['evidence'];command=block['command']
        directory=Path(command[command.index('--out')+1])
        if not directory.is_absolute():directory=ROOT/directory
        samples=block['samples']
        if len(samples)!=9 or sorted(s['dose'] for s in samples)!=[0]*3+[65536]*3+[262144]*3:
            raise ValueError('all nine original doses required')
        for index,sample in enumerate(samples):
            relative=f'frames/{index}/neutral-work.bin'
            # RC frames have an extra gpu directory; PT/dense do not.
            if relative not in block['payload_sha256']:relative=f'frames/{index}/gpu/neutral-work.bin'
            path=directory/relative
            raw=checked(path,block['payload_sha256'][relative])
            if len(raw)!=65536 or hashlib.sha256(raw).hexdigest()!=golden[sample['dose']]:
                raise ValueError('complete16384-lane CPU scratch mismatch')
            rows.append(dict(boundary=boundary['boundary']['id'],sample=index,dose=sample['dose'],
                lanes=16384,path=str(path),sha256=hashlib.sha256(raw).hexdigest(),all_words_cpu_exact=True))
    if len(rows)!=144:raise ValueError('complete retained scratch coverage differs')
    unchanged();elapsed,used=time.monotonic()-start,time.process_time()-cpu
    if elapsed>=180 or used>=120:raise ValueError('registered resource limit exceeded')
    result=dict(schema='n010-retained-neutral-work-full-cpu-replay/1',complete=True,posthoc=True,
        all144_scratch_images_all16384_words_cpu_exact=True,all_pass=False,accepted_timing=False,
        reference_admission=False,gpu_run=False,new_shader_runtime_verified=False,source_commit=commit,
        classification='ALL_RETAINED_INTEGER_SCRATCH_BYTES_CPU_EXACT_NO_TIMING_ADMISSION',
        unique_dose_sha256=golden,rows=rows,input_sha256=INPUTS,
        execution=dict(elapsed_seconds=elapsed,cpu_seconds=used,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),numerical_threads=1,
            cpu_limit_seconds=120,elapsed_limit_seconds=180,address_space_limit_bytes=2*1024**3),
        tests='NOT_RUN; post-hoc archived integer-work scientific replay, not new-shader/runtime validation')
    with OUTPUT.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    signal.alarm(0);print(result['classification'])


if __name__=='__main__':main()

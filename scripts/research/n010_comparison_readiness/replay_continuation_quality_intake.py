#!/usr/bin/env python3
"""Plan129: CPU-only scientific replay of real retained402/403; no new capture."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import numpy as np
import continuation_quality_provenance as C
from continuation_quality_provenance import R

PLAN = R.RESULTS.parent/'experiments/129-continuation-quality-proof-intake.md'
OUTPUT = R.RESULTS/'409-continuation-quality-intake-replay.json'
WORK = R.BASE/'continuation-quality-proof-intake-v1'


def main():
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:
        os.nice(15-priority)
    C.require(all(os.environ.get(k) == '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')),
              'one numerical thread required')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    signal.alarm(180)
    start,cpu = time.monotonic(),time.process_time()
    C.require(not OUTPUT.exists() and not WORK.exists(), 'existing result/work; no overwrite/retry')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),Path(C.__file__).resolve(),PLAN):
        C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))])
                  == R.checked(path), 'commit exact driver/component/recipe before replay')
    WORK.mkdir()
    lock = R.RESULTS/'026-dynamic-execution-state-lock.json'
    references = R.BASE/'references-v1'
    old = C.read(R.RESULTS/'404-continuation-pixel-pt-numerical.json')
    quality407 = C.read(R.RESULTS/'407-retained-continuation-c7-quality.json')
    for name,digest in quality407['payload_sha256'].items():
        R.checked(name,digest)
    # Ineligible C1 is execution only; this cannot contribute a quality row.
    rows = {}
    for cell in ('C1','C7'):
        baseline = R.retained_part(cell)
        C.require(baseline == old['rows'][cell], 'old404 replay differs from retained raw capture')
        row = C.verify_capture(R.part_result(cell),lock,cell,8,1024,
            references=references if cell=='C7' else None,
            score_work=WORK/'C7-quality' if cell=='C7' else None)
        frame = row['frames'][0]
        pairs = [(frame['active_gpu_us'],baseline['active_gpu_us']),
            (frame['image_envelope_gpu_us'],baseline['image_envelope_gpu_us']),
            (frame['max_dispatch_gpu_us'],baseline['max_dispatch_gpu_us']),
            (frame['cpu_frame_wall_us'],baseline['cpu_frame_wall_us']),
            (frame['readback_wall_us'],baseline['readback_wall_us']),
            (row['native_elapsed_seconds'],baseline['native_elapsed_seconds'])]
        C.require(all(R.close(a,b) for a,b in pairs)
            and frame['dispatch_count'] == baseline['dispatch_count']
            and frame['pixel_samples'] == baseline['pixel_samples']
            and frame['final_state_sha256'] == baseline['final_rng_and_sum_state_sha256']
            and row['persistent_sample_state_bytes'] == baseline['persistent_sample_state_bytes']
            and row['owned_peak_bytes'] == baseline['owned_peak_bytes'], 'generic raw cost/state replay differs')
        if cell=='C7':
            C.require(frame['quality']['components'] == quality407['score']['components']
                and frame['quality']['pilot_quality_target'] == quality407['score']['pilot_quality_target']
                and frame['quality']['capture_payload_sha256'] == quality407['score']['capture_payload_sha256'],
                'unchanged full-image score differs from407')
            for component in ('direct','indirect','total'):
                original = R.BASE/f'retained-continuation-c7-quality-v1/quality.{component}.error.npy'
                current = WORK/f'C7-quality/frame0.{component}.error.npy'
                C.require(R.checked(original) == current.read_bytes(), 'full error-map bytes differ from407')
        else:
            row['quality_classification'] = 'NOT_SCORED_REFERENCE_INELIGIBLE'
        rows[cell] = row
    for module in tuple(sys.modules.values()):
        filename = getattr(module,'__file__',None)
        if filename and Path(filename).resolve().is_relative_to(R.ROOT/'scripts/research'):
            R.checked(filename)
    payloads = {str(path):hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(WORK.rglob('*')) if path.is_file()}
    R.unchanged()
    elapsed,used = time.monotonic()-start,time.process_time()-cpu
    C.require(elapsed < 180 and used < 120, 'registered analysis bound exceeded')
    result = dict(schema='n010-continuation-quality-proof-intake-replay/1',complete=True,
        execution_intake_valid=True,all_pass=False,accepted_timing=False,reference_admission=False,
        gpu_run=False,posthoc=True,source_commit=commit,
        classification='TWO_RETAINED_STATIC_EXECUTIONS_ONE_ELIGIBLE_QUALITY_ROW_REPLAY_VALID',
        rows=rows,input_sha256=R.INPUTS,payload_sha256=payloads,
        execution=dict(pid=os.getpid(),affinity=sorted(os.sched_getaffinity(0)),
            nice=os.getpriority(os.PRIO_PROCESS,0),cpu_limit_seconds=120,elapsed_limit_seconds=180,
            address_space_limit_bytes=2*1024**3,elapsed_seconds=elapsed,cpu_seconds=used,
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            numerical_threads=1,python=sys.version,numpy=np.__version__),
        limitations=['Actual replay scope: static C1/C7 B8/1024 only; C1 unscored.',
            'Other budgets and dynamic 5-frame component paths not runtime verified.',
            'No all-split reference admission, full selected-boundary timing or final auditor completion.',
            'No accepted performance timing or whole N010 readiness determination.'],
        tests='NOT_RUN; read-only retained-data scientific provenance/quality replay only')
    with OUTPUT.open('x') as output:
        output.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    signal.alarm(0)
    print(result['classification'])


if __name__ == '__main__':
    main()

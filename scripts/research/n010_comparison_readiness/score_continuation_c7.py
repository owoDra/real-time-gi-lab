#!/usr/bin/env python3
"""Plan128: CPU-only post-hoc score of the retained403 full C7 image."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts/research/n010_reference_sampling'))
import replay_continuation_pixel_pt as R
import reference_provenance as P
import score_hdr as S
import numpy as np

PLAN = R.RESULTS.parent/'experiments/128-retained-continuation-c7-quality.md'
OUTPUT = R.RESULTS/'407-retained-continuation-c7-quality.json'
WORK = R.BASE/'retained-continuation-c7-quality-v1'


def main():
    os.sched_setaffinity(0, {31})
    priority = os.getpriority(os.PRIO_PROCESS, 0)
    if priority < 15:
        os.nice(15-priority)
    if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')):
        raise ValueError('one numerical thread required before importing NumPy')
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    signal.alarm(180)
    start, cpu_start = time.monotonic(), time.process_time()
    if OUTPUT.exists() or WORK.exists():
        raise ValueError('refuse existing result or work; preserve partials, no retry')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    for path in (Path(__file__).resolve(), PLAN):
        if subprocess.check_output(['git', 'show', commit+':'+str(path.relative_to(ROOT))]) != R.checked(path):
            raise ValueError('commit exact analysis recipe/driver before scoring')
    WORK.mkdir()
    # Replay actual retained capture/owned lifetimes, not saved result flags.
    observed = R.retained_part('C7')
    inputs = R.INPUTS
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename and Path(filename).resolve().is_relative_to(ROOT/'scripts/research'):
            R.checked(filename)
    physical = P.physical_proof(inputs)
    R.checked(P.Q.BINARY, physical['binary_sha256'])
    R.checked(P.Q.NET, physical['sobol_table_sha256'])
    lock = P.read(R.RESULTS/'026-dynamic-execution-state-lock.json', inputs)
    reference = R.BASE/'references-v1/C7_T_B8'
    proof = P.verify_reference(reference, 'C7', 8, lock['cells']['C7'], inputs)
    qualification = P.read(reference/'qualification.json', inputs)
    score_path = WORK/'quality.json'
    capture = R.WORK/'C7/capture'
    score = S.score(capture, qualification, reference, score_path)
    if score['scoring_exclusions'] != 0 or any(
            row['pixels'] != 57600 or row['scoring_exclusions'] != 0
            for row in score['components'].values()):
        raise ValueError('full-image scoring scope differs')
    with score_path.open('x') as output:
        output.write(json.dumps(score, indent=2, allow_nan=False)+'\n')
    payloads = {str(path):hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(WORK.iterdir())}
    R.unchanged()
    elapsed, cpu = time.monotonic()-start, time.process_time()-cpu_start
    if elapsed >= 180 or cpu >= 120:
        raise ValueError('registered resource bound exceeded; no result admission')
    result = dict(schema='n010-retained-continuation-c7-quality/1',
        complete=True, quality_evidence_valid=True, all_pass=False,
        accepted_timing=False, reference_admission=False, gpu_run=False,
        classification='POSTHOC_SINGLE_C7_ROW_QUALITY_'+score['pilot_quality_target'],
        source_commit=commit, posthoc=True, cell='C7', transport='T_B8', spp=1024,
        reference_proof=proof, score=score, descriptive_capture_costs=observed,
        input_sha256=inputs, payload_sha256=payloads,
        execution=dict(pid=os.getpid(),affinity=sorted(os.sched_getaffinity(0)),
            nice=os.getpriority(os.PRIO_PROCESS,0),cpu_limit_seconds=120,
            elapsed_limit_seconds=180,address_space_limit_bytes=2*1024**3,
            elapsed_seconds=elapsed,cpu_seconds=cpu,
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            python=sys.version,numpy=np.__version__,numerical_threads=1),
        limitations=['Existing403 selected before analysis; no new GPU acquisition.',
            'Single C7 row only; C1 B8 reference ineligible; no ladder/corpus completion.',
            'GPU costs descriptive; no paired or calibrated performance inference.',
            'No reference admission or whole N010 readiness determination.'],
        tests='NOT_RUN; retained-payload scientific quality/provenance analysis only')
    with OUTPUT.open('x') as output:
        output.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
    signal.alarm(0)
    print(result['classification'])


if __name__ == '__main__':
    main()

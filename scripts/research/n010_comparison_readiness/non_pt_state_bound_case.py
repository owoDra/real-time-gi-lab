#!/usr/bin/env python3
"""Plan159: exact static counter binding; one native or post-hoc retained replay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import acquire_non_pt_raw_case as A
import non_pt_raw_provenance as N
from non_pt_raw_provenance import C, P, R

PLAN = R.RESULTS.parent/'experiments/159-locked-static-frame-counter-intake.md'
OUTPUT = R.RESULTS/'616-posthoc-c7-hwrt-locked-counter-replay.json'
WORK = R.BASE/'raw-query-c7-hwrt-state-replay-v1'
PIN = '8a48580f97f68ae6bba7958661b6f2384c77dad53a8d65e3f78bfd70df81b5db'
EDITS = (
    ('def state(directory, expected, index, rc):',
     'def state(directory, expected, index, rc, dynamic):'),
    ("(1 if index == 0 else 2)", "(1 if dynamic and index == 0 else 2)"),
    ('state(frame_dir,source if index == 0 else target,index,rc)',
     'state(frame_dir,source if index == 0 else target,index,rc,dynamic)'),
    ('state(directory,target,count-1,rc)', 'state(directory,target,count-1,rc,dynamic)'),
)


def install():
    source = R.checked(Path(N.__file__).resolve(), PIN).decode()
    original = source
    for old,new in EDITS:
        C.require(source.count(old) == 1, 'unique state correction anchor required')
        source = source.replace(old,new,1)
    inverse = source
    for old,new in reversed(EDITS):
        C.require(inverse.count(new) == 1, 'unique inverse anchor required')
        inverse = inverse.replace(new,old,1)
    C.require(inverse == original, 'complete original verifier inverse differs')
    namespace = dict(__file__=N.__file__,__name__='n010_state_bound_raw_provenance')
    exec(compile(source,'<n010-state-bound-raw-provenance>','exec'),namespace)
    N.verify_capture = namespace['verify_capture']
    return dict(original_source_sha256=PIN,whole_source_inverse_exact=True,
        generated_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        substitutions=[dict(old=a,new=b) for a,b in EDITS])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--replay-c7',action='store_true')
    mode.add_argument('--case',choices=A.CASES)
    args = parser.parse_args()
    A.quiet()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    C.require(all(os.environ.get(k) == '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')),
        'one numerical thread required')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve()):
        C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))])
            == R.checked(path), 'commit exact159 plan/source before execution')
    composition = install()
    if args.case:
        sys.argv = [A.__file__,'--case',args.case]
        return A.main()
    C.require(not OUTPUT.exists() and not WORK.exists(), 'fresh post-hoc replay required')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
    signal.alarm(180)
    started,cpu = time.monotonic(),time.process_time()
    failed_path = R.RESULTS/'516-raw-query-static-C7-hwrt-pilot.json'
    failed = C.read(failed_path)
    C.require(failed['complete'] and failed['native_returncode'] == 0
        and failed['failure'] == 'continuation quality proof: RC state differs beyond registered frame-counter progression',
        'exact original516 native/intake failure required')
    for group in ('input_sha256','payload_sha256'):
        for path,digest in failed[group].items():R.checked(path,digest)
    capture = Path(failed['command'][failed['command'].index('--out')+1])
    native = capture.parent/'native-record.json'
    snapshot = C.read(native)
    C.require(snapshot['classification'] == 'FULL_NON_PT_NATIVE_TERMINAL_ANALYSIS_PENDING'
        and snapshot['payload_sha256'] == failed['payload_sha256']
        and snapshot['command'] == failed['command'], 'immutable native snapshot differs')
    view = C.read(R.RESULTS/'160-primary-direction-reference-view.json')
    for vertices in (2,8):
        name = f'C7_T_B{vertices}'
        entry = next(row for row in view['rows'] if row['name'] == name)
        ref = Path(view['work'])/name
        C.require(ref.is_symlink() and str(ref.resolve()) == entry['target'], 'fixed C7 reference view differs')
    result = dict(schema='n010-posthoc-rc-state-bound-replay/1',complete=False,posthoc=True,
        source_commit=commit,composition=composition,input_sha256=R.INPUTS,
        source_capture=str(failed_path),immutable_native_record=str(native),gpu_run=False,
        native_executed=False,execution_evidence_valid=False,quality_evidence_valid=False,
        accepted_timing=False,reference_admission=False,timing_precision='TIMING_INCONCLUSIVE',
        original516_failure_unchanged=True)
    try:
        proof = N.verify_capture(native,'static-C7-hwrt',references=Path(view['work']),score_work=WORK)
        R.unchanged()
        result.update(validation=proof,execution_evidence_valid=True,quality_evidence_valid=True,
            classification='POSTHOC_COMPLETE_FULL_C7_HWRT_RAW_PILOT_NO_SPEED_CLAIM')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='POSTHOC_RC_STATE_BOUND_REPLAY_FAILURE_RETAINED')
    result.update(complete=True,elapsed_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
        payload_sha256={str(p):P.sha(p) for p in WORK.rglob('*') if p.is_file()},
        tests='NOT_RUN; post-hoc CPU full retained native/raw/state/memory/quality replay only')
    A.write(OUTPUT,result,True)
    signal.alarm(0)
    print(json.dumps({k:result.get(k) for k in ('classification','execution_evidence_valid',
        'quality_evidence_valid','failure','elapsed_seconds')},indent=2))
    return 0 if result['quality_evidence_valid'] else 2


if __name__ == '__main__':raise SystemExit(main())

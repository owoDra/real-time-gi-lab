#!/usr/bin/env python3
"""Plan166: one post-hoc CPU full retained non-PT quality replay; no acquisition."""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import state_bound_pilot_provenance as B
from state_bound_pilot_provenance import C,P,R

PLAN=R.RESULTS.parent/'experiments/166-retained-non-pt-quality-replay.md'
CASES={'static-C7-software':(714,517,2), 'dynamic-C12-hwrt':(715,519,10)}
BASE=R.BASE/'retained-non-pt-quality-v1'


def write(path,value,fresh=False):
    with path.open('x' if fresh else 'w') as stream:
        stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=CASES,required=True);args=parser.parse_args()
    B.W.A.quiet()
    os.sched_setaffinity(0,{31});priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    C.require(os.getpriority(os.PRIO_PROCESS,0)==15 and all(os.environ.get(k)=='1'
        for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')),'exact nice15/BLAS1 required')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
    signal.alarm(180)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),B.PLAN,Path(B.__file__).resolve(),B.W.PLAN,Path(B.W.__file__).resolve()):
        C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))])==R.checked(path),
            'commit exact166/160/159 recipes/sources first')
    number,original_number,count=CASES[args.case]
    output=R.RESULTS/f'{number}-posthoc-{args.case}-full-quality-replay.json'
    work=BASE/args.case
    C.require(not output.exists() and not work.exists(),'fresh replay output/work required; no retry')
    row=next(row for row in B.inventory() if row['id']==args.case)
    capture=Path(row['path']);record=C.read(capture)
    C.require(capture.name.startswith(str(original_number)+'-') and record['complete']
        and record['native_returncode']==0 and record['boundary_id']==args.case
        and record['classification']=='FULL_NON_PT_RAW_EXECUTION_VALID_QUALITY_REPLAY_PENDING',
        'exact retained pending native required')
    capture_digest=P.sha(capture)
    view=C.read(R.RESULTS/'160-primary-direction-reference-view.json')
    cells=('C7',) if count==2 else ('C7','C12')
    for cell in cells:
        for vertices in (2,8):
            name=f'{cell}_T_B{vertices}'
            entry=next(row for row in view['rows'] if row['name']==name)
            reference=Path(view['work'])/name
            C.require(reference.is_symlink() and str(reference.resolve())==entry['target'],
                'frozen160 reference view differs')
    started,cpu=time.monotonic(),time.process_time()
    result=dict(schema='n010-retained-non-pt-quality-replay/1',complete=False,posthoc=True,
        source_commit=commit,boundary_id=args.case,source_capture=str(capture),
        source_capture_sha256_before=capture_digest,input_sha256=R.INPUTS,gpu_run=False,
        native_executed=False,execution_evidence_valid=False,quality_evidence_valid=False,
        accepted_timing=False,timing_precision='TIMING_INCONCLUSIVE',reference_admission=False,
        classification='POSTHOC_FULL_NON_PT_QUALITY_REPLAY_ACQUIRING',
        analysis_resources=dict(pid=os.getpid(),start_ticks=B.W.A.start_ticks(os.getpid()),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=[sys.executable,*sys.argv],
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            elapsed_limit_seconds=180),
        tests='NOT_RUN; post-hoc full retained raw/state/memory/quality CPU replay only')
    write(output,result,True)
    try:
        proof=B.non_pt(row,Path(view['work']),work)
        C.require(proof['execution_evidence_valid'] and proof['quality_evidence_valid']
            and len(proof['scores'])==count,'complete full-score evidence required')
        expected={(frame,vertices) for frame in range(1 if count==2 else 5) for vertices in (2,8)}
        C.require({(s['frame_index'],s['vertices']) for s in proof['scores']}==expected,
            'missing frame/transport score')
        R.unchanged()
        C.require(P.sha(capture)==capture_digest,'original acquisition was rewritten')
        result.update(validation=proof,execution_evidence_valid=True,quality_evidence_valid=True,
            source_capture_unchanged=True,classification='POSTHOC_FULL_NON_PT_QUALITY_REPLAY_COMPLETE_NO_SPEED_CLAIM')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='POSTHOC_NON_PT_QUALITY_REPLAY_FAILURE_PARTIALS_RETAINED')
    result.update(complete=True,cpu_seconds=time.process_time()-cpu,elapsed_seconds=time.monotonic()-started,
        payload_sha256={str(p):P.sha(p) for p in work.rglob('*') if p.is_file()})
    write(output,result);signal.alarm(0)
    print(json.dumps({k:result.get(k) for k in ('classification','boundary_id','quality_evidence_valid',
        'elapsed_seconds','failure')},indent=2))
    return 0 if result['quality_evidence_valid'] else 2


if __name__=='__main__':raise SystemExit(main())

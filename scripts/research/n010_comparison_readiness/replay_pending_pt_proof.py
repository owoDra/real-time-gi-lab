#!/usr/bin/env python3
"""Plan175A: CPU-only replay of a retained PT capture whose proof stage did not finish."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess

import acquire_continuation_quality_case as B
import acquire_selected_pt_quality_case as S132

OUT = B.R.RESULTS/'continuation-quality-proof-replays'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case',required=True)
    a = ap.parse_args()
    os.sched_setaffinity(0,{27})
    if os.getpriority(os.PRIO_PROCESS,0) < 15:os.nice(15-os.getpriority(os.PRIO_PROCESS,0))
    B.C.require(all(os.environ.get(k)=='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')),'one numerical thread')
    resource.setrlimit(resource.RLIMIT_CPU,(1800,1800))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),B.R.RESULTS.parent/'experiments/175-r1-reference-integration.md'):
        B.C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(B.R.ROOT))])
                    == path.read_bytes(),'commit exact replay before use')
    B.cases = S132.selected_cases
    description = B.describe(a.case)
    original = Path(description['result'])
    record = json.loads(original.read_text())
    B.C.require(record['classification']=='NATIVE_TERMINAL_PROOF_PENDING' and record['native_returncode']==0,
                'replay only a retained terminal native whose proof is pending')
    part = Path(description['part'])
    payload = B.native_payloads(part)
    B.C.require(all(payload.get(k)==v for k,v in record['payload_sha256'].items()),'retained capture bytes changed')
    output = OUT/(a.case+'.json');score_work = part.parent/(a.case+'.proof-replay')/'quality'
    B.C.require(not output.exists() and not score_work.exists(),'refuse existing replay')
    OUT.mkdir(parents=True,exist_ok=True);score_work.mkdir(parents=True)
    result = dict(schema='n010-pt-proof-replay/1',case=a.case,source_commit=commit,
        original_record_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        original_classification=record['classification'],native_executed=False,gpu_run=False,
        reason='130 runner RLIMIT_CPU120s ended proof stage after native returncode0',complete=False,
        tests='NOT_RUN')
    try:
        references = B.references_before_launch(description)
        proof = B.C.verify_capture(original,B.LOCK,description['cell'],description['vertices'],description['spp'],
            dynamic=description['dynamic'],references=references,score_work=score_work,
            reference_verifier=B.H.verify_reference)
        result.update(complete=True,execution_evidence_valid=True,quality_evidence_valid=True,validation=proof,
            classification='VALID_REPLAYED_QUALITY_RESULTS_RETAINED',
            quality_payload_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sorted(score_work.rglob('*')) if p.is_file()})
    except (OSError,ValueError,KeyError,IndexError) as error:
        result.update(complete=True,failure=str(error),classification='PROOF_REPLAY_FAILED_RETAINED')
    usage = resource.getrusage(resource.RUSAGE_SELF)
    result['cpu_seconds_diagnostic'] = usage.ru_utime+usage.ru_stime
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(result['classification'])


if __name__ == '__main__':
    main()

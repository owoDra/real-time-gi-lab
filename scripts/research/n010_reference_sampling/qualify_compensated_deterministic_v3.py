#!/usr/bin/env python3
"""Plan142: prepare only the cohort directory, then exact141 one-case intake."""
import json
import os
from pathlib import Path
import subprocess

import diagnose_original_sphere_pixel as D
import qualify_compensated_deterministic_v2 as V

PLAN=D.RESULTS.parent/'experiments/142-compensated-control-directory-preparation.md'


def case_output(name):
    return D.RESULTS/f'{473+V.NAMES.index(name):03d}-compensated-full-{name.lower()}.json'


def main():
    os.sched_setaffinity(0,{31})
    priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    D.quiet()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN,Path(V.__file__).resolve(),V.PLAN):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))])!=D.checked(path):
            raise ValueError('commit exact directory wrapper/plan before use')
    failed=json.loads(D.checked(D.RESULTS/'463-compensated-full-a2.json'))
    if failed.get('payload_sha256')!={} or not failed.get('failure','').startswith('[Errno 2] No such file or directory:'):
        raise ValueError('exact pre-native463 directory failure required')
    V.PLAN=PLAN
    V.WORK=D.OUT/'compensated-full-control-intake-v3'
    V.case_output=case_output
    V.WORK.mkdir(parents=True,exist_ok=True)
    return V.main()


if __name__=='__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Plan132: immutable130 single-case runner with prospectively selected PT spp."""
import hashlib
from pathlib import Path
import subprocess

import acquire_continuation_quality_case as B

PARENT_SHA = '8badfd0c638a4f75aa016ae97165fe75d040222f3f30ceae9da9298d609bcc73'
SELECTION_SHA = '55d5b79db48a333372340f00fb2bbe2f907e605883f9bd3e4b04447c94b022c9'
PLAN = B.R.RESULTS.parent/'experiments/132-selected-pt-quality-budget.md'
ORIGINAL_CASES = B.cases


def selected_cases():
    rows = {name:spec for name,spec in ORIGINAL_CASES().items() if not spec[3]}
    for cell in sorted(B.C.DYNAMIC,key=lambda c:int(c[1:])):
        for vertices in (2,8):
            rows[f'dynamic-{cell}-B{vertices}-n1024'] = (cell,vertices,1024,True)
    return rows


def main():
    raw = B.R.checked(B.__file__)
    B.C.require(hashlib.sha256(raw).hexdigest()==PARENT_SHA, 'frozen130 single-case parent changed')
    B.R.checked(B.R.RESULTS/'415-retained-pt-ladder-proof-replay.json',SELECTION_SHA)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN):
        B.C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(B.R.ROOT))])
                    == B.R.checked(path), 'commit exact selected-budget recipe/adapter before use')
    B.cases = selected_cases
    B.PLAN = PLAN
    return B.main()


if __name__=='__main__':
    raise SystemExit(main())

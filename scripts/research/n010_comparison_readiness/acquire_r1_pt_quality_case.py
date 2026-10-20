#!/usr/bin/env python3
"""Plan175D: frozen132/130 single-case PT runner with the747 R1 full-corpus reference view."""
import hashlib
from pathlib import Path
import subprocess
import types

import acquire_continuation_quality_case as B
import acquire_selected_pt_quality_case as S132
import r1_reference_provenance as X

PLAN = B.R.RESULTS.parent/'experiments/175-r1-reference-integration.md'
VIEW = B.R.RESULTS/'747-full-corpus-r1-reference-view.json'
PUBLISHED = B.R.RESULTS/'r1-quality-cases'
PARTS = B.R.BASE/'r1-quality-cases-v1'


def main():
    raw = B.R.checked(B.__file__)
    B.C.require(hashlib.sha256(raw).hexdigest()==S132.PARENT_SHA,'frozen130 single-case parent changed')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN,Path(X.__file__).resolve(),Path(S132.__file__).resolve()):
        B.C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(B.R.ROOT))])
                    == B.R.checked(path),'commit exact R1 adapter/recipe before use')
    B.C.require(VIEW.is_file(),'747 full-corpus R1 view required')
    B.cases = S132.selected_cases
    B.PLAN = PLAN
    B.VIEW = VIEW
    B.PARTS = PARTS
    B.PUBLISHED = PUBLISHED
    # Replace only the reference verifier and the score gate (175B); everything else is frozen130.
    B.H = types.SimpleNamespace(verify_reference=X.verify_reference)
    B.C.S = types.SimpleNamespace(score=X.score)
    return B.main()


if __name__=='__main__':
    raise SystemExit(main())

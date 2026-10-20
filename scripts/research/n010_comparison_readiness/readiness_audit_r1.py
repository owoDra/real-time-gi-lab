#!/usr/bin/env python3
"""Plan176: unchanged160/154 full readiness audit with declared R1 reference dispatch."""
from pathlib import Path
import subprocess

import r1_reference_provenance as X
import hybrid_reference_provenance as H
import score_hdr
import readiness_preflight_selected_pilots as A
import readiness_preflight_state_bound as W160
from state_bound_pilot_provenance import C, R

PLAN = R.RESULTS.parent/'experiments/176-r1-pilots-and-final-audit.md'
OUTPUT = R.RESULTS/'751-r1-full-readiness-audit.json'
DESCRIPTION = R.RESULTS/'751-r1-full-readiness-description.json'
WORK = R.BASE/'r1-full-readiness-v1'


def main():
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN,Path(X.__file__).resolve()):
        C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))])
            == R.checked(path),'commit exact176 adapter/plan first')
    H.verify_reference = X.verify_reference
    score_hdr.score = X.score
    inner_main = A.main
    inner_finish_program = A.program
    def program():
        source,proof = inner_finish_program()
        proof['r1_dispatch'] = dict(plan='176',verify_reference='r1_reference_provenance.verify_reference',
            score='r1_reference_provenance.score',r1_slots=list(X.R1_SLOTS),
            note='process-local module attribute dispatch; original functions used for16 original slots')
        return source,proof
    def main_redirected():
        A.DESCRIPTION,A.OUTPUT,A.WORK = DESCRIPTION,OUTPUT,WORK
        return inner_main()
    A.program = program
    A.main = main_redirected
    return W160.main()


if __name__ == '__main__':
    main()

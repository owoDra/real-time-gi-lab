#!/usr/bin/env python3
"""Plan160: source description or full state-bound selected-pilot readiness."""
from pathlib import Path
import subprocess

import readiness_preflight_selected_pilots as A
import state_bound_pilot_provenance as B
from state_bound_pilot_provenance import C, R


def main():
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),Path(B.__file__).resolve(),B.PLAN):
        C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))])
            == R.checked(path), 'commit exact160 source/plan before execution')
    R.checked(Path(A.__file__).resolve(),'d1545faac17f3326d94074c295ffc2b223ff575aef3336c8c7536d9454d42855')
    R.checked(Path(B.W.__file__).resolve(),B.WRAPPER_PIN)
    R.checked(B.W.PLAN)
    original = A.program
    def program():
        source,proof = original()
        proof['state_bound_selected_intake'] = B.composition()
        return source,proof
    A.program = program
    A.T = B
    A.PLAN = B.PLAN
    A.DESCRIPTION = R.RESULTS/'618-state-bound-selected-adapter-description.json'
    A.OUTPUT = R.RESULTS/'619-state-bound-selected-readiness-audit.json'
    A.WORK = R.BASE/'state-bound-selected-readiness-v1'
    return A.main()


if __name__ == '__main__':main()

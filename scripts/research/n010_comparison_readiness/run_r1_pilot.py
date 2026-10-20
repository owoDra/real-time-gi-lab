#!/usr/bin/env python3
"""Plan176: run an unchanged N010 pilot script with only its R1 eligibility gate replaced.

The pilot source is executed from its committed bytes with exactly one line replaced
(proved inverse); `score_hdr.score` is routed through the175B R1 scorer. Every other
byte, binary, command, budget, scoring metric and output format is the original.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import r1_reference_provenance as X
import score_hdr as S

ROOT = X.ROOT
LOCK = ROOT/'research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json'
VIEW = ROOT/'research/lanes/n010-comparison-readiness/results/747-full-corpus-r1-reference-view.json'
PLAN = ROOT/'research/lanes/n010-comparison-readiness/experiments/176-r1-pilots-and-final-audit.md'
GATES = {
    'acquire_dynamic_pilot.py':(
        "            if any(q['classification']!='STATISTICALLY_ELIGIBLE' for q in qualification):raise ValueError('reference not eligible')",
        "            _r1_require(a.references,(base,cell),vertices)"),
    'acquire_pt_pilot.py':(
        "        if row['classification']!='STATISTICALLY_ELIGIBLE':raise ValueError('reference not eligible')",
        "        _r1_require(a.references,(a.cell,),vertices)"),
}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def r1_require(references,cells,vertices):
    view = json.loads(VIEW.read_text());lock = json.loads(LOCK.read_text())
    if Path(references).resolve() != Path(view['work']).resolve():raise ValueError('pilot must use the747 view')
    for cell in cells:
        name = f'{cell}_T_B{vertices}'
        entry = next(r for r in view['rows'] if r['name']==name)
        directory = Path(references)/name
        if not directory.is_symlink() or str(directory.resolve()) != entry['target']:raise ValueError('747 view target changed')
        X.verify_reference(directory,cell,vertices,lock['cells'][cell],{})


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in GATES:raise SystemExit('usage: run_r1_pilot.py <pilot> args...')
    name = sys.argv[1];script = HERE/name
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip()
    for path in (Path(__file__),script,PLAN,Path(X.__file__)):
        if subprocess.check_output(['git','show',commit+':'+str(Path(path).resolve().relative_to(ROOT))],cwd=ROOT) != Path(path).read_bytes():
            raise ValueError('commit exact pilot/adapter/plan first: '+str(path))
    original = script.read_text();old,new = GATES[name]
    if original.count(old) != 1:raise ValueError('eligibility gate line not found exactly once')
    generated = original.replace(old,new)
    if generated.replace(new,old) != original:raise ValueError('generated pilot inverse differs')
    output = Path(sys.argv[sys.argv.index('--output')+1])
    provenance = output.with_name(output.stem+'.r1-adapter.json')
    if provenance.exists():raise ValueError('refuse existing adapter provenance')
    provenance.write_text(json.dumps(dict(schema='n010-r1-pilot-adapter/1',pilot=name,pilot_sha256=sha(script),
        adapter_sha256=sha(__file__),r1_provenance_sha256=sha(X.__file__),view_sha256=sha(VIEW),plan_sha256=sha(PLAN),
        source_commit=commit,replaced_line=old,replacement=new,inverse_exact=True,argv=sys.argv[2:],
        eligibility_rule='original for16 slots, R1 for8 (plan174)'),indent=2)+'\n')
    sys.modules['score_hdr'] = types.SimpleNamespace(score=X.score,metrics=S.metrics)
    sys.argv = [str(script)]+sys.argv[2:]
    exec(compile(generated,str(script),'exec'),dict(__name__='__main__',__file__=str(script),_r1_require=r1_require))


if __name__ == '__main__':
    main()

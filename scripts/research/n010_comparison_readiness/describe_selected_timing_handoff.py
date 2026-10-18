#!/usr/bin/env python3
"""Plan147: describe the full descriptive pilot scope; acquire nothing."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent/'experiments/147-selected-pilot-validity-without-speed-claims.md'
SELECTION = RESULTS/'417-selected-pt-quality-command-description.json'
OUTPUT = RESULTS/'503-selected-reportable-timing-scope.json'


def main():
    os.sched_setaffinity(0, {31})
    priority = os.getpriority(os.PRIO_PROCESS, 0)
    if priority < 15:os.nice(15-priority)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    inputs = {}
    for path in (Path(__file__).resolve(), PLAN, SELECTION):
        raw = path.read_bytes()
        if subprocess.check_output(['git', 'show', commit+':'+str(path.relative_to(ROOT))]) != raw:
            raise ValueError('commit exact scope source/plan/selection before description')
        inputs[str(path)] = hashlib.sha256(raw).hexdigest()
    selected = json.loads(SELECTION.read_text())
    cases = [r for r in selected['cases'] if r['spp'] == 1024]
    expected = {(c, v, False) for c in ('C1', 'C7', 'C8', 'C9') for v in (2, 8)}
    expected |= {(f'C{i}', v, True) for i in (*range(2, 7), *range(8, 13)) for v in (2, 8)}
    if len(cases) != 28 or {(r['cell'], r['vertices'], r['dynamic']) for r in cases} != expected:
        raise ValueError('exact selected28 PT trajectories differ')
    rows = []
    for case in cases:
        command = case['command']
        if (command[command.index('--spp')+1] != '1024'
                or command[command.index('--frames')+1] != ('5' if case['dynamic'] else '1')):
            raise ValueError('full selected command budget/history differs')
        rows.append(dict(id=f"{'dynamic' if case['dynamic'] else 'static'}-{case['cell']}-pt-B{case['vertices']}", role=f"pt-B{case['vertices']}",
                         cell=case['cell'], dynamic=case['dynamic'], frames=case['frames'],
                         selected_command=command, retained_capture=case['retained_capture']))
    for cell in ('C1', 'C7'):
        for role in ('hwrt', 'software', 'dense-rc'):
            rows.append(dict(id=f'static-{cell}-{role}', cell=cell, role=role, dynamic=False, frames=1))
    for cell in ('C6', 'C12'):
        rows.append(dict(id=f'dynamic-{cell}-hwrt', cell=cell, role='hwrt', dynamic=True, frames=5))
    original = {f'static-{c}-{role}' for c in ('C1', 'C7')
                for role in ('hwrt', 'software', 'pt-B2', 'pt-B8', 'dense-rc')}
    original |= {f'dynamic-{c}-{role}' for c in ('C6', 'C12') for role in ('hwrt', 'pt-B2', 'pt-B8')}
    ids = {r['id'] for r in rows}
    if len(rows) != len(ids) or len(ids) != 36 or not original <= ids or len(original) != 16:
        raise ValueError('complete original16/selected28 union36 differs')
    result = dict(schema='n010-selected-reportable-timing-scope/1', complete=True,
                  classification='SCOPE_METADATA_ONLY_NOT_EXECUTION_OR_READINESS',
                  source_commit=commit, input_sha256=inputs, rows=rows,
                  original_boundaries=sorted(original),
                  original_boundary_identity_map={k.removeprefix('static-').removeprefix('dynamic-'):k for k in sorted(original)},
                  prior_metadata_attempt=dict(source_commit='4b78b6ad',
                      failure='mode omitted from identity; static/dynamic C8/C9 collided',
                      output_created=False, native_executed=False), selected_pt_count=28,
                  non_pt_count=8, full_union_count=36, native_executed=False,
                  accepted_timing=False, final_handoff_admitted=False,
                  known_work_required_for_descriptive_handoff=False,
                  timing_evidence_valid=False, precision='NOT_EVALUATED',
                  tests='NOT_RUN; metadata description only')
    with OUTPUT.open('x') as stream:stream.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(result['classification'], len(rows))


if __name__ == '__main__':main()

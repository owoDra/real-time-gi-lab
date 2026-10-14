#!/usr/bin/env python3
"""Fix all 24 plan-037 reference targets; pending targets are not admission."""
import argparse
import json
from pathlib import Path
import subprocess
from reference_provenance import ROOT, RESULTS, read, sha
from point_guided_replayed_provenance import SELECTED, VARIANT

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lock', type=Path, required=True)
    ap.add_argument('--point-guided', type=Path, required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing reference view or scheduling record')
    inputs = {str(Path(__file__).resolve()): sha(Path(__file__))}
    for name in ('036-replayed-point-guided-proof-chain.md', '037-replayed-reference-comparison-transition.md'):
        p = RESULTS.parent/'experiments'/name
        inputs[str(p)] = sha(p)
    lock = read(a.lock, inputs)
    prior = read(RESULTS/'067-recovery-reference-view.json', inputs)
    expected = {f'C{i}_T_B{v}' for i in range(1,13) for v in (2,8)}
    if set(lock['cells']) != {f'C{i}' for i in range(1,13)} or {r['name'] for r in prior['rows']} != expected:
        raise ValueError('full locked corpus and previous scheduling map required')
    rows = []
    for old in prior['rows']:
        row = dict(old)
        if row['name'] in SELECTED:
            row.update(target=str((a.point_guided/row['name']).resolve()), computational_variant=VARIANT)
        else:
            q = read(Path(row['target'])/'qualification.json', inputs)
            if q['classification'] != 'STATISTICALLY_ELIGIBLE' or q['state_sha256'] != lock['cells'][row['cell']]['state_sha256']:
                raise ValueError('retained eligible original target changed')
        if row['state_sha256'] != lock['cells'][row['cell']]['state_sha256']:
            raise ValueError('scheduled state differs from lock')
        rows.append(row)
    a.work.mkdir(parents=True)
    for row in rows:
        (a.work/row['name']).symlink_to(row['target'], target_is_directory=True)
    result = {'schema': 'n010-reference-view/1', 'complete': True,
        'classification': 'SCHEDULING_VIEW_ONLY_NOT_READINESS',
        'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'work': str(a.work.resolve()), 'inputs': inputs, 'rows': rows, 'plan': '037',
        'selection_basis': 'Fifteen unchanged eligible original targets and nine fixed plan-036 targets; no selection on GI results; no comparison admission'}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result['classification'],len(rows))

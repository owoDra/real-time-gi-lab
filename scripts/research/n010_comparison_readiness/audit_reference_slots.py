#!/usr/bin/env python3
"""Replay complete reference provenance for explicitly selected locked slots."""
import argparse
import importlib
import json
from pathlib import Path
import subprocess
from reference_provenance import ROOT, read, sha


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--references', type=Path, required=True)
    ap.add_argument('--lock', type=Path, required=True)
    ap.add_argument('--slots', nargs='+', required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.output.exists():
        raise ValueError('refuse overwriting a retained provenance audit')
    import hybrid_reference_provenance as provenance
    inputs = {str(Path(__file__).resolve()): sha(Path(__file__)),
              str(Path(provenance.__file__).resolve()): sha(Path(provenance.__file__))}
    lock = read(a.lock, inputs)
    allowed = {f'{c}_T_B{v}' for c in lock['cells'] for v in (2, 8)}
    if not a.slots or len(set(a.slots)) != len(a.slots) or not set(a.slots) <= allowed:
        raise ValueError('unknown or duplicate locked slot')
    result = {'schema': 'n010-selected-reference-provenance-audit/1',
        'complete': False, 'all_pass': False, 'gpu_run': False,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'scope': 'CPU-only replay of explicitly selected complete reference slots; not whole-corpus readiness or comparison-view admission',
        'selected_slots': a.slots, 'inputs': inputs, 'rows': [], 'scoring_exclusions': 0}
    for slot in a.slots:
        cell, vertices = slot.rsplit('_T_B', 1)
        try:
            row = provenance.verify_reference(a.references/slot, cell, int(vertices), lock['cells'][cell], inputs)
        except (ValueError, OSError, KeyError, AssertionError) as error:
            row = {'slot': slot, 'pass': False, 'failure': str(error)}
        result['rows'].append(row)
    changed = [p for p, digest in inputs.items() if sha(Path(p)) != digest]
    result.update(complete=True, inputs_unchanged_after_audit=not changed,
                  changed_inputs=changed,
                  all_pass=bool(result['rows']) and all(r['pass'] for r in result['rows']) and not changed)
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'all_pass': result['all_pass'], 'rows': result['rows'], 'input_count': len(inputs)}))
    raise SystemExit(0 if result['all_pass'] else 2)

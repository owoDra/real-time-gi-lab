#!/usr/bin/env python3
"""Create a fixed full-corpus view for the Amendment 6 scheduling transition."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from reference_provenance import ROOT, read, physical_proof, incremental_proofs

# Scheduling selection, fixed before any incremental reference images exist.
# It does not select between acquisitions according to convergence or quality.
INCREMENTAL_CELLS = ('C2', 'C4', 'C5', 'C6')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--incremental', type=Path, required=True)
    parser.add_argument('--selection', type=Path, help='Prospective Amendment 8 full-slot target/variant map')
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing corpus view or scheduling record')
    inputs = {}
    lock = read(args.lock, inputs)
    if set(lock['cells']) != {f'C{i}' for i in range(1,13)}:
        raise ValueError('complete locked C1-C12 corpus required')
    physical_proof(inputs)
    proofs = incremental_proofs(inputs)
    if args.original.resolve() == args.incremental.resolve():
        raise ValueError('original and incremental acquisitions need separate roots')
    rows = []
    selection = read(args.selection, inputs) if args.selection else None
    if selection is not None and set(selection) != {f'C{i}_T_B{v}' for i in range(1,13) for v in (2,8)}:
        raise ValueError('recovery selection requires exactly all 24 slots')
    for cell in sorted(lock['cells'], key=lambda c:int(c[1:])):
        for vertices in (2,8):
            name = f'{cell}_T_B{vertices}'
            variant = 'exact-prefix-continuation' if cell in INCREMENTAL_CELLS else 'original-full-prefix'
            base = args.incremental if cell in INCREMENTAL_CELLS else args.original
            target = (base/name).resolve()
            if selection is not None:
                variant = selection[name]['computational_variant']
                target = Path(selection[name]['target']).resolve()
                if variant not in ('original-full-prefix','exact-prefix-continuation','proved-exact-prefix-recovery'):
                    raise ValueError('unknown scheduled reference variant')
            if variant == 'original-full-prefix' and not target.is_dir():
                raise ValueError('retained original acquisition missing: '+name)
            if (target/'qualification.json').exists():
                value = read(target/'qualification.json', inputs)
                if value['state_sha256'] != lock['cells'][cell]['state_sha256']:
                    raise ValueError('acquisition state differs from lock: '+name)
                if value.get('computational_variant', 'original-full-prefix') != variant:
                    raise ValueError('acquisition variant differs from scheduling plan')
            rows.append({'cell':cell, 'transport':f'T_B{vertices}', 'name':name,
                         'target':str(target), 'computational_variant':variant,
                         'state_sha256':lock['cells'][cell]['state_sha256']})
    # A view may contain pending references. It is never an eligibility decision.
    # The final provenance audit and preflight must examine all 24 actual chains.
    args.work.mkdir(parents=True)
    for row in rows:
        (args.work/row['name']).symlink_to(row['target'], target_is_directory=True)
    result = {'schema':'n010-reference-view/1', 'complete':True,
              'classification':'SCHEDULING_VIEW_ONLY_NOT_READINESS',
              'source_commit':subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
              'script_sha256':sha(Path(__file__)), 'work':str(args.work.resolve()),
              'inputs':inputs, 'proof_sha256':proofs, 'rows':rows,
              'amendment':'8' if selection else '6',
              'selection_basis':'Fixed interruption recovery map; all 24 slots preserved. No quality-based choice, threshold/corpus changes or overwritten evidence.' if selection else 'Fixed C2/C4/C5/C6 incremental; all other original. No quality-based choice, threshold/corpus changes or overwritten evidence.'}
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(result['classification'])

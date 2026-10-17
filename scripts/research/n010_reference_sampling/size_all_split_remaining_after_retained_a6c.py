#!/usr/bin/env python3
"""Plan089: same cost driver; dispatch successful same-acquisition237 proof."""
import json
from pathlib import Path

import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker


if __name__ == '__main__':
    require_no_other_research_worker()
    parent = D.HERE / 'size_all_split_remaining_controls.py'
    source = D.checked(parent, '5aa9b3c31a62c6cfcbdda6c2edf7142084ef51d8ca3f02f52ea9b436b1c879cd').decode()
    D.checked(Path(__file__).resolve())
    D.checked(D.RESULTS.parent / 'experiments/089-retained-a6c-cost-dispatch-amendment.md')
    proof = json.loads(D.checked(D.RESULTS / '237-posthoc-original-a6c-retained-control.json'))
    if (not proof['complete'] or not proof['all_pass'] or proof['native_reexecuted']
            or proof['native_returncode'] != 0 or not proof['deterministic_component_bits_primary_exact']):
        raise ValueError('actual same-acquisition A6c PASS required')
    for p, digest in proof['input_sha256'].items():
        D.checked(Path(p), digest)
    old = '234-all-split-original-a6c-full-physical-control.json'
    new = '237-posthoc-original-a6c-retained-control.json'
    if source.count(old) != 1 or new in source:
        raise ValueError('prerequisite dispatch anchor differs')
    changed = source.replace(old, new)
    if changed.replace(new, old) != source:
        raise ValueError('cost driver dispatch inverse differs')
    exec(compile(changed, str(parent) + '#plan089', 'exec'),
         {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})

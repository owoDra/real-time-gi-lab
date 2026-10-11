#!/usr/bin/env python3
"""N007 prospective fixed-seed multi-SPP statistical screening (no rendering)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from inspect_hdr import inspect

SPP = (512, 1024, 2048, 4096, 8192)
SEEDS = (305419896, 2596069104, 81985529216486895, 18364758544493064720)


def assess(manifest_path: Path) -> dict:
    manifest_path = manifest_path.resolve()
    root = manifest_path.parent
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get('schema_version') != 1:
        raise ValueError('unsupported manifest schema')
    for key, length in (('scene_sha256', 64), ('frame_state_sha256', 64),
                        ('source_commit', 40)):
        value = manifest.get(key)
        if not isinstance(value, str) or len(value) != length or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('invalid ' + key)
    levels = manifest.get('levels')
    if not isinstance(levels, list) or not 1 <= len(levels) <= len(SPP):
        raise ValueError('invalid SPP levels')
    if [v.get('spp') for v in levels] != list(SPP[:len(levels)]):
        raise ValueError('SPP levels must be an ordered prefix of frozen schedule')
    seen_paths = set()
    rows = []
    for level in levels:
        entries = level.get('references')
        if not isinstance(entries, list) or len(entries) != 4 or [v.get('seed') for v in entries] != list(SEEDS):
            raise ValueError('require four frozen distinct seeds in fixed order')
        paths = []
        for entry in entries:
            rel = Path(entry.get('path', ''))
            path = (root / rel).resolve()
            if rel.is_absolute() or '..' in rel.parts or not path.is_relative_to(root) or path in seen_paths:
                raise ValueError('unsafe or reused reference PFM path')
            seen_paths.add(path)
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry.get('sha256'):
                raise ValueError('missing file or reference SHA mismatch')
            paths.append(path)
        result = inspect(paths)
        rows.append({'spp': level['spp'], 'eligible': result['statistically_eligible'],
                     'active_fraction': result['union_positive_fraction'],
                     'noise_rms_range': result['noise_rms_range'],
                     'max_active_abs_p99': max(x['active_abs_luma_p99'] for x in result['pairwise']),
                     'max_active_rel_p99': max(x['active_rel_luma_p99'] for x in result['pairwise']),
                     'problems': result['problems']})
    accepted_spp = None
    for i in range(1, len(rows)):
        previous, current = rows[i-1], rows[i]
        fraction_stable = abs(current['active_fraction'] - previous['active_fraction']) <= .1 * max(previous['active_fraction'], 1e-8)
        current['signal_support_stable_vs_previous'] = fraction_stable
        if previous['eligible'] and current['eligible'] and fraction_stable:
            accepted_spp = current['spp']
            if i != len(rows)-1:
                raise ValueError('capture continued after two consecutive eligible SPP levels')
            break
    return {'schema_version': 1, 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
            'source_commit': manifest['source_commit'], 'scene_sha256': manifest['scene_sha256'],
            'frame_state_sha256': manifest['frame_state_sha256'],
            'rows': rows, 'eligible_at_spp': accepted_spp,
            'status': 'statistical-screen-pass' if accepted_spp else
                ('statistical-screen-fail' if len(rows) == len(SPP) else 'incomplete'),
            'physical_correctness_proven': False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = json.dumps(assess(args.manifest), indent=2, sort_keys=True, allow_nan=False) + '\n'
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')


if __name__ == '__main__':
    main()

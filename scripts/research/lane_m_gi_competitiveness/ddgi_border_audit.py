#!/usr/bin/env python3
"""Read-only retrospective SDK border invariant; never executes GPU or repairs data.

UpdateBorderTexel in pinned ProbeBlendingCS.hlsl specifies an exact copy from
the same probe's interior. Test uint32 identities, including signed zero; no
quality threshold, mask, interpolation or tolerance is involved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

REPO = Path(__file__).resolve().parents[3]
BASE = REPO / 'out/research/lane-m-gi-competitiveness'
SDK_SOURCE = REPO / 'out/research/n010-comparison-readiness/external/RTXGI-DDGI/rtxgi-sdk/shaders/ddgi/ProbeBlendingCS.hlsl'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def border_map(tile):
    """(destination y,x, source y,x), all four corners/rows/columns exactly once."""
    if tile not in (8, 16):
        raise ValueError('Only registered irradiance8/distance16 tiles')
    rows = []
    for y in range(tile):
        for x in range(tile):
            if x not in (0, tile - 1) and y not in (0, tile - 1):
                continue
            if x in (0, tile - 1) and y in (0, tile - 1):
                sx = 1 if x else tile - 2
                sy = 1 if y else tile - 2
            elif 0 < x < tile - 1:
                sx, sy = tile - 1 - x, y + (-1 if y else 1)
            else:
                sx, sy = x + (-1 if x else 1), tile - 1 - y
            rows.append((y, x, sy, sx))
    return np.asarray(rows, dtype=np.int64)


def check_atlas(array, tile, side):
    channels = {8: 4, 16: 2}[tile]
    if side < 1 or array.shape != (side, tile * side, tile * side, channels):
        raise ValueError('Incorrect complete atlas shape')
    if array.dtype != np.dtype('<f4') or not np.isfinite(array).all():
        raise ValueError('Atlas must be finite little-endian float32')
    m = border_map(tile)
    # Dimensions: layer, tile-y, tile-x, perimeter, channel. All reads only.
    ys = np.arange(side)[:, None, None] * tile
    xs = np.arange(side)[None, :, None] * tile
    actual = array[:, ys + m[:, 0], xs + m[:, 1], :]
    expected = array[:, ys + m[:, 2], xs + m[:, 3], :]
    bad = actual.view('<u4') != expected.view('<u4')
    mismatches = int(np.count_nonzero(bad))
    first = None
    if mismatches:
        z, ty, tx, p, c = np.argwhere(bad)[0].tolist()
        y, x, sy, sx = m[p].tolist()
        first = dict(destination=[z, ty * tile + y, tx * tile + x, c],
                     source=[z, ty * tile + sy, tx * tile + sx, c],
                     actual=float(actual[z, ty, tx, p, c]),
                     expected=float(expected[z, ty, tx, p, c]))
    return dict(exact_copy_pass=mismatches == 0, border_components=int(bad.size),
                mismatched_components=mismatches,
                mismatched_texels=int(np.count_nonzero(np.any(bad, axis=-1))),
                maximum_absolute_difference=float(np.max(np.abs(actual.astype(np.float64) - expected))),
                zero_nonzero_mismatched_components=int(np.count_nonzero(bad & ((actual == 0) != (expected == 0)))),
                first_mismatch=first)


def captures():
    """Exact frozen inventory: 6 static + 8 dynamic + 18 quality, no discovery glob."""
    for name in ('direct', 'black', 'unit', 'hdr', 'scene-one', 'scene-seven'):
        yield 'static', name, BASE / 'm001-ddgi-controls-v1' / name, [None]
    for kind in ('light', 'geometry'):
        for mode in ('fresh', 'transition'):
            for depth in (2, 8):
                name = f'{kind}-{mode}-b{depth}'
                yield 'dynamic', name, BASE / 'm001-ddgi-dynamic-controls-v1' / name, ([None] if mode == 'fresh' else list(range(4)))
    for cell in ('h01', 'h02', 'h03'):
        for depth in (2, 8):
            for rung in range(3):
                name = f'{cell}-b{depth}-q{rung}'
                yield 'quality', name, BASE / 'm001-ddgi-quality-v1' / name, [None]


def audit_all():
    rows, cases, inputs = [], [], {str(SDK_SOURCE.relative_to(REPO)): sha(SDK_SOURCE)}
    for family, name, work, frames in captures():
        receipt = json.loads((work / 'result.json').read_text())
        if not receipt['complete'] or receipt['returncode'] != 0:
            raise ValueError('Incomplete acquisition: ' + name)
        inputs[str((work / 'result.json').relative_to(REPO))] = sha(work / 'result.json')
        before = len(rows)
        for frame in frames:
            path = work / 'capture'
            if frame is not None:
                path = path / 'frames' / str(frame)
            config_path = path / 'configuration.json'
            config = json.loads(config_path.read_text())
            for p in [config_path]:
                key = str(p.relative_to(work))
                if sha(p) != receipt['payload_sha256'][key]:
                    raise ValueError('Original inventory identity differs: ' + str(p))
                inputs[str(p.relative_to(REPO))] = sha(p)
            for stage in range(config['vertices'] - 1):
                for role in ('current', 'previous'):
                    for j, tile in ((1, 8), (2, 16)):
                        p = path / f'stage-{stage}-{role}-{j}.f32'
                        digest = sha(p)
                        if digest != receipt['payload_sha256'][str(p.relative_to(work))]:
                            raise ValueError('Original atlas identity differs: ' + str(p))
                        inputs[str(p.relative_to(REPO))] = digest
                        a = np.fromfile(p, dtype='<f4').reshape(config['grid_side'], tile * config['grid_side'], tile * config['grid_side'], {1: 4, 2: 2}[j])
                        rows.append(dict(family=family, name=name, frame=frame, stage=stage, role=role,
                                         atlas='irradiance' if j == 1 else 'distance', path=str(p.relative_to(REPO)),
                                         sha256=digest, **check_atlas(a, tile, config['grid_side'])))
        own = rows[before:]
        cases.append(dict(family=family, name=name, atlases=len(own), failed_atlases=sum(not x['exact_copy_pass'] for x in own),
                          current_failed_atlases=sum(not x['exact_copy_pass'] for x in own if x['role'] == 'current')))
    return dict(schema='m001-ddgi-retrospective-border-audit/1',
                source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                auditor_sha256=sha(Path(__file__).resolve()), input_sha256=inputs,
                invariant='Every captured current/previous irradiance/distance border component equals its SDK-specified same-probe interior component bit-for-bit',
                gpu_executed=False, raw_evidence_modified=False, exact_copy_pass=all(x['exact_copy_pass'] for x in rows),
                acquisitions=len(cases), atlases=len(rows), failed_atlases=sum(not x['exact_copy_pass'] for x in rows),
                current_failed_atlases=sum(not x['exact_copy_pass'] for x in rows if x['role'] == 'current'),
                cases=cases, rows=rows, accepted_timing=False,
                qualification='RETROSPECTIVE_INVARIANT_ONLY_NOT_PHYSICAL_OR_QUALITY_ADMISSION')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise SystemExit('Existing output; never overwrite')
    report = audit_all()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f:
        json.dump(report, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
    print(json.dumps({k: report[k] for k in ('acquisitions', 'atlases', 'failed_atlases', 'current_failed_atlases', 'exact_copy_pass', 'gpu_executed')}))
    # A genuine failed predicate remains nonzero even though diagnostics are saved.
    raise SystemExit(0 if report['exact_copy_pass'] else 1)


if __name__ == '__main__':
    main()

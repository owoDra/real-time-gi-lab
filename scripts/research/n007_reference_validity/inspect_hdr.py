#!/usr/bin/env python3
"""N007 read-only, linear-HDR reference eligibility diagnostic (no rendering)."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

LUMA = (0.2126, 0.7152, 0.0722)
FLOOR = 1e-4
SPP = (512, 1024, 2048, 4096, 8192)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    v = sorted(values)
    pos = (len(v) - 1) * q
    i = int(pos)
    return v[i] * (1 - (pos - i)) + v[min(i + 1, len(v) - 1)] * (pos - i)


def read_pfm(path: Path) -> dict:
    raw = path.read_bytes()
    lines = raw.split(b'\n', 3)
    if len(lines) != 4 or lines[0].strip() != b'PF':
        raise ValueError(f'{path}: expected RGB PFM header')
    w, h = (int(v) for v in lines[1].split())
    scale = float(lines[2])
    if w < 1 or h < 1 or w * h > 100_000_000 or not math.isfinite(scale) or scale == 0:
        raise ValueError(f'{path}: invalid dimensions/scale')
    if len(lines[3]) != w * h * 12:
        raise ValueError(f'{path}: malformed payload')
    fmt = '<' if scale < 0 else '>'
    vals = struct.unpack(f'{fmt}{w*h*3}f', lines[3])
    # Same top-left convention as n001_contract.read_pfm.
    stride = w * 3
    pixels = tuple(v * abs(scale) for y in range(h - 1, -1, -1)
                   for v in vals[y * stride: (y + 1) * stride])
    ys = [sum(pixels[i + j] * LUMA[j] for j in range(3))
          for i in range(0, len(pixels), 3)]
    return {'width': w, 'height': h, 'rgb': pixels, 'y': ys,
            'sha256': hashlib.sha256(raw).hexdigest(),
            'nonfinite_channels': sum(not math.isfinite(v) for v in pixels),
            'negative_channels': sum(v < 0 for v in pixels if math.isfinite(v)),
            'scale': scale}


def info(img: dict) -> dict:
    ys = img['y']
    finite = [v for v in ys if math.isfinite(v)]
    return {'sha256': img['sha256'], 'width': img['width'], 'height': img['height'],
            'positive_luminance_pixels': sum(v > 0 for v in finite),
            'positive_fraction': sum(v > 0 for v in finite) / len(ys),
            'above_floor_pixels': sum(v >= FLOOR for v in finite),
            'mean_luminance': sum(finite) / len(ys) if len(finite) == len(ys) else None,
            'max_luminance': max(finite) if finite else None,
            'nonfinite_channels': img['nonfinite_channels'],
            'negative_channels': img['negative_channels'],
            'completely_black': all(v == 0 for v in img['rgb'])}


def compare(a: dict, b: dict, active: list[bool]) -> dict:
    if (a['width'], a['height']) != (b['width'], b['height']):
        raise ValueError('dimension mismatch')
    valid = all(math.isfinite(v) for v in a['rgb'] + b['rgb'])
    errors = [abs(x - y) for x, y in zip(a['y'], b['y'])] if valid else []
    rel = [err / max(FLOOR, (abs(ay) + abs(by)) / 2)
           for err, ay, by in zip(errors, a['y'], b['y'])]
    sq = sum((x - y) ** 2 for x, y in zip(a['rgb'], b['rgb'])) if valid else 0
    n = a['width'] * a['height']
    selected_abs = [e for e, flag in zip(errors, active) if flag]
    selected_rel = [e for e, flag in zip(rel, active) if flag]
    return {'whole_frame_rgb_rms': math.sqrt(sq / (3*n)) if valid else None,
            'whole_frame_abs_luma_p99': percentile(errors, .99),
            'active_pixel_count': len(selected_abs),
            'active_abs_luma_p99': percentile(selected_abs, .99),
            'active_rel_luma_p99': percentile(selected_rel, .99),
            'active_max_abs_luma': max(selected_abs, default=0),
            'pixel_mismatch_count': sum(e != 0 for e in errors) if valid else None,
            'exact_pixel_values_equal': a['rgb'] == b['rgb'],
            'raw_pfm_sha256_equal': a['sha256'] == b['sha256']}


def inspect(paths: list[Path], candidate: Path | None = None) -> dict:
    if len(paths) < 2:
        raise ValueError('at least two independently seeded references required')
    refs = [read_pfm(path) for path in paths]
    if len({(v['width'], v['height']) for v in refs}) != 1:
        raise ValueError('reference dimension mismatch')
    active = [any(img['y'][i] > 0 for img in refs)
              for i in range(refs[0]['width'] * refs[0]['height'])]
    pairwise = [compare(refs[i], refs[j], active)
                for i in range(len(refs)) for j in range(i + 1, len(refs))]
    records = [{'path': str(p), **info(img)} for p, img in zip(paths, refs)]
    n = len(active)
    union_count = sum(active)
    problems = []
    if any(v['nonfinite_channels'] or v['negative_channels'] for v in records):
        problems.append('nonfinite_or_negative_radiance')
    if any(v['completely_black'] for v in records):
        problems.append('black_reference')
    if union_count < 64 or union_count / n < 0.01:
        problems.append('insufficient_active_pixel_support')
    if max((v['max_luminance'] or 0) for v in records) < FLOOR:
        problems.append('low_absolute_reference_signal')
    if any(v['exact_pixel_values_equal'] for v in pairwise):
        problems.append('identical_independent_replicates')
    if len(refs) < 4:
        problems.append('fewer_than_four_independent_replicates')
    if not problems:
        # Preregistered noise gate on union-of-reference-positive pixels.
        if max(v['active_abs_luma_p99'] for v in pairwise) > 1e-5:
            problems.append('active_p99_abs_not_converged')
        if max(v['active_rel_luma_p99'] for v in pairwise) > .05:
            problems.append('active_p99_relative_not_converged')
    summary = {'schema_version': 1, 'purpose': 'reference-statistical-eligibility-only',
               'reference_paths': records,
               'union_positive_pixels': union_count,
               'union_positive_fraction': union_count / n,
               'pairwise': pairwise,
               'noise_rms_range': [min(v['whole_frame_rgb_rms'] for v in pairwise) if all(v['whole_frame_rgb_rms'] is not None for v in pairwise) else None,
                                   max(v['whole_frame_rgb_rms'] for v in pairwise) if all(v['whole_frame_rgb_rms'] is not None for v in pairwise) else None],
               'statistically_eligible': not problems,
               'problems': problems,
               'physical_correctness_proven': False,
               'note': 'Statistical eligibility cannot distinguish reference bias from shared transport-model errors.'}
    if candidate is not None:
        gpu = read_pfm(candidate)
        m = compare(gpu, refs[0], active)
        if gpu['nonfinite_channels'] or gpu['negative_channels']:
            problems.append('invalid_candidate_numeric_values')
        summary['candidate'] = {'path': str(candidate), **info(gpu),
                                'vs_first_reference': m,
                                'gpu_only_positive_pixels': sum(y > 0 and not mask
                                    for y, mask in zip(gpu['y'], active))}
        summary['statistically_eligible'] = not problems
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, action='append', required=True)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = inspect(args.reference, args.candidate)
    txt = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n'
    if args.output:
        args.output.write_text(txt, encoding='utf-8')
    else:
        print(txt, end='')


if __name__ == '__main__':
    main()

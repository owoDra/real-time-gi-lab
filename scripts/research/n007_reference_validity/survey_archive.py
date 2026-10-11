#!/usr/bin/env python3
"""N007 offline/read-only survey of archived N001/N004/N006 PFM pairs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path

LUMA = (0.2126, 0.7152, 0.0722)


def read_pfm(path: Path):
    raw = path.read_bytes()
    h = raw.split(b'\n', 3)
    if len(h) != 4 or h[0].strip() != b'PF':
        raise ValueError(f'invalid RGB PFM header: {path}')
    width, height = map(int, h[1].split())
    scale = float(h[2])
    if width <= 0 or height <= 0 or width * height > 100_000_000 or not math.isfinite(scale) or scale == 0:
        raise ValueError(f'invalid dimensions or scale: {path}')
    if len(h[3]) != width * height * 12:
        raise ValueError(f'invalid RGB PFM payload: {path}')
    endian = '<' if scale < 0 else '>'
    values = struct.unpack(f'{endian}{width*height*3}f', h[3])
    stride = width * 3
    rgb = [x * abs(scale) for y in range(height - 1, -1, -1)
           for x in values[y * stride:(y + 1) * stride]]
    if not all(math.isfinite(x) and x >= 0 for x in rgb):
        raise ValueError(f'negative or nonfinite radiance: {path}')
    y = [sum(rgb[k + i] * LUMA[i] for i in range(3))
         for k in range(0, len(rgb), 3)]
    return width, height, rgb, y, hashlib.sha256(raw).hexdigest()


def candidate_for(reference: Path) -> Path | None:
    if reference.name == 'reference-8bounce.pfm':
        names = ('candidate-000.pfm', 'current-000.pfm')
    else:
        matched = re.fullmatch(r'reference-8bounce-(\d{3})\.pfm', reference.name)
        if matched:
            names = (f'current-{matched.group(1)}.pfm',)
        else:
            matched = re.fullmatch(r'reference-(\d{3})\.pfm', reference.name)
            names = (f'output-{matched.group(1)}.pfm',) if matched else ()
    for name in names:
        p = reference.with_name(name)
        if p.is_file():
            return p
    return None


def discover_pairs(archive: Path) -> list[tuple[Path, Path]]:
    roots = (archive / 'out/research/lane-n-end-to-end-renderer',
             archive / 'out/research/n006-interval-aware-allocation')
    matches = []
    for root in roots:
        if not root.is_dir():
            continue
        for pfm in root.rglob('reference*.pfm'):
            cand = candidate_for(pfm)
            if cand:
                matches.append((pfm, cand))
    return sorted(matches)


def inspect_pair(archive: Path, reference: Path, candidate: Path) -> dict:
    rw, rh, rr, ry, rhash = read_pfm(reference)
    cw, ch, cr, cy, chash = read_pfm(candidate)
    if (rw, rh) != (cw, ch):
        raise ValueError('pair dimensions differ')
    n = rw * rh
    positive_ref = sum(y > 0 for y in ry)
    positive_candidate = sum(y > 0 for y in cy)
    candidate_only = sum(a == 0 and b > 0 for a, b in zip(ry, cy))
    ref_only = sum(a > 0 and b == 0 for a, b in zip(ry, cy))
    return {
        'reference': str(reference.relative_to(archive)),
        'candidate': str(candidate.relative_to(archive)),
        'dimensions': [rw, rh],
        'reference_sha256': rhash,
        'candidate_sha256': chash,
        'reference_positive_pixels': positive_ref,
        'candidate_positive_pixels': positive_candidate,
        'candidate_only_positive_pixels': candidate_only,
        'reference_only_positive_pixels': ref_only,
        'reference_above_1e-4_pixels': sum(y >= 1e-4 for y in ry),
        'candidate_above_1e-4_pixels': sum(y >= 1e-4 for y in cy),
        'reference_mean_luma': sum(ry) / n,
        'candidate_mean_luma': sum(cy) / n,
        'rgb_rms': math.sqrt(sum((a - b) ** 2 for a, b in zip(rr, cr)) / (n * 3)),
    }


def summarize_signatures(results: list[dict]) -> tuple[list[dict], dict[str, dict]]:
    """Do not confuse repeated archived runs with independent scene evidence."""
    signatures: dict[tuple[str, str], dict] = {}
    cohorts: dict[str, dict] = {}
    for item in results:
        key = (item['reference_sha256'], item['candidate_sha256'])
        signature = signatures.setdefault(key, {
            'reference_sha256': key[0],
            'candidate_sha256': key[1],
            'count': 0,
            'reference_positive_pixels': item['reference_positive_pixels'],
            'candidate_positive_pixels': item['candidate_positive_pixels'],
            'representative_reference': item['reference'],
        })
        signature['count'] += 1
        rel_parts = Path(item['reference']).parts
        group = rel_parts[3] if len(rel_parts) > 3 else 'unknown'
        cohort = cohorts.setdefault(group, {
            'inspected_pairs': 0,
            'reference_all_black_pairs': 0,
            'gpu_positive_with_black_reference_pairs': 0,
            'unique_signature_keys': set(),
        })
        cohort['inspected_pairs'] += 1
        black = item['reference_positive_pixels'] == 0
        cohort['reference_all_black_pairs'] += int(black)
        cohort['gpu_positive_with_black_reference_pairs'] += int(
            black and item['candidate_positive_pixels'] > 0)
        cohort['unique_signature_keys'].add(key)
    for cohort in cohorts.values():
        cohort['unique_pair_signatures'] = len(cohort.pop('unique_signature_keys'))
    return sorted(signatures.values(), key=lambda x: (-x['count'], x['reference_sha256'], x['candidate_sha256'])), dict(sorted(cohorts.items()))


def survey(archive: Path, max_pairs: int = 0) -> dict:
    archive = archive.resolve()
    if not archive.is_dir():
        raise ValueError(f'no private archive at {archive}')
    pairs = discover_pairs(archive)
    if max_pairs < 0:
        raise ValueError('--max-pairs must be nonnegative (0 means all)')
    selected = pairs[:max_pairs] if max_pairs else pairs
    results, errors = [], []
    for ref, cand in selected:
        try:
            results.append(inspect_pair(archive, ref, cand))
        except (OSError, ValueError, struct.error, OverflowError) as e:
            errors.append({'reference': str(ref.relative_to(archive)), 'error': str(e)})
    signatures, cohorts = summarize_signatures(results)
    return {
        'schema_version': 2,
        'classification': 'archived-image-survey-only; not physical-validation',
        'archive_root_not_exported': True,
        'total_discovered_pairs': len(pairs),
        'inspected_pairs': len(results),
        'failed_pairs': len(errors),
        'truncated': bool(max_pairs and len(pairs) > max_pairs),
        'reference_all_black_pairs': sum(x['reference_positive_pixels'] == 0 for x in results),
        'gpu_positive_with_black_reference_pairs': sum(
            x['reference_positive_pixels'] == 0 and x['candidate_positive_pixels'] > 0 for x in results),
        'unique_pair_signatures': len(signatures),
        'unique_black_reference_signatures': sum(x['reference_positive_pixels'] == 0 for x in signatures),
        'unique_gpu_positive_with_black_reference_signatures': sum(
            x['reference_positive_pixels'] == 0 and x['candidate_positive_pixels'] > 0 for x in signatures),
        'signature_groups': signatures,
        'cohort_summary': cohorts,
        'pairs': results,
        'errors': errors,
        'no_gpu_or_cpu_rendering': True,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', required=True, type=Path)
    p.add_argument('--max-pairs', type=int, default=0,
                   help='Optional diagnostic cap; 0 (default) inspects all discovered pairs')
    p.add_argument('--output', type=Path,
                   default=Path('out/research/n007-reference-validity/p0-archived-reference-survey.json'))
    args = p.parse_args()
    try:
        archive = args.archive.resolve()
        out = args.output.resolve()
        if out.is_relative_to(archive):
            raise ValueError('output must not write into the private archive')
        result = survey(archive, args.max_pairs)
        if not result['total_discovered_pairs']:
            raise ValueError('no paired reference/candidate PFMs discovered in archived N001/N004/N006 directories')
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n')
        print(json.dumps({k: result[k] for k in ('total_discovered_pairs','inspected_pairs','failed_pairs','truncated','reference_all_black_pairs','gpu_positive_with_black_reference_pairs','unique_pair_signatures','unique_black_reference_signatures')}, indent=2))
        print(f'Full read-only survey: {out}')
        return 0 if not result['failed_pairs'] and not result['truncated'] else 1
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f'N007 survey: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""N007 read-only verification of N006 M3b/M3c summary metadata (not PFMs)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

M3B_SHA = '1c251467f61b9bac777ca860f689c2903c55214cd4bb8ff9e2997b92e6cc98d6'
M3C_SHA = 'b2d030bfa8cd653ac4aa64840a0c1cd2a9de2a1beab5e75d447e2f6ea783b92b'
PIXELS = 320 * 180


def audit(m3b: Path, m3c: Path) -> dict:
    original = [p.read_bytes() for p in (m3b, m3c)]
    digests = [hashlib.sha256(v).hexdigest() for v in original]
    if digests != [M3B_SHA, M3C_SHA]:
        raise ValueError('historical summary hash mismatch (do not modify evidence)')
    b, c = (json.loads(v) for v in original)
    if (b.get('protocol_version') != 'n006-p1m3b-moving-rigid-q8-two-reference-signed-v1'
            or b.get('status') != 'invalid-retained'
            or b.get('scenario') != 'moving-rigid'
            or c.get('protocol_version') != 'n006-p1m3c-deforming-reference-eligibility-quality-v1'
            or c.get('scenario') != 'deforming-control'):
        raise ValueError('not the retained N006 M3b and M3c campaign metadata')
    preflight = c['reference_preflight']
    a = preflight['reference']
    d = preflight['reference_independent']
    if (a['nonfinite_rgb_pixels'] or a['negative_rgb_pixels'] or
            d['nonfinite_rgb_pixels'] or d['negative_rgb_pixels']):
        raise ValueError('unexpected invalid radiance in archived M3c summary')
    support_a, support_b = a['positive_rgb_pixels'], d['positive_rgb_pixels']
    # Any channel difference must occur in the union of positive-RGB pixels.
    # For two finite, nonnegative images, both are exactly zero outside this union.
    union_upper = min(PIXELS, support_a + support_b)
    zero_lower = PIXELS - union_upper
    # N001 uses linear interpolation at q*(n-1). If floor/ceil lie in zero
    # support, full-image p99 is forced zero regardless of active mismatch.
    q99_upper_index = (99 * (PIXELS - 1) + 99) // 100
    forced_zero = zero_lower > q99_upper_index
    return {
        'schema_version': 1,
        'classification': 'diagnostic-only-from-authentic-retained-summary-json',
        'sources': {'m3b_sha256': digests[0], 'm3c_sha256': digests[1]},
        'm3b': {'status': b['status'], 'failure': b['failures'],
                'PFM_read': False, 'reference_brightness_known': False},
        'm3c': {
            'pixels_per_image': PIXELS,
            'positive_pixels_a': support_a, 'positive_pixels_b': support_b,
            'positive_fraction_a': support_a / PIXELS,
            'positive_fraction_b': support_b / PIXELS,
            'union_positive_upper_bound': union_upper,
            'union_fraction_upper_bound': union_upper / PIXELS,
            'forced_full_frame_p99_zero_for_pairwise_luma_error': forced_zero,
            'max_luminance_a': a['max_luminance'],
            'max_luminance_b': d['max_luminance'],
            'mean_rgb_channel_a': a['rgb_channel_sum'] / (PIXELS * 3),
            'mean_rgb_channel_b': d['rgb_channel_sum'] / (PIXELS * 3),
            'reference_A_B_rgb_rms': preflight['reference_A_B_RMS'],
            'reference_A_sha256_claim': a['PFM_SHA256'],
            'reference_B_sha256_claim': d['PFM_SHA256'],
            'PFM_hashes_independently_verified': False,
            'PFM_read': False,
            'reported_spp_a': a['spp'], 'reported_spp_b': d['spp'],
            'historical_decision_unmodified': True,
        },
        'physical_correctness_proven': False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--m3b', type=Path, required=True)
    parser.add_argument('--m3c', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = json.dumps(audit(args.m3b, args.m3c), indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    else:
        print(text, end='')


if __name__ == '__main__':
    main()

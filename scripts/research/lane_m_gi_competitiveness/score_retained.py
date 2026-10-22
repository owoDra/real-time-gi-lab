#!/usr/bin/env python3
"""CPU-only whole-image HDR scoring of one already retained M001 RC capture."""
import argparse
import json

import reference_step as R
from score_hdr import score


def reference(cell, bounce):
    if (cell, bounce) == ('H01', 2):
        return R.ROOT / 'out/research/lane-m-gi-competitiveness/m001-h01-b2-original-admitted-reference-v1'
    return R.target(cell, bounce) / 'admitted'


def run(cell, bounce):
    state, audit, inputs = R.preflight(cell, bounce)
    ref = reference(cell, bounce)
    spec = {'state_directory': str((R.LANE / f'capture/M001-{cell}-hwrt').relative_to(R.ROOT)),
            'state_sha256': R.CAPTURE_SHA[cell]}
    verification = R.P.verify_reference(ref, cell, bounce, spec, inputs)
    dest = R.BASE / f'{cell}_T_B{bounce}' / 'retained-incumbent-hwrt-quality'
    R.require(not dest.exists(), 'refuse existing score or partial output')
    capture = R.ROOT / spec['state_directory']
    dest.mkdir(parents=True)
    scored = score(capture, R.read(ref / 'qualification.json'), ref, dest / 'quality.json')
    R.require(scored['state_bytes_equal'] and scored['complete_physical_scene_bytes_equal']
              and scored['scoring_exclusions'] == 0, 'state mismatch or scoring exclusion')
    report = {'schema': 'lane-m-m001-retained-incumbent-hdr-quality/1',
              'classification': 'PASS' if scored['pilot_quality_target'] == 'PASS' else 'QUALITY_FAIL',
              'quality': scored, 'reference_verification': verification,
              'reference_qualification_sha256': R.sha(ref / 'qualification.json'),
              'original_state_audit': audit, 'reference_inputs_sha256': inputs,
              'role': 'incumbent-hwrt', 'budget': 'unchanged original fixed RC capture; 512 spp capture metadata',
              'scope': 'Static controlled heldout at a finite-depth reference target; RC budgets are diagnostic fixed budgets, not asserted PT-equivalent.',
              'gpu_executed': False, 'new_candidate_image_acquired': False,
              'accepted_timing': False, 'superiority_claim': False}
    R.write_new(dest / 'quality.json', report)
    return {'cell': cell, 'transport': f'T_B{bounce}', 'classification': report['classification'],
            'total_nrmse': scored['components']['total']['nrmse'],
            'indirect_nrmse': scored['components']['indirect']['nrmse'],
            'indirect_signed_bias': scored['components']['indirect']['signed_sum_bias'],
            'result': str((dest / 'quality.json').relative_to(R.ROOT)),
            'result_sha256': R.sha(dest / 'quality.json')}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cell', required=True, choices=tuple(R.CAPTURE_SHA))
    ap.add_argument('--bounce', required=True, type=int, choices=(2, 8))
    args = ap.parse_args()
    print(json.dumps(run(args.cell, args.bounce), indent=2))

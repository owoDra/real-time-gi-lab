#!/usr/bin/env python3
"""CPU-only score of one retained fixed control at one independently admitted depth target."""
import argparse
import json
from pathlib import Path

import numpy as np
import audit_quality_step as A
import frozen_quality_step as F
import score_hdr as S

R = F.R


def run(cell, bounce, role):
    R.require(role == 'dense-rc', 'other controls need their native intake first')
    case = F.Case(cell, 2, 1, 'dense-rc')
    source_audit = A.audit(case)
    R.require(source_audit['quality_evidence_valid'], 'invalid retained dense source capture')
    state, _, inputs = R.preflight(cell, bounce)
    ref = F.reference(cell, bounce)
    spec = {'state_directory': str((R.LANE / f'capture/M001-{cell}-hwrt').relative_to(R.ROOT)),
            'state_sha256': state['sha256']}
    verification = R.P.verify_reference(ref, cell, bounce, spec, inputs)
    out = R.target(cell, bounce) / f'fixed-{role}-quality'
    R.require(not out.exists(), 'refuse existing score/partial; never overwrite native evidence')
    out.mkdir(parents=True)
    capture = case.WORK / 'capture'
    q = R.read(ref / 'qualification.json')
    scored = S.score(capture, q, ref, out / 'quality.json')
    reference_spp = q['levels'][-1]['spp']
    means = np.mean([R.Q.L.read_sidecar(ref / f'o.n{reference_spp}.s{i}.f64')['mean'] for i in range(4)], axis=0)
    replay = {}
    for name in ('direct', 'indirect', 'total'):
        actual = R.Q.L.read_pfm(capture / f'{name}.pfm') @ S.LUMA
        expected = means[..., R.Q.L.COMPONENTS.index(name), :] @ S.LUMA
        replay[name] = S.metrics(actual, expected)
        R.require(replay[name] == scored['components'][name]
                  and np.array_equal(np.load(out / f'quality.{name}.error.npy', allow_pickle=False), actual - expected),
                  'full-image independent metric/error replay differs')
    passed = A.quality_pass(replay)
    R.require(scored['pilot_quality_target'] == ('PASS' if passed else 'FAIL'), 'classifier differs')
    report = {'schema': 'lane-m-m001-fixed-control-reference-target/1', 'cell': cell,
              'transport': f'T_B{bounce}', 'role': role, 'classification': 'PASS' if passed else 'QUALITY_FAIL',
              'quality': scored, 'reference_verification': verification,
              'source_result_sha256': source_audit['result_sha256'],
              'source_raw_inventory_replayed': source_audit['raw_payloads_rehashed'],
              'owned_memory': source_audit['owned_memory'], 'native_work': str(case.WORK.relative_to(R.ROOT)),
              'gpu_executed_by_scorer': False, 'independent_metric_replay': True,
              'finite_depth_equivalent': False, 'accepted_timing': False,
              'scope': 'same fixed dense estimator image scored against a separately admitted reference target; not another native run'}
    R.write_new(out / 'quality.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cell', required=True, choices=('H01', 'H02', 'H03'))
    p.add_argument('--bounce', required=True, type=int, choices=(2, 8))
    p.add_argument('--role', required=True, choices=('dense-rc',))
    a = p.parse_args()
    r = run(a.cell, a.bounce, a.role)
    print(json.dumps({'cell': r['cell'], 'transport': r['transport'], 'role': r['role'],
                      'classification': r['classification'], 'components': r['quality']['components']}, indent=2))

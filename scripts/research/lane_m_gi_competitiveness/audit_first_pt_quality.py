#!/usr/bin/env python3
"""Independently audit retained first PT output on CPU; never acquire or retry."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

import numpy as np
import first_pt_quality as F
import score_hdr as S

R = F.R
PINNED_PLAN = R.ROOT / 'research/lanes/lane-m-gi-competitiveness/results/019-first-pt-cpu-plan.json'
PLAN_SHA = '091825218651b649b744cac31f978e3cc32112fbd347b32c53989abd964a8892'


def archive_members(path):
    """Read two compact proof records without extracting attacker-controlled paths."""
    with tarfile.open(path) as tar:
        members = tar.getmembers()
        R.require(len(members) == 2 and {m.name for m in members} == {'plan.json', 'result.json'},
                  'unexpected, missing or duplicate proof archive members')
        R.require(all(m.isfile() and 0 <= m.size <= 1024**2 for m in members),
                  'nonregular/oversized compact proof member')
        return {m.name: tar.extractfile(m).read() for m in members}


def validate_inventory(work, inventory):
    R.require(type(inventory) is dict and bool(inventory), 'missing native payload inventory')
    for name, digest in inventory.items():
        rel = Path(name)
        path = (work / rel).resolve()
        R.require(not rel.is_absolute() and '..' not in rel.parts
                  and path.is_relative_to(work.resolve()) and path.is_file(),
                  'unsafe/missing payload: ' + name)
        R.require(R.sha(path) == digest, 'retained payload changed: ' + name)
    actual = {str(p.relative_to(work)) for p in work.rglob('*') if p.is_file()
              and p != work / 'result.json'}
    R.require(actual == set(inventory), 'unrecorded or omitted local payload')


def quality_pass(components):
    total, indirect = components['total'], components['indirect']
    return (total['nrmse'] is not None and indirect['nrmse'] is not None
            and indirect['signed_sum_bias'] is not None and total['nrmse'] <= .05
            and indirect['nrmse'] <= .10 and abs(indirect['signed_sum_bias']) <= .05)


def audit():
    R.require(F.WORK.is_dir() and (F.WORK / 'result.json').is_file() and F.ARCHIVE.is_file(),
              'terminal PT evidence absent/incomplete; no GPU result can be inferred')
    R.require(R.sha(PINNED_PLAN) == PLAN_SHA and R.sha(F.PLAN) == PLAN_SHA,
              'frozen original CPU plan changed')
    members = archive_members(F.ARCHIVE)
    R.require(members['plan.json'] == PINNED_PLAN.read_bytes()
              and members['result.json'] == (F.WORK / 'result.json').read_bytes(),
              'compact proof differs from pinned plan/local terminal bytes')
    plan, result = json.loads(members['plan.json']), json.loads(members['result.json'])
    R.require(result['schema'] == 'lane-m-m001-first-pt-quality-result/1'
              and result['plan_sha256'] == PLAN_SHA and result['command'] == plan['command']
              and type(result.get('complete')) is bool
              and result['accepted_timing'] is False, 'terminal scope/plan identity differs')
    validate_inventory(F.WORK, result['payload_sha256'])
    started = R.read(F.WORK / 'started.json')
    R.require(started == {'plan_sha256': PLAN_SHA, 'plan': plan}, 'started receipt differs')
    if not result.get('complete'):
        R.require(result['classification'] == 'FAILED_RETAIN_PARTIAL_NO_RETRY',
                  'incomplete result falsely classified')
        return {'schema': 'lane-m-m001-first-pt-independent-cpu-audit/1',
                'classification': 'OPERATIONAL_FAILURE_RETAINED_NOT_A_QUALITY_DECISION',
                'result_sha256': R.sha(F.WORK / 'result.json'), 'error': result.get('error'),
                'quality_evidence_valid': False, 'accepted_timing': False,
                'gpu_executed_by_auditor': False}
    R.require(result.get('returncode') == 0 and result.get('gpu_executed') is True,
              'completed receipt lacks successful native execution')
    state, state_audit, inputs = R.preflight('H01', 2)
    for path, digest in plan['input_sha256'].items():
        R.require(R.sha(Path(path)) == digest, 'original prepared input drifted: ' + path)
    ref = F.reference('H01', 2)
    spec = {'state_directory': str((R.LANE / 'capture/M001-H01-hwrt').relative_to(R.ROOT)),
            'state_sha256': state['sha256']}
    verification = R.P.verify_reference(ref, 'H01', 2, spec, inputs)
    R.require(verification == plan['reference_verification'], 'reference admission changed')
    capture = F.WORK / 'capture'
    got = R.Q.L.read_state(capture)
    R.require(got['sha256'] == R.CAPTURE_SHA['H01'], 'complete physical state changed')
    R.require(hashlib.sha256(R.Q.scene_for_state(got, 2).text().encode()).hexdigest()
              == R.CORRECTED_SHA['H01'][2], 'complete derived physical scene changed')
    frames = R.read(capture / 'frames.json')
    R.require(result['timing'] == {'classification': 'DIAGNOSTIC_UNCALIBRATED_NO_SPEED_CLAIM',
                                   'native': frames}, 'terminal/native timing metadata differs')
    R.require((frames['family'], frames['spp'], frames['vertices'], frames['seed'],
               frames['width'], frames['height'], len(frames['frames'])) ==
              ('pixel-pt', 1, 2, 305419896, 320, 180, 1), 'native budget/viewport changed')
    R.require(frames['frames'][0]['index'] == 0 and frames['frames'][0]['seed'] == 305419896
              and frames['frames'][0]['state'] == 'static', 'native frame identity changed')
    for name in ('geometry-state.bin', 'frame-state.bin', 'direct.pfm', 'indirect.pfm', 'total.pfm'):
        R.require(R.sha(capture / name) == R.sha(capture / 'frames/0' / name),
                  'root/frame duplicate mismatch: ' + name)
    allocation = F.memory(R.read(capture / 'allocation-ledger.json'))
    R.require(allocation == result['memory'], 'independent owned memory replay differs')
    q = R.read(ref / 'qualification.json')
    spp = q['levels'][-1]['spp']
    means = np.mean([R.Q.L.read_sidecar(ref / f'o.n{spp}.s{i}.f64')['mean'] for i in range(4)], axis=0)
    components = {}
    quality = result['quality']
    R.require(result['reference_qualification_sha256'] == verification['qualification_sha256']
              and quality['cell'] == 'H01' and quality['transport'] == 'T_B2'
              and quality['state_sha256'] == R.CAPTURE_SHA['H01']
              and quality['reference_state_sha256'] == R.CAPTURE_SHA['H01']
              and quality['complete_oracle_scene_sha256'] == R.CORRECTED_SHA['H01'][2],
              'score reference/cell/transport identity changed')
    R.require(quality['scoring_exclusions'] == 0 and quality['state_bytes_equal']
              and quality['complete_physical_scene_bytes_equal'], 'exclusion/physical mismatch in score')
    for component in ('direct', 'indirect', 'total'):
        image = capture / f'{component}.pfm'
        R.require(R.sha(image) == quality['capture_payload_sha256'][component + '.pfm'],
                  'score refers to another image')
        gpu = R.Q.L.read_pfm(image) @ S.LUMA
        reference = means[..., R.Q.L.COMPONENTS.index(component), :] @ S.LUMA
        components[component] = S.metrics(gpu, reference)
        R.require(components[component] == quality['components'][component],
                  'whole-image metric replay differs: ' + component)
        error = np.load(F.WORK / f'quality.{component}.error.npy', allow_pickle=False)
        R.require(np.array_equal(error, gpu - reference), 'error map differs: ' + component)
    passed = quality_pass(components)
    R.require(quality['pilot_quality_target'] == ('PASS' if passed else 'FAIL')
              and result['classification'] == ('PASS' if passed else 'QUALITY_FAIL'),
              'reported classifier differs from frozen HDR thresholds')
    return {'schema': 'lane-m-m001-first-pt-independent-cpu-audit/1',
            'classification': result['classification'], 'quality_evidence_valid': True,
            'result_sha256': R.sha(F.WORK / 'result.json'), 'archive_sha256': R.sha(F.ARCHIVE),
            'raw_payloads_rehashed': len(result['payload_sha256']), 'reference_verification': verification,
            'components': components, 'owned_memory': allocation, 'state_audit': state_audit,
            'accepted_timing': False, 'gpu_executed_by_auditor': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    R.require(not args.output.exists(), 'refuse existing independent audit output')
    R.require(not args.output.resolve().is_relative_to(F.WORK.resolve()),
              'keep audit outside immutable native work root')
    report = audit()
    R.write_new(args.output, report)
    print(json.dumps(report, indent=2))

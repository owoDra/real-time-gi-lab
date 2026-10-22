#!/usr/bin/env python3
"""Independent whole-image CPU audit of one frozen M001 PT/dense unit; never acquire."""
import hashlib
import json
from pathlib import Path
import tarfile
import subprocess

import numpy as np
import first_pt_quality as Original
import score_hdr as S

R = Original.R

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


def audit(F):
    PINNED_PLAN = F.PLAN
    PLAN_SHA = R.sha(PINNED_PLAN)
    cell, bounce, spp, family = F.cell, F.bounce, F.spp, F.family
    R.require(F.WORK.is_dir() and (F.WORK / 'result.json').is_file() and F.ARCHIVE.is_file(),
              'terminal PT evidence absent/incomplete; no GPU result can be inferred')
    members = archive_members(F.ARCHIVE)
    R.require(members['plan.json'] == PINNED_PLAN.read_bytes()
              and members['result.json'] == (F.WORK / 'result.json').read_bytes(),
              'compact proof differs from pinned plan/local terminal bytes')
    plan, result = json.loads(members['plan.json']), json.loads(members['result.json'])
    R.require(plan['scope'] == {'cell': cell, 'bounce': bounce, 'spp': spp, 'family': family},
              'named audit differs from frozen plan scope')
    source = plan['source_commit']
    R.require(len(source) == 40 and all(c in '0123456789abcdef' for c in source)
              and subprocess.run(['git', 'merge-base', '--is-ancestor', source, 'HEAD'],
                                 cwd=R.ROOT, capture_output=True).returncode == 0,
              'plan source must be a reachable research ancestor')
    for name in ('frozen_quality_step.py', 'audit_quality_step.py'):
        path = R.ROOT / 'scripts/research/lane_m_gi_competitiveness' / name
        original = subprocess.check_output(['git', 'show', source + ':' + str(path.relative_to(R.ROOT))], cwd=R.ROOT)
        R.require(hashlib.sha256(original).hexdigest() == plan['input_sha256'][str(path)],
                  'plan code hashes differ from committed source')
    from frozen_quality_step import command
    R.require(plan['command'] == command(F), 'plan native command differs from named frozen unit')
    R.require(result['schema'] == 'lane-m-m001-frozen-quality-result/1'
              and result['plan_sha256'] == PLAN_SHA and result['command'] == plan['command']
              and type(result.get('complete')) is bool
              and result['accepted_timing'] is False, 'terminal scope/plan identity differs')
    validate_inventory(F.WORK, result['payload_sha256'])
    started = R.read(F.WORK / 'started.json')
    R.require(started == {'plan_sha256': PLAN_SHA, 'plan': plan}, 'started receipt differs')
    if not result.get('complete'):
        R.require(result['classification'] == 'FAILED_RETAIN_PARTIAL_NO_RETRY',
                  'incomplete result falsely classified')
        return {'schema': 'lane-m-m001-frozen-quality-independent-cpu-audit/1',
                'classification': 'OPERATIONAL_FAILURE_RETAINED_NOT_A_QUALITY_DECISION',
                'result_sha256': R.sha(F.WORK / 'result.json'), 'error': result.get('error'),
                'quality_evidence_valid': False, 'accepted_timing': False,
                'gpu_executed_by_auditor': False}
    R.require(result.get('returncode') == 0 and result.get('gpu_executed') is True,
              'completed receipt lacks successful native execution')
    state, state_audit, inputs = R.preflight(cell, bounce)
    for path, digest in plan['input_sha256'].items():
        R.require(R.sha(Path(path)) == digest, 'original prepared input drifted: ' + path)
    ref = F.reference(cell, bounce)
    spec = {'state_directory': str((R.LANE / f'capture/M001-{cell}-hwrt').relative_to(R.ROOT)),
            'state_sha256': state['sha256']}
    verification = R.P.verify_reference(ref, cell, bounce, spec, inputs)
    R.require(verification == plan['reference_verification'], 'reference admission changed')
    capture = F.WORK / 'capture'
    got = R.Q.L.read_state(capture)
    R.require(got['sha256'] == R.CAPTURE_SHA[cell], 'complete physical state changed')
    R.require(hashlib.sha256(R.Q.scene_for_state(got, bounce).text().encode()).hexdigest()
              == R.CORRECTED_SHA[cell][bounce], 'complete derived physical scene changed')
    frames = R.read(capture / 'frames.json')
    R.require(result['timing'] == {'classification': 'DIAGNOSTIC_UNCALIBRATED_NO_SPEED_CLAIM',
                                   'native': frames}, 'terminal/native timing metadata differs')
    R.require((frames['family'], frames['spp'], frames['vertices'], frames['seed'],
               frames['width'], frames['height'], len(frames['frames'])) ==
              (family, spp, bounce, 305419896, 320, 180, 1), 'native budget/viewport changed')
    R.require(frames['frames'][0]['index'] == 0 and frames['frames'][0]['seed'] == 305419896
              and frames['frames'][0]['state'] == 'static', 'native frame identity changed')
    for name in ('geometry-state.bin', 'frame-state.bin', 'direct.pfm', 'indirect.pfm', 'total.pfm'):
        R.require(R.sha(capture / name) == R.sha(capture / 'frames/0' / name),
                  'root/frame duplicate mismatch: ' + name)
    allocation = F.memory(R.read(capture / 'allocation-ledger.json'))
    R.require(allocation == result['memory'], 'independent owned memory replay differs')
    q = R.read(ref / 'qualification.json')
    reference_spp = q['levels'][-1]['spp']
    means = np.mean([R.Q.L.read_sidecar(ref / f'o.n{reference_spp}.s{i}.f64')['mean'] for i in range(4)], axis=0)
    components = {}
    quality = result['quality']
    R.require(result['reference_qualification_sha256'] == verification['qualification_sha256']
              and quality['cell'] == cell and quality['transport'] == f'T_B{bounce}'
              and quality['state_sha256'] == R.CAPTURE_SHA[cell]
              and quality['reference_state_sha256'] == R.CAPTURE_SHA[cell]
              and quality['complete_oracle_scene_sha256'] == R.CORRECTED_SHA[cell][bounce],
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
    return {'schema': 'lane-m-m001-frozen-quality-independent-cpu-audit/1',
            'classification': result['classification'], 'quality_evidence_valid': True,
            'result_sha256': R.sha(F.WORK / 'result.json'), 'archive_sha256': R.sha(F.ARCHIVE),
            'raw_payloads_rehashed': len(result['payload_sha256']), 'reference_verification': verification,
            'components': components, 'owned_memory': allocation, 'state_audit': state_audit,
            'accepted_timing': False, 'gpu_executed_by_auditor': False}



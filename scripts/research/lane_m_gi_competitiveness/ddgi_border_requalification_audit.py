#!/usr/bin/env python3
"""011 independent read-only physical, full-copy, semantic and allocation audit.

No GPU execution and no indirect HDR/reference quality scoring. Finite-stage
scene captures are used solely for exact invariants and direct physical checks.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
import ddgi_border_cases as F
import ddgi_border_copy_check as C
import ddgi_quality_audit as Q
import ddgi_dynamic_audit as D
from audit_h01_evidence import memory
from audit_quality_step import archive_members, validate_inventory
import score_hdr as S

R = F.R


def unit_labels(case):
    labels = ['fresh-zero-initialize']
    for k in range(case.depth - 1):
        p = f'stage-{k}'
        labels += [p + '-clear-destination']
        labels += ([p + '-trace-' + str(begin) for begin in range(0, case.side**3 * case.rays, 4096)]
                   if case.mode == 'scene' else [p + '-constant-ray-data'])
        labels += [p + '-sdk-blend', 'readback-' + p + '-pre-border-1', 'readback-' + p + '-pre-border-2',
                   p + '-border-irradiance', p + '-border-distance']
        labels += ['readback-' + p + '-current-' + str(j) for j in range(4)]
        labels += ['readback-' + p + '-previous-' + str(j) for j in range(1, 4)]
    return labels + ['primary-direct-gather']


def old_work(case):
    if case.family == 'static':
        return F.S.paths(case.name.removeprefix('static-'))[1]
    if case.family == 'dynamic':
        return D.F.paths(case.name.removeprefix('dynamic-'))[1]
    rung = (8, 16, 24).index(case.side)
    return Q.F.Case('H01', case.depth, rung).work


def old_identity_inputs(case):
    work = old_work(case)
    result = R.read(work / 'result.json')
    R.require(result['complete'] and result['returncode'] == 0, 'Corresponding old acquisition incomplete')
    validate_inventory(work, result['payload_sha256'])
    return {str(work / 'result.json'): R.sha(work / 'result.json'),
            **{str(work / p): h for p, h in result['payload_sha256'].items()}}


def atlas(path, layout):
    a = np.fromfile(path, dtype='<f4')
    shape = (layout['layers'], layout['h'], layout['w'], layout['channels'])
    R.require(a.size == int(np.prod(shape)) and np.isfinite(a).all(), '011 atlas incomplete/nonfinite/incorrect shape: ' + str(path))
    return a.reshape(shape)


def interior_bits(a, tile, side):
    # z, probe-y, local-y, probe-x, local-x, channel
    return a.reshape(side, side, tile, side, tile, a.shape[-1])[:, :, 1:-1, :, 1:-1, :].view('<u4')


def same_frame(a, b, case):
    names = D.data_names(case.depth) + [f'stage-{k}-pre-border-{j}.f32' for k in range(case.depth - 1) for j in (1, 2)]
    for name in names:
        R.require(R.sha(a / name) == R.sha(b / name), '011 corrected frame identity differs: ' + name)
    ca, cb = R.read(a / 'configuration.json'), R.read(b / 'configuration.json')
    ca.pop('setup_wall_us')
    cb.pop('setup_wall_us')
    R.require(ca == cb, '011 corrected non-timing configuration differs')


def frame_report(case, path, state_path, old_path):
    for n in ('geometry-state.bin', 'frame-state.bin'):
        R.require((path / n).read_bytes() == (state_path / n).read_bytes(), '011 physical state differs')
    state = R.Q.L.read_state(state_path)
    cfg = R.read(path / 'configuration.json')
    R.require((cfg['mode'], cfg['grid_side'], cfg['rays'], cfg['vertices'], cfg['seed']) ==
              (case.mode, case.side, case.rays, case.depth, 305419896), '011 budget/mode/seed differs')
    verts = state['verts'].reshape(-1, 3)
    lo, hi = verts.min(axis=0), verts.max(axis=0)
    extent = hi - lo
    origin = ((hi + lo) * .5).astype(np.float32)
    spacing = ((extent + 2 * (extent / (case.side - 1))) / (case.side - 1)).astype(np.float32)
    bias = float(np.float32(.01) * spacing.min())
    R.require(cfg['origin'] == origin.astype(float).tolist() and cfg['spacing'] == spacing.astype(float).tolist() and cfg['normal_view_bias'] == bias,
              '011 geometry-only grid/normal-view bias differs')
    R.require(cfg['hysteresis'] == 0 and cfg['gamma'] == 1 and cfg['brightness_threshold'] == 1e6 and cfg['distance_exponent'] == 50
              and cfg['rotation_updates_per_volume'] == 1 and cfg['ray_max'] == float(state['camera_forward_far'][3]), '011 descriptor/history differs')
    R.require(cfg['images'] == Q.layouts(case.side, case.rays), '011 full SDK image layout differs')
    packed = (path / 'constants-0.bin').read_bytes()
    R.require(len(packed) == 128 and packed == (path / 'constants-1.bin').read_bytes(), '011 packed atlas pair differs')
    f = np.frombuffer(packed, dtype='<f4')
    p0, p1, p2, p3, p4 = struct.unpack_from('<5I', packed, 92)
    baseline = (F.S.paths('scene-one')[1] / 'capture/constants-0.bin').read_bytes()
    R.require(np.array_equal(f[:3], origin) and f[3] == 0 and np.array_equal(f[20:23], spacing)
              and tuple(map(float, f[12:19])) == (cfg['ray_max'], bias, bias, 50., 1., 1e6, 1e6), '011 packed floats differ')
    R.require(packed[16:48] == baseline[16:48] and p0 == (case.side | (case.side << 10) | (case.side << 20))
              and p2 == (case.rays | (6 << 16) | (14 << 24)) and p3 == 0 and p4 == struct.unpack_from('<I', baseline, 108)[0], '011 packed rotation/count/format/features differ')
    units = Q.check_units([json.loads(x) for x in (path / 'dispatches.jsonl').read_text().splitlines()], unit_labels(case))
    pixels = np.fromfile(path / 'pixels.f32', dtype='<f4').reshape(180, 320, 4)
    R.require(np.isfinite(pixels).all() and (pixels[..., 3] == 1).all(), '011 nonfinite/incomplete pixels')
    for j, component in enumerate(('direct', 'indirect', 'total')):
        R.require(np.array_equal(R.Q.L.read_pfm(path / (component + '.pfm')), np.repeat(pixels[..., j, None], 3, axis=2)), '011 raw/PFM differs')
    R.require(np.array_equal(pixels[..., 2], pixels[..., 0] + pixels[..., 1]), '011 linear composite differs')
    direct = D.source_direct() if state_path == F.SOURCE else R.Q.L.read_sidecar(state_path / 'cpu-direct-v1/oracle.s0.f64')['mean'][..., R.Q.L.COMPONENTS.index('direct'), :] @ S.LUMA
    metrics = S.metrics(pixels[..., 0], direct)
    R.require(metrics['whole_image_max_absolute'] <= 1e-5 and metrics['nrmse'] is not None and metrics['nrmse'] <= 1e-4, '011 physical direct oracle mismatch')
    R.require((path / 'direct.pfm').read_bytes() == (old_path / 'direct.pfm').read_bytes(), '011 correction changed old primary/direct output')
    R.require(packed == (old_path / 'constants-0.bin').read_bytes(), '011 correction changed old packed constants')
    copies = []
    for k in range(case.depth - 1):
        for role, indices in (('current', range(4)), ('previous', range(1, 4))):
            for j in indices:
                p = path / f'stage-{k}-{role}-{j}.f32'
                a = atlas(p, cfg['images'][j])
                if role == 'previous':
                    if k:
                        R.require(R.sha(p) == R.sha(path / f'stage-{k-1}-current-{j}.f32'), '011 immutable previous stage changed')
                    else:
                        R.require((a.view('<u4') == 0).all(), '011 initial history not exactly +0')
                    if j in (1, 2):
                        R.require(C.check_atlas(a, 8 if j == 1 else 16, case.side)['exact_copy_pass'], '011 previous atlas border failed')
                elif j == 3:
                    R.require((a == 0).all(), '011 disabled probe metadata changed')
        for j, tile in ((1, 8), (2, 16)):
            before = atlas(path / f'stage-{k}-pre-border-{j}.f32', cfg['images'][j])
            after = atlas(path / f'stage-{k}-current-{j}.f32', cfg['images'][j])
            copies.append(dict(stage=k, type=j, **C.check_copy(before, after, tile, case.side)))
        if case.mode in ('constant0', 'constant1', 'constant8'):
            radiance = {'constant0': 0, 'constant1': 1, 'constant8': 8}[case.mode]
            for j, value in ((0, radiance), (1, radiance * .5), (2, .5)):
                a = atlas(path / f'stage-{k}-current-{j}.f32', cfg['images'][j]).reshape(-1, cfg['images'][j]['channels'])
                checked = a[:, :3] if j < 2 else a
                R.require(float(np.max(np.abs(checked - value))) <= 1e-5, '011 constant normalization/HDR clamp failed')
    if case.depth > 1:
        for j in range(4):
            new = atlas(path / f'stage-0-current-{j}.f32', cfg['images'][j])
            old = atlas(old_path / f'stage-0-current-{j}.f32', cfg['images'][j])
            if j in (1, 2):
                tile = 8 if j == 1 else 16
                R.require(np.array_equal(interior_bits(new, tile, case.side), interior_bits(old, tile, case.side)), '011 changed old stage0 interior blend math')
            else:
                R.require(np.array_equal(new.view('<u4'), old.view('<u4')), '011 changed old stage0 ray/probe data')
    if case.mode in ('direct', 'constant0'):
        R.require((pixels[..., 1] == 0).all(), '011 direct/black field leaked indirect')
    if case.name == 'static-hdr':
        unit = np.fromfile(F.get_case('static-unit').work / 'capture/pixels.f32', dtype='<f4').reshape(180, 320, 4)
        R.require(np.max(unit[..., 1]) > 0 and np.allclose(pixels[..., 1], 8 * unit[..., 1], rtol=1e-5, atol=2e-6), '011 HDR gather 8x linearity failed')
    if case.name == 'static-scene-seven' or (case.family == 'integrity' and case.depth == 8):
        one = F.get_case('static-scene-one') if case.family == 'static' else F.get_case(case.name.removesuffix('b8') + 'b2')
        root = one.work / 'capture'
        for j in range(4):
            R.require(R.sha(path / f'stage-0-current-{j}.f32') == R.sha(root / f'stage-0-current-{j}.f32'), '011 corrected B2/B8 stage0 differs')
    return dict(configuration=cfg, timing=units, direct_metrics=metrics, copies=copies, previous_atlas_immutable=True,
                initial_history_exactly_zero=True, old_stage0_rays_and_interiors_unchanged=True,
                old_primary_direct_unchanged=True, quality_scoring=False)


def audit(case):
    members = archive_members(case.archive)
    R.require(members['plan.json'] == case.plan.read_bytes() and members['result.json'] == (case.work / 'result.json').read_bytes(), '011 compact proof bytes differ')
    plan, result = json.loads(members['plan.json']), json.loads(members['result.json'])
    R.require(plan['name'] == result['name'] == case.name and plan['case'] == asdict(case) and plan['command'] == result['command'] == F.command(case)
              and result['plan_sha256'] == R.sha(case.plan) and result['semantic_admission'] is False and result['quality_admission'] is False
              and result['accepted_timing'] is False and plan['quality_scoring'] is False, '011 receipt scope/admission differs')
    validate_inventory(case.work, result['payload_sha256'])
    R.require(R.read(case.work / 'started.json') == dict(plan_sha256=R.sha(case.plan), plan=plan), '011 started receipt differs')
    if not result['complete']:
        R.require(result['classification'] == 'OPERATIONAL_FAILURE_RETAIN_PARTIAL_NO_RETRY', '011 failed process misclassified')
        return dict(name=case.name, classification='OPERATIONAL_FAILURE_RETAINED', semantic_pass=False, result_sha256=R.sha(case.work / 'result.json'),
                    archive_sha256=R.sha(case.archive), raw_payloads_rehashed=len(result['payload_sha256']), error=result.get('error'), gpu_executed_by_auditor=False, accepted_timing=False)
    R.require(result['returncode'] == 0 and result['gpu_executed'] is True and result['classification'] == 'RAW_BORDER_CONTROL_RETAINED_AUDIT_REQUIRED', '011 successful native evidence missing')
    for p, h in plan['input_sha256'].items():
        R.require(R.sha(Path(p)) == h, '011 planned input drift: ' + p)
    commit = plan['source_commit']
    R.require(subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=R.ROOT, capture_output=True).returncode == 0, '011 source commit unreachable')
    import ddgi_border_step as Step
    for p in Step.tracked_sources():
        R.require(hashlib.sha256(subprocess.check_output(['git', 'show', commit + ':' + str(p.relative_to(R.ROOT))], cwd=R.ROOT)).hexdigest() == plan['input_sha256'][str(p)], '011 source/protocol not committed')
    inputs = {}
    references = Q.F.verify_references(inputs)
    R.require(references == plan['reference_verification'], '011 original reference admission/provenance differs')
    R.require(F.D.audit_states() == plan['dynamic_states'] and {k: F.D.audit_oracle(k) for k in ('light', 'geometry')} == plan['dynamic_direct_controls'], '011 dynamic CPU states/direct controls differ')
    capture = case.work / 'capture'
    complete = R.read(capture / 'complete.json')
    R.require(complete['capture_complete'] and complete['quality_admission'] is False and complete['speed_admission'] is False and complete['semantic_admission'] is False, '011 native falsely admitted itself')
    allocation = memory(R.read(capture / 'allocation-ledger.json'))
    ledger = R.read(capture / 'allocation-ledger.json')
    images = [x for x in ledger['events'] if x['action'] == 'allocate' and x['buffer_usage'] == 15]
    R.require(len(images) == 12 and all(x['phase'] == 'startup' for x in images), '011 persistent atlas pair missing/reallocated')
    for j, layout in enumerate(Q.layouts(case.side, case.rays) * 2):
        R.require(images[j]['bytes'] >= layout['w'] * layout['h'] * layout['layers'] * layout['channels'] * 4, '011 allocation smaller than full image')
    old = old_work(case) / 'capture'
    if not case.transition:
        frames = [frame_report(case, capture, case.state, old)]
        R.require(R.read(capture / 'cpu-contract.json') == R.read(F.CPU / case.name / 'capture/cpu-contract.json'), '011 actual static CPU contract differs')
    else:
        R.require(R.read(capture / 'transition-contract.json') == R.read(F.CPU / case.name / 'capture/transition-contract.json') and complete['history_policy'] == 'reset-all' and complete['frames'] == 4, '011 actual transition schedule differs')
        sequence = [json.loads(x) for x in (capture / 'sequence.jsonl').read_text().splitlines()]
        expected = F.expected_schedule(case.kind, case.depth)
        R.require(len(sequence) == 4, '011 transition frame journal incomplete')
        frames = []
        fresh = F.get_case(f'dynamic-{case.kind}-fresh-b{case.depth}').work / 'capture'
        source = F.get_case('static-scene-one' if case.depth == 2 else 'static-scene-seven').work / 'capture'
        for k, step in enumerate(expected):
            event = sequence[k]
            R.require(event['frame'] == k and event['state_index'] == step['state_index']
                      and event['reset_both_atlases'] is True and event['moved_primitives'] == step['moved_primitives'], '011 transition frame/update journal differs')
            times = ('geometry_upload_gpu_us_diagnostic', 'geometry_upload_wall_us', 'blas_update_wall_us', 'tlas_update_wall_us')
            R.require(all(np.isfinite(event[key]) and event[key] >= 0 for key in times + ('frame_setup_update_wall_us', 'frame_complete_wall_us')), '011 invalid update diagnostics')
            R.require(all(event[key] > 0 if step['moved_primitives'] else event[key] == 0 for key in times), '011 missing/extra actual AS update diagnostics')
            frame = capture / 'frames' / str(k)
            state = F.D.WORK / case.kind if k in (1, 2) else F.SOURCE
            frames.append(frame_report(case, frame, state, old / 'frames' / str(k)))
            same_frame(frame, fresh if k in (1, 2) else source, case)
        same_frame(capture / 'frames/0', capture / 'frames/3', case)
        R.require(any(R.sha(capture / 'frames/0' / n) != R.sha(capture / 'frames/1' / n) for n in ('direct.pfm', 'stage-0-current-0.f32')), '011 changed-state check vacuous')
        R.require(len(ledger['events']) == (64 if case.kind == 'geometry' else 56), '011 transition allocation schedule differs')
        image_events = [x for x in ledger['events'] if x['buffer_usage'] == 15]
        R.require(len(image_events) == 24 and all(x['phase'] == ('startup' if x['action'] == 'allocate' else 'primary-direct-gather') for x in image_events), '011 persistent atlas lifetime differs')
    return dict(schema='m001-ddgi-separated-border-independent-cpu-audit/1', name=case.name, classification='BORDER_CONTROL_PASS',
                semantic_pass=True, result_sha256=R.sha(case.work / 'result.json'), archive_sha256=R.sha(case.archive),
                raw_payloads_rehashed=len(result['payload_sha256']), frames=frames, owned_memory=allocation,
                full_copy_exact=True, interior_unchanged=True, old_stage0_rays_and_interiors_unchanged=True,
                gpu_executed_by_auditor=False, quality_scoring=False, quality_admission=False, accepted_timing=False,
                scope='Named011 correctness control only; no indirect HDR quality decision, general dynamics, temporal support or speed claim')

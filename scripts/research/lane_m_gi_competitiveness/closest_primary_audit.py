#!/usr/bin/env python3
"""013 independent full raw/reference/physical/primary/HDR intake. Never run GPU."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess

import numpy as np
import closest_primary_step as F
import closest_primary_metrics as M
import audit_first_pt_quality as A
import fixed_rc_step as Fixed
import score_hdr as S
from audit_h01_evidence import memory

R, C, K = F.R, F.C, F.K


def validate_images(capture):
    images = {}
    for name in ('direct', 'indirect', 'total'):
        image = R.Q.L.read_pfm(capture / 'gpu' / f'{name}.pfm')
        R.require(image.shape == (180, 320, 3) and np.isfinite(image).all() and (image >= 0).all(),
                  '013 invalid physical PFM shape/value')
        R.require(np.array_equal(image[..., 0], image[..., 1]) and np.array_equal(image[..., 0], image[..., 2]),
                  '013 BF-P scalar channels differ')
        images[name] = image
    R.require(np.array_equal((images['direct'] + images['indirect']).astype(np.float32), images['total']),
              '013 native total does not equal F32 direct+indirect')
    return images


def validate_capture(case, capture, refs):
    expected = Fixed.REQUIRED | ({'gpu/primary-geometry.bin'} if case.backend == 'software' else set())
    actual = {str(p.relative_to(capture)) for p in capture.rglob('*') if p.is_file()}
    R.require(actual == expected, '013 missing/extra native capture payload')
    state = R.Q.L.read_state(capture)
    R.require((state['width'], state['height']) == (320, 180) and (state['meta'][:, 3] == 1).all(),
              '013 viewport/BF-P physical state differs')
    meta = R.read(capture / 'capture.json')
    target = case.cell == 'C1'
    R.require((meta['schema_version'], meta['scenario'], meta['backend'], meta['target_state'],
               meta['frame_id'], meta['spp'], meta['width'], meta['height'], meta['triangles'], meta['work_overflow'])
              == (1, 'static', case.backend, target, 2 if target else 1, 512, 320, 180,
                  262241 if target else 1248 if case.cell == 'H03' else 1224, 0), '013 native metadata differs')
    count = meta['work_items']
    R.require(type(count) is int and count > 0, '013 native work counter invalid')
    for name, size in [('probe-work.bin', 64*count), ('probe-hits.bin', 32*count),
                       ('probe-contributions.bin', 8*count), ('composite-lookup.bin', 80*57600),
                       ('hits.bin', 32*57600)]:
        R.require((capture / 'gpu' / name).stat().st_size == size, '013 native buffer byte count differs: ' + name)
    for depth, proof in refs.items():
        qual = R.read(Path(proof['directory']) / 'qualification.json')
        R.require(state['sha256'] == qual['state_sha256'], '013 frozen physical state byte mismatch')
        canonical = R.Q.scene_for_state(state, int(depth)).text().encode()
        R.require(hashlib.sha256(canonical).hexdigest() == qual['scene_sha256']
                  and canonical == (Path(proof['directory']) / 'scene.n008').read_bytes(),
                  '013 full canonical physical scene mismatch')
    if case.backend == 'software':
        raw = (capture / 'gpu/primary-geometry.bin').read_bytes()
        dtype = np.dtype([('v', '<f4', (3, 4)), ('meta', '<u4', (4,))])
        R.require(len(raw) == len(state['meta'])*64, '013 actual software primary geometry size differs')
        triangles = np.frombuffer(raw, dtype=dtype)
        R.require(np.isfinite(triangles['v']).all()
                  and np.array_equal(triangles['v'][:, :, :3], state['verts'])
                  and np.array_equal(triangles['meta'], state['meta']), '013 actual software GPU geometry differs')
    timing = [json.loads(line) for line in (capture / 'renderer-timings.jsonl').read_text().splitlines()]
    R.require([x['state'] for x in timing] == (['source', 'first-target'] if target else ['source']),
              '013 complete native frame sequence differs')
    for row in timing:
        R.require(row['classification'] == 'DIAGNOSTIC_UNCALIBRATED' and row['overflow'] == 0
                  and row['moved_primitives'] == 0 and row['topology_mutations'] == 0,
                  '013 timing/native static state metadata differs')
        R.require(all(math.isfinite(v) and v >= 0 for k, v in row.items() if k.endswith('_us')),
                  '013 native diagnostic timing invalid')
    owned = memory(R.read(capture / 'allocation-ledger.json'))
    R.require(owned['events'] > 0 and owned['true_peak_owned_bytes'] > 0, '013 empty owned allocation proof')
    return state, owned, timing


def reconstructed_positions(state, scene, gpu, oracle):
    """Diagnostic CPU reconstructions, never exact exported GPU origins/positions."""
    x, y = np.meshgrid(np.arange(320, dtype=np.float32), np.arange(180, dtype=np.float32))
    nx = np.float32(2) * ((x + np.float32(.5)) / np.float32(320)) - np.float32(1)
    ny = np.float32(1) - np.float32(2) * ((y + np.float32(.5)) / np.float32(180))
    # Match the specified float expression; actual shader contraction/rounding
    # may differ. These positions do not gate primary-depth or image decisions.
    direction = (state['camera_forward_far'][:3] + state['camera_right_tan_x'][:3] *
                 (nx * state['camera_right_tan_x'][3])[..., None] + state['camera_up_tan_y'][:3] *
                 (ny * state['camera_up_tan_y'][3])[..., None])
    direction /= np.linalg.norm(direction, axis=2, keepdims=True)
    origin, reference_direction = R.Q.L.camera_rays(scene.camera, 320, 180)
    g_hit, r_hit = gpu['flag'] == 1, oracle['tri'] != M.INVALID
    g_pos = np.zeros((57600, 3), dtype=np.float64)
    r_pos = np.zeros((57600, 3), dtype=np.float64)
    g_pos[g_hit] = (state['camera_pos_near'][:3] + direction.reshape(-1, 3)[g_hit] * gpu['t'][g_hit, None]).astype(np.float64)
    r_pos[r_hit] = origin + reference_direction.reshape(-1, 3)[r_hit] * oracle['t'][r_hit, None]
    both = g_hit & r_hit
    delta = np.zeros(57600, dtype=np.float64)
    delta[both] = np.linalg.norm(g_pos[both] - r_pos[both], axis=1)
    R.require(np.isfinite(g_pos).all() and np.isfinite(r_pos).all() and np.isfinite(delta).all(), '013 reconstructed position nonfinite')
    return dict(compared_both_hit_pixels=int(both.sum()), position_difference_pixels=int((both & (delta != 0)).sum()),
                maximum_position_distance=float(delta.max()), exact_gpu_positions_exported=False), {
                    'gpu_position_reconstructed': g_pos, 'reference_position': r_pos, 'position_distance': delta}


def score_capture(case, capture, refs):
    """Pure intake: return full reports/maps for subsequent immutable save/replay."""
    state, owned, timing = validate_capture(case, capture, refs)
    images = validate_images(capture)
    gpu = np.frombuffer((capture / 'gpu/hits.bin').read_bytes(), dtype=M.GPU_DTYPE)
    rows, arrays = {}, {}
    for depth, proof in refs.items():
        ref = Path(proof['directory'])
        q = R.read(ref / 'qualification.json')
        spp = q['levels'][-1]['spp']
        raw_hits = (ref / f'o.n{spp}.hits').read_bytes()
        R.require(raw_hits[:8] == b'N008HIT\0' and struct.unpack_from('<II', raw_hits, 8) == (320, 180)
                  and len(raw_hits) == 16 + 16*57600, '013 reference primary ABI/coverage differs')
        oracle = np.frombuffer(raw_hits, dtype=M.ORACLE_DTYPE, offset=16)
        primary, primary_arrays = M.primary(gpu, oracle, state['meta'], state['verts'], float(state['camera_forward_far'][3]))
        scene = R.Q.scene_for_state(state, int(depth))
        positions, position_arrays = reconstructed_positions(state, scene, gpu, oracle)
        primary.update(positions)
        arrays[f'primary-b{depth}.npz'] = dict(primary_arrays, **position_arrays)
        means = np.mean([R.Q.L.read_sidecar(ref / f'o.n{spp}.s{i}.f64')['mean'] for i in range(4)], axis=0)
        components = {}
        luminance = {}
        for component in ('direct', 'indirect', 'total'):
            g = images[component] @ S.LUMA
            r = means[..., R.Q.L.COMPONENTS.index(component), :] @ S.LUMA
            components[component] = S.metrics(g, r)
            arrays[f'quality-b{depth}.{component}.error.npy'] = g-r
            luminance[component] = (g.ravel(), r.ravel())
        named = []
        if case.cell == 'C1':
            for x, y, primitive in [(107, 109, 51389), (261, 161, 172941)]:
                at = y*320+x
                R.require(int(primary_arrays['reference_primitive'][at]) == primitive, '013 frozen C1 named reference changed')
                named.append(dict(x=x, y=y, id=at, gpu_primitive=int(gpu['prim'][at]),
                                  reference_primitive=primitive, gpu_direct=float(luminance['direct'][0][at]),
                                  reference_direct=float(luminance['direct'][1][at])))
        decision = M.classify(primary, components, named)
        rows[depth] = dict(decision, primary=primary, components=components, named_pixels=named,
                           reference_verification=proof, finite_depth_equivalent=False)
    decision = 'PASS' if all(x['classification'] == 'PASS' for x in rows.values()) else 'CORRECTNESS_FAIL'
    return dict(classification=decision, correctness_evidence_valid=True, rows=rows, owned_memory=owned,
                diagnostic_timing=timing, accepted_timing=False), arrays


def save_or_replay(p, report, arrays, save):
    if save:
        R.require(not p.scores.exists(), '013 independent score output exists; no overwrite')
        p.scores.mkdir(parents=True)
        for name, array in arrays.items():
            if name.endswith('.npz'):
                with (p.scores / name).open('xb') as handle: np.savez(handle, **array)
            else:
                with (p.scores / name).open('xb') as handle: np.save(handle, array, allow_pickle=False)
        report['derived_sha256'] = {name: C.sha(p.scores / name) for name in arrays}
        R.write_new(p.scores / 'result.json', report)
    else:
        saved = R.read(p.scores / 'result.json')
        R.require({str(x.relative_to(p.scores)) for x in p.scores.rglob('*') if x.is_file()}
                  == set(arrays) | {'result.json'}, '013 missing/extra saved audit payload')
        R.require(set(saved.get('derived_sha256', {})) == set(arrays), '013 missing/extra saved full maps')
        for name, array in arrays.items():
            path = p.scores / name
            R.require(C.sha(path) == saved['derived_sha256'][name], '013 saved full map hash changed')
            if name.endswith('.npz'):
                with np.load(path, allow_pickle=False) as loaded:
                    R.require(set(loaded.files) == set(array) and all(loaded[k].dtype == a.dtype and np.array_equal(loaded[k], a) for k, a in array.items()),
                              '013 full primary comparison array replay differs')
            else:
                loaded = np.load(path, allow_pickle=False)
                R.require(loaded.dtype == array.dtype and np.array_equal(loaded, array), '013 full f64 error-map replay differs')
        report['derived_sha256'] = saved.get('derived_sha256', {})
        R.require(saved == report, '013 independently recomputed report differs')
    return dict(report, derived_record_sha256=C.sha(p.scores / 'result.json'))


def audit(case, save=False):
    p = F.Paths(case)
    R.require(p.plan.is_file() and (p.work / 'result.json').is_file() and p.archive.is_file(),
              '013 terminal proof incomplete; never infer success/retry')
    members = A.archive_members(p.archive)
    R.require(members['plan.json'] == p.plan.read_bytes() and members['result.json'] == (p.work / 'result.json').read_bytes(),
              '013 archive/local terminal bytes differ')
    plan, result = R.read(p.plan), R.read(p.work / 'result.json')
    R.require(plan['schema'] == 'm001-closest-primary-plan/1' and result['schema'] == 'm001-closest-primary-result/1'
              and plan['scope'] == dict(cell=case.cell, backend=case.backend)
              and result['plan_sha256'] == C.sha(p.plan) and result['accepted_timing'] is False
              and result['command'] == plan['command'] and result['gpu_executed'] is True
              and type(result['complete']) is bool and plan['gpu_executed'] is False
              and plan['accepted_timing'] is False and plan['contract'] == str(K.CONTRACT),
              '013 terminal plan/scope identity differs')
    A.validate_inventory(p.work, result['payload_sha256'])
    R.require(R.read(p.work / 'started.json') == dict(plan_sha256=C.sha(p.plan), plan=plan), '013 started identity differs')
    report = dict(schema='m001-closest-primary-independent-cpu-audit/1', scope=plan['scope'],
                  plan_sha256=C.sha(p.plan), result_sha256=C.sha(p.work / 'result.json'), archive_sha256=C.sha(p.archive),
                  raw_payloads_rehashed=len(result['payload_sha256']), gpu_executed_by_auditor=False,
                  accepted_timing=False)
    if not result['complete']:
        R.require(result['classification'] == 'OPERATIONAL_FAILURE_RETAINED_STOP', '013 incomplete result falsely classified')
        report.update(classification='OPERATIONAL_FAILURE_RETAINED_STOP', correctness_evidence_valid=False, error=result.get('error'))
        return save_or_replay(p, report, {}, save)
    R.require(result['classification'] == 'RAW_CAPTURE_RETAINED_INDEPENDENT_AUDIT_REQUIRED'
              and result['returncode'] == 0 and result['timed_out'] is False, '013 native success absent')
    F.rehash(plan['input_sha256'])
    source = plan['source_commit']
    R.require(len(source) == 40 and subprocess.run(['git', 'merge-base', '--is-ancestor', source, 'HEAD'], cwd=C.ROOT).returncode == 0,
              '013 plan source not a reachable ancestor')
    for path, digest in plan['input_sha256'].items():
        file = Path(path).resolve()
        if file.is_relative_to(C.ROOT / 'scripts/research'):
            R.require(hashlib.sha256(subprocess.check_output(['git', 'show', source + ':' + str(file.relative_to(C.ROOT))], cwd=C.ROOT)).hexdigest() == digest,
                      '013 consumed source differs from committed acquisition version')
    inputs = {}
    binary = F.build_and_cpu(inputs)
    F.process_gate(inputs)
    refs = F.reference_inputs(case, inputs)
    R.require(refs == plan['reference_verification'] and plan['command'] == K.command(case, binary, p.capture),
              '013 native command/reference drift')
    measured, arrays = score_capture(case, p.capture, refs)
    report.update(measured)
    return save_or_replay(p, report, arrays, save)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cell', required=True, choices=['C1', 'H01', 'H02', 'H03'])
    ap.add_argument('--backend', required=True, choices=['hwrt', 'software'])
    ap.add_argument('--save', action='store_true')
    args = ap.parse_args()
    result = audit(K.Case(args.cell, args.backend), save=args.save)
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'diagnostic_timing', 'derived_sha256')}, indent=2))

#!/usr/bin/env python3
"""032 process/identity correction; unchanged031 native sampler and numerical helpers."""
import argparse
from pathlib import Path
import json
import os
import resource
import subprocess
import sys
import time
import numpy as np
import anchor_path_difference as L
import anchor_process_limits as C

B, K, ROOT, BASE = L.B, L.K, L.ROOT, L.BASE
TARGETS, BUILD, SEEDS, PRIMARY = L.TARGETS, L.BUILD, L.SEEDS, L.PRIMARY
P, S = L.P, L.S
PROTOCOL = ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/032-anchor-process-limit-correction.md'
OWN = [PROTOCOL]+[Path(__file__).with_name(n) for n in ('anchor_process_limits.py', 'anchor_path_difference_corrected.py', 'anchor_path_difference_corrected_audit.py', 'test_anchor_process_limits.py')]
PREPARATION = BASE/'m001-anchor032-cpu-contracts-v1/result.json'
limits, guarded, write = C.limits, C.guarded, C.write
reserve, phase, intake, geometry_data = L.reserve, L.phase, L.intake, L.geometry_data
raw_seed, query_totals, aggregate, reference = L.raw_seed, L.query_totals, L.aggregate, L.reference


def committed():
    head = L.committed()
    subprocess.run(['git', 'merge-base', '--is-ancestor', 'f1620af5', head], check=True)
    for p in OWN:
        K.need(subprocess.check_output(['git', 'show', head+':'+str(p.relative_to(ROOT))]) == p.read_bytes(), '032 commit complete correction before execution')
    for p in L.OWN:
        K.need(subprocess.check_output(['git', 'show', '2ba1cb84:'+str(p.relative_to(ROOT))]) == p.read_bytes(), '032 preserve all031 source/physical bytes')
    return head


def tag(cell, depth):
    K.need((cell, depth) in TARGETS, '032 unregistered target')
    return f'm001-anchor032-{cell.lower()}-b{depth}'


def previous(cell, depth, base=None):
    base = base or BASE; tag(cell, depth); pins = {}
    for c, d in TARGETS[:TARGETS.index((cell, depth))]:
        p = base/(tag(c, d)+'-audit-v1/result.json'); a = B.read(p)
        K.need(a['complete'] and a['valid'] and a['all_pass'] and (a['cell'], a['depth']) == (c, d), '032 prior audit invalid/missing')
        native = Path(a['native_receipt']); n = B.read(native)
        K.need(B.SHA(native) == a['native_receipt_sha256'] and n['complete'] and n['valid'], '032 prior native identity')
        pins[str(p)] = B.SHA(p); pins[str(native)] = B.SHA(native)
    B.rehash(pins); return pins


def frozen_geometry(info, out, pins):
    published = ROOT/'research/lanes/lane-m-gi-competitiveness/results/200-surface-anchor-coupled-path-first-launch-failure.json'
    K.need(subprocess.check_output(['git', 'show', 'fa5c60a1:'+str(published.relative_to(ROOT))]) == published.read_bytes(), '032 published031 failure identity')
    old = B.read(published); native = Path(old['native_receipt'])
    verification = published.with_name('202-surface-anchor-coupled-path-first-failure-verification.json')
    K.need(subprocess.check_output(['git', 'show', 'fa5c60a1:'+str(verification.relative_to(ROOT))]) == verification.read_bytes(), '032 published031 preservation identity')
    K.need(B.read(verification)['all_eight_frozen_geometry_artifacts'] == old['geometry_artifact_sha256'], '032 exact eight-artifact anchors')
    K.need(B.SHA(native) == old['native_receipt_sha256'], '032 failed031 native exact')
    n = B.read(native); K.need(not n['valid'] and not (native.parent/'paths').exists(), '032031 stays stopped before paths')
    B.rehash(n['input_sha256']); B.rehash({str(native.parent/k): h for k, h in n['payload_sha256'].items()})
    pins.update(n['input_sha256']); pins[str(published)] = B.SHA(published); pins[str(native)] = B.SHA(native)
    pins[str(verification)] = B.SHA(verification)
    pins.update(old['geometry_artifact_sha256'])
    frozen = native.parent/'geometry-frozen.json'; pins[str(frozen)] = B.SHA(frozen)
    B.rehash(pins)
    phase(out, 'original031-geometry-reuse-before', pins, geometry_generated_again=False, original031_stopped=True)
    return native.parent/'geometry'


def contracts(out):
    head = committed(); out = reserve(out, PREPARATION.parent)
    pins = {str(p): B.SHA(p) for p in [*OWN, *L.OWN, *P.OWN, *B.OWN]}
    r = dict(schema='m001-anchor032-process-contracts/1', source_commit=head, complete=False, all_pass=False,
             gpu_executed=False, input_sha256=pins, native_recompiled=False, old_suites_repeated=False)
    try:
        r['effective_parent_limits'] = limits(); phase(out, 'contracts-before', pins)
        old = BUILD/'result.json'; q = B.read(old)
        K.need(q['complete'] and q['all_pass'] and q['python_contract_count'] == 6 and q['native_contracts']['original_counted_path_comparisons'] == 2048, '032 reuse qualified031 exact build/contracts')
        B.rehash(q['input_sha256']); B.rehash(q['compiled_dependency_sha256']); B.rehash({str(BUILD/k): h for k, h in q['payload_sha256'].items()})
        K.need(B.inventory(BUILD) == q['payload_sha256'], '032 old build inventory exact')
        pins[str(old)] = B.SHA(old); pins[str(BUILD/'anchor_path_difference_cpu')] = q['native_executable_sha256']
        r.update(compiled_dependency_sha256=q['compiled_dependency_sha256'], native_executable_sha256=q['native_executable_sha256'],
                 reused031_native_contracts=q['native_contracts'], reused031_python_contracts=6, reused030_signed_contracts=15)
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', str(Path(__file__).parent), '-p', 'test_anchor_process_limits.py', '-v']
        env = dict(os.environ, VK_ICD_FILENAMES='/032-unusable-icd.json', VK_DRIVER_FILES='/032-unusable-icd.json')
        run = subprocess.run(command, capture_output=True, text=True, env=env, timeout=500)
        (out/'stdout.txt').write_text(run.stdout); (out/'stderr.txt').write_text(run.stderr)
        r.update(command=command, returncode=run.returncode, python=sys.version, numpy=np.__version__)
        K.need(run.returncode == 0 and '\nOK\n' in run.stderr, '032 actual limit/exec contracts failed')
        import re
        r['new_contract_count'] = int(re.search(r'Ran (\d+) tests?', run.stderr)[1])
        B.rehash(pins); B.rehash(q['compiled_dependency_sha256'])
        B.rehash({str(BUILD/k): h for k, h in q['payload_sha256'].items()})
        r.update(complete=True, all_pass=True)
    except Exception as e: r['error'] = type(e).__name__+': '+str(e)
    r['payload_sha256'] = B.inventory(out); write(out/'result.json', r); return r


def case(cell, depth, out):
    head = committed(); prior = previous(cell, depth)
    prep = B.read(PREPARATION); K.need(prep['complete'] and prep['all_pass'], '032 CPU preparation required')
    B.rehash(prep['input_sha256']); B.rehash(prep['compiled_dependency_sha256']); B.rehash({str(PREPARATION.parent/k): h for k, h in prep['payload_sha256'].items()})
    out = reserve(out, BASE/(tag(cell, depth)+'-v1')); pins = {str(p): B.SHA(p) for p in [*OWN, *L.OWN]}; pins.update(prior)
    pins[str(PREPARATION)] = B.SHA(PREPARATION); pins[str(BUILD/'anchor_path_difference_cpu')] = prep['native_executable_sha256']
    r = dict(schema='m001-anchor032-cpu-case/1', cell=cell, depth=depth, source_commit=head, complete=False, valid=False,
             classification='INVALID_STOP_NO_RETRY', gpu_executed=False, accepted_timing=False, input_sha256=pins, commands=[])
    started = time.monotonic()
    try:
        r['effective_parent_limits'] = limits()
        info = intake(cell, depth, out, pins); exe = str(BUILD/'anchor_path_difference_cpu')
        reused = (cell, depth) == ('H01', 2)
        if reused:
            geo_dir = frozen_geometry(info, out, pins)
            with np.load(geo_dir/'field.npz') as z: geo = {k: z[k] for k in z.files}
        else:
            geo_dir = out/'geometry'
            phase(out, 'geometry-before', pins, radiance_sampled=False)
            r['commands'].append(guarded([exe, 'geometry', '--scene', str(info['scene']), '--out', str(geo_dir)], out, 'geometry', cpu=120, wall=180))
            geo = geometry_data(info, geo_dir)
            for name, array in [('groups.i64', geo['groups'].astype('<i8')), ('anchors.u32', geo['anchors'])]:
                with (geo_dir/name).open('xb') as f: array.tofile(f)
            np.savez(geo_dir/'field.npz', **geo)
        from anchor_path_difference_audit import independent_groups
        groups, anchors, active = independent_groups(info, geo_dir)
        K.need(np.array_equal(groups, geo['groups']) and np.array_equal(anchors, geo['anchors']), '032 independent geometry before paths')
        geometry_pins = {str(geo_dir/k): h for k, h in B.inventory(geo_dir).items()}; pins.update(geometry_pins)
        phase(out, 'geometry-independent-before-paths', pins, all_groups=len(anchors), all_pixels=57600, radiance_sampled=False)
        phase(out, 'geometry-frozen', pins, all_geometry_frozen_before_radiance=True, geometry_directory=str(geo_dir), original031_reuse=reused)
        r.update(geometry_directory=str(geo_dir), original031_geometry_reused=reused,
                 actual_new_geometry_queries=0 if reused else 57600, charged_required_geometry_scan_queries=57600)
        pins[str(out/'geometry-frozen.json')] = B.SHA(out/'geometry-frozen.json')
        phase(out, 'paths-before', pins, reference_radiance_decoded=False)
        r['commands'].append(guarded([exe, 'paths', '--scene', str(info['scene']), '--geometry', str(geo_dir), '--out', str(out/'paths')], out, 'paths'))
        native = B.read(out/'paths/paths.json'); K.need(native['complete'] and native['pairs'] == 16 and native['absolute'] == 1024 and native['groups'] == len(geo['keys']), '032 native path boundary')
        images, efficiency, variances, queries = aggregate(out/'paths', geo['groups'])
        for i, q in enumerate(queries):
            K.need(native['rows'][i] == dict(seed=SEEDS[i], **q), '032 native complete role queries')
        np.savez(out/'images.npz', **images); np.savez(out/'variances.npz', **variances)
        path_pins = {str(out/'paths'/k): h for k, h in B.inventory(out/'paths').items()}; pins.update(path_pins)
        pins.update({str(out/k): B.SHA(out/k) for k in ('images.npz', 'variances.npz')})
        phase(out, 'candidate-frozen', pins, reference_radiance_decoded=False)
        ref = reference(info, out); scores = []; errors = {}
        for i, seed in enumerate(SEEDS):
            row, maps = S.score({k: images[k][i] for k in ('baseline', 'signed', 'clipped')}, images['direct'][i], ref)
            scores.append(dict(seed=seed, roles=row)); errors.update({f'seed{i}_{k}': v for k, v in maps.items()})
        np.savez(out/'full-hdr-errors.npz', **errors)
        passed = efficiency['pass_'] and all(x['roles'][k]['pass_'] for x in scores for k in ('signed', 'clipped'))
        r.update(complete=True, valid=True, pass_=bool(passed), classification='CPU_FEASIBILITY_PASS' if passed else 'REJECTED_NO_GPU',
                 efficiency=efficiency, scores=scores, groups=len(geo['keys']), active_pixels=int(geo['active'].sum()), all_pixels=57600,
                 scoring_exclusions=0, seeds=list(SEEDS), pairs_per_pixel_per_seed=16, absolute_per_anchor_per_seed=1024,
                 candidate_path_calls=4*(int(geo['active'].sum())*32+len(geo['keys'])*1024), baseline_path_calls=4*int(geo['active'].sum())*32,
                 complete_cpu_query_counts=True, extra_control_samples_per_pixel_per_seed=16, old_successful_tests_or_032_paths_repeated=False,
                 representative_geometry_selection_before_radiance=True, reference_read_after_candidate_freeze=True,
                 finite_rng_unbiasedness_proven=False, clipping_claimed_unbiased=False, new_reference_samples=0,
                 cpu_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                 child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        B.rehash(pins)
    except Exception as e: r['error'] = type(e).__name__+': '+str(e)
    r['diagnostic_cpu_wall_seconds'] = time.monotonic()-started
    r['payload_sha256'] = B.inventory(out); write(out/'result.json', r); return r


def parser():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='mode', required=True)
    c = sub.add_parser('contracts'); c.add_argument('--out', type=Path, required=True)
    for mode in ('case', 'audit'):
        c = sub.add_parser(mode); c.add_argument('--cell', choices=('H01', 'H02', 'H03'), required=True)
        c.add_argument('--depth', type=int, choices=(2, 8), required=True); c.add_argument('--out', type=Path, required=True)
    return p


if __name__ == '__main__':
    a = parser().parse_args()
    if a.mode == 'contracts': result = contracts(a.out)
    elif a.mode == 'case': result = case(a.cell, a.depth, a.out)
    else:
        from anchor_path_difference_corrected_audit import audit
        result = audit(a.cell, a.depth, a.out)
    print(json.dumps({k: result[k] for k in result if k in ('complete', 'valid', 'all_pass', 'classification', 'error')}))

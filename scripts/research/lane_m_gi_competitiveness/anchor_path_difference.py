#!/usr/bin/env python3
"""031 standalone CPU preparation/cases; no GPU entry point or default build."""
import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
import numpy as np
import surface_residual_replay as P
import surface_residual_signed_metrics as S
import anchor_difference_overlay as O

B, K, ROOT, BASE = P.B, P.K, P.ROOT, P.BASE
TARGETS = P.TARGETS
SOURCE = ROOT/'src/research/lane_m_gi_competitiveness'
PROTOCOL = ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/031-surface-anchor-coupled-path-difference.md'
OWN = [PROTOCOL, O.ORIGINAL]+[SOURCE/n for n in ('anchor_path_difference.hpp', 'anchor_path_difference_cpu.cpp', 'test_anchor_path_difference.cpp')]
OWN += [Path(__file__).with_name(n) for n in ('anchor_difference_overlay.py', 'anchor_path_difference.py', 'anchor_path_difference_audit.py', 'test_anchor_path_difference.py')]
OWN += [Path(__file__).with_name(n) for n in ('surface_residual_signed_metrics.py', 'surface_residual_corrected_audit.py', 'surface_residual_audit.py')]
BUILD = BASE/'m001-anchor031-cpu-build-v1'
SEEDS = (305419896, 2596069104, 81985529216486895, 18364758544493064720)
PRIMARY = np.dtype([('t', '<f8'), ('tri', '<u4'), ('front', '<u4')])
write = P.write


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (360, 360)); resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    K.need(os.environ.get('OPENBLAS_NUM_THREADS') == os.environ.get('OMP_NUM_THREADS') == '1', '031 single CPU/BLAS worker')


def committed():
    head = P.committed()
    subprocess.run(['git', 'merge-base', '--is-ancestor', '6a58c542', head], check=True)
    for p in OWN:
        K.need(subprocess.check_output(['git', 'show', head+':'+str(p.relative_to(ROOT))]) == p.read_bytes(), '031 commit all code/protocol first')
    K.need(subprocess.check_output(['git', 'show', '3b2980e8:'+str(O.ORIGINAL.relative_to(ROOT))]) == O.ORIGINAL.read_bytes(), '031 preserve physical oracle')
    return head


def reserve(out, expected):
    return P.reserve(out, expected)


def tag(cell, depth):
    K.need((cell, depth) in TARGETS, '031 unregistered target')
    return f'm001-anchor031-{cell.lower()}-b{depth}'


def phase(out, name, pins, **details):
    write(Path(out)/(name+'.json'), dict(input_sha256=dict(pins), **details))


def guarded(command, out, name, cpu=1200, wall=1800):
    def child_limits():
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    started = time.monotonic()
    write(out/(name+'.command.json'), dict(command=list(map(str, command)), cpu_limit=cpu, wall_limit=wall, address_limit=4*1024**3))
    with (out/(name+'.stdout')).open('xb') as stdout, (out/(name+'.stderr')).open('xb') as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True, preexec_fn=child_limits)
        try: code = process.wait(timeout=wall)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL); process.wait()
            raise ValueError('031 process wall timeout; no retry')
    K.need(code == 0, '031 process failure; preserve outputs; no retry: '+name)
    return dict(command=list(map(str, command)), returncode=code, diagnostic_cpu_wall_seconds=time.monotonic()-started)


def build(out):
    limits(); head = committed(); out = reserve(out, BUILD)
    pins = {str(p): B.SHA(p) for p in [*OWN, *P.OWN, *B.OWN]}
    r = dict(schema='m001-anchor031-cpu-preparation/1', source_commit=head, complete=False, all_pass=False, gpu_executed=False,
             input_sha256=pins, commands=[])
    try:
        phase(out, 'build-before', pins)
        old = BASE/'m001-residual030-cpu-contracts-v1/result.json'; qualification = B.read(old)
        K.need(qualification['complete'] and qualification['all_pass'] and qualification['new_contract_count'] == 15, '031 qualified signed scoring required')
        B.rehash(qualification['input_sha256']); B.rehash({str(old.parent/k): h for k, h in qualification['payload_sha256'].items()})
        pins[str(old)] = B.SHA(old); r['reused030_signed_contracts_without_rerun'] = 15
        generated, proof = O.overlay(O.ORIGINAL.read_bytes())
        (out/'anchor_counted_oracle.hpp').write_bytes(generated); r['physical_overlay'] = proof
        compiler = Path(shutil.which('c++')).resolve(); pins[str(compiler)] = B.SHA(compiler)
        r['compiler'] = str(compiler); r['compiler_version'] = subprocess.check_output([str(compiler), '--version'], text=True)
        for name in ('anchor_path_difference_cpu', 'test_anchor_path_difference'):
            command = [str(compiler), '-std=c++20', '-O2', '-fno-fast-math', '-ffp-contract=off', '-MMD', '-MF', str(out/(name+'.d')),
                       '-I'+str(out), '-I'+str(SOURCE), '-I'+str(O.ORIGINAL.parent), str(SOURCE/(name+'.cpp')), '-o', str(out/name)]
            r['commands'].append(guarded(command, out, name+'-compile', cpu=120, wall=180))
        r['commands'].append(guarded([str(out/'test_anchor_path_difference')], out, 'native-contracts', cpu=120, wall=180))
        native = B.read(out/'native-contracts.stdout'); K.need(native['all_pass'] and native['original_counted_path_comparisons'] == 2048, '031 actual physical kernel contracts')
        r['native_contracts'] = native
        env = dict(os.environ, VK_ICD_FILENAMES='/031-unusable-icd.json', VK_DRIVER_FILES='/031-unusable-icd.json')
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', str(Path(__file__).parent), '-p', 'test_anchor_path_difference.py', '-v']
        run = subprocess.run(command, capture_output=True, text=True, env=env, timeout=180)
        (out/'python-contracts.stdout').write_text(run.stdout); (out/'python-contracts.stderr').write_text(run.stderr)
        K.need(run.returncode == 0 and '\nOK\n' in run.stderr, '031 actual Python phase/geometry contracts')
        import re, shlex
        r['python_contract_count'] = int(re.search(r'Ran (\d+) tests?', run.stderr)[1]); dependencies = {}
        for file in out.glob('*.d'):
            for name in shlex.split(file.read_text().replace('\\\n', ' ').split(':', 1)[1]):
                p = Path(name).resolve(); dependencies[str(p)] = B.SHA(p)
        r['compiled_dependency_sha256'] = dependencies; B.rehash(dependencies); B.rehash(pins)
        r.update(complete=True, all_pass=True, native_executable_sha256=B.SHA(out/'anchor_path_difference_cpu'))
    except Exception as e: r['error'] = type(e).__name__+': '+str(e)
    r['payload_sha256'] = B.inventory(out); write(out/'result.json', r); return r


def previous(cell, depth, base=None):
    base = base or BASE; tag(cell, depth); pins = {}
    for c, d in TARGETS[:TARGETS.index((cell, depth))]:
        p = base/(tag(c, d)+'-audit-v1/result.json'); a = B.read(p)
        K.need(a['complete'] and a['valid'] and a['all_pass'] and (a['cell'], a['depth']) == (c, d), '031 prior audit invalid/missing')
        native = Path(a['native_receipt']); n = B.read(native)
        K.need(B.SHA(native) == a['native_receipt_sha256'] and n['complete'] and n['valid'], '031 prior native drift')
        pins[str(p)] = B.SHA(p); pins[str(native)] = B.SHA(native)
    B.rehash(pins); return pins


def intake(cell, depth, out, pins):
    phase(out, 'intake-before', pins, radiance_sampled=False, reference_radiance_decoded=False)
    info = P.intake(cell, depth); pins.update(info['pins']); info['pins'] = pins
    directory = Path(info['plan']['proof']['reference_directory']); qpath = directory/'qualification.json'
    K.need(B.SHA(qpath) == info['plan']['input_sha256'][str(qpath)], '031 anchored reference qualification')
    q = B.read(qpath); scene = directory/'scene.n008'; hits = directory/f"o.n{q['levels'][-1]['spp']}.hits"
    K.need(q['classification'] == 'STATISTICALLY_ELIGIBLE' and q['levels'][-1]['spp'] == 16384, '031 admitted reference required')
    K.need(B.SHA(scene) == q['scene_sha256'] and B.SHA(hits) == q['levels'][-1]['all_payload_sha256'][hits.name], '031 original scene/primary identities')
    pins.update({str(qpath): B.SHA(qpath), str(scene): B.SHA(scene), str(hits): B.SHA(hits)})
    info.update(scene=scene, reference_directory=directory, reference_q=q, primary_path=hits)
    phase(out, 'intake-verified', pins, radiance_sampled=False, reference_radiance_decoded=False)
    return info


def geometry_data(info, directory):
    primary = np.fromfile(directory/'primary.bin', dtype=PRIMARY)
    raw = info['primary_path'].read_bytes()
    K.need(raw[:8] == b'N008HIT\0' and raw[16:] == (directory/'primary.bin').read_bytes()
           and primary.shape == (57600,), '031 original complete CPU primary records')
    origins = np.fromfile(directory/'origins.f64', '<f8').reshape(57600, 3)
    normals = np.fromfile(directory/'normals.f64', '<f8').reshape(57600, 3)
    vertices = np.fromfile(directory/'vertices.f64', '<f8').reshape(-1, 3, 3)
    K.need(np.array_equal(vertices, info['vertices']), '031 triangle order/vertices/owners mismatch')
    active = primary['tri'] != 0xffffffff; index = np.where(active, primary['tri'], 0)
    owner = info['metadata'][index, 2].copy(); material = info['metadata'][index, 1].copy()
    geo = K.partition(origins, normals, active, owner, material, vertices, info['metadata'])
    geo['anchors'] = np.array([np.flatnonzero(geo['groups'] == g)[int((geo['groups'] == g).sum())//2]
                               for g in range(len(geo['keys']))], dtype='<u4')
    return geo


def raw_seed(directory, replicate, groups):
    p = directory/f'seed-{replicate}'; count = int(groups.max())+1
    result = {k: np.fromfile(p/name, '<f8').reshape(shape) for k, name, shape in [
        ('absolute', 'anchor-absolute.f64', (count, 1024)), ('local', 'local.f64', (57600, 16)),
        ('paired', 'paired-anchor.f64', (57600, 16)), ('extra', 'extra-local.f64', (57600, 16)), ('direct', 'direct.f64', (57600,))]}
    result['queries'] = np.fromfile(p/'query-counts.u64', '<u8').reshape(57600, 6)
    result['bank_queries'] = np.fromfile(p/'bank-query-counts.u64', '<u8').reshape(count, 2)
    for key in ('absolute', 'local', 'paired', 'extra', 'direct'):
        K.need(np.isfinite(result[key]).all() and (result[key] >= 0).all(), '031 invalid physical path payload')
    return result


def query_totals(data):
    q = data['queries'].sum(axis=0); b = data['bank_queries'].sum(axis=0)
    values = [int(x) for x in q]+[int(x) for x in b]
    return dict(zip(('local_closest', 'local_shadow', 'paired_closest', 'paired_shadow', 'extra_closest', 'extra_shadow', 'bank_closest', 'bank_shadow'), values))


def aggregate(directory, groups):
    images = {k: [] for k in ('baseline', 'signed', 'clipped', 'direct')}; queries = []
    active = groups >= 0
    for replicate in range(4):
        d = raw_seed(directory, replicate, groups)
        K.need(all((d[k][~active] == 0).all() for k in ('local', 'paired', 'extra', 'direct', 'queries')), '031 nonzero sky')
        candidate = d['absolute'].mean(axis=1)[np.maximum(groups, 0)]+(d['local']-d['paired']).mean(axis=1); candidate[~active] = 0
        images['signed'].append(candidate); images['clipped'].append(np.maximum(candidate, 0))
        images['baseline'].append((d['local'].sum(axis=1)+d['extra'].sum(axis=1))/32)
        images['direct'].append(d['direct']); queries.append(query_totals(d))
    images = {k: np.stack(v) for k, v in images.items()}
    K.need(all(np.array_equal(images['direct'][0], row) for row in images['direct']), '031 direct seed drift')
    vb = images['baseline'].var(axis=0, ddof=1); vc = images['signed'].var(axis=0, ddof=1)
    qb = 57600+sum(q['local_closest']+q['local_shadow']+q['extra_closest']+q['extra_shadow'] for q in queries)
    qc = 57600+sum(q['local_closest']+q['local_shadow']+q['paired_closest']+q['paired_shadow']+q['bank_closest']+q['bank_shadow'] for q in queries)
    K.need(np.isfinite([vb.sum(), vc.sum()]).all() and min(vb.sum(), vc.sum(), qb, qc) > 0, '031 undefined variance/cost')
    ratio = float(vb.sum())*qb/(float(vc.sum())*qc)
    return images, dict(baseline_variance=float(vb.sum()), candidate_variance=float(vc.sum()), baseline_complete_queries=qb,
                        candidate_complete_queries=qc, geometry_scan_queries_per_role=57600, ratio=ratio, pass_=bool(ratio >= 1.20)), dict(baseline=vb, signed=vc), queries


def reference(info, out):
    q = info['reference_q']; directory = info['reference_directory']
    info['pins'].update({str(directory/k): h for k, h in q['levels'][-1]['all_payload_sha256'].items()})
    phase(out, 'reference-before', info['pins'], reference_radiance_decoded=False)
    B.rehash(info['pins']); return P.references(info)


def case(cell, depth, out):
    limits(); head = committed(); prior = previous(cell, depth)
    prep = B.read(BUILD/'result.json'); K.need(prep['complete'] and prep['all_pass'], '031 CPU preparation required')
    B.rehash(prep['input_sha256']); B.rehash(prep['compiled_dependency_sha256']); B.rehash({str(BUILD/k): h for k, h in prep['payload_sha256'].items()})
    out = reserve(out, BASE/(tag(cell, depth)+'-v1')); pins = {str(p): B.SHA(p) for p in OWN}; pins.update(prior)
    pins[str(BUILD/'result.json')] = B.SHA(BUILD/'result.json'); pins[str(BUILD/'anchor_path_difference_cpu')] = prep['native_executable_sha256']
    r = dict(schema='m001-anchor031-cpu-case/1', cell=cell, depth=depth, source_commit=head, complete=False, valid=False,
             classification='INVALID_STOP_NO_RETRY', gpu_executed=False, accepted_timing=False, input_sha256=pins, commands=[])
    started = time.monotonic()
    try:
        info = intake(cell, depth, out, pins); exe = str(BUILD/'anchor_path_difference_cpu')
        phase(out, 'geometry-before', pins, radiance_sampled=False)
        r['commands'].append(guarded([exe, 'geometry', '--scene', str(info['scene']), '--out', str(out/'geometry')], out, 'geometry', cpu=120, wall=180))
        geo = geometry_data(info, out/'geometry')
        for name, array in [('groups.i64', geo['groups'].astype('<i8')), ('anchors.u32', geo['anchors'])]:
            with (out/'geometry'/name).open('xb') as f: array.tofile(f)
        np.savez(out/'geometry/field.npz', **geo)
        geometry_pins = {str(out/'geometry'/k): h for k, h in B.inventory(out/'geometry').items()}; pins.update(geometry_pins)
        phase(out, 'geometry-frozen', pins, all_geometry_frozen_before_radiance=True)
        pins[str(out/'geometry-frozen.json')] = B.SHA(out/'geometry-frozen.json')
        phase(out, 'paths-before', pins, reference_radiance_decoded=False)
        r['commands'].append(guarded([exe, 'paths', '--scene', str(info['scene']), '--geometry', str(out/'geometry'), '--out', str(out/'paths')], out, 'paths'))
        native = B.read(out/'paths/paths.json'); K.need(native['complete'] and native['pairs'] == 16 and native['absolute'] == 1024 and native['groups'] == len(geo['keys']), '031 native path boundary')
        images, efficiency, variances, queries = aggregate(out/'paths', geo['groups'])
        for i, q in enumerate(queries):
            K.need(native['rows'][i] == dict(seed=SEEDS[i], **q), '031 native complete role queries')
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
                 complete_cpu_query_counts=True, extra_control_samples_per_pixel_per_seed=16, old_successful_tests_or_031_paths_repeated=False,
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
    c = sub.add_parser('build'); c.add_argument('--out', type=Path, required=True)
    for mode in ('case', 'audit'):
        c = sub.add_parser(mode); c.add_argument('--cell', choices=('H01', 'H02', 'H03'), required=True)
        c.add_argument('--depth', type=int, choices=(2, 8), required=True); c.add_argument('--out', type=Path, required=True)
    return p


if __name__ == '__main__':
    a = parser().parse_args()
    if a.mode == 'build': result = build(a.out)
    elif a.mode == 'case': result = case(a.cell, a.depth, a.out)
    else:
        from anchor_path_difference_audit import audit
        result = audit(a.cell, a.depth, a.out)
    print(json.dumps({k: result[k] for k in result if k in ('complete', 'valid', 'all_pass', 'classification', 'error')}))

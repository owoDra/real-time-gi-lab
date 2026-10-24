#!/usr/bin/env python3
"""029 one finite CPU replay; exclusive outputs, no GPU entry point."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
import numpy as np
import surface_residual_cv as K
import nrd_no_prepass_build as B
import nrd_vulkan_audit as V
import nrd_no_prepass_audit as N
import closest_primary_metrics as M

ROOT = B.ROOT
BASE = B.BASE
PROTOCOL = ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/029-surface-incident-residual-cpu-replay.md'
OWN = [PROTOCOL]+[Path(__file__).with_name(x) for x in (
    'surface_residual_cv.py', 'surface_residual_replay.py', 'surface_residual_audit.py', 'test_surface_residual_cv.py')]
TARGETS = tuple((c, d) for c in ('H01', 'H02', 'H03') for d in (2, 8))
PREPARATION = BASE/'m001-residual029-cpu-contracts-v1/result.json'


def write(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write('\n')


def tag(cell, depth):
    K.need((cell, depth) in TARGETS, '029 unregistered target')
    return f'm001-residual029-{cell.lower()}-b{depth}'


def committed():
    head = B.committed()
    subprocess.run(['git', 'merge-base', '--is-ancestor', '580bc4b1', head], check=True)
    for p in OWN:
        K.need(subprocess.check_output(['git', 'show', head+':'+str(p.relative_to(ROOT))]) == p.read_bytes(),
               '029 commit complete implementation before execution')
    return head


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (240, 240))
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    K.need(os.environ.get('OPENBLAS_NUM_THREADS') == os.environ.get('OMP_NUM_THREADS') == '1',
           '029 require one BLAS/OMP thread')


def reserve(out, expected):
    out = Path(out).resolve(); expected = Path(expected).resolve()
    K.need(out == expected and out.is_relative_to(BASE) and not out.exists(), '029 exclusive canonical output')
    K.need(shutil.disk_usage(BASE).free >= 16*1024**3, '02916GiB disk guard')
    out.mkdir(); return out


def previous(cell, depth, base=None):
    base = base or BASE
    K.need((cell, depth) in TARGETS, '029 unregistered target')
    pins = {}
    for c, d in TARGETS[:TARGETS.index((cell, depth))]:
        p = base/(tag(c, d)+'-audit-v1/result.json'); a = B.read(p)
        K.need(a['complete'] and a['valid'] and a['all_pass'] and (a['cell'], a['depth']) == (c, d),
               '029 stop after invalid or missing prior audit')
        native = Path(a['native_receipt']); n = B.read(native)
        K.need(B.SHA(native) == a['native_receipt_sha256'] and n['complete'] and n['valid'], '029 prior native identity')
        pins[str(p)] = B.SHA(p); pins[str(native)] = B.SHA(native)
        pins.update({str(p.parent/k): h for k, h in a['payload_sha256'].items()})
    B.rehash(pins); return pins


def intake(cell, depth):
    K.need((cell, depth) in TARGETS, '029 unregistered target')
    published = ROOT/'research/lanes/lane-m-gi-competitiveness/results/163-nrd-cold-warm-six-targets-summary.json'
    K.need(subprocess.check_output(['git', 'show', '8d8b12fc:'+str(published.relative_to(ROOT))]) == published.read_bytes(),
           '029 immutable published026 anchor')
    pins = {str(p): B.SHA(p) for p in [*OWN, *B.OWN, published]}
    summary = B.read(published)
    folder = BASE/f'm001-nrd026-gpu-{cell.lower()}-b{depth}-n1-v1'
    native = folder/'result.json'; audit = BASE/f'm001-nrd026-gpu-{cell.lower()}-b{depth}-n1-audit-v1/result.json'
    for p in (native, audit):
        K.need(B.SHA(p) == summary['input_sha256'][str(p)], '029026 native/audit anchor')
        pins[str(p)] = B.SHA(p)
    n = B.read(native); a = B.read(audit); plan = B.read(folder/'plan.json')
    K.need(n['complete'] and n['valid'] and a['complete'] and a['valid']
           and (n['cell'], n['depth'], n['spp']) == (cell, depth, 1)
           and a['native_receipt_sha256'] == B.SHA(native) and n['plan_sha256'] == B.SHA(folder/'plan.json'),
           '029 original026 physical boundary')
    K.need(a['full_secondary_intersection_frames'] == [0, 1, 63] and len(a['all_frame_field_checks']) == 64
           and all(x['primary']['pass_'] and x['all_sample_sum_mean_exact'] and x['all_actual_guide_contracts_pass']
                   for x in a['all_frame_field_checks']), '029 certified026 coverage')
    pins[str(folder/'plan.json')] = B.SHA(folder/'plan.json')
    for name, h in a['payload_sha256'].items(): pins[str(audit.parent/name)] = h
    # Only metadata/geometry and old audit witnesses are read here. Evaluation
    # raw radiance is neither hashed nor numerically decoded before fit freeze.
    B.rehash(pins)
    capture = folder/'capture'
    def geometry_file(relative):
        p = capture/relative; h = n['payload_sha256']['capture/'+relative]
        K.need(p.is_file() and not p.is_symlink() and B.SHA(p) == h, '029 original geometry drift')
        pins[str(p)] = h; return p
    vertices, metadata = V.geometry(geometry_file('geometry-state.bin'))
    hp = geometry_file('frame-0/hits.u32'); op = geometry_file('frame-0/secondary-origins.f32')
    hits = np.fromfile(hp, dtype=M.GPU_DTYPE); origins = np.fromfile(op, dtype='<f4').reshape(57600, 4)
    K.need(hits.shape == (57600,) and np.isin(hits['flag'], [0, 1]).all(), '029 original primary ABI')
    return dict(cell=cell, depth=depth, folder=folder, capture=capture, native=n, plan=plan, pins=pins,
                hits=hits, origins=origins, vertices=vertices, metadata=metadata,
                reused026_secondary_intersections=a['secondary_samples_independently_intersected'])


def frame(info, index):
    K.need(type(index) is int and 0 <= index < 64, '029 frame outside fixed split')
    path = info['capture']/f'frame-{index}'; n = info['native']; pins = info['pins']
    for name in ('raw-pt.f32', 'secondary-rays.f32', 'hits.u32', 'secondary-origins.f32'):
        p = path/name; h = n['payload_sha256'][f'capture/frame-{index}/{name}']
        K.need(p.is_file() and not p.is_symlink() and B.SHA(p) == h, '029 consumed original frame drift')
        pins[str(p)] = h
    K.need(n['payload_sha256'][f'capture/frame-{index}/hits.u32'] == n['payload_sha256']['capture/frame-0/hits.u32'],
           '029 static primary bytes differ')
    raw = np.fromfile(path/'raw-pt.f32', dtype='<f4').reshape(57600, 4).astype(np.float64)
    rays = np.fromfile(path/'secondary-rays.f32', dtype='<f4').reshape(57600, 4).astype(np.float64)
    active = info['hits']['flag'] == 1
    K.need(np.isfinite(raw).all() and (raw[:, :3] >= 0).all() and np.isfinite(rays).all()
           and (raw[:, 3] == 1).all() and (raw[~active, 1] == 0).all() and (rays[~active] == 0).all(),
           '029 invalid actual path values')
    w = rays[:, :3].copy()
    K.need((np.abs((w[active]**2).sum(axis=1)-1) <= 1e-4).all()
           and ((w[active]*info['hits']['n'][active]).sum(axis=1) >= -1e-6).all(), '029 actual first direction')
    w[~active] = [0, 0, 1]
    return raw[:, 1], raw[:, 0], K.basis(w)


def references(info):
    proof = info['plan']['proof']; directory = Path(proof['reference_directory'])
    q = B.read(directory/'qualification.json')
    info['pins'][str(directory/'qualification.json')] = B.SHA(directory/'qualification.json')
    info['pins'].update({str(directory/k): h for k, h in q['levels'][-1]['all_payload_sha256'].items()})
    return N.reference(proof)


def score(images, direct, reference, out):
    rows = {}; errors = {}
    for name in ('baseline', 'signed', 'clipped'):
        values = dict(direct=direct.reshape(180, 320), indirect=images[name].reshape(180, 320),
                      total=(direct+images[name]).reshape(180, 320))
        components, maps = N.Q.score(values, reference)
        d = components['direct']
        direct_ok = d['nrmse'] <= 1e-4 and d['whole_image_max_absolute'] <= 1e-5 and d['gpu_zero_reference_positive'] == 0
        rows[name] = dict(components=components, pass_=bool(direct_ok and M.quality(components) == 'PASS'))
        errors.update({name+'_'+k: v for k, v in maps.items()})
    np.savez(out/'full-hdr-errors.npz', **errors)
    return rows


def replay(cell, depth, out):
    limits(); head = committed(); prior = previous(cell, depth)
    prep = B.read(PREPARATION); K.need(prep['complete'] and prep['all_pass'] and not prep['gpu_executed'], '029 CPU readiness required')
    B.rehash(prep['input_sha256']); B.rehash({str(PREPARATION.parent/k): h for k, h in prep['payload_sha256'].items()})
    out = reserve(out, BASE/(tag(cell, depth)+'-v1'))
    r = dict(schema='m001-residual029-cpu-replay/1', cell=cell, depth=depth, source_commit=head,
             complete=False, valid=False, classification='INVALID_STOP_NO_RETRY', gpu_executed=False, accepted_timing=False)
    start = time.monotonic()
    try:
        info = intake(cell, depth); pins = info['pins']; pins.update(prior); pins[str(PREPARATION)] = B.SHA(PREPARATION)
        active = info['hits']['flag'] == 1
        geo = K.partition(info['origins'][:, :3], info['hits']['n'], active, info['hits']['inst'], info['hits']['mat'],
                          info['vertices'], info['metadata'])
        values = []; direct = []; training = []
        for i in range(8):
            y, d, x = frame(info, i); values.append(y); direct.append(d); training.append(x)
        training = np.stack(training); fit = K.train(training, np.stack(values), geo['groups'], len(geo['keys']))
        mu = K.moments(geo['normal'])
        np.savez(out/'field.npz', **geo, **fit, mu=mu)
        write(out/'fit-frozen.json', dict(field_sha256=B.SHA(out/'field.npz'), training_frames=list(range(8)),
                                        evaluation_radiance_decoded=False, reference_radiance_decoded=False))
        fit['coefficients'].setflags(write=False); corrected = []; feature_sum = np.zeros_like(mu)
        for i in range(8, 64):
            y, d, x = frame(info, i); values.append(y); direct.append(d)
            corrected.append(y+K.correction(x[None], mu, fit['coefficients'], geo['groups'])[0]); feature_sum += x
        values = np.stack(values); direct = np.stack(direct); corrected = np.stack(corrected)
        images, variance = K.aggregate(values, corrected); direct_mean = direct.mean(axis=0)
        drift = feature_sum/56-mu; drift[~active] = 0
        np.savez(out/'frames.npz', raw_indirect=values, raw_direct=direct, corrected_evaluation=corrected, moment_drift=drift)
        np.savez(out/'images.npz', direct=direct_mean, **images)
        write(out/'evaluation-frozen.json', dict(field_sha256=B.SHA(out/'field.npz'), frames_sha256=B.SHA(out/'frames.npz'),
             images_sha256=B.SHA(out/'images.npz'), reference_radiance_decoded=False))
        K.need(B.SHA(out/'field.npz') == B.read(out/'fit-frozen.json')['field_sha256'], '029 field changed after freeze')
        reference = references(info); scores = score(images, direct_mean, reference, out)
        passed = variance['variance_pass'] and scores['signed']['pass_'] and scores['clipped']['pass_']
        negative = images['signed'] < 0
        r.update(complete=True, valid=True, classification='CPU_FEASIBILITY_PASS' if passed else 'REJECTED_NO_GPU',
                 pass_=bool(passed), variance=variance, scores=scores, groups=len(geo['keys']), active_pixels=int(active.sum()),
                 clipping=dict(negative_pixels=int(negative.sum()), minimum=float(images['signed'].min()),
                               negative_absolute_energy=float(-images['signed'][negative].sum()),
                               clipping_delta_sum=float((images['clipped']-images['signed']).sum())),
                 all_pixels=57600, scoring_exclusions=0, training_frames=list(range(8)), evaluation_frames=list(range(8, 64)),
                 physical_paths_per_pixel_budget=64, measured_ray_query_count_available=False,
                 new_physical_or_reference_samples=0, new_secondary_intersections=0,
                 reused026_full_secondary_intersection_frames=[0, 1, 63],
                 reused026_secondary_intersections=info['reused026_secondary_intersections'],
                 fitted_field_bytes=sum(x.nbytes for x in fit.values()), cpu_saved_arrays_bytes=sum(p.stat().st_size for p in out.glob('*.npz')),
                 coefficient_bytes=fit['coefficients'].nbytes, cpu_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                 regression_features=9, group_fit_count=len(geo['keys']), correction_dot_products=56*int(active.sum()),
                 clipping_claimed_unbiased=False, finite_rng_unbiasedness_proven=False,
                 reference_read_after_fit_and_evaluation_freeze=True, input_sha256=pins)
        B.rehash(pins)
    except Exception as e:
        r['error'] = type(e).__name__+': '+str(e)
    r['diagnostic_cpu_wall_seconds'] = time.monotonic()-start
    r['payload_sha256'] = B.inventory(out); write(out/'result.json', r); return r


def contracts(out):
    limits(); head = committed(); out = reserve(out, PREPARATION.parent)
    r = dict(schema='m001-residual029-cpu-contracts/1', source_commit=head, complete=False, all_pass=False, gpu_executed=False,
             input_sha256={str(p): B.SHA(p) for p in [*OWN, *B.OWN]}, python=sys.version, numpy=np.__version__)
    try:
        env = dict(os.environ, VK_ICD_FILENAMES='/029-unusable-icd.json', VK_DRIVER_FILES='/029-unusable-icd.json')
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', str(Path(__file__).parent), '-p', 'test_surface_residual_cv.py', '-v']
        run = subprocess.run(command, capture_output=True, text=True, env=env, timeout=340)
        (out/'stdout.txt').write_text(run.stdout); (out/'stderr.txt').write_text(run.stderr)
        r.update(command=command, returncode=run.returncode)
        K.need(run.returncode == 0 and '\nOK\n' in run.stderr, '029 actual-kernel contracts failed')
        import re
        r['contract_count'] = int(re.search(r'Ran (\d+) tests?', run.stderr)[1])
        B.rehash(r['input_sha256']); r.update(complete=True, all_pass=True)
    except Exception as e: r['error'] = type(e).__name__+': '+str(e)
    r['payload_sha256'] = B.inventory(out); write(out/'result.json', r); return r


def parser():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='mode', required=True)
    c = sub.add_parser('contracts'); c.add_argument('--out', type=Path, required=True)
    for name in ('replay', 'audit'):
        c = sub.add_parser(name); c.add_argument('--cell', choices=('H01', 'H02', 'H03'), required=True)
        c.add_argument('--depth', choices=(2, 8), type=int, required=True); c.add_argument('--out', type=Path, required=True)
    return p


if __name__ == '__main__':
    a = parser().parse_args()
    if a.mode == 'contracts': result = contracts(a.out)
    elif a.mode == 'replay': result = replay(a.cell, a.depth, a.out)
    else:
        from surface_residual_audit import audit
        result = audit(a.cell, a.depth, a.out)
    print(json.dumps({k: result[k] for k in result if k in ('complete', 'valid', 'all_pass', 'classification', 'error', 'contract_count')}))

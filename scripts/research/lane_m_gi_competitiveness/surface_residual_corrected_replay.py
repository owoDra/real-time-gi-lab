#!/usr/bin/env python3
"""030 CPU-only adapter correction; never calls stopped029 replay/contracts."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import numpy as np
import surface_residual_replay as R
import surface_residual_signed_metrics as S

K, B, BASE, ROOT = R.K, R.B, R.BASE, R.ROOT
TARGETS = R.TARGETS
PROTOCOL = ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/030-signed-residual-scoring-and-provenance-correction.md'
OWN = [PROTOCOL]+[Path(__file__).with_name(x) for x in (
    'surface_residual_signed_metrics.py', 'surface_residual_corrected_replay.py',
    'surface_residual_corrected_audit.py', 'test_surface_residual_corrected.py')]
PREPARATION = BASE/'m001-residual030-cpu-contracts-v1/result.json'
write, limits, reserve = R.write, R.limits, R.reserve


def committed():
    head = R.committed()
    subprocess.run(['git', 'merge-base', '--is-ancestor', '9749ac96', head], check=True)
    for p in OWN:
        K.need(subprocess.check_output(['git', 'show', head+':'+str(p.relative_to(ROOT))]) == p.read_bytes(),
               '030 commit complete implementation before execution')
    for p in R.OWN:
        K.need(subprocess.check_output(['git', 'show', '1c51a7c3:'+str(p.relative_to(ROOT))]) == p.read_bytes(),
               '030 preserve all original029 source/protocol bytes')
    return head


def tag(cell, depth):
    K.need((cell, depth) in TARGETS, '030 unregistered target')
    return f'm001-residual030-{cell.lower()}-b{depth}'


def previous(cell, depth, base=None):
    base = base or BASE; tag(cell, depth); pins = {}
    for c, d in TARGETS[:TARGETS.index((cell, depth))]:
        p = base/(tag(c, d)+'-audit-v1/result.json'); a = B.read(p)
        K.need(a['complete'] and a['valid'] and a['all_pass'] and (a['cell'], a['depth']) == (c, d),
               '030 stop after missing/invalid prior audit')
        native = Path(a['native_receipt']); n = B.read(native)
        K.need(B.SHA(native) == a['native_receipt_sha256'] and n['complete'] and n['valid'],
               '030 prior native identity')
        pins.update({str(p): B.SHA(p), str(native): B.SHA(native)})
        pins.update({str(p.parent/k): h for k, h in a['payload_sha256'].items()})
        pins.update(n['input_sha256'])
        pins.update({str(native.parent/k): h for k, h in n['payload_sha256'].items()})
    B.rehash(pins); return pins


def phase(out, name, pins, **details):
    """Exclusive durable receipt before the caller performs numerical work."""
    write(Path(out)/(name+'.json'), dict(input_sha256=dict(pins), **details))


def intake(cell, depth, out, pins):
    published = ROOT/'research/lanes/lane-m-gi-competitiveness/results/163-nrd-cold-warm-six-targets-summary.json'
    summary = B.read(published)
    for p in (BASE/f'm001-nrd026-gpu-{cell.lower()}-b{depth}-n1-v1/result.json',
              BASE/f'm001-nrd026-gpu-{cell.lower()}-b{depth}-n1-audit-v1/result.json'):
        pins[str(p)] = summary['input_sha256'][str(p)]
    pins[str(published)] = B.SHA(published)
    phase(out, 'intake-before', pins, evaluation_radiance_decoded=False, reference_radiance_decoded=False)
    info = R.intake(cell, depth); pins.update(info['pins']); info['pins'] = pins
    phase(out, 'intake-verified', pins, evaluation_radiance_decoded=False, reference_radiance_decoded=False)
    return info


def read_frame(info, index, out):
    expected = {}
    for name in ('raw-pt.f32', 'secondary-rays.f32', 'hits.u32', 'secondary-origins.f32'):
        expected[str(info['capture']/f'frame-{index}'/name)] = info['native']['payload_sha256'][f'capture/frame-{index}/{name}']
    phase(out, f'frame-{index}-before', expected, frame=index, expected_identities=True)
    return R.frame(info, index)


def reference(info, out):
    directory = Path(info['plan']['proof']['reference_directory']); qpath = directory/'qualification.json'
    expected_q = info['plan']['input_sha256'][str(qpath)]
    K.need(B.SHA(qpath) == expected_q, '030 original reference qualification identity')
    q = B.read(qpath); pins = {str(qpath): expected_q}
    pins.update({str(directory/k): h for k, h in q['levels'][-1]['all_payload_sha256'].items()})
    info['pins'].update(pins)
    phase(out, 'reference-before', info['pins'], reference_radiance_decoded=False)
    B.rehash(pins)
    return R.references(info)


def frozen_reuse(info, out):
    res = ROOT/'research/lanes/lane-m-gi-competitiveness/results'
    published = [res/'192-surface-incident-residual-first-scoring-failure.json',
                 res/'194-surface-incident-residual-first-failure-verification.json']
    for p in published:
        K.need(subprocess.check_output(['git', 'show', '549f6502:'+str(p.relative_to(ROOT))]) == p.read_bytes(),
               '030 original029 failure anchor')
        info['pins'][str(p)] = B.SHA(p)
    old = B.read(published[0]); native = Path(old['native_receipt'])
    K.need(B.SHA(native) == old['native_receipt_sha256'], '030029 invalid native drift')
    n = B.read(native); K.need(not n['valid'] and n['classification'] == 'INVALID_STOP_NO_RETRY', '030 stopped029 identity')
    inventory = Path(old['reconstructed_consumed_scope_sha256'])
    K.need(B.SHA(inventory) == old['reconstructed_consumed_scope_sha256_digest'], '030 reconstructed scope drift')
    scope = B.read(inventory); B.rehash(scope)
    info['pins'].update(scope)
    info['pins'].update({str(native): B.SHA(native), str(inventory): B.SHA(inventory)})
    artifact = native.parent
    K.need(set(n['payload_sha256']) == {'field.npz', 'frames.npz', 'images.npz', 'fit-frozen.json', 'evaluation-frozen.json'},
           '030 exact five frozen artifacts required')
    info['pins'].update({str(artifact/k): h for k, h in n['payload_sha256'].items()})
    B.rehash(info['pins'])
    phase(out, 'frozen-reuse-before', info['pins'], artifact_directory=str(artifact),
          original029_native_manifest_missing=True, reconstruction_is_post_failure=True,
          production_fit_or_correction_or_image_repeated=False)
    with np.load(artifact/'frames.npz') as z: frames = {k: z[k] for k in z.files}
    with np.load(artifact/'images.npz') as z: images = {k: z[k] for k in z.files}
    with np.load(artifact/'field.npz') as z: field = {k: z[k] for k in z.files}
    return artifact, frames, images, field


def fresh(info, out):
    active = info['hits']['flag'] == 1
    geo = K.partition(info['origins'][:, :3], info['hits']['n'], active, info['hits']['inst'], info['hits']['mat'],
                      info['vertices'], info['metadata'])
    raw, direct, features = [], [], []
    for i in range(8):
        y, d, x = read_frame(info, i, out); raw.append(y); direct.append(d); features.append(x)
    phase(out, 'training-before-fit', info['pins'], training_frames=list(range(8)), evaluation_radiance_decoded=False)
    fit = K.train(np.stack(features), np.stack(raw), geo['groups'], len(geo['keys'])); mu = K.moments(geo['normal'])
    field = dict(**geo, **fit, mu=mu); np.savez(out/'field.npz', **field)
    write(out/'fit-frozen.json', dict(field_sha256=B.SHA(out/'field.npz'), training_frames=list(range(8)),
          evaluation_radiance_decoded=False, reference_radiance_decoded=False))
    fit['coefficients'].setflags(write=False); corrected = []; feature_sum = np.zeros_like(mu)
    for i in range(8, 64):
        y, d, x = read_frame(info, i, out); raw.append(y); direct.append(d)
        corrected.append(y+K.correction(x[None], mu, fit['coefficients'], geo['groups'])[0]); feature_sum += x
    phase(out, 'evaluation-before-aggregate', info['pins'], reference_radiance_decoded=False)
    raw, direct, corrected = np.stack(raw), np.stack(direct), np.stack(corrected)
    images, _ = K.aggregate(raw, corrected); images['direct'] = direct.mean(axis=0)
    drift = feature_sum/56-mu; drift[~active] = 0
    frames = dict(raw_indirect=raw, raw_direct=direct, corrected_evaluation=corrected, moment_drift=drift)
    np.savez(out/'frames.npz', **frames); np.savez(out/'images.npz', **images)
    write(out/'evaluation-frozen.json', dict(field_sha256=B.SHA(out/'field.npz'), frames_sha256=B.SHA(out/'frames.npz'),
          images_sha256=B.SHA(out/'images.npz'), reference_radiance_decoded=False))
    K.need(B.SHA(out/'field.npz') == B.read(out/'fit-frozen.json')['field_sha256'], '030 frozen field drift')
    return out, frames, images, field


def replay(cell, depth, out):
    limits(); head = committed(); prior = previous(cell, depth)
    prep = B.read(PREPARATION); K.need(prep['complete'] and prep['all_pass'], '030 CPU contracts required')
    B.rehash(prep['input_sha256']); B.rehash({str(PREPARATION.parent/k): h for k, h in prep['payload_sha256'].items()})
    out = reserve(out, BASE/(tag(cell, depth)+'-v1'))
    pins = {str(p): B.SHA(p) for p in [*OWN, *R.OWN, *B.OWN, PREPARATION]}; pins.update(prior)
    r = dict(schema='m001-residual030-cpu-replay/1', cell=cell, depth=depth, source_commit=head,
             complete=False, valid=False, classification='INVALID_STOP_NO_RETRY', gpu_executed=False,
             accepted_timing=False, input_sha256=pins, original029_stays_stopped=True)
    start = time.monotonic()
    try:
        info = intake(cell, depth, out, pins)
        reused = (cell, depth) == ('H01', 2)
        artifact, frames, images, field = frozen_reuse(info, out) if reused else fresh(info, out)
        r['artifact_directory'] = str(artifact)
        r['artifact_sha256'] = {k: B.SHA(artifact/k) for k in ('field.npz', 'frames.npz', 'images.npz', 'fit-frozen.json', 'evaluation-frozen.json')}
        phase(out, 'scoring-before', pins, artifact_sha256=r['artifact_sha256'], reference_radiance_decoded=False)
        aggregate, variance = K.aggregate(frames['raw_indirect'], frames['corrected_evaluation'])
        for key in aggregate: K.need(np.array_equal(aggregate[key], images[key]), '030 original saved aggregate identity')
        ref = reference(info, out)
        scores, errors = S.score({k: images[k] for k in ('baseline', 'signed', 'clipped')}, images['direct'], ref)
        np.savez(out/'full-hdr-errors.npz', **errors)
        passed = variance['variance_pass'] and scores['signed']['pass_'] and scores['clipped']['pass_']
        negative = images['signed'] < 0
        r.update(complete=True, valid=True, classification='CPU_FEASIBILITY_PASS' if passed else 'REJECTED_NO_GPU',
                 pass_=bool(passed), variance=variance, scores=scores, groups=len(field['keys']),
                 active_pixels=int(field['active'].sum()), all_pixels=57600, scoring_exclusions=0,
                 clipping=dict(negative_pixels=int(negative.sum()), minimum=float(images['signed'].min()),
                 negative_absolute_energy=float(-images['signed'][negative].sum()),
                 clipping_delta_sum=float((images['clipped']-images['signed']).sum())),
                 physical_paths_per_pixel_budget=64, training_frames=list(range(8)), evaluation_frames=list(range(8, 64)),
                 production_frozen029_reuse=reused, original029_native_manifest_missing=reused,
                 original029_production_fit_or_correction_repeated=False,
                 new_physical_or_reference_samples=0, new_secondary_intersections=0,
                 reused026_full_secondary_intersection_frames=[0, 1, 63],
                 reused026_secondary_intersections=info['reused026_secondary_intersections'],
                 measured_ray_query_count_available=False, coefficient_bytes=field['coefficients'].nbytes,
                 fitted_field_bytes=sum(field[k].nbytes for k in ('coefficients', 'gram', 'rhs', 'lambdas', 'training_samples')),
                 cpu_saved_arrays_bytes=sum((artifact/k).stat().st_size for k in ('field.npz', 'frames.npz', 'images.npz')),
                 correction_dot_products=56*int(field['active'].sum()), regression_features=9, group_fit_count=len(field['keys']),
                 cpu_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                 clipping_claimed_unbiased=False, finite_rng_unbiasedness_proven=False,
                 reference_read_after_fit_and_evaluation_freeze=True)
        B.rehash(pins)
    except Exception as e: r['error'] = type(e).__name__+': '+str(e)
    r['diagnostic_cpu_wall_seconds'] = time.monotonic()-start
    r['payload_sha256'] = B.inventory(out); write(out/'result.json', r); return r


def contracts(out):
    limits(); head = committed(); out = reserve(out, PREPARATION.parent)
    r = dict(schema='m001-residual030-cpu-contracts/1', source_commit=head, complete=False, all_pass=False,
             gpu_executed=False, input_sha256={str(p): B.SHA(p) for p in [*OWN, *R.OWN, *B.OWN]})
    try:
        old = B.read(R.PREPARATION); K.need(old['complete'] and old['all_pass'] and old['contract_count'] == 15, '030029 contracts reuse')
        B.rehash(old['input_sha256']); B.rehash({str(R.PREPARATION.parent/k): h for k, h in old['payload_sha256'].items()})
        r['input_sha256'][str(R.PREPARATION)] = B.SHA(R.PREPARATION)
        r['reused029_contracts_without_rerun'] = 15
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', str(Path(__file__).parent), '-p', 'test_surface_residual_corrected.py', '-v']
        import os, re
        env = dict(os.environ, VK_ICD_FILENAMES='/030-unusable-icd.json', VK_DRIVER_FILES='/030-unusable-icd.json')
        run = subprocess.run(command, capture_output=True, text=True, env=env, timeout=340)
        (out/'stdout.txt').write_text(run.stdout); (out/'stderr.txt').write_text(run.stderr)
        r.update(command=command, returncode=run.returncode, python=sys.version, numpy=np.__version__)
        K.need(run.returncode == 0 and '\nOK\n' in run.stderr, '030 signed/provenance contracts failed')
        r['new_contract_count'] = int(re.search(r'Ran (\d+) tests?', run.stderr)[1])
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
        from surface_residual_corrected_audit import audit
        result = audit(a.cell, a.depth, a.out)
    print(json.dumps({k: result[k] for k in result if k in ('complete', 'valid', 'all_pass', 'classification', 'error', 'new_contract_count')}))

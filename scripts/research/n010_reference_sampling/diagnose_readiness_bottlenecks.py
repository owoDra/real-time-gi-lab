#!/usr/bin/env python3
"""Post-hoc CPU-only analysis of retained N010 evidence; never admits results."""
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import resource
import struct
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
OUT = ROOT/'out/research/n010-comparison-readiness'
SEEDS = (305419896, 2596069104, 81985529216486895, 18364758544493064720)
LUMA = np.array((.2126, .7152, .0722))
INPUTS = {}


def read_bytes(path, expected=None):
    path = path.resolve()
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('retained input identity changed: '+str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != digest:
        raise ValueError('input changed during diagnosis: '+str(path))
    INPUTS[str(path)] = digest
    return data


def read_json(path):
    return json.loads(read_bytes(path))


def sidecar(path, expected, spp, seed):
    data = read_bytes(path, expected)
    if data[:8] != b'N008F64\0':
        raise ValueError('unexpected f64 schema')
    w, h, n, actual_seed = struct.unpack_from('<IIIQ', data, 8)
    if n != spp or actual_seed != seed or len(data) != 28+w*h*24*8:
        raise ValueError('unexpected f64 dimensions/identity')
    a = np.frombuffer(data, dtype='<f8', offset=28).reshape(h, w, 2, 4, 3)
    # On disk all twelve means precede all twelve second moments per pixel.
    if not np.isfinite(a).all() or (a < 0).any():
        raise ValueError('invalid retained radiance/moments')
    return a[:, :, 0], a[:, :, 1]


def load_level(directory, qualification, spp):
    row = next(r for r in qualification['levels'] if r['spp'] == spp)
    means, seconds = [], []
    for i, seed in enumerate(SEEDS):
        name = f'o.n{spp}.s{i}.f64'
        mean, second = sidecar(directory/name, row['all_payload_sha256'][name], spp, seed)
        means.append(mean)
        seconds.append(second)
    return np.stack(means), np.stack(seconds)


def pairwise_p99(values):
    return max(float(np.quantile(np.abs(values[i]-values[j]), .99))
               for i, j in itertools.combinations(range(4), 2))


def main():
    target = RESULTS/'191-posthoc-readiness-bottleneck-diagnosis.json'
    if target.exists():
        raise ValueError('refuse overwriting a retained diagnosis')
    # One low-priority CPU, no GPU/native sampling and a finite analysis budget.
    allowed = os.sched_getaffinity(0)
    os.sched_setaffinity(0, {max(allowed)})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    start = time.monotonic()
    read_bytes(Path(__file__))
    view = read_json(RESULTS/'160-primary-direction-reference-view.json')
    campaign = read_json(RESULTS/'180-primary-direction-second-stop-bounded-feasibility.json')
    if not campaign['complete'] or campaign['all_pass']:
        raise ValueError('diagnosis expects the actual terminal failed candidate')
    original_dir = OUT/'references-recovery-sponza-v1/C1_T_B8'
    b2_dir = OUT/'references-v1/C1_T_B2'
    original = read_json(original_dir/'qualification.json')
    if INPUTS[str((original_dir/'qualification.json').resolve())] != campaign['baseline']['qualification_sha256']:
        raise ValueError('immutable feasibility baseline differs')
    b2 = read_json(b2_dir/'qualification.json')
    if original['state_sha256'] != b2['state_sha256']:
        raise ValueError('B2/B8 states differ')
    scene8 = read_bytes(original_dir/'scene.n008').decode()
    scene2 = read_bytes(b2_dir/'scene.n008').decode()
    if scene8.replace('max_bounces 8\n', 'max_bounces 2\n') != scene2:
        raise ValueError('B2/B8 scene definitions differ outside finite depth')
    # The original sampler uses a fresh per-sample RNG and the same dimensions
    # for B2 and the initial B8 prefix. This is a paired path-prefix diagnosis.
    for p in ('scripts/research/n010_comparison_readiness/generate_rqmc_oracle.py',
              'scripts/research/n010_comparison_readiness/generate_cached_oracle.py',
              'src/research/n008_hdr_oracle/n008_oracle.hpp'):
        read_bytes(ROOT/p)
    decomposition = []
    for spp in (8192, 16384, 32768):
        shallow, _ = load_level(b2_dir, b2, spp)
        full, _ = load_level(original_dir, original, spp)
        first = shallow[..., 2, :] @ LUMA
        total = full[..., 2, :] @ LUMA
        later = total-first
        centered = [v-v.mean(axis=0) for v in (first, later, total)]
        first_energy, later_energy, total_energy = [float(np.sum(v*v)) for v in centered]
        cross = float(2*np.sum(centered[0]*centered[1]))
        relative_residual = abs(first_energy+later_energy+cross-total_energy)/total_energy
        if relative_residual > 1e-12:
            raise ValueError('paired replicate-energy decomposition is inconsistent')
        decomposition.append({'spp':spp,
            'first_indirect_bounce_replicate_energy':first_energy,
            'later_indirect_bounces_replicate_energy':later_energy,
            'cross_covariance_energy':cross,'full_indirect_replicate_energy':total_energy,
            'later_to_full_energy_ratio':later_energy/total_energy,
            'first_to_full_energy_ratio':first_energy/total_energy,
            'decomposition_relative_residual':relative_residual,
            'first_indirect_pairwise_luma_p99':pairwise_p99(first),
            'later_indirect_pairwise_luma_p99':pairwise_p99(later),
            'full_indirect_pairwise_luma_p99':pairwise_p99(total),
            'scope':'Four retained replicate means, not iid per-path variance or a confidence bound. '
                    'Later means are paired B8 minus B2; their float64 rounding is retained.'})
    screens = [r['screen']['rows'][-1] for r in original['levels']]
    levels = [r['spp'] for r in original['levels']]
    errors = [r['max_active_abs_p99'] for r in screens]
    exponent = -float(np.polyfit(np.log(levels), np.log(errors), 1)[0])
    last_spp, last_error = levels[-1], errors[-1]
    predictions = []
    for spp in (131072, 262144):
        error = last_error*(spp/last_spp)**(-exponent)
        predictions.append({'spp':spp,'modelled_absolute_p99':error,
            'multiplicative_reduction_to_reach_original_1e_5':1e-5/error})
    timing = []
    for number in (169, 178):
        path = next(RESULTS.glob(f'{number}-*full-renderer.json'))
        d = read_json(path)
        for r in d['rows']:
            a = r.get('analysis')
            timing.append({'campaign':number,'boundary':r['boundary']['id'],
                'complete_blocks':len(r['blocks']),
                'verdict':('PASS' if a['all_pass'] else 'FAIL') if a else 'INCOMPLETE',
                'failed_gates':[k for k,v in a['gates'].items() if not v] if a else None,
                'control_order_bias':a['control_order_bias'] if a else None,
                'effect_order_bias':a['effect_order_bias'] if a else None})
    sizing = read_json(RESULTS/'185-deferred-image-calibration-sizing.json')
    if not sizing['complete'] or not sizing['all_pass'] or len(sizing['rows']) != 16:
        raise ValueError('actual terminal full sizing missing')
    result = {'schema':'n010-posthoc-readiness-bottleneck-diagnosis/1',
        'complete':True,'classification':'POST_HOC_DIAGNOSIS_NOT_ADMISSION',
        'gpu_run':False,'new_transport_samples':False,'eligible_for_references':False,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'input_sha256':INPUTS,
        'resources':{'cpu_affinity':sorted(os.sched_getaffinity(0)),
            'nice':os.getpriority(os.PRIO_PROCESS,0),'cpu_limit_seconds':120,
            'elapsed_seconds_diagnostic':time.monotonic()-start},
        'eligible_slots':view['retained_eligible_count'],'pending_slots':view['pending_count'],
        'reference_bounce_decomposition':decomposition,
        'original_cosine_convergence':{'levels':levels,'absolute_p99':errors,
            'observed_log_log_decay_exponent':exponent,'extrapolation':predictions,
            'scope':'Planning-only extrapolation, not cap evidence, eligibility or a new acceptance gate. '
                    'Two consecutive levels and all original tests still required.'},
        'candidate_180':{'complete':True,'all_pass':False,'levels':[
            {'spp':r['spp'],'ratio_to_original':r['absolute_p99_ratio_to_original_cosine'],
             'feasibility_pass':r['feasibility_pass']} for r in campaign['levels']]},
        'prior_timing_decisions':timing,
        'deferred_sizing_185':{'complete':True,'all_pass':True,'boundaries':16,
            'full_186_run':(RESULTS/'186-deferred-image-calibration-full-renderer.json').exists(),
            'scope':'Sizing evidence only; no full precision verdict and no causal proof of output-overhead hypothesis.'},
        'limits':'No sampler cause is inferred solely from full-frame energy decomposition. '
                 'No GPU clock/power/desktop cause is established by timing correlations. '
                 'No thresholds, seeds, cap, corpus, old evidence or scoring masks changed.',
        'tests':'NOT_RUN; retained scientific-data diagnosis only',
        'direct_error_1_0':'UNRESOLVED / 未解決; included without masks'}
    target.write_text(json.dumps(result, indent=2, allow_nan=False, ensure_ascii=False)+'\n')
    print(json.dumps({'decomposition':decomposition,'extrapolation':result['original_cosine_convergence'],
                      'output':str(target)},indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Plan 043: fresh C1 B8 8192/16384 feasibility, without reference admission."""
import argparse
import ctypes
import json
from pathlib import Path
import os
import resource
import subprocess
import sys
import time

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
import numpy as np
import qualify_references as Q
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files

SEEDS = list(Q.L.N007_SEEDS)
LEVELS = (8192, 16384)
KEYS = ('primary_hits', 'shadow_tests', 'shadow_blocked', 'backface_absorbed', 'proposal_null_samples')
PAYLOADS = tuple(f'.s{i}.{kind}' for i in range(4)
    for kind in ('f64', 'emission.pfm', 'direct.pfm', 'indirect.pfm', 'total.pfm'))+('.hits',)
CPU_LIMIT = 691200
AS_LIMIT = 4*1024**3


def prerequisites(inputs):
    proofs = {}
    for name in ('151-primary-direction-proposal-build.json', '152-primary-direction-physical-controls.json',
                 '153-primary-direction-all-state-and-prefix.json'):
        proof = read(RESULTS/name, inputs)
        if not proof['complete'] or not proof['all_pass']:
            raise ValueError('required complete PASS missing: '+name)
        check_files(proof['input_sha256'], inputs)
        proofs[name[:3]] = proof
    build, physical, prefix = (proofs[k] for k in ('151', '152', '153'))
    if not build['geometry_light_transport_source_unchanged'] or not build['sampling_physical_source_bytes_equal']:
        raise ValueError('sampling-only source proof missing')
    base = ROOT/'out/research/n010-comparison-readiness/primary-direction-build-v1'
    for directory, key in (('standalone', 'generated_sha256'), ('prefix', 'prefix_generated_sha256')):
        check_files({str(base/directory/name): h for name, h in build[key].items()}, inputs)
    if (physical['seeds'] != SEEDS or len(physical['rows']) != 17
        or len(physical['physical_checks']) != 8 or len(physical['iid_crosscheck']) != 2
        or not all(r['pass'] for key in ('rows', 'physical_checks', 'iid_crosscheck') for r in physical[key])):
        raise ValueError('physical proof scope differs')
    for row in physical['rows']:
        directory = Path(row['command'][row['command'].index('--out')+1]).parent
        check_files({str(directory/name): h for name, h in row['payload_sha256'].items()}, inputs)
    expected = {(f'C{i}', v) for i in range(1, 13) for v in (2, 8)}
    if (prefix['seeds'] != SEEDS or len(prefix['low_dose_rows']) != 24
        or {(r['cell'], r['vertices']) for r in prefix['low_dose_rows']} != expected
        or len(prefix['actual_level_rows']) != 2
        or {(r['cell'], r['vertices']) for r in prefix['actual_level_rows']} != {('C7', 2), ('C7', 8)}
        or len(prefix['process_attempts']) != 78
        or not all(r['pass'] for key in ('low_dose_rows', 'actual_level_rows', 'process_attempts') for r in prefix[key])):
        raise ValueError('all-state/prefix proof scope differs')
    for attempt in prefix['process_attempts']:
        if attempt['returncode'] != 0 or set(attempt['payload_sha256']) != set(PAYLOADS):
            raise ValueError('prefix proof invocation/payload scope differs')
        out = attempt['command'][attempt['command'].index('--out')+1]
        check_files({out+suffix: h for suffix, h in attempt['payload_sha256'].items()}, inputs)
    return base/'prefix/n010_primary_direction_prefix'


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing feasibility attempt')
    ctypes.CDLL(None).prctl(15, b'n010_dir_feas', 0, 0, 0)
    args.work = args.work.resolve()
    inputs = {str(p.resolve()): sha(p) for p in (
        Path(__file__), Path(Q.__file__), Path(Q.L.__file__), Path(Q.convergence.__file__),
        Path(sys.modules['inspect_hdr'].__file__), Q.NET,
        RESULTS.parent/'experiments/043-prospective-primary-direction-reference-sampling.md')}
    result = {'schema': 'n010-primary-direction-bounded-feasibility/1', 'complete': False, 'all_pass': False,
        'gpu_run': False, 'eligible_for_references': False, 'scoring_exclusions': 0,
        'classification': 'PREREQUISITES_UNCHECKED', 'input_sha256': inputs,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'threads': 16, 'seeds': SEEDS, 'selected_transport': 'C1_T_B8', 'levels': [], 'process_attempts': [],
        'limits': {'address_space_bytes': AS_LIMIT, 'cpu_seconds': CPU_LIMIT, 'elapsed_seconds': 43200},
        'feasibility_threshold': {'maximum_absolute_p99_ratio_each_level': 0.75, 'full_signal_support': 1.0},
        'scope': 'Fresh two-level practical feasibility only; no powered variance claim or corpus admission'}
    def save():
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    save()
    try:
        binary = prerequisites(inputs)
        baseline_directory = ROOT/'out/research/n010-comparison-readiness/references-recovery-sponza-v1/C1_T_B8'
        qualification = baseline_directory/'qualification.json'
        digest = '9da5eece00c7e1e490a35aefceb0a54f7ea42b0a90b4ad655d6713c482a9fa8f'
        if sha(qualification) != digest:
            raise ValueError('immutable original cosine baseline changed')
        baseline_q = read(qualification, inputs)
        if ([r['spp'] for r in baseline_q['levels']] != [8192, 16384, 32768, 65536]
            or baseline_q['cell'] != 'C1' or baseline_q['transport'] != 'T_B8'):
            raise ValueError('original cosine baseline scope differs')
        baseline = {r['spp']:r['screen']['rows'][-1] for r in baseline_q['levels'] if r['spp'] in LEVELS}
        for row in baseline_q['levels']:
            if row['spp'] in LEVELS:
                check_files({str(baseline_directory/name):h for name,h in row['all_payload_sha256'].items()}, inputs)
        result['baseline'] = {'method':'original cosine', 'qualification_sha256':digest,
            'qualification_path':str(qualification), 'levels':list(LEVELS)}
        lock = read(RESULTS/'026-dynamic-execution-state-lock.json', inputs)
        if set(lock['cells']) != {f'C{i}' for i in range(1, 13)}:
            raise ValueError('full locked corpus required')
        state = Q.L.read_state(ROOT/lock['cells']['C1']['state_directory'])
        if state['sha256'] != lock['cells']['C1']['state_sha256']:
            raise ValueError('C1 state changed')
        for p in (ROOT/lock['cells']['C1']['state_directory']).iterdir():
            if p.is_file():
                inputs[str(p.resolve())] = sha(p)
        scene = Q.scene_for_state(state, 8)
        args.work.mkdir(parents=True)
        scene_path = args.work/'scene.n008'
        scene_path.write_text(scene.text())
        (args.work/'retained-original-cosine-qualification.json').write_bytes(qualification.read_bytes())
        inputs[str(scene_path)] = sha(scene_path)
        if sha(scene_path) != baseline_q['scene_sha256']:
            raise ValueError('feasibility and baseline scenes differ')
        result.update(classification='ACQUIRING_UNADMITTED', scene_sha256=sha(scene_path),
                      state_sha256=state['sha256'], binary_sha256=sha(binary))
        previous = None
        manifests = []
        for spp in LEVELS:
            check_files(inputs, {})
            out = args.work/f'o.n{spp}'
            command = [str(binary), '--net', str(Q.NET), '--scene', str(scene_path), '--out', str(out),
                '--seeds', ','.join(map(str, SEEDS)), '--spp', str(spp), '--threads', '16']
            if previous:
                old_out = args.work/f'o.n{previous["spp"]}'
                command += ['--resume-prefix', str(old_out), '--resume-spp', str(previous['spp']),
                    '--resume-counters', ';'.join(','.join(str(r[k]) for k in KEYS) for r in previous['runs'])]
            receipt_path = args.work/f'n{spp}.resource-limits.json'
            def limits():
                resource.setrlimit(resource.RLIMIT_AS, (AS_LIMIT, AS_LIMIT))
                resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT, CPU_LIMIT))
                ticks = (Path('/proc')/str(os.getpid())/'stat').read_text().rsplit(')', 1)[1].split()[19]
                receipt_path.write_text(json.dumps({'pid': os.getpid(), 'start_ticks': int(ticks), 'uid': os.getuid(),
                    'cpu': list(resource.getrlimit(resource.RLIMIT_CPU)),
                    'address_space': list(resource.getrlimit(resource.RLIMIT_AS)), 'command': command})+'\n')
            attempt = {'command': command, 'pass': False, 'sample_interval': [previous['spp'] if previous else 0, spp]}
            result['process_attempts'].append(attempt)
            save()
            started = time.monotonic()
            try:
                proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                    timeout=43200, preexec_fn=limits)
            except subprocess.TimeoutExpired as error:
                (args.work/f'n{spp}.stdout.json').write_bytes(error.stdout or b'')
                (args.work/f'n{spp}.stderr.log').write_bytes(error.stderr or b'')
                raise ValueError('elapsed guard; partial outputs retained without retry')
            raw = args.work/f'n{spp}.stdout.json'; raw.write_text(proc.stdout)
            log = args.work/f'n{spp}.stderr.log'; log.write_text(proc.stderr)
            attempt.update(returncode=proc.returncode, stdout_sha256=sha(raw), stderr_sha256=sha(log),
                           wall_seconds_diagnostic=time.monotonic()-started)
            save()
            if proc.returncode:
                raise ValueError('feasibility native failed; no retry')
            receipt = read(receipt_path, inputs)
            if receipt['cpu'] != [CPU_LIMIT]*2 or receipt['address_space'] != [AS_LIMIT]*2 or receipt['command'] != command:
                raise ValueError('actual resource receipt differs')
            meta = json.loads(proc.stdout)
            if (meta['spp'] != spp or meta['seeds'] != SEEDS or len(meta['runs']) != 4
                or meta['scene_sha256'] != sha(scene_path) or meta['geometry_sha256'] != scene.geometry_sha256()):
                raise ValueError('native output identity differs')
            data = [Q.L.read_sidecar(Path(str(out)+f'.s{i}.f64')) for i in range(4)]
            if any(d['seed'] != seed or d['spp'] != spp or not all(np.isfinite(d[k]).all() and (d[k] >= 0).all()
                for k in ('mean', 'm2')) for d, seed in zip(data, SEEDS)):
                raise ValueError('native output header/finite/nonnegative failure')
            if any(not 0 <= r['proposal_null_samples'] <= spp*data[i]['width']*data[i]['height']
                   for i, r in enumerate(meta['runs'])):
                raise ValueError('null counter outside path bound')
            old_out = baseline_directory/f'o.n{spp}'
            original = [Q.L.read_sidecar(Path(str(old_out)+f'.s{i}.f64')) for i in range(4)]
            direct_exact = all(n[k][..., :2, :].tobytes() == o[k][..., :2, :].tobytes()
                for n, o in zip(data, original) for k in ('mean', 'm2'))
            deterministic_suffixes = ('.hits',)+tuple(f'.s{i}.{kind}.pfm' for i in range(4)
                for kind in ('direct', 'emission'))
            if not direct_exact or any(Path(str(out)+s).read_bytes() != Path(str(old_out)+s).read_bytes()
                                       for s in deterministic_suffixes):
                raise ValueError('C1 primary/direct/emission identity failure')
            payloads = {suffix: sha(Path(str(out)+suffix)) for suffix in PAYLOADS}
            inputs.update({str(out)+suffix: digest for suffix, digest in payloads.items()})
            metadata_path = args.work/f'n{spp}.meta.json'
            metadata_path.write_text(json.dumps(meta, indent=2)+'\n')
            inputs[str(metadata_path)] = sha(metadata_path)
            manifests.append({'spp': spp, 'references': [{'seed': seed, 'path': out.name+f'.s{i}.total.pfm',
                'sha256': payloads[f'.s{i}.total.pfm']} for i, seed in enumerate(SEEDS)]})
            manifest = args.work/f'screen-n{spp}.json'
            manifest.write_text(json.dumps({'schema_version': 1, 'source_commit': result['source_commit'],
                'scene_sha256': sha(scene_path), 'frame_state_sha256': state['sha256']['frame'], 'levels': manifests}, indent=2)+'\n')
            inputs[str(manifest)] = sha(manifest)
            screen = Q.assess(manifest)
            row = screen['rows'][-1]
            ratio = row['max_active_abs_p99']/baseline[spp]['max_active_abs_p99']
            result['levels'].append({'spp': spp, 'screen': screen, 'payload_sha256': payloads,
                'primary_direct_emission_exact_to_baseline': True,
                'resource_receipt_sha256': sha(receipt_path), 'absolute_p99_ratio_to_original_cosine': ratio,
                'feasibility_pass': bool(ratio <= 0.75 and row['active_fraction'] == 1.0
                    and (spp == LEVELS[0] or row['signal_support_stable_vs_previous']))})
            attempt['pass'] = True
            check_files(inputs, {})
            previous = meta
            save()
            print('C1_T_B8', spp, 'feasibility ratio', ratio, 'reference screen', screen['status'], flush=True)
        result['all_pass'] = len(result['levels']) == 2 and all(r['feasibility_pass'] for r in result['levels'])
        result['classification'] = 'BOUNDED_FEASIBILITY_PASS_NOT_ADMITTED' if result['all_pass'] else 'BOUNDED_FEASIBILITY_FAIL_STOP'
    except (ValueError, OSError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        result.update(classification='FAILED_PARTIALS_RETAINED_NO_RETRY', failure=str(error))
    result['complete'] = True
    save()
    raise SystemExit(0 if result['all_pass'] else 2)

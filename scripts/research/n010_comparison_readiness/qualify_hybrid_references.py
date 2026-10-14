#!/usr/bin/env python3
"""Acquire unchanged reference ladders only after complete hybrid proof gates."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

import numpy as np
import qualify_references as Q
import reference_provenance as provenance
import readiness_preflight as preflight
from reference_provenance import ROOT, RESULTS, sha, physical_proof
from readiness_preflight import replay

KEYS = ('primary_hits', 'shadow_tests', 'shadow_blocked', 'backface_absorbed')
BASE = ROOT/'out/research/n010-comparison-readiness/hybrid-oracle-build-v1'
PREFIX = ROOT/'out/research/n010-comparison-readiness/hybrid-prefix-build-v1'
BINARY = PREFIX/'phos-n010-hybrid-prefix'
SHADER = BASE/'hybrid.spv'
PLAN = RESULTS.parent/'experiments/029-hybrid-reference-acquisition.md'


def load(path, inputs):
    raw = path.read_bytes()
    inputs[str(path.resolve())] = sha(path)
    return json.loads(raw)


def check_files(mapping, inputs):
    for name, digest in mapping.items():
        path = Path(name)
        if not path.is_absolute():
            path = ROOT/path
        if sha(path) != digest:
            raise ValueError('proof artifact changed: '+str(path))
        key = str(path.resolve())
        if key in inputs and inputs[key] != digest:
            raise ValueError('conflicting proof identity: '+key)
        inputs[key] = digest


def prerequisites(inputs):
    physical_proof(inputs)
    build = load(RESULTS/'095-hybrid-oracle-build.json', inputs)
    prefix = load(RESULTS/'100-hybrid-prefix-build.json', inputs)
    for record, directory in ((build, BASE), (prefix, PREFIX)):
        if not record['complete'] or not record['all_pass']:
            raise ValueError('hybrid build is not complete/PASS')
        check_files(record['input_sha256'], inputs)
        check_files({str(directory/name): digest for name, digest
                     in record['generated_sha256'].items()}, inputs)
    if prefix['shared_shader_sha256'] != sha(SHADER):
        raise ValueError('prefix shared shader differs from validated base')
    full = load(RESULTS/'098-hybrid-full-numerical-conformance.json', inputs)
    if not full['complete'] or not full['all_pass']:
        raise ValueError('098 full numerical suite is not complete/PASS')
    expected = {(c, v, i) for c in ('C1', 'C7') for v in (2, 8) for i in range(4)}
    if len(full['rows']) != 16 or {(r['cell'], r['vertices'], r['seed_index'])
                                 for r in full['rows']} != expected:
        raise ValueError('098 numerical case coverage differs from protocol')
    check_files(full['input_sha256'], inputs)
    for row in full['rows']:
        if not row['pass']:
            raise ValueError('failed numerical case')
        path = Path(row['result'])
        if sha(path) != row['result_sha256']:
            raise ValueError('numerical child result changed')
        child = load(path, inputs)
        if not child['complete'] or not child['all_pass']:
            raise ValueError('incomplete numerical child')
        if ((child['cell'], child['vertices'], child['seed'])
                != (row['cell'], row['vertices'], Q.L.N007_SEEDS[row['seed_index']])
                or child['spp'] != 8192 or child['scoring_exclusions'] != 0
                or child['max_abs_mean'] > 1e-10 or child['max_abs_moment'] > 1e-10
                or child['indirect_nrmse'] > 1e-8 or not child['all_finite']
                or child['gpu_fault_flags'] or child['gpu_returncode']
                or child['cpu_counters'] != child['gpu_counters']
                or not all(child[k] for k in ('primary_records_byte_equal',
                    'direct_mean_byte_equal', 'emission_mean_byte_equal', 'owned_memory_replay_pass'))):
            raise ValueError('full numerical child violates unchanged gates')
        check_files(child['input_sha256'], inputs)
        # These identities are relative to the diagnostic work root, including gpu/.
        gpu_dir = Path(child['gpu_command'][-1])
        check_files({str(gpu_dir.parent/name): digest
                     for name, digest in child['payload_sha256'].items()}, inputs)
    physical = load(RESULTS/'099-hybrid-physical-controls.json', inputs)
    if not physical['complete'] or not physical['all_pass']:
        raise ValueError('099 physical controls are not complete/PASS')
    expected = {(name, i) for name in physical['frozen_scene_names'] for i in range(4)}
    if (len(physical['frozen_scene_names']) != 17 or len(physical['rows']) != 68
            or {(r['name'], r['seed_index']) for r in physical['rows']} != expected
            or len(physical['physical_checks']) != 8
            or not all(r['pass'] for r in physical['rows']+physical['physical_checks'])):
        raise ValueError('physical control coverage/gates differ from protocol')
    check_files(physical['input_sha256'], inputs)
    for row in physical['rows']:
        if (row['max_abs_mean'] > 1e-10 or row['max_abs_moment'] > 1e-10
                or row['indirect_nrmse'] is None or row['indirect_nrmse'] > 1e-8
                or row['fault_flags'] or row['returncode']
                or not all(row[k] for k in ('all_finite', 'primary_records_byte_equal',
                    'direct_mean_byte_equal', 'emission_mean_byte_equal', 'counters_equal',
                    'memory_replay', 'geometry_hash_match'))):
            raise ValueError('physical child violates unchanged numerical gates')
        out = Path(row['command'][-1])
        check_files({str(out/name): digest for name, digest in row['payload_sha256'].items()}, inputs)
    state = load(RESULTS/'101-hybrid-all-state-and-prefix.json', inputs)
    if not state['complete'] or not state['all_pass']:
        raise ValueError('101 all-state/prefix proof is not complete/PASS')
    low = {(f'C{c}', v, i) for c in range(1, 13) for v in (2, 8) for i in range(4)}
    high = {('C7', v, i) for v in (2, 8) for i in range(4)}
    for key, expected in (('low_dose_rows', low), ('actual_level_rows', high)):
        rows = state[key]
        if (len(rows) != len(expected) or {(r['cell'], r['vertices'], r['seed_index'])
                                         for r in rows} != expected
                or not all(r['pass'] for r in rows)):
            raise ValueError('all-state/prefix coverage/gates differ from protocol')
    for row in state['low_dose_rows']:
        if (not row['numerical_pass'] or not row['prefix_byte_equal']
                or row['max_abs_mean'] > 1e-10 or row['max_abs_moment'] > 1e-10
                or row['indirect_nrmse'] is None or row['indirect_nrmse'] > 1e-8
                or not all(row[k] for k in ('all_finite', 'primary_records_byte_equal',
                    'direct_mean_byte_equal', 'emission_mean_byte_equal', 'counters_equal',
                    'geometry_hash_match'))):
            raise ValueError('all-state child violates unchanged gates')
    check_files(state['input_sha256'], inputs)
    if len(state['process_attempts']) != 304:
        raise ValueError('incomplete prefix process evidence')
    for row in state['process_attempts']:
        if not row['pass'] or row['returncode']:
            raise ValueError('failed prefix child')
        cmd = row['command']
        out = Path(cmd[10])  # bash, wrapper, binary, scene, net, shader, seed, spp, batch, threads, out
        check_files({str(out/name): digest for name, digest in row['payload_sha256'].items()}, inputs)
        if not replay(load(out/'allocation-ledger.json', inputs)):
            raise ValueError('prefix owned memory replay failed')
    return {name: sha(RESULTS/name) for name in (
        '009-iid-precision-confirmation.json', '095-hybrid-oracle-build.json',
        '100-hybrid-prefix-build.json', '098-hybrid-full-numerical-conformance.json',
        '099-hybrid-physical-controls.json', '101-hybrid-all-state-and-prefix.json')}


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (172800, 172800))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lock', type=Path, required=True)
    ap.add_argument('--transports', nargs='+', required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--proof-only', action='store_true')
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing qualification work or result')
    ctypes.CDLL(None).prctl(15, b'n010_hyb_qual', 0, 0, 0)
    inputs = {}
    result = {'schema': 'n010-hybrid-reference-qualification/1', 'complete': False,
              'gpu_run': False, 'proof_only': a.proof_only, 'cells': [],
              'classification': 'PREREQUISITES_NOT_PROVEN', 'input_sha256': inputs,
              'selected_transports': a.transports, 'scoring_exclusions': 0,
              'work': str(a.work.resolve()), 'attempts': [], 'levels': list(Q.LEVELS),
              'seeds': list(Q.L.N007_SEEDS), 'batch': 16, 'cpu_fallback_threads': 16,
              'limits': {'address_space_bytes': 4*1024**3, 'cpu_seconds': 172800,
                         'elapsed_seconds_per_seed': 43200},
              'runtime': {'python': sys.version, 'numpy': np.__version__},
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              'scope': 'Fresh locked-state acquisition only; no current-view replacement or N010 readiness claim'}
    def save():
        a.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    try:
        lock = load(a.lock, inputs)
        if set(lock['cells']) != {f'C{i}' for i in range(1, 13)}:
            raise ValueError('full corpus lock required')
        allowed = {f'{c}_T_B{v}' for c in lock['cells'] for v in (2, 8)}
        if (not a.transports or len(set(a.transports)) != len(a.transports)
                or not set(a.transports) <= allowed):
            raise ValueError('unknown or duplicate transport')
        for path in (Path(__file__), Path(Q.__file__), Path(Q.L.__file__),
                     Path(Q.convergence.__file__), Path(provenance.__file__),
                     Path(preflight.__file__), Path(sys.executable), PLAN, Q.NET):
            inputs[str(path.resolve())] = sha(path)
        proofs = prerequisites(inputs)
        result['proof_sha256'] = proofs
        result['classification'] = 'PROOFS_PASS_ACQUISITION_NOT_RUN'
        if a.proof_only:
            result['complete'] = True
            save()
            return 0
        # Every dependency is now terminal. Freeze these identities before dispatch.
        def frozen():
            check_files(dict(inputs), {})
        a.work.mkdir(parents=True)
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = ':'.join(filter(None, [env.get('NIX_LD_LIBRARY_PATH'), env.get('LD_LIBRARY_PATH')]))
        for slot in a.transports:
            cell, v = slot.rsplit('_T_B', 1)
            vertices = int(v)
            spec = lock['cells'][cell]
            state = Q.L.read_state(ROOT/spec['state_directory'])
            if state['sha256'] != spec['state_sha256']:
                raise ValueError('locked state bytes changed')
            scene = Q.scene_for_state(state, vertices)
            out = a.work/slot
            out.mkdir()
            scene_path = out/'scene.n008'
            scene_path.write_text(scene.text())
            inputs[str(scene_path.resolve())] = sha(scene_path)
            levels, manifests, previous = [], [], None
            for spp in Q.LEVELS:
                frozen()
                runs = []
                dirs = []
                for i, seed in enumerate(Q.L.N007_SEEDS):
                    frozen()
                    for proc in Path('/proc').iterdir():
                        if not proc.name.isdigit():
                            continue
                        try:
                            comm = (proc/'comm').read_text().strip()
                        except OSError:
                            continue
                        if comm.startswith('phos-'):
                            raise ValueError('another GPU producer is active; no dispatch')
                    raw = out/f'n{spp}-seed{i}'
                    cmd = ['bash', 'scripts/run_with_vulkan.sh', str(BINARY), str(scene_path.resolve()),
                           str(Q.NET), str(SHADER), str(seed), str(spp), '16', '16', str(raw.resolve())]
                    start_spp = 0
                    if previous:
                        old = previous[i]
                        start_spp = spp//2
                        cmd += [str(old/'o.f64'), str(start_spp), str(old/'gpu.stats')]
                    attempt = {'command': cmd, 'sample_interval': [start_spp, spp],
                               'proof_sha256': proofs, 'pass': False}
                    result['attempts'].append(attempt)
                    attempt_path = out/f'n{spp}-seed{i}.attempt.json'
                    attempt_path.write_text(json.dumps(attempt, indent=2)+'\n')
                    result['gpu_run'] = True
                    save()
                    start = time.monotonic()
                    try:
                        proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True,
                                              text=True, timeout=43200, preexec_fn=limits)
                    except subprocess.TimeoutExpired as error:
                        for suffix, value in (('stdout', error.stdout), ('stderr', error.stderr)):
                            (out/f'n{spp}-seed{i}.{suffix}').write_bytes(
                                value if isinstance(value, bytes) else (value or '').encode())
                        attempt['failure'] = 'elapsed guard'
                        attempt_path.write_text(json.dumps(attempt, indent=2)+'\n')
                        raise ValueError('elapsed guard; partial attempt retained') from error
                    (out/f'n{spp}-seed{i}.stdout').write_text(proc.stdout)
                    (out/f'n{spp}-seed{i}.stderr').write_text(proc.stderr)
                    attempt.update(returncode=proc.returncode, wall_seconds_diagnostic=time.monotonic()-start,
                        stdout_sha256=sha(out/f'n{spp}-seed{i}.stdout'),
                        stderr_sha256=sha(out/f'n{spp}-seed{i}.stderr'))
                    attempt_path.write_text(json.dumps(attempt, indent=2)+'\n')
                    if proc.returncode:
                        raise ValueError('reference child failed; no automatic retry')
                    meta = load(raw/'gpu.json', inputs)
                    data = Q.L.read_sidecar(raw/'o.f64')
                    if (any(meta[k] != data[k] for k in ('seed', 'spp', 'width', 'height'))
                            or (data['seed'], data['spp'], data['width'], data['height'])
                            != (seed, spp, state['width'], state['height'])
                            or meta['vertices'] != vertices or meta['geometry_sha256'] != scene.geometry_sha256()
                            or meta['fault_flags'] or not meta['all_finite']
                            or not all(np.isfinite(x).all() for x in (data['mean'], data['m2']))
                            or 'AMD' not in meta['device']
                            or not replay(load(raw/'allocation-ledger.json', inputs))):
                        raise ValueError('reference identity/finite/device/fault/memory gate')
                    for suffix in ('f64', 'emission.pfm', 'direct.pfm', 'indirect.pfm', 'total.pfm'):
                        target = out/f'o.n{spp}.s{i}.{suffix}'
                        shutil.copyfile(raw/f'o.{suffix}', target)
                        inputs[str(target.resolve())] = sha(target)
                    hit = out/f'o.n{spp}.hits'
                    if i == 0:
                        shutil.copyfile(raw/'o.hits', hit)
                        inputs[str(hit.resolve())] = sha(hit)
                    elif (raw/'o.hits').read_bytes() != hit.read_bytes():
                        raise ValueError('replicate primary records differ')
                    attempt.update(payload_sha256={p.name: sha(p) for p in raw.iterdir() if p.is_file()})
                    attempt['pass'] = True
                    attempt_path.write_text(json.dumps(attempt, indent=2)+'\n')
                    inputs[str(attempt_path.resolve())] = sha(attempt_path)
                    check_files({str(raw/p): h for p, h in attempt['payload_sha256'].items()}, inputs)
                    runs.append({'seed': seed, **{k: meta[k] for k in KEYS},
                                 'raw_directory': str(raw.resolve()), 'sample_interval': [start_spp, spp],
                                 'fallback_report_scope': 'New sample interval only; total_paths is full target prefix'})
                    dirs.append(raw.resolve())
                frozen()
                prefix = out/f'o.n{spp}'
                manifests.append({'spp': spp, 'references': [
                    {'seed': seed, 'path': f'{prefix.name}.s{i}.total.pfm',
                     'sha256': sha(out/f'{prefix.name}.s{i}.total.pfm')}
                    for i, seed in enumerate(Q.L.N007_SEEDS)]})
                manifest = out/f'screen-n{spp}.json'
                manifest.write_text(json.dumps({'schema_version': 1, 'source_commit': result['source_commit'],
                    'scene_sha256': sha(scene_path), 'frame_state_sha256': state['sha256']['frame'],
                    'levels': manifests}, indent=2)+'\n')
                screen = Q.assess(manifest)
                means = np.stack([Q.L.read_sidecar(out/f'{prefix.name}.s{i}.f64')['mean'] for i in range(4)])
                payloads = {p.name: sha(p) for p in sorted(out.glob(f'o.n{spp}.*'))}
                metadata = {'spp': spp, 'seeds': list(Q.L.N007_SEEDS), 'runs': runs,
                    'binary_sha256': sha(BINARY), 'net_sha256': sha(Q.NET), 'shader_sha256': sha(SHADER),
                    'scene_sha256': sha(scene_path), 'geometry_sha256': scene.geometry_sha256(),
                    'proof_sha256': proofs, 'source_commit': result['source_commit'],
                    'computational_variant': 'validated-hybrid-numerical-port', 'all_payload_sha256': payloads}
                meta_path = out/f'n{spp}.meta.json'
                meta_path.write_text(json.dumps(metadata, indent=2)+'\n')
                levels.append({'spp': spp, 'screen': screen, 'geometry_hash_match': True,
                    'components_union_positive': {k: int((means[..., j, :].max(-1)>0).any(0).sum())
                                                   for j, k in enumerate(Q.L.COMPONENTS)},
                    'replicate_means_se_max': float((means.std(0, ddof=1)/2).max()),
                    'all_payload_sha256': payloads, 'metadata_sha256': sha(meta_path)})
                row = {'cell': cell, 'transport': 'T_B'+v, 'state_sha256': state['sha256'],
                    'scene_sha256': sha(scene_path), 'levels': levels, 'proof_sha256': proofs,
                    'computational_variant': 'validated-hybrid-numerical-port',
                    'classification': 'STATISTICALLY_ELIGIBLE'
                    if screen['status'] == 'statistical-screen-pass' else 'INELIGIBLE'}
                (out/'qualification.json').write_text(json.dumps(row, indent=2, allow_nan=False)+'\n')
                print(slot, spp, row['classification'], flush=True)
                previous = dirs
                if row['classification'] == 'STATISTICALLY_ELIGIBLE':
                    break
            result['cells'].append(row)
            save()
        frozen()
        result['complete'] = True
        result['classification'] = 'ACQUISITION_COMPLETE_REQUIRES_PROVENANCE_REVIEW'
        save()
        return 0
    except (ValueError, OSError, KeyError, AssertionError) as error:
        result['complete'] = True
        result['classification'] = 'STOPPED_RETAINED_FAILURE'
        result['failure'] = str(error)
        save()
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

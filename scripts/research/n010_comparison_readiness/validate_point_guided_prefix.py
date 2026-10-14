#!/usr/bin/env python3
"""Fail-closed all-state/direct and exact own-prefix proof for plan 031."""
import argparse
import ctypes
import json
from pathlib import Path
import resource
import subprocess
import time
import numpy as np
import qualify_references as Q
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files

KEYS = ('primary_hits', 'shadow_tests', 'shadow_blocked', 'backface_absorbed', 'proposal_null_samples')
PAYLOADS = tuple(f'.s{i}.{name}' for i in range(4)
    for name in ('f64', 'emission.pfm', 'direct.pfm', 'indirect.pfm', 'total.pfm')) + ('.hits',)


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (21600, 21600))


def wait_for(path, wait):
    while True:
        if path.exists():
            proof = json.loads(path.read_text())
            if proof.get('complete'):
                if not proof.get('all_pass'):
                    raise ValueError('required proof failed: '+path.name)
                return
        if not wait:
            raise ValueError('required proof incomplete: '+path.name)
        time.sleep(30)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--wait-for-physical-proof', action='store_true')
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing point-guided prefix acquisition')
    ctypes.CDLL(None).prctl(15, b'n010_guide_pfx', 0, 0, 0)
    wait_for(RESULTS/'113-point-guided-physical-controls.json', a.wait_for_physical_proof)
    inputs = {}
    proofs = {name: read(RESULTS/name, inputs) for name in (
        '112-point-guided-oracle-build.json', '113-point-guided-physical-controls.json',
        '114-point-guided-prefix-build.json', '078-all-state-cpu-port-controls.json')}
    for name, proof in proofs.items():
        if not proof['complete'] or not proof['all_pass']:
            raise ValueError('required proof incomplete/failed: '+name)
        check_files(proof['input_sha256'], inputs)
    physical = proofs['113-point-guided-physical-controls.json']
    if (len(physical['rows']) != 17 or len(physical['physical_checks']) != 8
        or len(physical['iid_crosscheck']) != 2
        or not all(r['pass'] for k in ('rows', 'physical_checks', 'iid_crosscheck') for r in physical[k])):
        raise ValueError('physical scope incomplete')
    for row in physical['rows']:
        directory = Path(row['command'][row['command'].index('--out')+1]).parent
        check_files({str(directory/name): h for name, h in row['payload_sha256'].items()}, inputs)
    builds = {}
    for number, directory, binary in (
        ('112', 'point-guided-oracle-build-v1', 'n010_point_guided_oracle'),
        ('114', 'point-guided-prefix-build-v1', 'n010_point_guided_prefix')):
        base = ROOT/'out/research/n010-comparison-readiness'/directory
        proof = next(v for k, v in proofs.items() if k.startswith(number))
        check_files({str(base/name): h for name, h in proof['generated_sha256'].items()}, inputs)
        builds[number] = base/binary
    for path in (Path(__file__), Path(Q.__file__), Path(Q.L.__file__), Q.NET,
                 RESULTS.parent/'experiments/031-point-guided-state-and-prefix-validation.md'):
        inputs[str(path.resolve())] = sha(path)
    lock = read(RESULTS/'016-corpus-state-lock.json', inputs)
    original = proofs['078-all-state-cpu-port-controls.json']
    expected = {(cell, vertices) for cell in lock['cells'] for vertices in (2, 8)}
    if (len(original['rows']) != 24 or {(r['cell'], r['vertices']) for r in original['rows']} != expected
        or original['spp'] != 16 or original['seeds'] != list(Q.L.N007_SEEDS)):
        raise ValueError('original control corpus/count/seeds differs')
    scenes = {}
    for slot in original['rows']:
        cell, vertices = slot['cell'], slot['vertices']
        directory = Path(slot['directory'])
        check_files({str(directory/name): h for name, h in slot['payload_sha256'].items()}, inputs)
        state = Q.L.read_state(ROOT/lock['cells'][cell]['state_directory'])
        if state['sha256'] != lock['cells'][cell]['state_sha256'] or state['sha256'] != slot['state_sha256']:
            raise ValueError('canonical state differs')
        for path in (ROOT/lock['cells'][cell]['state_directory']).iterdir():
            if path.is_file():
                inputs[str(path.resolve())] = sha(path)
        scene = directory/'scene.n008'
        if scene.read_text() != Q.scene_for_state(state, vertices).text() or sha(scene) != slot['scene_sha256']:
            raise ValueError('canonical scene differs')
        scenes[(cell, vertices)] = scene
    a.work.mkdir(parents=True)
    result = {'schema': 'n010-point-guided-all-state-and-prefix/1', 'complete': False, 'all_pass': False,
        'gpu_run': False, 'eligible_for_references': False, 'input_sha256': inputs,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'low_dose_rows': [], 'actual_level_rows': [], 'process_attempts': [], 'threads': 4,
        'seeds': list(Q.L.N007_SEEDS), 'thresholds': {'payload_byte_disagreements': 0, 'counter_disagreements': 0},
        'scope': 'All 24 locked slots/four seeds at 16 spp, own 8-to-16 prefix and both C7 8192-to-16384 prefixes; no statistical eligibility'}
    def save():
        a.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    def run(number, scene, spp, prefix, previous=None):
        check_files(inputs, {})
        command = [str(builds[number]), '--net', str(Q.NET), '--scene', str(scene), '--out', str(prefix.resolve()),
            '--seeds', ','.join(map(str, Q.L.N007_SEEDS)), '--spp', str(spp), '--threads', '4']
        if previous:
            old, meta = previous
            if meta['seeds'] != list(Q.L.N007_SEEDS) or meta['spp'] >= spp:
                raise ValueError('prefix identity mismatch')
            for suffix in PAYLOADS:
                path = Path(str(old)+suffix)
                inputs[str(path.resolve())] = sha(path)
            command += ['--resume-prefix', str(old.resolve()), '--resume-spp', str(meta['spp']), '--resume-counters',
                ';'.join(','.join(str(r[k]) for k in KEYS) for r in meta['runs'])]
        attempt = {'command': command, 'pass': False}
        result['process_attempts'].append(attempt)
        save()
        try:
            proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=3600, preexec_fn=limits)
        except subprocess.TimeoutExpired as error:
            Path(str(prefix)+'.stdout').write_bytes(error.stdout or b'')
            Path(str(prefix)+'.stderr').write_bytes(error.stderr or b'')
            raise ValueError('point-guided prefix elapsed guard; partial output retained')
        Path(str(prefix)+'.stdout').write_text(proc.stdout)
        Path(str(prefix)+'.stderr').write_text(proc.stderr)
        attempt['returncode'] = proc.returncode
        if proc.returncode:
            raise ValueError('point-guided prefix runtime failed')
        meta = json.loads(proc.stdout)
        if meta['spp'] != spp or meta['seeds'] != list(Q.L.N007_SEEDS) or meta['scene_sha256'] != sha(scene):
            raise ValueError('output scene/seed/count differs')
        data = [Q.L.read_sidecar(Path(str(prefix)+f'.s{i}.f64')) for i in range(4)]
        if any(d['seed'] != seed or d['spp'] != spp or not all(np.isfinite(d[k]).all() and (d[k] >= 0).all()
            for k in ('mean', 'm2')) for d, seed in zip(data, Q.L.N007_SEEDS)):
            raise ValueError('output header/finite/nonnegative gate')
        attempt.update(payload_sha256={s: sha(Path(str(prefix)+s)) for s in PAYLOADS})
        attempt['pass'] = True
        check_files(inputs, {})
        save()
        return meta, data
    def equal(left, lm, right, rm):
        return (all(Path(str(left)+s).read_bytes() == Path(str(right)+s).read_bytes() for s in PAYLOADS)
            and len(lm['runs']) == len(rm['runs']) == 4
            and all(all(x[k] == y[k] for k in ('seed',)+KEYS) for x, y in zip(lm['runs'], rm['runs'])))
    save()
    try:
        for slot in original['rows']:
            cell, vertices = slot['cell'], slot['vertices']
            scene = scenes[(cell, vertices)]
            directory = a.work/f'{cell}_T_B{vertices}'
            directory.mkdir()
            fresh = directory/'fresh16'
            fm, data = run('112', scene, 16, fresh)
            old = Path(slot['directory'])/'o'
            old_meta = json.loads((old.parent/'meta.json').read_text())
            original_data = [Q.L.read_sidecar(Path(str(old)+f'.s{i}.f64')) for i in range(4)]
            direct = all(n[k][..., :2, :].tobytes() == o[k][..., :2, :].tobytes()
                for n, o in zip(data, original_data) for k in ('mean', 'm2'))
            direct = direct and all(Path(str(fresh)+f'.s{i}.{component}.pfm').read_bytes()
                == Path(str(old)+f'.s{i}.{component}.pfm').read_bytes() for i in range(4) for component in ('direct', 'emission'))
            primary = Path(str(fresh)+'.hits').read_bytes() == Path(str(old)+'.hits').read_bytes()
            identity = (fm['geometry_sha256'] == old_meta['geometry_sha256']
                and all(all(n[k] == o[k] for k in ('width', 'height', 'spp', 'seed')) for n, o in zip(data, original_data)))
            row = {'cell': cell, 'vertices': vertices, 'direct_emission_exact': direct,
                'primary_records_exact': primary, 'geometry_headers_exact': identity, 'pass': False}
            result['low_dose_rows'].append(row)
            save()
            if not direct or not primary or not identity:
                raise ValueError('all-state direct/primary identity gate')
            small = directory/'prefix8'
            sm, _ = run('114', scene, 8, small)
            restored = directory/'restored16'
            rm, _ = run('114', scene, 16, restored, (small, sm))
            row['prefix_bytes_and_counters_exact'] = equal(fresh, fm, restored, rm)
            row['pass'] = row['prefix_bytes_and_counters_exact']
            save()
            print(cell, vertices, 'PASS' if row['pass'] else 'FAIL', flush=True)
            if not row['pass']:
                raise ValueError('all-state own-prefix mismatch')
        for vertices in (2, 8):
            directory = a.work/f'actual-C7-B{vertices}'
            directory.mkdir()
            scene = scenes[('C7', vertices)]
            fresh, small, restored = (directory/name for name in ('fresh16384', 'prefix8192', 'restored16384'))
            fm, _ = run('112', scene, 16384, fresh)
            sm, _ = run('114', scene, 8192, small)
            rm, _ = run('114', scene, 16384, restored, (small, sm))
            row = {'cell': 'C7', 'vertices': vertices, 'sample_interval': [8192, 16384],
                'pass': equal(fresh, fm, restored, rm)}
            result['actual_level_rows'].append(row)
            save()
            print('actual-prefix', vertices, 'PASS' if row['pass'] else 'FAIL', flush=True)
            if not row['pass']:
                raise ValueError('actual-level own-prefix mismatch')
        check_files(inputs, {})
        result['all_pass'] = (len(result['low_dose_rows']) == 24 and all(r['pass'] for r in result['low_dose_rows'])
            and len(result['actual_level_rows']) == 2 and all(r['pass'] for r in result['actual_level_rows'])
            and len(result['process_attempts']) == 78 and all(r['pass'] for r in result['process_attempts']))
    except (ValueError, OSError, KeyError, AssertionError) as error:
        result['failure'] = str(error)
    result['complete'] = True
    save()
    print('POINT-GUIDED STATE/PREFIX', 'PASS' if result['all_pass'] else 'FAIL', flush=True)
    raise SystemExit(0 if result['all_pass'] else 2)

#!/usr/bin/env python3
"""Audit hybrid raw prefix exports and qualified ladders without acquiring samples."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import numpy as np
import qualify_references as Q
import reference_provenance as original
import qualify_hybrid_references as acquisition
from readiness_preflight import replay

ROOT, RESULTS, sha, read = original.ROOT, original.RESULTS, original.sha, original.read
COUNTERS = acquisition.KEYS


def helper_identities(inputs):
    for path in (Path(__file__), Path(acquisition.__file__), Path(Q.__file__),
                 Path(Q.L.__file__), Path(Q.convergence.__file__), Path(original.__file__),
                 ROOT/'scripts/research/n010_comparison_readiness/readiness_preflight.py'):
        inputs[str(path.resolve())] = sha(path)


def audit_raw(directory, inputs, expected=None):
    directory = directory.resolve()
    names = {'o.f64', 'o.hits', 'gpu.stats', 'gpu.json', 'hybrid.json',
             'allocation-ledger.json'} | {f'o.{name}.pfm' for name in Q.L.COMPONENTS}
    for name in names:
        inputs[str(directory/name)] = sha(directory/name)
    meta = read(directory/'gpu.json', inputs)
    fallback = read(directory/'hybrid.json', inputs)
    data = Q.L.read_sidecar(directory/'o.f64')
    shape = (data['width'], data['height'], data['spp'], data['seed'])
    if shape != tuple(meta[k] for k in ('width', 'height', 'spp', 'seed')):
        raise ValueError('raw metadata/sidecar header mismatch')
    if expected and shape != expected:
        raise ValueError('raw output differs from frozen state/level/seed')
    if (meta['fault_flags'] or not meta['all_finite'] or 'AMD' not in meta['device']
            or not all(np.isfinite(v).all() and (v >= 0).all()
                       for v in (data['mean'], data['m2']))):
        raise ValueError('raw device/finite/fault/physical radiance failure')
    dtype = np.dtype([('sum', '<f8', (4, 4)), ('sum2', '<f8', (4, 4)),
                      ('counters', '<u8', (4,))])
    if dtype.itemsize != 288:
        raise ValueError('GStats ABI mismatch')
    raw = (directory/'gpu.stats').read_bytes()
    pixels = data['width']*data['height']
    if len(raw) != pixels*288:
        raise ValueError('raw prefix counter/sum length mismatch')
    values = np.frombuffer(raw, dtype=dtype).reshape(data['height'], data['width'])
    for field, component in (('sum', 'mean'), ('sum2', 'm2')):
        rgb = values[field][..., :3]
        if (not np.isfinite(values[field]).all() or (rgb < 0).any()
                or (values[field][..., 3] != 0).any()
                or (rgb/data['spp']).tobytes() != data[component].tobytes()
                or (data[component]*data['spp']).tobytes() != rgb.tobytes()):
            raise ValueError('raw sums and binary64 means/moments are not bit exact')
    actual = {key: sum(int(x) for x in values['counters'][..., i].ravel())
              for i, key in enumerate(COUNTERS)}
    if any(actual[k] != meta[k] for k in COUNTERS):
        raise ValueError('per-pixel raw counters do not reproduce global metadata')
    for i, name in enumerate(Q.L.COMPONENTS):
        image = Q.L.read_pfm(directory/f'o.{name}.pfm')
        if not np.array_equal(image, data['mean'][..., i, :].astype(np.float32)):
            raise ValueError('PFM differs from rounded binary64 component: '+name)
    hits = (directory/'o.hits').read_bytes()
    if (len(hits) != 16+pixels*16 or hits[:8] != b'N008HIT\0'
            or struct.unpack_from('<2I', hits, 8) != shape[:2]):
        raise ValueError('primary-record header/length mismatch')
    if (fallback['total_paths'] != pixels*data['spp'] or fallback['batch'] != 16
            or fallback['cpu_threads'] != 16 or fallback['cpu_fallback_paths'] < 0
            or fallback['cpu_fallback_paths'] > fallback['total_paths']
            or not replay(read(directory/'allocation-ledger.json', inputs))):
        raise ValueError('fallback scope or owned memory replay failure')
    return {'directory': str(directory), 'width': shape[0], 'height': shape[1],
            'spp': shape[2], 'seed': shape[3], 'counters': actual,
            'raw_sum_mean_moment_bit_exact': True, 'all_component_pfms_equal': True,
            'memory_replay_pass': True, 'pass': True}


def verify_reference(directory, cell, vertices, spec, inputs, require_eligible=True):
    helper_identities(inputs)
    directory = directory.resolve()
    q = read(directory/'qualification.json', inputs)
    if q.get('computational_variant') != 'validated-hybrid-numerical-port':
        return original.verify_reference(directory, cell, vertices, spec, inputs, require_eligible)
    proofs = acquisition.prerequisites(inputs)
    if q['proof_sha256'] != proofs or (q['cell'], q['transport'], q['state_sha256']) != (
            cell, f'T_B{vertices}', spec['state_sha256']):
        raise ValueError('hybrid proof/state/transport identity mismatch')
    state = Q.L.read_state(ROOT/spec['state_directory'])
    scene = Q.scene_for_state(state, vertices)
    if state['sha256'] != spec['state_sha256'] or (directory/'scene.n008').read_text() != scene.text():
        raise ValueError('hybrid scene is not the canonical locked state')
    if q['scene_sha256'] != sha(directory/'scene.n008'):
        raise ValueError('hybrid scene identity mismatch')
    inputs[str(directory/'scene.n008')] = q['scene_sha256']
    levels = q['levels']
    if (not (2 if require_eligible else 1) <= len(levels) <= len(Q.LEVELS)
            or [l['spp'] for l in levels] != list(Q.LEVELS[:len(levels)])):
        raise ValueError('hybrid levels are not the complete fixed prefix')
    previous = None
    for level in levels:
        spp = level['spp']
        expected = {f'o.n{spp}.hits'} | {f'o.n{spp}.s{i}.{suffix}' for i in range(4)
            for suffix in ('f64', 'emission.pfm', 'direct.pfm', 'indirect.pfm', 'total.pfm')}
        if set(level['all_payload_sha256']) != expected or not level['geometry_hash_match']:
            raise ValueError('hybrid reference payload/geometry gate')
        acquisition.check_files({str(directory/name): digest for name, digest
                                 in level['all_payload_sha256'].items()}, inputs)
        meta_path = directory/f'n{spp}.meta.json'
        meta = read(meta_path, inputs)
        if (level['metadata_sha256'] != sha(meta_path) or meta['spp'] != spp
                or meta['seeds'] != list(Q.L.N007_SEEDS) or len(meta['runs']) != 4
                or meta['proof_sha256'] != proofs or meta['binary_sha256'] != sha(acquisition.BINARY)
                or meta['shader_sha256'] != sha(acquisition.SHADER) or meta['net_sha256'] != sha(Q.NET)
                or meta['geometry_sha256'] != scene.geometry_sha256()
                or meta['scene_sha256'] != q['scene_sha256']
                or meta['all_payload_sha256'] != level['all_payload_sha256']
                or meta['computational_variant'] != q['computational_variant']):
            raise ValueError('hybrid level metadata/build identity mismatch')
        means = []
        for i, seed in enumerate(Q.L.N007_SEEDS):
            raw = directory/f'n{spp}-seed{i}'
            attempt = read(directory/f'n{spp}-seed{i}.attempt.json', inputs)
            cmd = ['bash', 'scripts/run_with_vulkan.sh', str(acquisition.BINARY),
                   str(directory/'scene.n008'), str(Q.NET), str(acquisition.SHADER),
                   str(seed), str(spp), '16', '16', str(raw)]
            start = previous['spp'] if previous else 0
            if previous:
                old = directory/f'n{start}-seed{i}'
                cmd += [str(old/'o.f64'), str(start), str(old/'gpu.stats')]
            run = meta['runs'][i]
            if (not attempt['pass'] or attempt['returncode'] or attempt['command'] != cmd
                    or attempt['sample_interval'] != [start, spp] or attempt['proof_sha256'] != proofs
                    or run['seed'] != seed or run['sample_interval'] != [start, spp]
                    or run['raw_directory'] != str(raw)):
                raise ValueError('hybrid deterministic seed/interval/prefix command differs')
            if set(attempt['payload_sha256']) != {p.name for p in raw.iterdir() if p.is_file()}:
                raise ValueError('hybrid raw output inventory differs')
            acquisition.check_files({str(raw/name): h for name, h in attempt['payload_sha256'].items()}, inputs)
            checked = audit_raw(raw, inputs, (state['width'], state['height'], spp, seed))
            g = read(raw/'gpu.json', inputs)
            f = read(raw/'hybrid.json', inputs)
            if (g['geometry_sha256'] != scene.geometry_sha256() or g['vertices'] != vertices
                    or any(run[k] != checked['counters'][k] for k in COUNTERS)
                    or f['cpu_fallback_paths'] > state['width']*state['height']*(spp-start)):
                raise ValueError('hybrid geometry/counter/fallback interval mismatch')
            for suffix in ('f64', 'emission.pfm', 'direct.pfm', 'indirect.pfm', 'total.pfm'):
                if sha(directory/f'o.n{spp}.s{i}.{suffix}') != sha(raw/f'o.{suffix}'):
                    raise ValueError('hybrid reference copy differs from raw output')
            if sha(directory/f'o.n{spp}.hits') != sha(raw/'o.hits'):
                raise ValueError('hybrid primary reference copy differs')
            means.append(Q.L.read_sidecar(raw/'o.f64')['mean'])
        manifest = directory/f'screen-n{spp}.json'
        read(manifest, inputs)
        screen = Q.assess(manifest)
        stack = np.stack(means)
        positive = {k: int((stack[..., j, :].max(-1)>0).any(0).sum())
                    for j, k in enumerate(Q.L.COMPONENTS)}
        if (screen != level['screen'] or screen['scene_sha256'] != q['scene_sha256']
                or screen['frame_state_sha256'] != spec['state_sha256']['frame']
                or positive != level['components_union_positive']
                or float((stack.std(0, ddof=1)/2).max()) != level['replicate_means_se_max']):
            raise ValueError('hybrid convergence/support/replicate summaries differ')
        previous = level
    classification = ('STATISTICALLY_ELIGIBLE' if levels[-1]['screen']['status'] == 'statistical-screen-pass'
                      else 'INELIGIBLE')
    if (q['classification'] != classification
            or any(l['screen']['status'] == 'statistical-screen-pass' for l in levels[:-1])
            or (require_eligible and classification != 'STATISTICALLY_ELIGIBLE')):
        raise ValueError('hybrid classification or first qualifying stop differs')
    return {'cell': cell, 'transport': f'T_B{vertices}', 'directory': str(directory),
            'computational_variant': q['computational_variant'], 'pass': True,
            'levels': [l['spp'] for l in levels], 'qualification_sha256': sha(directory/'qualification.json')}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw-results', type=Path, nargs='+', required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.output.exists():
        raise ValueError('refuse existing audit result')
    inputs = {str(Path(__file__).resolve()): sha(Path(__file__))}
    helper_identities(inputs)
    result = {'schema': 'n010-hybrid-raw-prefix-audit/1', 'complete': False, 'all_pass': False,
              'gpu_run': False, 'classification': 'RAW_EXPORT_AUDIT_ONLY_NOT_REFERENCE_ELIGIBILITY',
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              'inputs': inputs, 'rows': [], 'scoring_exclusions': 0}
    for path in a.raw_results:
        try:
            child = read(path, inputs)
            if not child['complete'] or not child['all_pass']:
                raise ValueError('raw source is not a complete/PASS diagnostic')
            acquisition.check_files(child['input_sha256'], inputs)
            directory = Path(child['gpu_command'][-1])
            acquisition.check_files({str(directory.parent/name): h for name, h
                                     in child['payload_sha256'].items()}, inputs)
            row = audit_raw(directory, inputs)
            row['source_result'] = str(path)
        except (ValueError, OSError, KeyError, AssertionError) as error:
            row = {'source_result': str(path), 'pass': False, 'reason': str(error)}
        result['rows'].append(row)
    result['complete'] = True
    result['all_pass'] = bool(result['rows']) and all(r['pass'] for r in result['rows'])
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print('RAW EXPORT AUDIT', 'PASS' if result['all_pass'] else 'FAIL')
    raise SystemExit(0 if result['all_pass'] else 2)

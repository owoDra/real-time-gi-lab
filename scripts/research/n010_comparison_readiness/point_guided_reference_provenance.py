#!/usr/bin/env python3
"""Fail-closed provenance for a separately validated sampling distribution."""
import json
from pathlib import Path
import struct
import numpy as np
import qualify_references as Q
import hybrid_reference_provenance as previous_api
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files

VARIANT = 'validated-point-guided-mixture'
BINARY = ROOT/'out/research/n010-comparison-readiness/point-guided-prefix-build-v1/n010_point_guided_prefix'
KEYS = ('primary_hits', 'shadow_tests', 'shadow_blocked', 'backface_absorbed', 'proposal_null_samples')
PROOFS = ('112-point-guided-oracle-build.json', '113-point-guided-physical-controls.json',
          '114-point-guided-prefix-build.json', '115-point-guided-all-state-and-prefix.json')
SELECTED = ('C1_T_B8', 'C2_T_B8', 'C3_T_B8', 'C4_T_B2', 'C4_T_B8',
            'C5_T_B2', 'C5_T_B8', 'C6_T_B2', 'C6_T_B8')


def prerequisites(inputs):
    proofs = {}
    for name in PROOFS:
        proof = read(RESULTS/name, inputs)
        proofs[name] = proof
        if not proof['complete'] or not proof['all_pass']:
            raise ValueError('guided prerequisite incomplete/failed: '+name)
        check_files(proof['input_sha256'], inputs)
    for number, directory in (('112', 'point-guided-oracle-build-v1'), ('114', 'point-guided-prefix-build-v1')):
        proof = next(v for name, v in proofs.items() if name.startswith(number))
        root = ROOT/'out/research/n010-comparison-readiness'/directory
        check_files({str(root/name): h for name, h in proof['generated_sha256'].items()}, inputs)
    if not proofs[PROOFS[2]]['sampling_physical_source_bytes_equal']:
        raise ValueError('guided continuation changed sampling/physics')
    physical = proofs[PROOFS[1]]
    if (len(physical['rows']) != 17 or len(physical['physical_checks']) != 8 or len(physical['iid_crosscheck']) != 2
        or not all(row['pass'] for key in ('rows', 'physical_checks', 'iid_crosscheck') for row in physical[key])
        or physical['seeds'] != list(Q.L.N007_SEEDS)):
        raise ValueError('guided physical proof scope/gates differs')
    for row in physical['rows']:
        prefix = Path(row['command'][row['command'].index('--out')+1])
        check_files({str(prefix.parent/name): h for name, h in row['payload_sha256'].items()}, inputs)
    state = proofs[PROOFS[3]]
    if (len(state['low_dose_rows']) != 24 or len(state['actual_level_rows']) != 2
        or len(state['process_attempts']) != 78 or state['seeds'] != list(Q.L.N007_SEEDS)
        or {(r['cell'], r['vertices']) for r in state['low_dose_rows']}
            != {(f'C{i}', v) for i in range(1, 13) for v in (2, 8)}
        or {(r['cell'], r['vertices']) for r in state['actual_level_rows']} != {('C7', 2), ('C7', 8)}
        or not all(r['pass'] for key in ('low_dose_rows', 'actual_level_rows', 'process_attempts') for r in state[key])):
        raise ValueError('guided all-state/prefix proof scope differs')
    for attempt in state['process_attempts']:
        prefix = Path(attempt['command'][attempt['command'].index('--out')+1])
        check_files({str(prefix)+suffix: h for suffix, h in attempt['payload_sha256'].items()}, inputs)
    for path in (Path(__file__), Path(Q.__file__), Path(Q.L.__file__), Path(Q.convergence.__file__),
                 Q.NET, RESULTS.parent/'experiments/032-point-guided-reference-qualification.md'):
        inputs[str(path.resolve())] = sha(path)
    return {name: sha(RESULTS/name) for name in PROOFS}


def verify_reference(directory, cell, vertices, spec, inputs, require_eligible=True):
    directory = directory.resolve()
    q = read(directory/'qualification.json', inputs)
    if q.get('computational_variant') != VARIANT:
        return previous_api.verify_reference(directory, cell, vertices, spec, inputs, require_eligible)
    proofs = prerequisites(inputs)
    acquisition = Path(__file__).with_name('qualify_point_guided_references.py')
    inputs[str(acquisition)] = sha(acquisition)
    if (q['proof_sha256'] != proofs or (q['cell'], q['transport'], q['state_sha256'])
        != (cell, f'T_B{vertices}', spec['state_sha256'])):
        raise ValueError('guided physical state/proof identity mismatch')
    state = Q.L.read_state(ROOT/spec['state_directory'])
    if state['sha256'] != spec['state_sha256']:
        raise ValueError('guided canonical state differs')
    for p in (ROOT/spec['state_directory']).iterdir():
        if p.is_file():
            inputs[str(p.resolve())] = sha(p)
    scene = Q.scene_for_state(state, vertices)
    scene_path = directory/'scene.n008'
    if scene_path.read_text() != scene.text() or sha(scene_path) != q['scene_sha256']:
        raise ValueError('guided scene differs from canonical locked state')
    inputs[str(scene_path)] = sha(scene_path)
    original = read(RESULTS/'078-all-state-cpu-port-controls.json', inputs)
    slot = next(r for r in original['rows'] if (r['cell'], r['vertices']) == (cell, vertices))
    hit_path = Path(slot['directory'])/'o.hits'
    if sha(hit_path) != slot['payload_sha256']['o.hits']:
        raise ValueError('retained original primary bytes changed')
    inputs[str(hit_path)] = sha(hit_path)
    levels = q['levels']
    if (not (2 if require_eligible else 1) <= len(levels) <= len(Q.LEVELS)
        or [l['spp'] for l in levels] != list(Q.LEVELS[:len(levels)])):
        raise ValueError('guided ladder is not the complete frozen prefix')
    previous = None
    for level in levels:
        spp = level['spp']
        names = {f'o.n{spp}.hits'} | {f'o.n{spp}.s{i}.{suffix}' for i in range(4)
            for suffix in ('f64', 'emission.pfm', 'direct.pfm', 'indirect.pfm', 'total.pfm')}
        if set(level['all_payload_sha256']) != names or not level['geometry_hash_match']:
            raise ValueError('guided reference output inventory/geometry differs')
        check_files({str(directory/name): h for name, h in level['all_payload_sha256'].items()}, inputs)
        meta_path = directory/f'n{spp}.meta.json'
        meta = read(meta_path, inputs)
        interval = [previous['spp'] if previous else 0, spp]
        if (level['metadata_sha256'] != sha(meta_path) or meta['proof_sha256'] != proofs
            or meta['spp'] != spp or meta['seeds'] != list(Q.L.N007_SEEDS) or len(meta['runs']) != 4
            or meta['binary_sha256'] != sha(BINARY) or meta['net_sha256'] != sha(Q.NET)
            or meta['scene_sha256'] != q['scene_sha256'] or meta['geometry_sha256'] != scene.geometry_sha256()
            or meta['computational_variant'] != VARIANT or meta['sample_interval'] != interval
            or meta['all_payload_sha256'] != level['all_payload_sha256']):
            raise ValueError('guided reference metadata identity differs')
        cmd = [str(BINARY), '--net', str(Q.NET), '--scene', str(scene_path), '--out', str(directory/f'o.n{spp}'),
            '--seeds', ','.join(map(str, Q.L.N007_SEEDS)), '--spp', str(spp), '--threads', '16']
        if previous:
            pm = read(directory/f'n{previous["spp"]}.meta.json', inputs)
            cmd += ['--resume-prefix', str(directory/f'o.n{previous["spp"]}'), '--resume-spp', str(previous['spp']),
                '--resume-counters', ';'.join(','.join(str(r[k]) for k in KEYS) for r in pm['runs'])]
            if (meta['previous_metadata_sha256'] != sha(directory/f'n{previous["spp"]}.meta.json')
                or meta['previous_payload_sha256'] != previous['all_payload_sha256']):
                raise ValueError('guided own-prefix chain differs')
        elif meta['previous_payload_sha256']:
            raise ValueError('guided fresh level imported a prefix')
        attempt = read(directory/f'n{spp}.attempt.json', inputs)
        if (not attempt['pass'] or attempt['returncode'] != 0 or attempt['command'] != cmd
            or attempt['sample_interval'] != interval or attempt['proof_sha256'] != proofs
            or attempt['previous_payload_sha256'] != meta['previous_payload_sha256']):
            raise ValueError('guided deterministic acquisition command differs')
        check_files(attempt['input_sha256'], inputs)
        raw_path = directory/f'n{spp}.stdout.json'
        if sha(raw_path) != attempt['stdout_sha256'] or sha(directory/f'n{spp}.stderr.log') != attempt['stderr_sha256']:
            raise ValueError('guided retained execution output differs')
        raw_meta = read(raw_path, inputs)
        inputs[str(directory/f'n{spp}.stderr.log')] = attempt['stderr_sha256']
        if any(raw_meta[k] != meta[k] for k in ('seeds', 'spp', 'scene_sha256', 'geometry_sha256', 'runs')):
            raise ValueError('guided enriched metadata differs from actual stdout')
        stack = []
        for i, seed in enumerate(Q.L.N007_SEEDS):
            data = Q.L.read_sidecar(directory/f'o.n{spp}.s{i}.f64')
            if ((data['width'], data['height'], data['spp'], data['seed']) != (state['width'], state['height'], spp, seed)
                or not all(np.isfinite(data[k]).all() and (data[k] >= 0).all() for k in ('mean', 'm2'))
                or meta['runs'][i]['seed'] != seed):
                raise ValueError('guided finite/replicate/header gate')
            for j, component in enumerate(Q.L.COMPONENTS):
                if not np.array_equal(Q.L.read_pfm(directory/f'o.n{spp}.s{i}.{component}.pfm'),
                                      data['mean'][..., j, :].astype(np.float32)):
                    raise ValueError('guided component PFM differs from binary64 mean')
            run = meta['runs'][i]
            if (any(not isinstance(run[k], int) or run[k] < 0 for k in KEYS)
                or run['primary_hits'] > state['width']*state['height']*spp
                or run['proposal_null_samples'] > state['width']*state['height']*spp
                or run['shadow_blocked'] > run['shadow_tests']):
                raise ValueError('guided counters violate path bounds')
            stack.append(data['mean'])
        hits = (directory/f'o.n{spp}.hits').read_bytes()
        if (hits != hit_path.read_bytes() or len(hits) != 16+state['width']*state['height']*16
            or hits[:8] != b'N008HIT\0' or struct.unpack_from('<2I', hits, 8) != (state['width'], state['height'])):
            raise ValueError('guided primary records differ from retained canonical control')
        manifest_path = directory/f'screen-n{spp}.json'
        manifest = read(manifest_path, inputs)
        expected_levels = [{'spp': l['spp'], 'references': [{'seed': seed,
            'path': f'o.n{l["spp"]}.s{i}.total.pfm', 'sha256': l['all_payload_sha256'][f'o.n{l["spp"]}.s{i}.total.pfm']}
            for i, seed in enumerate(Q.L.N007_SEEDS)]} for l in levels if l['spp'] <= spp]
        actual = Q.assess(manifest_path)
        means = np.stack(stack)
        positive = {k: int((means[..., j, :].max(-1)>0).any(0).sum()) for j, k in enumerate(Q.L.COMPONENTS)}
        if (manifest['levels'] != expected_levels or manifest['scene_sha256'] != q['scene_sha256']
            or manifest['frame_state_sha256'] != spec['state_sha256']['frame']
            or actual != level['screen'] or level['components_union_positive'] != positive
            or level['replicate_means_se_max'] != float((means.std(0, ddof=1)/2).max())):
            raise ValueError('guided unchanged screen/support/uncertainty replay differs')
        previous = level
    classification = 'STATISTICALLY_ELIGIBLE' if levels[-1]['screen']['status'] == 'statistical-screen-pass' else 'INELIGIBLE'
    if (q['classification'] != classification
        or any(l['screen']['status'] == 'statistical-screen-pass' for l in levels[:-1])):
        raise ValueError('guided classifier or first qualifying stop differs')
    if require_eligible and classification != 'STATISTICALLY_ELIGIBLE':
        raise ValueError('guided reference is not statistically eligible')
    check_files(inputs, {})
    return {'cell': cell, 'transport': f'T_B{vertices}', 'directory': str(directory),
        'computational_variant': VARIANT, 'levels': [l['spp'] for l in levels],
        'qualification_sha256': sha(directory/'qualification.json'), 'pass': True}

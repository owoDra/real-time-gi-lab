#!/usr/bin/env python3
"""Validate the original or exact-prefix reference chain without acquiring samples."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import qualify_references as Q

ROOT = Q.ROOT
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path, inputs):
    raw = path.read_bytes()
    inputs[str(path.resolve())] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)

def physical_proof(inputs):
    proof = read(RESULTS/'009-iid-precision-confirmation.json', inputs)
    if not (proof['complete'] and proof['all_pass']):
        raise ValueError('physical sampler proof incomplete/failed')
    if proof['binary_sha256'] != sha(Q.BINARY) or proof['sobol_table_sha256'] != sha(Q.NET):
        raise ValueError('physical sampler binary/net identity mismatch')
    return proof

def incremental_proofs(inputs):
    physical_proof(inputs)
    from qualify_incremental_references import dependencies
    return dependencies()

def verify_reference(directory, cell, vertices, spec, inputs, require_eligible=True):
    directory = directory.resolve()
    q = read(directory/'qualification.json', inputs)
    if (q['cell'], q['transport'], q['state_sha256']) != (cell, f'T_B{vertices}', spec['state_sha256']):
        raise ValueError('reference state/cell/transport differs from lock')
    state = Q.L.read_state(ROOT/spec['state_directory'])
    if state['sha256'] != spec['state_sha256']:
        raise ValueError('physical state bytes differ from lock')
    scene = Q.scene_for_state(state, vertices)
    scene_path = directory/'scene.n008'
    if scene_path.read_text() != scene.text() or q['scene_sha256'] != sha(scene_path):
        raise ValueError('reference physical scene differs from canonical locked state')
    inputs[str(scene_path)] = sha(scene_path)
    levels = q['levels']
    if [level['spp'] for level in levels] != list(Q.LEVELS[:len(levels)]) or not (2 if require_eligible else 1) <= len(levels) <= len(Q.LEVELS):
        raise ValueError('reference levels are not the complete frozen prefix')
    variant = q.get('computational_variant', 'original-full-prefix')
    if variant not in ('original-full-prefix', 'exact-prefix-continuation', 'proved-exact-prefix-recovery'):
        raise ValueError('unknown computational variant')
    proofs = incremental_proofs(inputs) if variant != 'original-full-prefix' else None
    if proofs is not None:
        if q['proof_sha256'] != proofs:
            raise ValueError('qualification proof dependency mismatch')
        for name, digest in proofs.items():
            inputs[str((RESULTS/name).resolve())] = digest
    previous = None
    for level in levels:
        spp = level['spp']
        expected = {f'o.n{spp}.hits'} | {f'o.n{spp}.s{i}.{suffix}' for i in range(4)
            for suffix in ('f64', 'emission.pfm', 'direct.pfm', 'indirect.pfm', 'total.pfm')}
        if set(level['all_payload_sha256']) != expected:
            raise ValueError('missing or unexpected reference payload')
        for name, digest in level['all_payload_sha256'].items():
            path = directory/name
            if sha(path) != digest:
                raise ValueError('reference payload changed: '+name)
            inputs[str(path)] = digest
        meta_path = directory/f'n{spp}.meta.json'
        meta = read(meta_path, inputs)
        imported_original = variant == 'proved-exact-prefix-recovery' and meta['binary_sha256'] == sha(Q.BINARY)
        binary = Q.BINARY if proofs is None or imported_original else ROOT/'build/n010-cpu/n010_incremental_oracle'
        if (meta['binary_sha256'], meta['net_sha256'], meta['scene_sha256'], meta['geometry_sha256']) != (
                sha(binary), sha(Q.NET), sha(scene_path), scene.geometry_sha256()):
            raise ValueError('reference metadata binary/net/physical geometry identity mismatch')
        if meta['spp'] != spp or meta['seeds'] != list(Q.L.N007_SEEDS) or len(meta['runs']) != 4:
            raise ValueError('reference metadata level/replicate mismatch')
        for i, seed in enumerate(Q.L.N007_SEEDS):
            sidecar = Q.L.read_sidecar(directory/f'o.n{spp}.s{i}.f64')
            if (sidecar['spp'], sidecar['seed'], sidecar['width'], sidecar['height']) != (spp, seed, state['width'], state['height']):
                raise ValueError('reference f64 header differs from frozen replicate/state')
            if meta['runs'][i]['seed'] != seed:
                raise ValueError('metadata run seed mismatch')
        if not level['geometry_hash_match']:
            raise ValueError('reference geometry mismatch')
        if proofs is not None and not imported_original:
            if level['metadata_sha256'] != inputs[str(meta_path)] or meta['proof_sha256'] != proofs or meta['computational_variant'] != 'exact-prefix-continuation':
                raise ValueError('incremental metadata/proof identity mismatch')
            expected_interval = [previous['spp'] if previous else 0, spp]
            if meta['sample_interval'] != expected_interval:
                raise ValueError('incremental sample interval differs from exact frozen prefix')
            if meta['all_payload_sha256'] != level['all_payload_sha256']:
                raise ValueError('incremental metadata payload identity mismatch')
            if previous:
                previous_meta = directory/f'n{previous["spp"]}.meta.json'
                if meta['previous_metadata_sha256'] != inputs[str(previous_meta)] or meta['previous_payload_sha256'] != previous['all_payload_sha256']:
                    raise ValueError('incremental prior-prefix chain mismatch')
            elif meta['previous_payload_sha256']:
                raise ValueError('fresh first level unexpectedly restored a prefix')
        manifest_path = directory/f'screen-n{spp}.json'
        read(manifest_path, inputs)
        actual = Q.assess(manifest_path)
        if actual != level['screen']:
            raise ValueError('stored convergence classification differs from unchanged assessor')
        if actual['scene_sha256'] != sha(scene_path) or actual['frame_state_sha256'] != spec['state_sha256']['frame']:
            raise ValueError('convergence manifest physical state mismatch')
        previous = level
    if variant == 'proved-exact-prefix-recovery':
        record = read(directory/'prefix-import.json', inputs)
        if q['prefix_import_sha256'] != sha(directory/'prefix-import.json') or record['proof_sha256'] != proofs:
            raise ValueError('imported prefix provenance changed')
        source = Path(record['source_directory'])
        if sha(source/'qualification.json') != record['source_qualification_sha256']:
            raise ValueError('retained source qualification changed after prefix import')
        for name, digest in record['file_sha256'].items():
            if sha(source/name) != digest or sha(directory/name) != digest:
                raise ValueError('imported prefix no longer matches retained source bytes')
        if len(record['levels']) > len(levels) or record['levels'] != [level['spp'] for level in levels[:len(record['levels'])]]:
            raise ValueError('imported frozen prefix differs from retained level sequence')
    expected_classification = 'STATISTICALLY_ELIGIBLE' if levels[-1]['screen']['status']=='statistical-screen-pass' else 'INELIGIBLE'
    if q['classification'] != expected_classification or any(level['screen']['status']=='statistical-screen-pass' for level in levels[:-1]):
        raise ValueError('qualification classifier or first qualifying stop differs from unchanged screens')
    if require_eligible and (q['classification'] != 'STATISTICALLY_ELIGIBLE' or levels[-1]['screen']['status'] != 'statistical-screen-pass'):
        raise ValueError('reference is not statistically eligible')
    return {'cell':cell, 'transport':f'T_B{vertices}', 'directory':str(directory),
            'computational_variant':variant, 'levels':[level['spp'] for level in levels],
            'qualification_sha256':sha(directory/'qualification.json'), 'pass':True}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--references', type=Path, required=True)
    parser.add_argument('--cells', nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('refuse overwriting an earlier provenance audit')
    inputs = {}
    lock = read(args.lock, inputs)
    if set(lock['cells']) != {f'C{i}' for i in range(1,13)}:
        raise ValueError('complete C1-C12 state lock required')
    selected = args.cells or list(lock['cells'])
    if len(set(selected)) != len(selected) or not set(selected) <= set(lock['cells']):
        raise ValueError('unknown/duplicate selected cell')
    physical_proof(inputs)
    result = {'schema':'n010-reference-provenance/1', 'complete':False, 'all_pass':False,
              'source_commit':subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
              'scope':'FULL_CORPUS' if set(selected)==set(lock['cells']) else 'SUBSET_AUDIT_ONLY',
              'inputs':inputs, 'rows':[]}
    for cell in selected:
        for vertices in (2,8):
            try:
                row = verify_reference(args.references/f'{cell}_T_B{vertices}', cell, vertices, lock['cells'][cell], inputs)
            except (OSError, ValueError, KeyError, AssertionError) as error:
                row = {'cell':cell, 'transport':f'T_B{vertices}', 'pass':False, 'reason':str(error)}
            result['rows'].append(row)
            args.output.write_text(json.dumps(result, indent=2)+'\n')
    result['complete'] = True
    result['all_pass'] = all(row['pass'] for row in result['rows'])
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(result['scope'], 'PASS' if result['all_pass'] else 'FAIL')
    raise SystemExit(0 if result['all_pass'] else 2)

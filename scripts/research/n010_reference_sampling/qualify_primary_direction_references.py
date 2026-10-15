#!/usr/bin/env python3
"""Plan 046: all eight fixed ladders, with explicit own-feasibility imports."""
import ctypes
import json
from pathlib import Path
import shutil
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
import numpy as np
import primary_direction_reference_provenance as P
from generate_rqmc_oracle import once
from reference_provenance import ROOT, RESULTS, sha
from qualify_hybrid_references import check_files


def import_feasibility(directory, q, proofs, inputs, result, spec):
    proof = P.feasibility(inputs)
    if q['cell'] != 'C1' or q['transport'] != 'T_B8' or q['state_sha256'] != proof['state_sha256']:
        raise ValueError('feasibility import canonical state differs')
    if sha(directory/'scene.n008') != proof['scene_sha256']:
        raise ValueError('feasibility import scene differs')
    q['feasibility_import'] = {'result_sha256': sha(RESULTS/P.PROOFS[-1]),
        'directory': str(P.FEASIBILITY_WORK), 'levels': [8192, 16384]}
    previous, manifests = None, []
    result['imported_feasibility_attempts'] = []
    for index, (level, actual) in enumerate(zip(proof['levels'], proof['process_attempts'])):
        spp = level['spp']
        out = directory/f'o.n{spp}'
        for suffix, digest in level['payload_sha256'].items():
            source = P.FEASIBILITY_WORK/(out.name+suffix)
            destination = directory/(out.name+suffix)
            if sha(source) != digest or destination.exists():
                raise ValueError('changed source or existing import destination')
            shutil.copyfile(source, destination)
            if sha(destination) != digest:
                raise ValueError('import payload copy differs')
            inputs[str(destination)] = digest
        for suffix in ('stdout.json', 'stderr.log', 'resource-limits.json'):
            source = P.FEASIBILITY_WORK/f'n{spp}.{suffix}'
            destination = directory/source.name
            shutil.copyfile(source, destination)
            if sha(destination) != sha(source):
                raise ValueError('import execution copy differs')
            inputs[str(destination)] = sha(destination)
        source_meta = P.FEASIBILITY_WORK/f'n{spp}.meta.json'
        native_meta = directory/f'n{spp}.imported-native-meta.json'
        shutil.copyfile(source_meta, native_meta)
        if sha(native_meta) != sha(source_meta):
            raise ValueError('import raw metadata copy differs')
        inputs[str(native_meta)] = sha(native_meta)
        meta = json.loads(native_meta.read_text())
        prior = q['levels'][-1]['all_payload_sha256'] if previous else {}
        payloads = {out.name+s: h for s, h in level['payload_sha256'].items()}
        receipt_sha = sha(directory/f'n{spp}.resource-limits.json')
        meta.update(binary_sha256=sha(P.BINARY), net_sha256=sha(P.Q.NET),
            computational_variant=P.VARIANT, proof_sha256=proofs,
            sample_interval=actual['sample_interval'], previous_payload_sha256=prior,
            all_payload_sha256=payloads, source_commit=proof['source_commit'],
            import_source_commit=result['source_commit'], resource_limits_sha256=receipt_sha,
            wall_seconds_diagnostic=actual['wall_seconds_diagnostic'])
        if previous:
            meta['previous_metadata_sha256'] = sha(directory/f'n{previous["spp"]}.meta.json')
        meta_path = directory/f'n{spp}.meta.json'
        meta_path.write_text(json.dumps(meta, indent=2)+'\n')
        inputs[str(meta_path)] = sha(meta_path)
        manifest_path = directory/f'screen-n{spp}.json'
        shutil.copyfile(P.FEASIBILITY_WORK/manifest_path.name, manifest_path)
        screen = P.Q.assess(manifest_path)
        if screen != level['screen']:
            raise ValueError('imported unchanged screen differs')
        manifests = json.loads(manifest_path.read_text())['levels']
        means = np.stack([P.Q.L.read_sidecar(directory/(out.name+f'.s{i}.f64'))['mean'] for i in range(4)])
        q['levels'].append({'spp': spp, 'screen': screen, 'geometry_hash_match': True,
            'metadata_sha256': sha(meta_path), 'all_payload_sha256': payloads,
            'components_union_positive': {k: int((means[..., j, :].max(-1)>0).any(0).sum())
                for j, k in enumerate(P.Q.L.COMPONENTS)},
            'replicate_means_se_max': float((means.std(0, ddof=1)/2).max())})
        imported_from = {'result_sha256': sha(RESULTS/P.PROOFS[-1]),
                         'attempt_index': index, 'directory': str(P.FEASIBILITY_WORK)}
        attempt = dict(actual)
        attempt.update(input_sha256=dict(inputs), proof_sha256=proofs,
            previous_payload_sha256=prior, resource_limits_sha256=receipt_sha, imported_from=imported_from)
        # Retain the original command verbatim; this is not a new native run.
        (directory/f'n{spp}.attempt.json').write_text(json.dumps(attempt, indent=2)+'\n')
        result['imported_feasibility_attempts'].append(imported_from)
        previous = meta
    q['classification'] = 'STATISTICALLY_ELIGIBLE' if q['levels'][-1]['screen']['status'] == 'statistical-screen-pass' else 'INELIGIBLE'
    (directory/'qualification.json').write_text(json.dumps(q, indent=2, allow_nan=False)+'\n')
    check_files(inputs, {})
    P.verify_reference(directory, 'C1', 8, spec, {}, require_eligible=False)
    return previous, manifests


def program():
    original = SCRIPTS/'qualify_point_guided_references.py'
    digest = 'cb9ce1e58a612cd66e6f2af1492e575b49e8ff3f003b6bef38d6e2112d77cc2e'
    if sha(original) != digest:
        raise ValueError('original fixed-ladder acquisition changed')
    source = original.read_text()
    source = once(source, 'Acquire the fixed nine unfinished slots only after full sampler proof.',
        'Acquire the fixed eight unfinished slots only after complete directional sampler proof.')
    source = once(source, '    a = ap.parse_args()',
        "    a = ap.parse_args()\n"
        "    if a.work.resolve() != P.REFERENCE_WORK:\n"
        "        raise ValueError('acquisition root differs from prospective eight-slot map')")
    for old, new in (
        ('import point_guided_reference_provenance as P', 'import primary_direction_reference_provenance as P'),
        ('n010-point-guided-reference-qualification/1', 'n010-primary-direction-reference-qualification/1'),
        ('preexec_fn=limits', 'preexec_fn=lambda: P.set_limits(prefix, spp, previous)'),
        ('            for spp in Q.LEVELS:\n',
         "            if selected == 'C1_T_B8':\n"
         "                previous, manifests = _import_feasibility(directory, q, proofs, inputs, result, lock['cells'][cell])\n"
         "                save()\n"
         "            for spp in Q.LEVELS:\n"
         "                if q['classification'] == 'STATISTICALLY_ELIGIBLE':\n"
         "                    break\n"
         "                if previous and spp <= previous['spp']:\n"
         "                    continue\n"),
        ('                fresh = json.loads(proc.stdout)',
         "                attempt['resource_limits_sha256'] = sha(directory/f'n{spp}.resource-limits.json')\n"
         "                fresh = json.loads(proc.stdout)\n"
         "                fresh['resource_limits_sha256'] = attempt['resource_limits_sha256']"),
        ('    inputs = {str(Path(__file__).resolve()): sha(Path(__file__)),',
         '    inputs = {'+repr(str(original))+': '+repr(digest)+', str(Path(__file__).resolve()): sha(Path(__file__)),')):
        source = once(source, old, new)
    source = once(source, 'Separate ladders for all nine prospectively selected unfinished slots; no view transition or whole-corpus admission',
        'Separate ladders for all eight prospectively selected unfinished slots; sixteen retained eligible references remain separate; no whole-corpus admission')
    if source.count('172800') != 3:
        raise ValueError('original resource-bound anchors changed')
    source = source.replace('172800', '691200')
    old_plan = '032-point-guided-reference-qualification.md'
    if source.count(old_plan) != 2:
        raise ValueError('original plan-identity anchors changed')
    source = source.replace(old_plan, '046-prospective-directional-corpus-admission.md')
    return original, source


if __name__ == '__main__':
    ctypes.CDLL(None).prctl(15, b'n010_dir_q', 0, 0, 0)
    original, source = program()
    exec(compile(source, str(original)+'#plan046', 'exec'),
         {'__name__': '__main__', '__file__': __file__, '_import_feasibility': import_feasibility})

#!/usr/bin/env python3
"""Recheck retained 113 outputs and replay its unchanged physical/iid analysis."""
import argparse
import json
from pathlib import Path
import subprocess
import textwrap
from types import SimpleNamespace
import numpy as np
import qualify_references as Q
import validate_sampler as V
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files
from generate_rqmc_oracle import once

ORIGINAL_SHA = '50991fb0fc8aef8cc132f20a73667ffc58ba94f752b449bb7b13245beb4d38a0'


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.output.exists():
        raise ValueError('refuse overwriting physical replay')
    inputs = {}
    runner = Path(__file__).with_name('validate_point_guided_oracle.py').resolve()
    if sha(runner) != ORIGINAL_SHA:
        raise ValueError('original 113 runner changed')
    for path in (Path(__file__), runner, Path(V.__file__), Path(V.P.__file__),
                 Path(Q.__file__), Path(Q.L.__file__),
                 RESULTS.parent/'experiments/035-point-guided-physical-analysis-replay.md'):
        inputs[str(path.resolve())] = sha(path)
    failed = read(RESULTS/'113-point-guided-physical-controls.json', inputs)
    if not failed['complete'] or failed['all_pass'] or failed.get('failure') != "'geometry_hash_match'":
        raise ValueError('113 is not the expected retained analysis failure')
    check_files(failed['input_sha256'], inputs)
    names = failed['frozen_scene_names']
    if len(names) != 17 or len(failed['rows']) != 17 or failed['physical_checks'] or failed['iid_crosscheck']:
        raise ValueError('unexpected retained acquisition/analysis coverage')
    controls = ROOT/'out/research/n010-comparison-readiness/sampler-validation-v1/rqmc'
    iid_proof = read(RESULTS/'009-iid-precision-confirmation.json', inputs)
    result = {'schema': 'n010-point-guided-physical-replay/1', 'complete': False,
        'all_pass': False, 'gpu_run': False, 'native_acquisition_run': False,
        'eligible_for_references': False, 'source_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'classification': 'POST_HOC_ANALYSIS_REPLAY_NOT_REFERENCE_ADMISSION',
        'input_sha256': inputs, 'frozen_scene_names': names, 'seeds': list(Q.L.N007_SEEDS),
        'rows': [], 'physical_checks': [], 'iid_crosscheck': [], 'scoring_exclusions': 0,
        'scope': 'All seventeen retained native acquisitions; unchanged eight physical and two iid gates; original 113 remains FAIL'}
    all_data = {}
    def save():
        a.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    try:
        for row in failed['rows']:
            if not row['pass'] or row['returncode']:
                raise ValueError('retained native export failed')
            name = row['name']
            prefix = Path(row['command'][row['command'].index('--out')+1])
            check_files({str(prefix.parent/p): h for p, h in row['payload_sha256'].items()}, inputs)
            meta = read(prefix.with_suffix('.meta.json'), inputs)
            old_meta = read(controls/(name+'.meta.json'), inputs)
            if (meta['seeds'], meta['spp'], meta['geometry_sha256']) != (
                    list(Q.L.N007_SEEDS), old_meta['spp'], old_meta['geometry_sha256']):
                raise ValueError('retained control geometry/seed/count differs')
            runs = [Q.L.read_sidecar(Path(str(prefix)+f'.s{i}.f64')) for i in range(4)]
            old = [Q.L.read_sidecar(controls/f'{name}.s{i}.f64') for i in range(4)]
            checks = {
                'all_finite_nonnegative': all(np.isfinite(d[k]).all() and (d[k] >= 0).all() for d in runs for k in ('mean', 'm2')),
                'direct_emission_exact': all(d[k][..., :2, :].tobytes() == o[k][..., :2, :].tobytes() for d, o in zip(runs, old) for k in ('mean', 'm2')),
                'primary_records_exact': prefix.with_suffix('.hits').read_bytes() == (controls/(name+'.hits')).read_bytes(),
                'headers_match': all(all(d[k] == o[k] for k in ('width', 'height', 'spp', 'seed')) for d, o in zip(runs, old)),
                'null_samples_bounded': all(0 <= r['proposal_null_samples'] <= meta['spp']*runs[i]['width']*runs[i]['height'] for i,r in enumerate(meta['runs']))}
            if any(checks[k] != row[k] for k in checks) or not all(checks.values()):
                raise ValueError('retained export gates differ')
            result['rows'].append({**row, 'acquisition_command_executed_by_replay': False, 'export_gates_replayed': True})
            means = np.stack([d['mean'] for d in runs])
            all_data[name] = {'mean': means.mean(0), 'se': means.std(0, ddof=1)/2,
                              'per_seed': runs, 'meta': meta}
        # Reuse the complete original analysis block, with only the omitted
        # metadata fields derived as in validate_sampler.render.
        source = runner.read_text()
        start = source.index('        def replay_control(')
        end = source.index('        frozen()\n        result[\'all_pass\']', start)
        block = textwrap.dedent(source[start:end])
        block = once(block, "meta = dict(data['meta'])", "meta = dict(data['meta'])\n    meta.update(name=name, geometry_hash_match=meta['geometry_sha256'] == scene.geometry_sha256())")
        replay_args = SimpleNamespace(work=ROOT/'out/research/n010-comparison-readiness/point-guided-physical-analysis-replay-v1')
        namespace = dict(globals(), a=replay_args)
        exec(compile(block, str(runner)+'#retained-analysis', 'exec'), namespace)
        check_files(inputs, {})
        result['inputs_unchanged_after_replay'] = True
        result['all_pass'] = (len(result['rows']) == 17 and len(result['physical_checks']) == 8
            and len(result['iid_crosscheck']) == 2 and all(r['pass'] for key in
                ('rows', 'physical_checks', 'iid_crosscheck') for r in result[key]))
    except (ValueError, OSError, KeyError, AssertionError) as error:
        result['failure'] = str(error)
    result['complete'] = True
    save()
    print(json.dumps({'all_pass': result['all_pass'], 'failure': result.get('failure'),
        'physical': [{'id': r.get('id'), 'pass': r['pass']} for r in result['physical_checks']],
        'iid': result['iid_crosscheck'], 'input_count': len(inputs)}))
    raise SystemExit(0 if result['all_pass'] else 2)

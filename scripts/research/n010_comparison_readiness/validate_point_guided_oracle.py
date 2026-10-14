#!/usr/bin/env python3
"""Independent physical controls for the separate point-guided CPU sampler."""
import argparse
import ctypes
import json
from pathlib import Path
import resource
import subprocess
import numpy as np
import qualify_references as Q
import validate_sampler as V
from reference_provenance import ROOT, RESULTS, read, sha


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (21600, 21600))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing guided physical acquisition')
    ctypes.CDLL(None).prctl(15, b'n010_guide_phys', 0, 0, 0)
    inputs = {}
    build_path = RESULTS/'112-point-guided-oracle-build.json'
    build = read(build_path, inputs)
    work = ROOT/'out/research/n010-comparison-readiness/point-guided-oracle-build-v1'
    binary = work/'n010_point_guided_oracle'
    if not build['complete'] or not build['all_pass']:
        raise ValueError('guided build incomplete/failed')
    for name, digest in build['generated_sha256'].items():
        if sha(work/name) != digest:
            raise ValueError('guided build artifact changed')
        inputs[str(work/name)] = digest
    from qualify_hybrid_references import check_files
    check_files(build['input_sha256'], inputs)
    controls = ROOT/'out/research/n010-comparison-readiness/sampler-validation-v1/rqmc'
    cached = read(RESULTS/'022-cached-oracle-equivalence.json', inputs)
    iid_proof = read(RESULTS/'009-iid-precision-confirmation.json', inputs)
    if not cached['complete'] or not cached['all_pass'] or not iid_proof['complete'] or not iid_proof['all_pass']:
        raise ValueError('original physical/iid control provenance incomplete')
    for path in (Path(__file__), Path(V.__file__), Path(V.P.__file__), Path(Q.L.__file__), Q.NET):
        inputs[str(path.resolve())] = sha(path)
    source_rows = {r['name']: r for r in cached['rows']}
    names = sorted(p.stem.replace('.meta', '') for p in controls.glob('*.meta.json'))
    if len(names) != 17:
        raise ValueError('all seventeen applicable original control scenes required')
    for name in names:
        row = source_rows[name]
        for path, digest in ((controls/(name+'.meta.json'), row['original_metadata_sha256']),
                             (controls/(name+'.n008'), row['scene_sha256'])):
            if sha(path) != digest:
                raise ValueError('original control metadata/scene changed')
            inputs[str(path)] = digest
        check_files({str(controls/name)+p['payload']: p['old_sha256'] for p in row['payloads']}, inputs)
    a.work.mkdir(parents=True)
    result = {'schema': 'n010-point-guided-physical-controls/1', 'complete': False, 'all_pass': False,
        'gpu_run': False, 'eligible_for_references': False, 'input_sha256': inputs,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'frozen_scene_names': names, 'seeds': list(Q.L.N007_SEEDS), 'rows': [],
        'physical_checks': [], 'iid_crosscheck': [], 'threads': 4, 'scoring_exclusions': 0,
        'scope': 'All original applicable physical controls and retained independent 16384-spp iid controls; no locked-corpus reference admission',
        'limits': {'address_space_bytes': 4*1024**3, 'cpu_seconds': 21600, 'elapsed_seconds_per_scene': 3600}}
    def save():
        a.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    def frozen():
        check_files(dict(inputs), {})
    all_data = {}
    save()
    try:
        for name in names:
            frozen()
            meta = json.loads((controls/(name+'.meta.json')).read_text())
            if meta['seeds'] != list(Q.L.N007_SEEDS):
                raise ValueError('original seed schedule changed')
            command = [str(binary), '--net', str(Q.NET), '--scene', str(controls/(name+'.n008')),
                '--out', str((a.work/name).resolve()), '--seeds', ','.join(map(str, Q.L.N007_SEEDS)),
                '--spp', str(meta['spp']), '--threads', '4']
            row = {'name': name, 'command': command, 'spp': meta['spp'], 'pass': False}
            result['rows'].append(row)
            save()
            try:
                proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                      timeout=3600, preexec_fn=limits)
            except subprocess.TimeoutExpired:
                raise ValueError('guided control elapsed guard; partial output retained')
            (a.work/(name+'.stdout')).write_text(proc.stdout)
            (a.work/(name+'.stderr')).write_text(proc.stderr)
            row['returncode'] = proc.returncode
            if proc.returncode:
                raise ValueError('guided control execution failed')
            fresh = json.loads(proc.stdout)
            (a.work/(name+'.meta.json')).write_text(json.dumps(fresh, indent=2)+'\n')
            if fresh['seeds'] != meta['seeds'] or fresh['spp'] != meta['spp'] or fresh['geometry_sha256'] != meta['geometry_sha256']:
                raise ValueError('guided control scene/seed/level differs')
            runs = [Q.L.read_sidecar(a.work/f'{name}.s{i}.f64') for i in range(4)]
            original = [Q.L.read_sidecar(controls/f'{name}.s{i}.f64') for i in range(4)]
            row['all_finite_nonnegative'] = all(np.isfinite(v).all() and (v >= 0).all()
                for data in runs for v in (data['mean'], data['m2']))
            row['direct_emission_exact'] = all(new[key][..., :2, :].tobytes() == old[key][..., :2, :].tobytes()
                for new, old in zip(runs, original) for key in ('mean', 'm2'))
            row['primary_records_exact'] = (a.work/(name+'.hits')).read_bytes() == (controls/(name+'.hits')).read_bytes()
            row['headers_match'] = all(all(new[k] == old[k] for k in ('width', 'height', 'spp', 'seed'))
                                      for new, old in zip(runs, original))
            row['null_samples_bounded'] = all(0 <= r['proposal_null_samples'] <= meta['spp']*runs[i]['width']*runs[i]['height']
                                             for i, r in enumerate(fresh['runs']))
            row['payload_sha256'] = {p.name: sha(p) for p in a.work.glob(name+'.*') if p.is_file()}
            row['pass'] = all(row[k] for k in ('all_finite_nonnegative', 'direct_emission_exact',
                                             'primary_records_exact', 'headers_match', 'null_samples_bounded'))
            means = np.stack([data['mean'] for data in runs])
            all_data[name] = {'mean': means.mean(0), 'se': means.std(0, ddof=1)/2, 'per_seed': runs, 'meta': fresh}
            save()
            print(name, 'PASS' if row['pass'] else 'FAIL', flush=True)
            if not row['pass']:
                raise ValueError('guided physical export/direct gate failed')
        def replay_control(res, scene, out, name, spp):
            if (controls/(name+'.n008')).read_text() != scene.text() or all_data[name]['meta']['spp'] != spp:
                raise ValueError('analytic control scene/count differs from original')
            data = all_data[name]
            meta = dict(data['meta'])
            meta['run_counters'] = [{k: run[k] for k in ('seed', 'primary_hits', 'shadow_tests', 'shadow_blocked', 'backface_absorbed')}
                                    for run in meta['runs']]
            res.runs.append(meta)
            return data
        V.render = replay_control
        V.P.render = replay_control
        V.P.check_stat = V.analytic_gate
        V.P.STAT_SPP = 8192
        for fn in (lambda: V.P.control_a2(a.work/'analytic'), lambda: V.P.control_a2(a.work/'analytic','A2b','n001_soft',1),
                   lambda: V.P.control_a4(a.work/'analytic'), lambda: V.P.control_a8(a.work/'analytic'),
                   lambda: V.no_leak(a.work/'analytic'), lambda: V.P.control_a6(a.work/'analytic'),
                   lambda: V.P.control_a6(a.work/'analytic','A10',1.6), lambda: V.P.control_a7(a.work/'analytic')):
            result['physical_checks'].append(fn().to_json())
            save()
        for name in ('A7', 'A6b'):
            reference = next(row for row in iid_proof['iid_crosscheck'] if row['name'] == name)
            prefix = Path(reference['command'][reference['command'].index('--out')+1])
            check_files({str(prefix.parent/p): h for p, h in reference['payload_sha256'].items()}, inputs)
            if sha(controls/(name+'.n008')) != reference['scene_sha256'] or reference['iid_spp'] != 16384:
                raise ValueError('iid physical scene/count mismatch')
            iid = [Q.L.read_sidecar(Path(str(prefix)+f'.s{i}.f64')) for i in range(4)]
            if any(d['seed'] != seed or d['spp'] != 16384 for d, seed in zip(iid, Q.L.N007_SEEDS)):
                raise ValueError('iid replicate identity mismatch')
            g = all_data[name]['mean'][..., 2, :]
            r = np.stack([d['mean'] for d in iid]).mean(0)[..., 2, :]
            relative = np.abs(g.mean((0,1))-r.mean((0,1)))/np.abs(r.mean((0,1)))
            nrmse = float(np.sqrt(np.mean((g-r)**2)/np.mean(r**2)))
            result['iid_crosscheck'].append({'name': name, 'per_channel_mean_relative_difference': relative.tolist(),
                'nrmse': nrmse, 'pass': bool((relative <= 0.002).all() and nrmse <= 0.01)})
            save()
        frozen()
        result['all_pass'] = (len(result['rows']) == 17 and all(r['pass'] for r in result['rows'])
            and len(result['physical_checks']) == 8 and all(r['pass'] for r in result['physical_checks'])
            and len(result['iid_crosscheck']) == 2 and all(r['pass'] for r in result['iid_crosscheck']))
    except (ValueError, OSError, KeyError, AssertionError) as error:
        result['failure'] = str(error)
    result['complete'] = True
    save()
    print('GUIDED PHYSICAL', 'PASS' if result['all_pass'] else 'FAIL', flush=True)
    raise SystemExit(0 if result['all_pass'] else 2)

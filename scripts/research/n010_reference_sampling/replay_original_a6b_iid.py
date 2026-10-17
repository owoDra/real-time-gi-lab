#!/usr/bin/env python3
"""Plan107: new fixed A6b comparison, retained original independent IID data."""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys

import numpy as np
import acquire_original_sphere_seed_wide8 as G
import cover_wide8_original_controls as C
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

OUTPUT = D.RESULTS / '271-whole-path-a6b-independent-iid-replay.json'
PLAN = D.RESULTS.parent / 'experiments/107-retained-a6b-independent-iid-replay.md'


def main():
    if OUTPUT.exists():
        raise ValueError('refuse existing independent replay; no retry')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (120,) * 2)
    for path in (Path(__file__).resolve(), PLAN, Path(G.__file__), Path(C.__file__),
                 Path(D.__file__), D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(path)
    parts = [G.retained_part('A6b', i) for i in range(4)]
    if not parts[-1]['full_four_seed_physical_pass']:
        raise ValueError('terminal full A6b physical PASS required; no waiting queue')
    for part in parts:
        for path, digest in part['input_sha256'].items():
            D.checked(Path(path), digest)
    proof = json.loads(D.checked(D.RESULTS / '009-iid-precision-confirmation.json'))
    if not proof['complete'] or not proof['all_pass']:
        raise ValueError('complete original independent dataset required')
    old = next(r for r in proof['iid_crosscheck'] if r['name'] == 'A6b')
    command = old['command']
    binary = D.ROOT / Path(command[0])
    D.checked(binary, proof['iid_binary_sha256'])
    iid_prefix = D.ROOT / Path(command[command.index('--out') + 1])
    scene = Path(command[command.index('--scene') + 1])
    D.checked(scene, old['scene_sha256'])
    for name, digest in old['payload_sha256'].items():
        D.checked(iid_prefix.parent / name, digest)
    iid_meta = json.loads(D.checked(iid_prefix.with_suffix('.meta.json')))
    if (old['iid_spp'] != 16384 or iid_meta['spp'] != 16384
            or iid_meta['seeds'] != list(D.SEEDS)
            or (iid_meta['width'], iid_meta['height']) != (128, 96)
            or len(iid_meta['runs']) != 4
            or iid_meta['scene_sha256'] != old['scene_sha256']):
        raise ValueError('retained independent full dataset identity differs')
    for part in parts:
        fresh = part['native_metadata']
        if (fresh['scene_sha256'] != old['scene_sha256']
                or fresh['geometry_sha256'] != iid_meta['geometry_sha256']
                or fresh['spp'] != 8192 or (fresh['width'], fresh['height']) != (128, 96)):
            raise ValueError('new full A6b physical target differs')
        prefix = Path(fresh['runs'][0]['prefix'])
        hits = prefix.parent / 'A6b.hits'
        if hits.read_bytes() != iid_prefix.with_suffix('.hits').read_bytes():
            raise ValueError('independent/new primary hit records differ')
    sys.path.insert(0, str(D.HERE.parent / 'n008_hdr_oracle'))
    import n008lib as L
    D.checked(Path(L.__file__))
    result = dict(schema='n010-whole-path-a6b-independent-iid-replay/1', complete=False,
                  all_pass=False, gpu_run=False, native_reexecuted=False, reference_admission=False,
                  classification='FIXED_RETAINED_INDEPENDENT_COMPARISON_ACQUIRING',
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  input_sha256=D.INPUTS,
                  candidate_parts=[str(G.paths('A6b', i)[0]) for i in range(4)],
                  independent_dataset='009-iid-precision-confirmation.json',
                  counts=dict(candidate_per_seed=8192, independent_per_seed=16384,
                              seeds=list(D.SEEDS), resolution=[128, 96]),
                  analysis_receipt=dict(pid=os.getpid(),
                      start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
                      affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                      cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
                      address_space=list(resource.getrlimit(resource.RLIMIT_AS))),
                  tests='NOT_RUN; scientific independent comparison replay, no new native')
    try:
        new_rows = [L.read_sidecar(Path(p['native_metadata']['runs'][0]['prefix'] + '.f64')) for p in parts]
        iid_rows = [L.read_sidecar(Path(str(iid_prefix) + f'.s{i}.f64')) for i in range(4)]
        for rows, spp in ((new_rows, 8192), (iid_rows, 16384)):
            for i, row in enumerate(rows):
                if (row['seed'] != D.SEEDS[i] or row['spp'] != spp
                        or (row['width'], row['height']) != (128, 96)
                        or not all(np.isfinite(row[k]).all() and (row[k] >= 0).all()
                                   for k in ('mean', 'm2'))):
                    raise ValueError('actual sidecar count/seed/shape/finite identity differs')
        got = np.stack([r['mean'] for r in new_rows]).mean(0)[..., 2, :]
        ref = np.stack([r['mean'] for r in iid_rows]).mean(0)[..., 2, :]
        got_mean, ref_mean = got.mean((0, 1)), ref.mean((0, 1))
        if not (ref_mean > 0).all() or not np.mean(ref**2) > 0:
            raise ValueError('independent control signal invalid')
        relative = np.abs(got_mean - ref_mean) / ref_mean
        nrmse = float(np.sqrt(np.mean((got-ref)**2) / np.mean(ref**2)))
        passed = bool((relative <= .002).all() and nrmse <= .01)
        for path, digest in list(D.INPUTS.items()):
            D.checked(Path(path), digest)
        result.update(complete=True, all_pass=passed,
                      classification='COMPLETE_INDEPENDENT_COMPARISON_PASS_NO_ADMISSION' if passed
                      else 'COMPLETE_INDEPENDENT_COMPARISON_FAIL_STOP',
                      independent_iid=dict(candidate_channel_means=got_mean.tolist(),
                          independent_channel_means=ref_mean.tolist(),
                          signed_channel_ratio_minus_one=(got_mean/ref_mean-1).tolist(),
                          per_channel_mean_relative_difference=relative.tolist(), nrmse=nrmse,
                          pass_=passed),
                      no_pixel_or_seed_exclusion=True,
                      scope='Original A6b independent-comparator check only; no zero-bias/state/prefix/reference admission')
    except (ValueError, OSError, KeyError, AssertionError) as error:
        result.update(classification='INDEPENDENT_COMPARISON_OPERATIONAL_FAILURE_RETAINED', failure=str(error))
    OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result.get(k) for k in ('complete', 'all_pass', 'classification',
                                               'failure', 'independent_iid')}, indent=2))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__ == '__main__':
    main()

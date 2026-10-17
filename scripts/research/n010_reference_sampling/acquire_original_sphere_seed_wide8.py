#!/usr/bin/env python3
"""Plan106: one explicit full-count seed, four-seed physical gate at last part."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np
import cover_wide8_original_controls as C
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

NAMES = ('A6a', 'A6b', 'A10')
PLAN = D.RESULTS.parent / 'experiments/106-original-sphere-seed-checkpoints.md'


def paths(name, index):
    number = 259 + NAMES.index(name) * 4 + index
    output = D.RESULTS / f'{number:03d}-wide8-original-{name.lower()}-seed{index}.json'
    work = D.OUT / 'wide8-original-sphere-seed-v1' / f'{name}-seed{index}'
    return output, work


def retained_part(name, index):
    output, _ = paths(name, index)
    data = json.loads(D.checked(output))
    if not (data['complete'] and data['all_pass'] and data['seed_integrity_pass']
            and data['name'] == name and data['seed_index'] == index):
        raise ValueError('complete prior seed integrity required')
    for p, digest in data['payload_sha256'].items():
        D.checked(Path(p), digest)
    receipt = json.loads(D.checked(Path(data['resource_receipt'])))
    stat = Path('/proc') / str(receipt['pid']) / 'stat'
    if stat.exists():
        fields = stat.read_text().rsplit(')', 1)[1].split()
        if int(fields[19]) == receipt['start_ticks'] and fields[0] != 'Z':
            raise ValueError('same prior native remains live')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', choices=NAMES, required=True)
    parser.add_argument('--seed-index', type=int, choices=range(4), required=True)
    args = parser.parse_args()
    name, index = args.name, args.seed_index
    output, work = paths(name, index)
    if output.exists() or work.exists():
        raise ValueError('refuse existing sphere seed part; no retry')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    for p in (Path(__file__).resolve(), PLAN, Path(C.__file__), Path(D.__file__),
              D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(p)
    original_level5 = C.pinned_result('258')
    prototype, coverage = C.pinned_result('254'), C.pinned_result('257')
    if not (original_level5['all_pass'] and prototype['all_pass'] and coverage['all_pass']):
        raise ValueError('terminal successful258/254/257 required; no waiting queue')
    previous_parts = [retained_part(name, i) for i in range(index)]
    for part in previous_parts:
        for p, digest in part['input_sha256'].items():
            D.checked(Path(p), digest)
    if NAMES.index(name) > 0:
        prior = retained_part(NAMES[NAMES.index(name) - 1], 3)
        if not prior['full_four_seed_physical_pass']:
            raise ValueError('previous artifact full physical gate required')
    if name == 'A6a':
        low_cpu = prototype['optimized_a6a_cpu_seconds']
        low_elapsed = prototype['attempts'][-1]['elapsed']
    else:
        pilot = next(r for r in coverage['rows'] if r['name'] == name)
        low_cpu, low_elapsed = pilot['child_cpu_seconds'], pilot['elapsed_seconds']
    projected_cpu, projected_elapsed = low_cpu * 256, low_elapsed * 256
    if projected_cpu > 6000 or projected_elapsed > 9000:
        raise ValueError('fixed full-seed operational resource margin absent')
    binary = D.OUT / 'wide8-cpu-bvh-v1/n010_wide8_exporter'
    D.checked(binary, prototype['payload_sha256'][str(binary)])
    proof = json.loads(D.checked(D.RESULTS / '022-cached-oracle-equivalence.json'))
    original = D.OUT / 'sampler-validation-v1/rqmc'
    old = next(r for r in proof['rows'] if r['name'] == name)
    meta = json.loads(D.checked(original / (name + '.meta.json'), old['original_metadata_sha256']))
    scene = original / (name + '.n008')
    D.checked(scene, old['scene_sha256'])
    for payload in old['payloads']:
        D.checked(original / (name + payload['payload']), payload['old_sha256'])
    if (meta['spp'] != 8192 or meta['seeds'] != list(D.SEEDS)
            or (meta['width'], meta['height']) != (128, 96)):
        raise ValueError('original full sphere scene/count/seed identity differs')
    net = D.OUT / 'sobol16x262144.bin'
    D.checked(net)
    sys.path.insert(0, str(D.HERE.parent / 'n010_comparison_readiness'))
    import validate_sampler as V
    for p in (Path(V.__file__), Path(V.P.__file__), Path(V.L.__file__)):
        D.checked(p)
    rho = (.5, .5, .5) if name == 'A6a' else (.9, .6, .3)
    light = (0, 0, 0) if name == 'A6a' else (.3, .2, -.1)
    intensity = (1, 1, 1) if name == 'A6a' else (2, 2, 2)
    authored, vertices, faces = V.P.sphere_scene(rho, light, intensity, 8,
                                               far=1.6 if name == 'A10' else float('inf'))
    if authored.text() != scene.read_text() or authored.geometry_sha256() != meta['geometry_sha256']:
        raise ValueError('independently authored original sphere/range differs')
    direct, allowance, indirect, bounds = V.P.sphere_expected(authored, rho, light, intensity,
                                                           8, (vertices, faces))
    work.mkdir(parents=True)
    prefix, receipt = work / name, work / 'native.resources.json'
    command = [str(binary), '--net', str(net), '--scene', str(scene), '--out', str(prefix),
               '--seeds', str(D.SEEDS[index]), '--spp', '8192', '--threads', '1']
    result = dict(schema='n010-wide8-original-sphere-seed/1', complete=False, all_pass=False,
                  seed_integrity_pass=False, name=name, seed_index=index, seed=D.SEEDS[index],
                  gpu_run=False, reference_admission=False,
                  classification='ORIGINAL_FULL_SPHERE_SEED_NATIVE_ACQUIRING',
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  input_sha256=D.INPUTS, command=command, resource_receipt=str(receipt),
                  prior_part_results=[str(paths(name, i)[0]) for i in range(index)],
                  operational_projection=dict(cpu_seconds=projected_cpu, elapsed_seconds=projected_elapsed,
                                              scope='Retained low-count linear cost planning, not ETA'),
                  native_limits=dict(cpu_seconds=7200, elapsed_seconds=10800,
                                     address_space_bytes=4 * 1024**3,
                                     affinity=sorted(os.sched_getaffinity(0)), nice=15),
                  full_four_seed_physical_pass=False,
                  scheduling='One explicit original full seed only; no next-seed/artifact queue',
                  tests='NOT_RUN; original full scientific physical-control seed acquisition')

    def hashes():
        return {str(p): C.sha(p) for p in sorted(work.iterdir()) if p.is_file()}

    def save():
        output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (7200,) * 2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(),
            start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
            address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
            command=command)) + '\n')

    save()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    try:
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=10800, preexec_fn=limits)
        except subprocess.TimeoutExpired as error:
            (work / 'native.stdout').write_bytes(error.stdout or b'')
            (work / 'native.stderr').write_bytes(error.stderr or b'')
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            result.update(returncode='NOT_EXPOSED_BY_TIMEOUTEXPIRED', elapsed_seconds=time.monotonic()-started,
                          child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                          payload_sha256=hashes())
            save()
            raise ValueError('full seed elapsed guard; no retry') from error
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        (work / 'native.stdout').write_text(proc.stdout)
        (work / 'native.stderr').write_text(proc.stderr)
        result.update(returncode=proc.returncode, elapsed_seconds=time.monotonic()-started,
                      child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                      classification='ORIGINAL_FULL_SPHERE_SEED_NATIVE_TERMINAL_ANALYSIS_PENDING',
                      payload_sha256=hashes())
        save()
        actual = json.loads(D.checked(receipt))
        if (actual['cpu'] != [7200] * 2 or actual['address_space'] != [4 * 1024**3] * 2
                or len(actual['affinity']) != 1 or actual['nice'] != 15):
            raise ValueError('actual full seed resource scope differs')
        if proc.returncode:
            raise ValueError('full seed native failure; no retry')
        resource.setrlimit(resource.RLIMIT_CPU, (220,) * 2)
        fresh = json.loads(proc.stdout)
        (work / (name + '.meta.json')).write_text(json.dumps(fresh, indent=2) + '\n')
        for key in ('scene_sha256', 'geometry_sha256', 'width', 'height', 'spp',
                    'triangles', 'point_lights', 'ray_offset'):
            if fresh[key] != meta[key]:
                raise ValueError('full seed metadata identity differs ' + key)
        if fresh['seeds'] != [D.SEEDS[index]] or len(fresh['runs']) != 1:
            raise ValueError('one original seed required')
        row = V.L.read_sidecar(Path(str(prefix) + '.s0.f64'))
        prior = V.L.read_sidecar(original / f'{name}.s{index}.f64')
        if (row['seed'] != D.SEEDS[index] or row['spp'] != 8192
                or (row['width'], row['height']) != (128, 96)):
            raise ValueError('full seed sidecar identity differs')
        for field in ('mean', 'm2'):
            if not (np.isfinite(row[field]).all() and (row[field] >= 0).all()):
                raise ValueError('full seed sidecar nonfinite/negative')
            if row[field][..., :2, :].tobytes() != prior[field][..., :2, :].tobytes():
                raise ValueError('original deterministic full seed bits differ')
        for component in ('emission', 'direct', 'indirect', 'total'):
            image = V.L.read_pfm(Path(str(prefix) + f'.s0.{component}.pfm'))
            if not (np.isfinite(image).all() and (image >= 0).all()):
                raise ValueError('full seed PFM nonfinite/negative')
        if prefix.with_suffix('.hits').read_bytes() != (original / (name + '.hits')).read_bytes():
            raise ValueError('original full seed hit bytes differ')
        run, old_run = fresh['runs'][0], meta['runs'][index]
        audit = run['all_split']
        if (run['seed'] != old_run['seed'] or run['primary_hits'] != old_run['primary_hits']
                or audit['own_checks'] != audit['component_attempts'] - audit['component_nulls']
                or not np.isfinite([audit['max_own_log_error'], audit['max_conditioned_error_fraction'],
                                   audit['max_unconditioned_error_fraction']]).all()
                or audit['max_own_log_error'] > 1e-6 or audit['max_conditioned_error_fraction'] > 1):
            raise ValueError('full seed original primary/proposal audit differs')
        result.update(seed_integrity_pass=True, native_metadata=fresh, complete=True,
                      all_pass=True, original_deterministic_primary_bits_exact=True,
                      classification='ORIGINAL_FULL_SPHERE_SEED_INTEGRITY_COMPLETE_NO_ADMISSION',
                      scope='One original8192 seed only; no full physical artifact until all four seeds pass')
        if index == 3:
            all_rows = [V.L.read_sidecar(Path(p['native_metadata']['runs'][0]['prefix'] + '.f64'))
                        for p in previous_parts] + [row]
            runs = [p['native_metadata']['runs'][0] for p in previous_parts] + [run]
            aggregate = dict(fresh, seeds=list(D.SEEDS), runs=runs, name=name, geometry_hash_match=True,
                             run_counters=[{k: r[k] for k in ('seed', 'primary_hits', 'shadow_tests',
                                                             'shadow_blocked', 'backface_absorbed')} for r in runs])
            means = np.stack([r['mean'] for r in all_rows])
            data = dict(mean=means.mean(0), se=means.std(0, ddof=1)/2,
                        per_seed=all_rows, meta=aggregate)
            control = V.P.Result(name, 'Original full sphere/range control; four explicit seed checkpoints')
            control.runs.append(aggregate)
            control.notes[name + '_mesh'] = bounds
            control.notes[name + '_expected_indirect'] = indirect
            mask = np.ones(direct.shape[:2], bool)
            V.analytic_gate(control, name, data, 'direct', direct, mask, tau=0, allowance=allowance)
            V.analytic_gate(control, name, data, 'indirect', indirect, mask, tau=.002)
            if name == 'A10':
                control.check('A10:all_primary_hits_within_far',
                              sum(r['primary_hits'] for r in runs) == 4 * 8192 * 128 * 96)
            physical = control.to_json()
            result.update(all_pass=bool(physical['pass']), full_four_seed_physical_pass=bool(physical['pass']),
                          physical_checks=physical, aggregate_metadata_derived_from_four_native_receipts=True,
                          original_full_artifacts_retained_if_pass=15 + NAMES.index(name),
                          classification='ORIGINAL_FULL_SPHERE_FOUR_SEED_PHYSICAL_COMPLETE_NO_ADMISSION',
                          scope='One original full four-seed8192 artifact; IID/bias/state/prefix/reference gates remain')
        for p, digest in list(D.INPUTS.items()):
            D.checked(Path(p), digest)
    except (ValueError, OSError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        result.update(complete=False, all_pass=False,
                      classification='ORIGINAL_FULL_SPHERE_SEED_FAILURE_PARTIALS_RETAINED', failure=str(error))
    result['payload_sha256'] = hashes()
    save()
    print(json.dumps({k: result.get(k) for k in ('name', 'seed_index', 'complete', 'all_pass',
        'seed_integrity_pass', 'full_four_seed_physical_pass', 'classification', 'failure',
        'elapsed_seconds', 'child_cpu_seconds')}, indent=2))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__ == '__main__':
    main()

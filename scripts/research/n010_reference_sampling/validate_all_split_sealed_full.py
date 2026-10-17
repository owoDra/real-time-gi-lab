#!/usr/bin/env python3
"""Plan101: one original full sealed-room physical artifact, never a queue."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

PLAN = D.RESULTS.parent / 'experiments/101-original-sealed-room-full-controls.md'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', choices=('sealed-dark', 'sealed-lit'), required=True)
    name = parser.parse_args().name
    stem = '252' if name == 'sealed-dark' else '253'
    work = D.OUT / ('all-split-original-' + name + '-full-v1')
    output = D.RESULTS / (stem + '-all-split-original-' + name + '-full-control.json')
    if work.exists() or output.exists():
        raise ValueError('refuse existing original full sealed-room acquisition')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    for p in (Path(__file__).resolve(), PLAN, Path(D.__file__), D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(p)
    if name == 'sealed-lit':
        dark = json.loads(D.checked(D.RESULTS / '252-all-split-original-sealed-dark-full-control.json'))
        if not dark['complete'] or not dark['all_pass'] or dark['name'] != 'sealed-dark':
            raise ValueError('successful terminal original full dark control required before lit')
        for p, h in dark['payload_sha256'].items():
            D.checked(Path(p), h)
    build = json.loads(D.checked(D.RESULTS / '224-all-split-exporter-build.json'))
    cost = json.loads(D.checked(D.RESULTS / '236-all-split-remaining-controls-cpu-cost.json'))
    proof = json.loads(D.checked(D.RESULTS / '022-cached-oracle-equivalence.json'))
    if not (build['complete'] and build['all_pass'] and cost['complete'] and proof['complete'] and proof['all_pass']):
        raise ValueError('complete unchanged build, cost and original-control evidence required')
    pilot = next(r for r in cost['rows'] if r['name'] == name)
    if not pilot['pass_cost_integrity'] or pilot['original_spp'] != 1024:
        raise ValueError('unchanged same-scene original-count cost inventory required')
    for p, h in build['payload_sha256'].items():
        D.checked(Path(p), h)
    binary = D.OUT / 'all-split-exporter-v1/n010_all_split_oracle'
    D.checked(binary)
    old = next(r for r in proof['rows'] if r['name'] == name)
    original = D.OUT / 'sampler-validation-v1/rqmc'
    meta = json.loads(D.checked(original / (name + '.meta.json'), old['original_metadata_sha256']))
    scene = original / (name + '.n008')
    D.checked(scene, old['scene_sha256'])
    for p in old['payloads']:
        D.checked(original / (name + p['payload']), p['old_sha256'])
    if (meta['spp'] != 1024 or meta['seeds'] != list(D.SEEDS) or
            (meta['width'], meta['height']) != (128, 96)):
        raise ValueError('original full scene/count/seed/shape differs')
    net = D.OUT / 'sobol16x262144.bin'
    D.checked(net)
    sys.path.insert(0, str(D.HERE.parent / 'n010_comparison_readiness'))
    import validate_sampler as V
    for p in (Path(V.__file__), Path(V.P.__file__), Path(V.L.__file__)):
        D.checked(p)
    origin, target = ((1.5, 1.2, 1.5), (0, 1, -1)) if name == 'sealed-dark' else ((-1.8, 1.2, 1.8), (-0.5, 1, -1))
    authored = V.L.Scene(V.L.Camera(origin, target), max_bounces=8)
    authored.material('wall', V.P.GRAY)
    for q in V.P.room_quads(True).values():
        authored.quad('wall', *q)
    authored.point((-1, 1.5, 0.3), (10, 10, 10))
    if authored.text() != scene.read_text() or authored.geometry_sha256() != meta['geometry_sha256']:
        raise ValueError('independent unchanged original authored sealed room differs')
    work.mkdir()
    prefix, receipt = work / name, work / 'native.resources.json'
    command = [str(binary), '--net', str(net), '--scene', str(scene), '--out', str(prefix),
               '--seeds', ','.join(map(str, D.SEEDS)), '--spp', '1024', '--threads', '1']
    result = dict(schema='n010-all-split-original-sealed-full-control/1', name=name,
                  complete=False, all_pass=False, gpu_run=False, reference_admission=False,
                  classification='ORIGINAL_FULL_SEALED_NATIVE_ACQUIRING', input_sha256=D.INPUTS,
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  command=command, native_limits=dict(cpu_seconds=1200, elapsed_seconds=1800,
                  address_space_bytes=4 * 1024**3, affinity=sorted(os.sched_getaffinity(0)), nice=15),
                  scheduling='One named native only; no automatic subsequent-control queue',
                  tests='NOT_RUN; unchanged original full scientific physical control')

    def save():
        output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')

    def hashes():
        return {str(p): D.sha(p) for p in sorted(work.iterdir()) if p.is_file()}

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (1200,) * 2)
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
            proc = subprocess.run(command, capture_output=True, text=True, timeout=1800, preexec_fn=limits)
        except subprocess.TimeoutExpired as e:
            (work / 'native.stdout').write_bytes(e.stdout or b'')
            (work / 'native.stderr').write_bytes(e.stderr or b'')
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            result.update(returncode='TIMEOUT_REAPED_BY_SUBPROCESS_RUN', elapsed_seconds=time.monotonic()-started,
                          child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                          classification='ORIGINAL_FULL_SEALED_NATIVE_TIMEOUT', payload_sha256=hashes())
            save()
            raise ValueError('full native elapsed guard; partials retained, no retry') from e
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        (work / 'native.stdout').write_text(proc.stdout)
        (work / 'native.stderr').write_text(proc.stderr)
        result.update(returncode=proc.returncode, elapsed_seconds=time.monotonic()-started,
                      child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                      classification='ORIGINAL_FULL_SEALED_NATIVE_TERMINAL_ANALYSIS_PENDING', payload_sha256=hashes())
        save()  # Native terminal evidence survives every subsequent analysis error.
        actual = json.loads(D.checked(receipt))
        if (actual['cpu'] != [1200] * 2 or actual['address_space'] != [4 * 1024**3] * 2 or
                len(actual['affinity']) != 1 or actual['nice'] != 15):
            raise ValueError('actual resource limits differ')
        if proc.returncode:
            raise ValueError('full native failure; no retry')
        resource.setrlimit(resource.RLIMIT_CPU, (220,) * 2)
        fresh = json.loads(proc.stdout)
        (work / (name + '.meta.json')).write_text(json.dumps(fresh, indent=2) + '\n')
        if any(fresh[k] != meta[k] for k in ('scene_sha256', 'geometry_sha256', 'width', 'height', 'spp', 'seeds')):
            raise ValueError('actual original scene/count/seed differs')
        rows = [V.L.read_sidecar(Path(str(prefix) + f'.s{i}.f64')) for i in range(4)]
        old_rows = [V.L.read_sidecar(original / f'{name}.s{i}.f64') for i in range(4)]
        if any(r['seed'] != s or r['spp'] != 1024 or (r['width'], r['height']) != (128, 96)
               or not all(np.isfinite(r[k]).all() and (r[k] >= 0).all() for k in ('mean', 'm2'))
               for r, s in zip(rows, D.SEEDS)):
            raise ValueError('full sidecar shape/seed/count/finite guard')
        if any(a[k][..., :2, :].tobytes() != b[k][..., :2, :].tobytes()
               for a, b in zip(rows, old_rows) for k in ('mean', 'm2')):
            raise ValueError('original deterministic mean/second bits differ')
        if prefix.with_suffix('.hits').read_bytes() != (original / (name + '.hits')).read_bytes():
            raise ValueError('original primary-hit bytes differ')
        if len(fresh['runs']) != 4:
            raise ValueError('four original seeds required')
        for new, prior in zip(fresh['runs'], meta['runs']):
            a = new['all_split']
            if (new['seed'] != prior['seed'] or new['primary_hits'] != prior['primary_hits'] or
                    a['own_checks'] != a['component_attempts'] - a['component_nulls'] or
                    not np.isfinite([a['max_own_log_error'], a['max_conditioned_error_fraction'],
                                     a['max_unconditioned_error_fraction']]).all() or
                    a['max_own_log_error'] > 1e-6 or a['max_conditioned_error_fraction'] > 1):
                raise ValueError('full original primary/proposal audit differs')
        means = np.stack([r['mean'] for r in rows])
        data = dict(mean=means.mean(0), se=means.std(0, ddof=1)/2, per_seed=rows, meta=fresh)
        physical = V.P.Result('N010-' + name, 'Unchanged original full sealed-room component')
        derived = dict(fresh, name=name, geometry_hash_match=True,
                       run_counters=[{k: r[k] for k in ('seed', 'primary_hits', 'shadow_tests',
                                                       'shadow_blocked', 'backface_absorbed')} for r in fresh['runs']])
        physical.runs.append(derived)
        if name == 'sealed-dark':
            V.P.check_zero_all(physical, 'dark', data)
        else:
            physical.check('lit:direct_and_total_positive_every_pixel',
                           bool((data['mean'][..., 1, :] > 0).all() and (data['mean'][..., 3, :] > 0).all()))
        checks = physical.to_json()
        for p, h in list(D.INPUTS.items()):
            D.checked(Path(p), h)
        result.update(complete=True, all_pass=checks['pass'], physical_checks=checks, native_metadata=fresh,
                      deterministic_component_bits_primary_exact=True,
                      classification='ORIGINAL_FULL_SEALED_PHYSICAL_COMPLETE_NO_ADMISSION',
                      scope='One original full sealed-room artifact only; no corpus reference admission')
    except (ValueError, OSError, KeyError, AssertionError, subprocess.SubprocessError) as e:
        result.update(classification='ORIGINAL_FULL_SEALED_FAILURE_PARTIALS_RETAINED', failure=str(e))
    result['payload_sha256'] = hashes()
    save()
    print(json.dumps({k: result.get(k) for k in ('name', 'complete', 'all_pass', 'classification',
                                               'failure', 'elapsed_seconds', 'child_cpu_seconds')}, indent=2))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__ == '__main__':
    main()

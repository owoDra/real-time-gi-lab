#!/usr/bin/env python3
"""Plan105: one full original level5 artifact; analytic diagnostic, no gate."""
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

WORK = D.OUT / 'wide8-original-level5-full-v1'
OUTPUT = D.RESULTS / '258-wide8-original-level5-full-artifact.json'
PLAN = D.RESULTS.parent / 'experiments/105-original-full-level5-artifact.md'
NAME = 'A6b_level5_diag'


def main():
    if WORK.exists() or OUTPUT.exists():
        raise ValueError('refuse existing full level5; no retry')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    for p in (Path(__file__).resolve(), PLAN, Path(C.__file__), Path(D.__file__),
              D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(p)
    prototype = C.pinned_result('254')
    coverage = C.pinned_result('257')
    if not prototype['all_pass'] or not coverage['all_pass']:
        raise ValueError('terminal successful254/257 required; no waiting queue')
    pilot = next(r for r in coverage['rows'] if r['name'] == NAME)
    if (not pilot['pass_'] or pilot['spp'] != 8 or pilot['child_cpu_seconds'] * 32 > 900
            or pilot['elapsed_seconds'] * 32 > 1350):
        raise ValueError('full level5 projected resource margin absent')
    binary = D.OUT / 'wide8-cpu-bvh-v1/n010_wide8_exporter'
    D.checked(binary, prototype['payload_sha256'][str(binary)])
    original = D.OUT / 'sampler-validation-v1/rqmc'
    proof = json.loads(D.checked(D.RESULTS / '022-cached-oracle-equivalence.json'))
    old = next(r for r in proof['rows'] if r['name'] == NAME)
    meta = json.loads(D.checked(original / (NAME + '.meta.json'), old['original_metadata_sha256']))
    scene = original / (NAME + '.n008')
    D.checked(scene, old['scene_sha256'])
    for payload in old['payloads']:
        D.checked(original / (NAME + payload['payload']), payload['old_sha256'])
    if (meta['spp'] != 256 or meta['seeds'] != list(D.SEEDS)
            or (meta['width'], meta['height']) != (128, 96)):
        raise ValueError('original full level5 identity differs')
    net = D.OUT / 'sobol16x262144.bin'
    D.checked(net)
    sys.path.insert(0, str(D.HERE.parent / 'n010_comparison_readiness'))
    import validate_sampler as V
    for p in (Path(V.__file__), Path(V.P.__file__), Path(V.L.__file__)):
        D.checked(p)
    authored, vertices, faces = V.P.sphere_scene((.9, .6, .3), (.3, .2, -.1), (2, 2, 2), 8, level=5)
    if authored.text() != scene.read_text() or authored.geometry_sha256() != meta['geometry_sha256']:
        raise ValueError('independent original authored level5 differs')
    _, _, indirect, bounds = V.P.sphere_expected(authored, (.9, .6, .3), (.3, .2, -.1),
                                               (2, 2, 2), 8, (vertices, faces))
    WORK.mkdir()
    prefix = WORK / NAME
    receipt = WORK / 'native.resources.json'
    command = [str(binary), '--net', str(net), '--scene', str(scene), '--out', str(prefix),
               '--seeds', ','.join(map(str, D.SEEDS)), '--spp', '256', '--threads', '1']
    result = dict(schema='n010-wide8-original-full-level5-artifact/1', complete=False,
                  all_pass=False, gpu_run=False, reference_admission=False,
                  physical_gate_decision='NOT_APPLICABLE_ORIGINAL_DIAGNOSTIC_ONLY',
                  classification='ORIGINAL_FULL_LEVEL5_NATIVE_ACQUIRING',
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  input_sha256=D.INPUTS, command=command,
                  operational_projection=dict(cpu_seconds=pilot['child_cpu_seconds'] * 32,
                                              elapsed_seconds=pilot['elapsed_seconds'] * 32,
                                              scope='Retained low-count linear cost planning, not ETA'),
                  native_limits=dict(cpu_seconds=1200, elapsed_seconds=1800,
                                     address_space_bytes=4 * 1024**3,
                                     affinity=sorted(os.sched_getaffinity(0)), nice=15),
                  scheduling='One original full native; no retry or next-artifact queue',
                  tests='NOT_RUN; original scientific full diagnostic artifact acquisition')

    def hashes():
        return {str(p): C.sha(p) for p in sorted(WORK.iterdir()) if p.is_file()}

    def save():
        OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')

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
        except subprocess.TimeoutExpired as error:
            (WORK / 'native.stdout').write_bytes(error.stdout or b'')
            (WORK / 'native.stderr').write_bytes(error.stderr or b'')
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            result.update(returncode='NOT_EXPOSED_BY_TIMEOUTEXPIRED',
                          elapsed_seconds=time.monotonic()-started,
                          child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                          payload_sha256=hashes())
            save()
            raise ValueError('full level5 elapsed guard; no retry') from error
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        (WORK / 'native.stdout').write_text(proc.stdout)
        (WORK / 'native.stderr').write_text(proc.stderr)
        result.update(returncode=proc.returncode, elapsed_seconds=time.monotonic()-started,
                      child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                      classification='ORIGINAL_FULL_LEVEL5_NATIVE_TERMINAL_ANALYSIS_PENDING',
                      payload_sha256=hashes())
        save()
        actual = json.loads(D.checked(receipt))
        if (actual['cpu'] != [1200] * 2 or actual['address_space'] != [4 * 1024**3] * 2
                or len(actual['affinity']) != 1 or actual['nice'] != 15):
            raise ValueError('actual full level5 resource scope differs')
        if proc.returncode:
            raise ValueError('full level5 native failure; no retry')
        resource.setrlimit(resource.RLIMIT_CPU, (220,) * 2)
        fresh = json.loads(proc.stdout)
        (WORK / (NAME + '.meta.json')).write_text(json.dumps(fresh, indent=2) + '\n')
        for key in ('scene_sha256', 'geometry_sha256', 'width', 'height', 'spp', 'seeds',
                    'triangles', 'point_lights', 'ray_offset'):
            if fresh[key] != meta[key]:
                raise ValueError('full level5 identity differs ' + key)
        rows = [V.L.read_sidecar(Path(str(prefix) + f'.s{i}.f64')) for i in range(4)]
        old_rows = [V.L.read_sidecar(original / f'{NAME}.s{i}.f64') for i in range(4)]
        for i, (new, prior) in enumerate(zip(rows, old_rows)):
            if (new['seed'] != D.SEEDS[i] or new['spp'] != 256
                    or (new['width'], new['height']) != (128, 96)):
                raise ValueError('full level5 sidecar identity differs')
            for field in ('mean', 'm2'):
                if not (np.isfinite(new[field]).all() and (new[field] >= 0).all()):
                    raise ValueError('nonfinite/negative full level5 sidecar')
                if new[field][..., :2, :].tobytes() != prior[field][..., :2, :].tobytes():
                    raise ValueError('full level5 original deterministic bits differ')
            for component in ('emission', 'direct', 'indirect', 'total'):
                image = V.L.read_pfm(Path(str(prefix) + f'.s{i}.{component}.pfm'))
                if not (np.isfinite(image).all() and (image >= 0).all()):
                    raise ValueError('nonfinite/negative full level5 PFM')
        if prefix.with_suffix('.hits').read_bytes() != (original / (NAME + '.hits')).read_bytes():
            raise ValueError('full level5 original hit bytes differ')
        if len(fresh['runs']) != 4:
            raise ValueError('full level5 four seeds absent')
        for new, prior in zip(fresh['runs'], meta['runs']):
            a = new['all_split']
            if (new['seed'] != prior['seed'] or new['primary_hits'] != prior['primary_hits']
                    or a['own_checks'] != a['component_attempts'] - a['component_nulls']
                    or not np.isfinite([a['max_own_log_error'], a['max_conditioned_error_fraction'],
                                       a['max_unconditioned_error_fraction']]).all()
                    or a['max_own_log_error'] > 1e-6 or a['max_conditioned_error_fraction'] > 1):
                raise ValueError('full level5 original primary/proposal audit differs')
        means = np.stack([r['mean'] for r in rows]).mean(0)
        got = means[..., 2, :]
        prediction = np.broadcast_to(indirect, got.shape)
        for p, digest in list(D.INPUTS.items()):
            D.checked(Path(p), digest)
        result.update(complete=True, all_pass=True,
                      classification='ORIGINAL_FULL_LEVEL5_DIAGNOSTIC_COMPLETE_NO_ADMISSION',
                      original_deterministic_primary_bits_exact=True, native_metadata=fresh,
                      original_full_artifacts_retained=14,
                      analytic_diagnostic=dict(expected_indirect=indirect.tolist(), mesh_bounds=bounds,
                          per_channel_region_relative_error=(got.mean((0, 1)) / indirect - 1).tolist(),
                          nrmse=float(np.sqrt(np.mean((got-prediction)**2) / np.mean(prediction**2))),
                          decision='NOT_GATED; original diagnostic-only mesh level'),
                      scope='One original full256 diagnostic artifact; no A6b analytic/IID gate or reference admission')
    except (ValueError, OSError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        result.update(classification='ORIGINAL_FULL_LEVEL5_FAILURE_PARTIALS_RETAINED', failure=str(error))
    result['payload_sha256'] = hashes()
    save()
    print(json.dumps({k: result.get(k) for k in ('complete', 'all_pass', 'classification', 'failure',
                                               'elapsed_seconds', 'child_cpu_seconds')}, indent=2))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__ == '__main__':
    main()

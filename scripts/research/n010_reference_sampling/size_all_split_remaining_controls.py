#!/usr/bin/env python3
"""Plan087: cost-only inventory; refuses live234, never starts full controls."""
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK = D.OUT / 'all-split-remaining-controls-cost-v1'
OUTPUT = D.RESULTS / '236-all-split-remaining-controls-cpu-cost.json'
PLAN = D.RESULTS.parent / 'experiments/087-remaining-original-controls-cost.md'
SCENES = (('A6a', 8192), ('A6b', 8192), ('A6b_level5_diag', 256),
          ('A10', 8192), ('sealed-dark', 1024), ('sealed-lit', 1024))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if WORK.exists() or OUTPUT.exists():
        raise ValueError('refuse existing remaining-control cost inventory')
    require_no_other_research_worker()
    previous = json.loads(D.checked(D.RESULTS / '234-all-split-original-a6c-full-physical-control.json'))
    if not previous.get('complete') or not previous.get('all_pass'):
        raise ValueError('terminal successful original full A6c required; no waiting queue')
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (120,) * 2)
    for p in (Path(__file__).resolve(), PLAN, Path(D.__file__),
              D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(p)
    build = json.loads(D.checked(D.RESULTS / '224-all-split-exporter-build.json'))
    if not build.get('complete') or not build.get('all_pass'):
        raise ValueError('unchanged successful exporter build required')
    for p, digest in build['payload_sha256'].items():
        D.checked(Path(p), digest)
    proof = json.loads(D.checked(D.RESULTS / '022-cached-oracle-equivalence.json'))
    original = D.OUT / 'sampler-validation-v1/rqmc'
    inputs = {}
    for name, full_count in SCENES:
        row = next(r for r in proof['rows'] if r['name'] == name)
        meta = json.loads(D.checked(original / (name + '.meta.json'), row['original_metadata_sha256']))
        scene = original / (name + '.n008')
        D.checked(scene, row['scene_sha256'])
        for payload in row['payloads']:
            D.checked(original / (name + payload['payload']), payload['old_sha256'])
        if (meta['spp'] != full_count or meta['seeds'] != list(D.SEEDS)
                or (meta['width'], meta['height']) != (128, 96)):
            raise ValueError('original count/seed/shape differs: ' + name)
        inputs[name] = (scene, meta)
    net = D.OUT / 'sobol16x262144.bin'
    D.checked(net)
    binary = D.OUT / 'all-split-exporter-v1/n010_all_split_oracle'
    sys.path.insert(0, str(D.HERE.parent / 'n008_hdr_oracle'))
    import n008lib as L
    D.checked(Path(L.__file__))
    WORK.mkdir()
    result = dict(schema='n010-all-split-remaining-controls-cpu-cost/1', complete=False,
                  gpu_run=False, reference_admission=False,
                  classification='COST_INVENTORY_ACQUIRING', input_sha256=D.INPUTS,
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  rows=[], full_acquisitions='NOT_RUN_NOT_QUEUED',
                  physical_control_decision='NOT_APPLICABLE_COST_ONLY',
                  budget=dict(total_native_cpu_seconds=180, total_native_elapsed_seconds=240,
                              per_native_cpu_seconds=90, per_native_elapsed_seconds=120),
                  tests='NOT_RUN; original-scene cost-only scientific inventory')

    def hashes():
        return {str(p): sha(p) for p in sorted(WORK.rglob('*')) if p.is_file()}

    def save():
        OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')

    save()
    native_cpu = native_elapsed = 0.0
    try:
        for name, full_count in SCENES:
            require_no_other_research_worker()
            for p, digest in list(D.INPUTS.items()):
                D.checked(Path(p), digest)
            cpu_limit = min(90, math.floor(180 - native_cpu))
            elapsed_limit = min(120.0, 240 - native_elapsed)
            if cpu_limit < 1 or elapsed_limit < 1:
                raise ValueError('total cost inventory resource budget exhausted; no retry')
            directory = WORK / name
            directory.mkdir()
            prefix = directory / name
            receipt = directory / 'native.resources.json'
            scene, original_meta = inputs[name]
            command = [str(binary), '--net', str(net), '--scene', str(scene), '--out', str(prefix),
                       '--seeds', ','.join(map(str, D.SEEDS)), '--spp', '8', '--threads', '1']
            row = dict(name=name, original_spp=full_count, pilot_spp=8, command=command,
                       classification='NATIVE_ACQUIRING', pass_cost_integrity=False,
                       native_cpu_limit=cpu_limit, native_elapsed_limit=elapsed_limit)
            result['rows'].append(row)
            save()

            def limits():
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit,) * 2)
                receipt.write_text(json.dumps(dict(pid=os.getpid(),
                    start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
                    address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                    command=command)) + '\n')

            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            start = time.monotonic()
            try:
                proc = subprocess.run(command, capture_output=True, text=True,
                                      timeout=elapsed_limit, preexec_fn=limits)
            except subprocess.TimeoutExpired as error:
                (directory / 'native.stdout').write_bytes(error.stdout or b'')
                (directory / 'native.stderr').write_bytes(error.stderr or b'')
                after = resource.getrusage(resource.RUSAGE_CHILDREN)
                elapsed = time.monotonic() - start
                cpu = (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime)
                native_cpu += cpu
                native_elapsed += elapsed
                row.update(classification='NATIVE_TIMEOUT_PARTIALS_RETAINED',
                           child_cpu_seconds=cpu, elapsed_seconds=elapsed,
                           returncode='NOT_EXPOSED_BY_TIMEOUTEXPIRED')
                result.update(native_cpu_seconds=native_cpu, native_elapsed_seconds=native_elapsed,
                              payload_sha256=hashes())
                save()
                raise ValueError('cost elapsed guard; no retry') from error
            elapsed = time.monotonic() - start
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu = (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime)
            native_cpu += cpu
            native_elapsed += elapsed
            (directory / 'native.stdout').write_text(proc.stdout)
            (directory / 'native.stderr').write_text(proc.stderr)
            row.update(returncode=proc.returncode, child_cpu_seconds=cpu, elapsed_seconds=elapsed,
                       classification='NATIVE_TERMINAL_ANALYSIS_PENDING')
            result.update(native_cpu_seconds=native_cpu, native_elapsed_seconds=native_elapsed,
                          payload_sha256=hashes())
            save()  # Terminal native receipt survives every subsequent analysis exception.
            actual = json.loads(D.checked(receipt))
            if (actual['cpu'] != [cpu_limit] * 2 or actual['address_space'] != [4 * 1024**3] * 2
                    or len(actual['affinity']) != 1 or actual['nice'] != 15):
                raise ValueError('actual native resource scope differs')
            if proc.returncode:
                raise ValueError('cost native failed; no retry')
            fresh = json.loads(proc.stdout)
            if (any(fresh[k] != original_meta[k] for k in
                    ('scene_sha256', 'geometry_sha256', 'width', 'height', 'seeds'))
                    or fresh['spp'] != 8 or len(fresh['runs']) != 4):
                raise ValueError('cost scene/count/seed differs')
            rows = [L.read_sidecar(Path(str(prefix) + f'.s{i}.f64')) for i in range(4)]
            if any(r['seed'] != s or r['spp'] != 8 or (r['width'], r['height']) != (128, 96)
                   or not all(np.isfinite(r[k]).all() and (r[k] >= 0).all() for k in ('mean', 'm2'))
                   for r, s in zip(rows, D.SEEDS)):
                raise ValueError('cost sidecar identity/finite/nonnegative guard')
            if any(r[k][..., :2, :].tobytes() != rows[0][k][..., :2, :].tobytes()
                   for r in rows for k in ('mean', 'm2')):
                raise ValueError('same-count inter-seed deterministic fields differ')
            if prefix.with_suffix('.hits').read_bytes() != (original / (name + '.hits')).read_bytes():
                raise ValueError('original primary-hit bytes differ')
            for run, old in zip(fresh['runs'], original_meta['runs']):
                a = run['all_split']
                if (run['seed'] != old['seed'] or run['primary_hits'] * full_count != old['primary_hits'] * 8
                        or a['own_checks'] != a['component_attempts'] - a['component_nulls']
                        or not np.isfinite([a['max_own_log_error'], a['max_conditioned_error_fraction'],
                                            a['max_unconditioned_error_fraction']]).all()
                        or a['max_own_log_error'] > 1e-6 or a['max_conditioned_error_fraction'] > 1):
                    raise ValueError('cost primary/proposal audit failed')
            row.update(classification='COST_COMPLETE_NO_PHYSICAL_OR_REFERENCE_ADMISSION',
                       pass_cost_integrity=True, native_metadata=fresh,
                       estimated_full_count_cpu_seconds=cpu * full_count / 8,
                       estimated_full_count_elapsed_seconds=elapsed * full_count / 8,
                       estimate_scope='Linear setup+output+work scaling; planning only, not a whole-run ETA')
            save()
        for p, digest in list(D.INPUTS.items()):
            D.checked(Path(p), digest)
        result.update(complete=True, classification='COST_INVENTORY_COMPLETE_NO_PHYSICAL_OR_REFERENCE_ADMISSION')
    except (ValueError, OSError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        result.update(classification='COST_INVENTORY_FAILURE_PARTIALS_RETAINED', failure=str(error))
    result['payload_sha256'] = hashes()
    save()
    print(json.dumps({k: result.get(k) for k in ('complete', 'classification', 'failure',
                                               'native_cpu_seconds', 'native_elapsed_seconds')}, indent=2))
    raise SystemExit(0 if result['complete'] else 2)


if __name__ == '__main__':
    main()

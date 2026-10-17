#!/usr/bin/env python3
"""Plan104: fixed retained-count backend coverage, not reference admission."""
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import time

import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK = D.OUT / 'wide8-original-control-coverage-v1'
OUTPUT = D.RESULTS / '257-wide8-original-control-coverage.json'
PLAN = D.RESULTS.parent / 'experiments/104-wide8-original-control-coverage.md'
DETERMINISTIC = ('A2', 'A2b', 'A4a', 'A4b', 'A8_authored',
                 'A8_frozen', 'A8_stale_rest_pose')
SIDEDNESS = ('A4c', 'A4d')
COST_NAMES = ('A6b', 'A6b_level5_diag', 'A10', 'sealed-dark', 'sealed-lit')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_result(stem):
    paths = list(D.RESULTS.glob(stem + '-*'))
    if len(paths) != 1:
        raise ValueError('nonunique result ' + stem)
    data = json.loads(D.checked(paths[0]))
    if not data.get('complete'):
        raise ValueError('terminal complete prerequisite absent ' + stem)
    for path, digest in data.get('payload_sha256', {}).items():
        D.checked(Path(path), digest)
    return data


def main():
    if WORK.exists() or OUTPUT.exists():
        raise ValueError('refuse existing coverage; no retry')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (220,) * 2)
    for p in (Path(__file__).resolve(), PLAN, Path(D.__file__),
              D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(p)
    prototype = pinned_result('254')
    timing = json.loads(D.checked(D.RESULTS / '255-orderstat-uncertainty-c7-calibration-diagnostic.json'))
    if (not prototype['all_pass'] or not prototype['execution_promising']
            or not timing['complete']):
        raise ValueError('terminal254 promising and terminal255 required')
    binary = D.OUT / 'wide8-cpu-bvh-v1/n010_wide8_exporter'
    D.checked(binary, prototype['payload_sha256'][str(binary)])
    original = D.OUT / 'sampler-validation-v1/rqmc'
    cases = []
    for stem, names, folder in (
            ('226', DETERMINISTIC, 'all-split-full-deterministic-v1'),
            ('225', SIDEDNESS, 'all-split-full-sidedness-v1')):
        proof = pinned_result(stem)
        if not proof['all_pass']:
            raise ValueError('original deterministic evidence failed')
        for name in names:
            row = next(r for r in proof['rows'] if r['name'] == name)
            command = list(row['command'])
            prefix = Path(command[command.index('--out') + 1])
            meta = json.loads(D.checked(D.OUT / folder / (name + '.meta.json')))
            cases.append((name, command, prefix, meta, proof, stem))
    for stem, name in (('229', 'A7'), ('232', 'A6c')):
        proof = pinned_result(stem)
        command = list(proof['command'])
        prefix = Path(command[command.index('--out') + 1])
        stdout = prefix.parent / 'native.stdout'
        meta = json.loads(D.checked(stdout))
        cases.append((name, command, prefix, meta, proof, stem))
    cost = pinned_result('236')
    for name in COST_NAMES:
        row = next(r for r in cost['rows'] if r['name'] == name)
        if not row['pass_cost_integrity']:
            raise ValueError('retained cost integrity absent')
        command = list(row['command'])
        prefix = Path(command[command.index('--out') + 1])
        cases.append((name, command, prefix, row['native_metadata'], cost, '236'))
    expected = set(DETERMINISTIC + SIDEDNESS + ('A7', 'A6c', 'A6a') + COST_NAMES)
    if len(cases) != 16 or len(expected) != 17 or {c[0] for c in cases} | {'A6a'} != expected:
        raise ValueError('original seventeen-artifact coverage differs')
    for name, command, prefix, meta, proof, stem in cases:
        scene = Path(command[command.index('--scene') + 1])
        D.checked(scene, meta['scene_sha256'])
        D.checked(Path(command[command.index('--net') + 1]))
        if (meta['seeds'] != list(D.SEEDS) or (meta['width'], meta['height']) != (128, 96)
                or len(meta['runs']) != 4):
            raise ValueError('retained identity differs ' + name)
        if scene != original / (name + '.n008'):
            raise ValueError('unexpected original scene path ' + name)
    WORK.mkdir()
    result = dict(schema='n010-wide8-original-control-coverage/1', complete=False,
                  all_pass=False, gpu_run=False, reference_admission=False,
                  classification='RETAINED_COUNT_BACKEND_COVERAGE_ACQUIRING',
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  input_sha256=D.INPUTS, rows=[], inherited_a6a_result='254',
                  original_control_names=sorted(expected), original_full_inventory=13,
                  scope='Nine original full64 deterministic cases; eight other cases at retained low counts only',
                  budget=dict(total_native_cpu_seconds=180, total_native_elapsed_seconds=240,
                              per_native_cpu_seconds=60, per_native_elapsed_seconds=90),
                  tests='NOT_RUN; fixed scientific backend identity acquisition')

    def hashes():
        return {str(p): sha(p) for p in sorted(WORK.rglob('*')) if p.is_file()}

    def save():
        OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')

    total_cpu = total_elapsed = 0.0
    save()
    try:
        for name, command, old_prefix, meta, proof, stem in cases:
            require_no_other_research_worker()
            cpu_limit = min(60, math.floor(180 - total_cpu))
            elapsed_limit = min(90, 240 - total_elapsed)
            if cpu_limit < 1 or elapsed_limit < 1:
                raise ValueError('coverage total native budget exhausted; no retry')
            directory = WORK / name
            directory.mkdir()
            prefix = directory / name
            receipt = directory / 'native.resources.json'
            command[0] = str(binary)
            command[command.index('--out') + 1] = str(prefix)
            row = dict(name=name, baseline_result=stem, spp=meta['spp'],
                       original_full_count=meta['spp'] == 64 and name in DETERMINISTIC + SIDEDNESS,
                       command=command, pass_=False, cpu_limit=cpu_limit,
                       elapsed_limit=elapsed_limit, classification='NATIVE_ACQUIRING')
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
                row.update(returncode='NOT_EXPOSED_BY_TIMEOUTEXPIRED',
                           elapsed_seconds=time.monotonic() - start,
                           child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                           classification='NATIVE_TIMEOUT_PARTIALS_RETAINED')
                result['payload_sha256'] = hashes()
                save()
                raise ValueError('elapsed guard; no retry') from error
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            elapsed = time.monotonic() - start
            cpu = after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime
            total_cpu += cpu
            total_elapsed += elapsed
            (directory / 'native.stdout').write_text(proc.stdout)
            (directory / 'native.stderr').write_text(proc.stderr)
            row.update(returncode=proc.returncode, elapsed_seconds=elapsed,
                       child_cpu_seconds=cpu, classification='NATIVE_TERMINAL_ANALYSIS_PENDING')
            result.update(native_cpu_seconds=total_cpu, native_elapsed_seconds=total_elapsed,
                          payload_sha256=hashes())
            save()
            actual = json.loads(D.checked(receipt))
            if (actual['cpu'] != [cpu_limit] * 2 or actual['address_space'] != [4 * 1024**3] * 2
                    or len(actual['affinity']) != 1 or actual['nice'] != 15):
                raise ValueError('actual resource scope differs ' + name)
            if proc.returncode:
                raise ValueError('native failed; no retry ' + name)
            fresh = json.loads(proc.stdout)
            (directory / (name + '.meta.json')).write_text(json.dumps(fresh, indent=2) + '\n')
            for key in ('scene_sha256', 'geometry_sha256', 'width', 'height', 'spp', 'seeds',
                        'ray_offset', 'point_lights', 'triangles', 'oracle', 'version'):
                if fresh[key] != meta[key]:
                    raise ValueError('metadata identity differs ' + name + ' ' + key)
            if len(fresh['runs']) != 4:
                raise ValueError('four original seeds missing ' + name)
            for new, old in zip(fresh['runs'], meta['runs']):
                for key in ('seed', 'primary_hits', 'shadow_tests', 'shadow_blocked',
                            'backface_absorbed', 'all_split'):
                    if new[key] != old[key]:
                        raise ValueError('integer/proposal audit differs ' + name + ' ' + key)
            old_payloads = [Path(p) for p in proof['payload_sha256'] if Path(p).parent == old_prefix.parent
                            and Path(p).name.startswith(name + '.')
                            and Path(p).suffix in ('.f64', '.pfm', '.hits')]
            if len(old_payloads) != 21:
                raise ValueError('retained21 payloads absent ' + name)
            identities = []
            for old in sorted(old_payloads):
                new = directory / old.name
                equal = new.read_bytes() == old.read_bytes()
                identities.append(dict(name=old.name, sha256=sha(new),
                                       original_sha256=proof['payload_sha256'][str(old)],
                                       byte_identical=equal))
                if not equal:
                    raise ValueError('output bytes differ ' + name + ' ' + old.name)
            row.update(pass_=True, classification='RETAINED_COUNT_BYTES_AND_AUDITS_EXACT',
                       payload_identities=identities, native_metadata=fresh)
            save()
        for p, digest in list(D.INPUTS.items()):
            D.checked(Path(p), digest)
        result.update(complete=True, all_pass=True,
                      classification='SEVENTEEN_ARTIFACT_RETAINED_COUNT_COVERAGE_PASS_NO_ADMISSION',
                      nine_original_full64_artifacts_exact=True,
                      original_full_inventory_unchanged=13, eligible_references_unchanged=16,
                      full_control_or_reference_queue='NOT_RUN_NOT_QUEUED')
    except (ValueError, OSError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        result.update(classification='COVERAGE_FAILURE_PARTIALS_RETAINED', failure=str(error))
    result['payload_sha256'] = hashes()
    save()
    print(json.dumps({k: result.get(k) for k in ('complete', 'all_pass', 'classification',
                                               'failure', 'native_cpu_seconds', 'native_elapsed_seconds')}, indent=2))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__ == '__main__':
    main()

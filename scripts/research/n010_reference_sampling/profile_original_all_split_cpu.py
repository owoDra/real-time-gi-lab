#!/usr/bin/env python3
"""Plan091: own unchanged CPU oracle, user IP-only perf samples, no new estimator."""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import time

import numpy as np
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK = D.OUT / 'original-all-split-cpu-profile-v1'
OUTPUT = D.RESULTS / '239-original-all-split-cpu-profile.json'
PLAN = D.RESULTS.parent / 'experiments/091-original-all-split-cpu-profile.md'
PERF = Path('/nix/store/r9yzbjkiz71ig7g26jdd9cc4pp8ymdph-perf-linux-7.2.10/bin/perf')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if WORK.exists() or OUTPUT.exists():
        raise ValueError('refuse existing original CPU profile')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    for p in (Path(__file__).resolve(), PLAN, Path(D.__file__), PERF,
              D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(p)
    build = json.loads(D.checked(D.RESULTS / '224-all-split-exporter-build.json'))
    costs = json.loads(D.checked(D.RESULTS / '236-all-split-remaining-controls-cpu-cost.json'))
    prior = json.loads(D.checked(D.RESULTS / '238-near-first-cpu-bvh-prototype.json'))
    c1_proof = json.loads(D.checked(D.RESULTS / '223-all-split-general-transport-equivalence.json'))
    if (not build['complete'] or not build['all_pass'] or not costs['complete']
            or not prior['complete'] or prior['execution_promising']):
        raise ValueError('original build/cost and stopped traversal decision required')
    for proof in (build, costs):
        for p, digest in proof['payload_sha256'].items():
            D.checked(Path(p), digest)
    a6a = next(r for r in costs['rows'] if r['name'] == 'A6a')
    binary = Path(a6a['command'][0])
    net = D.OUT / 'sobol16x262144.bin'
    c1 = D.OUT / 'references-recovery-sponza-v1/C1_T_B8/scene.n008'
    D.checked(net); D.checked(c1, c1_proof['input_sha256'][str(c1)])
    a6a_scene = Path(a6a['command'][a6a['command'].index('--scene') + 1])
    sys.path.insert(0, str(D.HERE.parent / 'n008_hdr_oracle'))
    import n008lib as L
    D.checked(Path(L.__file__))
    WORK.mkdir()
    result = dict(schema='n010-original-all-split-cpu-profile/1', complete=False,
                  gpu_run=False, reference_admission=False, classification='CPU_PROFILE_ACQUIRING',
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  input_sha256=D.INPUTS, rows=[],
                  perf_version=subprocess.check_output([str(PERF), '--version'], text=True).strip(),
                  perf_event_paranoid_read_only=Path('/proc/sys/kernel/perf_event_paranoid').read_text().strip(),
                  tests='NOT_RUN; own unchanged binary scientific CPU hotspot diagnosis',
                  scope='User IP-only sampling; no raw stacks/kernel/GPU/other-app data or performance admission')

    def hashes():
        return {str(p): sha(p) for p in sorted(WORK.rglob('*')) if p.is_file()}

    def save():
        OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')

    save()
    env = dict(os.environ, DEBUGINFOD_URLS='', PERF_PAGER='cat')

    def execute(command, directory, tag, record_native=False):
        receipt = directory / (tag + '.resources.json')
        cpu_limit, elapsed_limit = (220, 300) if record_native else (60, 90)
        attempt = dict(command=command, cpu_limit_seconds=cpu_limit,
                       elapsed_limit_seconds=elapsed_limit, native_processes=[])
        current['attempts'].append(attempt)
        save()

        def limits():
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit,) * 2)
            resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024**2,) * 2)
            receipt.write_text(json.dumps(dict(pid=os.getpid(),
                start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
                cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
                address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                file_size=list(resource.getrlimit(resource.RLIMIT_FSIZE)),
                affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                command=command)) + '\n')

        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        start = time.monotonic()
        proc = subprocess.Popen(command, cwd=directory, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, preexec_fn=limits,
                                start_new_session=True)
        known = set()
        timed_out = False
        while True:
            if record_native:
                queue = [proc.pid]
                while queue:
                    pid = queue.pop()
                    try:
                        p = Path('/proc') / str(pid)
                        children = (p / 'task' / str(pid) / 'children').read_text().split()
                        queue.extend(map(int, children))
                        words = (p / 'cmdline').read_bytes().split(b'\0')
                        fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
                        identity = (pid, int(fields[19]))
                        if words[0].decode() == str(binary) and identity not in known:
                            known.add(identity)
                            attempt['native_processes'].append(dict(pid=pid, start_ticks=identity[1],
                                cpu=list(resource.prlimit(pid, resource.RLIMIT_CPU)),
                                address_space=list(resource.prlimit(pid, resource.RLIMIT_AS)),
                                affinity=sorted(os.sched_getaffinity(pid)), nice=os.getpriority(os.PRIO_PROCESS, pid),
                                command=[w.decode() for w in words if w]))
                            save()
                    except (OSError, ValueError, IndexError):
                        pass
            try:
                stdout, stderr = proc.communicate(timeout=.25)
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() - start >= elapsed_limit:
                    # A live Popen handle owns this newly created process group.
                    os.killpg(proc.pid, signal.SIGKILL)
                    stdout, stderr = proc.communicate()
                    timed_out = True
                    break
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        (directory / (tag + '.stdout')).write_text(stdout)
        (directory / (tag + '.stderr')).write_text(stderr)
        attempt.update(returncode=proc.returncode, elapsed=time.monotonic() - start,
                       root_and_descendants_cpu_seconds=(after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime),
                       timed_out=timed_out)
        result['payload_sha256'] = hashes(); save()
        actual = json.loads(D.checked(receipt))
        if (actual['cpu'] != [cpu_limit] * 2 or actual['address_space'] != [4 * 1024**3] * 2
                or len(actual['affinity']) != 1 or actual['nice'] != 15):
            raise ValueError('actual profiler/analysis resources differ')
        if proc.returncode or timed_out:
            raise ValueError('profiling/analysis failed; retain permission/error outcome, no retry')
        if record_native:
            if len(attempt['native_processes']) != 1:
                raise ValueError('actual native process receipt missing or extra native')
            native = attempt['native_processes'][0]
            if (native['cpu'] != [220] * 2 or native['address_space'] != [4 * 1024**3] * 2
                    or len(native['affinity']) != 1 or native['nice'] != 15):
                raise ValueError('actual native resources differ')
        return stdout

    try:
        for name, scene, spp, shape in (('A6a', a6a_scene, 8, (128, 96)), ('C1', c1, 1, (320, 180))):
            require_no_other_research_worker()
            directory = WORK / name
            directory.mkdir()
            prefix = directory / name
            native = [str(binary), '--net', str(net), '--scene', str(scene), '--out', str(prefix),
                      '--seeds', ','.join(map(str, D.SEEDS)), '--spp', str(spp), '--threads', '1']
            current = dict(name=name, spp=spp, native_command=native, attempts=[], complete=False)
            result['rows'].append(current)
            save()
            data = directory / 'perf.data'
            command = [str(PERF), 'record', '-e', 'cpu-clock:u', '-F', '99', '-m', '64',
                       '-o', str(data), '--'] + native
            stdout = execute(command, directory, 'record', record_native=True)
            meta = json.loads(stdout)
            if (meta['scene_sha256'] != sha(scene) or meta['seeds'] != list(D.SEEDS)
                    or meta['spp'] != spp or (meta['width'], meta['height']) != shape or len(meta['runs']) != 4):
                raise ValueError('profile native scene/count/seed differs')
            arrays = [L.read_sidecar(Path(str(prefix) + f'.s{i}.f64')) for i in range(4)]
            if any(r['seed'] != seed or r['spp'] != spp or (r['width'], r['height']) != shape
                   or not all(np.isfinite(r[k]).all() and (r[k] >= 0).all() for k in ('mean', 'm2'))
                   for r, seed in zip(arrays, D.SEEDS)):
                raise ValueError('profile sidecar identity/finite/nonnegative guard')
            for run in meta['runs']:
                a = run['all_split']
                if (a['own_checks'] != a['component_attempts'] - a['component_nulls']
                        or a['max_own_log_error'] > 1e-6 or a['max_conditioned_error_fraction'] > 1):
                    raise ValueError('profile original proposal audit failed')
            if name == 'A6a':
                original_prefix = Path(a6a['command'][a6a['command'].index('--out') + 1])
                paths = [Path(p) for p in costs['payload_sha256'] if Path(p).parent == original_prefix.parent
                         and Path(p).suffix in ('.f64', '.pfm', '.hits')]
                if len(paths) != 21 or any(p.read_bytes() != (directory / p.name).read_bytes() for p in paths):
                    raise ValueError('profiled A6a original236 payload bytes differ')
                for new, old in zip(meta['runs'], a6a['native_metadata']['runs']):
                    if any(new[k] != old[k] for k in ('seed', 'primary_hits', 'shadow_tests',
                                                     'shadow_blocked', 'backface_absorbed', 'all_split')):
                        raise ValueError('profiled A6a original metadata/audits differ')
                current['original236_all21_payloads_and_audits_exact'] = True
            report = execute([str(PERF), 'report', '--stdio', '--no-children', '--show-nr-samples',
                              '--percent-limit', '0', '--sort', 'dso,symbol', '-i', str(data)], directory, 'report')
            (directory / 'report.txt').write_text(report)
            ips = execute([str(PERF), 'script', '--show-lost-events', '-F', 'ip', '-i', str(data)], directory, 'ip-samples')
            samples = sum(bool(re.fullmatch(r'(?:0x)?[0-9a-fA-F]+', line.strip())) for line in ips.splitlines())
            if samples == 0:
                raise ValueError('no decoded CPU IP samples; no hotspot verdict')
            current.update(complete=True, native_metadata=meta, decoded_ip_sample_count=samples,
                           lost_record_lines=[line for line in ips.splitlines() if 'LOST' in line.upper()],
                           report_sha256=sha(directory / 'report.txt'),
                           scope='Profile-only self instruction samples; limited scope/overhead, no convergence or GI timing verdict')
            if sum(p.stat().st_size for p in WORK.rglob('*') if p.is_file()) > 256 * 1024**2:
                raise ValueError('profile spool exceeds256MiB')
            save()
        for p, digest in list(D.INPUTS.items()):
            D.checked(Path(p), digest)
        result.update(complete=True, classification='CPU_PROFILE_COMPLETE_DIAGNOSTIC_ONLY')
    except (ValueError, OSError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        result.update(classification='CPU_PROFILE_FAILURE_PARTIALS_RETAINED', failure=str(error))
    result['payload_sha256'] = hashes(); save()
    print(json.dumps({k: result.get(k) for k in ('complete', 'classification', 'failure')}, indent=2))
    raise SystemExit(0 if result['complete'] else 2)


if __name__ == '__main__':
    main()

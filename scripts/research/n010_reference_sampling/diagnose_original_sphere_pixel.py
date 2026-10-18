#!/usr/bin/env python3
"""Plan136: separately build or execute one immutable-oracle pixel probe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent/'experiments/136-original-sphere-one-pixel-diagnosis.md'
SOURCE = ROOT/'src/research/n010_comparison_readiness/original_sphere_pixel_probe.cpp'
OUT = ROOT/'out/research/n010-comparison-readiness'
WORK = OUT/'original-sphere-one-pixel-diagnosis-v1'
HEADER = OUT/'wide8-cpu-bvh-v1/n010_rqmc_oracle.hpp'
NET = OUT/'sobol16x262144.bin'
SCENE = OUT/'sampler-validation-v1/rqmc/A6a.n008'
BUILD = RESULTS/'434-original-sphere-pixel-probe-build.json'
PROBE = RESULTS/'435-original-sphere-pixel-probe.json'
INPUTS = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(path, expected=None):
    path = Path(path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('input identity differs: '+str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != digest:
        raise ValueError('input changed: '+str(path))
    INPUTS[str(path)] = digest
    return raw


def unchanged():
    for path, digest in list(INPUTS.items()):
        checked(path, digest)


def start_ticks(pid):
    try:
        return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])
    except FileNotFoundError:
        return None


def quiet():
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            name = (entry/'comm').read_text().strip()
            words = (entry/'cmdline').read_bytes().split(b'\0')
        except OSError:
            continue
        if name.startswith(('n010_', 'n008_oracle', 'phos-', 'gi_')) or any(
                w.startswith((b'scripts/research/', str(ROOT/'scripts/research').encode()+b'/'))
                for w in words):
            raise ValueError('another research worker remains: '+entry.name+' '+name)


def own_lines(text):
    return [line for line in text.splitlines()
            if line.startswith(('ALL_SPLIT_OWN ', 'OWN_VERTEX '))]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage', choices=('build', 'probe'), required=True)
    args = ap.parse_args()
    os.sched_setaffinity(0, {31})
    priority = os.getpriority(os.PRIO_PROCESS, 0)
    if priority < 15:
        os.nice(15-priority)
    output = BUILD if args.stage == 'build' else PROBE
    part = WORK/args.stage
    if output.exists() or part.exists():
        raise ValueError('refuse existing result/work; no retry')
    quiet()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    for path in (Path(__file__).resolve(), PLAN, SOURCE):
        if subprocess.check_output(['git', 'show', commit+':'+str(path.relative_to(ROOT))]) != checked(path):
            raise ValueError('commit exact plan/driver/source before use')
    terminal = json.loads(checked(RESULTS/'433-original-a6a-seed2-terminal-failure.json'))
    if not (terminal['complete'] and terminal['terminal_identity_verified']
            and terminal['returncode'] == -6 and not terminal['native_live']
            and not terminal['scientific_seed_complete']):
        raise ValueError('terminal original261 numerical failure required')
    if start_ticks(terminal['native_pid']) == terminal['native_start_ticks']:
        raise ValueError('original process identity still exists; refuse overlap')
    for path, digest in terminal['input_sha256'].items():
        checked(path, digest)
    checked(HEADER, '40607186e96cad47e9386b4fcd78a71958894946a237e628c546566819970537')
    checked(NET)
    checked(SCENE)
    binary = WORK/'build/n010_original_pixel_probe'
    if args.stage == 'build':
        if WORK.exists():
            raise ValueError('refuse existing diagnosis directory')
        original = json.loads(checked(RESULTS/'254-wide8-cpu-bvh-prototype.json'))
        command = next(a['command'] for a in original['attempts']
                       if a['command'][0] == 'c++' and a['command'][-1].endswith('n010_wide8_exporter'))
        command = list(command)
        command[-3] = str(SOURCE)
        command[-1] = str(binary)
        command[1:1] = ['-I', str(HEADER.parent)]
        compiler = Path(shutil.which(command[0])).resolve()
        checked(compiler)
    else:
        build = json.loads(checked(BUILD))
        if not (build['complete'] and build['build_valid']):
            raise ValueError('complete reviewed build434 required')
        for group in ('input_sha256', 'payload_sha256'):
            for path, digest in build[group].items():
                checked(path, digest)
        command = [str(binary), str(NET), str(SCENE)]
        compiler = None
    unchanged()
    part.mkdir(parents=True)
    receipt = part/'native.resources.json'
    result = dict(schema='n010-original-sphere-one-pixel-diagnosis/1', stage=args.stage,
                  complete=False, build_valid=False, failure_reproduced=False,
                  posthoc=True, gpu_run=False, reference_admission=False,
                  accepted_timing=False, all_pass=False, source_commit=commit,
                  input_sha256=INPUTS, command=command,
                  compiler_realpath=str(compiler) if compiler else None,
                  original_header_unchanged=True, thresholds_unchanged=True,
                  classification='POSTHOC_ONE_PIXEL_PART_IN_PROGRESS',
                  tests='NOT_RUN; bounded scientific numerical diagnosis only')

    def save():
        output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
        resource.setrlimit(resource.RLIMIT_AS, (4*1024**3,)*2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(), pgid=os.getpgrp(),
            start_ticks=start_ticks(os.getpid()),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
            address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
            elapsed_limit_seconds=180, command=command))+'\n')

    save()
    try:
        quiet()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        started = time.monotonic()
        with (part/'native.stdout').open('wb') as out, (part/'native.stderr').open('wb') as err:
            child = subprocess.Popen(command, cwd=ROOT, stdout=out, stderr=err,
                                     start_new_session=True, preexec_fn=limits)
            result['native_pid'] = child.pid
            save()
            try:
                code = child.wait(timeout=180)
            except subprocess.TimeoutExpired:
                actual = json.loads(receipt.read_text())
                if (actual['pid'], actual['pgid'], actual['start_ticks']) != (
                        child.pid, child.pid, start_ticks(child.pid)):
                    raise ValueError('owned process identity differs; refuse signalling')
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(timeout=5)
                code = 'ELAPSED_GUARD_PARTIALS_RETAINED'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        result.update(returncode=code, elapsed_seconds=time.monotonic()-started,
                      child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
        save()
        actual = json.loads(checked(receipt))
        if not (actual['pid'] == child.pid and actual['pgid'] == child.pid
                and type(actual['start_ticks']) is int and actual['cpu'] == [120, 120]
                and actual['address_space'] == [4*1024**3]*2 and actual['affinity'] == [31]
                and actual['nice'] == 15 and actual['command'] == command
                and result['elapsed_seconds'] < 180 and result['child_cpu_seconds'] <= 120):
            raise ValueError('native resource boundary differs')
        if args.stage == 'build':
            if code != 0 or not binary.read_bytes().startswith(b'\x7fELF') or not os.access(binary, os.X_OK):
                raise ValueError('probe build failed; no native follows')
            if str(Path(shutil.which(command[0])).resolve()) != str(compiler):
                raise ValueError('compiler identity changed')
            result.update(build_valid=True, classification='PRIVATE_ORIGINAL_PIXEL_PROBE_BUILD_COMPLETE')
        else:
            observation = json.loads((part/'native.stdout').read_text())
            original = OUT/'wide8-original-sphere-seed-v1/A6a-seed2/native.stderr'
            expected = own_lines(checked(original).decode())
            observed = own_lines((part/'native.stderr').read_text())
            reproduced = (code == 77 and observation.get('exception_caught') is True
                          and observation.get('what') == 'own-family area-density mismatch'
                          and observation.get('pixel') == [96, 77]
                          and observation.get('seed') == 81985529216486895
                          and type(observation.get('sample_index')) is int
                          and 0 <= observation['sample_index'] < 8192
                          and len(expected) == 5 and observed == expected)
            if code not in (0, 77):
                raise ValueError('probe operational failure; partials retained')
            result.update(observation=observation, original_witness_lines=expected,
                          observed_witness_lines=observed, failure_reproduced=reproduced,
                          numerical_root_cause_established=False,
                          classification='ORIGINAL_ONE_PIXEL_FAILURE_REPRODUCED_NO_ADMISSION'
                          if reproduced else 'ORIGINAL_ONE_PIXEL_FAILURE_NOT_REPRODUCED_NO_ADMISSION')
        unchanged()
        result['terminal_identity_verified'] = True
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        result.update(failure=str(error), classification='ONE_PIXEL_PART_FAILURE_PARTIALS_RETAINED')
    result.update(complete=True, payload_sha256={str(p):sha(p) for p in part.iterdir() if p.is_file()})
    save()
    print(result['classification'])
    return 0 if result.get('terminal_identity_verified') else 2


if __name__ == '__main__':
    raise SystemExit(main())

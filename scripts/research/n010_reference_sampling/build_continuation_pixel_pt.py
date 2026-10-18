#!/usr/bin/env python3
"""Plans126/127: build only the isolated continuation PT, or describe its command plan.

--describe is metadata-only. Actual compilation requires terminal260 and
quiescence; no mode launches a GPU capture or a following research task.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
BUILD = ROOT / 'build/n009'
RESULTS = ROOT / 'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent / 'experiments/126-exact-sample-continuation-pixel-pt.md'
PREPARATION = RESULTS / '405-continuation-readback-source-prepare.json'
SOURCE = ROOT / 'out/research/n010-comparison-readiness/continuation-pixel-pt-accounted-source-v1'
WORK = SOURCE.with_name('continuation-pixel-pt-build-v1')
OUTPUT = RESULTS / '401-continuation-pixel-pt-build.json'
HOST = ROOT / 'src/research/n010_comparison_readiness/pixel_pt_main.cpp'
SHADER = ROOT / 'shaders/research/n010_comparison_readiness/n010_pixel_pt.comp.glsl'
INPUTS = {}


def checked(path, expected=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('input identity differs: ' + str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != digest:
        raise ValueError('input changed during build: ' + str(path))
    INPUTS[str(path)] = digest
    return raw


def unchanged():
    for name, digest in list(INPUTS.items()):
        checked(name, digest)


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
            raise ValueError('another research worker remains: ' + entry.name + ' ' + name)


def commands():
    checked(PREPARATION, '330746464fa7b73c01b20c4eb891f701d6a0bfeffb849c0fd3d6989e0ec83434')
    prep = json.loads(PREPARATION.read_bytes())
    if not (prep['complete'] and prep['source_preparation_valid'] and not prep['compiled']
            and prep['whole_host_inverse_exact'] and prep['whole_shader_inverse_exact']
            and prep['per_sample_transport_scalar_sum_body_byte_identical']):
        raise ValueError('valid uncompiled readback-accounted source405 required')
    for group in ('input_sha256', 'payload_sha256'):
        for name, digest in prep[group].items():
            checked(name, digest)
    checked(Path(__file__).resolve())
    checked(PLAN)
    checked(BUILD/'build.ninja')
    checked(BUILD/'phos-n010-pixel-pt', 'b96880ba40c8466b4210d9e5af0dad80855c96416496a6c47ad9dc7670d60ea0')
    checked(BUILD/'shaders/n010_pixel_pt.spv')
    text = subprocess.check_output(['ninja', '-C', str(BUILD), '-t', 'commands',
                                    'phos-n010-pixel-pt'], text=True)
    rows = []
    for line in text.splitlines():
        args = shlex.split(line)
        cwd = BUILD
        if args[:1] == ['cd'] and len(args) > 3 and args[2] == '&&':
            cwd, args = Path(args[1]), args[3:]
        if args[:2] == [':', '&&'] and args[-2:] == ['&&', ':']:
            args = args[2:-2]
        if '-c' in args or (str(SHADER) in args) or (
                '-o' in args and args[args.index('-o')+1] == 'phos-n010-pixel-pt'):
            if any(a in ('&&', ';', '|', ':') for a in args):
                raise ValueError('shell operation in native compiler command')
            rows.append((args, cwd))
    host = [(a, c) for a, c in rows if '-c' in a and Path(a[a.index('-c')+1]) == HOST]
    shaders = [(a, c) for a, c in rows if str(SHADER) in a]
    links = [(a, c) for a, c in rows if '-c' not in a and '-o' in a
             and a[a.index('-o')+1] == 'phos-n010-pixel-pt']
    if (len(host), len(shaders), len(links)) != (1, 1, 1):
        raise ValueError('unique original host/shader/link command required')
    compile_args, compile_cwd = host[0]
    old_object = compile_args[compile_args.index('-o')+1]
    deps = subprocess.check_output(['ninja', '-C', str(BUILD), '-t', 'deps', old_object], text=True)
    dependencies = [Path(line.strip()) for line in deps.splitlines() if line.startswith('    ')]
    if not dependencies:
        raise ValueError('original native dependency list unavailable')
    for path in dependencies:
        checked(path if path.is_absolute() else BUILD/path)
    obj = WORK/'continuation_pixel_pt.o'
    host_args = list(compile_args)
    for option, value in (('-c', SOURCE/'continuation_pixel_pt.cpp'), ('-o', obj),
                          ('-MT', obj), ('-MF', WORK/'continuation_pixel_pt.d')):
        host_args[host_args.index(option)+1] = str(value)
    defines = [i for i, a in enumerate(host_args) if a.startswith('-DPHOS_GI_INTEGRATION_SHADER_DIR=')]
    if len(defines) != 1:
        raise ValueError('unique private shader-directory definition required')
    host_args[defines[0]] = '-DPHOS_GI_INTEGRATION_SHADER_DIR="' + str(WORK/'shaders') + '"'
    shader_args, shader_cwd = shaders[0]
    shader_args = [str(SOURCE/'continuation_pixel_pt.comp.glsl') if a == str(SHADER) else a for a in shader_args]
    shader_args[shader_args.index('-o')+1] = str(WORK/'shaders/n010_pixel_pt.spv')
    link_args, link_cwd = links[0]
    link_args = list(link_args)
    if link_args.count(old_object) != 1:
        raise ValueError('original PT main object must occur exactly once in link')
    for i, a in enumerate(link_args):
        if a == old_object:
            link_args[i] = str(obj)
        elif a.startswith('-Wl,--dependency-file='):
            link_args[i] = '-Wl,--dependency-file=' + str(WORK/'continuation_pixel_pt.link.d')
        elif a.endswith(('.o', '.a')):
            checked(Path(a) if Path(a).is_absolute() else BUILD/a)
    link_args[link_args.index('-o')+1] = str(WORK/'phos-n010-continuation-pixel-pt')
    if '-ldl' not in link_args:
        raise ValueError('original Vulkan-loader link library missing')
    planned = [dict(label='shader', command=shader_args, cwd=str(shader_cwd)),
               dict(label='host', command=host_args, cwd=str(compile_cwd)),
               dict(label='link', command=link_args, cwd=str(link_cwd))]
    for row in planned:
        row['compiler_realpath'] = str(Path(row['command'][0]).resolve())
        checked(row['compiler_realpath'])
    return planned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--describe', action='store_true')
    args = parser.parse_args()
    os.sched_setaffinity(0, {31})
    priority = os.getpriority(os.PRIO_PROCESS, 0)
    if priority < 15:
        os.nice(15-priority)
    if not args.describe:
        quiet()
        control = json.loads(checked(RESULTS/'260-wide8-original-a6a-seed1.json'))
        if not control['complete'] or not control['seed_integrity_pass']:
            raise ValueError('terminal integrity-PASS260 required; no waiting/next-step queue')
        if OUTPUT.exists() or WORK.exists():
            raise ValueError('refuse existing build401 or work; no retry')
    planned = commands()
    unchanged()
    if args.describe:
        print(json.dumps(dict(classification='METADATA_ONLY_BUILD_COMMANDS_PREPARED',
            stages=[r['label'] for r in planned], immutable_inputs=len(INPUTS),
            private_binary=str(WORK/'phos-n010-continuation-pixel-pt'),
            native_compilers_launched=0, gpu_run=False)))
        return 0
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    frozen = subprocess.check_output(['git', 'show', commit + ':' + str(Path(__file__).resolve().relative_to(ROOT))])
    if hashlib.sha256(frozen).hexdigest() != INPUTS[str(Path(__file__).resolve())]:
        raise ValueError('commit the exact builder before native compilation')
    if os.getpriority(os.PRIO_PROCESS, 0) != 15:
        raise ValueError('actual nice15 required')
    if shutil.disk_usage(WORK.parent).free < 2 * 1024**3:
        raise ValueError('2GiB free-space guard; no compiler')
    WORK.mkdir()
    (WORK/'shaders').mkdir()
    result = dict(schema='n010-continuation-pixel-pt-build/1', complete=False, all_pass=False,
        build_valid=False, gpu_run=False, accepted_timing=False, reference_admission=False,
        source_commit=commit, input_sha256=INPUTS, attempts=[],
        classification='ISOLATED_COMPILATION_IN_PROGRESS',
        tests='NOT_RUN; isolated shader/host/link compilation only, no runtime/quality proof')

    def save():
        OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')

    save()
    try:
        for row in planned:
            quiet()
            unchanged()
            if str(Path(row['command'][0]).resolve()) != row['compiler_realpath']:
                raise ValueError('active compiler symlink changed')
            receipt = WORK/(row['label']+'.resources.json')
            stdout, stderr = WORK/(row['label']+'.stdout'), WORK/(row['label']+'.stderr')

            def limits():
                resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
                resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
                receipt.write_text(json.dumps(dict(pid=os.getpid(), pgid=os.getpgrp(),
                    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
                    address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                    elapsed_limit_seconds=180, command=row['command'], cwd=row['cwd']))+'\n')

            attempt = dict(row, terminal=False, resource_receipt=str(receipt))
            result['attempts'].append(attempt)
            save()
            started = time.monotonic()
            with stdout.open('wb') as out, stderr.open('wb') as err:
                native = subprocess.Popen(row['command'], cwd=row['cwd'], stdout=out, stderr=err,
                                          start_new_session=True, preexec_fn=limits)
                attempt['pid'] = native.pid
                save()
                try:
                    code = native.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    # Only the new process group owned by this invocation.
                    try:
                        os.killpg(native.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    native.wait(timeout=5)
                    code = 'TIMEOUT_PARTIALS_RETAINED'
            attempt.update(terminal=True, returncode=code, elapsed_seconds=time.monotonic()-started)
            save()
            actual = json.loads(checked(receipt))
            if (code != 0 or actual['pid'] != native.pid or actual['pgid'] != native.pid
                    or actual['cpu'] != [120, 120] or actual['address_space'] != [4 * 1024**3] * 2
                    or actual['affinity'] != [31] or actual['nice'] != 15
                    or actual['command'] != row['command'] or actual['cwd'] != row['cwd']):
                raise ValueError('compiler/resource failure; no following stage')
            if row['label'] == 'host':
                depfile = (WORK/'continuation_pixel_pt.d').read_text().replace('\\\n', ' ')
                for name in shlex.split(depfile.split(':', 1)[1]):
                    p = Path(name)
                    checked(p if p.is_absolute() else BUILD/p)
            produced = dict(shader=WORK/'shaders/n010_pixel_pt.spv',
                            host=WORK/'continuation_pixel_pt.o',
                            link=WORK/'phos-n010-continuation-pixel-pt')[row['label']]
            raw = checked(produced)
            expected_magic = b'\x03\x02\x23\x07' if row['label'] == 'shader' else b'\x7fELF'
            if not raw.startswith(expected_magic):
                raise ValueError('compiler output format differs')
            if row['label'] == 'link' and not os.access(produced, os.X_OK):
                raise ValueError('private linked output is not executable')
            if str(Path(row['command'][0]).resolve()) != row['compiler_realpath']:
                raise ValueError('active compiler symlink changed during native stage')
            unchanged()
        result.update(build_valid=True, all_pass=True,
                      classification='ISOLATED_BUILD_COMPLETE_RUNTIME_NOT_RUN')
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as error:
        result.update(failure=str(error), classification='ISOLATED_BUILD_FAILURE_PARTIALS_RETAINED')
    result['payload_sha256'] = {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in WORK.rglob('*') if p.is_file()}
    result['complete'] = True
    save()
    print(result['classification'])
    return 0 if result['build_valid'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

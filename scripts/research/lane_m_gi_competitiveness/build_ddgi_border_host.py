#!/usr/bin/env python3
"""011 private CPU build from reversible host overlays; never initialize Vulkan."""
import argparse
import json
import resource
import shlex
import subprocess
from pathlib import Path

import build_ddgi_transition_host as B
import ddgi_border_overlay as O

ROOT = B.ROOT
PROTOCOL = ROOT / 'research/lanes/lane-m-gi-competitiveness/experiments/011-ddgi-separated-border-requalification.md'


def run(work):
    if work.exists() or not work.is_relative_to(ROOT / 'out'):
        raise ValueError('New repository/out host evidence required; no overwrite')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tracked = [B.HOST, B.STATIC_HOST, B.TRANSITION_CONTRACT, B.CONTRACT, B.CONTRACT_TEST,
               Path(__file__).resolve(), Path(O.__file__).resolve(), PROTOCOL]
    for p in tracked:
        if subprocess.check_output(['git', 'show', commit + ':' + str(p.relative_to(ROOT))], cwd=ROOT) != p.read_bytes():
            raise ValueError('Commit011 builder/source/protocol before build')
    manifest_path = ROOT / 'research/lanes/n010-comparison-readiness/results/021-ddgi-source-provenance.json'
    if B.sha(manifest_path) != '632c24a7cc5863e97bde595ab937fd15d232e680ce85c7c470bff6bd6bb7c7b3':
        raise ValueError('Historical SDK provenance differs')
    import compile_ddgi_scene as S
    manifest = json.loads(manifest_path.read_text())
    S.C.check_files(B.SDK, manifest['source_files'])
    if B.sha(B.LIB) != '39c606e0d117f9afa0c1f3558b36277aa593b002c19a9b5e7d8faf7f805d9123':
        raise ValueError('Original SDK static archive differs')
    original = B.command_rows()
    compile_args, link = original['host'], original['link']
    old_main = compile_args[compile_args.index('-o') + 1]
    old_context = [x for x in link if x.endswith('/generated/n010_b002_vulkan.cpp.o')]
    if len(old_context) != 1:
        raise ValueError('Exactly one original Vulkan context required')
    inputs = {str(p): B.sha(p) for p in tracked + [B.CONTEXT, manifest_path, B.LIB, B.LOADER, Path(B.__file__).resolve()]}
    for obj in [x for x in link if x.endswith(('.o', '.a'))]:
        p = Path(obj) if Path(obj).is_absolute() else B.BUILD / obj
        inputs[str(p)] = B.sha(p)
        if obj.endswith('.o'):
            deps = subprocess.check_output(['ninja', '-C', str(B.BUILD), '-t', 'deps', obj], text=True)
            paths = [Path(x.strip()) for x in deps.splitlines() if x.startswith('    ')]
            if not paths:
                raise ValueError('Original object dependencies unavailable')
            for p in paths:
                p = p if p.is_absolute() else B.BUILD / p
                inputs[str(p)] = B.sha(p)
    compiler = Path(compile_args[0]).resolve()
    inputs[str(compiler)] = B.sha(compiler)
    for p, h in manifest['source_files'].items():
        inputs[str(B.SDK / p)] = h
    snapshots = {p.name: O.host(p.read_bytes(), p.name) for p in (B.HOST, B.STATIC_HOST)}
    work.mkdir(parents=True)
    for p in (B.HOST, B.STATIC_HOST):
        (work / p.name).write_bytes(snapshots[p.name])
    for p in (B.TRANSITION_CONTRACT, B.CONTRACT, B.CONTRACT_TEST):
        (work / p.name).write_bytes(p.read_bytes())
    (work / 'm001_b002_vulkan.cpp').write_text(B.image_feature_overlay(B.CONTEXT.read_text()))
    flags = ['-DRTXGI_COORDINATE_SYSTEM=2', '-DRTXGI_DDGI_RESOURCE_MANAGEMENT=0', '-DRTXGI_DDGI_USE_SHADER_CONFIG_FILE=0', '-DRTXGI_GFX_NAME_OBJECTS',
             '-I' + str(B.SDK / 'rtxgi-sdk/include'), '-I/nix/store/1rhchilgcirwrwmq4h8xqldkn8lx209x-libx11-1.8.13-dev/include',
             '-I/nix/store/h11h9pq0d23c8n2k0pd162mgzg1z4jca-xorgproto-2025.1/include']
    jobs = []
    for label, source in [('host', work / B.HOST.name), ('context', work / 'm001_b002_vulkan.cpp')]:
        args = list(compile_args)
        for flag, value in [('-c', source), ('-o', work / (label + '.o')), ('-MT', work / (label + '.o')), ('-MF', work / (label + '.d'))]:
            args[args.index(flag) + 1] = str(value)
        jobs.append((label, args + flags, B.BUILD))
    link = [str(work / 'host.o') if x == old_main else str(work / 'context.o') if x == old_context[0] else
            '-Wl,--dependency-file=' + str(work / 'link.d') if x.startswith('-Wl,--dependency-file=') else x for x in link]
    link[link.index('-o') + 1] = str(work / 'm001-ddgi-border-transition')
    link += [str(B.LIB), str(B.LOADER), '-pthread']
    jobs.append(('link', link, B.BUILD))
    jobs.append(('contract-test-build', [str(compiler), '-std=c++20', '-O2', '-g', '-fsanitize=undefined', str(work / B.CONTRACT_TEST.name), '-o', str(work / 'ddgi-contract-test')], ROOT))
    jobs.append(('contract-test-run', [str(work / 'ddgi-contract-test')], ROOT))
    report = dict(schema='m001-ddgi-separated-border-host-cpu-build/1', source_commit=commit, gpu_executed=False,
                  host_vulkan_executed=False, inverse_host_overlays_exact=True, private_context_overlay_inverse_exact=True,
                  input_sha256=inputs, generated_host_sha256={n: O.digest(raw) for n, raw in snapshots.items()}, rows=[],
                  scope='CPU compile/link and UBSan contract test only; Vulkan runtime/quality NOT_RUN')
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
        resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    for label, cmd, cwd in jobs:
        row = dict(label=label, command=cmd, cwd=str(cwd), pass_=False)
        try:
            p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=180, preexec_fn=limits)
            row.update(returncode=p.returncode, pass_=p.returncode == 0)
            (work / (label + '.stdout.txt')).write_text(p.stdout)
            (work / (label + '.stderr.txt')).write_text(p.stderr)
        except subprocess.TimeoutExpired as error:
            row['error'] = str(error)
            for kind, raw in [('stdout', error.stdout), ('stderr', error.stderr)]:
                (work / (label + '.' + kind + '.txt')).write_bytes(raw if isinstance(raw, bytes) else (raw or '').encode())
        row['pass'] = row.pop('pass_')
        report['rows'].append(row)
        print(label, row.get('returncode'), row['pass'], flush=True)
        if not row['pass']:
            break
    for label in ('host', 'context'):
        dep = work / (label + '.d')
        if dep.exists():
            words = shlex.split(dep.read_text().replace('\\\n', ' '))
            for word in words[1:]:
                p = Path(word)
                p = p if p.is_absolute() else B.BUILD / p
                if p.is_file():
                    report.setdefault('compiled_dependency_sha256', {})[str(p)] = B.sha(p)
    if any(B.sha(p) != h for p, h in inputs.items()):
        raise ValueError('CPU build input drift')
    report.update(complete=True, all_pass=len(report['rows']) == 5 and all(r['pass'] for r in report['rows']),
                  payload_sha256={str(p.relative_to(work)): B.sha(p) for p in sorted(work.rglob('*')) if p.is_file()})
    with (work / 'result.json').open('x') as f:
        json.dump(report, f, indent=2)
        f.write('\n')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    a = ap.parse_args()
    result = run(a.work.resolve())
    raise SystemExit(0 if result['all_pass'] else 1)

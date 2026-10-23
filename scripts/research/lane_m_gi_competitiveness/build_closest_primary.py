#!/usr/bin/env python3
"""013 CPU-only isolated rebuild. Never invoke Vulkan or mutate original outputs."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess

import closest_primary as C

ROOT = C.ROOT
PROTOCOL = ROOT / 'research/lanes/lane-m-gi-competitiveness/experiments/013-closest-primary-development-validation.md'
BUILD = ROOT / 'build/n009'
COMPILER = BUILD / '_deps/glslang-build/StandAlone/glslang'
VALIDATOR = Path('/nix/store/z5hs3p3inrq3w8cv71jycz7l4y3ny5xk-spirv-tools-1.4.363.0/bin/spirv-val')


def compile_command(entry, output, depfile, shaders):
    args = shlex.split(entry['command'])
    result = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ('-o', '-MF', '-MT'):
            value = {'-o': output, '-MF': depfile, '-MT': output}[arg]
            result.extend((arg, str(value)))
            i += 2
            continue
        for macro in ('PHOS_GI_INTEGRATION_SHADER_DIR', 'PHOS_GI_LANE_A_SHADER_DIR', 'PHOS_GI_LANE_B_SHADER_DIR'):
            if arg.startswith('-D' + macro + '='):
                arg = f'-D{macro}="{shaders}"'
        result.append(arg)
        i += 1
    if result.count('-o') != 1 or result.count('-MF') != 1 or result.count('-c') != 1:
        raise ValueError('Unexpected original compiler command')
    return result


def build(work):
    work = work.resolve()
    if work.exists() or not work.is_relative_to(ROOT / 'out'):
        raise ValueError('Use a new repository/out build root; no overwrite')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tracked = [Path(__file__).resolve(), Path(C.__file__).resolve(), PROTOCOL]
    for p in tracked:
        if subprocess.check_output(['git', 'show', commit + ':' + str(p.relative_to(ROOT))], cwd=ROOT) != p.read_bytes():
            raise ValueError('Commit builder/overlay/protocol before executing')
    original_binary = BUILD / 'phos-n010-capture'
    if C.sha(original_binary) != 'cc6d7802a45d68d5074a13bbdd5c2cc94310d2f7fa5c303ee890508dae7535ab':
        raise ValueError('Original fixed RC binary changed')
    diag = ROOT / 'research/lanes/n010-comparison-readiness/results/054-primary-tie-cpu-diagnostic.json'
    if json.loads(diag.read_text())['primary_shader_source_sha256'] != C.PINS:
        raise ValueError('Historical primary pins differ')
    entries = json.loads(subprocess.check_output(
        ['ninja', '-C', str(BUILD), '-t', 'compdb', 'CXX_COMPILER__phos-n010-capture_unscanned_Release'], text=True))
    if len(entries) != 13 or len({x['file'] for x in entries}) != 13:
        raise ValueError('Expected all thirteen original capture translation units')
    libraries = [BUILD / '_deps/vk_bootstrap-build/libvk-bootstrap.a', BUILD / '_deps/fastgltf-build/libfastgltf.a']
    originals = sorted((BUILD / 'shaders').glob('*.spv'))
    frozen_plan = ROOT / 'out/m001-h01-fixed-vanilla-plan.json'
    started = ROOT / 'out/research/lane-m-gi-competitiveness/fixed-controls/H01-vanilla/started.json'
    if C.sha(frozen_plan) != json.loads(started.read_text())['plan_sha256']:
        raise ValueError('Frozen original control plan identity differs')
    expected_shaders = {p: h for p, h in json.loads(frozen_plan.read_text())['input_sha256'].items()
                        if Path(p).suffix == '.spv'}
    if {str(p): C.sha(p) for p in originals} != expected_shaders:
        raise ValueError('Original shader tree differs from frozen control manifest')
    paths = tracked + [diag, original_binary, COMPILER, VALIDATOR, BUILD / 'build.ninja', frozen_plan, started] + libraries + originals
    paths += [Path(x['file']) for x in entries] + [C.SOURCE / name for name in C.PINS]
    inputs = {str(p): C.sha(p) for p in paths}
    for name, pin in C.PINS.items():
        if inputs[str(C.SOURCE / name)] != pin:
            raise ValueError('Original primary source pin differs')
    work.mkdir(parents=True)
    shaders = work / 'shaders'
    shaders.mkdir()
    objects = work / 'objects'
    objects.mkdir()
    report = dict(schema='m001-closest-primary-cpu-build/1', source_commit=commit,
                  complete=False, gpu_executed=False, input_sha256=inputs, rows=[],
                  original_compile_database=entries, runtime_admitted=False,
                  scope='CPU private shader compilation/SPIR-V validation/13-TU rebuild only')
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = env.get('NIX_LD_LIBRARY_PATH', env.get('LD_LIBRARY_PATH', ''))

    def run(label, cmd, cwd=ROOT):
        row = dict(label=label, command=cmd, cwd=str(cwd), complete=False)
        report['rows'].append(row)
        try:
            p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
            row.update(returncode=p.returncode, stdout=p.stdout, stderr=p.stderr, complete=True)
            if p.returncode != 0:
                raise ValueError('CPU build command failed: ' + label)
            return p.stdout
        except Exception as exc:
            row['error'] = repr(exc)
            raise

    try:
        for p in originals:
            if p.name not in ('n001_primary.spv', 'n003_primary_software.spv'):
                (shaders / p.name).write_bytes(p.read_bytes())
        for name in C.PINS:
            source = shaders / name
            source.write_bytes(C.overlay((C.SOURCE / name).read_bytes()))
            target = shaders / name.replace('.comp.glsl', '.spv')
            run('compile-' + name, [str(COMPILER), '-V', '--target-env', 'vulkan1.3', '-S', 'comp', str(source), '-o', str(target)])
            run('validate-' + name, [str(VALIDATOR), '--target-env', 'vulkan1.3', str(target)])
        compiled = []
        dependencies = set()
        for index, entry in enumerate(entries):
            output = objects / f'{index:02d}.o'
            depfile = objects / f'{index:02d}.d'
            command = compile_command(entry, output, depfile, shaders)
            run('compile-host-' + str(index), command, Path(entry['directory']))
            compiled.append(output)
            text = depfile.read_text().replace('\\\n', ' ')
            # This pinned build has no escaped spaces/colons in include paths.
            for token in shlex.split(text.split(':', 1)[1]):
                p = Path(token)
                dependencies.add(p if p.is_absolute() else Path(entry['directory']) / p)
        compiler = shlex.split(entries[0]['command'])[0]
        binary = work / 'm001-closest-primary-capture'
        run('link-private-host', [compiler, '-O3', '-DNDEBUG', *map(str, compiled), *map(str, libraries), '-ldl', '-o', str(binary)])
        run('host-compiler-version', [compiler, '--version'])
        report['dependency_sha256'] = {str(p): C.sha(p) for p in sorted(dependencies)}
        if not all(C.sha(Path(p)) == h for p, h in inputs.items()):
            raise ValueError('Original build input changed during private rebuild')
        tree = {p.name: C.sha(p) for p in shaders.glob('*.spv')}
        changed = [p.name for p in originals if tree[p.name] != inputs[str(p)]]
        if sorted(changed) != ['n001_primary.spv', 'n003_primary_software.spv'] or len(tree) != len(originals):
            raise ValueError('Unexpected original/private shader-tree difference')
        report.update(complete=True, executable=str(binary), executable_sha256=C.sha(binary),
                      private_shader_sha256=tree, changed_shader_names=changed,
                      original_inputs_unchanged=True, inverse_source_overlays_exact=True,
                      host_translation_units_recompiled=13, original_objects_reused=False,
                      default_cmake_graph_changed=False)
    except Exception as exc:
        report['error'] = repr(exc)
    finally:
        with (work / 'result.json').open('x') as f:
            json.dump(report, f, indent=2)
            f.write('\n')
    if not report['complete']:
        raise ValueError('Build failed; partial files/result retained: ' + report.get('error', 'unknown'))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = build(args.out)
    print(json.dumps({k: report[k] for k in ('complete', 'gpu_executed', 'executable_sha256', 'changed_shader_names', 'host_translation_units_recompiled')}, indent=2))

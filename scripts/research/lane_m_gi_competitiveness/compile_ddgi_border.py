#!/usr/bin/env python3
"""011 CPU-only modified-SDK interior + separated border shader compilation."""
import argparse
import json
import os
from pathlib import Path
import resource
import struct
import subprocess
import sys

import ddgi_border_overlay as O
import compile_ddgi_scene as S

ROOT, C = S.ROOT, S.C
PROTOCOL = ROOT / 'research/lanes/lane-m-gi-competitiveness/experiments/011-ddgi-separated-border-requalification.md'
BORDER = ROOT / 'shaders/research/lane_m_gi_competitiveness/m001_ddgi_border_copy.hlsl'
VALIDATOR = Path('/nix/store/z5hs3p3inrq3w8cv71jycz7l4y3ny5xk-spirv-tools-1.4.363.0/bin/spirv-val')


def local_size(path):
    raw = path.read_bytes()
    words = struct.unpack('<' + 'I' * (len(raw) // 4), raw)
    found = []
    i = 5
    while i < len(words):
        count, opcode = words[i] >> 16, words[i] & 65535
        if not count or i + count > len(words):
            raise ValueError('Malformed SPIR-V')
        if opcode == 16 and count == 6 and words[i + 2] == 17:
            found.append(list(words[i + 3:i + 6]))
        i += count
    if len(found) != 1:
        raise ValueError('Exactly one literal local size required')
    return found[0]


def run(work):
    if work.exists() or not work.is_relative_to(ROOT / 'out'):
        raise ValueError('New repository/out shader evidence required; no overwrite')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tracked = [Path(__file__).resolve(), Path(O.__file__).resolve(), BORDER, PROTOCOL]
    for p in tracked:
        if subprocess.check_output(['git', 'show', commit + ':' + str(p.relative_to(ROOT))], cwd=ROOT) != p.read_bytes():
            raise ValueError('Commit011 CPU source/protocol before execution')
    sm, cm = S.RESULTS / '021-ddgi-source-provenance.json', S.RESULTS / '034-dxc-cpu-compiler-provenance.json'
    if C.sha(sm) != '632c24a7cc5863e97bde595ab937fd15d232e680ce85c7c470bff6bd6bb7c7b3' or C.sha(cm) != '2b544a1c26f31f3c4675b8d8702ac9232d657be1bda0bdc3ac1131af92481197':
        raise ValueError('Historical SDK/compiler identity differs')
    sdk, compiler = json.loads(sm.read_text()), json.loads(cm.read_text())
    C.check_files(S.SDK, sdk['source_files'])
    C.check_files(S.PACKAGE, compiler['files'])
    old_receipt = S.RESULTS / '038-ddgi-shader-compilation.json'
    old = json.loads(old_receipt.read_text())
    if not old['all_pass'] or len(old['rows']) != 10:
        raise ValueError('Original ten shader pins unavailable')
    old_spvs = {}
    for row in old['rows']:
        p = Path(row['command'][row['command'].index('-Fo') + 1])
        if C.sha(p) != row['shader_sha256']:
            raise ValueError('Original shader pin differs')
        old_spvs[row['name']] = p
    original = S.SDK / 'rtxgi-sdk/shaders/ddgi/ProbeBlendingCS.hlsl'
    generated = O.interior_shader(original.read_bytes())
    inputs = {str(p): C.sha(p) for p in tracked + [original, sm, cm, old_receipt, VALIDATOR] + list(old_spvs.values())}
    for directory, manifest in ((S.SDK, sdk['source_files']), (S.PACKAGE, compiler['files'])):
        inputs.update({str(directory / p): h for p, h in manifest.items()})
    work.mkdir(parents=True)
    snapshot = work / 'ProbeBlendingInteriorCS.hlsl'
    snapshot.write_bytes(generated)
    (work / BORDER.name).write_bytes(BORDER.read_bytes())
    for name, path in old_spvs.items():
        if not name.startswith('blend-'):
            (work / path.name).write_bytes(path.read_bytes())
    jobs = []
    for row in old['rows']:
        if not row['name'].startswith('blend-'):
            continue
        cmd = list(row['command'])
        cmd[1] = str(snapshot)
        cmd[cmd.index('-Fo') + 1] = str(work / (row['name'] + '.spv'))
        n = row['defines']['RTXGI_DDGI_PROBE_NUM_TEXELS']
        jobs.append((row['name'], cmd, [n, n, 1], row['bindings']))
    for name, entry, n, binding in (('border-irradiance', 'CopyIrradianceBorder', 8, 2), ('border-distance', 'CopyDistanceBorder', 16, 3)):
        cmd = [str(S.PACKAGE / 'bin/dxc'), str(work / BORDER.name), '-E', entry, '-T', 'cs_6_6', '-spirv',
               '-fspv-target-env=vulkan1.2', '-D', '__spirv__', '-D', 'HLSL=1', '-D', 'RTXGI_COORDINATE_SYSTEM=2', '-Fo', str(work / (name + '.spv'))]
        jobs.append((name, cmd, [n, n, 1], [dict(name='Irradiance' if binding == 2 else 'Distance', binding=binding, set=0)]))
    report = dict(schema='m001-ddgi-separated-border-shader-cpu-compile/1', source_commit=commit, gpu_executed=False,
                  sdk_modified_derivative=True, original_sdk_unchanged=True, inverse_overlay_exact=generated.decode().replace(O.SDK_REPLACEMENT, O.SDK_TAIL).encode() == original.read_bytes(),
                  sdk_files_verified=len(sdk['source_files']), compiler_files_verified=len(compiler['files']), input_sha256=inputs, rows=[],
                  scope='CPU compilation/validation only; runtime/quality admission NOT_RUN')
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = ':'.join(filter(None, [str(S.PACKAGE / 'lib'), env.get('NIX_LD_LIBRARY_PATH'), env.get('LD_LIBRARY_PATH')]))
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
        resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    for name, cmd, size, bindings in jobs:
        row = dict(name=name, command=cmd, expected_local_size=size, expected_bindings=bindings, pass_=False)
        try:
            p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=180, preexec_fn=limits)
            row.update(returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
            if p.returncode == 0:
                target = work / (name + '.spv')
                row.update(shader_sha256=C.sha(target), reflection=C.spirv_metadata(target), local_size=local_size(target))
                v = subprocess.run([str(VALIDATOR), '--target-env', 'vulkan1.2', str(target)], env=env, capture_output=True, text=True, timeout=60)
                row.update(validation_returncode=v.returncode, validation_stdout=v.stdout, validation_stderr=v.stderr)
                # Names may be optimized; descriptor set/binding identities are normative.
                descriptor_ids = lambda bs: [(b['set'], b['binding']) for b in bs]
                row['pass_'] = v.returncode == 0 and row['local_size'] == size and descriptor_ids(row['reflection']['bindings']) == descriptor_ids(bindings)
        except subprocess.TimeoutExpired as error:
            row['error'] = str(error)
        row['pass'] = row.pop('pass_')
        report['rows'].append(row)
        print(name, row.get('returncode'), row['pass'], flush=True)
        if not row['pass']:
            break
    if any(C.sha(Path(p)) != h for p, h in inputs.items()):
        raise ValueError('CPU compile input drift')
    report.update(complete=True, all_pass=len(report['rows']) == 8 and all(r['pass'] for r in report['rows']),
                  payload_sha256={str(p.relative_to(work)): C.sha(p) for p in sorted(work.rglob('*')) if p.is_file()})
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

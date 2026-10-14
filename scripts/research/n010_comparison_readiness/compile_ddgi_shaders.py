#!/usr/bin/env python3
"""Compile pinned, unmodified RTXGI shaders to SPIR-V using pinned CPU DXC."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[3]
LANE = ROOT / 'research/lanes/n010-comparison-readiness'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check_files(root, manifest):
    for name, digest in manifest.items():
        if sha(root / name) != digest:
            raise ValueError('pinned dependency changed: ' + name)

def spirv_metadata(path):
    data = path.read_bytes()
    if len(data) % 4:
        raise ValueError('SPIR-V length')
    words = struct.unpack('<' + 'I' * (len(data) // 4), data)
    if len(words) < 5 or words[0] != 0x07230203:
        raise ValueError('SPIR-V header')
    names, bindings, sets = {}, {}, {}
    i = 5
    while i < len(words):
        count, opcode = words[i] >> 16, words[i] & 65535
        if count == 0 or i + count > len(words):
            raise ValueError('SPIR-V instruction length')
        operands = words[i+1:i+count]
        if opcode == 5:  # OpName
            raw = struct.pack('<' + 'I' * (len(operands)-1), *operands[1:])
            names[operands[0]] = raw.split(b'\0')[0].decode()
        if opcode == 71 and len(operands) == 3:  # OpDecorate
            if operands[1] == 33:
                bindings[operands[0]] = operands[2]
            elif operands[1] == 34:
                sets[operands[0]] = operands[2]
        i += count
    return {'version_word': words[1], 'bindings': [
        {'name': names.get(key, str(key)), 'binding': binding, 'set': sets.get(key)}
        for key, binding in sorted(bindings.items(), key=lambda pair: pair[1])]}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--dxc-package', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = json.loads((LANE/'results/021-ddgi-source-provenance.json').read_text())
    compiler = json.loads((LANE/'results/034-dxc-cpu-compiler-provenance.json').read_text())
    check_files(args.sdk, source['source_files'])
    check_files(args.dxc_package, compiler['files'])
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing shader acquisition')
    args.work.mkdir(parents=True)
    sdk = args.sdk.resolve() / 'rtxgi-sdk'
    dxc = args.dxc_package.resolve() / 'bin/dxc'
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = ':'.join(filter(None, [str(args.dxc_package.resolve()/'lib'),
                                    env.get('NIX_LD_LIBRARY_PATH'), env.get('LD_LIBRARY_PATH')]))
    common = {
        'HLSL': 1,
        'RTXGI_COORDINATE_SYSTEM': 2, 'RTXGI_DDGI_RESOURCE_MANAGEMENT': 0,
        'RTXGI_DDGI_SHADER_REFLECTION': 0, 'RTXGI_DDGI_BINDLESS_RESOURCES': 0,
        'RTXGI_DDGI_USE_SHADER_CONFIG_FILE': 0, 'RTXGI_PUSH_CONSTS_TYPE': 1,
        'VOLUME_CONSTS_REGISTER': 0, 'VOLUME_CONSTS_SPACE': 0,
        'RAY_DATA_REGISTER': 1, 'RAY_DATA_SPACE': 0, 'OUTPUT_SPACE': 0,
        'PROBE_DATA_REGISTER': 4, 'PROBE_DATA_SPACE': 0,
        'PROBE_VARIABILITY_REGISTER': 5, 'PROBE_VARIABILITY_SPACE': 0,
        'PROBE_VARIABILITY_AVERAGE_REGISTER': 6,
        'RTXGI_DDGI_DEBUG_PROBE_INDEXING': 0,
        'RTXGI_DDGI_DEBUG_OCTAHEDRAL_INDEXING': 0,
        'RTXGI_DDGI_DEBUG_BORDER_COPY_INDEXING': 0,
    }
    jobs = []
    for rays in (128, 256, 512):
        for radiance, texels, interior, binding in ((1, 8, 6, 2), (0, 16, 14, 3)):
            jobs.append((f'blend-{rays}-'+('irradiance' if radiance else 'distance'),
                'ProbeBlendingCS.hlsl', 'DDGIProbeBlendingCS', {
                    'OUTPUT_REGISTER': binding, 'RTXGI_DDGI_BLEND_RADIANCE': radiance,
                    'RTXGI_DDGI_PROBE_NUM_TEXELS': texels,
                    'RTXGI_DDGI_PROBE_NUM_INTERIOR_TEXELS': interior,
                    'RTXGI_DDGI_BLEND_SHARED_MEMORY': 1,
                    'RTXGI_DDGI_BLEND_RAYS_PER_PROBE': rays,
                    'RTXGI_DDGI_BLEND_SCROLL_SHARED_MEMORY': 0}))
    for name, file, entry in (
        ('relocation', 'ProbeRelocationCS.hlsl', 'DDGIProbeRelocationCS'),
        ('relocation-reset', 'ProbeRelocationCS.hlsl', 'DDGIProbeRelocationResetCS'),
        ('classification', 'ProbeClassificationCS.hlsl', 'DDGIProbeClassificationCS'),
        ('classification-reset', 'ProbeClassificationCS.hlsl', 'DDGIProbeClassificationResetCS')):
        jobs.append((name, file, entry, {}))
    result = {'schema': 'n010-ddgi-shader-compile/1', 'complete': False,
              'all_pass': False, 'gpu_run': False, 'cuda_used': False,
              'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'sdk_commit': source['commit'], 'source_manifest_sha256': sha(LANE/'results/021-ddgi-source-provenance.json'),
              'compiler_manifest_sha256': sha(LANE/'results/034-dxc-cpu-compiler-provenance.json'),
              'compiler_sha256': sha(dxc), 'rows': [],
              'acquisition_script_sha256': sha(Path(__file__)),
              'scope': 'CPU HLSL compilation only; no DDGI runtime or image-quality validation'}
    for name, file, entry, specific in jobs:
        output = (args.work / (name+'.spv')).resolve()
        defines = dict(common, **specific)
        cmd = [str(dxc), str(sdk/'shaders/ddgi'/file), '-E', entry, '-T', 'cs_6_6',
               '-spirv', '-D', '__spirv__', '-fspv-target-env=vulkan1.2',
               '-I', str(sdk/'shaders'), '-Fo', str(output)]
        for key, value in sorted(defines.items()):
            cmd.extend(['-D', f'{key}={value}'])
        run = subprocess.run(cmd, env=env, text=True, capture_output=True)
        row = {'name': name, 'command': cmd, 'defines': defines, 'returncode': run.returncode,
               'stdout': run.stdout, 'stderr': run.stderr}
        if run.returncode == 0:
            row.update(shader_sha256=sha(output), **spirv_metadata(output))
        result['rows'].append(row)
        args.output.write_text(json.dumps(result, indent=2)+'\n')
        print(name, run.returncode, flush=True)
    check_files(args.sdk, source['source_files'])
    check_files(args.dxc_package, compiler['files'])
    result.update(complete=True, all_pass=all(row['returncode']==0 for row in result['rows']))
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    raise SystemExit(0 if result['all_pass'] else 2)

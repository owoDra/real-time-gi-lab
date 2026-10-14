#!/usr/bin/env python3
"""Compile official SDK reduction kernels needed by unmanaged DDGI creation."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from compile_ddgi_shaders import ROOT, LANE, sha, check_files, spirv_metadata

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--dxc-package', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse overwriting an earlier shader acquisition')
    source_path = LANE/'results/021-ddgi-source-provenance.json'
    compiler_path = LANE/'results/034-dxc-cpu-compiler-provenance.json'
    blend_path = LANE/'results/038-ddgi-shader-compilation.json'
    source = json.loads(source_path.read_text())
    compiler = json.loads(compiler_path.read_text())
    blend = json.loads(blend_path.read_text())
    if not blend['complete'] or not blend['all_pass']:
        raise ValueError('baseline pinned shader compilation incomplete/failed')
    if blend['source_manifest_sha256'] != sha(source_path) or blend['compiler_manifest_sha256'] != sha(compiler_path):
        raise ValueError('baseline shader dependency identity mismatch')
    check_files(args.sdk, source['source_files'])
    check_files(args.dxc_package, compiler['files'])
    args.work.mkdir(parents=True)
    sdk = args.sdk.resolve()/'rtxgi-sdk'
    dxc = args.dxc_package.resolve()/'bin/dxc'
    defines = dict(blend['rows'][0]['defines'])
    # Shared configuration/registers are unchanged. Blending-only parameters
    # have no role in reduction and are omitted from this compiler invocation.
    defines = {k:v for k,v in defines.items() if k not in ('OUTPUT_REGISTER',)
               and not k.startswith('RTXGI_DDGI_BLEND_')}
    defines['RTXGI_DDGI_PROBE_NUM_INTERIOR_TEXELS'] = 6
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = ':'.join(filter(None, [str(args.dxc_package.resolve()/'lib'),
        env.get('NIX_LD_LIBRARY_PATH'), env.get('LD_LIBRARY_PATH')]))
    result = {'schema':'n010-ddgi-reduction-shader-compile/1', 'complete':False,
              'all_pass':False, 'gpu_run':False, 'cuda_used':False,
              'source_commit':subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
              'sdk_commit':source['commit'], 'source_manifest_sha256':sha(source_path),
              'compiler_manifest_sha256':sha(compiler_path), 'compiler_sha256':sha(dxc),
              'baseline_shader_compilation_sha256':sha(blend_path),
              'script_sha256':sha(Path(__file__)), 'rows':[],
              'scope':'CPU compilation only. Unmanaged SDK requires reduction modules/pipelines even when variability is disabled. Runtime must select a shader consistent with its supported subgroup width; no AMD runtime or GI quality claim.'}
    for wave in (32,64):
        for name, entry in (('reduction','DDGIReductionCS'), ('extra-reduction','DDGIExtraReductionCS')):
            specific = dict(defines, RTXGI_DDGI_WAVE_LANE_COUNT=wave)
            output = (args.work/f'{name}-wave{wave}.spv').resolve()
            command = [str(dxc), str(sdk/'shaders/ddgi/ReductionCS.hlsl'), '-E', entry,
                '-T','cs_6_6','-spirv','-D','__spirv__','-fspv-target-env=vulkan1.2',
                '-I',str(sdk/'shaders'),'-Fo',str(output)]
            for key, value in sorted(specific.items()):
                command += ['-D',f'{key}={value}']
            process = subprocess.run(command, env=env, text=True, capture_output=True)
            row = {'name':f'{name}-wave{wave}', 'entry':entry, 'wave_lane_count':wave,
                   'command':command, 'defines':specific, 'returncode':process.returncode,
                   'stdout':process.stdout, 'stderr':process.stderr}
            if process.returncode == 0:
                row.update(shader_sha256=sha(output), **spirv_metadata(output))
            result['rows'].append(row)
            args.output.write_text(json.dumps(result,indent=2)+'\n')
            print(row['name'],row['returncode'],flush=True)
    check_files(args.sdk, source['source_files'])
    check_files(args.dxc_package, compiler['files'])
    result.update(complete=True, all_pass=all(row['returncode']==0 for row in result['rows']))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    raise SystemExit(0 if result['all_pass'] else 2)

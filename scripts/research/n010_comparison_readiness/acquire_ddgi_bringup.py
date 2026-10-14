#!/usr/bin/env python3
"""Retain one preregistered official-SDK constant-field GPU diagnostic."""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
from compile_ddgi_shaders import ROOT, LANE, sha, check_files
from readiness_preflight import replay

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--shaders',type=Path,required=True)
    parser.add_argument('--reduction',type=Path,required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing GPU diagnostic acquisition')
    if not args.binary.name.startswith('phos-'):
        raise ValueError('GPU executable needs phos- process identity for the completion driver')
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():continue
        try:name=(process/'comm').read_text().strip()
        except OSError:continue
        if name.startswith('phos-'):raise ValueError('another GPU image producer is active')
    source_path=LANE/'results/021-ddgi-source-provenance.json'
    source=json.loads(source_path.read_text())
    sdk=ROOT/'out/research/n010-comparison-readiness/external/RTXGI-DDGI'
    check_files(sdk,source['source_files'])
    manifests=[LANE/'results'/name for name in ('038-ddgi-shader-compilation.json','056-ddgi-reduction-shader-compilation.json')]
    identities={str(path):sha(path) for path in manifests+[source_path,args.binary,
        ROOT/'src/research/n010_comparison_readiness/ddgi_volume_bringup.cpp',
        LANE/'experiments/015-ddgi-volume-runtime-bringup.md',
        ROOT/'build/n010-ddgi-sdk/lib/librtxgi-vulkan.a',Path(__file__)]}
    for path,directory in zip(manifests,(args.shaders,args.reduction)):
        data=json.loads(path.read_text())
        if not data['complete'] or not data['all_pass'] or data['source_manifest_sha256']!=sha(source_path):
            raise ValueError('shader provenance incomplete/failed/mismatched')
        for row in data['rows']:
            shader=directory/(row['name']+'.spv')
            if sha(shader)!=row['shader_sha256']:raise ValueError('pinned shader changed')
            identities[str(shader)]=sha(shader)
    args.work.mkdir(parents=True)
    command=['bash','scripts/run_with_vulkan.sh',str(args.binary.resolve()),
             str(args.shaders.resolve()),str(args.reduction.resolve()),str((args.work/'gpu').resolve())]
    result={'schema':'n010-ddgi-volume-bringup/1','complete':False,'all_pass':False,
            'gpu_run':True,'cuda_used':False,'command':command,'input_sha256':identities,
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'scope':'SDK volume resource/constant-field dispatch diagnostic only. No scene ray tracing, finite-depth GI, surface gather, temporal qualification or performance comparison.',
            'thresholds':{'irradiance_max_abs_error':1e-5,'distance_max_abs_error':1e-5},
            'scoring_exclusions':0,'rows':[]}
    (args.work/'attempt.json').write_text(json.dumps(result,indent=2)+'\n')
    process=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    (args.work/'stdout.log').write_text(process.stdout)
    (args.work/'stderr.log').write_text(process.stderr)
    result.update(returncode=process.returncode,stdout=process.stdout,stderr=process.stderr)
    measurements=args.work/'gpu/measurements.json'
    if measurements.exists():
        result['measurements']=json.loads(measurements.read_text())
        images=result['measurements']['image_layouts']
        for control in (0,1):
            row={'radiance':control,'all_finite':True}
            for image_type,key,channels,expected in ((1,'irradiance',4,0.5*control),(2,'distance',2,0.5)):
                image=images[image_type]
                raw=args.work/'gpu'/f'control{control}.{key}.f32'
                values=np.frombuffer(raw.read_bytes(),dtype='<f4')
                size=image['width']*image['height']*image['layers']*channels
                if values.size!=size:raise ValueError('unexpected GPU readback shape')
                values=values.reshape(-1,channels)
                row['all_finite'] &= bool(np.isfinite(values).all())
                # Recompute directly from every retained float; no masks/border omissions.
                selected=values[:,:3] if image_type==1 else values
                row[key+'_max_abs_error']=float(np.max(np.abs(selected.astype(np.float64)-expected))) if np.isfinite(selected).all() else None
                row[key+'_scored_texels']=len(values)
            row['pass']=row['all_finite'] and row['irradiance_max_abs_error']<=1e-5 and row['distance_max_abs_error']<=1e-5
            result['rows'].append(row)
    memory_path=args.work/'gpu/allocation-ledger.json'
    if memory_path.exists():
        result['allocation_ledger']=json.loads(memory_path.read_text())
        result['independent_memory_replay_pass']=replay(result['allocation_ledger'])
    check_files(sdk,source['source_files'])
    if any(sha(Path(path))!=digest for path,digest in identities.items()):raise ValueError('frozen diagnostic dependency changed')
    result.update(complete=True,all_pass=process.returncode==0 and len(result['rows'])==2
                  and all(row['pass'] for row in result['rows']) and result.get('independent_memory_replay_pass',False),
                  payload_sha256={str(path.relative_to(args.work)):sha(path) for path in sorted(args.work.rglob('*')) if path.is_file()})
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('PASS' if result['all_pass'] else 'FAIL')
    raise SystemExit(0 if result['all_pass'] else 2)

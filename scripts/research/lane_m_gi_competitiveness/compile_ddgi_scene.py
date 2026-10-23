#!/usr/bin/env python3
"""CPU compile only: pinned SDK + isolated scene HLSL; never initialize Vulkan."""
import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts/research/n010_comparison_readiness'))
import compile_ddgi_shaders as C

SOURCE=ROOT/'shaders/research/lane_m_gi_competitiveness/m001_ddgi_scene.hlsl'
SDK=ROOT/'out/research/n010-comparison-readiness/external/RTXGI-DDGI'
PACKAGE=ROOT/'out/research/n010-comparison-readiness/external/dxc-v1.7.2308/package'
RESULTS=ROOT/'research/lanes/n010-comparison-readiness/results'


def run(work):
    if work.exists(): raise ValueError('refuse existing CPU compilation evidence')
    sm=RESULTS/'021-ddgi-source-provenance.json';cm=RESULTS/'034-dxc-cpu-compiler-provenance.json'
    if C.sha(sm)!='632c24a7cc5863e97bde595ab937fd15d232e680ce85c7c470bff6bd6bb7c7b3' or C.sha(cm)!='2b544a1c26f31f3c4675b8d8702ac9232d657be1bda0bdc3ac1131af92481197':
        raise ValueError('historical SDK/compiler provenance changed')
    source=json.loads(sm.read_text());compiler=json.loads(cm.read_text())
    C.check_files(SDK,source['source_files']);C.check_files(PACKAGE,compiler['files'])
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for path in (SOURCE,Path(__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():
            raise ValueError('commit shader and CPU driver before compiling')
    validator=shutil.which('spirv-val')
    if not validator: raise ValueError('SPIR-V CPU validator unavailable')
    work.mkdir(parents=True)
    snapshot=work/'m001_ddgi_scene.hlsl';snapshot.write_bytes(SOURCE.read_bytes())
    env=dict(os.environ);env['LD_LIBRARY_PATH']=':'.join(filter(None,[str(PACKAGE/'lib'),env.get('NIX_LD_LIBRARY_PATH'),env.get('LD_LIBRARY_PATH')]))
    definitions={'HLSL':1,'RTXGI_COORDINATE_SYSTEM':2,'RTXGI_DDGI_USE_SHADER_CONFIG_FILE':0,
                 'RTXGI_DDGI_BINDLESS_RESOURCES':0,'RTXGI_DDGI_RESOURCE_MANAGEMENT':0,'RTXGI_DDGI_SHADER_REFLECTION':0}
    d={'schema':'lane-m-m001-ddgi-scene-cpu-compile/1','source_commit':commit,'gpu_executed':False,
       'complete':False,'all_pass':False,'scope':'CPU HLSL compilation/validation only; host, semantic/runtime/physical/finite-depth/history/memory admission NOT RUN',
       'input_sha256':{str(p):C.sha(p) for p in (SOURCE,Path(__file__).resolve(),sm,cm,PACKAGE/'bin/dxc',Path(validator))},
       'sdk_files_verified':len(source['source_files']),'compiler_files_verified':len(compiler['files']),'rows':[]}
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    for entry in ('TraceProbes','GatherPixels'):
        target=work/(entry+'.spv')
        cmd=[str(PACKAGE/'bin/dxc'),str(snapshot),'-E',entry,'-T','cs_6_6','-spirv',
             '-fspv-target-env=vulkan1.2','-fspv-extension=SPV_KHR_ray_query','-I',str(SDK/'rtxgi-sdk/shaders'),'-Fo',str(target)]
        for key,value in definitions.items():cmd+=['-D',f'{key}={value}']
        row={'entry':entry,'command':cmd,'definitions':definitions,'pass':False}
        try:
            p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=180,preexec_fn=limits)
            (work/(entry+'.stdout.txt')).write_text(p.stdout);(work/(entry+'.stderr.txt')).write_text(p.stderr)
            row['returncode']=p.returncode
            if p.returncode==0:
                row.update(shader_sha256=C.sha(target),reflection=C.spirv_metadata(target))
                v=subprocess.run([validator,'--target-env','vulkan1.2',str(target)],env=env,capture_output=True,text=True,timeout=60)
                row.update(validation_returncode=v.returncode,validation_stdout=v.stdout,validation_stderr=v.stderr,pass_=v.returncode==0)
                row['pass']=row.pop('pass_')
        except subprocess.TimeoutExpired as error:
            row['error']='CPU compiler/validator timeout retained: '+str(error)
        d['rows'].append(row)
        print(entry,row.get('returncode'),row['pass'],flush=True)
        if not row['pass']:break
    C.check_files(SDK,source['source_files']);C.check_files(PACKAGE,compiler['files'])
    if any(C.sha(Path(p))!=h for p,h in d['input_sha256'].items()): raise ValueError('CPU compile input drift')
    d.update(complete=True,all_pass=len(d['rows'])==2 and all(x['pass'] for x in d['rows']),
             payload_sha256={str(p.relative_to(work)):C.sha(p) for p in sorted(work.rglob('*')) if p.is_file()})
    with (work/'result.json').open('x') as f:f.write(json.dumps(d,indent=2)+'\n')
    return d

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);a=ap.parse_args()
    d=run(a.work.resolve());print(json.dumps({'all_pass':d['all_pass'],'gpu_executed':False,'work':str(a.work)},indent=2));sys.exit(0 if d['all_pass'] else 2)

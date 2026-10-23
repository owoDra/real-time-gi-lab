#!/usr/bin/env python3
"""Build a private standalone DDGI host on CPU; never execute that host or Vulkan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BUILD=ROOT/'build/n009'
HOST=ROOT/'src/research/lane_m_gi_competitiveness/ddgi_scene_main.cpp'
CONTRACT=HOST.with_name('ddgi_contract.hpp')
CONTRACT_TEST=HOST.with_name('ddgi_contract_test.cpp')
OLD=ROOT/'src/research/n010_comparison_readiness/pixel_pt_main.cpp'
CONTEXT=BUILD/'src/research/n010_comparison_readiness/generated/n010_b002_vulkan.cpp'
SDK=ROOT/'out/research/n010-comparison-readiness/external/RTXGI-DDGI'
LIB=ROOT/'build/n010-ddgi-sdk/lib/librtxgi-vulkan.a'
LOADER=Path('/run/current-system/sw/share/nix-ld/lib/libvulkan.so')


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def image_feature_overlay(source):
    needle='        .set_name(target_device);'
    if source.count(needle)!=1:raise ValueError('unique private context insertion required')
    addition='''

    // M001 private SDK adapter needs typed and untyped storage images.
    VkPhysicalDeviceFeatures sdk_features{};
    sdk_features.shaderStorageImageReadWithoutFormat = VK_TRUE;
    sdk_features.shaderStorageImageWriteWithoutFormat = VK_TRUE;
    sdk_features.shaderStorageImageExtendedFormats = VK_TRUE;
    selector.set_required_features(sdk_features);'''
    overlay=source.replace(needle,needle+addition)
    if overlay.replace(addition,'')!=source:raise ValueError('private context inverse mismatch')
    return overlay


def command_rows():
    raw=subprocess.check_output(['ninja','-C',str(BUILD),'-t','commands','phos-n010-pixel-pt'],text=True)
    rows=[]
    for line in raw.splitlines():
        a=shlex.split(line)
        if a[:2]==[':','&&'] and a[-2:]==['&&',':']:a=a[2:-2]
        if '-c' in a and Path(a[a.index('-c')+1])==OLD:rows.append(('host',a))
        if '-o' in a and a[a.index('-o')+1]=='phos-n010-pixel-pt':rows.append(('link',a))
    if [x[0] for x in rows]!=['host','link']:raise ValueError('unique original CPU build commands required')
    if any(x in ('&&',';','|') for _,a in rows for x in a):raise ValueError('shell command refused')
    return dict(rows)


def run(work):
    if work.exists():raise ValueError('refuse existing CPU build evidence')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for p in (HOST,CONTRACT,CONTRACT_TEST,Path(__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(p.relative_to(ROOT))],cwd=ROOT)!=p.read_bytes():
            raise ValueError('commit standalone host/contract/builder before build')
    source_manifest=ROOT/'research/lanes/n010-comparison-readiness/results/021-ddgi-source-provenance.json'
    if sha(source_manifest)!='632c24a7cc5863e97bde595ab937fd15d232e680ce85c7c470bff6bd6bb7c7b3':raise ValueError('SDK provenance differs')
    sys.path.insert(0,str(ROOT/'scripts/research/n010_comparison_readiness'));import compile_ddgi_shaders as C
    manifest=json.loads(source_manifest.read_text());C.check_files(SDK,manifest['source_files'])
    if sha(LIB)!='39c606e0d117f9afa0c1f3558b36277aa593b002c19a9b5e7d8faf7f805d9123':raise ValueError('SDK static archive differs')
    original=command_rows();compile_args=original['host'];old_main=compile_args[compile_args.index('-o')+1]
    link=original['link'];old_context=[x for x in link if x.endswith('/generated/n010_b002_vulkan.cpp.o')]
    if len(old_context)!=1:raise ValueError('one historical ledger context required')
    inputs={p:sha(p) for p in (HOST,CONTRACT,CONTRACT_TEST,CONTEXT,Path(__file__).resolve(),source_manifest,LIB,LOADER)}
    for obj in [x for x in link if x.endswith(('.o','.a'))]:
        p=Path(obj) if Path(obj).is_absolute() else BUILD/obj;inputs[p]=sha(p)
        if obj.endswith('.o'):
            raw=subprocess.check_output(['ninja','-C',str(BUILD),'-t','deps',obj],text=True)
            deps=[Path(x.strip()) for x in raw.splitlines() if x.startswith('    ')]
            if not deps:raise ValueError('original object dependencies unavailable')
            for p in deps:
                if not p.is_absolute():p=BUILD/p
                inputs[p]=sha(p)
    compiler=Path(compile_args[0]).resolve();inputs[compiler]=sha(compiler)
    work.mkdir(parents=True)
    (work/HOST.name).write_bytes(HOST.read_bytes());(work/CONTRACT.name).write_bytes(CONTRACT.read_bytes())
    (work/CONTRACT_TEST.name).write_bytes(CONTRACT_TEST.read_bytes())
    (work/'m001_b002_vulkan.cpp').write_text(image_feature_overlay(CONTEXT.read_text()))
    flags=['-DRTXGI_COORDINATE_SYSTEM=2','-DRTXGI_DDGI_RESOURCE_MANAGEMENT=0','-DRTXGI_DDGI_USE_SHADER_CONFIG_FILE=0','-DRTXGI_GFX_NAME_OBJECTS',
           '-I'+str(SDK/'rtxgi-sdk/include'),'-I/nix/store/1rhchilgcirwrwmq4h8xqldkn8lx209x-libx11-1.8.13-dev/include',
           '-I/nix/store/h11h9pq0d23c8n2k0pd162mgzg1z4jca-xorgproto-2025.1/include']
    rows=[]
    for label,source in [('host',work/HOST.name),('context',work/'m001_b002_vulkan.cpp')]:
        args=list(compile_args)
        for flag,value in [('-c',source),('-o',work/(label+'.o')),('-MT',work/(label+'.o')),('-MF',work/(label+'.d'))]:args[args.index(flag)+1]=str(value)
        rows.append((label,args+flags))
    link=[str(work/'host.o') if x==old_main else str(work/'context.o') if x==old_context[0] else
          '-Wl,--dependency-file='+str(work/'link.d') if x.startswith('-Wl,--dependency-file=') else x for x in link]
    link[link.index('-o')+1]=str(work/'m001-ddgi-scene');link += [str(LIB),str(LOADER),'-pthread']
    rows.append(('link',link))
    rows.append(('contract-test-build',[str(compiler),'-std=c++20','-O2','-g','-fsanitize=undefined',str(work/CONTRACT_TEST.name),'-o',str(work/'ddgi-contract-test')]))
    d={'schema':'m001-ddgi-private-host-build/1','source_commit':commit,'gpu_executed':False,'host_executed':False,
       'complete':False,'all_pass':False,'sdk_files_verified':len(manifest['source_files']),
       'private_context_overlay_inverse_exact':True,'scope':'CPU compile/link only; runtime semantics/quality NOT RUN',
       'input_sha256':{str(p):h for p,h in inputs.items()},'rows':[]}
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    for label,cmd in rows:
        row={'label':label,'command':cmd,'cwd':str(BUILD),'pass':False}
        try:
            p=subprocess.run(cmd,cwd=BUILD,capture_output=True,text=True,timeout=180,preexec_fn=limits)
            (work/(label+'.stdout.txt')).write_text(p.stdout);(work/(label+'.stderr.txt')).write_text(p.stderr)
            row.update(returncode=p.returncode,pass_=p.returncode==0);row['pass']=row.pop('pass_')
        except subprocess.TimeoutExpired as error:
            row['error']=str(error)
            for kind,raw in [('stdout',error.stdout),('stderr',error.stderr)]:
                (work/(label+'.'+kind+'.txt')).write_bytes(raw if isinstance(raw,bytes) else (raw or '').encode())
        d['rows'].append(row);print(label,row.get('returncode'),row['pass'],flush=True)
        if not row['pass']:break
    for label in ('host','context'):
        dep=work/(label+'.d')
        if dep.exists():
            words=shlex.split(dep.read_text().replace('\\\n',' '));
            for word in words[1:]:
                p=Path(word);p=p if p.is_absolute() else BUILD/p
                if p.is_file():d.setdefault('compiled_dependency_sha256',{})[str(p)]=sha(p)
    C.check_files(SDK,manifest['source_files'])
    if any(sha(p)!=h for p,h in inputs.items()):raise ValueError('input changed during CPU build')
    d.update(complete=True,all_pass=len(d['rows'])==4 and all(x['pass'] for x in d['rows']),
             payload_sha256={str(p.relative_to(work)):sha(p) for p in sorted(work.rglob('*')) if p.is_file()})
    with (work/'result.json').open('x') as f:f.write(json.dumps(d,indent=2)+'\n')
    return d

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);a=ap.parse_args()
    work=a.work.resolve()
    if not work.is_relative_to(ROOT/'out'):raise ValueError('CPU build evidence must be under repository out/')
    d=run(work);print(json.dumps({'all_pass':d['all_pass'],'work':str(work),'gpu_executed':False}));sys.exit(0 if d['all_pass'] else 2)

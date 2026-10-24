#!/usr/bin/env python3
"""028 compile private host/API objects only; reuse025 SDK and all shaders."""
import argparse
from pathlib import Path
import shlex
import subprocess
import sys
import nrd_quality_build as Q
import nrd_no_prepass_overlay as O

ROOT=Q.ROOT;BASE=Q.BASE;SHA=Q.SHA;read=Q.read;need=Q.need;rehash=Q.rehash;inventory=Q.inventory;write=Q.write
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/028-nrd-diffuse-no-prepass-cold-warm-quality.md'
OWN=[PROTOCOL]+[Path(__file__).with_name(n) for n in ('nrd_no_prepass_build.py','nrd_no_prepass_overlay.py','nrd_no_prepass_process.py','nrd_no_prepass_audit.py','test_nrd_no_prepass.py')]
PARENT=BASE/'m001-nrd026-cpu-build-v1'
SDK=Q.S.SDK

def committed():
    head=Q.committed()
    for p in OWN:need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'028 commit all code/tests/protocol before execution')
    subprocess.run(['git','merge-base','--is-ancestor','892708b3',head],cwd=ROOT,check=True)
    return head

def run(work):
    head=committed();work=work.resolve();need(work.is_relative_to(BASE) and not work.exists(),'028 exclusive build')
    pins={str(p):SHA(p) for p in OWN};parents={}
    for folder in (PARENT,Q.SKY,SDK):
        r=read(folder/'result.json');need(r['all_pass'],'028 qualified parent build')
        pins[str(folder/'result.json')]=SHA(folder/'result.json')
        for key in ('input_sha256','compiled_dependency_sha256'):rehash(r.get(key,{}));pins.update(r.get(key,{}))
        pins.update({str(folder/name):h for name,h in r['payload_sha256'].items()});parents[folder]=r
    rehash(pins);work.mkdir()
    host=Q.S.V.SRC/'nrd_vulkan_runtime.cpp';header=Q.S.V.SRC/'nrd_vulkan_contract.hpp';probe=Q.S.V.SRC/'nrd_api_probe.cpp'
    for p,fn in ((host,O.host),(header,O.header),(probe,O.probe)):(work/p.name).write_bytes(fn(p.read_bytes()))
    commands=[]
    for label,original,oldfolder,source in [('host',parents[PARENT]['rows'][0]['command'],PARENT,host),('api',next(x['command'] for x in parents[SDK]['rows'] if x['label']=='api-compile'),SDK,probe)]:
        cmd=list(original)
        for j,x in enumerate(cmd):
            if x=='-I'+str(oldfolder):cmd[j]='-I'+str(work)
        for flag,value in (('-c',work/source.name),('-o',work/(label+'.o')),('-MT',work/(label+'.o')),('-MF',work/(label+'.d'))):cmd[cmd.index(flag)+1]=str(value)
        commands.append((label+'-compile',cmd))
    library=Path(parents[PARENT]['sdk_library']);need(library==Q.SKY/'libNRD.a','028 SDK library identity')
    link=list(parents[PARENT]['rows'][1]['command'])
    link[link.index(str(PARENT/'host.o'))]=str(work/'host.o');link[link.index('-o')+1]=str(work/'nrd-vulkan')
    for j,x in enumerate(link):
        if x.startswith('-Wl,--dependency-file='):link[j]='-Wl,--dependency-file='+str(work/'link.d')
    commands.append(('host-link',link))
    api=list(next(x['command'] for x in parents[SDK]['rows'] if x['label']=='api-link'))
    api[api.index(str(SDK/'api.o'))]=str(work/'api.o');api[api.index(str(SDK/'artifacts/libNRD.a'))]=str(library);api[api.index('-o')+1]=str(work/'nrd-api-probe');commands.append(('api-link',api))
    r=dict(schema='m001-nrd028-private-host-api-build/1',source_commit=head,complete=False,all_pass=False,gpu_executed=False,input_sha256=pins,compiled_dependency_sha256={},rows=[],executable=str(work/'nrd-vulkan'),api_executable=str(work/'nrd-api-probe'),sdk_library=str(library),shader_directory=parents[PARENT]['shader_directory'],sdk_shaders_other_objects_rebuilt=False,only_setting_changed={'diffusePrepassBlurRadius':[30,0]})
    try:
        for label,cmd in commands:
            row=Q.S.execute(label,cmd,work);r['rows'].append(row);need(row['pass_'],'028 build failure: '+label)
        for name in ('host','api'):
            for dep in shlex.split((work/(name+'.d')).read_text().replace('\\\n',' '))[1:]:
                p=Path(dep);p=p if p.is_absolute() else Q.S.V.B.D.BUILD/p
                if p.is_file():r['compiled_dependency_sha256'][str(p)]=SHA(p)
        need(str(work/header.name) in r['compiled_dependency_sha256'],'028 private header dependency')
        need(all(str(work/p.name) in r['compiled_dependency_sha256'] for p in (host,probe)),'028 private source dependencies');rehash(pins);r['all_pass']=True
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    r.update(complete=True,payload_sha256=inventory(work));write(work/'result.json',r);return r

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',required=True,type=Path);a=ap.parse_args();r=run(a.work);print({k:r.get(k) for k in ('all_pass','error')});sys.exit(0 if r['all_pass'] else 2)

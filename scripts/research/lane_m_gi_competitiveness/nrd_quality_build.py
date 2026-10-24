#!/usr/bin/env python3
"""026 compile one private host and relink; reuse SDK, objects and all shaders."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
import nrd_sky_build as S
import nrd_quality_overlay as O

ROOT=S.ROOT;BASE=S.BASE;SHA=S.SHA;read=S.read;need=S.need;rehash=S.rehash;inventory=S.inventory
OLD=BASE/'m001-nrd024-cpu-build-v1';SKY=BASE/'m001-nrd025-cpu-build-v2'
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/026-nrd-cold-and-64-frame-static-hdr-quality.md'
OWN=[PROTOCOL]+[Path(__file__).with_name(n) for n in ('nrd_quality_build.py','nrd_quality_overlay.py','nrd_quality_process.py','nrd_quality_audit.py','test_nrd_quality.py')]

def committed():
    head=S.committed()
    for p in OWN:need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))])==p.read_bytes(),'026 commit all source/test/process/audit before execution')
    return head

def write(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')

def run(work):
    head=committed();work=work.resolve();need(work.is_relative_to(BASE) and not work.exists(),'026 exclusive build output')
    original=read(OLD/'result.json');sky=read(SKY/'result.json');need(sky['all_pass'] and not sky['gpu_executed'],'026 qualified025 SDK required')
    pins={str(p):SHA(p) for p in OWN}
    for folder,r in ((OLD,original),(SKY,sky)):
        rehash(r['compiled_dependency_sha256']);pins.update(r['compiled_dependency_sha256']);pins[str(folder/'result.json')]=SHA(folder/'result.json')
        pins.update({str(folder/name):h for name,h in r['payload_sha256'].items()})
    rehash(pins);work.mkdir()
    host=S.V.SRC/'nrd_vulkan_runtime.cpp';header=S.V.SRC/'nrd_vulkan_contract.hpp';(work/host.name).write_bytes(O.host(host.read_bytes()));(work/header.name).write_bytes(O.header(header.read_bytes()))
    compile=list(original['rows'][0]['command'])
    for j,x in enumerate(compile):
        if x=='-I'+str(OLD):compile[j]='-I'+str(work)
    for flag,value in (('-c',work/host.name),('-o',work/'host.o'),('-MT',work/'host.o'),('-MF',work/'host.d')):compile[compile.index(flag)+1]=str(value)
    link=list(original['rows'][3]['command'])
    for j,x in enumerate(link):
        if x==str(OLD/'host.o'):link[j]=str(work/'host.o')
        elif x==str(S.SDK/'artifacts/libNRD.a'):link[j]=str(SKY/'libNRD.a')
        elif x.startswith('-Wl,--dependency-file='):link[j]='-Wl,--dependency-file='+str(work/'link.d')
    link[link.index('-o')+1]=str(work/'nrd-vulkan')
    r=dict(schema='m001-nrd026-private-quality-host-build/1',source_commit=head,complete=False,all_pass=False,gpu_executed=False,input_sha256=pins,compiled_dependency_sha256={},rows=[],executable=str(work/'nrd-vulkan'),shader_directory=str(S.NATIVE),sdk_library=str(SKY/'libNRD.a'),old_sdk_shaders_objects_rebuilt=False)
    try:
        for label,command in [('host-compile',compile),('host-link',link)]:
            row=S.execute(label,command,work);r['rows'].append(row);need(row['pass_'],'026 host build failed')
        for name in shlex.split((work/'host.d').read_text().replace('\\\n',' '))[1:]:
            p=Path(name);p=p if p.is_absolute() else S.V.B.D.BUILD/p
            if p.is_file():r['compiled_dependency_sha256'][str(p)]=SHA(p)
        need(str(work/header.name) in r['compiled_dependency_sha256'],'026 private header not compiled');rehash(pins);r['all_pass']=True
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    r.update(complete=True,payload_sha256=inventory(work));write(work/'result.json',r);return r

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();r=run(a.work);print(json.dumps({k:r.get(k) for k in ('all_pass','error')}));sys.exit(0 if r['all_pass'] else 2)

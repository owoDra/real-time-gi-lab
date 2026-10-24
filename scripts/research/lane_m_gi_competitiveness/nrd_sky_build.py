#!/usr/bin/env python3
"""025 isolated one-family SDK shader rebuild and unchanged-object relinks."""
import argparse
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import subprocess
import sys
import build_nrd_vulkan as V

ROOT=V.ROOT; BASE=V.BASE; SHA=V.SHA; read=V.read; need=V.need; rehash=V.rehash; inventory=V.inventory
SDK=V.SDK_BUILD; NATIVE=BASE/'m001-nrd024-cpu-build-v2'
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/025-nrd-sky-material-initialization-intervention.md'
OWN=[PROTOCOL]+[Path(__file__).with_name(n) for n in ('nrd_sky_build.py','test_nrd_sky.py','nrd_sky_process.py','nrd_sky_audit.py')]
OLD='float4 centerWorldPosMaterialID = s_WorldPos_MaterialID[sharedMemoryIndex.y][sharedMemoryIndex.x];'
NEW='float4 centerWorldPosMaterialID = isSky == 0.0 ? s_WorldPos_MaterialID[sharedMemoryIndex.y][sharedMemoryIndex.x] : float4(0.0, 0.0, 0.0, 0.0);'

def patch(data):
    need(data.count(OLD.encode())==1 and NEW.encode() not in data,'025 exact single upstream patch site')
    return data.replace(OLD.encode(),NEW.encode())

def committed():
    head=V.committed()
    for p in OWN:need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'025 commit all implementation/tests/audits before execution')
    return head

def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(240,240));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))

def env():
    return {**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','VK_ICD_FILENAMES':'/nonexistent/m001-nrd025-no-gpu.json','LD_LIBRARY_PATH':str(V.B.S.DXC.parent.parent/'lib')+':'+os.environ.get('NIX_LD_LIBRARY_PATH',os.environ.get('LD_LIBRARY_PATH',''))}

def execute(label,command,work,cwd=None):
    row=dict(label=label,command=list(map(str,command)),cwd=str(cwd or V.B.D.BUILD),pass_=False,cpu_limit=240,wall_limit=360)
    try:
        p=subprocess.run(row['command'],cwd=row['cwd'],env=env(),capture_output=True,timeout=360,preexec_fn=limits)
        row.update(returncode=p.returncode,pass_=p.returncode==0)
        for name,data in (('stdout',p.stdout),('stderr',p.stderr)):(work/(label+'.'+name+'.txt')).write_bytes(data)
    except subprocess.TimeoutExpired as e:
        row['error']=repr(e)
        for name,data in (('stdout',e.stdout),('stderr',e.stderr)):(work/(label+'.'+name+'.txt')).write_bytes(data or b'')
    print(label,row.get('returncode'),row['pass_'],flush=True)
    return row

def run(work):
    head=committed();work=work.resolve();need(work.is_relative_to(BASE) and not work.exists(),'025 exclusive build output')
    pins,_=V.inputs()
    for p in OWN:pins[str(p)]=SHA(p)
    sdk=read(SDK/'result.json');native=read(NATIVE/'result.json')
    for folder,r in ((SDK,sdk),(NATIVE,native)):
        need(r['all_pass'],'025 qualified original artifact required');rehash(r['compiled_dependency_sha256']);pins.update(r['compiled_dependency_sha256'])
        for name,h in r['payload_sha256'].items():pins[str(folder/name)]=h
        pins[str(folder/'result.json')]=SHA(folder/'result.json')
    for n in ('139-nrd-native-vulkan-first-runtime-failure.json','141-nrd-native-vulkan-first-runtime-failure-verification.json'):
        p=ROOT/'research/lanes/lane-m-gi-competitiveness/results'/n
        need(subprocess.check_output(['git','show','72da1d4a:'+str(p.relative_to(ROOT))])==p.read_bytes(),'025 original024 outcome changed');pins[str(p)]=SHA(p)
    rehash(pins);work.mkdir();private=work/'source';shutil.copytree(SDK/'source/NRD-e06852bd',private/'NRD-e06852bd')
    source=private/'NRD-e06852bd';target=source/'Shaders/RELAX_AtrousSmem.cs.hlsl';old=target.read_bytes();target.write_bytes(patch(old))
    (work/'registered-source.diff').write_text('--- upstream/RELAX_AtrousSmem.cs.hlsl\n+++ private/RELAX_AtrousSmem.cs.hlsl\n-'+OLD+'\n+'+NEW+'\n')
    need(all(p.read_bytes()==((patch(q.read_bytes())) if p==target else q.read_bytes()) for p in source.rglob('*') if p.is_file() for q in [SDK/'source/NRD-e06852bd'/p.relative_to(source)]),'025 private source differs beyond registered line')
    headers=work/'headers';headers.mkdir();cfg=work/'Shaders025.cfg'
    selected=[l for l in (source/'Shaders/Shaders.cfg').read_text().splitlines() if l.startswith('RELAX_AtrousSmem.cs.hlsl ')]
    need(len(selected)==1 and 'NRD_SIGNAL={NRD_SIGNAL_DIFF,NRD_SIGNAL_SPEC,NRD_SIGNAL_BOTH}' in selected[0] and 'NRD_MODE={NRD_MODE_RADIANCE,NRD_MODE_SH}' in selected[0],'025 six original family permutations')
    cfg.write_text(selected[0]+'\n')
    commands=(SDK/'upstream-commands.txt').read_text().splitlines();original_shader=next(l for l in commands if ' --serial -p SPIRV ' in l)
    cmd=shlex.split(original_shader.split(' && ',1)[1]);cmd[cmd.index('--sourceDir')+1]=str(source/'Shaders');cmd[cmd.index('-c')+1]=str(cfg);cmd[cmd.index('-o')+1]=str(headers)
    compile_cmd=shlex.split(next(l for l in commands if l.endswith('/Source/Relax.cpp')))
    for j,x in enumerate(compile_cmd):
        if str(SDK/'source/NRD-e06852bd') in x:compile_cmd[j]=x.replace(str(SDK/'source/NRD-e06852bd'),str(source))
    compile_cmd.insert(1,'-I'+str(headers))
    for flag,value in (('-o',work/'Relax.cpp.o'),('-MT',work/'Relax.cpp.o'),('-MF',work/'Relax.cpp.d')):compile_cmd[compile_cmd.index(flag)+1]=str(value)
    library=work/'libNRD.a';shutil.copyfile(SDK/'artifacts/libNRD.a',library)
    ar=Path('/run/current-system/sw/bin/ar').resolve();pins[str(ar)]=SHA(ar)
    link=list(native['rows'][3]['command'])
    for j,x in enumerate(link):
        if x==str(SDK/'artifacts/libNRD.a'):link[j]=str(library)
        elif x.startswith('-Wl,--dependency-file='):link[j]='-Wl,--dependency-file='+str(work/'link.d')
    link[link.index('-o')+1]=str(work/'nrd-vulkan')
    api=list(sdk['rows'][4]['command']);api[api.index(str(SDK/'artifacts/libNRD.a'))]=str(library);api[api.index('-o')+1]=str(work/'nrd-api-probe')
    rows=[('atrous-six-permutations',cmd),('relax-object',compile_cmd),('replace-archive-member',[str(ar),'rcs',str(library),str(work/'Relax.cpp.o')]),('native-relink',link),('api-relink',api)]
    r=dict(schema='m001-nrd025-private-sky-sdk-build/1',source_commit=head,complete=False,all_pass=False,gpu_executed=False,input_sha256=pins,compiled_dependency_sha256={},rows=[],executable=str(work/'nrd-vulkan'),api_executable=str(work/'nrd-api-probe'),shader_directory=str(NATIVE),upstream_commit=V.B.S.PINS['NRD-e06852bd'],private_source_variant='SKY_WORLD_POSITION_MATERIAL_ZERO_BEFORE_EARLY_OUT',changed_source=str(target),changed_source_sha256=SHA(target),original_source_sha256=hashlib_sha(old),sdk_family_permutations=6,old_native_objects_rebuilt=False,old_sdk_objects_rebuilt=False)
    try:
        for label,command in rows:
            row=execute(label,command,work);r['rows'].append(row);need(row['pass_'],'025 build step failed: '+label)
        need([p.name for p in headers.iterdir()]==['RELAX_AtrousSmem.cs.spirv.h'],'025 only registered SDK header generated')
        old_members=subprocess.check_output([str(ar),'t',str(SDK/'artifacts/libNRD.a')],text=True).splitlines();new_members=subprocess.check_output([str(ar),'t',str(library)],text=True).splitlines()
        need(old_members==new_members and len(new_members)==7 and len(set(new_members))==7,'025 archive member identity')
        identities={}
        for member in new_members:
            a=subprocess.check_output([str(ar),'p',str(SDK/'artifacts/libNRD.a'),member]);b=subprocess.check_output([str(ar),'p',str(library),member])
            need((a!=b)==(member=='Relax.cpp.o'),'025 unregistered archive member difference');identities[member]=dict(original_sha256=hashlib_sha(a),new_sha256=hashlib_sha(b),unchanged=a==b)
        r['archive_members']=identities
        for name in shlex.split((work/'Relax.cpp.d').read_text().replace('\\\n',' '))[1:]:
            p=Path(name);p=p if p.is_absolute() else V.B.D.BUILD/p
            if p.is_file():r['compiled_dependency_sha256'][str(p)]=SHA(p)
        need(str(target) in r['compiled_dependency_sha256'] or str(headers/'RELAX_AtrousSmem.cs.spirv.h') in r['compiled_dependency_sha256'],'025 replacement header compilation absent')
        rehash(pins);r['all_pass']=True
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    r.update(complete=True,payload_sha256=inventory(work))
    with (work/'result.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    return r

def hashlib_sha(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();r=run(a.work);print(json.dumps({k:r.get(k) for k in ('all_pass','error')}));sys.exit(0 if r['all_pass'] else 2)

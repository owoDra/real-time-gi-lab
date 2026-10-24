#!/usr/bin/env python3
"""024 CPU private adapter build, reusing successful022/023artifacts."""
import argparse
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import subprocess
import sys
import nrd_vulkan_overlay as O
import build_nrd_cpu as B
import build_integrated_pt as I
ROOT=B.ROOT;BASE=B.BASE;SRC=B.SOURCE;SHA=B.sha
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/024-nrd-native-vulkan-guide-runtime-controls.md'
SDK_BUILD=BASE/'m001-nrd023-cpu-build-v1';OLD_BUILD=BASE/'m001-integrated022-cpu-build-v1'
OWN=[Path(__file__).resolve(),Path(O.__file__).resolve(),PROTOCOL]+[Path(__file__).with_name(n) for n in ('test_nrd_vulkan.py','nrd_vulkan_process.py','nrd_vulkan_audit.py')]+[SRC/n for n in ('nrd_vulkan_runtime.cpp','nrd_vulkan_contract.hpp','test_nrd_vulkan_contract.cpp')]+[B.SHADERS/'nrd_composite_rgb.hlsl']

def read(p):return json.loads(Path(p).read_text())
def need(v,m):
 if not v:raise ValueError(m)
def committed():
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 for p in OWN:need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'024 commit all source/contracts/process/audit before execution')
 return head

def rehash(mapping):
 for p,h in mapping.items():need(Path(p).is_file() and SHA(p)==h,'024 changed evidence: '+str(p))

def inventory(p):return {str(f.relative_to(p)):SHA(f) for f in sorted(p.rglob('*')) if f.is_file() and f!=p/'result.json'}

def inputs():
 sdk=read(SDK_BUILD/'result.json');old=read(OLD_BUILD/'result.json');need(sdk['all_pass'] and old['all_pass'] and not sdk['gpu_executed'] and not old['gpu_executed'],'024 prior successful builds required')
 pins={str(p):SHA(p) for p in OWN+[Path(B.__file__),Path(I.__file__),Path(B.D.__file__),Path(B.S.__file__),Path(B.S.O.__file__),B.S.O.PT,B.S.O.CONTEXT]}
 for directory,r in ((SDK_BUILD,sdk),(OLD_BUILD,old)):
  rehash(r['compiled_dependency_sha256']);pins.update(r['compiled_dependency_sha256']);rehash({str(directory/p):h for p,h in r['payload_sha256'].items()});pins.update({str(directory/p):h for p,h in r['payload_sha256'].items()});pins[str(directory/'result.json')]=SHA(directory/'result.json')
 for n in ('133-nrd-relax-source-cpu-build.json','135-nrd-relax-real-sdk-cpu-qualification.json','137-nrd-relax-cpu-verification.json'):
  p=ROOT/'research/lanes/lane-m-gi-competitiveness/results'/n;j=read(p);need(j.get('all_pass',j.get('all_checks_pass')) is True,'024 CPU source/SDK qualification required');need(subprocess.check_output(['git','show','c43dbea2:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'024 changed023publication');pins[str(p)]=SHA(p)
 cc=B.D.command_rows();pins[str(Path(cc['host'][0]).resolve())]=SHA(Path(cc['host'][0]).resolve())
 for x in cc['link']:
  if x.endswith(('.o','.a')):
   p=Path(x);p=p if p.is_absolute() else B.D.BUILD/p;pins[str(p)]=SHA(p)
   if x.endswith('.o'):
    dep=subprocess.check_output(['ninja','-C',str(B.D.BUILD),'-t','deps',x],text=True)
    for line in dep.splitlines():
     if line.startswith('    '):
      p=Path(line.strip());p=p if p.is_absolute() else B.D.BUILD/p;pins[str(p)]=SHA(p)
 for p in (B.GLSLANG,B.VAL,B.S.DXC,B.D.LOADER):pins[str(p)]=SHA(p)
 return pins,cc

def run(work):
 head=committed();work=work.resolve();need(work.is_relative_to(BASE) and not work.exists(),'024 exclusive build output');pins,original=inputs();work.mkdir(parents=True)
 for p in OWN:
  if p.suffix in ('.hpp','.cpp','.hlsl'):shutil.copyfile(p,work/p.name)
 (work/'nrd_producer.comp.glsl').write_bytes(O.producer(B.S.O.PT.read_bytes()))
 bounded=B.S.O.bounded(B.S.O.CONTEXT.read_bytes(),'context');private=B.D.image_feature_overlay(bounded.decode()).encode();need(B.D.image_feature_overlay(bounded.decode()).encode()==private,'024 private context deterministic');(work/'nrd_context.cpp').write_bytes(private)
 shutil.copyfile(SDK_BUILD/'nrd_pack_guides.spv',work/'nrd_pack_guides.spv')
 sdk=SDK_BUILD/'source/NRD-e06852bd';flags=['-I'+str(SRC),'-I'+str(work),'-I'+str(sdk/'Include'),'-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all'];rows=[]
 for label,name in (('host','nrd_vulkan_runtime.cpp'),('context','nrd_context.cpp'),('contract','test_nrd_vulkan_contract.cpp')):
  cmd=list(original['host'])
  for flag,value in (('-c',work/name),('-o',work/(label+'.o')),('-MT',work/(label+'.o')),('-MF',work/(label+'.d'))):cmd[cmd.index(flag)+1]=str(value)
  rows.append((label+'-compile',cmd+flags))
 cmd=list(original['link']);oldmain=original['host'][original['host'].index('-o')+1]
 for j,x in enumerate(cmd):
  if x==oldmain:cmd[j]=str(work/'host.o')
  elif x.endswith('/generated/n010_b002_vulkan.cpp.o'):cmd[j]=str(work/'context.o')
  elif x.endswith('/lane_b_traversal/b002_hwrt.cpp.o'):cmd[j]=str(OLD_BUILD/'hwrt.o')
  elif x.startswith('-Wl,--dependency-file='):cmd[j]='-Wl,--dependency-file='+str(work/'link.d')
 cmd[cmd.index('-o')+1]=str(work/'nrd-vulkan');cmd+=[str(SDK_BUILD/'artifacts/libNRD.a'),str(SDK_BUILD/'build/shadermake/libShaderMakeBlob.a'),str(B.D.LOADER),'-pthread','-fsanitize=undefined','-fno-sanitize-recover=all'];rows.append(('host-link',cmd))
 rows.append(('contract-link',[original['host'][0],str(work/'contract.o'),str(B.D.LOADER),'-pthread','-fsanitize=undefined','-o',str(work/'nrd-vulkan-contract')]))
 rows.append(('producer-compile',[str(B.GLSLANG),'-V','--target-env','vulkan1.3',str(work/'nrd_producer.comp.glsl'),'-o',str(work/'nrd_producer.spv')]))
 rows.append(('producer-validate',[str(B.VAL),'--target-env','vulkan1.3',str(work/'nrd_producer.spv')]))
 rows.append(('composite-compile',[str(B.S.DXC),str(work/'nrd_composite_rgb.hlsl'),'-E','main','-T','cs_6_0','-spirv','-fspv-target-env=vulkan1.2','-WX','-I',str(sdk/'Shaders'),'-I',str(SDK_BUILD/'source/MathLib-aa432ad9'),'-Fo',str(work/'nrd_composite.spv')]))
 rows.append(('composite-validate',[str(B.VAL),'--target-env','vulkan1.2',str(work/'nrd_composite.spv')]))
 r=dict(schema='m001-nrd024-private-build/1',source_commit=head,complete=False,all_pass=False,gpu_executed=False,sdk_rebuilt=False,old_objects_rebuilt=False,input_sha256=pins,compiled_dependency_sha256={},rows=[],executable=str(work/'nrd-vulkan'),contract_executable=str(work/'nrd-vulkan-contract'),shader_directory=str(work))
 env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','LD_LIBRARY_PATH':str(B.S.DXC.parent.parent/'lib')+':'+os.environ.get('NIX_LD_LIBRARY_PATH',os.environ.get('LD_LIBRARY_PATH',''))}
 def limits():resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
 for label,cmd in rows:
  row=dict(label=label,command=cmd,cwd=str(B.D.BUILD),pass_=False)
  try:
   p=subprocess.run(cmd,cwd=B.D.BUILD,env=env,capture_output=True,timeout=180,preexec_fn=limits);row.update(returncode=p.returncode,pass_=p.returncode==0)
   for n,data in (('stdout',p.stdout),('stderr',p.stderr)):(work/(label+'.'+n+'.txt')).write_bytes(data)
  except subprocess.TimeoutExpired as e:
   row['error']=str(e)
   for n,data in (('stdout',e.stdout),('stderr',e.stderr)):(work/(label+'.'+n+'.txt')).write_bytes(data or b'')
  r['rows'].append(row);print(label,row.get('returncode'),row['pass_'],flush=True)
  if not row['pass_']:break
 for d in work.glob('*.d'):
  if d.name=='link.d':continue
  for name in shlex.split(d.read_text().replace('\\\n',' '))[1:]:
   p=Path(name);p=p if p.is_absolute() else B.D.BUILD/p
   if p.is_file():r['compiled_dependency_sha256'][str(p)]=SHA(p)
 rehash(pins);r.update(complete=True,all_pass=len(r['rows'])==len(rows) and all(x['pass_'] for x in r['rows']),payload_sha256=inventory(work))
 with (work/'result.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
 return r
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();r=run(a.work);print(json.dumps(dict(all_pass=r['all_pass'],gpu_executed=False)));sys.exit(0 if r['all_pass'] else 2)

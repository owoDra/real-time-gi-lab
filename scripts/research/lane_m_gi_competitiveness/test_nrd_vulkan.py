#!/usr/bin/env python3
"""024 actual CPU adapter/CLI and independent ray/stop guard contracts."""
import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import struct
import subprocess
import sys
import numpy as np
import build_nrd_vulkan as B
import nrd_vulkan_process as P
import nrd_vulkan_audit as A
import test_nrd_cpu as Q

def run(build,work):
 head=B.committed();b=B.read(build/'result.json');B.need(b['complete'] and b['all_pass'] and not b['gpu_executed'],'024 complete CPU build required');B.rehash(b['input_sha256']);B.rehash(b['compiled_dependency_sha256']);B.rehash({str(build/p):h for p,h in b['payload_sha256'].items()});B.need(work.is_relative_to(B.BASE) and not work.exists(),'024 exclusive CPU contracts');work.mkdir()
 r=dict(schema='m001-nrd024-cpu-contracts/1',source_commit=head,complete=False,all_pass=False,gpu_executed=False,input_sha256={str(p):B.SHA(p) for p in B.OWN},build_receipt=str(build/'result.json'),build_receipt_sha256=B.SHA(build/'result.json'),commands=[],checks=[],cpp_checks=0)
 env={**os.environ,'VK_ICD_FILENAMES':'/nonexistent/m024-no-gpu.json','VK_DRIVER_FILES':'/nonexistent/m024-no-gpu.json','LD_LIBRARY_PATH':os.environ.get('NIX_LD_LIBRARY_PATH',os.environ.get('LD_LIBRARY_PATH','')),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
 def check(name,condition):B.need(bool(condition),'024 CPU contract '+name);r['checks'].append(name)
 def reject(name,action):
  try:action()
  except (ValueError,FileNotFoundError,KeyError):r['checks'].append(name);return
  raise ValueError('024 contract accepted '+name)
 def command(name,args,expected=0):
  def limits():resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
  p=subprocess.run(list(map(str,args)),env=env,capture_output=True,timeout=180,preexec_fn=limits)
  for key,value in (('stdout',p.stdout),('stderr',p.stderr)):(work/(name+'.'+key+'.txt')).write_bytes(value)
  row=dict(name=name,command=list(map(str,args)),returncode=p.returncode,expected_returncode=expected,pass_=p.returncode==expected);r['commands'].append(row);B.need(row['pass_'],'024 actual native contract failed '+name);return p
 try:
  p=command('native-scalar',[b['contract_executable']]);scalar=json.loads(p.stdout);check('actual-new-cpp-mapping-range-contracts',scalar['complete'] and scalar['actual_cpp_checks']==33 and not scalar['gpu_initialized']);r['cpp_checks']=scalar['actual_cpp_checks']
  old=B.O.S.producer(B.O.S.O.PT.read_bytes()).decode();new=B.O.producer(B.O.S.O.PT.read_bytes()).decode();check('actual-generated-physical-producer-source',new.encode()==(build/'nrd_producer.comp.glsl').read_bytes())
  for token in ('uniform01(', 'cosine_direction(', 'trace(', 'direct_light('):check('no-new-transport-operation-'+token,new.count(token)==old.count(token))
  reject('reject-changed-original-physical-source',lambda:B.O.producer(B.O.S.O.PT.read_bytes()+b'\n'))
  check('actual-producer-bindings',Q.spirv(build/'nrd_producer.spv')['descriptors']==[[0,k] for k in range(10)])
  composite=Q.spirv(build/'nrd_composite.spv');check('actual-composite-bindings',composite['descriptors']==[[0,k] for k in range(3)] and composite['local_size']==[8,8,1]);check('official-packing-shader-reused-exact',(build/'nrd_pack_guides.spv').read_bytes()==(B.SDK_BUILD/'nrd_pack_guides.spv').read_bytes())
  proofs=[]
  for cell,depth,spp in P.TARGETS:
   pins={};proof=P.original(cell,depth,pins);r['input_sha256'].update(pins);proofs.append(proof);out=work/('native-'+cell.lower());args=[b['executable'],'--cpu-check','--state',proof['primary_capture'],'--out',out,'--spp',str(spp),'--vertices',str(depth),'--shaders',build];command(cell.lower()+'-actual-cpu-input',args);c=B.read(out/'complete.json');check(cell+'-no-gpu-and-buffer-budget',c['complete'] and not c['gpu_initialized'] and c['spp']==spp and c['vertices']==depth and c['secondary_ray_bytes']==57600*spp*16 and c['secondary_primitive_bytes']==57600*spp*4 and (out/'camera.f32').read_bytes()==Path(proof['original_camera']).read_bytes())
  state=proofs[0]['primary_capture'];base=[b['executable'],'--cpu-check','--state',state,'--out',str(work/'forbidden'),'--spp','16','--vertices','2','--shaders',str(build)]
  command('reject-no-options',[b['executable']],2)
  for label,index,value in [('mode',1,'--render'),('unknown-option',2,'--input'),('duplicate-option',6,'--state'),('spp-sign',7,'-16'),('spp-suffix',7,'16x'),('spp-overflow',7,'4294967296'),('unregistered-spp',7,'32'),('unregistered-depth',9,'7'),('absent-state',3,str(work/'absent-state')),('missing-shaders',11,str(work/'absent-shaders')),('absent-parent',5,str(work/'absent-parent/new'))]:
   args=list(base);args[index]=value;command('reject-'+label,args,2);check('no-output-for-'+label,not (work/'forbidden').exists())
  args=list(base);args[5]=str(work/'native-h01');before=B.inventory(work/'native-h01');command('reject-existing-output',args,2);check('existing-cpu-output-unchanged',before==B.inventory(work/'native-h01'))
  broken=work/'broken-shaders';broken.mkdir()
  for name in ('nrd_producer.spv','nrd_pack_guides.spv','nrd_composite.spv'):shutil.copyfile(build/name,broken/name)
  (broken/'nrd_pack_guides.spv').write_bytes(struct.pack('<4I',0x07230203,0,0,0));args=list(base);args[11]=str(broken);command('reject-truncated-shader-before-gpu',args,2);check('bad-shader-no-output',not (work/'forbidden').exists())
  # Independent actual double-oracle fixtures cover closest hit, farther hit
  # with self exclusion, miss, backface/two-sided hit and parallel ray.
  tri=np.array([[[-1,-1,3],[1,-1,3],[0,1,3]],[[-1,-1,5],[1,-1,5],[0,1,5]]],dtype=float);meta=np.array([[7,0xffffffff,1,1],[19,0xffffffff,1,1]],dtype='<u4');origins=np.array([[0,0,0],[0,0,0],[4,0,0],[0,0,4],[0,0,0]],dtype=float);dirs=np.array([[0,0,1],[0,0,1],[0,0,1],[0,0,-1],[1,0,0]],dtype=float);ignore=np.array([0xffffffff,7,0xffffffff,0xffffffff,0xffffffff],dtype='<u4');dist,ids=A.closest(origins,dirs,ignore,tri,meta)
  check('actual-physical-ray-oracle-identities',np.array_equal(ids,np.array([7,19,0xffffffff,7,0xffffffff],dtype='<u4')));check('actual-physical-ray-oracle-distances',np.array_equal(dist[[0,1,3]],[3,5,1]) and np.isposinf(dist[[2,4]]).all());reject('actual-ray-oracle-shape-rejection',lambda:A.closest(origins[:1],dirs,ignore,tri,meta))
  intake=work/'plan-intake';intake.mkdir();(intake/'plan.json').write_text('{}\n');P.launch_inventory(intake);check('new-only-plan-intake',True)
  for extra in ('started.json','result.json','capture'):
   p=intake/extra;p.mkdir() if extra=='capture' else p.write_text('{}\n');reject('reject-launched-partial-'+extra,lambda:P.launch_inventory(intake));p.rmdir() if p.is_dir() else p.unlink()
  (intake/'plan.json').unlink();(intake/'plan.json').symlink_to(work/'h01-actual-cpu-input.stdout.txt');reject('reject-plan-symlink',lambda:P.launch_inventory(intake))
  reject('reject-second-control-without-first-audit',lambda:P.previous('H02',8));reject('reject-third-control-without-prior-audits',lambda:P.previous('H03',2))
  image_names=['noisy-diffuse','normal-roughness','view-z','motion','denoised']+[f'permanent-{j}' for j in range(6)]+[f'transient-{j}' for j in range(4)];seq=A.sequence([dict(name=n) for n in image_names]);check('registered-bounded-unit-boundary',len(seq)==1454 and seq[0]==(0xffffffff,'initialize-images') and seq[1]==(0,'producer-0') and seq[-1]==(2,'readback-transient-3'))
  reject('reject-incomplete-device-journal',lambda:A.timestamps([],dict(timestamp_valid_bits=64,timestamp_period_ns=1),[],[dict(name=n) for n in image_names]));reject('reject-invalid-owned-ledger-schema',lambda:A.ledger_report(dict(schema='wrong',device_contexts=1),{},[]))
  r['all_pass']=True
 except Exception as e:r['error']=type(e).__name__+': '+str(e)
 B.rehash(r['input_sha256']);B.rehash({str(build/p):h for p,h in b['payload_sha256'].items()});r.update(complete=True,python_checks=len(r['checks']),actual_native_commands=len(r['commands']),payload_sha256=B.inventory(work))
 with (work/'result.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
 print(json.dumps({k:r.get(k) for k in ('all_pass','cpp_checks','python_checks','actual_native_commands','error')}));return r
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--build',type=Path,required=True);ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();r=run(a.build.resolve(),a.work.resolve());sys.exit(0 if r['all_pass'] else 2)

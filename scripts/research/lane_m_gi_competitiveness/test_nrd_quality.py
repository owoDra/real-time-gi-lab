#!/usr/bin/env python3
"""026 actual native budget/input tests, six-reference and cold/warm stop gates."""
import argparse
import json
from pathlib import Path
import tempfile
import numpy as np
import nrd_quality_build as B
import nrd_quality_overlay as O
import nrd_quality_process as P
import nrd_quality_audit as A

def run(work,build_path):
 head=B.committed();work=work.resolve();B.need(work.is_relative_to(B.BASE) and not work.exists(),'026 exclusive CPU test output');b=B.read(build_path);B.need(b['all_pass'] and not b['gpu_executed'],'026 actual passing build required');B.rehash(b['input_sha256']);B.rehash(b['compiled_dependency_sha256']);B.rehash({str(build_path.parent/name):h for name,h in b['payload_sha256'].items()});work.mkdir()
 r=dict(schema='m001-nrd026-cpu-quality-contracts/1',source_commit=head,complete=False,all_pass=False,gpu_executed=False,input_sha256={str(p):B.SHA(p) for p in B.OWN},build_receipt=str(build_path),build_receipt_sha256=B.SHA(build_path),checks=[],commands=[],references=[])
 def check(name,fn):fn();r['checks'].append(dict(name=name,pass_=True))
 def reject(fn):
  try:fn()
  except (ValueError,FileNotFoundError,KeyError):return
  raise AssertionError('026 expected rejection')
 try:
  check('actual compiled private host equals exact reversible overlay',lambda:B.need((build_path.parent/'nrd_vulkan_runtime.cpp').read_bytes()==O.host((B.S.V.SRC/'nrd_vulkan_runtime.cpp').read_bytes()),'host source'))
  check('actual compiled budget header equals exact reversible overlay',lambda:B.need((build_path.parent/'nrd_vulkan_contract.hpp').read_bytes()==O.header((B.S.V.SRC/'nrd_vulkan_contract.hpp').read_bytes()),'header source'))
  check('reject changed physical host schedule source',lambda:reject(lambda:O.host(b'broken')))
  check('reject changed budget contract site',lambda:reject(lambda:O.header(b'broken')))
  check('64 distinct fixed seeds and original cold seed',lambda:B.need(len(set(O.seed(i) for i in range(64)))==64 and O.seed(0)==305419896 and O.seed(1)==2959855665,'seed sequence'))
  for i in (-1,64,True):check('reject seed index '+str(i),lambda i=i:reject(lambda:O.seed(i)))
  rows=[dict(iteration=i,quality_pass=True) for i in range(64)]
  check('all64 passes admit cold and warm',lambda:B.need(A.decision(rows)==dict(cold_pass=True,warm_pass=True,joint_pass=True),'all pass'))
  bad=[dict(x) for x in rows];bad[63]['quality_pass']=False
  check('one terminal warm loss rejects warm despite63 passes',lambda:B.need(A.decision(bad)==dict(cold_pass=True,warm_pass=False,joint_pass=False),'terminal loss'))
  cold=[dict(x) for x in rows];cold[0]['quality_pass']=False
  check('warm-only pass preserves cold loss',lambda:B.need(A.decision(cold)==dict(cold_pass=False,warm_pass=True,joint_pass=False),'cold loss'))
  settling=[dict(x) for x in rows];settling[47]['quality_pass']=False
  check('settling row retained outside fixed last16 window',lambda:B.need(A.decision(settling)['joint_pass'],'settling window'))
  check('reject missing warm frame',lambda:reject(lambda:A.decision(rows[:-1])))
  check('reject reordered frame sequence',lambda:reject(lambda:A.decision(list(reversed(rows)))))
  check('original quality gate rejects excessive energy bias',lambda:B.need(A.M.quality({name:dict(pixels=57600,scoring_exclusions=0,nrmse=0.,signed_sum_bias=.06 if name=='indirect' else 0.,whole_image_max_absolute=0.) for name in ('direct','indirect','total')})=='QUALITY_FAIL','bias gate'))
  for cell,depth in P.TARGETS:
   pins={};proof=P.original(cell,depth,1,pins);r['input_sha256'].update(pins);r['references'].append(dict(cell=cell,depth=depth,verification=proof['reference_verification']))
   for spp in P.LADDER:
    dest=work/f'cpu-{cell.lower()}-b{depth}-n{spp}';cmd=[b['executable'],'--cpu-check','--state',proof['primary_capture'],'--out',str(dest),'--spp',str(spp),'--vertices',str(depth),'--shaders',b['shader_directory']]
    row=B.S.execute(f'{cell.lower()}-b{depth}-n{spp}',cmd,work);row.update(expected_returncode=0,contract_pass=row['returncode']==0);r['commands'].append(row);B.need(row['pass_'],'026 actual CPU native command');c=B.read(dest/'complete.json');check(f'{cell}-b{depth}-n{spp} actual dimensions noGPU',lambda c=c,spp=spp:B.need(c['complete'] and not c['gpu_initialized'] and c['spp']==spp and c['secondary_ray_bytes']==57600*spp*16 and c['secondary_primitive_bytes']==57600*spp*4,'actual shape'))
  first=work/'cpu-h01-b2-n1';base=list(r['commands'][0]['command']);base[5]=str(work/'forbidden')
  for spp in ('0','2','3','32','65','-1','4294967296'):
   cmd=list(base);cmd[7]=spp;row=B.S.execute('reject-spp-'+spp,cmd,work);row.update(expected_returncode=2,contract_pass=row['returncode']==2);r['commands'].append(row);check('actual native rejects spp '+spp,lambda row=row:B.need(row['returncode']==2 and not (work/'forbidden').exists(),'budget reject'))
  before=B.inventory(first);cmd=list(base);cmd[5]=str(first);row=B.S.execute('reject-overwrite',cmd,work);row.update(expected_returncode=2,contract_pass=row['returncode']==2);r['commands'].append(row);check('actual existing CPU output unchanged',lambda:B.need(row['returncode']==2 and B.inventory(first)==before,'overwrite'))
  with tempfile.TemporaryDirectory(dir=work) as directory:
   fixture=Path(directory)
   check('initial first-rung plan has no dependency',lambda:B.need(P.previous('H01',2,1,fixture)=={},'initial gate'))
   check('missing preceding rung stops without GPU',lambda:reject(lambda:P.previous('H01',2,4,fixture)))
   for spp,passed in ((1,False),(4,False),(16,True)):
    native=fixture/f'native-{spp}.json';B.write(native,dict(complete=True,valid=True));out=fixture/(P.tag('H01',2,spp)+'-audit-v1');out.mkdir();B.write(out/'result.json',dict(cell='H01',depth=2,spp=spp,complete=True,valid=True,classification='JOINT_QUALITY_PASS' if passed else 'QUALITY_FAIL',joint_pass=passed,cold_pass=passed,warm_pass=passed,native_receipt=str(native),native_receipt_sha256=B.SHA(native),payload_sha256={}))
   check('first joint pass blocks later rung',lambda:reject(lambda:P.previous('H01',2,64,fixture)))
   check('terminal prior target permits next target',lambda:B.need(bool(P.previous('H01',8,1,fixture)),'next target'))
   bad=fixture/(P.tag('H01',2,16)+'-audit-v1/result.json');v=B.read(bad);v['valid']=False;bad.write_text(json.dumps(v));check('operational failure blocks next target',lambda:reject(lambda:P.previous('H01',8,1,fixture)))
  r.update(all_pass=True,actual_native_cpu_commands=len(r['commands']),python_checks=len(r['checks']),qualified_reference_slots=6,prior024_025_contracts_reused_not_rerun=True)
 except Exception as e:r['error']=type(e).__name__+': '+str(e)
 B.rehash(r['input_sha256']);r.update(complete=True,payload_sha256=B.inventory(work));B.write(work/'result.json',r);return r

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--build',type=Path,required=True);a=ap.parse_args();r=run(a.work,a.build.resolve());print(json.dumps({k:r.get(k) for k in ('all_pass','python_checks','actual_native_cpu_commands','qualified_reference_slots','error')}));raise SystemExit(0 if r['all_pass'] else 2)

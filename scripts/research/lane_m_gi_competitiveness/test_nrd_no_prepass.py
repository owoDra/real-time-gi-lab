#!/usr/bin/env python3
"""028 actual native budget/input tests, six-reference and cold/warm stop gates."""
import argparse
import json
from pathlib import Path
import tempfile
import struct
import nrd_semantics_audit as S
import nrd_quality_process as OLD
import numpy as np
import nrd_no_prepass_build as B
import nrd_no_prepass_overlay as O
import nrd_no_prepass_process as P
import nrd_no_prepass_audit as A

def run(work,build_path):
 head=B.committed();work=work.resolve();B.need(work.is_relative_to(B.BASE) and not work.exists(),'028 exclusive CPU test output');b=B.read(build_path);B.need(b['all_pass'] and not b['gpu_executed'],'028 actual passing build required');B.rehash(b['input_sha256']);B.rehash(b['compiled_dependency_sha256']);B.rehash({str(build_path.parent/name):h for name,h in b['payload_sha256'].items()});work.mkdir()
 r=dict(schema='m001-nrd028-cpu-quality-contracts/1',source_commit=head,complete=False,all_pass=False,gpu_executed=False,input_sha256={str(p):B.SHA(p) for p in B.OWN},build_receipt=str(build_path),build_receipt_sha256=B.SHA(build_path),checks=[],commands=[],references=[],probes=[])
 def check(name,fn):fn();r['checks'].append(dict(name=name,pass_=True))
 def reject(fn):
  try:fn()
  except (ValueError,FileNotFoundError,KeyError):return
  raise AssertionError('028 expected rejection')
 try:
  check('actual compiled private host equals exact reversible overlay',lambda:B.need((build_path.parent/'nrd_vulkan_runtime.cpp').read_bytes()==O.host((B.Q.S.V.SRC/'nrd_vulkan_runtime.cpp').read_bytes()),'host source'))
  check('actual compiled API probe overlay',lambda:B.need((build_path.parent/'nrd_api_probe.cpp').read_bytes()==O.probe((B.Q.S.V.SRC/'nrd_api_probe.cpp').read_bytes()),'probe source'))
  check('actual compiled budget header equals exact reversible overlay',lambda:B.need((build_path.parent/'nrd_vulkan_contract.hpp').read_bytes()==O.header((B.Q.S.V.SRC/'nrd_vulkan_contract.hpp').read_bytes()),'header source'))
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
   oldplan=B.BASE/f'm001-nrd026-gpu-{cell.lower()}-b{depth}-n1-v1/plan.json'; original=B.read(oldplan);proof=original['proof'];r['input_sha256'][str(oldplan)]=B.SHA(oldplan);r['references'].append(dict(cell=cell,depth=depth,verification=proof['reference_verification'],reused=True))
   for spp in P.LADDER:
    dest=work/f'cpu-{cell.lower()}-b{depth}-n{spp}';cmd=[b['executable'],'--cpu-check','--state',proof['primary_capture'],'--out',str(dest),'--spp',str(spp),'--vertices',str(depth),'--shaders',b['shader_directory']]
    row=B.Q.S.execute(f'{cell.lower()}-b{depth}-n{spp}',cmd,work);row.update(expected_returncode=0,contract_pass=row['returncode']==0);r['commands'].append(row);B.need(row['pass_'],'028 actual CPU native command');c=B.read(dest/'complete.json');check(f'{cell}-b{depth}-n{spp} actual dimensions noGPU',lambda c=c,spp=spp:B.need(c['complete'] and not c['gpu_initialized'] and c['spp']==spp and c['secondary_ray_bytes']==57600*spp*16 and c['secondary_primitive_bytes']==57600*spp*4,'actual shape'))
  first=work/'cpu-h01-b2-n1';base=list(r['commands'][0]['command']);base[5]=str(work/'forbidden')
  for spp in ('0','2','3','32','65','-1','4294967296'):
   cmd=list(base);cmd[7]=spp;row=B.Q.S.execute('reject-spp-'+spp,cmd,work);row.update(expected_returncode=2,contract_pass=row['returncode']==2);r['commands'].append(row);check('actual native rejects spp '+spp,lambda row=row:B.need(row['returncode']==2 and not (work/'forbidden').exists(),'budget reject'))
  before=B.inventory(first);cmd=list(base);cmd[5]=str(first);row=B.Q.S.execute('reject-overwrite',cmd,work);row.update(expected_returncode=2,contract_pass=row['returncode']==2);r['commands'].append(row);check('actual existing CPU output unchanged',lambda:B.need(row['returncode']==2 and B.inventory(first)==before,'overwrite'))
  with tempfile.TemporaryDirectory(dir=work) as directory:
   fixture=Path(directory)
   check('initial first-rung plan has no dependency',lambda:B.need(P.previous('H01',2,1,fixture)=={},'initial gate'))
   check('missing preceding rung stops without GPU',lambda:reject(lambda:P.previous('H01',2,4,fixture)))
   for spp,passed in ((1,False),(4,False),(16,True)):
    native=fixture/f'native-{spp}.json';B.write(native,dict(complete=True,valid=True));out=fixture/(P.tag('H01',2,spp)+'-audit-v1');out.mkdir();B.write(out/'result.json',dict(cell='H01',depth=2,spp=spp,complete=True,valid=True,classification='JOINT_QUALITY_PASS' if passed else 'QUALITY_FAIL',joint_pass=passed,cold_pass=passed,warm_pass=passed,native_receipt=str(native),native_receipt_sha256=B.SHA(native),payload_sha256={}))
   check('first joint pass blocks later rung',lambda:reject(lambda:P.previous('H01',2,64,fixture)))
   check('terminal prior target permits next target',lambda:B.need(bool(P.previous('H01',8,1,fixture)),'next target'))
   bad=fixture/(P.tag('H01',2,16)+'-audit-v1/result.json');v=B.read(bad);v['valid']=False;bad.write_text(json.dumps(v));check('operational failure blocks next target',lambda:reject(lambda:P.previous('H01',8,1,fixture)))
  extra_contracts(check,reject,work)
  sdk_probes(r,work,b)
  r.update(all_pass=True,actual_native_cpu_commands=sum(not x['label'].startswith('sdk-') for x in r['commands']),actual_sdk_processes=3,python_checks=len(r['checks']),qualified_reference_slots=6,prior024_025_026_mathematical_physical_contracts_reused_not_rerun=True,actual_sdk_api_frames=195)
 except Exception as e:r['error']=type(e).__name__+': '+str(e)
 B.rehash(r['input_sha256']);r.update(complete=True,payload_sha256=B.inventory(work));B.write(work/'result.json',r);return r

def constant_delta(old,new,layout):
 B.need(len(new)==len(old),'028 constant size')
 spec=layout['fields'].get('gDiffBlurRadius')
 if spec is None:
  B.need(new==old,'028 Clear constants changed');return 0
 B.need(spec['kind']=='float' and spec['count']==1 and spec['bytes']==4,'028 scalar float blur layout')
 at=spec['offset'];B.need(type(at) is int and 0<=at<=len(old)-4,'028 blur constant bounds')
 B.need(old[at:at+4]==struct.pack('<f',30.) and new[at:at+4]==struct.pack('<f',0.),'028 only30 to positive zero')
 B.need(new[:at]+old[at:at+4]+new[at+4:]==old,'028 unregistered constant difference')
 return 4

def extra_contracts(check,reject,work):
 raw=(B.Q.S.V.SRC/'nrd_vulkan_runtime.cpp').read_bytes();base=O.Q.host(raw)
 patched=O.host(raw);restored=patched.replace(O.SETTING[1].encode(),O.SETTING[0].encode()).replace(b'm001-nrd028-native-quality-runtime/1',b'm001-nrd026-native-quality-runtime/1')
 check('entire host differs only setting and schema',lambda:B.need(restored==base,'028 host complete whitelist'))
 for value in (b'',O.SETTING[0].encode()*2,O.SETTING[1].encode()):check('reject ambiguous settings site '+str(len(value)),lambda value=value:reject(lambda:O.apply(value,[O.SETTING])))
 rows=[dict(iteration=i,quality_pass=True) for i in range(64)]
 for i in range(48,64):
  bad=[dict(x) for x in rows];bad[i]['quality_pass']=False
  check('each warm frame independently vetoes '+str(i),lambda bad=bad:B.need(not A.decision(bad)['joint_pass'],'028 warm veto'))
 layout={'fields':{'gDiffBlurRadius':dict(kind='float',count=1,bytes=4,offset=4)}};old=b'ABCD'+struct.pack('<f',30.)+b'EFGH';new=b'ABCD'+struct.pack('<f',0.)+b'EFGH'
 check('accept exact one constant member change',lambda:B.need(constant_delta(old,new,layout)==4,'028 delta'))
 check('accept exact Clear constants',lambda:B.need(constant_delta(b'ABCD',b'ABCD',{'fields':{}})==0,'028 clear'))
 for name,v in [('extra byte',new+b'!'),('unregistered member',b'X'+new[1:]),('negative zero',new[:4]+struct.pack('<f',-0.)+new[8:]),('wrong radius',new[:4]+struct.pack('<f',1.)+new[8:])]:check('reject '+name,lambda v=v:reject(lambda:constant_delta(old,v,layout)))
 check('reject truncated reflected field',lambda:reject(lambda:constant_delta(b'AB',b'AB',layout)))
 check('reject Clear difference',lambda:reject(lambda:constant_delta(b'AB',b'AC',{'fields':{}})))
 with tempfile.TemporaryDirectory(dir=work) as folder:
  root=Path(folder);old=root/'old';new=root/'new';old.write_bytes(b'1234');new.write_bytes(b'1234');expected=B.SHA(old)
  check('accept actual complete byte witness',lambda:B.need(A.exact_field(new,old,expected)==4,'028 bytes'))
  new.write_bytes(b'1235');check('reject one changed producer bit',lambda:reject(lambda:A.exact_field(new,old,expected)))
  new.unlink();check('reject absent new field despite valid old',lambda:reject(lambda:A.exact_field(new,old,expected)))
  new.symlink_to(old);check('reject substituted historical witness',lambda:reject(lambda:A.exact_field(new,old,expected)))
 with tempfile.TemporaryDirectory(dir=work) as folder:
  root=Path(folder);(root/'plan.json').write_text('{}')
  check('accept never launched plan intake',lambda:P.S.launch_inventory(root));(root/'started.json').write_text('{}')
  check('reject partial or previously launched intake',lambda:reject(lambda:P.S.launch_inventory(root)))

def sdk_probes(r,work,build):
 # Reuse published025/026 contracts only after receipt and payload hashes.
 oldcontracts=B.BASE/'m001-nrd026-cpu-contracts-v1/result.json';old=B.read(oldcontracts)
 B.need(old['all_pass'] and old['actual_native_cpu_commands']==32,'028 pinned026 contracts')
 r['input_sha256'][str(oldcontracts)]=B.SHA(oldcontracts)
 B.rehash(old['input_sha256']);r['input_sha256'].update(old['input_sha256'])
 for cell in ('H01','H02','H03'):
  original_plan=B.BASE/f'm001-nrd026-gpu-{cell.lower()}-b2-n1-v1/plan.json';p=B.read(original_plan);proof=p['proof'];reference=Path(proof['sdk_cpu_capture']);out=work/cell.lower()
  row=B.Q.S.execute('sdk-'+cell.lower(),[build['api_executable'],'--cpu-inspect','--state',proof['primary_capture'],'--out',str(out)],work);r['commands'].append(row);B.need(row['pass_'],'028 new API failure')
  expected_files={str(p.relative_to(reference)) for p in reference.rglob('*') if p.is_file()};actual_files={str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()};B.need(actual_files==expected_files,'028 SDK file coverage')
  config=B.read(out/'instance.json');prior=B.read(reference/'instance.json');B.need(config.pop('schema')=='m001-nrd028-instance/1','028 instance schema');prior.pop('schema');settings=config.pop('configured_settings');defaults=prior.pop('default_settings')
  B.need(settings==dict(defaults,diffuse_prepass_radius=0) and config==prior,'028 all resources/settings except prepass equal')
  complete=B.read(out/'complete.json');before=B.read(reference/'complete.json');B.need(complete.pop('schema')=='m001-nrd028-real-sdk-cpu-probe/1','028 API completion schema');before.pop('schema');B.need(complete==before and complete['api_frames']==65,'028 actual65 API frames')
  actual=A.A.jsonl(out/'dispatches.jsonl');original=A.A.jsonl(reference/'dispatches.jsonl');B.need(actual==original and len(actual)==65,'028 all dispatch/resource/grid/match flags identical')
  changed=0;clears=0;constants=set()
  layouts=[S.reflect((out/f'pipelines/{i}.spv').read_bytes(),False) for i in range(15)]
  for frame in actual:
   for d in frame['dispatches']:
    name='constants/'+d['constant_file'];constants.add(name);a=(reference/name).read_bytes();b=(out/name).read_bytes();delta=constant_delta(a,b,layouts[d['pipeline']]);changed+=bool(delta);clears+=not bool(delta)
  B.need(changed==650 and clears==22,'028650 RELAX22 Clear records')
  B.need(actual[0]['dispatches']==[{**d,'constant_file':d['constant_file'].replace('64-','0-',1)} for d in actual[64]['dispatches']],'028 reset dispatch identity')
  for a,b in zip(actual[0]['dispatches'],actual[64]['dispatches']):B.need((out/'constants'/a['constant_file']).read_bytes()==(out/'constants'/b['constant_file']).read_bytes(),'028 reset-to-cold bytes')
  for name in expected_files-constants-{'instance.json','complete.json'}:B.need((reference/name).read_bytes()==(out/name).read_bytes(),'028 unregistered SDK payload difference: '+name)
  for p in reference.rglob('*'):
   if p.is_file():r['input_sha256'][str(p)]=B.SHA(p)
  r['probes'].append(dict(cell=cell,api_frames=65,RELAX_changed_records=changed,Clear_unchanged_records=clears,changed_bytes=changed*4,all15_pipeline_bytes_unchanged=True,reset_to_cold_constants_exact=True,all_other_bytes_resources_dispatches_settings_equal=True))

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--build',type=Path,required=True);a=ap.parse_args();r=run(a.work,a.build.resolve());print(json.dumps({k:r.get(k) for k in ('all_pass','python_checks','actual_native_cpu_commands','qualified_reference_slots','error')}));raise SystemExit(0 if r['all_pass'] else 2)

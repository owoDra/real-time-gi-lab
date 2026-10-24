#!/usr/bin/env python3
"""024 one-process plan/intake/stop runner; never automatically queues a cohort."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import build_nrd_vulkan as B
import nrd_vulkan_audit as A
import guided_transport_cpu as G
import integrated_pt_process as I
BASE=B.BASE;ROOT=B.ROOT;TARGETS=[('H01',2,16),('H02',8,64),('H03',2,64)]
BUILD=BASE/'m001-nrd024-cpu-build-v2/result.json';CPU=BASE/'m001-nrd024-cpu-contracts-v1/result.json'

def tag(cell,depth):return f'm001-nrd024-gpu-{cell.lower()}-b{depth}'
def write(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def pin_receipt(p,pins):
 r=B.read(p);pins[str(p)]=B.SHA(p)
 for name,h in r.get('payload_sha256',{}).items():pins[str(p.parent/name)]=h
 B.rehash(pins);return r

def original(cell,depth,pins):
 p=BASE/f'm001-integrated022-gpu-{cell.lower()}-b{depth}-v1/result.json';r=pin_receipt(p,pins);B.need(r['complete'] and r['valid'],'024 original022capture unavailable');q=p.parent/'plan.json';B.need(B.SHA(q)==r['plan_sha256'],'024 original022plan differs');pins[str(q)]=B.SHA(q);j=B.read(q);state=Path(j['proof']['primary_capture']);reference=Path(j['proof']['reference']['directory'])/'o.n8192.hits'
 for p in (state/'geometry-state.bin',state/'frame-state.bin',reference):pins[str(p)]=B.SHA(p)
 cpu_directory=BASE/('m001-nrd023-cpu-contracts-v1' if cell=='H01' else 'm001-nrd023-cpu-contracts-v3')/cell.lower()
 for p in cpu_directory.rglob('*'):
  if p.is_file():pins[str(p)]=B.SHA(p)
 return dict(primary_capture=str(state),original_raw=str(q.parent/'capture/raw-pt.f32'),original_camera=str(q.parent/'capture/camera.f32'),primary_oracle=str(reference),sdk_cpu_capture=str(cpu_directory))

def previous(cell,depth):
 index=next(i for i,t in enumerate(TARGETS) if t[:2]==(cell,depth));pins={}
 for c,d,s in TARGETS[:index]:
  p=BASE/(tag(c,d)+'-audit-v1')/'result.json';r=pin_receipt(p,pins);B.need(r['complete'] and r['all_pass'] and r['classification']=='NATIVE_NRD_CONTROL_PASS','024 previous independent terminal audit not passing')
 return pins

def prepared(cell,depth):
 head=B.committed();target=next((t for t in TARGETS if t[:2]==(cell,depth)),None);B.need(target is not None,'024 unregistered control');pins=previous(cell,depth)
 build=pin_receipt(BUILD,pins);cpu=pin_receipt(CPU,pins);B.need(build['all_pass'] and cpu['all_pass'] and not build['gpu_executed'] and not cpu['gpu_executed'],'024 actual CPU readiness missing')
 for r in (build,cpu):
  for field in ('input_sha256','compiled_dependency_sha256'):
   B.rehash(r.get(field,{}));pins.update(r.get(field,{}))
 proof=original(cell,depth,pins);proof.update(spp=target[2],executable=build['executable'],shaders=build['shader_directory'])
 for p in B.OWN:pins[str(p)]=B.SHA(p)
 B.rehash(pins);return head,pins,proof

def command(proof,out,depth):return [proof['executable'],'--gpu','--state',proof['primary_capture'],'--out',str(out/'capture'),'--spp',str(proof['spp']),'--vertices',str(depth),'--shaders',proof['shaders']]

def quiet():
 I.quiet()
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name)==os.getpid():continue
  try:name=(p/'exe').readlink().name
  except (FileNotFoundError,PermissionError,ProcessLookupError):continue
  B.need(name!='nrd-vulkan','024 another NRD native process active')

def launch_inventory(root):
 B.need(root.is_dir() and not root.is_symlink(),'024 plan parent invalid')
 B.need({p.name for p in root.iterdir()}=={'plan.json'} and (root/'plan.json').is_file() and not (root/'plan.json').is_symlink(),'024 already launched/partial/extra intake; no retry')

def prepare(cell,depth,out):
 head,pins,proof=prepared(cell,depth);B.need(out==BASE/(tag(cell,depth)+'-v1') and not out.exists(),'024 exclusive canonical output');quiet();B.need(shutil.disk_usage(BASE).free>=16*1024**3,'024 disk gate');out.mkdir()
 plan=dict(schema='m001-nrd024-one-native-plan/1',cell=cell,depth=depth,source_commit=head,input_sha256=pins,proof=proof,command=command(proof,out,depth),gpu_processes_authorized=1,accepted_timing=False);write(out/'plan.json',plan);return out/'plan.json'

def validate(path):
 root=path.parent.resolve();B.need(path.name=='plan.json' and root.is_relative_to(BASE),'024 invalid plan path');launch_inventory(root);p=B.read(path);head,pins,proof=prepared(p['cell'],p['depth'])
 B.need(p==dict(schema='m001-nrd024-one-native-plan/1',cell=p['cell'],depth=p['depth'],source_commit=head,input_sha256=pins,proof=proof,command=command(proof,root,p['depth']),gpu_processes_authorized=1,accepted_timing=False) and root==BASE/(tag(p['cell'],p['depth'])+'-v1'),'024 plan/provenance/command differs');return p

def run(path):
 plan=validate(path);root=path.parent;quiet();B.need(shutil.disk_usage(root).free>=16*1024**3,'024 disk gate');write(root/'started.json',dict(plan_sha256=B.SHA(path),gpu_processes_authorized=1))
 r=dict(schema='m001-nrd024-one-native-runtime/1',cell=plan['cell'],depth=plan['depth'],source_commit=plan['source_commit'],complete=False,valid=False,gpu_executed=True,classification='STOP_NO_RETRY',accepted_timing=False,plan_sha256=B.SHA(path))
 try:
  launch=root/'launch';launch.mkdir();native=G.guarded(plan['command'],launch,120,180);write(launch/'result.json',native);B.need(native['returncode']==0 and not native['timed_out'],'024 native failed/timeout; stop no retry');complete=B.read(root/'capture/complete.json');B.need(complete['complete'] and complete['frames']==3 and complete['units']==1454 and complete['aggregate_reserved_at_teardown']==0,'024 native incomplete/ownership');B.rehash(plan['input_sha256']);r.update(complete=True,valid=True,classification='GPU_EXECUTED_AUDIT_REQUIRED')
 except Exception as e:r['error']=repr(e)
 r['payload_sha256']=B.inventory(root);write(root/'result.json',r);return r

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='mode',required=True);p=sub.add_parser('prepare');p.add_argument('--cell',choices=('H01','H02','H03'),required=True);p.add_argument('--depth',type=int,choices=(2,8),required=True);p.add_argument('--out',type=Path,required=True);p=sub.add_parser('run');p.add_argument('--plan',type=Path,required=True);p=sub.add_parser('audit');p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if a.mode=='prepare':print(prepare(a.cell,a.depth,a.out.resolve()))
 elif a.mode=='run':
  r=run(a.plan.resolve());print(json.dumps({k:r.get(k) for k in ('complete','valid','classification','error')}));sys.exit(0 if r['complete'] else 2)
 else:
  r=A.run(a.native.resolve(),a.out.resolve());print(json.dumps({k:r.get(k) for k in ('complete','all_pass','classification','error')}));sys.exit(0 if r['all_pass'] else 2)

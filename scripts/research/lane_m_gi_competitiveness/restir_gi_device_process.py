#!/usr/bin/env python3
"""034 exclusive ordered one-process GPU plans. No clocks/power configuration."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time
import restir_gi_device_build as D
import restir_gi_device_model as M
import anchor_process_limits as C
import integrated_pt_process as I

B,BASE=D.B,D.BASE


def root_for(size):
    M.need(size in ('17x9','320x180'),'unregistered dimension')
    return BASE/('m001-restir034-gpu-'+size+'-v1')


def previous(size):
    if size=='17x9':return {}
    p=Path(str(root_for('17x9'))+'-audit')/'result.json';r=B.read(p)
    M.need(r['complete'] and r['all_pass'] and r['classification']=='ANALYTIC_GPU_DIMENSION_PASS','first full independent audit required')
    B.rehash(r['input_sha256']);B.rehash({str(p.parent/k):v for k,v in r['payload_sha256'].items()})
    return {str(p):B.SHA(p)}


def readiness(size,build):
    D.committed();M.need(build in [BASE/f'm001-restir034-cpu-build-v{i}' for i in (1,2,3)],'registered build')
    inputs,trees=D.intake();r=D.pin_inventory(build,inputs)
    M.need(r['classification']=='CPU_DEVICE_CONTROL_PREPARATION_PASS' and not r['gpu_executed'],'CPU qualification required')
    inputs.update(previous(size));folder=build/('inputs-'+size)
    M.need(folder.is_dir(),'prepared full inputs')
    return inputs,dict(executable=r['executable'],inputs=str(folder),shaders=r['shader_directory'],build=str(build),official_trees=trees)


def command(proof,root):return [proof['executable'],'--gpu','--input',proof['inputs'],'--out',str(root/'native'),'--shaders',proof['shaders']]


def pristine(root):
    M.need({p.name for p in root.iterdir()}=={'plan.json'},'already launched/partial/extra inventory: never retry')


def plan(size,build):
    head=D.committed();root=root_for(size);M.need(not root.exists(),'exclusive GPU root')
    inputs,proof=readiness(size,build);I.quiet();M.need(shutil.disk_usage(BASE).free>=16*1024**3,'16GiB disk guard')
    root.mkdir();r=dict(schema='m001-restir034-one-gpu-plan/1',source_commit=head,size=size,input_sha256=inputs,
                      proof=proof,command=command(proof,root),gpu_processes_authorized=1,accepted_timing=False,power_clock_changes=False)
    C.write(root/'plan.json',r);print(root/'plan.json',flush=True)


def run(path):
    start=time.monotonic();path=path.resolve();r=B.read(path);root=root_for(r['size'])
    M.need(path==root/'plan.json' and r['schema']=='m001-restir034-one-gpu-plan/1','plan identity');pristine(root)
    M.need(r['source_commit']==D.committed() and r['gpu_processes_authorized']==1 and r['accepted_timing'] is False and r['power_clock_changes'] is False,'plan authority')
    inputs,proof=readiness(r['size'],Path(r['proof']['build']))
    M.need(inputs==r['input_sha256'] and proof==r['proof'] and command(proof,root)==r['command'],'reconstructed plan differs')
    I.quiet();M.need(shutil.disk_usage(BASE).free>=16*1024**3,'disk guard');B.rehash(inputs)
    # Removing unusable CPU-check ICD overrides affects only this child environment.
    os.environ.pop('VK_ICD_FILENAMES',None);os.environ.pop('VK_DRIVER_FILES',None)
    result=dict(schema='m001-restir034-one-gpu-receipt/1',source_commit=r['source_commit'],complete=False,all_pass=False,
                classification='INVALID_GPU_ACQUISITION',size=r['size'],gpu_process_attempts=0,input_sha256=dict(inputs,**{str(path):B.SHA(path)}))
    C.write(root/'launch-before.json',dict(command=r['command'],gpu_process_attempts=1))
    try:
        result['effective_parent_limits']=C.limits();result['gpu_process_attempts']=1
        result['process']=C.guarded(r['command'],root,'gpu',cpu=120,wall=180)
        native=B.read(root/'native/complete.json')
        M.need(native['complete'] and native['gpu_initialized'] and native['dispatches']==240 and native['copies']==48 and native['units']==288 and native['configurations']==48,'fixed native boundary')
        B.rehash(result['input_sha256']);M.need(time.monotonic()-start<600,'wrapper wall600')
        result.update(complete=True,all_pass=True,classification='GPU_ACQUISITION_COMPLETE_REQUIRES_INDEPENDENT_AUDIT')
    except Exception as e:result['error']=type(e).__name__+': '+str(e)
    result['payload_sha256']=B.inventory(root);C.write(root/'result.json',result)
    print(json.dumps({k:result.get(k) for k in ('complete','classification','gpu_process_attempts','error')}),flush=True)
    return 0 if result['all_pass'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    p=sub.add_parser('plan');p.add_argument('--size',choices=['17x9','320x180'],required=True);p.add_argument('--build',type=Path,required=True)
    p=sub.add_parser('run');p.add_argument('--plan',type=Path,required=True);args=parser.parse_args()
    if args.operation=='plan':plan(args.size,args.build)
    else:sys.exit(run(args.plan))

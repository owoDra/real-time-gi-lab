#!/usr/bin/env python3
"""038 include-only correction; frozen037 native/GLSL/model/tests, no rebuild."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import restir_gi_gpu_bridge as G

ROOT,BASE,C=G.ROOT,G.BASE,G.C
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/038-physical-gpu-sdk-math-include-correction.md'
OWN=[PROTOCOL,Path(__file__).resolve()]
FAILED=G.PREP;PREP=BASE/'m001-restir038-cpu-build-v1'
ORIGINAL_COMMITTED=G.committed;ORIGINAL_FINISH=G.finish
ORIGINAL_SOURCE_STATE=G.source_state


def committed():
    head=ORIGINAL_COMMITTED();subprocess.run(['git','merge-base','--is-ancestor','f3c426ef',head],cwd=ROOT,check=True)
    for p in OWN:G.need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'commit038 wrapper before use')
    for p in G.OWN:G.need(subprocess.check_output(['git','show','c9c50cab:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'all037 source/model/tests immutable')
    return head


def corrected(raw):
    needle=b'#include <Rtxdi/GI/ReSTIRGIParameters.h>'
    extra=b'\n#include <Rtxdi/Utils/Math.hlsli>'
    G.need(raw.count(needle)==1 and extra not in raw,'one missing include only')
    result=raw.replace(needle,needle+extra)
    G.need(result.replace(needle+extra,needle)==raw,'exact include-only inverse')
    return result


def finish(root,r):
    r.update(study='038',original_physical_source_commit='c9c50cab6afd89a353183c095270c456a7f019b8',original_preregistration_commit='2d427d0b',correction_preregistration_commit='f3c426ef',old037_stopped=True)
    return ORIGINAL_FINISH(root,r)


def case_root(cell,depth):
    G.need((cell,depth) in G.M.TARGETS,'registered038 case');return BASE/f'm001-restir038-{cell.lower()}-b{depth}-v1'


def source_state(cell,depth,pins):
    pins.update({str(p):G.sha(p) for p in OWN})
    return ORIGINAL_SOURCE_STATE(cell,depth,pins)


G.committed=committed;G.finish=finish;G.PREP=PREP;G.case_root=case_root;G.source_state=source_state


def build():
    head=committed();G.need(not PREP.exists(),'exclusive038 build');G.need(shutil.disk_usage(BASE).free>=16*1024**3,'16GiB free disk')
    pins,old,trees=G.imports();pins.update({str(p):G.sha(p) for p in OWN})
    publication=ROOT/'research/lanes/lane-m-gi-competitiveness/results/226-restir-gi-physical-gpu-preparation-failure.json'
    published=G.read(publication);G.need(subprocess.check_output(['git','show','b9f26870:'+str(publication.relative_to(ROOT))],cwd=ROOT)==publication.read_bytes(),'exact stopped037 publication')
    G.need(G.sha(FAILED/'result.json')==published['raw_receipt_sha256'],'original failed build receipt')
    failed=G.read(FAILED/'result.json');G.need(not failed['complete'] and not failed['all_pass'] and not failed['gpu_executed'] and G.inventory(FAILED)==failed['payload_sha256'],'immutable stopped037 inventory')
    for mapping in (failed['input_sha256'],{str(FAILED/k):v for k,v in failed['payload_sha256'].items()}):G.rehash(mapping);pins.update(mapping)
    pins[str(FAILED/'result.json')]=G.sha(FAILED/'result.json');pins[str(publication)]=G.sha(publication)
    dep=Path(published['compiled_dependency_manifest']);G.need(G.sha(dep)==published['compiled_dependency_manifest_sha256'],'actual037 host dependency audit');dependencies=G.read(dep);G.rehash(dependencies);pins.update(dependencies);pins[str(dep)]=G.sha(dep)
    for label in ('host-compile','host-link','producer-compile','producer-validate','producer-disassemble','make-dependencies'):
        terminal=G.read(FAILED/(label+'.process.json'));G.need(terminal['returncode']==0 and terminal['reaped'] and not terminal['timed_out'],'reuse successful037 step only')
    failure=G.read(FAILED/'make-compile.process.json');G.need(failure['returncode']==5 and failure['reaped'] and not failure['timed_out'] and "use of undeclared identifier 'RTXDI_PI'" in (FAILED/'make-compile.stderr').read_text(),'exact correction cause')
    PREP.mkdir();C.write(PREP/'inputs-before.json',dict(source_commit=head,input_sha256=pins))
    r=dict(schema='m001-restir038-include-only-cpu-preparation/1',source_commit=head,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',gpu_executed=False,input_sha256=pins,compiled_dependency_sha256=dependencies,official_source_trees=trees,rows=[],new_host_compilations=0,new_glsl_compilations=0,old_successful_tests_reexecuted=False)
    try:
        r['effective_parent']=C.limits();os.environ.update(VK_ICD_FILENAMES='/038-no-gpu.json',VK_DRIVER_FILES='/038-no-gpu.json')
        os.environ['LD_LIBRARY_PATH']=str(G.S.N.DXC.parent.parent/'lib')+':'+os.environ.get('NIX_LD_LIBRARY_PATH',os.environ.get('LD_LIBRARY_PATH',''))
        for name in ('host.o','host.d','physical-gpu','physical_producer.spv','physical_producer.spvasm','physical_producer.comp.glsl','original_producer.spv'):
            shutil.copyfile(FAILED/name,PREP/name);G.need(G.sha(PREP/name)==failed['payload_sha256'][name],'exact successful037 binary reuse')
        shutil.copymode(FAILED/'physical-gpu',PREP/'physical-gpu')
        source=corrected(G.HLSL.read_bytes());(PREP/G.HLSL.name).write_bytes(source)
        r['include_only_inverse_exact']=True;r['private_hlsl_sha256']=G.sha(PREP/G.HLSL.name)
        rows=[]
        for name,packed in (('make',0),('load',1)):
            stem='physical_'+name
            args=[G.S.N.DXC,PREP/G.HLSL.name,'-T','cs_6_5','-E','main','-spirv','-fspv-target-env=vulkan1.3','-fvk-use-dx-layout','-Od','-WX','-D',f'PACKED={packed}','-I',G.S.LIB/'Include']
            rows.extend([(name+'-dependencies',args+['-Fo',PREP/(stem+'.spv'),'-MD','-MF',PREP/(stem+'.shader.d')]),(name+'-compile',args+['-Fo',PREP/(stem+'.spv')]),(name+'-validate',[G.I.VAL,'--target-env','vulkan1.3',PREP/(stem+'.spv')]),(name+'-disassemble',[G.I.VAL.parent/'spirv-dis',PREP/(stem+'.spv'),'-o',PREP/(stem+'.spvasm')])])
        rows.append(('new-python-contracts',[sys.executable,'-m','unittest','discover','-s',Path(__file__).parent,'-p','test_restir_gi_gpu_bridge.py','-v']))
        for cell,depth in G.M.TARGETS:
            state=G.source_state(cell,depth,pins);rows.append((f'cpu-{cell.lower()}-b{depth}',[PREP/'physical-gpu','--cpu-check','--state',state,'--out',PREP/f'cpu-{cell.lower()}-b{depth}','--vertices',depth,'--shaders',PREP]))
        for label,args in rows:
            print('038',label,'START',flush=True);r['rows'].append(dict(label=label,process=G.guard(args,PREP,label)));print('038',label,'PASS',flush=True)
        for name in ('make','load'):
            asm=(PREP/f'physical_{name}.spvasm').read_text();G.need('OpRayQueryInitializeKHR' in asm and 'OpRayQueryProceedKHR' in asm,'actual real BVH visibility')
            G.need('ArrayStride 128' in asm and 'ArrayStride 32' in asm and 'ArrayStride 16' in asm,'actual candidate/packed/output ABI')
            dependency=(PREP/f'physical_{name}.shader.d').read_text();G.need(all(x in dependency for x in ('Reservoir.hlsli','TypePacking.hlsli','Math.hlsli')),'actual unmodified official SDK/include correction')
        for cell,depth in G.M.TARGETS:
            j=G.read(PREP/f'cpu-{cell.lower()}-b{depth}/complete.json');G.need(j['complete'] and not j['gpu_initialized'] and j['vertices']==depth,'actual unusable-ICD native checks')
        G.rehash(pins);r.update(complete=True,all_pass=True,classification='CPU_GPU_BRIDGE_INCLUDE_CORRECTION_PASS',new_python_contracts=8,new_hlsl_compilations=2,native_cpu_input_checks=6,reused_successful037_steps=5,reused037_executable=True,reused037_physical_producer=True)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return finish(PREP,r)


def case(cell,depth):
    # Only process glue/output roots differ. Native, full model and numerical
    # criteria are the frozen037 functions, not duplicated/repaired versions.
    for p in Path('/proc').iterdir():
        if p.name.isdigit() and int(p.name)!=os.getpid():
            try:name=(p/'exe').readlink().name
            except (FileNotFoundError,PermissionError,ProcessLookupError):continue
            G.need(name!='physical-gpu','another physical bridge native is active')
    # The frozen037 case launches its own audit entry. Use this wrapper entry
    # through an explicit local path override, restoring it after the call.
    original=G.__file__;G.__file__=__file__
    try:return G.case(cell,depth)
    finally:G.__file__=original


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='mode',required=True);sub.add_parser('build')
    p=sub.add_parser('case');p.add_argument('--cell',choices=['H01','H02','H03'],required=True);p.add_argument('--depth',choices=[2,8],type=int,required=True)
    p=sub.add_parser('audit-worker');p.add_argument('--root',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--depth',choices=[2,8],type=int,required=True)
    args=parser.parse_args()
    if args.mode=='build':sys.exit(build())
    elif args.mode=='case':sys.exit(case(args.cell,args.depth))
    else:sys.exit(G.audit_worker(args.root,args.capture,args.depth))

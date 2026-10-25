#!/usr/bin/env python3
"""035 exclusive CPU build/cases. No GPU entry point or current Renderer change."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import anchor_process_limits as C
import restir_gi_device_build as D
import restir_gi_physical_overlay as O
import restir_gi_physical_model as M

ROOT,BASE,B=D.ROOT,D.BASE,D.B
CPP=ROOT/'src/research/lane_m_gi_competitiveness/restir_gi_physical_extract.cpp'
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/035-restir-gi-physical-candidate-semantics.md'
OWN=[CPP,PROTOCOL]+[Path(__file__).with_name(n) for n in ('restir_gi_physical_overlay.py','restir_gi_physical_model.py','restir_gi_physical_process.py','restir_gi_physical_audit.py','test_restir_gi_physical.py')]
BUILD=BASE/'m001-restir035-cpu-build-v1'


def committed():
    head=D.committed();subprocess.run(['git','merge-base','--is-ancestor','5d2efb30',head],check=True)
    for p in OWN:M.need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))])==p.read_bytes(),'commit all035 code before use')
    M.need(subprocess.check_output(['git','show','d5d33d9e:'+str(O.ORIGINAL.relative_to(ROOT))])==O.ORIGINAL.read_bytes(),'immutable original oracle')
    return head


def canonical(cell,depth):
    M.need((cell,depth) in M.TARGETS,'unregistered target');return BASE/f'm001-restir035-{cell.lower()}-b{depth}-v1'


def previous(cell,depth):
    pins={}
    for c,d in M.TARGETS[:M.TARGETS.index((cell,depth))]:
        p=Path(str(canonical(c,d))+'-audit')/'result.json';r=B.read(p)
        M.need(r['complete'] and r['all_pass'] and r['classification']=='CPU_PHYSICAL_CANDIDATE_CASE_PASS','previous full independent audit required')
        M.need(B.SHA(r['native_receipt'])==r['native_receipt_sha256'],'previous native identity');pins[str(p)]=B.SHA(p);pins[r['native_receipt']]=r['native_receipt_sha256']
    B.rehash(pins);return pins


def intake(cell,depth):
    canonical(cell,depth);p=ROOT/'research/lanes/lane-m-gi-competitiveness/results/204-anchor-process-correction-six-target-summary.json'
    M.need(subprocess.check_output(['git','show','6e6fad49:'+str(p.relative_to(ROOT))])==p.read_bytes(),'032 original metadata anchor')
    summary=B.read(p);row=next(x for x in summary['targets'] if (x['cell'],x['depth'])==(cell,depth));pins={str(p):B.SHA(p)}
    npath=Path(row['native_receipt']);M.need(B.SHA(npath)==row['native_receipt_sha256'],'032 native metadata identity');pins[str(npath)]=B.SHA(npath);native=B.read(npath)
    M.need(native['complete'] and native['valid'],'prior physical extraction input valid')
    scenes=[Path(k) for k in native['input_sha256'] if k.endswith('/scene.n008')];M.need(len(scenes)==1,'one exact original scene');scene=scenes[0]
    pins[str(scene)]=native['input_sha256'][str(scene)]
    geometry=Path(row['geometry_directory'])
    for name,want in row['geometry_artifact_sha256'].items():
        q=Path(name);q=q if q.is_absolute() else geometry/q;M.need(B.SHA(q)==want,'frozen physical geometry');pins[str(q)]=want
    B.rehash(pins);return dict(scene=str(scene),geometry=str(geometry)),pins


def build(out):
    head=committed();out=out.resolve();M.need(out in [BASE/f'm001-restir035-cpu-build-v{i}' for i in (1,2,3)] and not out.exists(),'exclusive CPU build')
    for i in range(1,int(out.name[-1])):M.need(not B.read(BASE/f'm001-restir035-cpu-build-v{i}/result.json')['all_pass'],'do not repeat successful preparation')
    compiler=Path(B.read(D.BUILD/'result.json')['commands'][0]['command'][0]);original=O.ORIGINAL.read_bytes();generated,proof=O.overlay(original)
    pins={str(p):B.SHA(p) for p in [*OWN,O.ORIGINAL,compiler,Path(C.__file__),D.BUILD/'result.json']}
    sdkpins,_=D.S.source_pins();pins.update(sdkpins)
    reference=ROOT/'out/external/rtxdi-a6efab96033/Samples/FullSample/Shaders/LightingPasses/ShadeSecondarySurfaces.hlsl'
    M.need('RTXDI_GIReservoir reservoir = RTXDI_EmptyGIReservoir();' in reference.read_text() and 'if (isValidSecondarySurface && !outputShadingResult)' in reference.read_text(),'pinned physical MISS initialization')
    out.mkdir();(out/'restir035_observed.hpp').write_bytes(generated);C.write(out/'observation-inverse.json',proof);C.write(out/'inputs-before.json',dict(source_commit=head,input_sha256=pins))
    r=dict(schema='m001-restir035-cpu-preparation/1',source_commit=head,complete=False,all_pass=False,gpu_executed=False,input_sha256=pins,compiled_dependency_sha256={},commands=[],step_inputs={},old_successful_tests_reexecuted=False)
    os.environ.update(VK_DRIVER_FILES='/035-no-driver.json',VK_ICD_FILENAMES='/035-no-driver.json')
    def command(label,args,outputs,deps):
        args=list(map(str,args));r['step_inputs'][label]=deps
        for i in range(1,int(out.name[-1])):
            old=BASE/f'm001-restir035-cpu-build-v{i}';q=B.read(old/'result.json');rows=[x for x in q['commands'] if x['label']==label]
            if len(rows)!=1 or q['step_inputs'].get(label)!=deps:continue
            if [x.replace(str(old),str(out)) for x in rows[0]['command']]!=args:continue
            for name in [*outputs,label+'.stdout',label+'.stderr']:
                M.need(B.SHA(old/name)==q['payload_sha256'][name],'reusable phase exact');shutil.copy2(old/name,out/name)
            C.write(out/(label+'.reuse.json'),dict(original_receipt=str(old/'result.json'),original_receipt_sha256=B.SHA(old/'result.json'),reexecuted=False))
            r['commands'].append(dict(label=label,command=args,executed=False,reused_from=str(old)));print(label,'REUSED_NO_EXECUTION',flush=True);return
        row=C.guarded(args,out,label,cpu=120,wall=180);r['commands'].append(dict(label=label,executed=True,**row));print(label,'PASS',flush=True)
    try:
        r['effective_parent_limits']=C.limits()
        command('native-compile',[compiler,'-std=c++20','-O2','-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all','-MD','-MF',out/'native.d','-I'+str(out),'-I'+str(O.ORIGINAL.parent),CPP,'-o',out/'physical-extract'],['physical-extract','native.d'],{str(p):pins[str(p)] for p in (compiler,CPP,O.ORIGINAL)}|{'generated_header':proof['generated_sha256']})
        command('new-native-contracts',[out/'physical-extract','--contracts'],[],{'executable':B.SHA(out/'physical-extract')})
        r['new_native_contracts']=B.read(out/'new-native-contracts.stdout');M.need(r['new_native_contracts']['new_path_pairs']==128,'new native path contracts')
        os.environ['RESTIR035_TEST_BUILD']=str(out)
        command('new-python-contracts',[sys.executable,'-m','unittest','discover','-s',Path(__file__).parent,'-p','test_restir_gi_physical.py','-v'],[],{str(p):B.SHA(p) for p in OWN if p.suffix=='.py'})
        stderr=(out/'new-python-contracts.stderr').read_text();match=re.search(r'Ran (\d+) tests?',stderr);M.need(match and '\nOK\n' in stderr,'new Python contracts');r['new_python_contracts']=int(match[1])
        for name in shlex.split((out/'native.d').read_text().replace('\\\n',' '))[1:]:
            p=Path(name);p=p if p.is_absolute() else ROOT/p
            if p.is_file():r['compiled_dependency_sha256'][str(p)]=B.SHA(p)
        B.rehash(pins);B.rehash(r['compiled_dependency_sha256']);r.update(complete=True,all_pass=True,classification='CPU_PHYSICAL_EXTRACTION_PREPARATION_PASS',executable=str(out/'physical-extract'))
    except Exception as e:r.update(error=type(e).__name__+': '+str(e),classification='INVALID_PREPARATION')
    r['payload_sha256']=B.inventory(out);C.write(out/'result.json',r);print(json.dumps({k:r.get(k) for k in ('complete','all_pass','classification','error')}),flush=True);return 0 if r['all_pass'] else 1


def case(cell,depth,build):
    head=committed();root=canonical(cell,depth);M.need(not root.exists(),'exclusive physical case');prior=previous(cell,depth)
    M.need(build in [BASE/f'm001-restir035-cpu-build-v{i}' for i in (1,2,3)],'canonical preparation');pins={};prep=D.pin_inventory(build,pins)
    M.need(prep['classification']=='CPU_PHYSICAL_EXTRACTION_PREPARATION_PASS','successful new CPU preparation');info,old=intake(cell,depth);pins.update(old);pins.update(prior)
    M.need(shutil.disk_usage(BASE).free>=16*1024**3,'16GiB free disk');root.mkdir();C.write(root/'inputs-before.json',dict(source_commit=head,input_sha256=pins,info=info))
    r=dict(schema='m001-restir035-physical-case/1',source_commit=head,cell=cell,depth=depth,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',gpu_executed=False,input_sha256=pins,info=info)
    os.environ.update(VK_DRIVER_FILES='/035-no-driver.json',VK_ICD_FILENAMES='/035-no-driver.json')
    try:
        r['effective_parent_limits']=C.limits();r['process']=C.guarded([prep['executable'],'--scene',info['scene'],'--out',str(root/'paths')],root,'paths',cpu=1200,wall=1800)
        native=B.read(root/'paths/complete.json');M.need(native['complete'] and native['paths_per_role']==230400 and native['vertices']==depth and native['seeds']==list(M.SEEDS),'complete original/observed physical boundary')
        B.rehash(pins);r.update(complete=True,all_pass=True,classification='CPU_PATH_ACQUISITION_COMPLETE_REQUIRES_INDEPENDENT_AUDIT',native=native)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    r['payload_sha256']=B.inventory(root);C.write(root/'result.json',r);print(json.dumps({k:r.get(k) for k in ('complete','classification','error')}),flush=True);return 0 if r['all_pass'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    p=sub.add_parser('build');p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('case');p.add_argument('--cell',choices=['H01','H02','H03'],required=True);p.add_argument('--depth',choices=[2,8],type=int,required=True);p.add_argument('--build',type=Path,required=True)
    args=parser.parse_args();sys.exit(build(args.out) if args.operation=='build' else case(args.cell,args.depth,args.build.resolve()))

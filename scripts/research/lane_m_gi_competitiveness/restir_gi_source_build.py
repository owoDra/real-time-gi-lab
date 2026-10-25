#!/usr/bin/env python3
"""033 actual upstream host API and six shader compile qualifications, no GPU."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import anchor_path_difference_corrected as A
import anchor_process_limits as C
import nrd_source_contract as N
from build_nrd_cpu import VAL

ROOT,BASE,B=A.ROOT,A.BASE,A.B
LIB=ROOT/'out/external/rtxdi-library-f12037fa033'
SAMPLE=ROOT/'out/external/rtxdi-a6efab96033'
PINS={LIB:'f12037fa8e97ebc08e9e3edfd2de528ed1772a4b',SAMPLE:'a6efab966b7c3b272da0461578eb56ac61c7cbff'}
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/033-restir-gi-source-bridge-cpu-qualification.md'
CPP=ROOT/'src/research/lane_m_gi_competitiveness/restir_gi_api_contract.cpp'
HLSL=ROOT/'shaders/research/lane_m_gi_competitiveness/restir_gi_analytic_fixture.hlsl'
OWN=[PROTOCOL,CPP,HLSL]+[Path(__file__).with_name(n) for n in ('restir_gi_source_build.py','restir_gi_source_audit.py','restir_gi_bridge_math.py','test_restir_gi_bridge.py')]
PERMUTATIONS=('make','spatial-basic','spatial-ray','temporal-basic','temporal-ray','fused-ray')


def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()


def committed():
    head=git('rev-parse','HEAD')
    if git('branch','--show-current')!='research-lane-m-gi-competitiveness':raise ValueError('033 branch mismatch')
    subprocess.run(['git','merge-base','--is-ancestor','49e25ed7',head],check=True)
    for p in OWN:
        if subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))])!=p.read_bytes():raise ValueError('033 commit ALL source/contracts before execution')
    return head


def source_pins():
    result={};trees={}
    for folder,commit in PINS.items():
        if git('rev-parse','HEAD',cwd=folder)!=commit or git('status','--porcelain','--untracked-files=no',cwd=folder):raise ValueError('033 dirty or incorrect official source')
        trees[str(folder)]=git('rev-parse','HEAD^{tree}',cwd=folder)
        for entry in subprocess.check_output(['git','ls-tree','-r','-z','HEAD'],cwd=folder).split(b'\0'):
            if not entry:continue
            meta,name=entry.split(b'\t');mode,kind,identity=meta.decode().split()
            if mode=='160000':continue  # Recorded gitlink, not a downloaded dependency.
            path=folder/name.decode()
            if mode not in ('100644','100755') or not path.is_file() or path.is_symlink():raise ValueError('033 unsupported official file')
            data=path.read_bytes()
            import hashlib
            if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=identity:raise ValueError('033 source blob identity')
            result[str(path)]=B.SHA(path)
    link=git('ls-tree','HEAD','Libraries/Rtxdi',cwd=SAMPLE).split()[2]
    if link!=PINS[LIB]:raise ValueError('033 exact sample/library gitlink mismatch')
    return result,trees


def run(out):
    head=committed();out=out.resolve()
    if out not in [BASE/f'm001-restir033-cpu-build-v{i}' for i in (1,2,3)] or out.exists():raise ValueError('033 exclusive canonical attempt')
    for i in range(1,int(out.name[-1])):
        old=B.read(BASE/f'm001-restir033-cpu-build-v{i}/result.json')
        if old['all_pass']:raise ValueError('033 successful preparation cannot be repeated')
    if shutil.disk_usage(BASE).free<16*1024**3:raise ValueError('033 disk guard')
    inputs,trees=source_pins();inputs.update({str(p):B.SHA(p) for p in [*OWN,Path(C.__file__),Path(N.__file__),VAL,VAL.parent/'spirv-dis']})
    oldnative=A.BUILD/'result.json';old=B.read(oldnative)
    if not old['complete'] or not old['all_pass']:raise ValueError('033 qualified compiler source')
    compiler=Path(old['compiler']);inputs[str(compiler)]=B.SHA(compiler)
    if inputs[str(compiler)]!=old['input_sha256'][str(compiler)]:raise ValueError('033 compiler bytes differ')
    oldnrd=BASE/'m001-nrd023-cpu-build-v1/result.json';q=B.read(oldnrd)
    if not q['complete'] or not q['all_pass']:raise ValueError('033 qualified DXC source')
    for p in (N.DXC.parent.parent).rglob('*'):
        if p.is_file():
            inputs[str(p)]=B.SHA(p)
            if q['input_sha256'].get(str(p))!=inputs[str(p)]:raise ValueError('033 DXC executable/library identity')
    inputs[str(oldnative)]=B.SHA(oldnative);inputs[str(oldnrd)]=B.SHA(oldnrd)
    out.mkdir();r=dict(schema='m001-restir033-source-build/1',source_commit=head,complete=False,all_pass=False,
                      classification='INVALID_PREPARATION',gpu_executed=False,sdk_shader_executed=False,
                      sdk_host_executed=False,new_m001_paths=0,new_reference_samples=0,input_sha256=inputs,
                      official_source_commits={str(k):v for k,v in PINS.items()},official_source_trees=trees,
                      commands=[],step_inputs={},compiled_dependency_sha256={},all_six_compiled=False)
    C.write(out/'inputs-before.json',dict(input_sha256=inputs,source_commit=head))
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',VK_ICD_FILENAMES='/033-no-gpu.json',VK_DRIVER_FILES='/033-no-gpu.json')
    env['LD_LIBRARY_PATH']=str(N.DXC.parent.parent/'lib')+':'+os.environ.get('NIX_LD_LIBRARY_PATH',os.environ.get('LD_LIBRARY_PATH',''))
    os.environ.update(env)
    def command(label,args,outputs=(),dependencies=None):
        # A failed step is terminal for this attempt; durable receipts survive.
        args=list(map(str,args));dependencies=dependencies or {}
        r['step_inputs'][label]=dependencies
        C.write(out/(label+'.inputs-before.json'),dict(input_sha256=dependencies))
        for attempt in range(1,int(out.name[-1])):
            previous=BASE/f'm001-restir033-cpu-build-v{attempt}';q=B.read(previous/'result.json')
            rows=[x for x in q['commands'] if x.get('label')==label]
            olddeps=q.get('step_inputs',{}).get(label,{})
            normalized={k.replace(str(previous),str(out)):v for k,v in olddeps.items()}
            if len(rows)!=1 or normalized!=dependencies or not dependencies:continue
            row=rows[0]
            if [x.replace(str(previous),str(out)) for x in row['command']]!=args:continue
            for name in outputs:
                if name.endswith('.d'):
                    for dep in shlex.split((previous/name).read_text().replace('\\\n',' '))[1:]:
                        path=Path(dep);path=path if path.is_absolute() else ROOT/path
                        if path.is_file() and q['compiled_dependency_sha256'].get(str(path))!=B.SHA(path):raise ValueError('033 reusable compiled dependency changed')
            members=[]
            for name in [*outputs,label+'.stdout',label+'.stderr']:
                path=previous/name;members.extend(sorted(path.rglob('*')) if path.is_dir() else [path])
            if any(not p.is_file() or q['payload_sha256'].get(str(p.relative_to(previous)))!=B.SHA(p) for p in members if not p.is_dir()):raise ValueError('033 reusable phase output changed')
            B.rehash(dependencies)
            C.write(out/(label+'.reuse.json'),dict(original_receipt=str(previous/'result.json'),original_receipt_sha256=B.SHA(previous/'result.json'),original_command=row,executed_again=False))
            for name in [*outputs,label+'.stdout',label+'.stderr']:
                source=previous/name;destination=out/name
                if source.is_dir():shutil.copytree(source,destination)
                else:shutil.copy2(source,destination)
            r['commands'].append(dict(label=label,command=args,executed_in_this_attempt=False,reused_from=str(previous)))
            print(label,'REUSED_EXACT_NO_EXECUTION',flush=True);return
        row=C.guarded(args,out,label,cpu=120,wall=180);r['commands'].append(dict(row,label=label,executed_in_this_attempt=True));print(label,'PASS',flush=True)
    try:
        r['effective_parent_limits']=C.limits()
        flags=['-std=c++20','-O2','-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(LIB/'Include')]
        objects=[]
        native_inputs={k:v for k,v in inputs.items() if k.startswith(str(LIB)+'/') or k==str(compiler)}
        for label,path in [('sdk-gi',LIB/'Source/ReSTIRGI.cpp'),('sdk-utils',LIB/'Source/RtxdiUtils.cpp'),('host-contract',CPP)]:
            obj=out/(label+'.o');objects.append(obj)
            deps=dict(native_inputs);deps[str(path)]=B.SHA(path)
            command(label+'-compile',[compiler,*flags,'-MD','-MF',out/(label+'.d'),'-c',path,'-o',obj],(label+'.o',label+'.d'),deps)
        command('host-link',[compiler,*objects,'-fsanitize=undefined','-fno-sanitize-recover=all','-o',out/'host-contract'],('host-contract',),{str(p):B.SHA(p) for p in [compiler,*objects]})
        command('host-execute',[out/'host-contract','--out',out/'host-data'],('host-data',),{str(out/'host-contract'):B.SHA(out/'host-contract')})
        host=B.read(out/'host-execute.stdout')
        if not host['all_pass'] or host['state_count']!=2880:raise ValueError('033 host contracts')
        r.update(sdk_host_executed=True,host_contracts=host)
        command('analytic-tests',[sys.executable,'-m','unittest','discover','-s',Path(__file__).parent,'-p','test_restir_gi_bridge.py','-v'],(),{str(Path(__file__).with_name(n)):B.SHA(Path(__file__).with_name(n)) for n in ('restir_gi_bridge_math.py','test_restir_gi_bridge.py')})
        stderr=(out/'analytic-tests.stderr').read_text();match=re.search(r'Ran (\d+) tests?',stderr)
        if '\nOK\n' not in stderr or not match:raise ValueError('033 analytic contracts')
        r['new_analytic_contracts']=int(match[1])
        shader_inputs={k:v for k,v in inputs.items() if k.startswith(str(LIB)+'/') or k.startswith(str(N.DXC.parent.parent)+'/') or k==str(HLSL)}
        for index,name in enumerate(PERMUTATIONS):
            command(name+'-compile',[N.DXC,HLSL,'-T','cs_6_5','-E','main','-spirv','-fspv-target-env=vulkan1.2','-fvk-use-dx-layout','-Od','-WX','-D',f'PASS={index}','-I',LIB/'Include','-Fo',out/(name+'.spv'),'-MD','-MF',out/(name+'.shader.d')],(name+'.spv',name+'.shader.d'),shader_inputs)
            command(name+'-validate',[VAL,'--target-env','vulkan1.2',out/(name+'.spv')],(),{str(x):B.SHA(x) for x in (VAL,out/(name+'.spv'))})
            command(name+'-disassemble',[VAL.parent/'spirv-dis',out/(name+'.spv'),'-o',out/(name+'.spvasm')],(name+'.spvasm',),{str(x):B.SHA(x) for x in (VAL.parent/'spirv-dis',out/(name+'.spv'))})
        r['all_six_compiled']=True
        for p in out.glob('*.d'):
            for name in shlex.split(p.read_text().replace('\\\n',' '))[1:]:
                path=Path(name);path=path if path.is_absolute() else ROOT/path
                if path.is_file():r['compiled_dependency_sha256'][str(path)]=B.SHA(path)
        # Rehash all immutable inputs after actual execution, before independent audit.
        B.rehash(inputs);B.rehash(r['compiled_dependency_sha256']);again,_=source_pins()
        if any(inputs[k]!=v for k,v in again.items()):raise ValueError('033 source changed during execution')
        from restir_gi_source_audit import inspect
        r['independent_audit']=inspect(out,host)
        r.update(complete=True,all_pass=True,classification='CPU_SOURCE_BRIDGE_COMPILE_PASS')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    for p in out.glob('*.d'):
        for name in shlex.split(p.read_text().replace('\\\n',' '))[1:]:
            path=Path(name);path=path if path.is_absolute() else ROOT/path
            if path.is_file():r['compiled_dependency_sha256'][str(path)]=B.SHA(path)
    r['payload_sha256']=B.inventory(out);C.write(out/'result.json',r)
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=run(a.out);print(json.dumps({k:r[k] for k in ('complete','all_pass','classification','error') if k in r}));sys.exit(0 if r['all_pass'] else 2)

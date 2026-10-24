#!/usr/bin/env python3
"""023 full upstream CPU build, native API probe and guide shader compilation."""
import argparse
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import subprocess
import sys
import nrd_source_contract as S
import build_ddgi_host as D
ROOT=S.ROOT;BASE=ROOT/'out/research/lane-m-gi-competitiveness';SOURCE=ROOT/'src/research/lane_m_gi_competitiveness';SHADERS=ROOT/'shaders/research/lane_m_gi_competitiveness'
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/023-nrd-relax-source-cpu-qualification.md'
OWN=[Path(__file__).resolve(),Path(S.__file__).resolve(),Path(__file__).with_name('test_nrd_cpu.py'),PROTOCOL]+[SOURCE/n for n in ('nrd_api_probe.cpp','nrd_guide_contract.hpp','test_nrd_guide_contract.cpp')]+[SHADERS/'nrd_pack_guides.hlsl']
VAL=Path('/nix/store/z5hs3p3inrq3w8cv71jycz7l4y3ny5xk-spirv-tools-1.4.363.0/bin/spirv-val');GLSLANG=ROOT/'build/n009/_deps/glslang-build/StandAlone/glslang'
sha=S.O.sha


def committed():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for p in OWN:
        if subprocess.check_output(['git','show',commit+':'+str(p.relative_to(ROOT))],cwd=ROOT)!=p.read_bytes():raise ValueError('Commit023builder/API/guide/contracts/tests before execution')
    return commit


def inventory(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'result.json'}


def source_files():
    result={}
    for name,commit in S.PINS.items():
        p=S.EXTERNAL/name
        if subprocess.check_output(['git','rev-parse','HEAD'],cwd=p,text=True).strip()!=commit or subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=p):raise ValueError('023 upstream commit/source dirty')
        result[name]=subprocess.check_output(['git','ls-files','-z'],cwd=p).decode().strip('\0').split('\0')
        if not result[name] or any(not (p/n).is_file() or (p/n).is_symlink() or Path(n).is_absolute() or '..' in Path(n).parts for n in result[name]):raise ValueError('023 unsupported upstream source member')
    return result


def run(work):
    commit=committed();work=work.resolve()
    if not work.is_relative_to(BASE) or work.exists():raise ValueError('023 new exclusive output under out required')
    if sha(S.ARCHIVE)!=S.ARCHIVE_SHA:raise ValueError('023 DXC archive pin differs')
    files=source_files();inputs={str(p):sha(p) for p in OWN+[Path(S.O.__file__),S.O.PT,Path(D.__file__),GLSLANG,VAL,S.ARCHIVE]}
    for name,names in files.items():
        for n in names:inputs[str(S.EXTERNAL/name/n)]=sha(S.EXTERNAL/name/n)
    for p in S.ARCHIVE.parent.rglob('*'):
        if p.is_file():inputs[str(p)]=sha(p)
    original=D.command_rows()['host'];compiler=Path(original[0]).resolve();inputs[str(compiler)]=sha(compiler)
    work.mkdir(parents=True);private=work/'source';private.mkdir()
    for name,names in files.items():
        dst=private/name;dst.mkdir()
        for n in names:
            target=dst/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(S.EXTERNAL/name/n,target)
    for p in OWN:
        if p.suffix in ('.cpp','.hpp','.hlsl'):shutil.copyfile(p,work/p.name)
    (work/'nrd_producer.comp.glsl').write_bytes(S.producer(S.O.PT.read_bytes()))
    build=work/'build';artifacts=work/'artifacts';shaders=artifacts/'shaders';artifacts.mkdir();shaders.mkdir()
    wrapper='''cmake_minimum_required(VERSION 3.30)
project(M001NRD023 LANGUAGES C CXX)
set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "@ARTIFACTS@")
set(SHADERMAKE_FIND_COMPILERS OFF CACHE BOOL "" FORCE)
set(SHADERMAKE_TOOL OFF CACHE BOOL "" FORCE)
add_subdirectory("@MATH@" mathlib)
add_subdirectory("@SM@" shadermake)
set(SHADERMAKE_PATH "$<TARGET_FILE:ShaderMake>;--serial")
set(SHADERMAKE_DXC_VK_PATH "@DXC@")
set(NRD_STATIC_LIBRARY ON CACHE BOOL "" FORCE)
set(NRD_NRI OFF CACHE BOOL "" FORCE)
set(NRD_EMBEDS_SPIRV_SHADERS ON CACHE BOOL "" FORCE)
set(NRD_EMBEDS_DXIL_SHADERS OFF CACHE BOOL "" FORCE)
set(NRD_EMBEDS_DXBC_SHADERS OFF CACHE BOOL "" FORCE)
set(NRD_SHADERS_PATH "@SHADERS@" CACHE STRING "" FORCE)
add_subdirectory("@NRD@" nrd)
'''
    for key,value in dict(ARTIFACTS=artifacts,MATH=private/'MathLib-aa432ad9',SM=private/'ShaderMake-3f01623a',DXC=S.DXC,SHADERS=shaders,NRD=private/'NRD-e06852bd').items():wrapper=wrapper.replace('@'+key+'@',str(value))
    (work/'CMakeLists.txt').write_text(wrapper)
    flags=['-I'+str(work),'-I'+str(SOURCE),'-I'+str(private/'NRD-e06852bd/Include'),'-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all'];rows=[]
    rows.append(('configure',['cmake','-S',str(work),'-B',str(build),'-G','Ninja'],False))
    rows.append(('upstream-serial-build',['cmake','--build',str(build),'--target','NRD','--','-j1'],True))
    for label,name in (('api','nrd_api_probe.cpp'),('contract','test_nrd_guide_contract.cpp')):
        cmd=list(original)
        for flag,value in (('-c',work/name),('-o',work/(label+'.o')),('-MT',work/(label+'.o')),('-MF',work/(label+'.d'))):cmd[cmd.index(flag)+1]=str(value)
        rows.append((label+'-compile',cmd+flags,False))
    rows.append(('api-link',[str(compiler),str(work/'api.o'),str(artifacts/'libNRD.a'),str(build/'shadermake/libShaderMakeBlob.a'),'-pthread','-fsanitize=undefined','-fno-sanitize-recover=all','-o',str(work/'nrd-api-probe')],False))
    rows.append(('contract-link',[str(compiler),str(work/'contract.o'),'-fsanitize=undefined','-fno-sanitize-recover=all','-o',str(work/'nrd-guide-contract')],False))
    rows.append(('pack-guide-compile',[str(S.DXC),str(work/'nrd_pack_guides.hlsl'),'-E','main','-T','cs_6_0','-spirv','-fspv-target-env=vulkan1.2','-WX','-I',str(private/'NRD-e06852bd/Shaders'),'-I',str(private/'MathLib-aa432ad9'),'-Fo',str(work/'nrd_pack_guides.spv')],False))
    rows.append(('pack-guide-validate',[str(VAL),'--target-env','vulkan1.2',str(work/'nrd_pack_guides.spv')],False))
    rows.append(('producer-compile',[str(GLSLANG),'-V','--target-env','vulkan1.3',str(work/'nrd_producer.comp.glsl'),'-o',str(work/'nrd_producer.spv')],False))
    rows.append(('producer-validate',[str(VAL),'--target-env','vulkan1.3',str(work/'nrd_producer.spv')],False))
    result=dict(schema='m001-nrd023-upstream-cpu-build/1',source_commit=commit,complete=False,all_pass=False,gpu_executed=False,sdk_api_executed=False,source_pins=S.PINS,input_sha256=inputs,compiled_dependency_sha256={},rows=[],executable=str(work/'nrd-api-probe'),contract_executable=str(work/'nrd-guide-contract'),sdk_source=str(private/'NRD-e06852bd'))
    env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','LD_LIBRARY_PATH':str(S.DXC.parent.parent/'lib')+':'+os.environ.get('NIX_LD_LIBRARY_PATH',os.environ.get('LD_LIBRARY_PATH',''))}
    for label,cmd,large in rows:
        row=dict(label=label,command=cmd,cwd=str(D.BUILD),pass_=False,cpu_limit=1200 if large else 120,wall_limit=1800 if large else 180)
        def limits():resource.setrlimit(resource.RLIMIT_CPU,(row['cpu_limit'],row['cpu_limit']));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
        try:
            p=subprocess.run(cmd,cwd=D.BUILD,env=env,capture_output=True,timeout=row['wall_limit'],preexec_fn=limits);row.update(returncode=p.returncode,pass_=p.returncode==0)
            for key,data in (('stdout',p.stdout),('stderr',p.stderr)):(work/(label+'.'+key+'.txt')).write_bytes(data)
        except subprocess.TimeoutExpired as e:
            row['error']=str(e)
            for key,data in (('stdout',e.stdout),('stderr',e.stderr)):(work/(label+'.'+key+'.txt')).write_bytes(data or b'')
        result['rows'].append(row);print(label,row.get('returncode'),row['pass_'],flush=True)
        if not row['pass_']:break
    if build.is_dir():
        for label,cmd in (('upstream-commands',['ninja','-C',str(build),'-t','commands','NRD']),('upstream-deps',['ninja','-C',str(build),'-t','deps'])):
            p=subprocess.run(cmd,capture_output=True,text=True);(work/(label+'.txt')).write_text(p.stdout+p.stderr)
            if label=='upstream-deps':
                for line in p.stdout.splitlines():
                    if line.startswith('    '):
                        dep=Path(line.strip());dep=dep if dep.is_absolute() else build/dep
                        if dep.is_file():result['compiled_dependency_sha256'][str(dep)]=sha(dep)
    for p in work.glob('*.d'):
        for name in shlex.split(p.read_text().replace('\\\n',' '))[1:]:
            dep=Path(name);dep=dep if dep.is_absolute() else D.BUILD/dep
            if dep.is_file():result['compiled_dependency_sha256'][str(dep)]=sha(dep)
    unchanged=all(sha(p)==h for p,h in inputs.items());private_exact=all((private/name/n).read_bytes()==(S.EXTERNAL/name/n).read_bytes() for name,names in files.items() for n in names)
    result.update(complete=True,all_pass=len(result['rows'])==len(rows) and all(r['pass_'] for r in result['rows']) and unchanged and private_exact,original_inputs_unchanged=unchanged,upstream_private_tracked_sources_exact=private_exact,payload_sha256=inventory(work))
    with (work/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(all_pass=result['all_pass'],rows=len(result['rows']),payloads=len(result['payload_sha256']),gpu_executed=False)));return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();r=run(a.work);sys.exit(0 if r['all_pass'] else 2)

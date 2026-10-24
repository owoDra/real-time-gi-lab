#!/usr/bin/env python3
"""022 private native/shader CPU compilation; never runs Vulkan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import subprocess
import sys
import integrated_pt_overlay as O
import build_ddgi_host as D
ROOT,BUILD=O.ROOT,D.BUILD
BASE=ROOT/'out/research/lane-m-gi-competitiveness'
SOURCE=ROOT/'src/research/lane_m_gi_competitiveness'
SHADERS=ROOT/'shaders/research/lane_m_gi_competitiveness'
OLD_SPV=BASE/'m001-q019-kernel-cpu-build-v1/surface_quadratic_device.spv'
SPV_SHA='fc29a8d59cb4f1a57c304e1265f36a1f3ff8f1f28d295bf4172d9d5a7d944827'
GLSLANG=BUILD/'_deps/glslang-build/StandAlone/glslang'
VAL=Path('/nix/store/z5hs3p3inrq3w8cv71jycz7l4y3ny5xk-spirv-tools-1.4.363.0/bin/spirv-val')
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/022-integrated-pt-reconstruction-correctness.md'
OWN=[Path(__file__).resolve(),Path(O.__file__).resolve(),Path(__file__).with_name('test_integrated_pt.py'),PROTOCOL]+[SOURCE/n for n in ('integrated_pt_reconstruction.cpp','integrated_state.hpp','integrated_safety.hpp','test_integrated_contract.cpp')]+[SHADERS/'integrated_composite.comp.glsl']


def committed():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for p in OWN:
        if subprocess.check_output(['git','show',commit+':'+str(p.relative_to(ROOT))],cwd=ROOT)!=p.read_bytes():raise ValueError('Commit022 CPU host/build/contracts before execution')
    return commit


def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))


def inventory(root):return {str(p.relative_to(root)):O.sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p.name!='result.json'}


def run(work):
    commit=committed();work=work.resolve()
    if not work.is_relative_to(BASE) or work.exists():raise ValueError('022 new exclusive CPU build under out required')
    if O.sha(OLD_SPV)!=SPV_SHA:raise ValueError('022 unchanged019shader differs')
    # Compute all overlays and exact inverse checks before compilation/output.
    overlays={'integrated_producer.comp.glsl':O.producer(O.PT.read_bytes()),'integrated_b002_vulkan.cpp':O.bounded(O.CONTEXT.read_bytes(),'context'),'integrated_b002_hwrt.cpp':O.bounded(O.HWRT.read_bytes(),'hwrt')}
    original=D.command_rows();cc=original['host'];link=original['link'];oldmain=cc[cc.index('-o')+1]
    replacements={oldmain:'host.o'}
    for fragment,label in (('/generated/n010_b002_vulkan.cpp.o','context.o'),('/lane_b_traversal/b002_hwrt.cpp.o','hwrt.o')):
        found=[x for x in link if x.endswith(fragment)]
        if len(found)!=1:raise ValueError('022 one original link object required')
        replacements[found[0]]=label
    inputs={str(p):O.sha(p) for p in OWN+[O.PT,O.CONTEXT,O.HWRT,OLD_SPV,GLSLANG,VAL,Path(D.LOADER),Path(D.__file__).resolve()]}
    for obj in [x for x in link if x.endswith(('.o','.a'))]:
        p=Path(obj) if Path(obj).is_absolute() else BUILD/obj;inputs[str(p)]=O.sha(p)
        if obj.endswith('.o'):
            raw=subprocess.check_output(['ninja','-C',str(BUILD),'-t','deps',obj],text=True)
            deps=[Path(x.strip()) for x in raw.splitlines() if x.startswith('    ')]
            if not deps:raise ValueError('022 missing reused object dependencies')
            for p in deps:
                if not p.is_absolute():p=BUILD/p
                inputs[str(p)]=O.sha(p)
    inputs[str(Path(cc[0]).resolve())]=O.sha(Path(cc[0]).resolve())
    work.mkdir(parents=True)
    for name,raw in overlays.items():(work/name).write_bytes(raw)
    for p in OWN:
        if p.suffix in ('.cpp','.hpp','.glsl'):(work/p.name).write_bytes(p.read_bytes())
    shutil.copyfile(OLD_SPV,work/'surface_quadratic_device.spv')
    rows=[];flags=['-I'+str(SOURCE),'-I'+str(work),'-I'+str(SHADERS),'-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all']
    for label,src in (('host',work/'integrated_pt_reconstruction.cpp'),('context',work/'integrated_b002_vulkan.cpp'),('hwrt',work/'integrated_b002_hwrt.cpp'),('contract',work/'test_integrated_contract.cpp')):
        args=list(cc)
        for flag,value in (('-c',src),('-o',work/(label+'.o')),('-MT',work/(label+'.o')),('-MF',work/(label+'.d'))):args[args.index(flag)+1]=str(value)
        rows.append((label+'-compile',args+flags))
    native=[str(work/replacements[x]) if x in replacements else '-Wl,--dependency-file='+str(work/'link.d') if x.startswith('-Wl,--dependency-file=') else x for x in link]
    native[native.index('-o')+1]=str(work/'integrated-pt');native += [str(D.LOADER),'-pthread','-fsanitize=undefined','-fno-sanitize-recover=all'];rows.append(('host-link',native))
    # Contract calls shared scalar/safety code, not Vulkan; retain original
    # include path through its object and link loader only for ledger ABI.
    rows.append(('contract-link',[cc[0],str(work/'contract.o'),'-o',str(work/'integrated-contract'),str(D.LOADER),'-pthread','-fsanitize=undefined','-fno-sanitize-recover=all']))
    for name in ('producer','composite'):
        src=work/('integrated_'+name+('.comp.glsl' if name=='producer' else '.comp.glsl'))
        dst=work/('integrated_'+name+'.spv')
        rows.append((name+'-compile',[str(GLSLANG),'-V','--target-env','vulkan1.3',str(src),'-o',str(dst)]));rows.append((name+'-validate',[str(VAL),'--target-env','vulkan1.3',str(dst)]))
    rows.append(('unchanged-quadratic-validate',[str(VAL),'--target-env','vulkan1.3',str(work/'surface_quadratic_device.spv')]))
    result=dict(schema='m001-integrated022-private-cpu-build/1',source_commit=commit,complete=False,all_pass=False,gpu_executed=False,host_executed=False,overlay_inverse_exact=True,rows=[],input_sha256=inputs,compiled_dependency_sha256={})
    for label,cmd in rows:
        row=dict(label=label,command=cmd,cwd=str(BUILD),pass_=False)
        try:
            p=subprocess.run(cmd,cwd=BUILD,capture_output=True,timeout=180,preexec_fn=limits,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
            for name,data in (('stdout',p.stdout),('stderr',p.stderr)):(work/(label+'.'+name+'.txt')).write_bytes(data)
            row.update(returncode=p.returncode,pass_=p.returncode==0)
        except subprocess.TimeoutExpired as e:
            row['error']=str(e)
            for name,data in (('stdout',e.stdout),('stderr',e.stderr)):(work/(label+'.'+name+'.txt')).write_bytes(data or b'')
        result['rows'].append(row);print(label,row.get('returncode'),row['pass_'],flush=True)
        if not row['pass_']:break
    for dep in work.glob('*.d'):
        if dep.name=='link.d':continue
        for word in shlex.split(dep.read_text().replace('\\\n',' '))[1:]:
            p=Path(word);p=p if p.is_absolute() else BUILD/p
            if p.is_file():result['compiled_dependency_sha256'][str(p)]=O.sha(p)
    unchanged=all(O.sha(p)==h for p,h in inputs.items())
    result.update(complete=True,all_pass=unchanged and len(result['rows'])==len(rows) and all(r['pass_'] for r in result['rows']),inputs_unchanged=unchanged,payload_sha256=inventory(work),executable=str(work/'integrated-pt'),shader_directory=str(work),contract_executable=str(work/'integrated-contract'))
    with (work/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();r=run(a.work);print(json.dumps(dict(all_pass=r['all_pass'],work=str(a.work),gpu_executed=False)));sys.exit(0 if r['all_pass'] else 2)

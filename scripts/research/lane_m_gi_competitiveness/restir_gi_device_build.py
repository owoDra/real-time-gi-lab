#!/usr/bin/env python3
"""034 CPU preparation, exact033 object/SPIR-V reuse, no Vulkan initialization."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import restir_gi_source_build as S
import anchor_process_limits as C
import restir_gi_device_model as M

ROOT,BASE,B=S.ROOT,S.BASE,S.B
OLD=BASE/'m001-restir033-cpu-build-v3'
CPP=ROOT/'src/research/lane_m_gi_competitiveness/restir_gi_device_controls.cpp'
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/034-restir-gi-analytic-device-controls.md'
OWN=[CPP,PROTOCOL]+[Path(__file__).with_name(n) for n in ('restir_gi_device_build.py','restir_gi_device_model.py','restir_gi_device_process.py','restir_gi_device_audit.py','test_restir_gi_device.py')]
HEADERS=ROOT/'build/n007/_deps/vulkan-headers-for-vk-bootstrap-src/include'
LOADER=Path('/run/current-system/sw/share/nix-ld/lib/libvulkan.so')
LEDGER=ROOT/'src/research/n010_comparison_readiness/allocation_ledger.hpp'
BUILD=BASE/'m001-restir034-cpu-build-v1'


def committed():
    head=S.committed();subprocess.run(['git','merge-base','--is-ancestor','5080ffd5',head],check=True)
    for p in OWN:
        M.need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))])==p.read_bytes(),'commit all034 code before use')
    return head


def pin_inventory(root,inputs):
    receipt=root/'result.json';r=B.read(receipt);inputs[str(receipt)]=B.SHA(receipt)
    M.need(r['complete'] and r['all_pass'],'prior successful preparation')
    for k,v in r['payload_sha256'].items():
        p=root/k;M.need(B.SHA(p)==v,'prior full payload changed');inputs[str(p)]=v
    for key in ('input_sha256','compiled_dependency_sha256'):
        B.rehash(r.get(key,{}));inputs.update(r.get(key,{}))
    return r


def intake():
    inputs,trees=S.source_pins();old=pin_inventory(OLD,inputs)
    for number in (207,210):
        p=next((ROOT/'research/lanes/lane-m-gi-competitiveness/results').glob(str(number)+'-*.json'))
        M.need(subprocess.check_output(['git','show','f8f35862:'+str(p.relative_to(ROOT))])==p.read_bytes(),'published033 identity');inputs[str(p)]=B.SHA(p)
    M.need(old['all_six_compiled'] and old['classification']=='CPU_SOURCE_BRIDGE_COMPILE_PASS','six qualified real shaders')
    # Check exact layouts from the ALREADY QUALIFIED disassembly; no compiler/SDK test reruns.
    for name in S.PERMUTATIONS:
        asm=(OLD/(name+'.spvasm')).read_text()
        offsets=[int(x) for x in re.findall(r'OpMemberDecorate %type_Controls \d+ Offset (\d+)',asm)]
        M.need(offsets==[0,4,8,12,16,32,48,64,76],'Controls SPIR-V offsets')
        M.need('ArrayStride 32' in asm and 'ArrayStride 48' in asm,'packed/surface SPIR-V strides')
    return inputs,trees


def run(out):
    head=committed();out=out.resolve()
    M.need(out in [BASE/f'm001-restir034-cpu-build-v{i}' for i in (1,2,3)] and not out.exists(),'exclusive registered CPU attempt')
    for i in range(1,int(out.name[-1])):M.need(not B.read(BASE/f'm001-restir034-cpu-build-v{i}/result.json')['all_pass'],'do not repeat successful build')
    M.need(shutil.disk_usage(BASE).free>=16*1024**3,'disk guard')
    inputs,trees=intake();compiler=Path(B.read(S.A.BUILD/'result.json')['compiler'])
    for p in [*OWN,compiler,LEDGER,LOADER,Path(C.__file__),Path(sys.executable)]:inputs[str(p)]=B.SHA(p)
    for p in HEADERS.rglob('*'):
        if p.is_file():inputs[str(p)]=B.SHA(p)
    out.mkdir();C.write(out/'inputs-before.json',dict(source_commit=head,input_sha256=inputs))
    r=dict(schema='m001-restir034-cpu-preparation/1',source_commit=head,complete=False,all_pass=False,
           gpu_executed=False,shader_compiles=0,sdk_host_reexecutions=0,old_tests_reexecuted=0,
           input_sha256=inputs,compiled_dependency_sha256={},commands=[],official_source_trees=trees)
    os.environ.update(VK_ICD_FILENAMES='/034-no-driver.json',VK_DRIVER_FILES='/034-no-driver.json')
    def command(label,args):
        row=C.guarded(list(map(str,args)),out,label,cpu=120,wall=180);r['commands'].append(dict(label=label,**row));print(label,'PASS',flush=True)
    try:
        r['effective_parent_limits']=C.limits()
        fixtures=[]
        for w,h in M.DIMENSIONS:
            folder=out/f'inputs-{w}x{h}';info=M.build_fixtures(folder,w,h,(OLD/'host-data/neighbor-offsets.u8').read_bytes());fixtures.append(dict(path=str(folder),**info))
        r['fixtures']=fixtures
        flags=['-std=c++20','-O2','-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(S.LIB/'Include'),'-I'+str(HEADERS),'-I'+str(LEDGER.parent)]
        command('host-compile',[compiler,*flags,'-MD','-MF',out/'host.d','-c',CPP,'-o',out/'host.o'])
        for dep in shlex.split((out/'host.d').read_text().replace('\\\n',' '))[1:]:
            p=Path(dep);p=p if p.is_absolute() else ROOT/p
            if p.is_file():r['compiled_dependency_sha256'][str(p)]=B.SHA(p)
        command('host-link',[compiler,out/'host.o',OLD/'sdk-gi.o',OLD/'sdk-utils.o',LOADER,'-fsanitize=undefined','-fno-sanitize-recover=all','-pthread','-o',out/'device-controls'])
        for f in fixtures:
            command(f"native-cpu-{f['width']}x{f['height']}",[out/'device-controls','--cpu-check','--input',f['path'],'--out',out/f"cpu-{f['width']}x{f['height']}",'--shaders',OLD])
            q=B.read(out/f"cpu-{f['width']}x{f['height']}/complete.json")
            M.need(q['complete'] and not q['gpu_initialized'] and q['reservoir_array_pitch']==f['pitch'],'CPU-only native identity')
        os.environ.update(RESTIR034_TEST_BUILD=str(out))
        command('new-cpu-tests',[sys.executable,'-m','unittest','discover','-s',Path(__file__).parent,'-p','test_restir_gi_device.py','-v'])
        stderr=(out/'new-cpu-tests.stderr').read_text();match=re.search(r'Ran (\d+) tests?',stderr)
        M.need(match is not None and '\nOK\n' in stderr,'new CPU contracts')
        r['new_cpu_contracts']=int(match[1]);r['executable']=str(out/'device-controls');r['shader_directory']=str(OLD)
        B.rehash(inputs);B.rehash(r['compiled_dependency_sha256']);again,_=intake();M.need(all(inputs[k]==v for k,v in again.items()),'CPU intake changed')
        r.update(complete=True,all_pass=True,classification='CPU_DEVICE_CONTROL_PREPARATION_PASS')
    except Exception as e:r.update(error=type(e).__name__+': '+str(e),classification='INVALID_PREPARATION')
    r['payload_sha256']=B.inventory(out);C.write(out/'result.json',r)
    print(json.dumps({k:r.get(k) for k in ('complete','all_pass','classification','error')}),flush=True)
    return 0 if r['all_pass'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();sys.exit(run(args.out))

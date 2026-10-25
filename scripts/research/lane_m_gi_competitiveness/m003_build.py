#!/usr/bin/env python3
"""050/M003 private build: the 049 sequence harness and the 022 bounded context/HWRT overlay
sources, recompiled with a private safety header whose only change is the process wall guard
(180 s -> 1800 s, needed by 192-frame Sponza sequences). Byte-identical source copies are placed
next to the private header so that quoted includes resolve to it; every input is hashed."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'out/research/lane-m-gi-competitiveness'
OLD022=BASE/'m001-integrated022-cpu-build-v1'
SRC=ROOT/'src/research/lane_m_gi_competitiveness'
SHADER=ROOT/'shaders/research/lane_m_gi_competitiveness/rtcv_sequence.comp.glsl'
GLSLANG=ROOT/'build/n009/_deps/glslang-build/StandAlone/glslang'
VAL=Path('/nix/store/z5hs3p3inrq3w8cv71jycz7l4y3ny5xk-spirv-tools-1.4.363.0/bin/spirv-val')
ROLES=range(6)
GUARD_OLD='Clock::now()-safety_started).count()<180,'
GUARD_NEW='Clock::now()-safety_started).count()<1800,'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(out):
    out=Path(out).resolve();assert not out.exists();out.mkdir(parents=True);rec=dict(schema='m003-build/1',inputs={},rows=[])
    safety=(SRC/'integrated_safety.hpp').read_text();assert safety.count(GUARD_OLD)==1
    (out/'integrated_safety.hpp').write_text(safety.replace(GUARD_OLD,GUARD_NEW))
    for src in (SRC/'rtcv_sequence_gpu.cpp',OLD022/'integrated_b002_vulkan.cpp',OLD022/'integrated_b002_hwrt.cpp',SRC/'integrated_safety.hpp',SHADER,OLD022/'surface_quadratic_device.spv'):
        rec['inputs'][str(src)]=sha(src)
    for name in ('rtcv_sequence_gpu.cpp','integrated_b002_vulkan.cpp','integrated_b002_hwrt.cpp'):
        src=(SRC if name.startswith('rtcv') else OLD022)/name;(out/name).write_bytes(src.read_bytes());assert sha(out/name)==sha(src)
    (out/'surface_quadratic_device.spv').write_bytes((OLD022/'surface_quadratic_device.spv').read_bytes())
    inc=[f'-I{ROOT}/src/research/n010_comparison_readiness',f'-I{ROOT}/src',f'-I{ROOT}/src/research/lane_n_end_to_end_renderer/imported/lane_a_split_rc',
         f'-I{ROOT}/src/research/lane_n_end_to_end_renderer/imported/lane_b_traversal',f'-I{ROOT}/src/research/lane_n_end_to_end_renderer/imported/integration',
         f'-I{ROOT}/build/n007/_deps/vk_bootstrap-src/src',f'-I{ROOT}/build/n007/_deps/vulkan-headers-for-vk-bootstrap-src/include']
    flags=['-O3','-DNDEBUG','-std=c++20','-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all']
    cmds=[]
    for name,obj in (('integrated_b002_vulkan.cpp','context.o'),('integrated_b002_hwrt.cpp','hwrt.o'),('rtcv_sequence_gpu.cpp','host.o')):
        cmds.append((obj,['c++',f'-DPHOS_GI_INTEGRATION_SHADER_DIR="{ROOT}/build/n009/shaders"',*inc,*flags,'-I',str(out),f'-I{SRC}',f'-I{OLD022}','-o',str(out/obj),'-c',str(out/name)]))
    b=ROOT/'build/n009'
    cmds.append(('link',['c++','-O3','-DNDEBUG',str(out/'host.o'),str(out/'context.o'),str(b/'src/research/n010_comparison_readiness/CMakeFiles/phos-n010-pixel-pt.dir/__/lane_n_end_to_end_renderer/imported/lane_b_traversal/b002_compute.cpp.o'),
                     str(out/'hwrt.o'),str(b/'src/research/n010_comparison_readiness/CMakeFiles/phos-n010-pixel-pt.dir/__/lane_n_end_to_end_renderer/imported/integration/i001_compute.cpp.o'),
                     '-o',str(out/'rtcv-sequence'),str(b/'_deps/vk_bootstrap-build/libvk-bootstrap.a'),'-ldl','/run/current-system/sw/share/nix-ld/lib/libvulkan.so','-pthread','-fsanitize=undefined','-fno-sanitize-recover=all']))
    for r in ROLES:
        cmds.append((f'role{r}',[str(GLSLANG),'-V','--target-env','vulkan1.3',f'-DROLE={r}',str(SHADER),'-o',str(out/f'rtcv_role{r}.spv')]))
        cmds.append((f'validate{r}',[str(VAL),'--target-env','vulkan1.3',str(out/f'rtcv_role{r}.spv')]))
    for label,cmd in cmds:
        p=subprocess.run(cmd,cwd=b,capture_output=True,text=True);rec['rows'].append(dict(label=label,command=cmd,returncode=p.returncode,stderr=p.stderr[-2000:]))
        if p.returncode!=0:break
    rec['all_pass']=all(r['returncode']==0 for r in rec['rows']) and len(rec['rows'])==len(cmds)
    rec['outputs']={f.name:sha(f) for f in sorted(out.iterdir()) if f.is_file()}
    (out/'result.json').write_text(json.dumps(rec,indent=1)+'\n');return rec


if __name__=='__main__':
    r=build(sys.argv[1]);print(r['all_pass'])

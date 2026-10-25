#!/usr/bin/env python3
"""046/M002 CPU-only heldout geometry, exported states and locked reference qualification."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'out/research/lane-m-gi-competitiveness'
OUT=BASE/'m002-states-v1';REFS=BASE/'m002-references-v1'
FACTORY=ROOT/'scripts/research/lane_n_end_to_end_renderer/n004_scene_factory.py'
EXPORTER=ROOT/'build/n009/src/research/n009_scene_contract/n009_state_export'
CONTRACT=ROOT/'out/research/n010-comparison-readiness/light-selection-v1/sponza-local-motion.n009contract'
VALIDATION=ROOT/'research/lanes/n010-comparison-readiness/results/009-iid-precision-confirmation.json'
H01=dict(geometry='f8b25b1c20ad84b6b9b030a2edd12c4a812af7199e21002897be9cf974ad75ca',frame='70745baa8ebeabe9ffe20a8ba284261bfc7ea060eda1d318bc2ad338f1b8e7e4')
SCENES={'S1':('leak','thin',0.071),'S2':('leak','one-sided',None),'S3':('world','sparse',None),'S4':('world','large-horizontal',None)}
CELLS={'S1':('S1','static'),'S2':('S2','static'),'S3':('S3','static'),'S4':('S4','static'),
       'S1C':('S1','camera-motion'),'S1L':('S1','light-motion'),'S3C':('S3','camera-motion'),'S3L':('S3','light-motion')}


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,why):
    if not ok:raise ValueError('046 '+why)


def factory():
    spec=importlib.util.spec_from_file_location('m002_factory',FACTORY);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def export(gltf,out,regime):
    env=dict(os.environ,PHOS_N009_CONTRACT=str(CONTRACT))
    run=subprocess.run([str(EXPORTER),'--scene',str(gltf),'--out',str(out),'--regime',regime,'--frame-id','1'],env=env,capture_output=True,text=True,timeout=120)
    need(run.returncode==0,'state exporter '+run.stderr[-200:]);info=json.loads(run.stdout.strip().splitlines()[-1])
    return info


def states():
    need(not OUT.exists(),'exclusive M002 states');OUT.mkdir();m=factory();g=OUT/'gltf'
    check=OUT/'h01-reproduction';export(m.write_gltf(g,'M001-H01',m.leak_scene('medium',0.137)),check,'static')
    got=dict(geometry=sha(check/'geometry-state.bin'),frame=sha(check/'frame-state.bin'));need(got==H01,'exporter reproduces M001 H01 bytes')
    manifest=dict(schema='m002-states/1',factory_sha256=sha(FACTORY),exporter_sha256=sha(EXPORTER),contract_sha256=sha(CONTRACT),h01_reproduction=got,scenes={},cells={})
    for name,(family,kind,thickness) in SCENES.items():
        groups=m.leak_scene(kind,thickness) if family=='leak' and thickness is not None else m.leak_scene(kind) if family=='leak' else m.world_scene(kind)
        gltf=m.write_gltf(g,'M002-'+name,groups);manifest['scenes'][name]=dict(family=family,kind=kind,thickness=thickness,gltf_sha256=sha(gltf),bin_sha256=sha(g/f'M002-{name}.bin'))
    for cell,(scene,regime) in CELLS.items():
        out=OUT/cell;info=export(g/f'M002-{scene}.gltf',out,regime);count=int.from_bytes((out/'geometry-state.bin').read_bytes()[4:8],'little')
        need(count<=2048,'triangle cap for M002 harness')
        manifest['cells'][cell]=dict(scene=scene,regime=regime,triangles=count,exporter=info,geometry_sha256=sha(out/'geometry-state.bin'),frame_sha256=sha(out/'frame-state.bin'))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({c:(v['triangles'],v['regime']) for c,v in manifest['cells'].items()}))


def lock():
    sys.path.insert(0,str(ROOT/'scripts/research/n008_hdr_oracle'));import n008lib as L
    cells={c:dict(state_directory=str((OUT/c).relative_to(ROOT)),state_sha256=L.read_state(OUT/c)['sha256']) for c in CELLS}
    p=OUT/'lock.json';need(not p.exists(),'exclusive lock');p.write_text(json.dumps(dict(cells=cells),indent=2)+'\n');return p


def qualify(cell):
    work=REFS;work.mkdir(exist_ok=True);out=work/f'{cell}-result.json';need(not out.exists(),'one qualification per cell')
    run=subprocess.run([sys.executable,str(ROOT/'scripts/research/n010_comparison_readiness/qualify_references.py'),'--lock',str(OUT/'lock.json'),'--validation',str(VALIDATION),'--cells',cell,'--work',str(work),'--output',str(out)],capture_output=True,text=True)
    (work/f'{cell}-qualify.log').write_text(run.stdout+run.stderr);need(run.returncode==0,'qualification '+cell)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['states','lock','qualify']);ap.add_argument('--cell');a=ap.parse_args()
    if a.mode=='states':states()
    elif a.mode=='lock':print(lock())
    else:qualify(a.cell)

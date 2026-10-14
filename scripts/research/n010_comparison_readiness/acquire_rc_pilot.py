#!/usr/bin/env python3
"""Retained N010 RC/direct/topology pilot; no accepted timing claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    binary=ROOT/'build/n009/phos-n010-capture'
    sponza=ROOT/'assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf'
    control=ROOT/'out/research/n008-hdr-oracle/phase-b-states/n004-scenes/leak-medium.gltf'
    contract=ROOT/'research/lanes/n009-scene-contract/contract/sponza-c1.n009contract'
    result={'schema':'n010-rc-correctness-pilot/1','complete':False,'rows':[]}
    for cell,scene,scenario,topology in [('C7',control,'static',False),('C1',sponza,'static',False),('C6',sponza,'deforming-control',True)]:
        for backend in (('hwrt','vanilla') if topology else ('hwrt','software','vanilla')):
            out=(a.work/f'{cell}-{backend}').resolve()
            if out.exists():raise ValueError('refuse to overwrite capture '+str(out))
            env=os.environ.copy()
            env['PHOS_N009_CONTRACT']=str(contract)
            env['PHOS_N010_MEMORY_LEDGER']=str(out/'allocation-ledger.json')
            cmd=['bash','scripts/run_with_vulkan.sh',str(binary),'--scene',str(scene),'--scenario',scenario,
                 '--backend',backend,'--direct-profile','ulp4','--target-state','--out',str(out)]
            if topology:cmd.append('--topology-churn')
            proc=subprocess.run(cmd,env=env,text=True,capture_output=True)
            row={'cell':cell,'backend':backend,'profile':'ulp4','source_commit':source,
                 'binary_sha256':sha(binary),'command':cmd,'contract_sha256':sha(contract),
                 'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,
                 'payload_sha256':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}
            result['rows'].append(row)
            a.output.write_text(json.dumps(result,indent=2)+'\n')
            print(cell,backend,proc.returncode,flush=True)
            if proc.returncode:raise SystemExit('failed capture retained')
    result['complete']=True
    a.output.write_text(json.dumps(result,indent=2)+'\n')

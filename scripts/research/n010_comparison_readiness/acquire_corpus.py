#!/usr/bin/env python3
"""Acquire preregistered additional source/target regimes and freeze states."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from acquire_rc_pilot import ROOT,sha
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    binary=ROOT/'build/n009/phos-n010-capture'
    sponza=ROOT/'assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf'
    control=ROOT/'out/research/n008-hdr-oracle/phase-b-states/n004-scenes/leak-medium.gltf'
    contract=ROOT/'out/research/n010-comparison-readiness/light-selection-v1/sponza-local-motion.n009contract'
    result={'schema':'n010-additional-corpus/1','complete':False,'rows':[]}
    scenarios=[('C3',sponza,'light-motion',False),('C8',control,'camera-motion',False),
               ('C9',control,'light-motion',False),('C10',control,'moving-rigid',False),
               ('C11',control,'deforming-control',False),('C12',control,'deforming-control',True)]
    for cell,scene,scenario,topology in scenarios:
        for backend in ('hwrt','vanilla'):
            for target in (False,True):
                out=(a.work / f'{cell}-{backend}-' / ('target' if target else 'source')).resolve()
                if out.exists():raise ValueError('refuse to overwrite '+str(out))
                env=os.environ.copy();env['PHOS_N009_CONTRACT']=str(contract)
                env['PHOS_N010_MEMORY_LEDGER']=str(out/'allocation-ledger.json')
                cmd=['bash','scripts/run_with_vulkan.sh',str(binary),'--scene',str(scene),'--scenario',scenario,
                     '--backend',backend,'--direct-profile','ulp4','--out',str(out)]
                if target:cmd.append('--target-state')
                if target and topology:cmd.append('--topology-churn')
                proc=subprocess.run(cmd,env=env,text=True,capture_output=True)
                row={'cell':cell,'backend':backend,'target':target,'scenario':scenario,'topology':topology,
                     'capture_directory':str(out.relative_to(ROOT)), 'profile':'ulp4','source_commit':source,
                     'binary_sha256':sha(binary),'command':cmd,'contract_sha256':sha(contract),
                     'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,
                     'payload_sha256':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}
                result['rows'].append(row)
                a.output.write_text(json.dumps(result,indent=2)+'\n')
                print(cell,backend,target,proc.returncode,flush=True)
                if proc.returncode:raise SystemExit('failed corpus acquisition retained')
    result['complete']=True
    a.output.write_text(json.dumps(result,indent=2)+'\n')

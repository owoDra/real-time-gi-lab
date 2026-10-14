#!/usr/bin/env python3
"""N010 complete source/target/recovery cohort with all-frame HDR scoring."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from acquire_rc_pilot import ROOT,sha
from score_hdr import score

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cells',nargs='+',required=True)
    ap.add_argument('--lock',type=Path,required=True)
    ap.add_argument('--references',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--roles',nargs='+',choices=['incumbent-hwrt','incumbent-software','vanilla-traversal','pixel-pt-B2','pixel-pt-B8','dense-rc'])
    ap.add_argument('--pt-spp-b2',type=int,choices=[1,4,16,64,256,1024],default=256)
    ap.add_argument('--pt-spp-b8',type=int,choices=[1,4,16,64,256,1024],default=1024)
    a=ap.parse_args()
    lock=json.loads(a.lock.read_text())
    source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    contract=ROOT/'out/research/n010-comparison-readiness/light-selection-v1/sponza-local-motion.n009contract'
    result={'schema':'n010-dynamic-cohort-pilot/1','complete':False,'lock_sha256':sha(a.lock),
            'selected_roles':a.roles,'pt_spp_b2':a.pt_spp_b2,'pt_spp_b8':a.pt_spp_b8,'rows':[]}
    for cell in a.cells:
        spec=lock['cells'][cell]
        if 'source_directory' not in spec:raise ValueError('missing source transition state')
        state=ROOT/spec['source_directory'];target=ROOT/spec['state_directory']
        base='C1' if cell in ('C2','C3','C4','C5','C6') else 'C7'
        for vertices in (2,8):
            ref_source=a.references/f'{base}_T_B{vertices}';ref_target=a.references/f'{cell}_T_B{vertices}'
            qualification=[json.loads((p/'qualification.json').read_text()) for p in (ref_source,ref_target)]
            if any(q['classification']!='STATISTICALLY_ELIGIBLE' for q in qualification):raise ValueError('reference not eligible')
        roles=['incumbent-hwrt','vanilla-traversal','pixel-pt-B2','pixel-pt-B8','dense-rc']
        if cell not in ('C6','C12'):roles.insert(1,'incumbent-software')
        elif a.roles is None or 'incumbent-software' in a.roles:result['rows'].append({'cell':cell,'role':'incumbent-software','classification':'UNSUPPORTED_IN_CAPTURE_API','reason':'N002 integrated churn entry point is HWRT-only; no software topology result inferred'})
        if a.roles:
            roles=[role for role in roles if role in a.roles]
        for role in roles:
            out=(a.work/f'{cell}-{role}').resolve()
            if out.exists():raise ValueError('refuse to overwrite '+str(out))
            env=os.environ.copy();env['PHOS_N009_CONTRACT']=str(contract)
            if role.startswith('incumbent') or role=='vanilla-traversal':
                binary=ROOT/'build/n009/phos-n010-capture'
                backend='hwrt' if role=='incumbent-hwrt' else ('software' if role=='incumbent-software' else 'vanilla')
                scene=ROOT/('assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf' if base=='C1' else 'out/research/n008-hdr-oracle/phase-b-states/n004-scenes/leak-medium.gltf')
                cmd=['bash','scripts/run_with_vulkan.sh',str(binary),'--scene',str(scene),'--scenario',spec['scenario'],
                     '--backend',backend,'--direct-profile','ulp4','--target-state','--recovery-frames','3','--out',str(out)]
                if cell in ('C6','C12'):cmd.append('--topology-churn')
                env['PHOS_N010_MEMORY_LEDGER']=str(out/'allocation-ledger.json')
            else:
                binary=ROOT/'build/n009/phos-n010-pixel-pt'
                vertices=8 if role=='pixel-pt-B8' else 2
                spp=1 if role=='dense-rc' else (a.pt_spp_b8 if vertices==8 else a.pt_spp_b2)
                cmd=['bash','scripts/run_with_vulkan.sh',str(binary),'--state',str(state),'--target-state',str(target),
                     '--family','dense-rc' if role=='dense-rc' else 'pixel-pt','--spp',str(spp),'--vertices',str(vertices),
                     '--seed','305419896','--frames','5','--out',str(out)]
            proc=subprocess.run(cmd,env=env,text=True,capture_output=True)
            evidence={'cell':cell,'role':role,'source_commit':source,'binary_sha256':sha(binary),'command':cmd,
                      'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'scores':[]}
            if proc.returncode==0:
                for f in range(5):
                    frame_dir=out/'frames'/str(f)
                    for vertices in ([2] if role=='pixel-pt-B2' else ([8] if role=='pixel-pt-B8' else [2,8])):
                        ref=(a.references/f'{base if f==0 else cell}_T_B{vertices}')
                        qpath=ref/'qualification.json';q=json.loads(qpath.read_text())
                        score_path=frame_dir/f'quality-B{vertices}.json'
                        scored=score(frame_dir,q,ref,score_path)
                        scored.update(frame_index=f,role=role,qualification_sha256=sha(qpath))
                        score_path.write_text(json.dumps(scored,indent=2)+'\n')
                        evidence['scores'].append(scored)
                ledger=out/'allocation-ledger.json'
                evidence['ledger_sha256']=sha(ledger)
                evidence['memory']=json.loads(ledger.read_text())
                timing=out/('frames.json' if (out/'frames.json').exists() else 'renderer-timings.jsonl')
                evidence['timing_sha256']=sha(timing)
                evidence['timings']=json.loads(timing.read_text()) if timing.suffix=='.json' else [json.loads(line) for line in timing.read_text().splitlines()]
            evidence['payload_sha256']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
            result['rows'].append(evidence)
            a.output.write_text(json.dumps(result,indent=2)+'\n')
            print(cell,role,proc.returncode,flush=True)
            if proc.returncode:raise SystemExit('failed sequence retained')
    result['complete']=True
    a.output.write_text(json.dumps(result,indent=2)+'\n')

#!/usr/bin/env python3
"""Acquire all fixed N010 pixel-PT budget levels and score eligible references."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from score_hdr import score
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cell',required=True)
    ap.add_argument('--vertices',type=int,nargs='+',choices=(2,8),default=[2,8])
    ap.add_argument('--state',type=Path,required=True)
    ap.add_argument('--references',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    binary=ROOT/'build/n009/phos-n010-pixel-pt'
    source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    result={'schema':'n010-pt-cohort-pilot/1','complete':False,'cell':a.cell,'selected_vertices':a.vertices,'full_two_transport_ladder':set(a.vertices)=={2,8},'rows':[]}
    for vertices in a.vertices:
        ref=a.references/f'{a.cell}_T_B{vertices}'
        qfile=ref/'qualification.json'
        row=json.loads(qfile.read_text())
        if row['classification']!='STATISTICALLY_ELIGIBLE':raise ValueError('reference not eligible')
        for spp in (1,4,16,64,256,1024):
            out=(a.work/f'{a.cell}_B{vertices}_n{spp}').resolve()
            cmd=['bash','scripts/run_with_vulkan.sh',str(binary),'--state',str(a.state),'--out',str(out),
                 '--vertices',str(vertices),'--spp',str(spp),'--seed','305419896','--frames','1']
            proc=subprocess.run(cmd,text=True,capture_output=True)
            evidence={'vertices':vertices,'spp':spp,'source_commit':source,'binary_sha256':sha(binary),
                      'command':cmd,'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr}
            if out.exists():evidence['payload_sha256']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
            if proc.returncode==0:
                score_path=out/'quality.json'
                evidence['quality']=score(out,row,ref,score_path)
                evidence['quality']['qualification_sha256']=sha(qfile)
                score_path.write_text(json.dumps(evidence['quality'],indent=2)+'\n')
                evidence['allocation_ledger']=json.loads((out/'allocation-ledger.json').read_text())
                evidence['timings']=json.loads((out/'frames.json').read_text())
            result['rows'].append(evidence)
            a.output.write_text(json.dumps(result,indent=2)+'\n')
            print(vertices,spp,proc.returncode,evidence.get('quality',{}).get('pilot_quality_target'),flush=True)
            if proc.returncode:raise SystemExit('failed capture retained')
    result['complete']=True
    a.output.write_text(json.dumps(result,indent=2)+'\n')

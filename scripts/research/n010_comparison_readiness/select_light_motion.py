#!/usr/bin/env python3
"""Frozen N010 local light-motion search; only geometry and direct are read."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts/research/n008_hdr_oracle'))
sys.path.insert(0,str(ROOT/'scripts/research/n009_scene_contract'))
import n008lib as L
from select_contract import point_triangle_distance
from qualify_references import scene_for_state

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.work.exists():raise ValueError('refuse to overwrite selection')
    a.work.mkdir(parents=True)
    base=ROOT/'out/research/n009-scene-contract/states/static'
    st=L.read_state(base)
    vertices=st['verts']; flat=vertices.reshape(-1,3)
    diagonal=float(np.linalg.norm(flat.max(0)-flat.min(0)))
    light=st['light_pos_interval'][:3].astype(float)
    scale=float(st['light_pos_interval'][3])
    record={'schema':'n010-local-light-selection/1','source_state_sha256':st['sha256'],
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'diag':diagonal,'light_scale':scale,'candidates':[]}
    for fraction in (0.01,0.02,0.04,0.08):
        for axis,sign in ((0,1),(0,-1),(1,1),(1,-1),(2,1),(2,-1)):
            candidate=light.copy();candidate[axis]+=sign*fraction*diagonal
            candidate=candidate.astype(np.float32)
            distance=point_triangle_distance(candidate.astype(float),vertices[:,0],vertices[:,1],vertices[:,2])
            tag=f'f{fraction}-a{axis}-s{sign}'
            row={'tag':tag,'position':candidate.astype(float).tolist(),'min_triangle_distance':distance,
                 'free_space':distance>=2*scale}
            if row['free_space']:
                local=st.copy();local['light_pos_interval']=st['light_pos_interval'].copy()
                local['light_pos_interval'][:3]=candidate
                sc=scene_for_state(local,1)
                meta=L.run_oracle(sc,a.work/tag,'direct',seeds=(L.N007_SEEDS[0],),spp=1)
                image=L.read_sidecar(Path(meta['runs'][0]['prefix']+'.f64'))['mean'][...,1,:]
                y=image@np.array((.2126,.7152,.0722))
                row['direct']={'positive_pixels':int((y>0).sum()),'fraction':float((y>0).mean()),'peak':float(y.max()),
                               'passes':bool((y>0).sum()>=64 and (y>0).mean()>=.01 and y.max()>=1e-4)}
                row['payload_sha256']={p.name:sha(p) for p in sorted((a.work/tag).iterdir()) if p.is_file()}
            record['candidates'].append(row)
            if row['free_space'] and row['direct']['passes']:
                record['selected']=row['tag']
                original=(ROOT/'research/lanes/n009-scene-contract/contract/sponza-c1.n009contract').read_text()
                lines=[('light_motion '+' '.join(f'{v:.9g}' for v in candidate)) if line.startswith('light_motion ') else line for line in original.splitlines()]
                contract=a.work/'sponza-local-motion.n009contract';contract.write_text('\n'.join(lines)+'\n')
                record['contract_sha256']=sha(contract)
                a.output.write_text(json.dumps(record,indent=2)+'\n')
                print(tag,'PASS',flush=True)
                sys.exit(0)
    record['selected']=None
    a.output.write_text(json.dumps(record,indent=2)+'\n')
    raise SystemExit('no local light candidate passes; retain negative result')

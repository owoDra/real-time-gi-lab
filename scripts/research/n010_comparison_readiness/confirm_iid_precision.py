#!/usr/bin/env python3
"""Execute the prospectively fixed N010 Amendment 2 precision confirmation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/research/n008_hdr_oracle'))
import n008lib as L

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    old = ROOT / 'out/research/n010-comparison-readiness/sampler-validation-v1'
    validation = ROOT / 'research/lanes/n010-comparison-readiness/results/003-sampler-validation.json'
    v = json.loads(validation.read_text())
    if not v['complete'] or not all(c['pass'] for c in v['controls']):
        raise ValueError('original physical controls incomplete/failed')
    a.work.mkdir(parents=True, exist_ok=True)
    result = {'schema': 'n010-sampler-precision-confirmation/1', 'complete': False,
              'amendment': 'experiments/004-iid-precision-amendment.md',
              'original_validation_sha256': sha(validation),
              'original_crosscheck_all_pass': v['all_pass'],
              'binary_sha256': v['binary_sha256'], 'sobol_table_sha256': v['sobol_table_sha256'],
              'source_commit': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
              'iid_binary_sha256': sha(L.oracle_binary()), 'iid_crosscheck': []}
    def save():
        a.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    save()
    for name in ('A7', 'A6b'):
        scene = old / 'rqmc' / f'{name}.n008'
        prefix = a.work / name
        if any(a.work.glob(name+'.*')):
            raise ValueError('refuse to overwrite confirmation artifacts')
        cmd = [str(L.oracle_binary()), '--scene', str(scene), '--out', str(prefix),
               '--seeds', ','.join(map(str,L.N007_SEEDS)), '--spp','16384','--checkpoints','8192']
        proc = subprocess.run(cmd, check=True, text=True, capture_output=True)
        meta = json.loads(proc.stdout)
        (a.work/f'{name}.meta.json').write_text(json.dumps(meta, indent=2)+'\n')
        checks = []
        for i in range(4):
            for ext in ('f64',) + tuple(c+'.pfm' for c in L.COMPONENTS):
                cp = Path(str(prefix)+f'.s{i}.c8192.{ext}')
                original = old / 'iid' / f'{name}.s{i}.{ext}'
                checks.append({'checkpoint': cp.name, 'original_sha256': sha(original),
                               'checkpoint_sha256': sha(cp), 'equal': sha(cp)==sha(original)})
        g = np.mean([L.read_sidecar(old/'rqmc'/f'{name}.s{i}.f64')['mean'] for i in range(4)],axis=0)[...,2,:]
        r = np.mean([L.read_sidecar(Path(run['prefix']+'.f64'))['mean'] for run in meta['runs']],axis=0)[...,2,:]
        rel = np.abs(g.mean((0,1))-r.mean((0,1)))/np.abs(r.mean((0,1)))
        nrmse = float(np.sqrt(np.mean((g-r)**2)/np.mean(r**2)))
        row = {'name': name, 'command': cmd, 'scene_sha256': sha(scene), 'iid_spp':16384,
               'rqmc_spp':8192,'per_channel_mean_relative_difference':rel.tolist(), 'nrmse':nrmse,
               'checkpoints':checks, 'payload_sha256':{p.name:sha(p) for p in sorted(a.work.glob(name+'.*'))},
               'pass':bool(all(c['equal'] for c in checks) and (rel<=0.002).all() and nrmse<=0.01)}
        result['iid_crosscheck'].append(row)
        save()
        print(name,row['pass'],nrmse,flush=True)
    result.update(complete=True, all_pass=all(r['pass'] for r in result['iid_crosscheck']))
    save()

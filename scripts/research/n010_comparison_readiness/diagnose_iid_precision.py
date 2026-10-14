#!/usr/bin/env python3
"""Post-hoc A7 diagnosis against unchanged independent quadrature; no rendering."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/research/n008_hdr_oracle'))
import phase_a_controls as P
import n008lib as L
WORK = ROOT / 'out/research/n010-comparison-readiness/sampler-validation-v1'
rows = []
for kind in ('rqmc', 'iid'):
    def load(res, scene, out, name, spp):
        meta = json.loads((WORK / kind / f'{name}.meta.json').read_text())
        runs = [L.read_sidecar(Path(r['prefix'] + '.f64')) for r in meta['runs']]
        return {'mean': np.mean([r['mean'] for r in runs], axis=0),
                'per_seed': runs, 'meta': meta}
    def compare(res, label, data, comp, expected, mask, tau, allowance=None):
        got = data['mean'][..., L.COMPONENTS.index(comp), :]
        ref = np.broadcast_to(expected, got.shape)
        rows.append({'sampler': kind, 'component': comp,
                     'whole_image_nrmse': float(np.sqrt(np.mean((got-ref)**2)/np.mean(ref**2))),
                     'control_region_nrmse': float(np.sqrt(np.mean((got[mask]-ref[mask])**2)/np.mean(ref[mask]**2))),
                     'per_channel_mean_relative_error': (np.abs(got.mean((0,1))-ref.mean((0,1)))/np.abs(ref.mean((0,1)))).tolist()})
    P.render, P.check_stat = load, compare
    P.control_a7(WORK)
print(json.dumps({'classification': 'POST_HOC_DIAGNOSTIC', 'rows': rows}, indent=2))

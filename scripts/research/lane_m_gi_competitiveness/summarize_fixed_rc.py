#!/usr/bin/env python3
"""CPU-only full replay of six fixed vanilla/software captures; no acquisition."""
import argparse
import json
from pathlib import Path
import subprocess
import fixed_rc_step as F

R = F.R

def collect():
    d = {'schema': 'lane-m-m001-fixed-traversal-controls/1', 'complete': True,
         'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=R.ROOT,text=True).strip(),
         'accepted_timing': False, 'finite_depth_equivalent': False,
         'native_audits': [], 'hdr_byte_identity': []}
    for role in ('vanilla','software'):
        for cell in ('H01','H02','H03'):
            c = F.Case(cell,role)
            actual = F.audit(c)
            intake = R.ROOT / f'out/{c.tag}-independent-audit.json'
            R.require(actual == R.read(intake) and actual['quality_evidence_valid'], 'original intake replay differs')
            d['native_audits'].append({'cell':cell,'role':role,'work':str(c.work.relative_to(R.ROOT)),
                                      'intake_sha256':R.sha(intake),'audit':actual})
            original = R.LANE / f'capture/M001-{cell}-hwrt/gpu'
            comparison = {name: {'original_sha256':R.sha(original/f'{name}.pfm'),
                                  'control_sha256':R.sha(c.capture/'gpu'/f'{name}.pfm')}
                          for name in ('direct','indirect','total')}
            d['hdr_byte_identity'].append({'cell':cell,'role':role,'components':comparison,
                'all_equal':all(x['original_sha256']==x['control_sha256'] for x in comparison.values())})
            print(cell,role,[x['classification'] for x in actual['rows']],flush=True)
    rows = [x for native in d['native_audits'] for x in native['audit']['rows']]
    d.update(native_cases=len(d['native_audits']),reference_targets=len(rows),
             quality_pass=sum(r['classification']=='PASS' for r in rows),
             quality_fail=sum(r['classification']=='QUALITY_FAIL' for r in rows),
             native_payload_hashes_replayed=sum(x['audit']['raw_payloads_rehashed'] for x in d['native_audits']))
    return d

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    R.require(not a.output.exists(),'refuse existing fixed RC replay');d=collect();R.write_new(a.output,d)
    print(json.dumps({k:v for k,v in d.items() if k not in ('native_audits','hdr_byte_identity')},indent=2))

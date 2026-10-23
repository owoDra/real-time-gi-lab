#!/usr/bin/env python3
"""CPU-only immutable010 checkpoint collector; replay all existing units, never acquire."""
import argparse
from pathlib import Path
import subprocess

import ddgi_quality_step as F
import ddgi_quality_audit as A


def collect():
    rows=[];reports={}
    for cell,depth in F.TARGETS:
        for rung in range(3):
            case=F.Case(cell,depth,rung)
            if not case.work.exists() and not case.archive.exists():continue
            audit=A.audit(case);reports[case.name]=audit
            result=F.R.read(case.work/'result.json');plan=F.R.read(case.plan)
            rows.append({'audit':audit,'source_commit':plan['source_commit'],'plan_sha256':F.R.sha(case.plan),
                'native_payload_sha256':result['payload_sha256']})
    next_=F.next_case(reports)
    selected=[]
    for cell,depth in F.TARGETS:
        group=[r for r in reports.values() if r['scope']['cell']==cell and r['scope']['vertices']==depth]
        passed=[r for r in group if r['classification']=='PASS']
        selected.append({'cell':cell,'vertices':depth,'classification':'PASS' if passed else 'QUALITY_FAIL' if len(group)==3 else 'INCOMPLETE',
            'first_pass_rung':passed[0]['scope']['rung'] if passed else None,'native_cases':len(group)})
    return {'schema':'m001-ddgi-quality-screen-raw-replay/1','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=F.R.ROOT,text=True).strip(),
        'collector_sha256':F.R.sha(Path(__file__)),'gpu_executed_by_collector':False,'accepted_timing':False,'superiority_claim':False,
        'all_existing_evidence_valid':all(r['quality_evidence_valid'] for r in reports.values()),'cohort_complete':next_ is None,
        'next_named_case':None if next_ is None else next_.scope,'native_acquisitions':len(rows),
        'raw_payloads_rehashed':sum(r['raw_payloads_rehashed'] for r in reports.values()),
        'completed_gpu_units':sum(r['native']['timing']['completed_gpu_units'] for r in reports.values()),
        'quality_pass_cases':sum(r['classification']=='PASS' for r in reports.values()),
        'quality_fail_cases':sum(r['classification']=='QUALITY_FAIL' for r in reports.values()),
        'max_true_peak_owned_bytes':max((r['native']['owned_memory']['true_peak_owned_bytes'] for r in reports.values()),default=0),
        'selected':selected,'rows':rows,'scope':'Only010 exact fresh-static finite-stage budgets. No broader dynamic/Sponza/device/temporal or speed acceptance.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    F.R.require(not args.output.exists(),'refuse existing checkpoint');d=collect();F.R.write_new(args.output,d)
    print({k:v for k,v in d.items() if k!='rows'})

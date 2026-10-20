#!/usr/bin/env python3
"""Plan174 R1: scoring-aligned eligibility from four pooled replicate means (no rendering)."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
PLAN=ROOT/'research/lanes/n010-comparison-readiness/experiments/174-scoring-aligned-reference-eligibility-amendment.md'
LUMA=np.array((0.2126,0.7152,0.0722))
COMPONENTS=('emission','direct','indirect','total')
SEEDS=(305419896,2596069104,81985529216486895,18364758544493064720)
LEVELS=(8192,16384,32768,65536,131072,262144)
LIMITS=dict(total_nrmse=0.005,indirect_nrmse=0.010,indirect_sum_bias=0.005)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sidecar(path):
    raw=Path(path).read_bytes()
    if raw[:8]!=b'N008F64\0':raise ValueError(f'bad sidecar {path}')
    w,h,spp=np.frombuffer(raw[8:20],np.uint32);seed=int(np.frombuffer(raw[20:28],np.uint64)[0])
    rec=np.frombuffer(raw[28:],np.float64)
    if rec.size!=int(w)*int(h)*24:raise ValueError(f'truncated sidecar {path}')
    return int(spp),seed,rec.reshape(-1,24)


def level_row(work,spp):
    means={c:[] for c in COMPONENTS};files={}
    for k,seed in enumerate(SEEDS):
        path=work/f'o.n{spp}.s{k}.f64'
        got_spp,got_seed,rec=sidecar(path)
        if got_spp!=spp or got_seed!=seed:raise ValueError(f'replicate identity mismatch {path}')
        if not np.isfinite(rec).all() or (rec<0).any():raise ValueError(f'nonfinite/negative {path}')
        files[path.name]=sha(path)
        for i,c in enumerate(COMPONENTS):means[c].append(rec[:,3*i:3*i+3]@LUMA)
    row=dict(spp=spp,sidecar_sha256=files,components={})
    for c in COMPONENTS:
        y=np.array(means[c]);m=y.mean(0);se2=y.var(0,ddof=1)/4
        rms=float(np.sqrt(np.mean(m**2)));total=float(m.sum())
        row['components'][c]=dict(reference_rms=rms,reference_sum=total,
            noise_nrmse=float(np.sqrt(np.mean(se2))/rms) if rms>0 else None,
            noise_sum_bias=float(np.sqrt(se2.sum())/total) if total>0 else None,
            max_pixel_se=float(np.sqrt(se2.max())))
    t=np.array(means['total']);row['active_fraction']=float(np.any(t>0,axis=0).mean())
    tc,ic=row['components']['total'],row['components']['indirect']
    row['r1_level_pass']=bool(tc['noise_nrmse'] is not None and ic['noise_nrmse'] is not None and
        ic['noise_sum_bias'] is not None and tc['noise_nrmse']<=LIMITS['total_nrmse'] and
        ic['noise_nrmse']<=LIMITS['indirect_nrmse'] and ic['noise_sum_bias']<=LIMITS['indirect_sum_bias'])
    return row


def assess(slot,work,original):
    rows=[];eligible=None
    for spp in LEVELS:
        if not all((work/f'o.n{spp}.s{k}.f64').exists() for k in range(4)):break
        rows.append(level_row(work,spp))
    for i in range(1,len(rows)):
        prev,cur=rows[i-1],rows[i]
        cur['support_stable_vs_previous']=abs(cur['active_fraction']-prev['active_fraction'])<=.1*max(prev['active_fraction'],1e-8)
        if prev['r1_level_pass'] and cur['r1_level_pass'] and cur['support_stable_vs_previous']:
            eligible=cur['spp'];break
    complete_levels=[r['spp'] for r in rows]
    if eligible:classification='R1_STATISTICALLY_ELIGIBLE'
    elif complete_levels and complete_levels[-1]==LEVELS[-1]:classification='R1_INELIGIBLE_AT_CAP'
    else:classification='R1_INCOMPLETE'
    return dict(slot=slot,work=str(work),eligibility_rule='R1',classification=classification,
        r1_eligible_at_spp=eligible,levels=rows,limits=LIMITS,
        original_screen=original,original_classification=(original or {}).get('classification'))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--slot',action='append',nargs=2,metavar=('SLOT','WORK'),required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.output.exists():raise ValueError('refuse existing R1 result')
    results=[]
    for slot,work in a.slot:
        work=Path(work);q=work/'qualification.json'
        original=json.loads(q.read_text()) if q.exists() else None
        if original:
            for level in original.get('levels',[]):
                for name,h in (level.get('all_payload_sha256') or {}).items():
                    if (work/name).exists() and sha(work/name)!=h:raise ValueError(f'payload changed {work/name}')
            original={k:original[k] for k in ('classification','levels') if k in original}
        results.append(assess(slot,work,original))
    out=dict(schema='n010-r1-reference-eligibility/1',plan_sha256=sha(PLAN),script_sha256=sha(__file__),
        gpu_run=False,reference_admission_rule='R1 statistical eligibility only; physical admission per174 route',
        slots=results,tests='NOT_RUN')
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    for r in results:
        print(r['slot'],r['classification'],r['r1_eligible_at_spp'],
              [(l['spp'],round(l['components']['total']['noise_nrmse'],5),round(l['components']['indirect']['noise_nrmse'],5),l['r1_level_pass']) for l in r['levels']])


if __name__=='__main__':main()

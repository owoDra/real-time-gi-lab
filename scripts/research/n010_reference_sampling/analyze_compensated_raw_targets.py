#!/usr/bin/env python3
"""Plan139: independent Decimal80 verification of candidate geometric residuals."""
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import time
from decimal import Decimal, localcontext

import diagnose_original_sphere_pixel as D

ROOT, RESULTS = D.ROOT, D.RESULTS
PLAN = RESULTS.parent/'experiments/139-compensated-raw-target-candidate.md'
OUTPUT = RESULTS/'450-compensated-raw-target-arithmetic.json'
SOURCE = RESULTS/'449-compensated-raw-target-probe.json'


def main():
    if OUTPUT.exists():
        raise ValueError('refuse existing geometric analysis')
    os.sched_setaffinity(0,{31})
    priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    D.quiet()
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    start=time.monotonic();before=time.process_time()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),Path(D.__file__).resolve(),PLAN):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))])!=D.checked(path):
            raise ValueError('commit exact analysis/recipe before execution')
    candidate=json.loads(D.checked(SOURCE))
    if not (candidate['complete'] and candidate['terminal_identity_verified']
            and candidate['candidate_one_pixel_pass']):
        raise ValueError('complete successful bounded candidate449 required')
    for group in ('input_sha256','payload_sha256'):
        for path,digest in candidate[group].items():D.checked(path,digest)
    original=json.loads(D.checked(RESULTS/'444-original-sphere-density-witness.json'))
    rows=candidate['density_steps'];precision=candidate['raw_precision_steps']
    key=lambda r:(r['stage'],r['light'],r['index'])
    if len(rows)!=12 or len(precision)!=12 or len({key(r) for r in rows})!=12:
        raise ValueError('exact complete witness streams required')
    residuals={key(r):r for r in precision}
    old={key(r):r for r in original['density_steps']}
    if len(residuals)!=12 or set(residuals)!=set(map(key,rows)) or set(old)!=set(residuals):
        raise ValueError('witness stream correspondence differs')
    generated=[r for r in rows if r['stage']=='generate']
    points={(r['target_triangle'],tuple(r['target'])):r for r in generated}
    outputs=[];rounding_exact=[];delta_nearest=[];legs=[]
    with localcontext() as context:
        context.prec=80
        scalar=lambda x:Decimal.from_float(float(x))
        vec=lambda x:list(map(scalar,x))
        norm=lambda a:sum((x*x for x in a),Decimal(0)).sqrt()
        sub=lambda a,b:[x-y for x,y in zip(a,b)]
        for row in rows:
            p=residuals[key(row)]
            origin,target,low,delta=map(vec,(row['origin'],row['target'],p['low'],p['delta']))
            creator=points[row['target_triangle'],tuple(row['target'])]
            created_precision=residuals[key(creator)]
            if p['low']!=created_precision['low']:
                raise ValueError('geometric target residual changed between families')
            source_origin,source_direction=map(vec,(creator['origin'],creator['direction']))
            t=scalar(creator['hit_t'])
            exact_hit=[a+b*t for a,b in zip(source_origin,source_direction)]
            exact_low=sub(exact_hit,target)
            nearest_low=[float(x) for x in exact_low]
            exact_compensated_target=[a+b for a,b in zip(target,low)]
            expected_delta=sub(exact_compensated_target,origin)
            exact_residual=p['low']==nearest_low
            nearest_delta=p['delta']==[float(x) for x in expected_delta]
            rounding_exact.append(exact_residual);delta_nearest.append(nearest_delta)
            same={k:row[k]==old[key(row)][k] for k in (
                'origin','source_normal','source_raw','target','target_normal','source_triangle','target_triangle')}
            outputs.append(dict(stage=row['stage'],light=row['light'],index=row['index'],
                low_bits_equal_independent_nearest_binary64=exact_residual,
                delta_equal_independent_nearest_binary64=nearest_delta,
                physical_operands_equal_original=same,
                original_high_point_storage_error=str(norm(sub(target,exact_hit))),
                compensated_point_error=str(norm(sub(exact_compensated_target,exact_hit))),
                delta_rounding_error=str(norm(sub(delta,expected_delta)))))
        for g in generated:
            r=next(x for x in rows if x['stage']=='reconstruct' and (x['light'],x['index'])==(g['light'],g['index']))
            terms=[math.log(r[k])-math.log(g[k]) for k in ('pdf','cosine','d2')]
            legs.append(dict(light=g['light'],index=g['index'],
                log_pdf_difference=terms[0],log_cosine_difference=terms[1],
                log_d2_difference=terms[2],net_log_density_difference=terms[0]+terms[1]-terms[2],
                direction_equal_generated=r['direction']==g['direction']))
    sampled=generated[-1]['cumulative_log']
    eye=next(r for r in rows if key(r)==('reconstruct',False,0))
    light=next(r for r in rows if key(r)==('reconstruct',True,2))
    reconstructed=eye['cumulative_log']+light['cumulative_log']
    elapsed=time.monotonic()-start;cpu=time.process_time()-before
    if elapsed>=180 or cpu>120:raise ValueError('analysis resource boundary exceeded')
    D.unchanged()
    result=dict(schema='n010-compensated-raw-target-arithmetic/1',complete=True,posthoc=True,
        source_commit=commit,input_sha256=D.INPUTS,all_pass=False,gpu_run=False,
        reference_admission=False,accepted_timing=False,
        classification='INDEPENDENT_DECIMAL80_CANDIDATE_GEOMETRY_ANALYSIS_NO_REFERENCE_ADMISSION',
        all12_target_residuals_independent_nearest_binary64=all(rounding_exact),
        all12_compensated_deltas_independent_nearest_binary64=all(delta_nearest),
        all12_physical_operands_equal_original=all(all(o['physical_operands_equal_original'].values()) for o in outputs),
        no_new_density_threshold=True,geometric_verification=outputs,own_family_legs=legs,
        witness_sampled_log_density=sampled,witness_reconstructed_log_density=reconstructed,
        witness_absolute_log_error=abs(sampled-reconstructed),
        full_one_pixel_observation=candidate['observation'],
        scope='One pixel8192 samples and exact sample3265 operands; not global physical/support/Jacobian/bias qualification',
        execution=dict(elapsed_seconds=elapsed,cpu_seconds=cpu,affinity=[31],nice=15,
            cpu_limit_seconds=120,elapsed_limit_seconds=180,address_space_limit_bytes=4*1024**3),
        tests='NOT_RUN; independent scientific Decimal80 replay only')
    with OUTPUT.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('classification','all12_target_residuals_independent_nearest_binary64',
        'all12_compensated_deltas_independent_nearest_binary64','all12_physical_operands_equal_original',
        'witness_absolute_log_error')}))


if __name__=='__main__':
    main()

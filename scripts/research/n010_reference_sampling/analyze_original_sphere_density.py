#!/usr/bin/env python3
"""Plans137/138: post-hoc exact-binary64 Decimal80 density decomposition."""
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
OUTPUT = RESULTS/'445-original-sphere-density-arithmetic.json'
WITNESS = RESULTS/'444-original-sphere-density-witness.json'
PLANS = [RESULTS.parent/'experiments'/name for name in (
    '137-original-sphere-density-operands.md', '138-exact-whole-sample-witness-selector.md')]


def arithmetic(g, r):
    with localcontext() as context:
        context.prec = 80
        scalar = lambda x: Decimal.from_float(float(x))
        vec = lambda x: list(map(scalar, x))
        dot = lambda a,b: sum((x*y for x,y in zip(a,b)), Decimal(0))
        sub = lambda a,b: [x-y for x,y in zip(a,b)]
        norm = lambda a: dot(a,a).sqrt()
        unit = lambda a: [x/norm(a) for x in a]
        origin, direction, target = map(vec, (g['origin'],g['direction'],g['target']))
        rec_direction = vec(r['direction'])
        source_normal, target_normal = map(vec,(g['source_normal'],g['target_normal']))
        t = scalar(g['hit_t'])
        exact_ray_target = [a+b*t for a,b in zip(origin,direction)]
        stored_target_error = sub(target,exact_ray_target)
        exact_rec_direction = unit(sub(target,origin))
        gen_unit = unit(direction)
        gen_pdf_cos = dot(source_normal,direction)
        unit_pdf_cos = dot(source_normal,gen_unit)
        rec_exact_pdf_cos = dot(source_normal,exact_rec_direction)
        rec_float_pdf_cos = dot(source_normal,rec_direction)
        # No acceptance tolerance: retain exact arithmetic contributions.
        log_pdf_actual = (scalar(r['pdf'])/scalar(g['pdf'])).ln()
        log_cos_actual = (scalar(r['cosine'])/scalar(g['cosine'])).ln()
        log_d2_actual = (scalar(r['d2'])/scalar(g['d2'])).ln()
        log_pdf_direction = (rec_float_pdf_cos/gen_pdf_cos).ln()
        log_pdf_components = dict(
            original_direction_normalization=(unit_pdf_cos/gen_pdf_cos).ln(),
            rounded_target_direction=(rec_exact_pdf_cos/unit_pdf_cos).ln(),
            reconstructed_direction_arithmetic=(rec_float_pdf_cos/rec_exact_pdf_cos).ln(),
            pdf_dot_division_rounding=log_pdf_actual-log_pdf_direction)
        return {key:str(value) for key,value in dict(
            original_direction_norm=norm(direction),
            stored_raw_target_rounding_distance=norm(stored_target_error),
            target_rounding_over_segment_length=norm(stored_target_error)/t,
            exact_ray_to_rounded_target_direction_difference=norm(sub(gen_unit,exact_rec_direction)),
            reconstructed_direction_additional_rounding=norm(sub(rec_direction,exact_rec_direction)),
            observed_direction_difference=norm(sub(rec_direction,direction)),
            original_source_cosine=gen_pdf_cos,
            reconstructed_source_cosine=rec_float_pdf_cos,
            original_target_cosine=abs(dot(target_normal,direction)),
            reconstructed_target_cosine=abs(dot(target_normal,rec_direction)),
            log_pdf_difference=log_pdf_actual,log_target_cosine_difference=log_cos_actual,
            log_distance_squared_difference=log_d2_actual,
            net_log_density_difference=log_pdf_actual+log_cos_actual-log_d2_actual,
            **{'log_pdf_'+key:value for key,value in log_pdf_components.items()}).items()}


def main():
    if OUTPUT.exists():
        raise ValueError('refuse existing post-hoc arithmetic result')
    os.sched_setaffinity(0,{31})
    priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:
        os.nice(15-priority)
    D.quiet()
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    start=time.monotonic();before=time.process_time()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in [Path(__file__).resolve(),Path(D.__file__).resolve()]+PLANS:
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))])!=D.checked(path):
            raise ValueError('commit exact analysis/plan before execution')
    witness=json.loads(D.checked(WITNESS))
    if not (witness['complete'] and witness['failure_reproduced']
            and witness['observation']['sample_index']==3265):
        raise ValueError('exact original numerical failure witness444 required')
    for group in ('input_sha256','payload_sha256'):
        for path,digest in witness[group].items():
            D.checked(path,digest)
    rows=witness['density_steps']
    if len(rows)!=12 or any(row['k']!=4 or row['split']!=3 for row in rows):
        raise ValueError('complete fixed failing-component operand stream required')
    generated=[row for row in rows if row['stage']=='generate']
    if [(row['light'],row['index']) for row in generated]!=[(False,0),(True,0),(True,1),(True,2)]:
        raise ValueError('original own-family1+3 leg order differs')
    legs=[]
    for g in generated:
        matches=[r for r in rows if r['stage']=='reconstruct' and
                 (r['light'],r['index'])==(g['light'],g['index'])]
        if len(matches)!=1:
            raise ValueError('own-family reconstruction missing or duplicate')
        r=matches[0]
        same={key:g[key]==r[key] for key in (
            'origin','source_normal','source_raw','target','target_normal','source_triangle','target_triangle')}
        if not all(same.values()):
            raise ValueError('own-family physical operands differ; cannot infer rounding-only mechanism')
        terms=[math.log(r[key])-math.log(g[key]) for key in ('pdf','cosine','d2')]
        legs.append(dict(light=g['light'],index=g['index'],source_triangle=g['source_triangle'],
            target_triangle=g['target_triangle'],same_physical_operands=same,hit_t=g['hit_t'],
            binary64_log_pdf_difference=terms[0],binary64_log_cosine_difference=terms[1],
            binary64_log_d2_difference=terms[2],binary64_net_log_difference=terms[0]+terms[1]-terms[2],
            decimal80=arithmetic(g,r)))
    sampled=generated[-1]['cumulative_log']
    own_eye=next(r for r in rows if r['stage']=='reconstruct' and not r['light'] and r['index']==0)
    own_light=next(r for r in rows if r['stage']=='reconstruct' and r['light'] and r['index']==2)
    reconstructed=own_eye['cumulative_log']+own_light['cumulative_log']
    original=json.loads(D.checked(RESULTS/'433-original-a6a-seed2-terminal-failure.json'))['density_check']
    if sampled!=original['sampled_log_density'] or reconstructed!=original['reconstructed_log_density']:
        raise ValueError('operand cumulative logs do not reproduce original failure')
    difference=reconstructed-sampled
    term_sum=math.fsum(row['binary64_net_log_difference'] for row in legs)
    wanted={legs[-1]['source_triangle'],legs[-1]['target_triangle']}
    triangle_vertices={};index=0
    for line in D.checked(D.SCENE).decode().splitlines():
        if not line.startswith('tri '):
            continue
        if index in wanted:
            values=list(map(float,line.split()[2:]))
            if len(values)!=9:
                raise ValueError('triangle record format differs')
            triangle_vertices[index]=[values[i:i+3] for i in (0,3,6)]
        index+=1
    shared=[v for v in triangle_vertices[legs[-1]['source_triangle']]
            if v in triangle_vertices[legs[-1]['target_triangle']]]
    elapsed=time.monotonic()-start;cpu=time.process_time()-before
    if elapsed>=180 or cpu>120:
        raise ValueError('CPU arithmetic resource guard exceeded')
    D.unchanged()
    result=dict(schema='n010-original-sphere-density-arithmetic/1',complete=True,posthoc=True,
        all_pass=False,reference_admission=False,accepted_timing=False,gpu_run=False,
        source_commit=commit,input_sha256=D.INPUTS,original_sample=3265,
        classification='OWN_DENSITY_DISCREPANCY_LOCALIZED_TO_SHORT_LEG_TARGET_COORDINATE_ROUNDING',
        threshold_unchanged=True,original_maximum_absolute_log_error=1e-6,
        sampled_log_density=sampled,reconstructed_log_density=reconstructed,
        original_log_difference=difference,sum_of_four_leg_differences=term_sum,
        accumulation_decomposition_residual=difference-term_sum,
        all12_operand_records_retained_in=str(WITNESS),own_family_legs=legs,
        short_leg_triangle_vertices=triangle_vertices,short_leg_shared_vertices=shared,
        numerical_mechanism_scope='This exact original failed sample only; no sampler-bias bound or repair admission',
        repair_executed=False,full_seed_retry=False,next_seed_queued=False,
        execution=dict(elapsed_seconds=elapsed,cpu_seconds=cpu,affinity=[31],nice=15,
                       cpu_limit_seconds=120,elapsed_limit_seconds=180,address_space_limit_bytes=4*1024**3),
        tests='NOT_RUN; post-hoc Decimal80 arithmetic on retained scientific witness only')
    with OUTPUT.open('x') as stream:
        stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(result['classification'])


if __name__=='__main__':
    main()

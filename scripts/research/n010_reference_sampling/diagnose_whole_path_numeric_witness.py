#!/usr/bin/env python3
"""Plan068: reproduce the exact first guard failure and diagnose its geometry."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
from decimal import Decimal, localcontext

import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK=D.OUT/'whole-path-numeric-witness-v1'
PARENT=D.OUT/'whole-path-mixture-diagnosis-v1'
OUTPUT=D.RESULTS/'211-whole-path-numeric-failure-witness.json'
PLAN=D.RESULTS.parent/'experiments/068-whole-path-numeric-failure-witness.md'

REPORT=r'''
            if(error>bound) {
                const auto& tri=scene_.triangles.at(target.triangle);
                std::fprintf(stderr,"WHOLE_WITNESS {\"triangle\":%u,\"index\":%zu,\"sphere\":%s,\"origin\":[%.17g,%.17g,%.17g],\"target\":[%.17g,%.17g,%.17g],\"direction\":[%.17g,%.17g,%.17g],\"actual\":[%.17g,%.17g,%.17g],\"vertices\":[[%.17g,%.17g,%.17g],[%.17g,%.17g,%.17g],[%.17g,%.17g,%.17g]],\"hit_t\":%.17g,\"error\":%.17g,\"bound\":%.17g}\n",
                    target.triangle,i,sphere?"true":"false",
                    current.origin.x,current.origin.y,current.origin.z,
                    target.point.x,target.point.y,target.point.z,
                    direction.x,direction.y,direction.z,actual.x,actual.y,actual.z,
                    tri.v0.x,tri.v0.y,tri.v0.z,tri.v1.x,tri.v1.y,tri.v1.z,tri.v2.x,tri.v2.y,tri.v2.z,
                    hit.t,error,bound);
                throw std::runtime_error("raw-target closest-hit reconstruction error");
            }
'''


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def arithmetic(w):
    with localcontext() as context:
        context.prec=80
        # Decimal.from_float uses the exact recorded binary64 values; JSON's
        # 17 significant digits round-trip each original witness coordinate.
        vec=lambda a:[Decimal.from_float(float(x)) for x in a]
        sub=lambda a,b:[x-y for x,y in zip(a,b)]
        dot=lambda a,b:sum((x*y for x,y in zip(a,b)),Decimal(0))
        cross=lambda a,b:[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
        norm=lambda a:dot(a,a).sqrt()
        origin,target,direction,actual=map(vec,(w['origin'],w['target'],w['direction'],w['actual']))
        v0,v1,v2=map(vec,w['vertices']);normal=cross(sub(v1,v0),sub(v2,v0));length=norm(normal)
        cosine=abs(dot(normal,direction))/length/norm(direction)
        target_plane=dot(normal,sub(target,v0))/length
        actual_plane=dot(normal,sub(actual,v0))/length
        t=dot(normal,sub(v0,origin))/dot(normal,direction)
        plane_hit=[a+t*b for a,b in zip(origin,direction)]
        expected=norm(sub(plane_hit,target));actual_error=norm(sub(actual,target))
        return {k:str(v) for k,v in dict(abs_normal_dot_unit_direction=cosine,
            near_parallel_condition_number=1/cosine,target_signed_plane_distance=target_plane,
            actual_signed_plane_distance=actual_plane,line_plane_parameter=t,
            exact_line_plane_to_target_distance=expected,recorded_actual_to_target_distance=actual_error,
            actual_to_high_precision_line_plane_distance=norm(sub(actual,plane_hit)),
            expected_miss_divided_by_original_bound=expected/Decimal.from_float(w['bound']),
            plane_residual_amplified_by_inverse_cosine=abs(target_plane)/cosine).items()}


def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing witness')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    D.checked(Path(__file__));D.checked(PLAN)
    prior=json.loads(D.checked(D.RESULTS/'210-whole-path-mixture-diagnosis.json'))
    if prior['complete'] or prior['classification']!='OPERATIONAL_FAILURE_PARTIALS_RETAINED' or [a['returncode'] for a in prior['attempts']]!=[0,-6]:
        raise ValueError('exact terminal original native failure required')
    for path,h in prior['input_sha256'].items():D.checked(Path(path),h)
    for path in PARENT.iterdir():
        if path.is_file():D.checked(path)
    original=(PARENT/'n010_rqmc_oracle.hpp').read_text()
    old='            if(error>bound)throw std::runtime_error("raw-target closest-hit reconstruction error");'
    generated=D.once(original,old,REPORT)
    if D.once(generated,REPORT,old)!=original:raise ValueError('exact witness inverse differs')
    WORK.mkdir();(WORK/'n010_rqmc_oracle.hpp').write_text(generated)
    for name in ('main.cpp','pixels.txt'):(WORK/name).write_bytes((PARENT/name).read_bytes())
    net,scene=prior['attempts'][1]['command'][1:3]
    binary=WORK/'n010_whole_path_witness';data=WORK/'partial-data.json'
    commands=[['c++','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread','-I',str(D.ROOT/'src/research/n008_hdr_oracle'),str(WORK/'main.cpp'),'-o',str(binary)],
              [str(binary),net,scene,str(WORK/'pixels.txt'),str(data)]]
    result=dict(schema='n010-whole-path-numeric-witness/1',complete=False,gpu_run=False,
        reference_admission=False,classification='POSTHOC_WITNESS_ACQUIRING',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        exact_original_guard_and_source_inverse=True,input_sha256=D.INPUTS,attempts=[],tests='NOT_RUN; bounded post-hoc failure reproduction only')
    def save():OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()
    try:
        for i,command in enumerate(commands):
            receipt=WORK/f'step-{i}.resources.json'
            def limits():
                resource.setrlimit(resource.RLIMIT_CPU,(220,)*2);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
                receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
            attempt=dict(command=command,elapsed_limit_seconds=300);result['attempts'].append(attempt);save();start=time.monotonic()
            proc=subprocess.run(command,capture_output=True,text=True,timeout=300,preexec_fn=limits)
            (WORK/f'step-{i}.stdout').write_text(proc.stdout);(WORK/f'step-{i}.stderr').write_text(proc.stderr)
            attempt.update(returncode=proc.returncode,elapsed=time.monotonic()-start,receipt_sha256=sha(receipt));save()
            actual=json.loads(D.checked(receipt))
            if actual['cpu']!=[220,220] or actual['address_space']!=[4*1024**3]*2 or len(actual['affinity'])!=1 or actual['nice']!=15:
                raise ValueError('actual witness resource limits differ')
            if i==0 and proc.returncode:raise ValueError('witness compile failure; no retry')
        lines=[line.split('WHOLE_WITNESS ',1)[1] for line in proc.stderr.splitlines() if line.startswith('WHOLE_WITNESS ')]
        if proc.returncode!=-6 or len(lines)!=1 or 'raw-target closest-hit reconstruction error' not in proc.stderr:
            raise ValueError('expected single same guard failure not reproduced')
        witness=json.loads(lines[0]);analysis=arithmetic(witness)
        for path,h in list(D.INPUTS.items()):D.checked(Path(path),h)
        result.update(complete=True,classification='POSTHOC_SAME_GUARD_REPRODUCED_NO_ADMISSION',witness=witness,decimal80_analysis=analysis,
            payload_sha256={str(p):sha(p) for p in WORK.iterdir() if p.is_file()})
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        result.update(classification='WITNESS_OPERATIONAL_FAILURE_PARTIALS_RETAINED',failure=str(error))
    save();print(json.dumps({k:result.get(k) for k in ('complete','classification','failure','decimal80_analysis')},indent=2))
    raise SystemExit(0 if result['complete'] else 2)


if __name__=='__main__':main()

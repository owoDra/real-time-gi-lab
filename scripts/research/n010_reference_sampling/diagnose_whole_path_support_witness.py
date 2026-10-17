#!/usr/bin/env python3
"""Plan070: exact terminal own-support failure and deterministic trace witness."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK=D.OUT/'whole-path-support-witness-v1'
PARENT=D.OUT/'whole-path-conditioned-diagnosis-v1'
OUTPUT=D.RESULTS/'213-whole-path-own-support-witness.json'
PLAN=D.RESULTS.parent/'experiments/070-whole-path-own-support-witness.md'

STEP=r'''
            if(report) {
                std::fprintf(stderr,"OWN_STEP {\"index\":%zu,\"sphere\":%s,\"source_triangle\":%u,\"expected_triangle\":%u,\"pdf\":%.17g,\"origin\":[%.17g,%.17g,%.17g],\"normal\":[%.17g,%.17g,%.17g],\"direction\":[%.17g,%.17g,%.17g],\"target\":[%.17g,%.17g,%.17g]}\n",
                    i,sphere?"true":"false",current.raw.triangle,target.triangle,pdf,
                    current.origin.x,current.origin.y,current.origin.z,current.normal.x,current.normal.y,current.normal.z,
                    direction.x,direction.y,direction.z,target.point.x,target.point.y,target.point.z);
            }
'''

HIT=r'''
            if(report) {
                std::fprintf(stderr,"OWN_HIT {\"index\":%zu,\"expected_triangle\":%u,\"actual_triangle\":%u,\"hit\":%s,\"hit_t\":%.17g,\"expected_vertices\":[",
                    i,target.triangle,hit.tri,hit.hit()?"true":"false",hit.hit()?hit.t:0);
                const auto& expected=scene_.triangles.at(target.triangle);
                for(int c=0;c<3;++c){const auto v=c==0?expected.v0:(c==1?expected.v1:expected.v2);std::fprintf(stderr,"%s[%.17g,%.17g,%.17g]",c?",":"",v.x,v.y,v.z);}
                std::fprintf(stderr,"],\"actual_vertices\":[");
                if(hit.hit()) {
                    const auto& actual=scene_.triangles.at(hit.tri);
                    for(int c=0;c<3;++c){const auto v=c==0?actual.v0:(c==1?actual.v1:actual.v2);std::fprintf(stderr,"%s[%.17g,%.17g,%.17g]",c?",":"",v.x,v.y,v.z);}
                }
                std::fprintf(stderr,"]}\n");
            }
'''

CALL=r'''
            if(!std::isfinite(eye?log_eye:log_light)) {
                std::fprintf(stderr,"OWN_WITNESS {\"eye\":%s,\"x\":%u,\"y\":%u,\"prefix_length\":%u,\"sampled_log_density\":%.17g,\"own_reconstructed_finite\":false,\"raw_vertices\":[",
                    eye?"true":"false",x,y,k,sampled_log);
                for(size_t j=0;j<generated.size();++j)std::fprintf(stderr,"%s{\"triangle\":%u,\"point\":[%.17g,%.17g,%.17g]}",
                    j?",":"",generated[j].triangle,generated[j].point.x,generated[j].point.y,generated[j].point.z);
                std::fprintf(stderr,"]}\n");
                (void)whole_density(eye?primary:light,generated,!eye,audit,nullptr,true);
            }
'''


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing support witness')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    D.checked(Path(__file__));D.checked(PLAN)
    prior=json.loads(D.checked(D.RESULTS/'212-whole-path-conditioned-diagnosis.json'))
    if prior['complete'] or prior['classification']!='OPERATIONAL_FAILURE_PARTIALS_RETAINED' or [a['returncode'] for a in prior['attempts']]!=[0,-6]:
        raise ValueError('exact terminal own-support failure required')
    for path,h in prior['input_sha256'].items():D.checked(Path(path),h)
    for path in PARENT.iterdir():
        if path.is_file():D.checked(path)
    original=(PARENT/'n010_rqmc_oracle.hpp').read_text();generated=original
    edits=[('bool light_first,WholeAudit& audit,WholeState* endpoint=nullptr) const {',
            'bool light_first,WholeAudit& audit,WholeState* endpoint=nullptr,bool report=false) const {'),
        ('            if(!(pdf>0))return -kInf;',STEP+'\n            if(!(pdf>0))return -kInf;'),
        ('            if(!hit.hit()||hit.tri!=target.triangle)return -kInf;',HIT+'\n            if(!hit.hit()||hit.tri!=target.triangle)return -kInf;'),
        ('            whole_check_density(sampled_log,eye?log_eye:log_light,audit);',CALL+'\n            whole_check_density(sampled_log,eye?log_eye:log_light,audit);')]
    for a,b in edits:generated=D.once(generated,a,b)
    restored=generated
    for a,b in reversed(edits):restored=D.once(restored,b,a)
    if restored!=original:raise ValueError('exact support witness inverse differs')
    WORK.mkdir();(WORK/'n010_rqmc_oracle.hpp').write_text(generated)
    for name in ('main.cpp','pixels.txt'):(WORK/name).write_bytes((PARENT/name).read_bytes())
    net,scene=prior['attempts'][1]['command'][1:3]
    binary=WORK/'n010_whole_path_support_witness';data=WORK/'partial-data.json'
    commands=[['c++','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread','-I',str(D.ROOT/'src/research/n008_hdr_oracle'),str(WORK/'main.cpp'),'-o',str(binary)],
              [str(binary),net,scene,str(WORK/'pixels.txt'),str(data)]]
    result=dict(schema='n010-whole-path-support-witness/1',complete=False,gpu_run=False,reference_admission=False,
        classification='POSTHOC_SUPPORT_WITNESS_ACQUIRING',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        exact_original_guard_and_source_inverse=True,input_sha256=D.INPUTS,attempts=[],tests='NOT_RUN; bounded post-hoc support reproduction only')
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
                raise ValueError('actual support witness resource limits differ')
            if i==0 and proc.returncode:raise ValueError('support witness compile failure; no retry')
        extract=lambda tag:[json.loads(line.split(tag+' ',1)[1]) for line in proc.stderr.splitlines() if line.startswith(tag+' ')]
        witness,steps,hits=extract('OWN_WITNESS'),extract('OWN_STEP'),extract('OWN_HIT')
        if proc.returncode!=-6 or len(witness)!=1 or not steps or 'generated own-family prefix has zero/nonfinite density' not in proc.stderr:
            raise ValueError('expected exact support failure not reproduced')
        for path,h in list(D.INPUTS.items()):D.checked(Path(path),h)
        result.update(complete=True,classification='POSTHOC_SAME_OWN_SUPPORT_FAILURE_REPRODUCED_NO_ADMISSION',witness=witness[0],steps=steps,hits=hits,
            payload_sha256={str(p):sha(p) for p in WORK.iterdir() if p.is_file()})
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        result.update(classification='SUPPORT_WITNESS_OPERATIONAL_FAILURE_PARTIALS_RETAINED',failure=str(error))
    save();print(json.dumps({k:result.get(k) for k in ('complete','classification','failure','witness','steps','hits')},indent=2))
    raise SystemExit(0 if result['complete'] else 2)


if __name__=='__main__':main()

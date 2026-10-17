#!/usr/bin/env python3
"""Plan073: both-hemisphere original support-predicate witness, no sampled paths."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK=D.OUT/'coincident-predicate-witness-v1'
OUTPUT=D.RESULTS/'216-coincident-predicate-witness.json'
PLAN=D.RESULTS.parent/'experiments/073-coincident-predicate-witness.md'

MAIN='\n#include "n010_rqmc_oracle.hpp"\n#include <bit>\n#include <iomanip>\nusing namespace phos::gi::research::n008;\nvoid vector(std::ostream& out,V3 v) {out<<"["<<v.x<<","<<v.y<<","<<v.z<<"]";}\nvoid bits(std::ostream& out,V3 v) {out<<"["<<std::bit_cast<uint64_t>(v.x)<<","<<std::bit_cast<uint64_t>(v.y)<<","<<std::bit_cast<uint64_t>(v.z)<<"]";}\nbool same(V3 a,V3 b) {return std::bit_cast<uint64_t>(a.x)==std::bit_cast<uint64_t>(b.x)&&std::bit_cast<uint64_t>(a.y)==std::bit_cast<uint64_t>(b.y)&&std::bit_cast<uint64_t>(a.z)==std::bit_cast<uint64_t>(b.z);}\nint main(int argc,char**argv) {\n    if(argc!=4)return 2;\n    std::ifstream file(argv[1]);const Scene scene=parse_scene(file);const Oracle oracle(scene);\n    std::ifstream witness(argv[2]);uint32_t ids[2];V3 p,direction;\n    witness>>ids[0]>>ids[1]>>p.x>>p.y>>p.z>>direction.x>>direction.y>>direction.z;\n    if(!witness||ids[0]>=scene.triangles.size()||ids[1]>=scene.triangles.size())return 3;\n    std::ofstream out(argv[3]);out<<std::setprecision(17)<<"[";\n    for(int hemisphere=0;hemisphere<2;++hemisphere) {\n    direction={hemisphere?1.0:-1.0,0,0};\n    Oracle::WholeAudit audit;const bool accepted=oracle.whole_coincident({ids[0],p},ids[1],direction,audit);\n    if(hemisphere)out<<",";\n    out<<"{\\"accepted\\":"<<(accepted?"true":"false")<<",\\"incoming_x\\":"<<direction.x<<",\\"offset\\":"<<oracle.offset()<<",\\"surfaces\\":[";\n    V3 normals[2],spawns[2],nudges[2],mapped[2];int axes[2];double planes[2];\n    for(int j=0;j<2;++j) {\n        const auto& triangle=scene.triangles[ids[j]];const auto& material=scene.materials[triangle.material];\n        const auto geometric=normalize(cross(triangle.v1-triangle.v0,triangle.v2-triangle.v0));\n        normals[j]=dot(geometric,direction)<0?geometric:geometric*-1.0;\n        nudges[j]=oracle.nudge_inside(triangle,p);spawns[j]=nudges[j]+normals[j]*oracle.offset();\n        mapped[j]=Oracle::cosine_sample(normals[j],0.375,0.625);\n        axes[j]=-1;planes[j]=0;\n        for(int a=0;a<3;++a)if(triangle.v0[a]==triangle.v1[a]&&triangle.v1[a]==triangle.v2[a]){axes[j]=a;planes[j]=triangle.v0[a];}\n        long double bary[3]{};\n        if(axes[j]>=0) {\n            const int u=(axes[j]+1)%3,v=(axes[j]+2)%3;\n            const long double ax=triangle.v0[u],ay=triangle.v0[v],bx=triangle.v1[u],by=triangle.v1[v],cx=triangle.v2[u],cy=triangle.v2[v];\n            const long double det=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax);\n            bary[1]=(((long double)p[u]-ax)*(cy-ay)-((long double)p[v]-ay)*(cx-ax))/det;\n            bary[2]=((bx-ax)*((long double)p[v]-ay)-(by-ay)*((long double)p[u]-ax))/det;\n            bary[0]=1-bary[1]-bary[2];\n        }\n        if(j)out<<",";\n        out<<"{\\"barycentric\\":["<<bary[0]<<","<<bary[1]<<","<<bary[2]<<"],\\"basis_sign\\":"<<std::copysign(1.0,normals[j].z)<<",\\"triangle\\":"<<ids[j]<<",\\"geometric_normal\\":";vector(out,geometric);\n        out<<",\\"normal\\":";vector(out,normals[j]);out<<",\\"normal_bits\\":";bits(out,normals[j]);\n        out<<",\\"nudge\\":";vector(out,nudges[j]);out<<",\\"nudge_bits\\":";bits(out,nudges[j]);\n        out<<",\\"spawn\\":";vector(out,spawns[j]);out<<",\\"spawn_bits\\":";bits(out,spawns[j]);\n        out<<",\\"mapped_direction\\":";vector(out,mapped[j]);out<<",\\"mapped_direction_bits\\":";bits(out,mapped[j]);\n        out<<",\\"axis\\":"<<axes[j]<<",\\"plane\\":"<<planes[j]<<",\\"material\\":"<<triangle.material\n           <<",\\"two_sided\\":"<<(material.two_sided?"true":"false")<<",\\"rho\\":["<<material.rho[0]<<","<<material.rho[1]<<","<<material.rho[2]\n           <<"],\\"emit\\":["<<material.emit[0]<<","<<material.emit[1]<<","<<material.emit[2]<<"],\\"recorded_direction_cosine\\":"<<dot(normals[j],direction);\n        if(axes[j]>=0)out<<",\\"signed_spawn_plane_distance\\":"<<(spawns[j][axes[j]]-planes[j])*normals[j][axes[j]];\n        out<<"}";\n    }\n    out<<"],\\"normal_numeric_equal\\":"<<((normals[0].x==normals[1].x&&normals[0].y==normals[1].y&&normals[0].z==normals[1].z)?"true":"false")\n       <<",\\"normal_bits_equal\\":"<<(same(normals[0],normals[1])?"true":"false")\n       <<",\\"nudge_bits_equal\\":"<<(same(nudges[0],nudges[1])?"true":"false")\n       <<",\\"spawn_bits_equal\\":"<<(same(spawns[0],spawns[1])?"true":"false")\n       <<",\\"mapped_direction_bits_equal\\":"<<(same(mapped[0],mapped[1])?"true":"false")\n       <<",\\"axis_plane_exactly_equal\\":"<<((axes[0]>=0&&axes[0]==axes[1]&&planes[0]==planes[1])?"true":"false")<<"}";\n    }\n    out<<"]\\n";\n    return out?0:4;\n}\n'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing operator diagnosis')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    D.checked(Path(__file__));D.checked(PLAN)
    previous=json.loads(D.checked(D.RESULTS/'215-whole-path-geometric-support-diagnosis.json'))
    if previous['complete'] or previous['classification']!='OPERATIONAL_FAILURE_PARTIALS_RETAINED':
        raise ValueError('actual incomplete previous result required')
    for p,h in previous['payload_sha256'].items():D.checked(Path(p),h)
    import re
    from collections import deque
    log=D.OUT/'whole-path-geometric-support-diagnosis-v1/step-1.stderr'
    with log.open() as f:last=next(v for v in reversed(deque(f,maxlen=5)) if v.startswith('unmatched '))
    match=re.fullmatch(r'unmatched target=(\d+) hit=(\d+) point=([^ ]+)\n',last)
    if not match:raise ValueError('candidate witness format differs')
    ids=list(map(int,match.group(1,2)));point=list(map(float,match.group(3).split(',')))
    proof=json.loads(D.checked(D.RESULTS/'193-selected-bounce-path-diagnosis.json'))
    old=next(v for v in proof['variants'] if v['variant']=='original')
    header=next(Path(p) for p in old['payload_sha256'] if p.endswith('.hpp'))
    D.checked(header,old['payload_sha256'][str(header)])
    scene=D.OUT/'references-recovery-sponza-v1/C1_T_B8/scene.n008';D.checked(scene)
    inclusion=D.checked(D.HERE/'whole_path_geometric.inc').decode()
    D.checked(D.HERE/'diagnose_coincident_path_surfaces.py')
    physical=header.read_text();anchor='    // One camera sample; writes per-component radiance.'
    generated=D.once(physical,anchor,inclusion+'\n'+anchor)
    if D.once(generated,inclusion+'\n'+anchor,anchor)!=physical:raise ValueError('physical inverse differs')
    WORK.mkdir();(WORK/'n010_rqmc_oracle.hpp').write_text(generated);(WORK/'main.cpp').write_text(MAIN)
    witness=WORK/'witness.txt';witness.write_text(' '.join(map(str,[*ids,*point,1,0,0]))+'\n')
    binary=WORK/'n010_surface_operator';data=WORK/'data.json'
    commands=[['c++','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread','-I',str(D.ROOT/'src/research/n008_hdr_oracle'),str(WORK/'main.cpp'),'-o',str(binary)],
              [str(binary),str(scene),str(witness),str(data)]]
    result=dict(schema='n010-coincident-predicate-witness/1',complete=False,gpu_run=False,reference_admission=False,
        classification='POSTHOC_OPERATOR_DIAGNOSIS_ACQUIRING',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        original_header_whole_source_inverse_exact=True,candidate_pair_ids=ids,candidate_raw_point=point,input_sha256=D.INPUTS,attempts=[],tests='NOT_RUN; original-operator witness calculation only')
    def save():OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()
    try:
        for i,command in enumerate(commands):
            receipt=WORK/f'step-{i}.resources.json'
            def limits():
                resource.setrlimit(resource.RLIMIT_CPU,(120,)*2);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
                receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
            attempt=dict(command=command,elapsed_limit_seconds=180);result['attempts'].append(attempt);save();start=time.monotonic()
            proc=subprocess.run(command,capture_output=True,text=True,timeout=180,preexec_fn=limits)
            (WORK/f'step-{i}.stdout').write_text(proc.stdout);(WORK/f'step-{i}.stderr').write_text(proc.stderr)
            attempt.update(returncode=proc.returncode,elapsed=time.monotonic()-start,receipt_sha256=sha(receipt));save()
            actual=json.loads(D.checked(receipt))
            if actual['cpu']!=[120,120] or actual['address_space']!=[4*1024**3]*2 or len(actual['affinity'])!=1 or actual['nice']!=15:
                raise ValueError('actual operator diagnosis limits differ')
            if proc.returncode:raise ValueError('operator diagnostic failed; no retry')
        observation=json.loads(D.checked(data))
        for path,h in list(D.INPUTS.items()):D.checked(Path(path),h)
        result.update(complete=True,classification='POSTHOC_CANDIDATE_PAIR_PREDICATES_NO_ADMISSION',observation=observation,
            payload_sha256={str(p):sha(p) for p in WORK.iterdir() if p.is_file()})
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        result.update(classification='OPERATOR_DIAGNOSIS_FAILURE_PARTIALS_RETAINED',failure=str(error))
    save();print(json.dumps({k:result.get(k) for k in ('complete','classification','failure','observation')},indent=2))
    raise SystemExit(0 if result['complete'] else 2)


if __name__=='__main__':main()

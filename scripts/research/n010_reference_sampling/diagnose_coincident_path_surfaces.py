#!/usr/bin/env python3
"""Plan071: original binary64 operators on one retained coplanar-hit witness."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK=D.OUT/'coincident-surface-operator-diagnosis-v1'
OUTPUT=D.RESULTS/'214-coincident-surface-operator-diagnosis.json'
PLAN=D.RESULTS.parent/'experiments/071-coincident-surface-operator-diagnosis.md'

MAIN=r'''
#include "n010_rqmc_oracle.hpp"
#include <bit>
#include <iomanip>
using namespace phos::gi::research::n008;
void vector(std::ostream& out,V3 v) {out<<"["<<v.x<<","<<v.y<<","<<v.z<<"]";}
void bits(std::ostream& out,V3 v) {out<<"["<<std::bit_cast<uint64_t>(v.x)<<","<<std::bit_cast<uint64_t>(v.y)<<","<<std::bit_cast<uint64_t>(v.z)<<"]";}
bool same(V3 a,V3 b) {return std::bit_cast<uint64_t>(a.x)==std::bit_cast<uint64_t>(b.x)&&std::bit_cast<uint64_t>(a.y)==std::bit_cast<uint64_t>(b.y)&&std::bit_cast<uint64_t>(a.z)==std::bit_cast<uint64_t>(b.z);}
int main(int argc,char**argv) {
    if(argc!=4)return 2;
    std::ifstream file(argv[1]);const Scene scene=parse_scene(file);const Oracle oracle(scene);
    std::ifstream witness(argv[2]);uint32_t ids[2];V3 p,direction;
    witness>>ids[0]>>ids[1]>>p.x>>p.y>>p.z>>direction.x>>direction.y>>direction.z;
    if(!witness||ids[0]>=scene.triangles.size()||ids[1]>=scene.triangles.size())return 3;
    std::ofstream out(argv[3]);out<<std::setprecision(17)<<"{\"offset\":"<<oracle.offset()<<",\"surfaces\":[";
    V3 normals[2],spawns[2],nudges[2],mapped[2];int axes[2];double planes[2];
    for(int j=0;j<2;++j) {
        const auto& triangle=scene.triangles[ids[j]];const auto& material=scene.materials[triangle.material];
        const auto geometric=normalize(cross(triangle.v1-triangle.v0,triangle.v2-triangle.v0));
        normals[j]=dot(geometric,direction)<0?geometric:geometric*-1.0;
        nudges[j]=oracle.nudge_inside(triangle,p);spawns[j]=nudges[j]+normals[j]*oracle.offset();
        mapped[j]=Oracle::cosine_sample(normals[j],0.375,0.625);
        axes[j]=-1;planes[j]=0;
        for(int a=0;a<3;++a)if(triangle.v0[a]==triangle.v1[a]&&triangle.v1[a]==triangle.v2[a]){axes[j]=a;planes[j]=triangle.v0[a];}
        if(j)out<<",";
        out<<"{\"triangle\":"<<ids[j]<<",\"geometric_normal\":";vector(out,geometric);
        out<<",\"normal\":";vector(out,normals[j]);out<<",\"normal_bits\":";bits(out,normals[j]);
        out<<",\"nudge\":";vector(out,nudges[j]);out<<",\"nudge_bits\":";bits(out,nudges[j]);
        out<<",\"spawn\":";vector(out,spawns[j]);out<<",\"spawn_bits\":";bits(out,spawns[j]);
        out<<",\"mapped_direction\":";vector(out,mapped[j]);out<<",\"mapped_direction_bits\":";bits(out,mapped[j]);
        out<<",\"axis\":"<<axes[j]<<",\"plane\":"<<planes[j]<<",\"material\":"<<triangle.material
           <<",\"two_sided\":"<<(material.two_sided?"true":"false")<<",\"rho\":["<<material.rho[0]<<","<<material.rho[1]<<","<<material.rho[2]
           <<"],\"emit\":["<<material.emit[0]<<","<<material.emit[1]<<","<<material.emit[2]<<"],\"recorded_direction_cosine\":"<<dot(normals[j],direction);
        if(axes[j]>=0)out<<",\"signed_spawn_plane_distance\":"<<(spawns[j][axes[j]]-planes[j])*normals[j][axes[j]];
        out<<"}";
    }
    out<<"],\"normal_numeric_equal\":"<<((normals[0].x==normals[1].x&&normals[0].y==normals[1].y&&normals[0].z==normals[1].z)?"true":"false")
       <<",\"normal_bits_equal\":"<<(same(normals[0],normals[1])?"true":"false")
       <<",\"nudge_bits_equal\":"<<(same(nudges[0],nudges[1])?"true":"false")
       <<",\"spawn_bits_equal\":"<<(same(spawns[0],spawns[1])?"true":"false")
       <<",\"mapped_direction_bits_equal\":"<<(same(mapped[0],mapped[1])?"true":"false")
       <<",\"axis_plane_exactly_equal\":"<<((axes[0]>=0&&axes[0]==axes[1]&&planes[0]==planes[1])?"true":"false")<<"}\n";
    return out?0:4;
}
'''


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing operator diagnosis')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    D.checked(Path(__file__));D.checked(PLAN)
    previous=json.loads(D.checked(D.RESULTS/'213-whole-path-own-support-witness.json'))
    if not previous['complete'] or previous['classification']!='POSTHOC_SAME_OWN_SUPPORT_FAILURE_REPRODUCED_NO_ADMISSION':
        raise ValueError('actual retained support witness required')
    hit=previous['hits'][-1];step=previous['steps'][-1]
    if not hit['hit'] or hit['expected_triangle']==hit['actual_triangle']:raise ValueError('different witness mechanism')
    proof=json.loads(D.checked(D.RESULTS/'193-selected-bounce-path-diagnosis.json'))
    old=next(v for v in proof['variants'] if v['variant']=='original')
    header=next(Path(p) for p in old['payload_sha256'] if p.endswith('.hpp'))
    D.checked(header,old['payload_sha256'][str(header)])
    scene=D.OUT/'references-recovery-sponza-v1/C1_T_B8/scene.n008';D.checked(scene)
    WORK.mkdir();(WORK/'n010_rqmc_oracle.hpp').write_bytes(header.read_bytes());(WORK/'main.cpp').write_text(MAIN)
    witness=WORK/'witness.txt';witness.write_text(' '.join(map(str,[hit['expected_triangle'],hit['actual_triangle'],*step['target'],*step['direction']]))+'\n')
    binary=WORK/'n010_surface_operator';data=WORK/'data.json'
    commands=[['c++','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread','-I',str(D.ROOT/'src/research/n008_hdr_oracle'),str(WORK/'main.cpp'),'-o',str(binary)],
              [str(binary),str(scene),str(witness),str(data)]]
    result=dict(schema='n010-coincident-surface-operator-diagnosis/1',complete=False,gpu_run=False,reference_admission=False,
        classification='POSTHOC_OPERATOR_DIAGNOSIS_ACQUIRING',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        original_header_byte_identical=True,input_sha256=D.INPUTS,attempts=[],tests='NOT_RUN; original-operator witness calculation only')
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
        result.update(complete=True,classification='POSTHOC_ORIGINAL_OPERATOR_OBSERVATIONS_NO_ADMISSION',observation=observation,
            payload_sha256={str(p):sha(p) for p in WORK.iterdir() if p.is_file()})
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        result.update(classification='OPERATOR_DIAGNOSIS_FAILURE_PARTIALS_RETAINED',failure=str(error))
    save();print(json.dumps({k:result.get(k) for k in ('complete','classification','failure','observation')},indent=2))
    raise SystemExit(0 if result['complete'] else 2)


if __name__=='__main__':main()

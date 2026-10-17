#!/usr/bin/env python3
"""Plan076: bounded rho1 furnace analytic/iid control; no reference admission."""
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import time
import numpy as np
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK=D.OUT/'all-split-furnace-control-v1'
OUTPUT=D.RESULTS/'219-bounded-all-split-furnace-control.json'
PLAN=D.RESULTS.parent/'experiments/076-bounded-all-split-furnace-control.md'
PIXELS=[(16,16),(48,16),(80,16),(112,16),(16,80),(48,80),(80,80),(112,80)]
MAIN=r'''
#include "n010_rqmc_oracle.hpp"
#include <iomanip>
using namespace phos::gi::research::n008;
int main(int argc,char**argv) {
    if(argc!=5)return 2;
    N010NetRng::load(argv[1]);std::ifstream f(argv[2]);const Scene scene=parse_scene(f);
    if(scene.max_bounces!=8||scene.points.size()!=1||scene.width!=128||scene.height!=96)return 3;
    for(const auto& m:scene.materials)if(m.rho!=Rgb{1,1,1}||m.emit!=Rgb{0,0,0}||!m.two_sided)return 4;
    const Oracle oracle(scene);Scene dark_scene=scene;dark_scene.points[0].intensity={0,0,0};const Oracle dark(dark_scene);
    std::ifstream pixels(argv[3]);uint32_t x,y;
    const uint64_t seeds[]={305419896ULL,2596069104ULL,81985529216486895ULL,18364758544493064720ULL};
    std::ofstream out(argv[4]);out<<std::setprecision(17)<<"[";bool comma=false;
    while(pixels>>x>>y)for(auto seed:seeds) {
        const size_t pixel=size_t(y)*scene.width+x;Oracle::PrimaryCache cache;RenderCounters cnt;
        Xoshiro256 prime(seed);Rgb ignored[kComponents];oracle.sample(x,y,prime,ignored,cnt,nullptr,&cache);
        if(!cache.hit.hit())return 5;
        Oracle::WholeAudit audit;double mix[8]{},mix2[8]{},iid[8]{},iid2[8]{};
        double mix_total=0,mix_total2=0,iid_total=0,iid_total2=0;
        for(uint32_t n=0;n<8192;++n) {
            N010NetRng rng(seed,pixel,n);Rgb comp[kComponents];double depth[8]{};
            oracle.whole_sample(x,y,rng,comp,cache,audit,depth);
            for(int k=1;k<8;++k){mix[k]+=depth[k];mix2[k]+=depth[k]*depth[k];}
            mix_total+=comp[kIndirect][0];mix_total2+=comp[kIndirect][0]*comp[kIndirect][0];
        }
        Xoshiro256 iid_rng(seed);
        for(uint32_t n=0;n<16384;++n) {
            Rgb comp[kComponents];double trace[9]{};trace[8]=1;
            oracle.sample(x,y,iid_rng,comp,cnt,nullptr,&cache,trace);
            for(int k=1;k<8;++k){iid[k]+=trace[k];iid2[k]+=trace[k]*trace[k];}
            iid_total+=comp[kIndirect][0];iid_total2+=comp[kIndirect][0]*comp[kIndirect][0];
        }
        Oracle::PrimaryCache dark_cache;Xoshiro256 dark_prime(seed);RenderCounters dc;
        dark.sample(x,y,dark_prime,ignored,dc,nullptr,&dark_cache);N010NetRng dark_rng(seed,pixel,0);
        Oracle::WholeAudit da;Rgb dark_comp[kComponents];double dark_depth[8]{};
        dark.whole_sample(x,y,dark_rng,dark_comp,dark_cache,da,dark_depth);
        bool dark_zero=true;for(auto& c:dark_comp)for(auto v:c)dark_zero=dark_zero&&v==0;
        for(auto v:dark_depth)dark_zero=dark_zero&&v==0;
        if(comma)out<<",";comma=true;
        out<<"{\"x\":"<<x<<",\"y\":"<<y<<",\"seed\":"<<seed<<",\"mixture_depth_mean\":[";
        for(int k=1;k<8;++k)out<<(k>1?",":"")<<mix[k]/8192;
        out<<"],\"mixture_depth_second\":[";for(int k=1;k<8;++k)out<<(k>1?",":"")<<mix2[k]/8192;
        out<<"],\"iid_depth_mean\":[";for(int k=1;k<8;++k)out<<(k>1?",":"")<<iid[k]/16384;
        out<<"],\"iid_depth_second\":[";for(int k=1;k<8;++k)out<<(k>1?",":"")<<iid2[k]/16384;
        out<<"],\"mixture_total_mean\":"<<mix_total/8192<<",\"iid_total_mean\":"<<iid_total/16384
           <<",\"mixture_total_second\":"<<mix_total2/8192<<",\"iid_total_second\":"<<iid_total2/16384
           <<",\"dark_exact_zero\":"<<(dark_zero?"true":"false")
           <<",\"own_checks\":"<<audit.own_checks<<",\"attempts\":"<<audit.component_attempts<<",\"nulls\":"<<audit.component_nulls
           <<",\"max_own_log_error\":"<<audit.max_own_log_error<<",\"max_target_fraction\":"<<audit.max_target_error_fraction
           <<",\"max_unconditioned_target_fraction\":"<<audit.max_unconditioned_target_error_fraction
           <<",\"max_weight\":"<<audit.max_weight<<"}";
    }
    out<<"]\n";return out?0:6;
}
'''

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing control')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    for p in (Path(__file__),PLAN,Path(D.__file__),D.HERE/'run_primary_direction_sequence.py'):D.checked(p)
    proof=json.loads(D.checked(D.RESULTS/'218-all-split-path-mixture-diagnosis.json'))
    if not proof['complete'] or not proof['diagnostic_promising']:raise ValueError('completed promising prototype required')
    for p,h in proof['payload_sha256'].items():D.checked(Path(p),h)
    header=next(Path(p) for p in proof['payload_sha256'] if p.endswith('.hpp'))
    original_scene=D.OUT/'sampler-validation-v1/rqmc/A6a.n008';text=D.checked(original_scene).decode()
    edited=D.once(text,'material sphere 0.5 0.5 0.5 0.0 0.0 0.0 1','material sphere 1.0 1.0 1.0 0.0 0.0 0.0 1')
    if D.once(edited,'material sphere 1.0 1.0 1.0 0.0 0.0 0.0 1','material sphere 0.5 0.5 0.5 0.0 0.0 0.0 1')!=text:raise ValueError('scene inverse differs')
    tris=np.array([[float(x) for x in line.split()[2:]] for line in edited.splitlines() if line.startswith('tri ')]).reshape(-1,3,3)
    normals=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);normals/=np.linalg.norm(normals,axis=1)[:,None]
    radii=np.linalg.norm(tris,axis=2);rmin=float(np.min(np.abs(np.sum(normals*tris[:,0],axis=1))));rmax=float(np.max(radii))
    diagonal=float(np.linalg.norm(tris.max((0,1))-tris.min((0,1))));offset=1e-12*diagonal
    delta=offset+1024*np.finfo(float).eps*(1+rmax)
    bounds=[(rmin-delta)/(math.pi*(rmax+delta)**3),(rmax+delta)/(math.pi*(rmin-delta)**3)]
    net=D.OUT/'sobol16x262144.bin';D.checked(net)
    WORK.mkdir();(WORK/'n010_rqmc_oracle.hpp').write_bytes(header.read_bytes());(WORK/'main.cpp').write_text(MAIN)
    scene=WORK/'scene.n008';scene.write_text(edited);pixels=WORK/'pixels.txt';pixels.write_text(''.join(f'{x} {y}\n' for x,y in PIXELS))
    binary=WORK/'n010_furnace_control';data=WORK/'data.json'
    result=dict(schema='n010-bounded-all-split-furnace-control/1',complete=False,all_pass=False,gpu_run=False,reference_admission=False,
        classification='BOUNDED_PHYSICAL_CONTROL_ACQUIRING',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        input_sha256=D.INPUTS,pixels=PIXELS,seeds=list(D.SEEDS),rqmc_spp=8192,iid_spp=16384,
        original_generated_header_byte_identical=True,scene_only_rho_edit_inverse_exact=True,
        furnace_geometry=dict(minimum_face_radius=rmin,maximum_vertex_radius=rmax,offset=offset,roundoff_inclusive_displacement=delta,single_depth_envelope=bounds),
        attempts=[],tests='NOT_RUN; bounded independent scientific control, not full17 suite')
    def save():OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()
    try:
        commands=[['c++','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread','-I',str(D.ROOT/'src/research/n008_hdr_oracle'),str(WORK/'main.cpp'),'-o',str(binary)],
                  [str(binary),str(net),str(scene),str(pixels),str(data)]]
        for i,command in enumerate(commands):
            receipt=WORK/f'step-{i}.resources.json'
            def limits():
                resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(220,)*2)
                receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
            attempt=dict(command=command,elapsed_limit_seconds=300);result['attempts'].append(attempt);save();start=time.monotonic()
            try:proc=subprocess.run(command,capture_output=True,text=True,timeout=300,preexec_fn=limits)
            except subprocess.TimeoutExpired as e:
                (WORK/f'step-{i}.stdout').write_bytes(e.stdout or b'');(WORK/f'step-{i}.stderr').write_bytes(e.stderr or b'');raise ValueError('elapsed guard') from e
            (WORK/f'step-{i}.stdout').write_text(proc.stdout);(WORK/f'step-{i}.stderr').write_text(proc.stderr)
            attempt.update(returncode=proc.returncode,elapsed=time.monotonic()-start,receipt_sha256=sha(receipt));save()
            actual=json.loads(D.checked(receipt))
            if actual['cpu']!=[220,220] or actual['address_space']!=[4*1024**3]*2 or len(actual['affinity'])!=1 or actual['nice']!=15:raise ValueError('actual limits differ')
            if proc.returncode:raise ValueError('compile/native failure, no retry')
        rows=json.loads(D.checked(data))
        if len(rows)!=32 or {(r['x'],r['y'],r['seed']) for r in rows}!={(x,y,s) for x,y in PIXELS for s in D.SEEDS}:raise ValueError('actual scope differs')
        checks=[]
        for r in rows:
            if not r['dark_exact_zero'] or r['nulls']!=0 or r['own_checks']!=7*8192 or r['attempts']!=7*8192 or r['max_own_log_error']>1e-6 or r['max_target_fraction']>1 or r['max_weight']>8:raise ValueError('native audit/closed sphere support failed')
            for key in ('mixture_depth_mean','mixture_depth_second','iid_depth_mean','iid_depth_second'):
                a=np.array(r[key]);
                if not np.isfinite(a).all() or (a<0).any():raise ValueError('nonfinite/negative control')
        for depth in (1,7):
            key='depth_mean' if depth==1 else 'total_mean'
            values={}
            for name in ('mixture','iid'):
                a=np.array([r[name+'_'+key][0] if depth==1 else r[name+'_'+key] for r in rows]).reshape(8,4).mean(1)
                target=depth/math.pi;lower=depth*bounds[0]-.002*target;upper=depth*bounds[1]+.002*target
                good=bool(((a>=lower)&(a<=upper)).all())
                checks.append(dict(kind='analytic_furnace',depth=depth,variant=name,target=target,lower=lower,upper=upper,minimum=float(a.min()),maximum=float(a.max()),pass_=good))
                values[name]=a
            rel=float(abs(values['mixture'].mean()/values['iid'].mean()-1));nrmse=float(np.sqrt(np.mean((values['mixture']-values['iid'])**2)/np.mean(values['iid']**2)))
            checks.append(dict(kind='independent_iid',depth=depth,relative_mean_difference=rel,nrmse=nrmse,pass_=rel<=.002 and nrmse<=.01))
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(complete=True,all_pass=all(c['pass_'] for c in checks),classification='BOUNDED_PHYSICAL_CONTROL_COMPLETE_NO_ADMISSION',checks=checks,dark_exact_zero_all=True,
            scope='Eight derived rho1 furnace pixels, B2/B8, not all17 original controls or corpus qualification')
    except (ValueError,OSError,subprocess.SubprocessError) as e:result.update(classification='BOUNDED_CONTROL_FAILURE_PARTIALS_RETAINED',failure=str(e))
    result['payload_sha256']={str(p):sha(p) for p in WORK.iterdir() if p.is_file()};save()
    print(json.dumps({k:result.get(k) for k in ('complete','all_pass','classification','failure','checks')},indent=2))
    raise SystemExit(0 if result['complete'] and result['all_pass'] else 2)

if __name__=='__main__':main()

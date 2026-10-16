#!/usr/bin/env python3
"""Plan 057: small, low-priority C1 path diagnosis, never reference admission."""
import hashlib
import json
import os
from pathlib import Path
import resource
import struct
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
OUT = ROOT/'out/research/n010-comparison-readiness'
WORK = OUT/'selected-bounce-diagnosis-v1'
TARGET = RESULTS/'193-selected-bounce-path-diagnosis.json'
PLAN = RESULTS.parent/'experiments/057-bounded-cause-diagnosis-and-critical-path.md'
SEEDS = (305419896, 2596069104, 81985529216486895, 18364758544493064720)
INPUTS = {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(path, expected=None):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('input identity changed: '+str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != digest:
        raise ValueError('input changed during diagnosis: '+str(path))
    INPUTS[str(path)] = digest
    return data


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('diagnostic source anchor is not unique')
    return text.replace(old, new)


MAIN = r'''
#include "n010_rqmc_oracle.hpp"
#include <iomanip>
#include <iostream>
using namespace phos::gi::research::n008;
int main(int argc,char** argv) {
    if(argc!=5) return 2;
    N010NetRng::load(argv[1]);
    std::ifstream in(argv[2]); const Scene scene=parse_scene(in);
    const Oracle oracle(scene);
    if(scene.max_bounces!=8||scene.width!=320||scene.height!=180) return 3;
    std::ifstream pixels(argv[3]); uint32_t x,y;
    const std::array<uint64_t,4> seeds={305419896ULL,2596069104ULL,
        81985529216486895ULL,18364758544493064720ULL};
    std::ofstream out(argv[4]); out<<std::setprecision(17)<<"["; bool comma=false;
    while(pixels>>x>>y) {
        if(x>=scene.width||y>=scene.height) return 4;
        for(const auto seed:seeds) {
            const uint32_t spp=8192; const size_t pixel=size_t(y)*scene.width+x;
            Oracle::PrimaryCache cache; RenderCounters cnt;
            double sum[4][3]{},second[4][3]{},bmean[8]{},bcross[8][8]{};
            double weight=0,weight2=0;
            for(uint32_t s=0;s<spp;++s) {
                N010NetRng rng(seed,pixel,s); Rgb comp[kComponents];
                double trace[9]{}; trace[8]=1;
                oracle.sample(x,y,rng,comp,cnt,nullptr,&cache,trace);
                for(int c=0;c<3;++c) {
                    double total=0;
                    for(int k=0;k<kComponents;++k) {
                        sum[k][c]+=comp[k][c];second[k][c]+=comp[k][c]*comp[k][c];
                        total+=comp[k][c];
                    }
                    sum[kComponents][c]+=total;second[kComponents][c]+=total*total;
                }
                for(int i=0;i<8;++i) {
                    bmean[i]+=trace[i];
                    for(int j=0;j<8;++j)bcross[i][j]+=trace[i]*trace[j];
                }
                weight+=trace[8];weight2+=trace[8]*trace[8];
            }
            const double inv=1.0/double(spp);
            if(comma)out<<",";comma=true;
            out<<"{\"x\":"<<x<<",\"y\":"<<y<<",\"seed\":"<<seed<<",\"mean\":[";
            for(int k=0;k<12;++k)out<<(k?",":"")<<sum[k/3][k%3]*inv;
            out<<"],\"second\":[";
            for(int k=0;k<12;++k)out<<(k?",":"")<<second[k/3][k%3]*inv;
            out<<"],\"bounce_mean\":[";
            for(int k=0;k<8;++k)out<<(k?",":"")<<bmean[k]*inv;
            out<<"],\"bounce_cross\":[";
            for(int k=0;k<64;++k)out<<(k?",":"")<<bcross[k/8][k%8]*inv;
            out<<"],\"weight_mean\":"<<weight*inv<<",\"weight_second\":"<<weight2*inv<<"}";
        }
    }
    out<<"]\n";return out?0:5;
}
'''


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3,)*2)
    resource.setrlimit(resource.RLIMIT_CPU, (120,)*2)


def run(command, label, result):
    receipt = {'command':command,'cpu_affinity':sorted(os.sched_getaffinity(0)),
               'nice':os.getpriority(os.PRIO_PROCESS,0),'address_space_bytes':4*1024**3,
               'cpu_seconds':120,'elapsed_limit_seconds':180}
    result['attempts'].append(receipt)
    TARGET.write_text(json.dumps(result, indent=2)+'\n')
    start = time.monotonic()
    try:
        p = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,
                           timeout=180,preexec_fn=limits)
    except subprocess.TimeoutExpired as error:
        (WORK/(label+'.stdout')).write_bytes(error.stdout or b'')
        (WORK/(label+'.stderr')).write_bytes(error.stderr or b'')
        receipt.update(failure='ELAPSED_GUARD_NO_RETRY',elapsed=time.monotonic()-start)
        raise ValueError('diagnostic elapsed guard') from error
    stdout, stderr = WORK/(label+'.stdout'), WORK/(label+'.stderr')
    stdout.write_text(p.stdout);stderr.write_text(p.stderr)
    receipt.update(returncode=p.returncode,elapsed=time.monotonic()-start,
                   stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
    TARGET.write_text(json.dumps(result,indent=2)+'\n')
    if p.returncode: raise ValueError('diagnostic invocation failed; no retry')


def main():
    if WORK.exists() or TARGET.exists(): raise ValueError('refuse existing diagnosis')
    sys.path.insert(0,str(HERE.parent/'n010_comparison_readiness'))
    from run_primary_direction_sequence import require_no_other_research_worker
    from build_nested_scramble import OLD_UNIFORM, NEW_UNIFORM
    require_no_other_research_worker()
    os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    for path in (Path(__file__).resolve(),PLAN,HERE/'run_primary_direction_sequence.py',
                 HERE/'build_nested_scramble.py',RESULTS/'191-posthoc-readiness-bottleneck-diagnosis.json'):
        checked(path)
    original_dir=OUT/'references-recovery-sponza-v1/C1_T_B8'
    q=json.loads(checked(original_dir/'qualification.json',
        '9da5eece00c7e1e490a35aefceb0a54f7ea42b0a90b4ad655d6713c482a9fa8f'))
    payloads=q['levels'][0]['all_payload_sha256']
    means=[];retained={}
    for i,seed in enumerate(SEEDS):
        p=original_dir/f'o.n8192.s{i}.f64';raw=checked(p,payloads[p.name])
        if struct.unpack_from('<IIIQ',raw,8)!=(320,180,8192,seed):raise ValueError('sidecar identity')
        retained['original',seed]=np.frombuffer(raw,dtype='<f8',offset=28).reshape(180,320,24)
        means.append(retained['original',seed][...,6:9]@np.array((.2126,.7152,.0722)))
    means=np.stack(means);energy=np.sum((means-means.mean(0))**2,axis=0).ravel()
    order=np.lexsort((np.arange(energy.size),-energy))
    selected=list(map(int,order[:8]))
    for x,y in ((40,30),(120,30),(200,30),(280,30),(40,150),(120,150),(200,150),(280,150)):
        if y*320+x not in selected:selected.append(y*320+x)
    for i in order:
        if len(selected)==16:break
        if int(i) not in selected:selected.append(int(i))
    guided=json.loads(checked(RESULTS/'180-primary-direction-second-stop-bounded-feasibility.json'))
    if not guided['complete'] or guided['all_pass']:raise ValueError('terminal failed 180 required')
    for i,seed in enumerate(SEEDS):
        p=OUT/f'primary-direction-feasibility-recovery-v3/o.n8192.s{i}.f64'
        raw=checked(p,guided['levels'][0]['payload_sha256'][f'.s{i}.f64'])
        if struct.unpack_from('<IIIQ',raw,8)!=(320,180,8192,seed):raise ValueError('guided sidecar identity')
        retained['guided',seed]=np.frombuffer(raw,dtype='<f8',offset=28).reshape(180,320,24)
    WORK.mkdir()
    pixels=WORK/'pixels.txt';pixels.write_text(''.join(f'{i%320} {i//320}\n' for i in selected))
    net=OUT/'sobol16x262144.bin';scene=original_dir/'scene.n008'
    checked(net);checked(scene)
    result={'schema':'n010-selected-bounce-path-diagnosis/1','complete':False,'gpu_run':False,
        'classification':'POST_HOC_DIAGNOSTIC_ACQUIRING_NO_ADMISSION',
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'input_sha256':INPUTS,'selected_pixels':[[i%320,i//320] for i in selected],
        'selection_scope':'Post-hoc original-8192 energy tails plus fixed grid; C1 only, not acceptance',
        'seeds':list(SEEDS),'spp':8192,'attempts':[],'variants':[],
        'reference_admission':False,'tests':'NOT_RUN; selected-path scientific diagnosis'}
    TARGET.write_text(json.dumps(result,indent=2)+'\n')
    try:
        for variant,build_number,folder in (('original',187,'owen-reference-build-v1'),
                ('guided',151,'primary-direction-build-v1'),('nested',187,'owen-reference-build-v1')):
            require_no_other_research_worker()
            proof=json.loads(checked(next(RESULTS.glob(f'{build_number}-*.json'))))
            if not proof['complete'] or not proof['all_pass']:raise ValueError('build proof missing')
            p=OUT/folder/'standalone/n010_rqmc_oracle.hpp'
            source=checked(p,proof['generated_sha256'][p.name]).decode()
            if variant=='original':source=once(source,NEW_UNIFORM,OLD_UNIFORM)
            original=source
            edits=[('PrimaryCache* cache = nullptr) const {',
                    'PrimaryCache* cache = nullptr, double* diagnostic_bounce = nullptr) const {'),
                   ('            if (bounce + 1 >= scene_.max_bounces) return;',
                    '            if(diagnostic_bounce) diagnostic_bounce[bounce] = '
                    '0.2126*(throughput[0]*f[0]*e[0]) + 0.7152*(throughput[1]*f[1]*e[1]) + 0.0722*(throughput[2]*f[2]*e[2]);\n'
                    '            if (bounce + 1 >= scene_.max_bounces) return;')]
            if variant=='guided':edits.append(('                ray={origin,draw.direction};',
                '                if(diagnostic_bounce) diagnostic_bounce[8]=draw.correction;\n'
                '                ray={origin,draw.direction};'))
            for old,new in edits:source=once(source,old,new)
            restored=source
            for old,new in reversed(edits):restored=once(restored,new,old)
            if restored!=original:raise ValueError('instrumentation inverse failed')
            directory=WORK/variant;directory.mkdir()
            header=directory/'n010_rqmc_oracle.hpp';header.write_text(source)
            main=directory/'main.cpp';main.write_text(MAIN)
            binary=directory/'n010_bounce_diagnostic';data_path=directory/'data.json'
            run(['c++','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread',
                 '-I',str(ROOT/'src/research/n008_hdr_oracle'),str(main),'-o',str(binary)],variant+'-compile',result)
            run([str(binary),str(net),str(scene),str(pixels),str(data_path)],variant+'-native',result)
            rows=json.loads(data_path.read_text())
            if len(rows)!=64:raise ValueError('selected path result scope differs')
            exact=None
            if variant!='nested':
                exact=all(np.asarray(r['mean']+r['second'],dtype='<f8').tobytes()==
                    retained[variant,r['seed']][r['y'],r['x']].tobytes() for r in rows)
                if not exact:raise ValueError('instrumentation failed bit-exact retained moment replay')
            grouped=np.array([[next(r['bounce_mean'] for r in rows if r['x']==i%320 and r['y']==i//320 and r['seed']==seed)
                               for seed in SEEDS] for i in selected])
            centered=grouped-grouped.mean(1,keepdims=True)
            replicate_cov=np.einsum('psb,psc->bc',centered,centered)
            covs=np.asarray([np.array(r['bounce_cross']).reshape(8,8)-np.outer(r['bounce_mean'],r['bounce_mean']) for r in rows])
            later=covs[:,2:,2:].sum((1,2));whole=covs[:,1:,1:].sum((1,2))
            summary={'variant':variant,'whole_header_instrumentation_inverse_exact':True,
                'unmodified_header_sha256':hashlib.sha256(original.encode()).hexdigest(),
                'selected_retained_mean_second_bit_exact':exact,
                'payload_sha256':{str(p):sha(p) for p in (header,main,binary,data_path)},
                'selected_replicate_bounce_cross_energy':replicate_cov.tolist(),
                'selected_full_indirect_replicate_energy':float(replicate_cov[1:,1:].sum()),
                'selected_first_indirect_replicate_energy':float(replicate_cov[1,1]),
                'selected_later_indirect_replicate_energy':float(replicate_cov[2:,2:].sum()),
                'path_moments_not_rqmc_standard_errors':{
                    'first_indirect_variance_sum':float(covs[:,1,1].sum()),
                    'later_indirect_variance_sum':float(later.sum()),
                    'full_indirect_variance_sum':float(whole.sum()),
                    'first_later_covariance_sum':float(covs[:,1,2:].sum()),
                    'weight_mean':float(np.mean([r['weight_mean'] for r in rows])),
                    'weight_second':float(np.mean([r['weight_second'] for r in rows]))}}
            result['variants'].append(summary)
            TARGET.write_text(json.dumps(result,indent=2)+'\n')
            print(variant,json.dumps({k:v for k,v in summary.items() if k.startswith('selected_') and k!='selected_replicate_bounce_cross_energy'}),flush=True)
        for p,digest in INPUTS.items():
            if sha(Path(p))!=digest:raise ValueError('input changed during selected-path diagnosis')
        result.update(complete=True,classification='POST_HOC_DIAGNOSTIC_COMPLETE_NO_ADMISSION')
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        result.update(complete=False,classification='DIAGNOSTIC_OPERATIONAL_FAILURE_PARTIALS_RETAINED',failure=str(error))
    TARGET.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    raise SystemExit(0 if result['complete'] else 2)


if __name__=='__main__':main()

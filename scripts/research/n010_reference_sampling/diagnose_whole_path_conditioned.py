#!/usr/bin/env python3
"""Plan069: explicit geometric backward-error audit amendment, original mixture."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

import numpy as np
import diagnose_selected_bounce_paths as D
import diagnose_readiness_bottlenecks as B
from run_primary_direction_sequence import require_no_other_research_worker

WORK=D.OUT/'whole-path-conditioned-diagnosis-v1'
OUTPUT=D.RESULTS/'212-whole-path-conditioned-diagnosis.json'
PLAN=D.RESULTS.parent/'experiments/069-conditioned-raw-target-numeric-audit.md'
PIXELS=[(40,30),(120,30),(200,30),(280,30),(40,150),(120,150),(200,150),(280,150)]



def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing CV diagnosis')
    require_no_other_research_worker()
    os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    for p in (Path(__file__),PLAN,Path(D.__file__),Path(B.__file__),D.HERE/'whole_path_conditioned.inc',
              D.HERE/'run_primary_direction_sequence.py'):
        D.checked(p)
    witness=json.loads(D.checked(D.RESULTS/'211-whole-path-numeric-failure-witness.json'))
    if not witness['complete'] or witness['classification']!='POSTHOC_SAME_GUARD_REPRODUCED_NO_ADMISSION':raise ValueError('actual previous witness required')
    original_inclusion=D.checked(D.HERE/'whole_path_mixture.inc').decode()
    revised_inclusion=D.checked(D.HERE/'whole_path_conditioned.inc').decode()
    audit_old='''            audit.max_target_error_fraction=std::max(audit.max_target_error_fraction,error/bound);
            if(error>bound)throw std::runtime_error("raw-target closest-hit reconstruction error");'''
    audit_new='''            const auto& numeric_triangle=scene_.triangles.at(target.triangle);
            const auto numeric_normal=normalize(cross(numeric_triangle.v1-numeric_triangle.v0,numeric_triangle.v2-numeric_triangle.v0));
            const double target_plane_error=std::abs(dot(numeric_normal,target.point-numeric_triangle.v0));
            const double actual_plane_error=std::abs(dot(numeric_normal,actual-numeric_triangle.v0));
            const double conditioned_error=error*std::abs(dot(numeric_normal,direction));
            const double certified_error=std::max({target_plane_error,actual_plane_error,conditioned_error});
            audit.max_unconditioned_target_error_fraction=std::max(audit.max_unconditioned_target_error_fraction,error/bound);
            audit.max_target_error_fraction=std::max(audit.max_target_error_fraction,certified_error/bound);
            if(certified_error>bound)throw std::runtime_error("conditioned raw-target/plane reconstruction error");'''
    edits=[(audit_old,audit_new),('double max_own_log_error{},max_target_error_fraction{},max_weight{};',
        'double max_own_log_error{},max_target_error_fraction{},max_weight{},max_unconditioned_target_error_fraction{};')]
    expected=original_inclusion
    for a,b in edits:expected=D.once(expected,a,b)
    if expected!=revised_inclusion:raise ValueError('non-diagnostic whole-path implementation changed')
    for a,b in reversed(edits):expected=D.once(expected,b,a)
    if expected!=original_inclusion:raise ValueError('original inclusion inverse differs')
    proof=json.loads(D.checked(D.RESULTS/'193-selected-bounce-path-diagnosis.json'))
    old=next(v for v in proof['variants'] if v['variant']=='original')
    if not proof['complete'] or not old['selected_retained_mean_second_bit_exact']:
        raise ValueError('exact completed original diagnostic required')
    for p,h in old['payload_sha256'].items():D.checked(Path(p),h)
    header=next(Path(p) for p in old['payload_sha256'] if p.endswith('.hpp'))
    original=header.read_text()
    pairs=[('    // One camera sample; writes per-component radiance.',
        (D.HERE/'whole_path_conditioned.inc').read_text()+'\n    // One camera sample; writes per-component radiance.')]

    generated=original
    for a,b in pairs:generated=D.once(generated,a,b)
    restored=generated
    for a,b in reversed(pairs):restored=D.once(restored,b,a)
    if restored!=original:raise ValueError('whole CV header inverse differs')
    original_main=D.MAIN;main_source=original_main
    restriction=r'''
    const Oracle oracle(scene);
    if(scene.sampling!=Sampling::Center||scene.points.size()!=1)return 6;
    for(const auto& m:scene.materials) {
        if(!m.two_sided)return 7;
        for(int c=0;c<3;++c)if(m.rho[c]!=1||m.emit[c]!=0)return 8;
    }
    const auto& intensity=scene.points[0].intensity;
    if(intensity[0]!=intensity[1]||intensity[1]!=intensity[2]||!(intensity[0]>0))return 9;
'''
    main_pairs=[('    const Oracle oracle(scene);',restriction),
        ('double sum[4][3]{},second[4][3]{},bmean[8]{},bcross[8][8]{};',
         'double sum[4][3]{},second[4][3]{},bmean[8]{},bcross[8][8]{},mixsum[4][3]{},mixsecond[4][3]{},depthmean[8]{};Oracle::WholeAudit audit;'),
        ('oracle.sample(x,y,rng,comp,cnt,nullptr,&cache,trace);',r'''
                oracle.sample(x,y,rng,comp,cnt,nullptr,&cache,trace);
                N010NetRng mixture_rng(seed,pixel,s);Rgb mixture[kComponents];double depth[8]{};
                oracle.whole_sample(x,y,mixture_rng,mixture,cache,audit,depth);
                for(int j=0;j<8;++j)depthmean[j]+=depth[j];
'''),
        ('                for(int i=0;i<8;++i) {',r'''
                for(int c=0;c<3;++c) {
                    double total=0;
                    for(int k=0;k<kComponents;++k) {
                        const double value=mixture[k][c];mixsum[k][c]+=value;mixsecond[k][c]+=value*value;total+=value;
                    }
                    mixsum[kComponents][c]+=total;mixsecond[kComponents][c]+=total*total;
                }
                for(int i=0;i<8;++i) {
'''),
        ('out<<"],\\"weight_mean\\":"<<weight*inv<<",\\"weight_second\\":"<<weight2*inv<<"}";',r'''
            out<<"],\"weight_mean\":"<<weight*inv<<",\"weight_second\":"<<weight2*inv<<",\"mixture_mean\":[";
            for(int k=0;k<12;++k)out<<(k?",":"")<<mixsum[k/3][k%3]*inv;
            out<<"],\"mixture_second\":[";
            for(int k=0;k<12;++k)out<<(k?",":"")<<mixsecond[k/3][k%3]*inv;
            out<<"],\"mixture_depth_mean\":[";
            for(int k=0;k<8;++k)out<<(k?",":"")<<depthmean[k]*inv;
            out<<"],\"audit\":{\"eye_samples\":"<<audit.eye_samples<<",\"light_samples\":"<<audit.light_samples
               <<",\"prefixes\":"<<audit.prefixes<<",\"forward_null\":"<<audit.forward_null
               <<",\"opposite_zero\":"<<audit.opposite_zero<<",\"density_reconstructions\":"<<audit.density_reconstructions
               <<",\"bvh_queries\":"<<audit.bvh_queries<<",\"own_checks\":"<<audit.own_checks
               <<",\"max_own_log_error\":"<<audit.max_own_log_error
               <<",\"max_target_error_fraction\":"<<audit.max_target_error_fraction
               <<",\"max_unconditioned_target_error_fraction\":"<<audit.max_unconditioned_target_error_fraction
               <<",\"max_weight\":"<<audit.max_weight
               <<",\"endpoint_shadow_tests\":"<<audit.direct_counters.shadow_tests
               <<",\"endpoint_shadow_blocked\":"<<audit.direct_counters.shadow_blocked<<"}}";
''')]

    for a,b in main_pairs:main_source=D.once(main_source,a,b)
    restored=main_source
    for a,b in reversed(main_pairs):restored=D.once(restored,b,a)
    if restored!=original_main:raise ValueError('whole CV main inverse differs')
    data_old=next(Path(p) for p in old['payload_sha256'] if p.endswith('/data.json'))
    retained=json.loads(data_old.read_bytes())
    net=D.OUT/'sobol16x262144.bin';scene=D.OUT/'references-recovery-sponza-v1/C1_T_B8/scene.n008'
    D.checked(net);D.checked(scene)
    WORK.mkdir()
    (WORK/'n010_rqmc_oracle.hpp').write_text(generated);(WORK/'main.cpp').write_text(main_source)
    pixels=WORK/'pixels.txt';pixels.write_text(''.join(f'{x} {y}\n' for x,y in PIXELS))
    binary=WORK/'n010_whole_path_diagnostic';data_path=WORK/'data.json'
    result=dict(schema='n010-whole-path-conditioned-diagnosis/1',complete=False,gpu_run=False,
        classification='DIAGNOSTIC_ACQUIRING_NO_ADMISSION',reference_admission=False,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        input_sha256=D.INPUTS,pixels=PIXELS,spp=8192,seeds=list(D.SEEDS),
        whole_header_and_main_inverse_exact=True,inclusion_only_numeric_edits_proved=True,numerical_guard_amendment='069; original 210 guard failed; geometric backward-error audit explicitly replaced',attempts=[],
        tests='NOT_RUN; paired original/whole-path scientific prototype only')
    def save():OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()
    try:
        commands=[['c++','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread',
            '-I',str(D.ROOT/'src/research/n008_hdr_oracle'),str(WORK/'main.cpp'),'-o',str(binary)],
            [str(binary),str(net),str(scene),str(pixels),str(data_path)]]
        for i,command in enumerate(commands):
            receipt=WORK/f'step-{i}.resources.json'
            def limits():
                resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(220,)*2)
                receipt.write_text(json.dumps(dict(pid=os.getpid(),
                    start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
            attempt=dict(command=command,elapsed_limit_seconds=300);result['attempts'].append(attempt);save();start=time.monotonic()
            try:proc=subprocess.run(command,capture_output=True,text=True,timeout=300,preexec_fn=limits)
            except subprocess.TimeoutExpired as e:
                (WORK/f'step-{i}.stdout').write_bytes(e.stdout or b'');(WORK/f'step-{i}.stderr').write_bytes(e.stderr or b'')
                raise ValueError('elapsed guard, retained partials') from e
            (WORK/f'step-{i}.stdout').write_text(proc.stdout);(WORK/f'step-{i}.stderr').write_text(proc.stderr)
            attempt.update(returncode=proc.returncode,elapsed=time.monotonic()-start,receipt_sha256=sha(receipt));save()
            actual=json.loads(D.checked(receipt))
            if actual['cpu']!=[220,220] or actual['address_space']!=[4*1024**3]*2 or len(actual['affinity'])!=1 or actual['nice']!=15:
                raise ValueError('actual low-load resource limits differ')
            if proc.returncode:raise ValueError('native/compile failure; no retry')
        rows=json.loads(D.checked(data_path))
        if len(rows)!=32 or {(r['x'],r['y'],r['seed']) for r in rows}!={(x,y,s) for x,y in PIXELS for s in D.SEEDS}:
            raise ValueError('actual diagnostic scope differs')
        original_exact=all(np.asarray(r['mean']+r['second'],dtype='<f8').tobytes()==
            np.asarray(next(z['mean']+z['second'] for z in retained if (z['x'],z['y'],z['seed'])==(r['x'],r['y'],r['seed'])),dtype='<f8').tobytes() for r in rows)
        if not original_exact:raise ValueError('original paths/moments changed')
        for r in rows:
            a=r['audit']
            if r['mixture_mean'][:6]!=r['mean'][:6]:raise ValueError('mixture deterministic components differ')
            if (a['eye_samples']!=4096 or a['light_samples']!=4096 or a['own_checks']!=a['prefixes'] or
                a['max_own_log_error']>1e-6 or a['max_target_error_fraction']>1 or a['max_weight']>2):
                raise ValueError('mixture counts/own-density reconstruction failed')
        variants=[]
        for name,prefix in (('original',''),('mixture','mixture_')):
            m=np.array([[next(r[prefix+'mean'] for r in rows if (r['x'],r['y'],r['seed'])==(x,y,seed)) for x,y in PIXELS] for seed in D.SEEDS]).reshape(4,8,4,3)
            second=np.array([[next(r[prefix+'second'] for r in rows if (r['x'],r['y'],r['seed'])==(x,y,seed)) for x,y in PIXELS] for seed in D.SEEDS]).reshape(4,8,4,3)
            if not np.isfinite(m).all() or not np.isfinite(second).all() or (m<0).any() or (second<0).any():raise ValueError('nonfinite corrected/original moments')
            luma=m[...,2,:]@B.LUMA
            variants.append(dict(variant=name,max_pairwise_indirect_p99=B.pairwise_p99(luma),
                indirect_replicate_variance_sum=float(np.var(luma,axis=0,ddof=1).sum()),
                mean_path_variance_sum=float(np.maximum(second[...,2,0]-m[...,2,0]**2,0).mean(0).sum()),
                negative_indirect_mean_values=int((m[...,2,:]<0).sum())))
        ratios={k:variants[1][k]/variants[0][k] for k in ('max_pairwise_indirect_p99','indirect_replicate_variance_sum','mean_path_variance_sum')}
        promising=ratios['max_pairwise_indirect_p99']<=.75 and ratios['indirect_replicate_variance_sum']<=.75**2
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(complete=True,classification='DIAGNOSTIC_COMPLETE_NO_ADMISSION',original_mean_second_bit_exact=True,deterministic_components_bit_exact=True,all_prefix_own_density_reconstruction_pass=True,
            variants=variants,mixture_over_original=ratios,diagnostic_promising=promising,
            payload_sha256={str(p):sha(p) for p in WORK.iterdir() if p.is_file()},
            scope='Eight fixed C1 pixels, one level/four seeds, no physical/full-frame/state/prefix proof or reference admission')
    except (ValueError,OSError,subprocess.SubprocessError) as e:
        result.update(classification='OPERATIONAL_FAILURE_PARTIALS_RETAINED',failure=str(e))
    save()
    print(json.dumps({k:result.get(k) for k in ('complete','classification','failure','diagnostic_promising','mixture_over_original')},indent=2))
    raise SystemExit(0 if result['complete'] else 2)


if __name__=='__main__':main()

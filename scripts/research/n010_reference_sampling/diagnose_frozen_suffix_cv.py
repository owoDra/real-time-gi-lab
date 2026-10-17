#!/usr/bin/env python3
"""Plan 066: independent frozen full-suffix table correction diagnosis only."""
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

WORK=D.OUT/'frozen-suffix-cv-diagnosis-v1'
OUTPUT=D.RESULTS/'209-frozen-suffix-cv-diagnosis.json'
PLAN=D.RESULTS.parent/'experiments/066-frozen-suffix-control-variate-diagnosis.md'
PIXELS=[(40,30),(120,30),(200,30),(280,30),(40,150),(120,150),(200,150),(280,150)]

PREDICT=r'''
    struct N010TrainVertex {V3 origin,normal;uint32_t bounce;double u,v;};
    struct N010SuffixModel {
        struct Cell {std::array<double,16> sum{};std::array<uint32_t,16> count{};};
        std::vector<Cell> cells=std::vector<Cell>(32768);
        Aabb box;std::array<double,8> global{};std::array<uint64_t,8> global_count{};
        uint64_t paths{},vertices{};
        explicit N010SuffixModel(const Scene& scene) {
            for(const auto& t:scene.triangles){box.grow(t.v0);box.grow(t.v1);box.grow(t.v2);}
        }
        uint32_t key(V3 origin,V3 normal,uint32_t bounce) const {
            if(bounce<1||bounce>6)throw std::runtime_error("suffix model bounce");
            uint32_t value=bounce*8+((normal.x>=0?1:0)|(normal.y>=0?2:0)|(normal.z>=0?4:0));
            for(int c=0;c<3;++c) {
                const double width=box.hi[c]-box.lo[c];
                const double t=width>0?std::clamp((origin[c]-box.lo[c])/width,0.0,1.0):0.0;
                value=value*8+std::min(7U,uint32_t(8*t));
            }
            if(value>=cells.size())throw std::runtime_error("suffix model key bound");
            return value;
        }
        static unsigned bin(double u,double v) {return 4*std::min(3,int(4*u))+std::min(3,int(4*v));}
        void add(const N010TrainVertex& vertex,double suffix) {
            if(!std::isfinite(suffix)||suffix<0)throw std::runtime_error("suffix pilot invalid");
            auto& cell=cells[key(vertex.origin,vertex.normal,vertex.bounce)];const auto a=bin(vertex.u,vertex.v);
            cell.sum[a]+=suffix;++cell.count[a];global[vertex.bounce]+=suffix;++global_count[vertex.bounce];++vertices;
        }
        double delta(V3 origin,V3 normal,uint32_t bounce,double u,double v) const {
            const auto& cell=cells[key(origin,normal,bounce)];
            const double prior=global_count[bounce]?global[bounce]/global_count[bounce]:0;
            std::array<double,16> values{};double average=0;
            for(int a=0;a<16;++a){values[a]=(cell.sum[a]+32*prior)/(cell.count[a]+32);average+=values[a]*(1.0/16);}
            return average-values[bin(u,v)];
        }
        void dump(const std::string& name) const {
            std::ofstream out(name);out.precision(17);
            out<<"pilot_paths "<<paths<<"\nvertices "<<vertices<<"\ngrid 8 normal_octants 8 direction_bins 4 prior 32 seed 88275743102001\n";
            for(unsigned j=0;j<8;++j)out<<"global "<<j<<" "<<global[j]<<" "<<global_count[j]<<"\n";
            for(size_t i=0;i<cells.size();++i)for(unsigned a=0;a<16;++a)if(cells[i].count[a])
                out<<i<<" "<<a<<" "<<cells[i].sum[a]<<" "<<cells[i].count[a]<<"\n";
            if(!out)throw std::runtime_error("suffix model dump");
        }
    };
'''

CORRECT=r'''
            if(bounce>=1) {
                if(diagnostic_vertices)diagnostic_vertices->push_back({origin,n,bounce,n010_u1,n010_u2});
                if(diagnostic_cv&&diagnostic_model) {
                    const double delta=diagnostic_model->delta(origin,n,bounce,n010_u1,n010_u2);
                    for(int c=0;c<3;++c)(*diagnostic_cv)[c]+=throughput[c]*delta;
                }
            }
'''

TRAIN=r'''
    const Oracle oracle(scene);
    if(scene.sampling!=Sampling::Center)return 6;
    for(const auto& m:scene.materials) {
        if(!m.two_sided)return 7;
        for(int c=0;c<3;++c)if(m.rho[c]!=1||m.emit[c]!=0)return 8;
    }
    for(const auto& p:scene.points)if(p.intensity[0]!=p.intensity[1]||p.intensity[1]!=p.intensity[2])return 9;
    Oracle::N010SuffixModel model(scene);
    {
        std::ifstream training_pixels(argv[3]);uint32_t px,py;
        while(training_pixels>>px>>py) {
            Oracle::PrimaryCache cache;RenderCounters counters;
            for(uint32_t s=0;s<8192;++s) {
                N010NetRng rng(0x50494c4f5431ULL,size_t(py)*scene.width+px,s);
                Rgb comp[kComponents];double trace[9]{};std::vector<Oracle::N010TrainVertex> vertices;
                oracle.sample(px,py,rng,comp,counters,nullptr,&cache,trace,nullptr,nullptr,&vertices);
                ++model.paths;
                for(const auto& vertex:vertices) {
                    double suffix=0;for(unsigned j=vertex.bounce+1;j<8;++j)suffix+=trace[j];
                    model.add(vertex,suffix);
                }
            }
        }
    }
    if(model.paths!=65536)return 10;
    model.dump(std::string(argv[4])+".model-before.txt");
'''


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing CV diagnosis')
    require_no_other_research_worker()
    os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    for p in (Path(__file__),PLAN,Path(D.__file__),Path(B.__file__),
              D.HERE/'run_primary_direction_sequence.py'):
        D.checked(p)
    proof=json.loads(D.checked(D.RESULTS/'193-selected-bounce-path-diagnosis.json'))
    old=next(v for v in proof['variants'] if v['variant']=='original')
    if not proof['complete'] or not old['selected_retained_mean_second_bit_exact']:
        raise ValueError('exact completed original diagnostic required')
    for p,h in old['payload_sha256'].items():D.checked(Path(p),h)
    header=next(Path(p) for p in old['payload_sha256'] if p.endswith('.hpp'))
    original=header.read_text()
    pairs=[('    // One camera sample; writes per-component radiance.',PREDICT+'\n    // One camera sample; writes per-component radiance.'),
        ('double* diagnostic_bounce = nullptr) const {',
         'double* diagnostic_bounce = nullptr, Rgb* diagnostic_cv = nullptr, const N010SuffixModel* diagnostic_model=nullptr, std::vector<N010TrainVertex>* diagnostic_vertices=nullptr) const {\n        if(diagnostic_cv)*diagnostic_cv={0,0,0};'),
        ('            const double n010_u1 = rng.uniform(), n010_u2 = rng.uniform();',
         '            const double n010_u1 = rng.uniform(), n010_u2 = rng.uniform();'+CORRECT)]
    generated=original
    for a,b in pairs:generated=D.once(generated,a,b)
    restored=generated
    for a,b in reversed(pairs):restored=D.once(restored,b,a)
    if restored!=original:raise ValueError('whole CV header inverse differs')
    original_main=D.MAIN;main_source=original_main
    main_pairs=[('    const Oracle oracle(scene);',TRAIN),
        ('    out<<"]\\n";return out?0:5;', '    model.dump(std::string(argv[4])+".model-after.txt");\n    out<<"]\\n";return out?0:5;'),
        ('double sum[4][3]{},second[4][3]{},bmean[8]{},bcross[8][8]{};',
        'double sum[4][3]{},second[4][3]{},bmean[8]{},bcross[8][8]{},cvsum[4][3]{},cvsecond[4][3]{};'),
        ('oracle.sample(x,y,rng,comp,cnt,nullptr,&cache,trace);',
         'Rgb correction{};oracle.sample(x,y,rng,comp,cnt,nullptr,&cache,trace,&correction,&model);'),
        ('                for(int i=0;i<8;++i) {',r'''
                for(int c=0;c<3;++c) {
                    double total=0;
                    for(int k=0;k<kComponents;++k) {
                        const double value=comp[k][c]+(k==kIndirect?correction[c]:0.0);
                        cvsum[k][c]+=value;cvsecond[k][c]+=value*value;total+=value;
                    }
                    cvsum[kComponents][c]+=total;cvsecond[kComponents][c]+=total*total;
                }
                for(int i=0;i<8;++i) {'''),
        ('out<<"],\\"weight_mean\\":"<<weight*inv<<",\\"weight_second\\":"<<weight2*inv<<"}";',r'''
            out<<"],\"weight_mean\":"<<weight*inv<<",\"weight_second\":"<<weight2*inv<<",\"cv_mean\":[";
            for(int k=0;k<12;++k)out<<(k?",":"")<<cvsum[k/3][k%3]*inv;
            out<<"],\"cv_second\":[";
            for(int k=0;k<12;++k)out<<(k?",":"")<<cvsecond[k/3][k%3]*inv;
            out<<"]}";''')]
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
    binary=WORK/'n010_suffix_cv_diagnostic';data_path=WORK/'data.json'
    result=dict(schema='n010-frozen-suffix-cv-diagnosis/1',complete=False,gpu_run=False,
        classification='DIAGNOSTIC_ACQUIRING_NO_ADMISSION',reference_admission=False,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        input_sha256=D.INPUTS,pixels=PIXELS,spp=8192,seeds=list(D.SEEDS),
        whole_header_and_main_inverse_exact=True,attempts=[],
        tests='NOT_RUN; independent-pilot paired-path scientific prototype only')
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
        before=D.checked(Path(str(data_path)+'.model-before.txt'))
        after=D.checked(Path(str(data_path)+'.model-after.txt'))
        if before!=after or not before.startswith(b'pilot_paths 65536\n'):raise ValueError('pilot scope/model freeze differs')
        rows=json.loads(D.checked(data_path))
        if len(rows)!=32 or {(r['x'],r['y'],r['seed']) for r in rows}!={(x,y,s) for x,y in PIXELS for s in D.SEEDS}:
            raise ValueError('actual diagnostic scope differs')
        original_exact=all(np.asarray(r['mean']+r['second'],dtype='<f8').tobytes()==
            np.asarray(next(z['mean']+z['second'] for z in retained if (z['x'],z['y'],z['seed'])==(r['x'],r['y'],r['seed'])),dtype='<f8').tobytes() for r in rows)
        if not original_exact:raise ValueError('original paths/moments changed')
        if any(r['cv_mean'][:6]!=r['mean'][:6] for r in rows):raise ValueError('deterministic components changed')
        variants=[]
        for name,prefix in (('original',''),('corrected','cv_')):
            m=np.array([[next(r[prefix+'mean'] for r in rows if (r['x'],r['y'],r['seed'])==(x,y,seed)) for x,y in PIXELS] for seed in D.SEEDS]).reshape(4,8,4,3)
            second=np.array([[next(r[prefix+'second'] for r in rows if (r['x'],r['y'],r['seed'])==(x,y,seed)) for x,y in PIXELS] for seed in D.SEEDS]).reshape(4,8,4,3)
            if not np.isfinite(m).all() or not np.isfinite(second).all():raise ValueError('nonfinite corrected/original moments')
            luma=m[...,2,:]@B.LUMA
            variants.append(dict(variant=name,max_pairwise_indirect_p99=B.pairwise_p99(luma),
                indirect_replicate_variance_sum=float(np.var(luma,axis=0,ddof=1).sum()),
                mean_path_variance_sum=float(np.maximum(second[...,2,0]-m[...,2,0]**2,0).mean(0).sum()),
                negative_indirect_mean_values=int((m[...,2,:]<0).sum())))
        ratios={k:variants[1][k]/variants[0][k] for k in ('max_pairwise_indirect_p99','indirect_replicate_variance_sum','mean_path_variance_sum')}
        promising=ratios['max_pairwise_indirect_p99']<=.75 and ratios['indirect_replicate_variance_sum']<=.75**2
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(complete=True,classification='DIAGNOSTIC_COMPLETE_NO_ADMISSION',original_mean_second_bit_exact=True,deterministic_components_bit_exact=True,pilot_paths=65536,model_dump_bit_exact_before_after=True,
            variants=variants,corrected_over_original=ratios,diagnostic_promising=promising,
            payload_sha256={str(p):sha(p) for p in WORK.iterdir() if p.is_file()},
            scope='Eight fixed C1 pixels, one level/four seeds, no physical/full-frame/state/prefix proof or reference admission')
    except (ValueError,OSError,subprocess.SubprocessError) as e:
        result.update(classification='OPERATIONAL_FAILURE_PARTIALS_RETAINED',failure=str(e))
    save()
    print(json.dumps({k:result.get(k) for k in ('complete','classification','failure','diagnostic_promising','corrected_over_original')},indent=2))
    raise SystemExit(0 if result['complete'] else 2)


if __name__=='__main__':main()

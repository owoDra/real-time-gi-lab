#!/usr/bin/env python3
"""Plan 062: eight-pixel array-RQMC prototype with the original physical body."""
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

WORK=D.OUT/'array-rqmc-transport-diagnosis-v1'
OUTPUT=D.RESULTS/'203-array-rqmc-transport-diagnosis.json'
PLAN=D.RESULTS.parent/'experiments/062-array-rqmc-transport-diagnosis.md'
PIXELS=[(40,30),(120,30),(200,30),(280,30),(40,150),(120,150),(200,150),(280,150)]

MAIN=r'''
#include "n010_rqmc_oracle.hpp"
#include <iomanip>
#include <numeric>
using namespace phos::gi::research::n008;
constexpr uint32_t count=8192;
struct PathState {
    std::array<double,16> coordinates{};
    Oracle::N010ArrayVertex vertex;
    std::array<Rgb,3> components{};
    uint64_t key{};
};
struct ReplayRng {
    const std::array<double,16>& coordinates;unsigned dim{};
    double uniform(){if(dim>=14)throw std::runtime_error("array RNG dimension");return coordinates[dim++];}
};
struct Stats {
    double sum[4][3]{},second[4][3]{};
    void add(const Rgb* components) {
        for(int c=0;c<3;++c) {
            double total=0;
            for(int k=0;k<3;++k) {const double value=components[k][c];sum[k][c]+=value;second[k][c]+=value*value;total+=value;}
            sum[3][c]+=total;second[3][c]+=total*total;
        }
    }
    void write(std::ostream& out,const char* prefix)const {
        out<<",\""<<prefix<<"mean\":[";
        for(int k=0;k<12;++k)out<<(k?",":"")<<sum[k/3][k%3]/count;
        out<<"],\""<<prefix<<"second\":[";
        for(int k=0;k<12;++k)out<<(k?",":"")<<second[k/3][k%3]/count;
        out<<"]";
    }
};
uint64_t spatial_key(const Oracle::N010ArrayVertex& v,const Aabb& box) {
    if(!v.active)return UINT64_MAX;
    uint32_t q[3];
    for(int c=0;c<3;++c) {
        const double width=box.hi[c]-box.lo[c];
        const double coordinate=width>0?(v.origin[c]-box.lo[c])/width:0.0;
        q[c]=uint32_t(std::clamp(coordinate,0.0,1.0)*262143.0);
    }
    uint64_t key=0;
    for(int bit=0;bit<18;++bit)for(int c=0;c<3;++c)key|=uint64_t((q[c]>>bit)&1U)<<(3*bit+c);
    const unsigned octant=(v.normal.x>=0?1:0)|(v.normal.y>=0?2:0)|(v.normal.z>=0?4:0);
    return key|(uint64_t(octant)<<54);
}
int main(int argc,char**argv) {
    if(argc!=5)return 2;N010NetRng::load(argv[1]);
    std::ifstream in(argv[2]);const Scene scene=parse_scene(in);const Oracle oracle(scene);
    if(scene.max_bounces!=8||scene.width!=320||scene.height!=180||scene.sampling!=Sampling::Center)return 3;
    for(const auto& m:scene.materials)for(double e:m.emit)if(e!=0)return 4;
    Aabb box;for(const auto& t:scene.triangles){box.grow(t.v0);box.grow(t.v1);box.grow(t.v2);}
    const std::array<uint64_t,4> seeds={305419896ULL,2596069104ULL,81985529216486895ULL,18364758544493064720ULL};
    std::ifstream pixels(argv[3]);std::ofstream out(argv[4]);out<<std::setprecision(17)<<"[";bool comma=false;uint32_t x,y;
    while(pixels>>x>>y)for(uint64_t seed:seeds) {
        if(x>=scene.width||y>=scene.height)return 5;
        const size_t pixel=size_t(y)*scene.width+x;
        Stats original,array;Oracle::PrimaryCache original_cache,array_cache;RenderCounters original_count,array_count;
        std::vector<PathState> states(count);double first_luma=0;
        for(uint32_t s=0;s<count;++s) {
            N010NetRng rng(seed,pixel,s);Rgb comp[3];double trace[9]{};
            oracle.sample(x,y,rng,comp,original_count,nullptr,&original_cache,trace);
            original.add(comp);
            N010NetRng coordinates(seed,pixel,s);
            for(int d=0;d<14;++d)states[s].coordinates[d]=coordinates.uniform();
            ReplayRng replay{states[s].coordinates};double first_trace[9]{};
            oracle.sample(x,y,replay,states[s].components.data(),array_count,nullptr,&array_cache,first_trace,&states[s].vertex,1);
            first_luma+=first_trace[1];
        }
        std::vector<uint32_t> order(count),points(count);
        for(uint32_t bounce=1;bounce<=6;++bounce) {
            std::iota(order.begin(),order.end(),0);std::iota(points.begin(),points.end(),0);
            for(auto& state:states)state.key=spatial_key(state.vertex,box);
            std::sort(order.begin(),order.end(),[&](auto a,auto b){return states[a].key!=states[b].key?states[a].key<states[b].key:a<b;});
            uint32_t shift[3];for(int d=0;d<3;++d)shift[d]=uint32_t(N010NetRng::mix(seed^N010NetRng::mix(pixel)^N010NetRng::mix(0x415252415900ULL+3*bounce+d)));
            auto word=[&](uint32_t s,int d){return N010NetRng::net[size_t(s)*16+d]^shift[d];};
            std::sort(points.begin(),points.end(),[&](auto a,auto b){const auto aa=word(a,0),bb=word(b,0);return aa!=bb?aa<bb:a<b;});
            for(uint32_t rank=0;rank<count;++rank) {
                auto& state=states[order[rank]];
                state.coordinates[2*bounce]=(double(word(points[rank],1))+.5)*0x1p-32;
                state.coordinates[2*bounce+1]=(double(word(points[rank],2))+.5)*0x1p-32;
            }
            for(auto& state:states) {
                ReplayRng replay{state.coordinates};
                oracle.sample(x,y,replay,state.components.data(),array_count,nullptr,&array_cache,nullptr,&state.vertex,bounce+1);
            }
        }
        for(const auto& state:states)array.add(state.components.data());
        if(comma)out<<",";comma=true;
        out<<"{\"x\":"<<x<<",\"y\":"<<y<<",\"seed\":"<<seed<<",\"first_indirect_luma_mean\":"<<first_luma/count;
        original.write(out,"");array.write(out,"array_");
        out<<",\"original_shadow_tests\":"<<original_count.shadow_tests<<",\"array_with_prefix_replay_shadow_tests\":"<<array_count.shadow_tests<<"}";
    }
    out<<"]\n";return out?0:6;
}
'''


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing array diagnostic')
    require_no_other_research_worker()
    os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    for p in (Path(__file__),PLAN,Path(D.__file__),Path(B.__file__),D.HERE/'run_primary_direction_sequence.py'):
        D.checked(p)
    previous=json.loads(D.checked(D.RESULTS/'202-later-bounce-cv-path-diagnosis.json',
        '58f75c7606a5553c4e409c3c5375cc9b8c9d2ec3a2639a5b4817cc8390af9fea'))
    if not previous['complete'] or previous['diagnostic_promising']:raise ValueError('actual prior prototype termination required')
    proof=json.loads(D.checked(D.RESULTS/'193-selected-bounce-path-diagnosis.json'))
    old=next(v for v in proof['variants'] if v['variant']=='original')
    if not proof['complete'] or not old['selected_retained_mean_second_bit_exact']:raise ValueError('original diagnostic proof absent')
    for p,h in old['payload_sha256'].items():D.checked(Path(p),h)
    original=next(Path(p) for p in old['payload_sha256'] if p.endswith('.hpp')).read_text()
    pairs=[('    // One camera sample; writes per-component radiance.',
        '    struct N010ArrayVertex {bool active{};V3 origin{},normal{};};\n    // One camera sample; writes per-component radiance.'),
        ('double* diagnostic_bounce = nullptr) const {',
         'double* diagnostic_bounce = nullptr, N010ArrayVertex* vertex=nullptr, uint32_t stop=UINT32_MAX) const {\n        if(vertex)*vertex={};'),
        ('            if (bounce + 1 >= scene_.max_bounces) return;',
         '            if(vertex&&bounce==stop){vertex->active=bounce+1<scene_.max_bounces;vertex->origin=origin;vertex->normal=n;return;}\n            if (bounce + 1 >= scene_.max_bounces) return;')]
    generated=original
    for a,b in pairs:generated=D.once(generated,a,b)
    restored=generated
    for a,b in reversed(pairs):restored=D.once(restored,b,a)
    if restored!=original:raise ValueError('whole physical-body inverse differs')
    retained=json.loads(next(Path(p) for p in old['payload_sha256'] if p.endswith('/data.json')).read_bytes())
    net=D.OUT/'sobol16x262144.bin';scene=D.OUT/'references-recovery-sponza-v1/C1_T_B8/scene.n008'
    D.checked(net);D.checked(scene)
    WORK.mkdir();(WORK/'n010_rqmc_oracle.hpp').write_text(generated);(WORK/'main.cpp').write_text(MAIN)
    pixels=WORK/'pixels.txt';pixels.write_text(''.join(f'{x} {y}\n' for x,y in PIXELS))
    binary=WORK/'n010_array_diagnostic';data_path=WORK/'data.json'
    result=dict(schema='n010-array-rqmc-transport-diagnosis/1',complete=False,gpu_run=False,
        classification='DIAGNOSTIC_ACQUIRING_NO_ADMISSION',reference_admission=False,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        input_sha256=D.INPUTS,pixels=PIXELS,spp=8192,seeds=list(D.SEEDS),whole_physical_header_inverse_exact=True,
        attempts=[],tests='NOT_RUN; paired original/array scientific prototype only')
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
                receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
            attempt=dict(command=command,elapsed_limit_seconds=300);result['attempts'].append(attempt);save();start=time.monotonic()
            try:proc=subprocess.run(command,capture_output=True,text=True,timeout=300,preexec_fn=limits)
            except subprocess.TimeoutExpired as e:
                (WORK/f'step-{i}.stdout').write_bytes(e.stdout or b'');(WORK/f'step-{i}.stderr').write_bytes(e.stderr or b'')
                raise ValueError('elapsed guard, partials retained') from e
            (WORK/f'step-{i}.stdout').write_text(proc.stdout);(WORK/f'step-{i}.stderr').write_text(proc.stderr)
            attempt.update(returncode=proc.returncode,elapsed=time.monotonic()-start,receipt_sha256=sha(receipt));save()
            actual=json.loads(D.checked(receipt))
            if actual['cpu']!=[220,220] or actual['address_space']!=[4*1024**3]*2 or len(actual['affinity'])!=1 or actual['nice']!=15:
                raise ValueError('actual low-load resource limits differ')
            if proc.returncode:raise ValueError('compile/native failed, no retry')
        rows=json.loads(D.checked(data_path))
        if len(rows)!=32 or {(r['x'],r['y'],r['seed']) for r in rows}!={(x,y,s) for x,y in PIXELS for s in D.SEEDS}:
            raise ValueError('actual array scope differs')
        for r in rows:
            original_row=next(z for z in retained if (z['x'],z['y'],z['seed'])==(r['x'],r['y'],r['seed']))
            if np.asarray(r['mean']+r['second'],dtype='<f8').tobytes()!=np.asarray(original_row['mean']+original_row['second'],dtype='<f8').tobytes():
                raise ValueError('original moments differ from retained 193')
            if r['first_indirect_luma_mean']!=original_row['bounce_mean'][1]:
                raise ValueError('candidate first-indirect coupling differs')
            if r['array_mean'][:6]!=r['mean'][:6]:raise ValueError('candidate deterministic components changed')
        variants=[]
        for name,prefix in (('original',''),('array','array_')):
            m=np.array([[next(r[prefix+'mean'] for r in rows if (r['x'],r['y'],r['seed'])==(x,y,seed)) for x,y in PIXELS] for seed in D.SEEDS]).reshape(4,8,4,3)
            s=np.array([[next(r[prefix+'second'] for r in rows if (r['x'],r['y'],r['seed'])==(x,y,seed)) for x,y in PIXELS] for seed in D.SEEDS]).reshape(4,8,4,3)
            if not np.isfinite(m).all() or not np.isfinite(s).all() or (m<0).any() or (s<0).any():raise ValueError('invalid array moments')
            if not np.array_equal(m[...,0],m[...,1]) or not np.array_equal(m[...,0],m[...,2]):raise ValueError('grey diagnostic moment assumption differs')
            luma=m[...,2,:]@B.LUMA
            variants.append(dict(variant=name,max_pairwise_indirect_p99=B.pairwise_p99(luma),
                indirect_replicate_variance_sum=float(np.var(luma,axis=0,ddof=1).sum()),
                mean_path_variance_sum=float(np.maximum(s[...,2,0]-m[...,2,0]**2,0).mean(0).sum())))
        ratios={k:variants[1][k]/variants[0][k] for k in ('max_pairwise_indirect_p99','indirect_replicate_variance_sum','mean_path_variance_sum')}
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(complete=True,classification='DIAGNOSTIC_COMPLETE_NO_ADMISSION',original_moments_bit_exact=True,
            first_indirect_coupling_bit_exact=True,deterministic_components_bit_exact=True,
            variants=variants,array_over_original=ratios,
            diagnostic_promising=ratios['max_pairwise_indirect_p99']<=.75 and ratios['indirect_replicate_variance_sum']<=.75**2,
            payload_sha256={str(p):sha(p) for p in WORK.iterdir() if p.is_file()},
            scope='Eight fixed C1 pixels, one 8192-path array/four seeds; no larger-level prefix, physical/full-frame/state proofs or reference admission')
    except (ValueError,OSError,subprocess.SubprocessError) as e:result.update(classification='OPERATIONAL_FAILURE_PARTIALS_RETAINED',failure=str(e))
    save();print(json.dumps({k:result.get(k) for k in ('complete','classification','failure','diagnostic_promising','array_over_original')},indent=2))
    raise SystemExit(0 if result['complete'] else 2)


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Plan080: opt-in full-output single-thread all-split CPU exporter build."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK=D.OUT/'all-split-exporter-v1'
OUTPUT=D.RESULTS/'224-all-split-exporter-build.json'
PLAN=D.RESULTS.parent/'experiments/080-all-split-exporter-and-full-sidedness-controls.md'
WRAPPER=r'''
    // Plan080: single-thread renderer audit, auxiliary original cache prime.
    mutable WholeAudit renderer_audit_{};
    mutable uint64_t primary_prime_samples_{};
    template<class Rng>
    void sample_all_split(uint32_t x,uint32_t y,Rng& rng,Rgb out[kComponents],RenderCounters& cnt,
                          PrimaryRecord* primary,PrimaryCache* cache) const {
        if(!cache)throw std::runtime_error("all-split renderer requires primary cache");
        if(!cache->hit_ready) {
            auto prime_rng=rng;Rgb ignored[kComponents];RenderCounters prime_counters;
            sample(x,y,prime_rng,ignored,prime_counters,primary,cache);
            ++primary_prime_samples_;
        }
        if(cache->hit.hit()) {
            ++cnt.primary_hits;
            const auto& tri=scene_.triangles[cache->hit.tri];const auto& material=scene_.materials[tri.material];
            const auto ng=normalize(cross(tri.v1-tri.v0,tri.v2-tri.v0));
            if(!material.two_sided&&!(dot(ng,primary_ray(x,y,0.5,0.5).dir)<0))++cnt.backface_absorbed;
            cnt.shadow_tests+=cache->shadow_tests;cnt.shadow_blocked+=cache->shadow_blocked;
        }
        const auto before_tests=renderer_audit_.direct_counters.shadow_tests;
        const auto before_blocked=renderer_audit_.direct_counters.shadow_blocked;
        double depth[8]{};whole_sample(x,y,rng,out,*cache,renderer_audit_,depth);
        cnt.shadow_tests+=renderer_audit_.direct_counters.shadow_tests-before_tests;
        cnt.shadow_blocked+=renderer_audit_.direct_counters.shadow_blocked-before_blocked;
    }
'''

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing exporter build')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    D.checked(Path(__file__));D.checked(PLAN)
    proof=json.loads(D.checked(D.RESULTS/'223-all-split-general-transport-equivalence.json'))
    if not proof['complete'] or not proof['per_sample_legacy_component_depth_bits_exact'] or not proof['retained218_accumulated_bits_exact']:raise ValueError('exact generic prototype proof required')
    for p,h in proof['payload_sha256'].items():D.checked(Path(p),h)
    original_header=next(Path(p) for p in proof['payload_sha256'] if p.endswith('.hpp'));header=original_header.read_text()
    edits=[('    // One camera sample; writes per-component radiance.',WRAPPER+'\n    // One camera sample; writes per-component radiance.'),
           ('        std::vector<PixelStats> stats(std::size_t(scene_.width) * scene_.height);','        if(threads!=1)throw std::runtime_error("all-split export requires one render thread");\n        renderer_audit_={};primary_prime_samples_=0;\n        std::vector<PixelStats> stats(std::size_t(scene_.width) * scene_.height);'),
           ('                            sample(x, y, rng, comp, per_thread[t],','                            sample_all_split(x, y, rng, comp, per_thread[t],')]
    for a,b in edits:header=D.once(header,a,b)
    inverse=header
    for a,b in reversed(edits):inverse=D.once(inverse,b,a)
    if inverse!=original_header.read_text():raise ValueError('export header inverse differs')
    main_file=D.ROOT/'src/research/n008_hdr_oracle/n008_oracle_main.cpp';source=D.checked(main_file).decode()
    meta=r'''
            const auto& a=oracle.renderer_audit_;
            std::printf(",\"all_split\":{\"auxiliary_primary_primes\":%llu,\"proposal_bvh_queries\":%llu,\"component_attempts\":%llu,\"component_nulls\":%llu,\"own_checks\":%llu,\"max_own_log_error\":%.17g,\"max_conditioned_error_fraction\":%.17g,\"max_unconditioned_error_fraction\":%.17g}}",
                (unsigned long long)oracle.primary_prime_samples_,(unsigned long long)a.bvh_queries,
                (unsigned long long)a.component_attempts,(unsigned long long)a.component_nulls,(unsigned long long)a.own_checks,
                a.max_own_log_error,a.max_target_error_fraction,a.max_unconditioned_target_error_fraction);
'''
    restriction=r'''
        if(threads!=1||scene.sampling!=Sampling::Center||scene.max_bounces<1||scene.max_bounces>8||scene.points.size()!=1)
            throw std::runtime_error("all-split requires centre,one point,1..8 vertices,one thread");
        for(const auto& m:scene.materials)for(int c=0;c<3;++c)
            if(m.emit[c]!=0||!std::isfinite(m.rho[c])||m.rho[c]<0)
                throw std::runtime_error("all-split nonemissive nonnegative finite RGB scope");
        const Oracle oracle(scene);
'''
    pairs=[('#include "n008_oracle.hpp"','#include "n010_rqmc_oracle.hpp"'),
           ('        unsigned threads = std::max(1U, std::thread::hardware_concurrency());','        unsigned threads = 1;'),
           ('            else if (a == "--threads")','            else if(a=="--net") N010NetRng::load(value());\n            else if (a == "--threads")'),
           ('        const Oracle oracle(scene);',restriction),
           ('\\"oracle\\":\\"n008\\"','\\"oracle\\":\\"n010-all-split-general\\"'),
           ('\\"cpu_seconds_diagnostic\\":%.3f}",','\\"cpu_seconds_diagnostic\\":%.3f",'),
           ('static_cast<unsigned long long>(counters.backface_absorbed), secs);','static_cast<unsigned long long>(counters.backface_absorbed), secs);\n'+meta)]
    for a,b in pairs:source=D.once(source,a,b)
    inverse=source
    for a,b in reversed(pairs):inverse=D.once(inverse,b,a)
    if inverse!=main_file.read_text():raise ValueError('CLI main inverse differs')
    WORK.mkdir();(WORK/'n010_rqmc_oracle.hpp').write_text(header);(WORK/'main.cpp').write_text(source)
    binary=WORK/'n010_all_split_oracle';receipt=WORK/'compile.resources.json'
    command=['c++','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread','-I',str(D.ROOT/'src/research/n008_hdr_oracle'),str(WORK/'main.cpp'),'-o',str(binary)]
    result=dict(schema='n010-all-split-exporter-build/1',complete=False,all_pass=False,gpu_run=False,reference_admission=False,classification='ISOLATED_BUILD_ACQUIRING',input_sha256=D.INPUTS,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),header_and_main_inverses_exact=True,command=command,tests='NOT_RUN; standalone scientific exporter build only')
    OUTPUT.write_text(json.dumps(result,indent=2)+'\n')
    def limits():
        resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(220,)*2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
    start=time.monotonic()
    try:
        proc=subprocess.run(command,capture_output=True,text=True,timeout=300,preexec_fn=limits)
        (WORK/'compile.stdout').write_text(proc.stdout);(WORK/'compile.stderr').write_text(proc.stderr)
        result.update(returncode=proc.returncode,elapsed=time.monotonic()-start)
        actual=json.loads(D.checked(receipt))
        if actual['cpu']!=[220,220] or actual['address_space']!=[4*1024**3]*2 or len(actual['affinity'])!=1 or actual['nice']!=15:raise ValueError('actual compiler limits differ')
        if proc.returncode:raise ValueError('compile failed; no retry')
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(complete=True,all_pass=True,classification='ISOLATED_EXPORTER_BUILD_PASS_NO_RUNTIME_ADMISSION')
    except (ValueError,OSError,subprocess.SubprocessError) as e:result.update(classification='BUILD_FAILURE_PARTIALS_RETAINED',failure=str(e))
    result['payload_sha256']={str(p):sha(p) for p in WORK.iterdir() if p.is_file()};OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result.get(k) for k in ('complete','all_pass','failure','elapsed')},indent=2))
    raise SystemExit(0 if result['all_pass'] else 2)

if __name__=='__main__':main()

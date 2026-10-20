#!/usr/bin/env python3
"""Plan173: capture exact operands of the737 conditioned raw-target/plane guard failure."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

REPO=Path(__file__).resolve().parents[3]
OUT=REPO/'out/research/n010-comparison-readiness'
RESULTS=REPO/'research/lanes/n010-comparison-readiness/results'
PLAN=RESULTS.parent/'experiments/173-737-guard-failure-witness.md'
MANIFEST=RESULTS/'evidence/740-suspension-local-archive-manifest.json'
WORK=OUT/'737-guard-witness-v1'
OUTPUT=RESULTS/'742-737-guard-failure-witness.json'
SOURCE=OUT/'thread-private-reference-source-v2/prefix'
SCENE=OUT/'private-four-core-reference-ladders-v1/C1_T_B8/scene.n008'
NET=OUT/'sobol16x262144.bin'
SEED=2596069104
FLAGS=['-mavx512f','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread',
       '-I',str(REPO/'src/research/n008_hdr_oracle')]
CPU_LIMIT,ELAPSED_LIMIT,AS_LIMIT=57600,14400,4*1024**3
GUARD='            if(certified_error>bound)throw std::runtime_error("conditioned raw-target/plane reconstruction error");'
WITNESS_FIELDS=[('ox','current.origin.x'),('oy','current.origin.y'),('oz','current.origin.z'),
    ('px','target.point.x'),('py','target.point.y'),('pz','target.point.z'),
    ('lx','target.low.x'),('ly','target.low.y'),('lz','target.low.z'),
    ('wx','direction.x'),('wy','direction.y'),('wz','direction.z'),
    ('distance','distance'),('t','hit.t'),('error','error'),('bound','bound'),
    ('target_plane','target_plane_error'),('actual_plane','actual_plane_error'),
    ('conditioned','conditioned_error')]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def once(text,a,b):
    if text.count(a)!=1:raise ValueError(f'expected one occurrence: {a[:60]!r}')
    return text.replace(a,b)


def witness_macro():
    fmt=','.join(f'\\"{k}\\":\\"%a\\"' for k,_ in WITNESS_FIELDS)
    args=','.join(e for _,e in WITNESS_FIELDS)
    return ('#define N010_GUARD_WITNESS(kind) std::fprintf(stderr,"GUARD_WITNESS {\\"kind\\":\\"%s\\",'
            '\\"x\\":%u,\\"y\\":%u,\\"s\\":%u,\\"light_first\\":%d,\\"index\\":%u,\\"source_triangle\\":%u,'
            '\\"target_triangle\\":%u,\\"hit_triangle\\":%u,\\"coincident\\":%d,'+fmt+'}\\n",kind,'
            'n010_diag_x,n010_diag_y,n010_diag_s,int(light_first),uint32_t(i),current.raw.triangle,'
            'target.triangle,hit.tri,int(coincident),'+args+')\n')


def generate(header,main):
    decl=('static thread_local uint32_t n010_diag_x{},n010_diag_y{},n010_diag_s{},n010_diag_near{};\n'
          +witness_macro()+'// ---------------------------------------------------------------- intersection')
    guard_new=('            if(certified_error>0.9*bound&&n010_diag_near++<64)N010_GUARD_WITNESS("near");\n'
               '            if(certified_error>bound)N010_GUARD_WITNESS("fail");\n'+GUARD)
    edits=[('// ---------------------------------------------------------------- intersection',decl),
           ('                            N010NetRng rng(seed, pixel, s);',
            '                            N010NetRng rng(seed, pixel, s);n010_diag_x=x;n010_diag_y=y;n010_diag_s=s;')]
    generated=header
    for a,b in edits:generated=once(generated,a,b)
    if generated.count(GUARD)!=2:raise ValueError('expected exactly two guard sites')
    generated=generated.replace(GUARD,guard_new)
    restored=generated.replace(guard_new,GUARD)
    for a,b in reversed(edits):restored=once(restored,b,a)
    if restored!=header:raise ValueError('diagnostic header inverse differs')
    return generated,main


def limits():
    os.sched_setaffinity(0,{28,29,30,31});os.nice(15)
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_LIMIT,CPU_LIMIT))
    resource.setrlimit(resource.RLIMIT_AS,(AS_LIMIT,AS_LIMIT))


def parse_witnesses(text):
    rows=[]
    for line in text.splitlines():
        if line.startswith('GUARD_WITNESS '):
            row=json.loads(line[len('GUARD_WITNESS '):])
            for k,_ in WITNESS_FIELDS:row[k]=float.fromhex(row[k])
            rows.append(row)
    return rows


def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing742 diagnosis')
    manifest=json.loads(MANIFEST.read_bytes())
    frozen={Path(f['original_path']):f['sha256'] for f in manifest['files']}
    for path in (SOURCE/'n010_rqmc_oracle.hpp',SOURCE/'n010_rqmc_main.cpp',SCENE,NET):
        if sha(path)!=frozen[path]:raise ValueError(f'frozen input changed: {path}')
    header=(SOURCE/'n010_rqmc_oracle.hpp').read_text();main_source=(SOURCE/'n010_rqmc_main.cpp').read_text()
    generated,main_source=generate(header,main_source)
    WORK.mkdir()
    (WORK/'n010_rqmc_oracle.hpp').write_text(generated);(WORK/'n010_rqmc_main.cpp').write_text(main_source)
    binary=WORK/'n010_737_guard_witness'
    result=dict(schema='n010-737-guard-failure-witness/1',complete=False,gpu_run=False,
        classification='DIAGNOSTIC_ACQUIRING_NO_ADMISSION',reference_admission=False,feasibility=False,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        plan_sha256=sha(PLAN),script_sha256=sha(__file__),
        frozen_input_sha256={str(p):frozen[p] for p in (SOURCE/'n010_rqmc_oracle.hpp',SOURCE/'n010_rqmc_main.cpp',SCENE,NET)},
        generated_sha256={'header':sha(WORK/'n010_rqmc_oracle.hpp'),'main':sha(WORK/'n010_rqmc_main.cpp')},
        header_inverse_exact=True,seed=SEED,spp=8192,threads=4,affinity=[28,29,30,31],nice=15,
        limits=dict(cpu=CPU_LIMIT,elapsed=ELAPSED_LIMIT,address_space=AS_LIMIT),
        tests='NOT_RUN; diagnostic instrumentation only')
    def save():OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()
    compile_cmd=['c++',*FLAGS,str(WORK/'n010_rqmc_main.cpp'),'-o',str(binary)]
    compiled=subprocess.run(compile_cmd,capture_output=True,text=True)
    result['compile']=dict(command=compile_cmd,returncode=compiled.returncode,stderr=compiled.stderr[-4000:],
                           compiler=subprocess.check_output(['c++','--version'],text=True).splitlines()[0])
    if compiled.returncode:result['classification']='COMPILE_FAILED';result['complete']=True;save();return
    result['binary_sha256']=sha(binary);save()
    command=[str(binary),'--net',str(NET),'--scene',str(SCENE),'--out',str(WORK/'o.n8192'),
             '--seeds',str(SEED),'--spp','8192','--threads','4']
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    start=time.monotonic()
    with open(WORK/'stdout.json','wb') as out,open(WORK/'stderr.log','wb') as err:
        process=subprocess.Popen(command,stdout=out,stderr=err,preexec_fn=limits,env=env)
        result.update(command=command,native_pid=process.pid);save()
        try:returncode=process.wait(timeout=ELAPSED_LIMIT)
        except subprocess.TimeoutExpired:
            process.kill();returncode=process.wait();result['elapsed_guard_stop']=True
    usage=resource.getrusage(resource.RUSAGE_CHILDREN)
    stderr=(WORK/'stderr.log').read_text(errors='replace')
    witnesses=parse_witnesses(stderr)
    failures=[w for w in witnesses if w['kind']=='fail']
    result.update(returncode=returncode,wall_seconds_diagnostic=time.monotonic()-start,
        child_cpu_seconds=usage.ru_utime+usage.ru_stime,
        stdout_sha256=sha(WORK/'stdout.json'),stderr_sha256=sha(WORK/'stderr.log'),
        stderr_tail=stderr.splitlines()[-3:],near_witnesses=sum(w['kind']=='near' for w in witnesses),
        fail_witnesses=failures,complete=True,
        classification='WITNESS_CAPTURED_ANALYSIS_PENDING' if failures else 'NOT_REPRODUCED')
    save()


if __name__=='__main__':main()

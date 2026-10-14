#!/usr/bin/env python3
"""One bounded Amendment 7 numerical-port diagnostic, never reference admission."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import numpy as np
import qualify_references as Q
from reference_provenance import ROOT, RESULTS, sha, physical_proof, verify_reference
from readiness_preflight import replay

KEYS=('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(90,90))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cell',required=True)
    parser.add_argument('--vertices',type=int,choices=(2,8),required=True)
    parser.add_argument('--spp',type=int,required=True)
    parser.add_argument('--seed-index',type=int,choices=range(4),default=0)
    parser.add_argument('--batch',type=int,default=1)
    parser.add_argument('--elapsed-limit',type=int,default=120)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.work.exists() or args.output.exists():raise ValueError('refuse existing diagnostic attempt')
    if not 1<=args.spp<=8192:raise ValueError('diagnostic sample interval only')
    if not 1<=args.batch<=64:raise ValueError('bounded diagnostic batch required')
    if not 60<=args.elapsed_limit<=900:raise ValueError('explicit elapsed budget must be 60..900 seconds')
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:comm=(proc/'comm').read_text().strip()
        except OSError:continue
        if comm.startswith('phos-'):raise ValueError('another GPU image producer is active')
    lock_path=RESULTS/'016-corpus-state-lock.json';lock=json.loads(lock_path.read_text())
    spec=lock['cells'][args.cell];state=Q.L.read_state(ROOT/spec['state_directory'])
    if state['sha256']!=spec['state_sha256']:raise ValueError('physical state changed')
    binary=ROOT/'build/n010-cpu/phos-n010-gpu-reference'
    shader=ROOT/'out/research/n010-comparison-readiness/gpu-oracle-compile-v3/n010_gpu_oracle.spv'
    compile_record=RESULTS/'066-bounded-gpu-reference-compilation.json'
    compiler=json.loads(compile_record.read_text())
    if not compiler['all_pass'] or compiler['shader_sha256']!=sha(shader):raise ValueError('compiled shader changed')
    inputs={};physical_proof(inputs)
    paths=[binary,shader,compile_record,lock_path,Q.BINARY,Q.NET,Path(__file__),
        ROOT/'src/research/n010_comparison_readiness/gpu_reference_main.cpp',
        ROOT/'shaders/research/n010_comparison_readiness/n010_gpu_oracle.comp.glsl',
        RESULTS.parent/'experiments/016-amendment-7-gpu-reference-feasibility.md']
    inputs.update({str(p.resolve()):sha(p) for p in paths})
    args.work.mkdir(parents=True)
    scene=args.work/'scene.n008';scene.write_text(Q.scene_for_state(state,args.vertices).text())
    seed=Q.L.N007_SEEDS[args.seed_index]
    result={'schema':'n010-gpu-reference-conformance/1','complete':False,'all_pass':False,
        'classification':'DIAGNOSTIC_ONLY_NOT_REFERENCE_ELIGIBILITY','gpu_run':False,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'input_sha256':inputs,'scene_sha256':sha(scene),'cell':args.cell,'vertices':args.vertices,
        'spp':args.spp,'seed':seed,'batch':args.batch,'scoring_exclusions':0,
        'limits':{'address_space_bytes':4*1024**3,'cpu_seconds':90,'elapsed_seconds':args.elapsed_limit},
        'thresholds':{'max_absolute_mean_and_moment':1e-10,'indirect_nrmse':1e-8,'counter_disagreements':0},
        'scope':'Bounded numerical execution trial under CPU reference load. No GI performance claim or reference admission.'}
    def run(name,command):
        result[name+'_command']=command
        (args.work/'attempt.json').write_text(json.dumps(result,indent=2)+'\n')
        env=os.environ.copy();env['LD_LIBRARY_PATH']=':'.join(filter(None,[env.get('NIX_LD_LIBRARY_PATH'),env.get('LD_LIBRARY_PATH')]))
        try:
            p=subprocess.run(command,cwd=ROOT,env=env,text=True,capture_output=True,timeout=args.elapsed_limit,preexec_fn=limits)
            stdout,stderr=p.stdout,p.stderr;result[name+'_returncode']=p.returncode
        except subprocess.TimeoutExpired as error:
            stdout,stderr=error.stdout or b'',error.stderr or b''
            if isinstance(stdout,bytes):stdout=stdout.decode(errors='replace')
            if isinstance(stderr,bytes):stderr=stderr.decode(errors='replace')
            result[name+'_returncode']=None;result[name+'_timeout']=True
        (args.work/(name+'.stdout')).write_text(stdout);(args.work/(name+'.stderr')).write_text(stderr)
        if result[name+'_returncode']!=0:raise ValueError(name+' failed; retained without automatic retry')
        return json.loads(stdout) if name=='cpu' else None
    try:
        result['gpu_run']=True
        run('gpu',['bash','scripts/run_with_vulkan.sh',str(binary),str(scene.resolve()),str(Q.NET),str(shader),str(seed),str(args.spp),str(args.batch),str((args.work/'gpu').resolve())])
        if args.spp==8192:
            directory=ROOT/'out/research/n010-comparison-readiness/references-v1'/f'{args.cell}_T_B{args.vertices}'
            verify_reference(directory,args.cell,args.vertices,spec,inputs,require_eligible=False)
            meta_path=directory/'n8192.meta.json';meta=json.loads(meta_path.read_text())
            if meta['scene_sha256']!=sha(scene) or meta['binary_sha256']!=sha(Q.BINARY) or meta['seeds'][args.seed_index]!=seed:raise ValueError('original CPU reference identity mismatch')
            cpu_prefix=directory/f'o.n8192.s{args.seed_index}';cpu_hits=directory/'o.n8192.hits';cpu_counters=meta['runs'][args.seed_index]
            inputs[str(meta_path)]=sha(meta_path)
        else:
            meta=run('cpu',[str(Q.BINARY),'--net',str(Q.NET),'--scene',str(scene.resolve()),'--out',str((args.work/'cpu').resolve()),'--seeds',str(seed),'--spp',str(args.spp)])
            cpu_prefix=args.work/'cpu.s0';cpu_hits=args.work/'cpu.hits';cpu_counters=meta['runs'][0]
        gpu_prefix=args.work/'gpu/o';gpu_meta=json.loads((args.work/'gpu/gpu.json').read_text())
        inputs[str(Path(str(cpu_prefix)+'.f64').resolve())]=sha(Path(str(cpu_prefix)+'.f64'))
        inputs[str(cpu_hits.resolve())]=sha(cpu_hits)
        cpu=Q.L.read_sidecar(Path(str(cpu_prefix)+'.f64'));gpu=Q.L.read_sidecar(Path(str(gpu_prefix)+'.f64'))
        for key in ('width','height','spp','seed'):
            if cpu[key]!=gpu[key]:raise ValueError('sidecar shape/replicate mismatch')
        difference=gpu['mean']-cpu['mean'];ind=difference[...,2,:];den=float(np.sum(cpu['mean'][...,2,:]**2))
        nrmse=float(np.sqrt(np.sum(ind**2)/den)) if den else (0.0 if not np.any(ind) else None)
        moment_key='m2'
        result.update(primary_records_byte_equal=cpu_hits.read_bytes()==(args.work/'gpu/o.hits').read_bytes(),
            direct_mean_byte_equal=cpu['mean'][...,1,:].tobytes()==gpu['mean'][...,1,:].tobytes(),
            emission_mean_byte_equal=cpu['mean'][...,0,:].tobytes()==gpu['mean'][...,0,:].tobytes(),
            max_abs_mean=float(np.max(np.abs(difference))),max_abs_moment=float(np.max(np.abs(gpu[moment_key]-cpu[moment_key]))),
            indirect_nrmse=nrmse,cpu_counters={k:cpu_counters[k] for k in KEYS},gpu_counters={k:gpu_meta[k] for k in KEYS},
            all_finite=bool(all(np.isfinite(x).all() for x in (cpu['mean'],gpu['mean'],cpu[moment_key],gpu[moment_key]))),gpu_fault_flags=gpu_meta['fault_flags'],
            owned_memory_replay_pass=replay(json.loads((args.work/'gpu/allocation-ledger.json').read_text())))
        result['all_pass']=bool(result['primary_records_byte_equal'] and result['direct_mean_byte_equal'] and result['emission_mean_byte_equal'] and result['all_finite'] and result['gpu_fault_flags']==0 and result['cpu_counters']==result['gpu_counters'] and result['max_abs_mean']<=1e-10 and result['max_abs_moment']<=1e-10 and nrmse is not None and nrmse<=1e-8 and result['owned_memory_replay_pass'])
        for path,digest in inputs.items():
            if sha(Path(path))!=digest:raise ValueError('frozen diagnostic input changed')
    except (ValueError,OSError,KeyError,StopIteration) as error:
        result['failure']=str(error)
    result['payload_sha256']={str(p.relative_to(args.work)):sha(p) for p in args.work.rglob('*') if p.is_file()}
    result['complete']=True;args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('DIAGNOSTIC PASS' if result['all_pass'] else 'DIAGNOSTIC FAIL')
    raise SystemExit(0 if result['all_pass'] else 2)

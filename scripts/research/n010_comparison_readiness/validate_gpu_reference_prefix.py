#!/usr/bin/env python3
"""All-state CPU/GPU conformance and exact actual-level prefix continuation."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import numpy as np
import qualify_references as Q
from reference_provenance import ROOT,RESULTS,sha
from readiness_preflight import replay
KEYS=('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')
PAYLOADS=('o.f64','o.emission.pfm','o.direct.pfm','o.indirect.pfm','o.total.pfm','o.hits')
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(90,90))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.work.exists() or args.output.exists():raise ValueError('refuse existing prefix diagnostic')
    ctypes.CDLL(None).prctl(15,b'n010_prefix_chk',0,0,0)
    proofs=[RESULTS/name for name in ('075-gpu-reference-full-conformance-resource-followup.json',
        '076-gpu-reference-prefix-build.json','077-gpu-reference-physical-controls.json','078-all-state-cpu-port-controls.json')]
    while True:
        ready=True
        for path in proofs:
            if not path.exists():ready=False;continue
            proof=json.loads(path.read_text())
            if proof['complete'] and not proof['all_pass']:raise ValueError('required diagnostic failed: '+path.name)
            ready=ready and proof['complete'] and proof['all_pass']
        if ready:break
        time.sleep(30)
    args.work.mkdir(parents=True)
    base=ROOT/'build/n010-cpu/phos-n010-gpu-reference';prefix=base.with_name(base.name+'-prefix')
    shader=ROOT/'out/research/n010-comparison-readiness/gpu-oracle-compile-v3/n010_gpu_oracle.spv'
    inputs={str(p.resolve()):sha(p) for p in proofs+[base,prefix,shader,Q.NET,Q.BINARY,Path(__file__),
        ROOT/'src/research/n010_comparison_readiness/gpu_reference_prefix_main.cpp',
        ROOT/'src/research/n010_comparison_readiness/gpu_reference_main.cpp',
        RESULTS.parent/'experiments/020-gpu-reference-all-state-and-prefix-plan.md']}
    result={'schema':'n010-gpu-reference-all-state-and-prefix/1','complete':False,'all_pass':False,
        'gpu_run':True,'eligible_for_references':False,'input_sha256':inputs,'low_dose_rows':[],
        'actual_level_rows':[],'process_attempts':[],
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'limits':{'address_space_bytes':4*1024**3,'cpu_seconds':90,'elapsed_seconds':900},
        'thresholds':{'max_abs_mean_and_moment':1e-10,'indirect_nrmse':1e-8,'prefix_byte_and_counter_disagreements':0},
        'scoring_exclusions':0,'scope':'All 24 states/both transports/four seeds: original CPU vs base GPU at 16 spp; byte-exact separate prefix 8→16; actual-level 8192→16384 C7 both transports/four seeds. No statistical reference admission.'}
    def save():args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    env=os.environ.copy();env['LD_LIBRARY_PATH']=':'.join(filter(None,[env.get('NIX_LD_LIBRARY_PATH'),env.get('LD_LIBRARY_PATH')]))
    def run(binary,scene,seed,spp,out,previous=None):
        if any(sha(Path(p))!=digest for p,digest in inputs.items()):raise ValueError('frozen prefix diagnostic input changed')
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():continue
            try:comm=(proc/'comm').read_text().strip()
            except OSError:continue
            if comm.startswith('phos-'):raise ValueError('another GPU image producer is active')
        command=['bash','scripts/run_with_vulkan.sh',str(binary),str(scene),str(Q.NET),str(shader),str(seed),str(spp),'16',str(out.resolve())]
        if previous:
            old,old_meta=previous
            if old_meta['seed']!=seed or old_meta['spp']>=spp:raise ValueError('restored replicate/level mismatch')
            command += [str(old/'o.f64'),str(old_meta['spp'])]+[str(old_meta[k]) for k in KEYS]
            inputs[str((old/'o.f64').resolve())]=sha(old/'o.f64')
            inputs[str((old/'gpu.json').resolve())]=sha(old/'gpu.json')
        attempt={'command':command,'pass':False};result['process_attempts'].append(attempt);save()
        try:proc=subprocess.run(command,cwd=ROOT,env=env,text=True,capture_output=True,timeout=900,preexec_fn=limits)
        except subprocess.TimeoutExpired:
            attempt['failure']='bounded elapsed guard';raise ValueError('prefix runtime timeout')
        out.parent.mkdir(parents=True,exist_ok=True)
        out.with_suffix('.stdout').write_text(proc.stdout);out.with_suffix('.stderr').write_text(proc.stderr);attempt['returncode']=proc.returncode
        if proc.returncode:raise ValueError('prefix runtime failed')
        meta=json.loads((out/'gpu.json').read_text())
        if meta['seed']!=seed or meta['spp']!=spp or meta['fault_flags'] or not meta['all_finite'] or not replay(json.loads((out/'allocation-ledger.json').read_text())):raise ValueError('prefix runtime identity/fault/memory gate')
        attempt.update(pass_=True,payload_sha256={p.name:sha(p) for p in out.iterdir() if p.is_file()});attempt['pass']=True;save()
        return meta
    def equal(left,lmeta,right,rmeta):
        return all((left/name).read_bytes()==(right/name).read_bytes() for name in PAYLOADS) and all(lmeta[k]==rmeta[k] for k in KEYS)
    save()
    try:
        cpu_proof=json.loads(proofs[3].read_text());locked={}
        if len(cpu_proof['rows'])!=24:raise ValueError('all-state original CPU controls incomplete')
        for slot in cpu_proof['rows']:
            cell,vertices=slot['cell'],slot['vertices'];directory=Path(slot['directory']);scene=directory/'scene.n008'
            for name,digest in slot['payload_sha256'].items():
                path=directory/name
                if sha(path)!=digest:raise ValueError('retained CPU control bytes changed')
                inputs[str(path.resolve())]=digest
            cpu_meta=json.loads((directory/'meta.json').read_text());locked[(cell,vertices)]=scene
            for i,seed in enumerate(Q.L.N007_SEEDS):
                out=args.work/f'{cell}_T_B{vertices}'/f'seed{i}';out.mkdir(parents=True)
                fresh=out/'base16';fresh_meta=run(base,scene,seed,16,fresh)
                gpu=Q.L.read_sidecar(fresh/'o.f64');cpu=Q.L.read_sidecar(directory/f'o.s{i}.f64')
                if any(gpu[k]!=cpu[k] for k in ('width','height','spp','seed')):raise ValueError('all-state replicate/header mismatch')
                difference=gpu['mean']-cpu['mean'];den=float(np.sum(cpu['mean'][...,2,:]**2));ind=difference[...,2,:]
                nrmse=float(np.sqrt(np.sum(ind**2)/den)) if den else (0.0 if not np.any(ind) else None)
                row={'cell':cell,'vertices':vertices,'seed_index':i,'max_abs_mean':float(np.max(np.abs(difference))),
                    'max_abs_moment':float(np.max(np.abs(gpu['m2']-cpu['m2']))),'indirect_nrmse':nrmse,
                    'all_finite':bool(all(np.isfinite(v).all() for v in (gpu['mean'],gpu['m2'],cpu['mean'],cpu['m2']))),
                    'primary_records_byte_equal':(fresh/'o.hits').read_bytes()==(directory/'o.hits').read_bytes(),
                    'direct_mean_byte_equal':gpu['mean'][...,1,:].tobytes()==cpu['mean'][...,1,:].tobytes(),
                    'emission_mean_byte_equal':gpu['mean'][...,0,:].tobytes()==cpu['mean'][...,0,:].tobytes(),
                    'counters_equal':all(fresh_meta[k]==cpu_meta['runs'][i][k] for k in KEYS),
                    'geometry_hash_match':fresh_meta['geometry_sha256']==cpu_meta['geometry_sha256']}
                row['numerical_pass']=bool(row['all_finite'] and row['max_abs_mean']<=1e-10 and row['max_abs_moment']<=1e-10 and nrmse is not None and nrmse<=1e-8 and row['primary_records_byte_equal'] and row['direct_mean_byte_equal'] and row['emission_mean_byte_equal'] and row['counters_equal'] and row['geometry_hash_match'])
                result['low_dose_rows'].append(row);save()
                if not row['numerical_pass']:raise ValueError('fixed all-state numerical gate failed')
                small=out/'prefix8';small_meta=run(prefix,scene,seed,8,small)
                restored=out/'restored16';restored_meta=run(prefix,scene,seed,16,restored,(small,small_meta))
                row['prefix_byte_equal']=equal(fresh,fresh_meta,restored,restored_meta);row['pass']=row['numerical_pass'] and row['prefix_byte_equal'];save()
                print(cell,vertices,i,'PASS' if row['pass'] else 'FAIL',flush=True)
                if not row['pass']:raise ValueError('all-state dyadic prefix mismatch')
        full=json.loads(proofs[0].read_text())
        for vertices in (2,8):
            for i,seed in enumerate(Q.L.N007_SEEDS):
                retained=next(row for row in full['rows'] if (row['cell'],row['vertices'],row['seed_index'])==('C7',vertices,i))
                path=Path(retained['result'])
                if sha(path)!=retained['sha256']:raise ValueError('full conformance case changed')
                old=Path(json.loads(path.read_text())['gpu_command'][-1]);old_meta=json.loads((old/'gpu.json').read_text())
                inputs[str(path.resolve())]=sha(path)
                out=args.work/f'actual-C7-B{vertices}-seed{i}';out.mkdir()
                scene=locked[('C7',vertices)];fresh=out/'fresh16384';fresh_meta=run(prefix,scene,seed,16384,fresh)
                restored=out/'restored16384';restored_meta=run(prefix,scene,seed,16384,restored,(old,old_meta))
                row={'cell':'C7','vertices':vertices,'seed_index':i,'sample_interval':[8192,16384],
                    'prefix_input_sha256':sha(old/'o.f64'),'pass':equal(fresh,fresh_meta,restored,restored_meta)}
                result['actual_level_rows'].append(row);save();print('actual-prefix',vertices,i,'PASS' if row['pass'] else 'FAIL',flush=True)
                if not row['pass']:raise ValueError('actual-level prefix mismatch')
        result['all_pass']=len(result['low_dose_rows'])==96 and all(r['pass'] for r in result['low_dose_rows']) and len(result['actual_level_rows'])==8 and all(r['pass'] for r in result['actual_level_rows'])
        if any(sha(Path(p))!=digest for p,digest in inputs.items()):raise ValueError('frozen numerical proof input changed')
    except (ValueError,OSError,KeyError,AssertionError,StopIteration) as error:
        result['failure']=str(error);result['all_pass']=False
    result['complete']=True;save();print('ALL-STATE/PREFIX PASS' if result['all_pass'] else 'ALL-STATE/PREFIX FAIL',flush=True)
    raise SystemExit(0 if result['all_pass'] else 2)

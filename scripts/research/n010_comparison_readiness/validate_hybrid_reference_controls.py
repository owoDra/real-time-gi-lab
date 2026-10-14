#!/usr/bin/env python3
"""Validate the streamed hybrid against every applicable original physical control."""
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
from reference_provenance import ROOT,RESULTS,sha,physical_proof
from readiness_preflight import replay
import validate_sampler as V
P=V.P
KEYS=('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(21600,21600))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--conformance',type=Path,default=RESULTS/'098-hybrid-full-numerical-conformance.json')
    args=parser.parse_args()
    if args.work.exists() or args.output.exists():raise ValueError('refuse existing control acquisition')
    ctypes.CDLL(None).prctl(15,b'n010_hyb_phys',0,0,0)
    full=args.conformance
    while True:
        if full.exists():
            data=json.loads(full.read_text())
            if data['complete']:
                if not data['all_pass']:raise ValueError('full numerical conformance failed; no control dispatch')
                break
        time.sleep(30)
    args.work.mkdir(parents=True)
    controls=ROOT/'out/research/n010-comparison-readiness/sampler-validation-v1/rqmc'
    cache=RESULTS/'022-cached-oracle-equivalence.json';cached=json.loads(cache.read_text())
    if not cached['complete'] or not cached['all_pass']:raise ValueError('CPU original control identity proof required')
    proof_rows={row['name']:row for row in cached['rows']}
    binary=ROOT/'out/research/n010-comparison-readiness/hybrid-oracle-build-v1/phos-n010-hybrid-reference'
    shader=ROOT/'out/research/n010-comparison-readiness/hybrid-oracle-build-v1/hybrid.spv'
    build_record=RESULTS/'095-hybrid-oracle-build.json';build=json.loads(build_record.read_text())
    if not build['all_pass'] or sha(binary)!=build['generated_sha256'][binary.name] or sha(shader)!=build['generated_sha256'][shader.name]:raise ValueError('hybrid build changed')
    names=sorted(p.stem.replace('.meta','') for p in controls.glob('*.meta.json'))
    if len(names)!=17:raise ValueError('expected every original point-light control scene')
    inputs={};physical_proof(inputs)
    paths=[binary,shader,Q.NET,cache,full,build_record,RESULTS.parent/'experiments/027-hybrid-physical-controls.md',Path(__file__),Path(V.__file__),Path(P.__file__),
        ROOT/'out/research/n010-comparison-readiness/hybrid-oracle-build-v1/hybrid.cpp',
        ROOT/'out/research/n010-comparison-readiness/hybrid-oracle-build-v1/hybrid.comp.glsl']
    for name in names:
        meta=controls/(name+'.meta.json');scene=controls/(name+'.n008');row=proof_rows[name]
        if sha(meta)!=row['original_metadata_sha256'] or sha(scene)!=row['scene_sha256']:raise ValueError('original control identity changed')
        paths += [meta,scene,controls/(name+'.hits')]
        for payload in row['payloads']:
            path=Path(str(controls/name)+payload['payload'])
            if sha(path)!=payload['old_sha256']:raise ValueError('original proved control payload changed')
            paths.append(path)
    inputs.update({str(p.resolve()):sha(p) for p in paths})
    result={'schema':'n010-hybrid-reference-physical-controls/1','complete':False,'all_pass':False,
        'gpu_run':True,'eligible_for_references':False,'input_sha256':inputs,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'frozen_scene_names':names,'seeds':list(Q.L.N007_SEEDS),'rows':[],
        'limits':{'address_space_bytes':4*1024**3,'cpu_seconds':21600,'elapsed_seconds':3600},
        'scope':'Every original applicable point-light control, unchanged original sample counts, all four seeds, whole-frame numerical/counter gates and original independent analytic/support gates. Unsupported emissive/box-camera cases are outside this adapter.',
        'thresholds':{'max_abs_mean_and_moment':1e-10,'indirect_nrmse':1e-8,'counter_disagreements':0},
        'scoring_exclusions':0,'cpu_fallback_threads':16,'implementation':'Streamed GPU samples plus independent original CPU whole-path recomputation under the fixed ambiguity guard; no stored reference-radiance/hit overrides','stop':'First runtime/numerical/physical failure retained; no automatic retry'}
    def save():args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    env=os.environ.copy();env['LD_LIBRARY_PATH']=':'.join(filter(None,[env.get('NIX_LD_LIBRARY_PATH'),env.get('LD_LIBRARY_PATH')]))
    all_gpu={};save()
    try:
        for name in names:
            meta=json.loads((controls/(name+'.meta.json')).read_text());all_gpu[name]=[]
            if meta['seeds']!=list(Q.L.N007_SEEDS):raise ValueError('original seed schedule mismatch')
            for i,seed in enumerate(Q.L.N007_SEEDS):
                if any(sha(Path(p))!=digest for p,digest in inputs.items()):raise ValueError('frozen controls changed')
                for proc in Path('/proc').iterdir():
                    if not proc.name.isdigit():continue
                    try:comm=(proc/'comm').read_text().strip()
                    except OSError:continue
                    if comm.startswith('phos-'):raise ValueError('another GPU image producer is active')
                out=args.work/f'{name}-seed{i}'
                command=['bash','scripts/run_with_vulkan.sh',str(binary),str(controls/(name+'.n008')),str(Q.NET),str(shader),str(seed),str(meta['spp']),'16','16',str(out.resolve())]
                row={'name':name,'seed_index':i,'seed':seed,'spp':meta['spp'],'command':command,'pass':False}
                result['rows'].append(row);save()
                try:
                    proc=subprocess.run(command,cwd=ROOT,env=env,text=True,capture_output=True,timeout=3600,preexec_fn=limits)
                    (args.work/f'{name}-seed{i}.stdout').write_text(proc.stdout);(args.work/f'{name}-seed{i}.stderr').write_text(proc.stderr);row['returncode']=proc.returncode
                except subprocess.TimeoutExpired:
                    row['failure']='bounded elapsed guard';raise ValueError('GPU control timeout')
                if proc.returncode:raise ValueError('GPU control execution failed')
                gpu=Q.L.read_sidecar(out/'o.f64');cpu=Q.L.read_sidecar(controls/f'{name}.s{i}.f64');gmeta=json.loads((out/'gpu.json').read_text())
                if any(gpu[k]!=cpu[k] for k in ('width','height','spp','seed')):raise ValueError('control sidecar identity mismatch')
                difference=gpu['mean']-cpu['mean'];den=float(np.sum(cpu['mean'][...,2,:]**2));ind=difference[...,2,:]
                nrmse=float(np.sqrt(np.sum(ind**2)/den)) if den else (0.0 if not np.any(ind) else None)
                row.update(all_finite=bool(all(np.isfinite(x).all() for x in (gpu['mean'],gpu['m2'],cpu['mean'],cpu['m2']))),
                    max_abs_mean=float(np.max(np.abs(difference))),max_abs_moment=float(np.max(np.abs(gpu['m2']-cpu['m2']))),indirect_nrmse=nrmse,
                    primary_records_byte_equal=(out/'o.hits').read_bytes()==(controls/(name+'.hits')).read_bytes(),
                    direct_mean_byte_equal=gpu['mean'][...,1,:].tobytes()==cpu['mean'][...,1,:].tobytes(),emission_mean_byte_equal=gpu['mean'][...,0,:].tobytes()==cpu['mean'][...,0,:].tobytes(),
                    counters_equal=all(gmeta[k]==meta['runs'][i][k] for k in KEYS),fault_flags=gmeta['fault_flags'],
                    geometry_hash_match=gmeta['geometry_sha256']==meta['geometry_sha256'],
                    memory_replay=replay(json.loads((out/'allocation-ledger.json').read_text())),payload_sha256={p.name:sha(p) for p in out.iterdir() if p.is_file()})
                row['pass']=bool(row['all_finite'] and row['max_abs_mean']<=1e-10 and row['max_abs_moment']<=1e-10 and nrmse is not None and nrmse<=1e-8 and row['primary_records_byte_equal'] and row['direct_mean_byte_equal'] and row['emission_mean_byte_equal'] and row['counters_equal'] and row['fault_flags']==0 and row['memory_replay'] and row['geometry_hash_match'])
                all_gpu[name].append((gpu,gmeta));save();print(name,i,'PASS' if row['pass'] else 'FAIL',flush=True)
                if not row['pass']:raise ValueError('fixed control numerical gate failed')
        def load_control(res,scene,out,name,spp):
            if (controls/(name+'.n008')).read_text()!=scene.text():raise ValueError('independent analytic control generated a different scene')
            values=all_gpu[name];means=np.stack([v[0]['mean'] for v in values]);meta=json.loads((controls/(name+'.meta.json')).read_text())
            if meta['spp']!=spp:raise ValueError('physical control sample count changed')
            meta['run_counters']=[{'seed':v[1]['seed'],**{k:v[1][k] for k in KEYS}} for v in values]
            res.runs.append(meta)
            return {'mean':means.mean(0),'se':means.std(0,ddof=1)/2,'per_seed':[v[0] for v in values],'meta':meta}
        P.render=load_control;V.render=load_control;P.check_stat=V.analytic_gate;P.STAT_SPP=8192
        result['physical_checks']=[]
        for fn in (lambda:P.control_a2(args.work/'analytic'),lambda:P.control_a2(args.work/'analytic','A2b','n001_soft',1),
            lambda:P.control_a4(args.work/'analytic'),lambda:P.control_a8(args.work/'analytic'),lambda:V.no_leak(args.work/'analytic'),
            lambda:P.control_a6(args.work/'analytic'),lambda:P.control_a6(args.work/'analytic','A10',1.6),lambda:P.control_a7(args.work/'analytic')):
            check=fn().to_json();result['physical_checks'].append(check);save()
        result['all_pass']=len(result['rows'])==68 and all(row['pass'] for row in result['rows']) and all(check['pass'] for check in result['physical_checks'])
        if any(sha(Path(p))!=digest for p,digest in inputs.items()):raise ValueError('physical proof inputs changed during acquisition')
    except (ValueError,OSError,KeyError,AssertionError) as error:
        result['failure']=str(error)
        result['all_pass']=False
    result['complete']=True;save();print('PHYSICAL DIAGNOSTIC PASS' if result['all_pass'] else 'PHYSICAL DIAGNOSTIC FAIL',flush=True)
    raise SystemExit(0 if result['all_pass'] else 2)

#!/usr/bin/env python3
"""015 bounded standalone CPU build, actual-kernel tests and one-scene pilot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

import numpy as np
import closest_primary_step as F

R,C,K=F.R,F.C,F.K
ROOT=C.ROOT
SOURCE=ROOT/'src/research/lane_m_gi_competitiveness'
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/015-all-bounce-directional-guide-cpu-feasibility.md'
BASE=K.BASE
FILES=[SOURCE/name for name in ('guided_transport.hpp','guided_transport_cpu.cpp','test_guided_transport.cpp')]
FILES += [Path(__file__).resolve(),PROTOCOL,ROOT/'src/research/n008_hdr_oracle/n008_oracle.hpp']


def write(path,data):
    with path.open('x') as handle:json.dump(data,handle,indent=2,allow_nan=False);handle.write('\n')


def source_inputs():return {str(p):C.sha(p) for p in FILES}


def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def new_root(path):
    path=path.resolve()
    R.require(path.is_relative_to(BASE) and not path.exists(),'015 output must be new under repository/out; no overwrite')
    path.mkdir(parents=True)
    return path


def guarded(command,work,cpu=300,wall=600):
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(cpu,cpu))
        resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    start=time.monotonic()
    p=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                       text=True,start_new_session=True,preexec_fn=limits)
    timeout=False
    try:out,err=p.communicate(timeout=wall)
    except subprocess.TimeoutExpired:
        timeout=True;os.killpg(p.pid,signal.SIGTERM)
        try:out,err=p.communicate(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
    (work/'stdout.txt').write_text(out);(work/'stderr.txt').write_text(err)
    return dict(command=command,returncode=p.returncode,timed_out=timeout,diagnostic_wall_seconds=time.monotonic()-start,stdout=out,stderr=err)


def build(out):
    out=new_root(out)
    record=dict(schema='m001-guide-cpu-build/1',complete=False,gpu_executed=False,
                source_commit=head(),input_sha256=source_inputs(),rows=[])
    try:
        compiler=Path(shutil.which('c++')).resolve();record['compiler']=str(compiler)
        record['compiler_version']=subprocess.check_output([str(compiler),'--version'],text=True)
        for name in ('test_guided_transport','guided_transport_cpu'):
            dest=out/name;work=out/(name+'-compile');work.mkdir()
            command=[str(compiler),'-std=c++20','-O2','-fno-fast-math','-ffp-contract=off',
                     '-fsanitize=undefined','-fno-sanitize-recover=all','-MD','-MF',str(out/(name+'.d')),
                     '-I'+str(SOURCE),'-I'+str(ROOT/'src/research/n008_hdr_oracle'),str(SOURCE/(name+'.cpp')),'-o',str(dest)]
            row=guarded(command,work,120,180);record['rows'].append(row)
            R.require(row['returncode']==0 and not row['timed_out'],'015 CPU compile failed; preserve/stop')
        work=out/'actual-kernel-tests';work.mkdir()
        tests=guarded([str(out/'test_guided_transport')],work,120,180);record['rows'].append(tests)
        R.require(tests['returncode']==0 and not tests['timed_out'],'015 actual-kernel CPU tests failed; preserve/stop')
        record['actual_contracts']=json.loads(tests['stdout'])
        record['binary_sha256']=C.sha(out/'guided_transport_cpu')
        dependencies={}
        import shlex
        for file in out.glob('*.d'):
            for name in shlex.split(file.read_text().replace('\\\n',' ').split(':',1)[1]):
                path=Path(name).resolve();dependencies[str(path)]=C.sha(path)
        record['dependency_sha256']=dependencies
        F.rehash(record['input_sha256']);record['complete']=True
    except Exception as exc:record['error']=repr(exc)
    finally:write(out/'result.json',record)
    return record


def intake(capture,refs):
    native=R.read(capture/'capture.json')
    R.require(native['schema']=='m001-all-bounce-guide-cpu-native/1' and native['gpu_executed'] is False
              and native['candidate_is_independent_reference'] is False and native['spp']==1024
              and native['grid']==8 and native['bins']==64 and native['training_paths']==65536
              and native['seeds']==list(R.Q.L.N007_SEEDS),'015 native boundary differs')
    primary=np.fromfile(capture/'all-primary.bin',dtype=[('t','<f8'),('tri','<u4'),('front','<u4')])
    R.require(primary.shape==(57600,),'015 complete primary shape differs')
    qual=R.read(Path(refs['8']['directory'])/'qualification.json');spp=qual['levels'][-1]['spp']
    oracle_hits=(Path(refs['8']['directory'])/f'o.n{spp}.hits').read_bytes()
    R.require(oracle_hits[:8]==b'N008HIT\0' and (capture/'all-primary.bin').read_bytes()==oracle_hits[16:],
              '015 original oracle primary bytes differ')
    hits=np.flatnonzero(primary['tri']!=0xffffffff)
    selected=np.fromfile(capture/'selected-pixels.u32',dtype='<u4')
    expected=hits[((2*np.arange(16)+1)*len(hits))//32]
    R.require(selected.shape==(16,) and np.array_equal(selected,expected)
              and native['primary_hit_pixels']==len(hits) and native['primary_scan_queries']==57600,
              '015 geometry-only pixel selection differs')
    weights=np.fromfile(capture/'training-weights.f64',dtype='<f8')
    cdf=np.fromfile(capture/'guide-cdf.u32',dtype='<u4')
    R.require(weights.size==cdf.size==512*7*64,'015 complete guide storage size differs')
    weights=weights.reshape(-1,64);cdf=cdf.reshape(-1,64).astype(np.int64)
    R.require(np.isfinite(weights).all() and (weights>=0).all() and (cdf[:,-1]==2**24).all()
              and (np.diff(cdf,axis=1)>=0).all(),'015 guide weight/CDF invalid')
    masses=np.diff(cdf,axis=1,prepend=0)
    largest=weights.max(axis=1);positive=largest>0
    scaled=weights[positive].astype(np.longdouble)/largest[positive,None]
    ideal=scaled/scaled.sum(axis=1,keepdims=True)*2**24
    R.require((np.abs(masses[positive]-ideal)<=1+1e-8).all()
              and (masses[~positive]==2**24//64).all(),'015 quantized PDF mass/fallback differs')
    expected_files={'capture.json','all-primary.bin','selected-pixels.u32','training-weights.f64','guide-cdf.u32'}
    rows={};derived={};sample_count=4*16*1024
    R.require([(x['depth'],x['guided']) for x in native['rows']]==[(d,g) for d in (2,8) for g in (False,True)],'015 fixed native row order differs')
    for x in native['rows']:
        expected_files|={x['sample_file'],x['direct_file']}
        samples=np.fromfile(capture/x['sample_file'],dtype='<f8');direct=np.fromfile(capture/x['direct_file'],dtype='<f8')
        R.require(samples.size==sample_count and direct.size==64 and np.isfinite(samples).all()
                  and (samples>=0).all() and np.isfinite(direct).all() and (direct>=0).all(),'015 sample coverage/value invalid')
        samples=samples.reshape(4,16,1024);direct=direct.reshape(4,16)
        mean=samples.mean(axis=2);variance=samples.var(axis=2,ddof=1)
        R.require(type(x['closest_queries']) is int and x['closest_queries']>=64
                  and type(x['shadow_queries']) is int and x['shadow_queries']>=0
                  and type(x['null_samples']) is int and 0<=x['null_samples']<=sample_count,'015 invalid query counters')
        if not x['guided']:R.require(x['null_samples']==0,'015 cosine role has mixture nulls')
        role='guided' if x['guided'] else 'cosine';name=f"b{x['depth']}-{role}"
        rdir=Path(refs[str(x['depth'])]['directory']);q=R.read(rdir/'qualification.json');nspp=q['levels'][-1]['spp']
        reference=np.mean([R.Q.L.read_sidecar(rdir/f'o.n{nspp}.s{i}.f64')['mean'] for i in range(4)],axis=0)
        ri=reference.reshape(57600,4,3)[selected,2,0];rms=float(np.sqrt(np.mean(ri**2)))
        rows[name]=dict(depth=x['depth'],role=role,samples=sample_count,zero_samples=int((samples==0).sum()),
                        null_samples=x['null_samples'],closest_queries=x['closest_queries'],shadow_queries=x['shadow_queries'],
                        summed_unbiased_sample_variance=float(variance.sum()),per_seed_pixel_means=mean.tolist(),
                        per_seed_pixel_variances=variance.tolist(),per_seed_pixel_direct=direct.tolist(),
                        subset_indirect_nrmse=float(np.sqrt(np.mean((mean.mean(axis=0)-ri)**2))/rms) if rms>0 else None,
                        subset_is_full_image_quality_evidence=False)
        derived[name+'.means.npy']=mean;derived[name+'.variances.npy']=variance
    R.require({str(p.relative_to(capture)) for p in capture.rglob('*') if p.is_file()}==expected_files,'015 missing/extra CPU payload')
    training=native['training_closest_queries']+native['training_shadow_queries'];efficiency={}
    R.require(training>0,'015 empty training cost')
    for d in (2,8):
        a,b=rows[f'b{d}-cosine'],rows[f'b{d}-guided'];va,vb=a['summed_unbiased_sample_variance'],b['summed_unbiased_sample_variance']
        ca=a['closest_queries']+a['shadow_queries'];cb=b['closest_queries']+b['shadow_queries']+training
        R.require(va>0 and vb>0 and np.isfinite([va,vb]).all() and ca>0 and cb>0,'015 undefined feasibility evidence')
        effect=va*ca/(vb*cb);R.require(np.isfinite(effect) and effect>0,'015 invalid efficiency ratio')
        efficiency[str(d)]=dict(ratio=effect,pass_=effect>=1.20,cosine_cost_queries=ca,guided_cost_queries=cb,
                               full_training_cost_charged=training,scoring_exclusions=0,accepted_gpu_timing=False)
    return dict(valid=True,classification='CPU_FEASIBILITY_PASS' if all(x['pass_'] for x in efficiency.values()) else 'REJECTED_NO_GPU',
                native=native,selected_pixels=selected.tolist(),rows=rows,efficiency=efficiency,
                whole_image_quality_admitted=False,accepted_timing=False),derived


def pilot(cell,build_root,out):
    R.require(cell in ('H01','H02','H03'),'015 unregistered scene')
    R.require(sys.byteorder=='little','015 little-endian native ABI required')
    R.require(not subprocess.check_output(['git','diff','HEAD','--','scripts','src','shaders'],cwd=ROOT),'Commit015source before pilot')
    for path,h in source_inputs().items():
        committed=subprocess.check_output(['git','show',head()+':'+str(Path(path).relative_to(ROOT))],cwd=ROOT)
        R.require(hashlib.sha256(committed).hexdigest()==h,'015 consumed source not committed')
    out=new_root(out);record=dict(schema='m001-guide-cpu-pilot/1',cell=cell,complete=False,valid=False,
                                  source_commit=head(),gpu_executed=False,accepted_timing=False)
    try:
        for previous in ('H01','H02','H03')[:('H01','H02','H03').index(cell)]:
            old=R.read(BASE/f'm001-guide-cpu-{previous.lower()}-v1/result.json')
            R.require(old['complete'] and old['valid'],'015 earlier scene invalid/missing; stop')
        R.quiet();R.require(shutil.disk_usage(out).free>=16*1024**3,'015 requires16GiB free')
        build_record=R.read(build_root/'result.json');R.require(build_record['complete'],'015 build/tests unavailable')
        F.rehash(build_record['input_sha256']);F.rehash(build_record['dependency_sha256'])
        binary=build_root/'guided_transport_cpu';R.require(C.sha(binary)==build_record['binary_sha256'],'015 binary drift')
        inputs=source_inputs();inputs[str(build_root/'result.json')]=C.sha(build_root/'result.json');inputs[str(binary)]=C.sha(binary)
        refs=F.reference_inputs(K.Case(cell,'hwrt'),inputs)
        scene=Path(refs['8']['directory'])/'scene.n008'
        plan=dict(source_commit=head(),cell=cell,build=str(build_root),input_sha256=inputs,reference_verification=refs,
                  command=[str(binary),'--scene',str(scene),'--out',str(out/'capture')],gpu_executed=False)
        write(out/'plan.json',plan)
        write(out/'started.json',dict(cpu_only=True,plan_sha256=C.sha(out/'plan.json')))
        native=guarded(plan['command'],out);record['native_process']=native
        R.require(native['returncode']==0 and not native['timed_out'],'015 CPU acquisition invalid; preserve/stop')
        F.rehash(inputs)
        scored,arrays=intake(out/'capture',refs)
        record.update(scored)
        scores=out/'scores';scores.mkdir()
        for name,array in arrays.items():
            with (scores/name).open('xb') as handle:np.save(handle,array,allow_pickle=False)
        record['score_sha256']={name:C.sha(scores/name) for name in arrays}
        record['plan_sha256']=C.sha(out/'plan.json');record['complete']=True
    except Exception as exc:record.update(error=repr(exc),classification='INVALID_STOP_NO_RETRY')
    finally:
        record['payload_sha256']={str(p.relative_to(out)):C.sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
        write(out/'result.json',record)
    return record


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=['build','pilot']);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cell',choices=['H01','H02','H03']);ap.add_argument('--build',type=Path)
    args=ap.parse_args()
    if args.action=='build':result=build(args.out)
    else:
        R.require(args.cell is not None and args.build is not None,'015 pilot needs --cell/--build')
        result=pilot(args.cell,args.build.resolve(),args.out)
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_sha256','dependency_sha256','rows','payload_sha256','native_process')},indent=2))
    sys.exit(0 if result['complete'] else 1)

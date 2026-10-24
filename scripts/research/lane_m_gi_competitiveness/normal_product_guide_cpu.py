#!/usr/bin/env python3
"""016 fixed candidate-only CPU acquisition using immutable015 training/controls."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import numpy as np
import guided_transport_cpu as G

R,C,K,F=G.R,G.C,G.K,G.F
ROOT,SOURCE,BASE=G.ROOT,G.SOURCE,G.BASE
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/016-normal-product-guide-cpu-feasibility.md'
FILES=G.FILES+[SOURCE/x for x in ('normal_product_guide.hpp','normal_product_guide_cpu.cpp','test_normal_product_guide.cpp')]+[Path(__file__).resolve(),PROTOCOL]
RESULTS=ROOT/'research/lanes/lane-m-gi-competitiveness/results'
CELLS=('H01','H02','H03')

def source_inputs():return {str(p):C.sha(p) for p in FILES}


def new_root(path):
    path=path.resolve()
    R.require(path.is_relative_to(BASE) and not path.exists(),'016 needs new output under repository/out')
    path.mkdir(parents=True);return path


def build(out):
    out=new_root(out);record=dict(schema='m001-product-cpu-build/1',complete=False,gpu_executed=False,
                                 source_commit=G.head(),input_sha256=source_inputs(),rows=[])
    try:
        compiler=Path(shutil.which('c++')).resolve();record['compiler']=str(compiler)
        record['compiler_version']=subprocess.check_output([str(compiler),'--version'],text=True)
        for name in ('test_normal_product_guide','normal_product_guide_cpu'):
            work=out/(name+'-compile');work.mkdir()
            cmd=[str(compiler),'-std=c++20','-O2','-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all',
                 '-MD','-MF',str(out/(name+'.d')),'-I'+str(SOURCE),'-I'+str(ROOT/'src/research/n008_hdr_oracle'),str(SOURCE/(name+'.cpp')),'-o',str(out/name)]
            row=G.guarded(cmd,work,120,180);record['rows'].append(row)
            R.require(row['returncode']==0 and not row['timed_out'],'016 compile failed; preserve/stop')
        work=out/'actual-kernel-tests';work.mkdir()
        row=G.guarded([str(out/'test_normal_product_guide')],work,120,180);record['rows'].append(row)
        R.require(row['returncode']==0 and not row['timed_out'],'016 actual kernel tests failed; preserve/stop')
        record['actual_contracts']=json.loads(row['stdout']);record['binary_sha256']=C.sha(out/'normal_product_guide_cpu')
        deps={}
        for file in out.glob('*.d'):
            for name in shlex.split(file.read_text().replace('\\\n',' ').split(':',1)[1]):
                path=Path(name).resolve();deps[str(path)]=C.sha(path)
        record['dependency_sha256']=deps
        # Reuse, rehash and explicitly identify the prior25checks, never rerun.
        prior=RESULTS/'099-all-bounce-guide-cpu-preparation.json';p=R.read(prior)
        R.require(p['complete'] and p['actual_contract_checks']==25 and not p['gpu_executed'],'015 kernel gate unavailable')
        R.require(C.sha(Path(p['raw_build_receipt']))==p['raw_build_receipt_sha256'],'015 build receipt drift')
        old=R.read(Path(p['raw_build_receipt']));F.rehash(old['input_sha256']);F.rehash(old['dependency_sha256'])
        record['prior_kernel_checks_reused']=25;record['prior_preparation_sha256']=C.sha(prior)
        F.rehash(record['input_sha256']);record['complete']=True
    except Exception as exc:record['error']=repr(exc)
    finally:G.write(out/'result.json',record)
    return record


def old_inputs(cell,inputs):
    old=BASE/f'm001-guide-cpu-{cell.lower()}-v1';receipt=R.read(old/'result.json')
    # Anchor old result bytes in already published, immutable100 proof.
    published=R.read(RESULTS/'100-all-bounce-guide-cpu-feasibility-raw-replay.json')
    # Full old receipt chain is also pinned by the frozen final raw replay.
    final_path=BASE/'m001-guide-cpu-final-replay-v1/result.json'
    verification=R.read(RESULTS/'102-all-bounce-guide-cpu-feasibility-verification.json')
    R.require(C.sha(final_path)==verification['raw_receipt_sha256'],'015 final replay drift')
    # Published100 embeds exact original receipts; check membership independently of key layout.
    needle=C.sha(old/'result.json')
    R.require(needle in json.dumps(published),'015 result identity absent from published replay')
    R.require(receipt['complete'] and receipt['valid'] and receipt['gpu_executed'] is False,'015 source pilot unavailable')
    R.require({str(p.relative_to(old)) for p in old.rglob('*') if p.is_file()}==set(receipt['payload_sha256'])|{'result.json'},'015 inventory changed')
    inputs.update({str(old/p):h for p,h in receipt['payload_sha256'].items()})
    for path in (old/'result.json',final_path,RESULTS/'100-all-bounce-guide-cpu-feasibility-raw-replay.json',RESULTS/'102-all-bounce-guide-cpu-feasibility-verification.json'):
        inputs[str(path)]=C.sha(path)
    plan=R.read(old/'plan.json');inputs.update(plan['input_sha256'])
    build=R.read(Path(plan['build'])/'result.json');inputs.update(build['input_sha256']);inputs.update(build['dependency_sha256'])
    R.require(C.sha(Path(plan['build'])/'guided_transport_cpu')==build['binary_sha256'],'015 binary drift')
    inputs[str(Path(plan['build'])/'guided_transport_cpu')]=build['binary_sha256']
    F.rehash(inputs)
    return old,receipt


def intake(capture,old,refs):
    previous,_=G.intake(old/'capture',refs)
    native=R.read(capture/'capture.json')
    R.require(native['schema']=='m001-normal-product-guide-cpu-native/1' and native['gpu_executed'] is False
              and native['candidate_is_independent_reference'] is False and native['new_training_paths']==0
              and native['grid']==8 and native['bins']==64 and native['spp']==1024
              and native['seeds']==list(R.Q.L.N007_SEEDS),'016 native boundary differs')
    for key in ('guide_lo','guide_extent','primary_hit_pixels','primary_scan_queries'):
        R.require(native[key]==previous['native'][key],'016 field/primary boundary differs')
    for name in ('all-primary.bin','selected-pixels.u32'):
        R.require((capture/name).read_bytes()==(old/'capture'/name).read_bytes(),'016 geometry bytes differ')
    R.require([x['depth'] for x in native['rows']]==[2,8],'016 row order differs')
    expected={'capture.json','all-primary.bin','selected-pixels.u32'};rows={};arrays={};efficiency={}
    train=previous['native']['training_closest_queries']+previous['native']['training_shadow_queries']
    for x in native['rows']:
        depth=x['depth'];name=f'b{depth}-product';expected|={name+'.samples.f64',name+'.direct.f64'}
        R.require(x['sample_file']==name+'.samples.f64' and x['direct_file']==name+'.direct.f64','016 output names differ')
        values=np.fromfile(capture/x['sample_file'],dtype='<f8');direct=np.fromfile(capture/x['direct_file'],dtype='<f8')
        R.require(values.size==65536 and direct.size==64 and np.isfinite(values).all() and (values>=0).all()
                  and np.isfinite(direct).all() and (direct>=0).all(),'016 invalid sample coverage/values')
        R.require((capture/x['direct_file']).read_bytes()==(old/'capture'/f'b{depth}-cosine.direct.f64').read_bytes(),'016 primary direct changed')
        for key in ('closest_queries','shadow_queries','null_samples'):
            R.require(type(x[key]) is int and x[key]>=0,'016 invalid query counters')
        R.require(x['closest_queries']>=64 and x['null_samples']<=65536,'016 invalid query count boundary')
        values=values.reshape(4,16,1024);mean=values.mean(axis=2);variance=values.var(axis=2,ddof=1)
        rows[name]=dict(depth=depth,role='product',samples=65536,zero_samples=int((values==0).sum()),
                        null_samples=x['null_samples'],closest_queries=x['closest_queries'],shadow_queries=x['shadow_queries'],
                        summed_unbiased_sample_variance=float(variance.sum()),per_seed_pixel_means=mean.tolist(),
                        per_seed_pixel_variances=variance.tolist(),per_seed_pixel_direct=direct.reshape(4,16).tolist())
        arrays[name+'.means.npy']=mean;arrays[name+'.variances.npy']=variance
        a=previous['rows'][f'b{depth}-cosine'];b=rows[name];va=a['summed_unbiased_sample_variance'];vb=b['summed_unbiased_sample_variance']
        ca=a['closest_queries']+a['shadow_queries'];cb=b['closest_queries']+b['shadow_queries']+train
        R.require(va>0 and vb>0 and np.isfinite([va,vb]).all() and ca>0 and cb>0,'016 undefined efficiency evidence')
        ratio=va*ca/(vb*cb);R.require(np.isfinite(ratio) and ratio>0,'016 invalid ratio')
        efficiency[str(depth)]=dict(ratio=ratio,pass_=ratio>=1.20,cosine_cost_queries=ca,product_cost_queries=cb,
                                   full_original_training_cost_charged=train,scoring_exclusions=0,accepted_gpu_timing=False)
    R.require({str(p.relative_to(capture)) for p in capture.rglob('*') if p.is_file()}==expected,'016 capture inventory differs')
    return dict(valid=True,classification='CPU_FEASIBILITY_PASS' if all(x['pass_'] for x in efficiency.values()) else 'REJECTED_NO_GPU',
                native=native,selected_pixels=previous['selected_pixels'],rows=rows,efficiency=efficiency,
                reused_cosine_rows={f'b{d}-cosine':previous['rows'][f'b{d}-cosine'] for d in (2,8)},
                new_render_paths=131072,reused_cosine_render_paths=131072,new_training_paths=0,reused_training_paths=65536,
                whole_image_quality_admitted=False,accepted_timing=False),arrays


def pilot(cell,build_root,out):
    R.require(cell in CELLS and sys.byteorder=='little','016 unregistered scene/ABI')
    for path,digest in source_inputs().items():
        committed=subprocess.check_output(['git','show',G.head()+':'+str(Path(path).relative_to(ROOT))],cwd=ROOT)
        R.require(hashlib.sha256(committed).hexdigest()==digest,'Commit016source before pilot')
    out=new_root(out);record=dict(schema='m001-product-cpu-pilot/1',cell=cell,complete=False,valid=False,
                                  source_commit=G.head(),gpu_executed=False,accepted_timing=False)
    try:
        for prior in CELLS[:CELLS.index(cell)]:
            p=R.read(BASE/f'm001-product-cpu-{prior.lower()}-v1/result.json')
            R.require(p['complete'] and p['valid'],'016 prior scene invalid; stop')
        R.quiet();R.require(shutil.disk_usage(out).free>=16*1024**3,'016 requires16GiB disk')
        build=R.read(build_root/'result.json');R.require(build['complete'],'016 build/tests unavailable')
        F.rehash(build['input_sha256']);F.rehash(build['dependency_sha256']);binary=build_root/'normal_product_guide_cpu'
        R.require(C.sha(binary)==build['binary_sha256'],'016 binary drift')
        inputs=source_inputs();inputs[str(build_root/'result.json')]=C.sha(build_root/'result.json');inputs[str(binary)]=C.sha(binary)
        old,receipt=old_inputs(cell,inputs);refs=F.reference_inputs(K.Case(cell,'hwrt'),inputs)
        # Validate every old payload and numerical row before any new native path.
        old_score,_=G.intake(old/'capture',refs)
        R.require(old_score['efficiency']==receipt['efficiency'] and old_score['rows']==receipt['rows'],'015 raw replay mismatch')
        scene=Path(refs['8']['directory'])/'scene.n008'
        plan=dict(source_commit=G.head(),cell=cell,build=str(build_root),old_pilot=str(old),input_sha256=inputs,reference_verification=refs,
                  command=[str(binary),'--scene',str(scene),'--weights',str(old/'capture/training-weights.f64'),'--out',str(out/'capture')],gpu_executed=False)
        G.write(out/'plan.json',plan);G.write(out/'started.json',dict(cpu_only=True,plan_sha256=C.sha(out/'plan.json')))
        native=G.guarded(plan['command'],out);record['native_process']=native
        R.require(native['returncode']==0 and not native['timed_out'],'016 acquisition invalid; preserve/stop')
        F.rehash(inputs);scored,arrays=intake(out/'capture',old,refs);record.update(scored)
        scores=out/'scores';scores.mkdir()
        for name,array in arrays.items():
            with (scores/name).open('xb') as handle:np.save(handle,array,allow_pickle=False)
        record['score_sha256']={name:C.sha(scores/name) for name in arrays};record['plan_sha256']=C.sha(out/'plan.json');record['complete']=True
    except Exception as exc:record.update(error=repr(exc),classification='INVALID_STOP_NO_RETRY')
    finally:
        record['payload_sha256']={str(p.relative_to(out)):C.sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
        G.write(out/'result.json',record)
    return record


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('build','pilot'));ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cell',choices=CELLS);ap.add_argument('--build',type=Path);args=ap.parse_args()
    if args.action=='build':record=build(args.out)
    else:
        R.require(args.cell is not None and args.build is not None,'016 pilot needs --cell/--build')
        record=pilot(args.cell,args.build.resolve(),args.out)
    print(json.dumps({k:record[k] for k in ('schema','complete','valid','error','classification','actual_contracts','efficiency') if k in record},indent=2))
    sys.exit(0 if record['complete'] else 1)

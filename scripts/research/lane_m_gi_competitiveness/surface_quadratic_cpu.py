#!/usr/bin/env python3
"""018 one-target geometry-fitted quadratic reconstruction, no rendering/GPU."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import geometry_filter_cpu as P
import surface_quadratic_filter as Q

R,C,F,G=P.R,P.C,P.F,P.G
ROOT,BASE,RESULTS=P.ROOT,P.BASE,P.RESULTS
PROTOCOL=RESULTS.parent/'experiments/018-surface-quadratic-reconstruction-cpu-screen.md'
OWN=[Path(__file__).resolve(),Path(Q.__file__).resolve(),Path(__file__).with_name('test_surface_quadratic_filter.py'),PROTOCOL]
PREPARATION=RESULTS/'111-surface-quadratic-reconstruction-cpu-preparation.json'
TARGETS,SPP=P.TARGETS,P.SPP


def inputs_now():
    inputs=P.inputs_now();inputs.update({str(p):C.sha(p) for p in OWN});return inputs


def prepare_inputs(cell,depth):
    inputs,proofs=P.prepare_inputs(cell,depth)
    publication=RESULTS/'108-geometry-barrier-reconstruction-six-targets-raw-replay.json';P.pin(publication,inputs)
    old=next(x for x in R.read(publication)['records'] if (x['cell'],x['depth'])==(cell,depth));audit=old['audit']
    R.require(audit['complete'] and audit['valid'] and audit['geometry_masks_replayed'],'018 old geometry evidence invalid')
    P.pin(Path(old['audit_receipt']),inputs,old['audit_receipt_sha256'])
    receipt=Path(audit['receipt']);P.pin(receipt,inputs,audit['receipt_sha256']);record=R.read(receipt);work=receipt.parent
    R.require(record['complete'] and record['valid'] and record['gpu_executed'] is False,'018 old CPU source invalid')
    R.require({str(p.relative_to(work)) for p in work.rglob('*') if p.is_file()}==set(record['payload_sha256'])|{'result.json'},'018 old CPU inventory differs')
    for name,digest in record['payload_sha256'].items():
        path=(work/name).resolve();R.require(path.is_relative_to(work.resolve()),'018 unsafe old inventory');P.pin(path,inputs,digest)
    inputs.update(R.read(work/'plan.json')['input_sha256'])
    old_gate=R.read(P.PREPARATION)
    R.require(old_gate['complete'] and old_gate['actual_new_contract_tests']==16,'018 prior017 kernel checks unavailable')
    P.pin(P.PREPARATION,inputs);P.pin(Path(old_gate['raw_test_receipt']),inputs,old_gate['raw_test_receipt_sha256'])
    inputs.update(inputs_now());F.rehash(inputs)
    proofs['old_017_work']=str(work)
    return inputs,proofs


def geometry(proofs):
    old=Path(proofs['old_017_work'])
    with np.load(old/'geometry.npz',allow_pickle=False) as data:
        pos,normal,hit,material,epsilon=(data[name] for name in ('position','normal','hit','material','epsilon'))
    with np.load(old/'geometry-masks.npz',allow_pickle=False) as data:masks=data['masks']
    P.B.validate_geometry(pos,normal,hit,material,float(epsilon))
    expected=P.geometry(Path(proofs['primary_capture']))
    for a,b in zip((pos,normal,hit,material,epsilon),expected):R.require(np.array_equal(a,b),'018 old geometry and actual source differ')
    R.require(masks.shape==(3,25,180,320) and masks.dtype==np.bool_,'018 old geometry masks differ')
    return pos,normal,hit,material,float(epsilon),masks


def coefficient_summary(coefficients,maps,hit):
    rows=[]
    for stage,stride in enumerate(P.B.STRIDES):
        c=coefficients[stage];model=maps['model'][stage];bits=maps['selected_columns'][stage]
        ranks=np.array([int(v).bit_count() for v in bits[hit]],dtype=np.uint8)
        rows.append(dict(stride=stride,quadratic_model_pixels=int((model==0).sum()),affine_fallback_pixels=int((model==1).sum()),
                         constant_fallback_pixels=int((model==2).sum()),miss_pixels=int((model==255).sum()),
                         selected_rank_histogram={str(k):int((ranks==k).sum()) for k in range(1,7)},
                         maximum_coefficient_l1=float(np.abs(c).sum(axis=0).max()),
                         maximum_hit_constant_error=float(np.abs(c.sum(axis=0)[hit]-1).max()),
                         negative_coefficients=int((c<0).sum())))
    return rows


def run(cell,depth,out):
    for path in OWN:
        blob=subprocess.check_output(['git','show',G.head()+':'+str(path.relative_to(ROOT))],cwd=ROOT)
        R.require(hashlib.sha256(blob).hexdigest()==C.sha(path),'Commit018source before fitting')
    out=P.new_root(out);record=dict(schema='m001-surface-quadratic-cpu-target/1',cell=cell,depth=depth,complete=False,valid=False,
                                  source_commit=G.head(),gpu_executed=False,new_render_paths=0,new_reference_paths=0,accepted_timing=False)
    try:
        target=(cell,depth);R.require(target in TARGETS,'018 target unregistered')
        for c,d in TARGETS[:TARGETS.index(target)]:
            previous=R.read(BASE/f'm001-quadratic-{c.lower()}-b{d}-terminal-audit-v1/result.json')
            R.require(previous['complete'] and previous['valid'],'018 earlier independent terminal audit missing/invalid')
        gate=R.read(PREPARATION);R.require(gate['complete'] and gate['actual_new_contract_tests']==14,'018 CPU gate missing')
        F.rehash(gate['input_sha256']);R.quiet();R.require(shutil.disk_usage(out).free>=16*1024**3,'018 needs16GiB free')
        inputs,proofs=prepare_inputs(cell,depth);P.pin(PREPARATION,inputs)
        plan=dict(schema='m001-surface-quadratic-cpu-plan/1',cell=cell,depth=depth,source_commit=G.head(),input_sha256=inputs,
                  proof=proofs,stages=list(P.B.STRIDES),spp=list(SPP),gpu_executed=False)
        G.write(out/'plan.json',plan);G.write(out/'started.json',dict(plan_sha256=C.sha(out/'plan.json'),cpu_only=True))
        pos,normal,hit,material,epsilon,masks=geometry(proofs)
        coefficients,maps=Q.fit(pos,normal,hit,masks)
        P.save_arrays(out/'coefficients.npz',coefficients=coefficients,**maps)
        # Complete geometry-only coefficients/selection are saved before intensity.
        refdir=Path(proofs['reference']['directory']);q=R.read(refdir/'qualification.json');nspp=q['levels'][-1]['spp']
        mean=np.mean([R.Q.L.read_sidecar(refdir/f'o.n{nspp}.s{i}.f64')['mean'] for i in range(4)],axis=0)
        reference={name:mean[...,R.Q.L.COMPONENTS.index(name),:]@P.S.LUMA for name in ('direct','indirect','total')}
        bias_stages,bias_raw,bias_clipping=Q.reconstruct(reference['indirect'],coefficients)
        bias,errors=P.score_images(reference['direct'],bias_stages[-1],reference)
        P.save_arrays(out/'reference-bias-stages.npz',stages=bias_stages,unclipped=bias_raw);P.save_arrays(out/'reference-bias-errors.npz',**errors)
        rows=[]
        for level in proofs['levels']:
            spp=level['spp'];capture=Path(level['work'])/'capture'
            direct=R.Q.L.read_pfm(capture/'direct.pfm');indirect=R.Q.L.read_pfm(capture/'indirect.pfm')
            for a in (direct,indirect):R.require(a.shape==(180,320,3) and np.isfinite(a).all() and (a>=0).all()
                         and np.array_equal(a[...,0],a[...,1]) and np.array_equal(a[...,0],a[...,2]),'018 invalid original grey image')
            direct=direct@P.S.LUMA;indirect=indirect@P.S.LUMA
            stages,raw,clipping=Q.reconstruct(indirect,coefficients)
            components,errors=P.score_images(direct,stages[-1],reference)
            P.save_arrays(out/f'n{spp}-stages.npz',stages=stages,unclipped=raw);P.save_arrays(out/f'n{spp}-errors.npz',**errors)
            rows.append(dict(spp=spp,components=components,clipping=clipping,
                             classification='PASS' if P.B.quality(components) else 'QUALITY_FAIL',
                             original_pt_receipt_sha256=level['receipt_sha256'],scoring_exclusions=0))
        F.rehash(inputs);decision=P.B.decision(rows,bias)
        record.update(valid=True,complete=True,rows=rows,reference_bias_components=bias,reference_bias_clipping=bias_clipping,
                      decision=decision,classification='CPU_RECONSTRUCTION_FEASIBILITY_PASS' if decision['pass_'] else 'REJECTED_NO_GPU',
                      hit_pixels=int(hit.sum()),geometry_epsilon=epsilon,coefficient_bytes=int(coefficients.nbytes),
                      coefficient_summary=coefficient_summary(coefficients,maps,hit),plan_sha256=C.sha(out/'plan.json'),
                      source_sample_reduction_is_speed_claim=False)
    except Exception as exc:record.update(error=repr(exc),classification='INVALID_STOP_NO_RETRY')
    finally:
        record['payload_sha256']={str(p.relative_to(out)):C.sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
        G.write(out/'result.json',record)
    return record


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cell',choices=('H01','H02','H03'),required=True)
    ap.add_argument('--depth',type=int,choices=(2,8),required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    import resource
    resource.setrlimit(resource.RLIMIT_CPU,(300,300));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    r=run(a.cell,a.depth,a.out);print(json.dumps({k:r[k] for k in ('cell','depth','complete','valid','classification','decision','error') if k in r},indent=2))
    sys.exit(0 if r['complete'] else 1)

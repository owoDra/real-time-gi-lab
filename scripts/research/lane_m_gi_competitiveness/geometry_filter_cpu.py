#!/usr/bin/env python3
"""017 one-target full-image reconstruction of immutable original GPU PT data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import guided_transport_cpu as G
import geometry_barrier_filter as B
import closest_primary_audit as A
import score_hdr as S

R,C,K,F=G.R,G.C,G.K,G.F
ROOT,BASE=G.ROOT,G.BASE
RESULTS=ROOT/'research/lanes/lane-m-gi-competitiveness/results'
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/017-geometry-barrier-reconstruction-cpu-screen.md'
OWN=[Path(__file__).resolve(),Path(B.__file__).resolve(),Path(__file__).with_name('test_geometry_barrier_filter.py'),PROTOCOL]
TARGETS=tuple((c,d) for c in ('H01','H02','H03') for d in (2,8))
SPP=(1,4,16,64)
PREPARATION=RESULTS/'107-geometry-barrier-reconstruction-cpu-preparation.json'


def inputs_now():
    paths=set(OWN)
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if file:
            p=Path(file).resolve()
            if p.is_relative_to(ROOT/'scripts/research') and p.suffix=='.py':paths.add(p)
    return {str(p):C.sha(p) for p in sorted(paths)}


def new_root(p):
    p=p.resolve();R.require(p.is_relative_to(BASE) and not p.exists(),'017 new repository/out directory required')
    p.mkdir(parents=True);return p


def pin(path,inputs,expected=None):
    digest=C.sha(path);R.require(expected is None or digest==expected,'017 immutable identity drift: '+str(path))
    inputs[str(path)]=digest


def inventory(work,record,inputs):
    R.require(record['complete'] and record['returncode']==0 and record['gpu_executed'] is True
              and record['accepted_timing'] is False,'017 old source not admitted')
    hashes=record['payload_sha256']
    R.require({str(p.relative_to(work)) for p in work.rglob('*') if p.is_file()}==set(hashes)|{'result.json'},'017 old inventory differs')
    for rel,digest in hashes.items():
        p=(work/rel).resolve();R.require(p.is_relative_to(work.resolve()),'017 unsafe old payload path');pin(p,inputs,digest)


def prepare_inputs(cell,depth):
    inputs=inputs_now();proofs={};refs=F.reference_inputs(K.Case(cell,'hwrt'),inputs)
    p022=RESULTS/'022-six-pt-ladders-raw-replay.json';pin(p022,inputs)
    row=next(x for x in R.read(p022)['rows'] if x['cell']==cell and x['transport']==f'T_B{depth}')
    R.require(row['classification']=='PASS' and row['selected_spp']==(256 if depth==2 else 1024),'017 old PT first pass differs')
    levels=[]
    for spp in SPP:
        old=next(x for x in row['levels'] if x['spp']==spp);work=ROOT/old['work'];receipt=work/'result.json'
        pin(receipt,inputs,old['result_sha256']);record=R.read(receipt);inventory(work,record,inputs)
        plan=ROOT/f'out/m001-{cell.lower()}-b{depth}-pixel-pt-n{spp}-plan.json'
        if (cell,depth,spp)==('H01',2,1):plan=ROOT/'out/m001-h01-b2-pt-n1-plan.json'
        pin(plan,inputs,old['plan_sha256']);inputs.update(R.read(plan)['input_sha256'])
        frames=R.read(work/'capture/frames.json')
        R.require((frames['family'],frames['vertices'],frames['spp'],frames['seed'],frames['width'],frames['height'],len(frames['frames']))
                  ==('pixel-pt',depth,spp,305419896,320,180,1),'017 old PT boundary differs')
        state=R.Q.L.read_state(work/'capture')
        R.require(state['sha256']==R.CAPTURE_SHA[cell],'017 old PT state differs')
        levels.append(dict(spp=spp,work=str(work),receipt_sha256=C.sha(receipt)))
    p096=RESULTS/'096-closest-primary-eight-controls-raw-replay.json';pin(p096,inputs)
    primary=next(x for x in R.read(p096)['rows'] if x['name']==cell.lower()+'-hwrt');work=Path(primary['work'])
    R.require(primary['report']['correctness_evidence_valid'] and primary['report']['classification']=='PASS','017 primary correctness not admitted')
    pin(work/'result.json',inputs,primary['report']['result_sha256']);record=R.read(work/'result.json');inventory(work,record,inputs)
    plan=Path(primary['plan']);pin(plan,inputs,primary['plan_sha256']);inputs.update(R.read(plan)['input_sha256'])
    for d in ('2','8'):
        p=primary['report']['rows'][d]['primary']
        R.require(p['pass_'] and p['primitive_mismatches']==p['hit_presence_mismatches']==p['depth_bound_failures']==0,
                  '017 actual M001 primary equivalence unavailable')
    physical=R.Q.L.read_state(work/'capture')
    R.require(physical['sha256']==R.CAPTURE_SHA[cell],'017 geometry export and PT states differ')
    proofs.update(reference=refs[str(depth)],levels=levels,raw_pt_selected_spp=row['selected_spp'],primary_capture=str(work/'capture'))
    inputs.update(inputs_now());F.rehash(inputs)
    return inputs,proofs


def geometry(capture):
    state=R.Q.L.read_state(capture);gpu=np.fromfile(capture/'gpu/hits.bin',dtype=A.M.GPU_DTYPE)
    R.require(gpu.shape==(57600,) and np.isin(gpu['flag'],(0,1)).all(),'017 primary ABI differs')
    hit=gpu['flag']==1;metadata=state['meta'];order=np.argsort(metadata[:,0]);where=np.searchsorted(metadata[order,0],gpu['prim'][hit])
    R.require((where<len(metadata)).all(),'017 primary outside geometry');rows=order[where]
    R.require(np.array_equal(metadata[rows,0],gpu['prim'][hit]) and np.array_equal(metadata[rows,1],gpu['mat'][hit])
              and np.array_equal(metadata[rows,2],gpu['inst'][hit]),'017 hit metadata differs')
    x,y=np.meshgrid(np.arange(320,dtype=np.float32),np.arange(180,dtype=np.float32))
    nx=np.float32(2)*((x+np.float32(.5))/np.float32(320))-np.float32(1)
    ny=np.float32(1)-np.float32(2)*((y+np.float32(.5))/np.float32(180))
    direction=(state['camera_forward_far'][:3]+state['camera_right_tan_x'][:3]*(nx*state['camera_right_tan_x'][3])[...,None]
               +state['camera_up_tan_y'][:3]*(ny*state['camera_up_tan_y'][3])[...,None])
    direction/=np.linalg.norm(direction,axis=2,keepdims=True);direction=direction.reshape(-1,3)
    position=np.zeros((57600,3),dtype=np.float64)
    position[hit]=(state['camera_pos_near'][:3]+direction[hit]*gpu['t'][hit,None]).astype(np.float64)
    normal=np.zeros_like(position);normal[hit]=gpu['n'][hit].astype(float)
    normal[hit]/=np.linalg.norm(normal[hit],axis=1,keepdims=True)
    flip=hit & ((normal*direction).sum(axis=1)>0);normal[flip]*=-1
    diagonal=float(np.linalg.norm(state['verts'].max(axis=(0,1))-state['verts'].min(axis=(0,1))))
    epsilon=1e-5*max(1.,diagonal)
    return position.reshape(180,320,3),normal.reshape(180,320,3),hit.reshape(180,320),gpu['mat'].reshape(180,320),epsilon


def save_arrays(path,**arrays):
    with path.open('xb') as handle:np.savez_compressed(handle,**arrays)


def score_images(direct,indirect,reference):
    values=dict(direct=direct,indirect=indirect,total=direct+indirect)
    components={name:S.metrics(values[name],reference[name]) for name in values}
    B.quality(components) # Defined/finite complete-image predicates, including losses.
    return components,{name:values[name]-reference[name] for name in values}


def reconstruct_target(cell,depth,out):
    for path in OWN:
        blob=subprocess.check_output(['git','show',G.head()+':'+str(path.relative_to(ROOT))],cwd=ROOT)
        R.require(hashlib.sha256(blob).hexdigest()==C.sha(path),'Commit017implementation before reconstruction')
    out=new_root(out);record=dict(schema='m001-geometry-filter-cpu-target/1',cell=cell,depth=depth,complete=False,valid=False,
                                  source_commit=G.head(),gpu_executed=False,new_render_paths=0,new_reference_paths=0,accepted_timing=False)
    try:
        target=(cell,depth);R.require(target in TARGETS,'017 target unregistered')
        for c,d in TARGETS[:TARGETS.index(target)]:
            previous=R.read(BASE/f'm001-geometry-filter-{c.lower()}-b{d}-terminal-audit-v1/result.json')
            R.require(previous['complete'] and previous['valid'],'017 previous independent terminal audit missing/invalid')
        gate=R.read(PREPARATION);R.require(gate['complete'] and gate['actual_new_contract_tests']==16,'017 CPU preparation missing')
        F.rehash(gate['input_sha256']);R.quiet();R.require(shutil.disk_usage(out).free>=16*1024**3,'017 requires16GiB free')
        inputs,proofs=prepare_inputs(cell,depth);pin(PREPARATION,inputs)
        plan=dict(schema='m001-geometry-filter-cpu-plan/1',cell=cell,depth=depth,source_commit=G.head(),input_sha256=inputs,
                  proof=proofs,stages=list(B.STRIDES),spp=list(SPP),gpu_executed=False)
        G.write(out/'plan.json',plan);G.write(out/'started.json',dict(plan_sha256=C.sha(out/'plan.json'),cpu_only=True))
        pos,normal,hit,material,epsilon=geometry(Path(proofs['primary_capture']))
        masks=B.geometry_masks(pos,normal,hit,material,epsilon)
        save_arrays(out/'geometry.npz',position=pos,normal=normal,hit=hit,material=material,epsilon=np.array(epsilon))
        save_arrays(out/'geometry-masks.npz',masks=masks)
        # Only now read indirect reference intensity, after immutable masks exist.
        refdir=Path(proofs['reference']['directory']);q=R.read(refdir/'qualification.json');spp=q['levels'][-1]['spp']
        mean=np.mean([R.Q.L.read_sidecar(refdir/f'o.n{spp}.s{i}.f64')['mean'] for i in range(4)],axis=0)
        reference={name:mean[...,R.Q.L.COMPONENTS.index(name),:]@S.LUMA for name in ('direct','indirect','total')}
        bias_stages=B.reconstruct(reference['indirect'],masks);bias,errors=score_images(reference['direct'],bias_stages[-1],reference)
        save_arrays(out/'reference-bias-stages.npz',stages=bias_stages)
        save_arrays(out/'reference-bias-errors.npz',**errors)
        rows=[]
        for level in proofs['levels']:
            spp=level['spp'];capture=Path(level['work'])/'capture'
            direct=R.Q.L.read_pfm(capture/'direct.pfm');indirect=R.Q.L.read_pfm(capture/'indirect.pfm')
            for a in (direct,indirect):R.require(a.shape==(180,320,3) and np.isfinite(a).all() and (a>=0).all()
                                          and np.array_equal(a[...,0],a[...,1]) and np.array_equal(a[...,0],a[...,2]),'017 source is not valid grey RGB')
            direct=direct@S.LUMA;indirect=indirect@S.LUMA
            stages=B.reconstruct(indirect,masks);components,errors=score_images(direct,stages[-1],reference)
            save_arrays(out/f'n{spp}-stages.npz',stages=stages)
            save_arrays(out/f'n{spp}-errors.npz',**errors)
            rows.append(dict(spp=spp,components=components,classification='PASS' if B.quality(components) else 'QUALITY_FAIL',
                             original_pt_receipt_sha256=level['receipt_sha256'],scoring_exclusions=0))
        F.rehash(inputs)
        decision=B.decision(rows,bias)
        record.update(valid=True,complete=True,rows=rows,reference_bias_components=bias,decision=decision,
                      classification='CPU_RECONSTRUCTION_FEASIBILITY_PASS' if decision['pass_'] else 'REJECTED_NO_GPU',
                      hit_pixels=int(hit.sum()),geometry_epsilon=epsilon,accepted_taps_per_stage=masks.sum(axis=(1,2,3)).tolist(),
                      primary_geometry_source='013actual GPU t/normal/IDs; CPU reconstructed positions; no reference radiance',
                      sample_reduction_vs_original_selected_pt=proofs['raw_pt_selected_spp']/decision['first_passing_spp'] if decision['first_passing_spp'] else None,
                      reduction_is_speed_claim=False,plan_sha256=C.sha(out/'plan.json'))
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
    result=reconstruct_target(a.cell,a.depth,a.out)
    print(json.dumps({k:result[k] for k in ('cell','depth','complete','valid','classification','decision','error') if k in result},indent=2))
    sys.exit(0 if result['complete'] else 1)

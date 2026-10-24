"""020 one named native float32 CPU rehearsal; no GPU launch path here."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import surface_quadratic_cpu as Q
import surface_quadratic_material_abi as M

P=Q.P
R,C,F,G=Q.R,Q.C,Q.F,Q.G
ROOT,BASE,RESULTS=Q.ROOT,Q.BASE,Q.RESULTS
PREPARATION=RESULTS/'115-surface-quadratic-device-kernel-host-cpu-preparation.json'
PROTOCOL=M.PROTOCOL
TARGETS=Q.TARGETS
NAMES=('reference-bias','n1','n4','n16','n64')
OWN=M.OWN


def selected_spp(cell,depth):
    R.require((cell,depth) in TARGETS,'020 unregistered target')
    return 16 if (cell,depth)==('H01',2) else 64


def decision(cell,depth,rows):
    R.require([row['name'] for row in rows]==list(NAMES),'020 missing/reordered quality rows')
    selected=selected_spp(cell,depth);row=next(x for x in rows if x['name']==f'n{selected}')
    return dict(selected_spp=selected,selected_image_pass=bool(row['pass_']),reference_bias_pass=bool(rows[0]['pass_']),pass_=bool(row['pass_'] and rows[0]['pass_']))


def tag(cell,depth):
    R.require((cell,depth) in TARGETS,'020 unregistered target')
    return f'm001-q020-cpu-{cell.lower()}-b{depth}'


def previous_gate(cell,depth,base=BASE):
    R.require((cell,depth) in TARGETS,'020 unregistered target')
    inputs={}
    for c,d in TARGETS[:TARGETS.index((cell,depth))]:
        path=base/(tag(c,d)+'-terminal-audit-v1/result.json');r=R.read(path)
        R.require(r['complete'] is True and r['valid'] is True and r['source_commit']==G.head()
                  and r['decision']==decision(c,d,r['rows']) and r['decision']['pass_'] is True,'020 earlier CPU audit missing/invalid/failed; stop')
        pin_inventory(path,inputs)
        native=pin_inventory(Path(r['native_receipt']),inputs,r['native_receipt_sha256'])
        R.require(native['complete'] is True and native['valid'] is True,'020 prior native evidence incomplete')
    return inputs


def source_inputs():
    return {str(p):C.sha(p) for p in M.OWN}


def pin_inventory(receipt,inputs,expected=None):
    P.pin(receipt,inputs,expected);r=R.read(receipt);root=receipt.parent
    R.require({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}==set(r['payload_sha256'])|{'result.json'},'020 inventory differs')
    for name,digest in r['payload_sha256'].items():
        path=(root/name).resolve();R.require(path.is_relative_to(root.resolve()),'020 unsafe inventory path');P.pin(path,inputs,digest)
    return r


def prepare_inputs(cell,depth):
    inputs,proof=M.OLD.prepare_inputs(cell,depth)
    gate=M.build_gate(inputs)
    proof.update(executable=gate['executable'],shader=gate['shader'])
    capture=Path(proof['primary_capture'])
    raw=np.fromfile(capture/'gpu/hits.bin',dtype='<u4').reshape(57600,8)
    proof['material_abi']=M.canonical_metadata(raw,R.Q.L.read_state(capture)['meta'])
    inputs.update(source_inputs());F.rehash(inputs)
    return inputs,proof


def images(proof):
    refdir=Path(proof['reference']['directory']);q=R.read(refdir/'qualification.json');spp=q['levels'][-1]['spp']
    R.require(spp==16384,'020 original reference level differs')
    mean=np.mean([R.Q.L.read_sidecar(refdir/f'o.n{spp}.s{i}.f64')['mean'] for i in range(4)],axis=0)
    reference={name:mean[...,R.Q.L.COMPONENTS.index(name),:]@P.S.LUMA for name in ('direct','indirect','total')}
    sources=[reference['indirect']];direct=[reference['direct']]
    for level in proof['levels']:
        capture=Path(level['work'])/'capture'
        values={name:R.Q.L.read_pfm(capture/(name+'.pfm')) for name in ('direct','indirect')}
        for value in values.values():
            R.require(value.shape==(180,320,3) and np.isfinite(value).all() and (value>=0).all() and np.array_equal(value[...,0],value[...,1]) and np.array_equal(value[...,0],value[...,2]),'020 original PT image invalid')
        sources.append(values['indirect']@P.S.LUMA);direct.append(values['direct']@P.S.LUMA)
    return np.stack(sources).astype('<f4'),direct,reference


def input_arrays(proof):
    capture=Path(proof['primary_capture']);state=R.Q.L.read_state(capture)
    raw=np.fromfile(capture/'gpu/hits.bin',dtype='<u4').reshape(57600,8)
    with np.load(Path(proof['old_017_work'])/'geometry.npz',allow_pickle=False) as g:epsilon=float(g['epsilon'])
    camera=np.array([*state['camera_pos_near'],*state['camera_forward_far'],*state['camera_right_tan_x'],*state['camera_up_tan_y'],epsilon,5,320,180],dtype='<f4')
    R.require(camera.shape==(20,) and np.isfinite(camera).all() and np.isin(raw[:,7],(0,1)).all(),'020 input ABI differs')
    sources,_,_=images(proof)
    return dict(camera=camera,hits=raw,sources=sources)


def committed():
    M.committed()


def run_cpu(cell,depth,out):
    committed();prior=previous_gate(cell,depth);out=P.new_root(out)
    r=dict(schema='m001-q020-one-target-native-cpu-rehearsal/1',cell=cell,depth=depth,complete=False,valid=False,gpu_executed=False,new_render_paths=0,new_reference_paths=0,source_commit=G.head())
    try:
        R.quiet();R.require(shutil.disk_usage(out).free>=16*1024**3,'020 requires16GiB free')
        inputs,proof=prepare_inputs(cell,depth);inputs.update(prior);arrays=input_arrays(proof)
        inputdir=out/'input';inputdir.mkdir()
        for name,key in (('camera.f32','camera'),('hits.u32','hits'),('sources.f32','sources')):
            with (inputdir/name).open('xb') as f:arrays[key].tofile(f)
            P.pin(inputdir/name,inputs)
        command=[proof['executable'],'--cpu-check','--input',str(inputdir),'--out',str(out/'capture')]
        plan=dict(schema='m001-q020-cpu-plan/1',cell=cell,depth=depth,source_commit=G.head(),input_sha256=inputs,proof=proof,command=command,names=list(NAMES),gpu_executed=False,env=dict(VK_ICD_FILENAMES='/nonexistent/q020-native-cpu-rehearsal.json'))
        G.write(out/'plan.json',plan);G.write(out/'started.json',dict(plan_sha256=C.sha(out/'plan.json'),gpu_executed=False));launch=out/'launch';launch.mkdir()
        saved=os.environ.get('VK_ICD_FILENAMES');os.environ['VK_ICD_FILENAMES']=plan['env']['VK_ICD_FILENAMES']
        try:native=G.guarded(command,launch,120,180)
        finally:
            if saved is None:os.environ.pop('VK_ICD_FILENAMES',None)
            else:os.environ['VK_ICD_FILENAMES']=saved
        G.write(launch/'result.json',native)
        R.require(native['returncode']==0 and not native['timed_out'],'020 native CPU failure; stop/no identical retry')
        complete=R.read(out/'capture/complete.json');R.require(complete['complete'] and complete['gpu_initialized'] is False,'020 native CPU completion invalid')
        F.rehash(inputs)
        r.update(complete=True,valid=True,classification='CPU_EXECUTED_AUDIT_REQUIRED',plan_sha256=C.sha(out/'plan.json'),native_returncode=native['returncode'],native_timed_out=native['timed_out'])
    except Exception as error:r.update(error=repr(error),classification='STOP_NO_RETRY')
    finally:
        r['payload_sha256']={str(p.relative_to(out)):C.sha(p) for p in sorted(out.rglob('*')) if p.is_file()};G.write(out/'result.json',r)
    return r


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cell',choices=('H01','H02','H03'),required=True);ap.add_argument('--depth',type=int,choices=(2,8),required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    r=run_cpu(a.cell,a.depth,a.out.resolve());print(json.dumps({k:r[k] for k in ('cell','depth','complete','valid','classification','error') if k in r},indent=2));sys.exit(0 if r['complete'] else 1)

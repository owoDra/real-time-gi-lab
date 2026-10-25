#!/usr/bin/env python3
"""039 targeted frozen-output CPU diagnosis; never runs the full037 auditor."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import restir_gi_gpu_include_correction as H
G,C,M=H.G,H.C,H.G.M
ROOT,BASE=G.ROOT,G.BASE
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/039-frozen-gpu-endpoint-discrepancy-diagnosis.md'
OWN=[PROTOCOL,Path(__file__).resolve()]
OUT=BASE/'m001-restir039-endpoint-diagnosis-v1'
FROZEN=H.case_root('H01',2)


def committed():
    head=H.committed();subprocess.run(['git','merge-base','--is-ancestor','a8a5ee33',head],cwd=ROOT,check=True)
    for p in OWN:M.need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'commit039 before diagnosis')
    return head


def imports():
    pins={str(p):G.sha(p) for p in [*OWN,*H.OWN,*G.OWN,Path(C.__file__),Path(sys.executable)]}
    p=ROOT/'research/lanes/lane-m-gi-competitiveness/results/230-restir-gi-physical-gpu-first-condition-stop.json'
    M.need(subprocess.check_output(['git','show','97ab8eaa:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'exact038 outcome')
    pub=G.read(p);M.need(pub['classification']=='STOP_FLOAT32_ENDPOINT_DIRECTION_MISMATCH_NO_RETRY' and pub['fully_audited_seeds']==2,'preserve038 stop')
    native=G.read(FROZEN/'result.json');M.need(G.sha(FROZEN/'result.json')==pub['native_receipt_sha256'] and not native['all_pass'] and native['gpu_executed'],'exact stopped038 receipt')
    M.need(G.inventory(FROZEN)==native['payload_sha256'],'all original038 raw bytes')
    pins.update(native['input_sha256']);pins.update({str(FROZEN/k):v for k,v in native['payload_sha256'].items()});pins[str(FROZEN/'result.json')]=G.sha(FROZEN/'result.json');pins[str(p)]=G.sha(p)
    G.pin_archive(H.PREP/'result.json',pins);G.rehash(pins)
    return pins


def distribution(a):
    a=np.asarray(a);M.need(np.isfinite(a).all(),'finite diagnostic field')
    return dict(count=int(a.size),zero=int((a==0).sum()),minimum=float(np.min(a)),median=float(np.median(a)),p90=float(np.quantile(a,.9)),p99=float(np.quantile(a,.99)),maximum=float(np.max(a)))


def worker(root):
    wanted=dict(cpu=[1200,1200],address=[C.ADDRESS,C.ADDRESS],core=[0,0],sigxcpu_default=True,sigxcpu_unblocked=True)
    M.need(C.state()==wanted and not root.exists(),'actual inherited numeric envelope/exclusive output');root.mkdir()
    C.write(root/'effective-before.json',dict(pid=os.getpid(),effective=C.state()))
    pins=imports();r=dict(schema='m001-restir039-frozen-endpoint-diagnosis-worker/1',source_commit=committed(),complete=False,all_pass=False,pid=os.getpid(),effective_worker=wanted,input_sha256=pins,rows=[],full037_audit_reexecuted=False,gpu_executed=False,old038_still_stopped=True)
    try:
        data=(FROZEN/'capture/geometry-state.bin').read_bytes();geometry=np.frombuffer(data,np.dtype([('vertices','<f4',(3,3)),('metadata','<u4',4)]),offset=8)
        triangles=geometry['vertices'].astype(float);geometric=M.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]))
        for index,seed in enumerate(M.SEEDS):
            folder=FROZEN/'capture'/f'seed-{index}';w=np.fromfile(folder/'witnesses.bin',M.WITNESS).reshape(57600,2);c=np.fromfile(folder/'candidates.bin',M.CANDIDATE)
            original=np.fromfile(folder/'original.f32','<f4').reshape(57600,4);sdk=np.fromfile(folder/'sdk-output.f32','<f4').reshape(57600,6,4)
            for a,b in (('original.f32','observed.f32'),('original-hits.u32','observed-hits.u32'),('original-source.f32','observed-source.f32')):M.need((folder/a).read_bytes()==(folder/b).read_bytes(),'all four saved paired PT/primary/source bits')
            hit=M.bits(w['normal_kind'][:,1,3])==2;ids=np.flatnonzero(hit)
            origin=c['origin_pdf'][:,:3].astype(float);endpoint=c['endpoint_primitive'][:,:3].astype(float);ray=w['direction_direct'][:,1,:3].astype(float);t=w['origin_t'][:,1,3].astype(float)
            M.need(np.array_equal(c['origin_pdf'][hit,:3],w['origin_t'][hit,1,:3]) and np.array_equal(c['endpoint_primitive'][hit,:3],w['position_primitive'][hit,1,:3]),'actual origin and barycentric endpoint are the recorded candidate')
            distance=np.zeros(57600);distance[hit]=np.linalg.norm(endpoint[hit]-origin[hit],axis=1);M.need((distance[hit]>0).all(),'positive finite hit segments')
            direction=np.zeros((57600,3));direction[hit]=(endpoint[hit]-origin[hit])/distance[hit,None]
            error=np.zeros((57600,3));error[hit]=direction[hit]-ray[hit]
            failed_components=np.zeros((57600,3),bool);failed_components[hit]=~M.near(direction[hit],ray[hit]);failed=failed_components.any(axis=1)
            position_error=np.zeros((57600,3));position_error[hit]=endpoint[hit]-(origin+t[:,None]*ray)[hit]
            spacing=np.zeros((57600,3));spacing[hit]=np.abs(np.spacing(c['endpoint_primitive'][hit,:3])).astype(float)
            source_cos=c['direction_cosine'][:,3].astype(float);cosine=np.zeros(57600);cosine[hit]=np.maximum(0,(direction[hit]*c['normal_status'][hit,:3]).sum(axis=1))
            pdf=c['origin_pdf'][:,3].astype(float);recovered=np.zeros((57600,3));recovered[hit]=c['radiance_trial'][hit,:3]*cosine[hit,None]/(np.pi*pdf[hit,None])
            recovery_error=recovered-original[:,1,None];recovery_failed=~M.near(recovered,original[:,1,None]).all(axis=1)
            primitive=M.bits(w['position_primitive'][:,1,3]);primary=M.bits(w['position_primitive'][:,0,3]);normal_dot=np.zeros(57600);plane_gap=np.zeros(57600)
            normal_dot[hit]=(geometric[primary[hit]]*geometric[primitive[hit]]).sum(axis=1)
            plane_gap[hit]=np.abs(((triangles[primitive[hit],0]-triangles[primary[hit],0])*geometric[primary[hit]]).sum(axis=1))
            arrays=dict(secondary_hit=hit,generated_direction=ray,endpoint_direction=direction,direction_error=error,failed_components=failed_components,failed_pixels=failed,distance=distance,intersection_t=t,barycentric_endpoint_minus_ray_endpoint=position_error,local_float32_spacing=spacing,source_cosine=source_cos,geometric_cosine=cosine,source_pdf=pdf,recovered=recovered,recovery_error=recovery_error,recovery_failed=recovery_failed,primitive_normal_dot=normal_dot,primitive_plane_gap=plane_gap,saved_sdk_output=sdk)
            for k,a in arrays.items():M.need(np.isfinite(a).all(),'finite complete diagnostic array '+k)
            with (root/f'seed-{index}-full-endpoint-fields.npz').open('xb') as f:np.savez_compressed(f,**arrays)
            failures=[]
            for pixel in np.flatnonzero(failed):
                failures.append(dict(pixel=int(pixel),x=int(pixel%320),y=int(pixel//320),failed_components=failed_components[pixel].tolist(),origin=origin[pixel].tolist(),endpoint=endpoint[pixel].tolist(),generated_direction=ray[pixel].tolist(),endpoint_direction=direction[pixel].tolist(),direction_error=error[pixel].tolist(),intersection_t=float(t[pixel]),endpoint_distance=float(distance[pixel]),barycentric_endpoint_minus_ray_endpoint=position_error[pixel].tolist(),local_float32_spacing=spacing[pixel].tolist(),primary_primitive=int(primary[pixel]),secondary_primitive=int(primitive[pixel]),primitive_normal_dot=float(normal_dot[pixel]),primitive_plane_gap=float(plane_gap[pixel]),source_pdf=float(pdf[pixel]),source_cosine=float(source_cos[pixel]),geometric_cosine=float(cosine[pixel]),original_raw=original[pixel].tolist(),recovery_error=recovery_error[pixel].tolist(),recovery_failed=bool(recovery_failed[pixel]),sdk_output=sdk[pixel].tolist()))
            C.write(root/f'seed-{index}-every-failure.json',failures)
            row=dict(seed=seed,seed_index=index,paths=57600,secondary_hits=int(hit.sum()),paired_original_observed_bytes_exact=True,direction_failed_pixels=int(failed.sum()),direction_failed_components=int(failed_components.sum()),indirect_recovery_failed_pixels=int(recovery_failed.sum()),saved_unpacked_hemisphere_failures=int((sdk[hit,1,2]!=1).sum()),saved_unpacked_visibility_failures=int((sdk[hit,1,3]!=1).sum()),saved_packed_hemisphere_failures=int((sdk[hit,4,2]!=1).sum()),saved_packed_visibility_failures=int((sdk[hit,4,3]!=1).sum()),distance=distribution(distance[hit]),direction_absolute_error=distribution(np.abs(error[hit])),position_absolute_error=distribution(np.abs(position_error[hit])),recovery_absolute_error=distribution(np.abs(recovery_error)),failed_pixel_ids=np.flatnonzero(failed).tolist())
            r['rows'].append(row);print('039 seed',index,'direction_failed_pixels',row['direction_failed_pixels'],'recovery_failed_pixels',row['indirect_recovery_failed_pixels'],flush=True)
        G.rehash(pins);M.need(C.state()==wanted,'numeric envelope unchanged');r.update(complete=True,all_pass=True,classification='FROZEN_ENDPOINT_DIAGNOSIS_EXECUTED_NO_ADMISSION')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(root,r)


def run():
    head=committed();M.need(not OUT.exists() and shutil.disk_usage(BASE).free>=16*1024**3,'exclusive039/16GiB');pins=imports();OUT.mkdir()
    C.write(OUT/'inputs-before.json',dict(source_commit=head,input_sha256=pins))
    r=dict(schema='m001-restir039-supervised-frozen-diagnosis/1',source_commit=head,complete=False,all_pass=False,input_sha256=pins,gpu_executed=False,full037_audit_reexecuted=False,old038_still_stopped=True)
    try:
        r['effective_parent']=C.limits();command=[sys.executable,Path(__file__).resolve(),'worker']
        r['process']=G.guard(command,OUT,'numeric',1200,1800);w=G.read(OUT/'worker/result.json')
        M.need(w['pid']==r['process']['pid'] and w['complete'] and w['all_pass'] and len(w['rows'])==4,'actual complete targeted worker')
        G.rehash(pins);r.update(complete=True,all_pass=True,classification='FROZEN_ENDPOINT_DIAGNOSIS_EXECUTED_NO_ADMISSION',rows=w['rows'])
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(OUT,r)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['run','worker']);args=parser.parse_args()
    sys.exit(run() if args.mode=='run' else worker(OUT/'worker'))

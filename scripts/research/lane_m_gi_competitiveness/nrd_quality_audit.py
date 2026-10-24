"""026 all-frame witness/guide/HDR audit, fixed full physical frames0/1/63.
Field predicates derive from unchanged024 frame_audit; only physical coverage
is conditional and explicitly reported. All64 primary fields remain checked.
"""
import json
import math
from pathlib import Path
import resource
import numpy as np
import nrd_quality_build as B
import nrd_quality_process as P
import nrd_quality_overlay as O
import nrd_vulkan_audit as A
import closest_primary_metrics as M
import integrated_pt_audit as Q
INVALID=A.INVALID
data=A.data
closest=A.closest

def decision(rows):
 B.need(len(rows)==64 and [r['iteration'] for r in rows]==list(range(64)),'026 complete ordered quality frames')
 cold=rows[0]['quality_pass'];warm=all(r['quality_pass'] for r in rows[48:64])
 return dict(cold_pass=bool(cold),warm_pass=bool(warm),joint_pass=bool(cold and warm))

def sdk_audit(capture,cpu):
 reference=A.jsonl(cpu/'dispatches.jsonl')[:64];actual=A.jsonl(capture/'sdk-dispatches.jsonl');offset=0;total=0
 for iteration,frame in enumerate(reference):
  for j,d in enumerate(frame['dispatches']):
   x=actual[offset];offset+=1
   B.need(all(x[k]==d[k] for k in ('name','identifier','grid','constant_bytes','matches_previous','pipeline')) and x['iteration']==iteration and x['dispatch']==j and len(x['resources'])==len(d['resources']),'026 SDK command differs')
   for a,b in zip(x['resources'],d['resources']):
    image=5+b['pool_index'] if b['type']==31 else 11+b['pool_index'] if b['type']==30 else {6:0,1:1,2:2,0:3,18:4}.get(b['type'])
    B.need(image is not None and a['image']==image and all(a[k]==b[k] for k in ('descriptor_type','type','pool_index')) and a['sdk_reported_name']==b['name'],'026 actual SDK numeric/resource binding')
   raw=(capture/f'frame-{iteration}/constants/{j}.bin').read_bytes();B.need(raw==(cpu/'constants'/d['constant_file']).read_bytes(),'026 actual SDK constants');total+=len(raw)
 B.need(offset==len(actual)==651,'026 SDK dispatch coverage')
 for j in range(15):B.need((capture/f'pipelines/{j}.spv').read_bytes()==(cpu/f'pipelines/{j}.spv').read_bytes(),'026 pipeline differs from025 variant')
 return dict(dispatches=offset,constant_bytes=total,all_pipeline_bytes_exact_to025_variant_cpu=True)

def timestamp_audit(capture,images):
 device=B.read(capture/'device.json');bits=device['timestamp_valid_bits'];period=device['timestamp_period_ns'];B.need(1<=bits<=64 and math.isfinite(period) and period>0,'026 device timestamp facts');mask=(1<<bits)-1
 expected=[(0xffffffff,'initialize-images')]
 for i in range(64):
  expected.extend((i,f'producer-{p}') for p in range(0,57600,128));expected.append((i,'pack-guides'));expected.extend((i,f'sdk-{j}') for j in range(21 if i==0 else 10));expected.append((i,'compose-rgb'));expected.extend((i,'readback-'+x['name']) for x in images)
 events=A.jsonl(capture/'dispatches.jsonl');B.need(len(expected)==30540 and len(events)==61080,'026 unit journal coverage');active=[0.]*64;maximum=0.
 for j,((iteration,label),begin,end) in enumerate(zip(expected,events[::2],events[1::2])):
  B.need(begin==dict(event='begin',unit=j,iteration=iteration,label=label) and end['event']=='complete' and end['unit']==j,'026 unit sequence')
  B.need(all(type(end[k]) is int and 0<=end[k]<2**64 for k in ('timestamp_begin','timestamp_end')),'026 timestamp words')
  us=((end['timestamp_end']-end['timestamp_begin'])&mask)*period/1000;B.need(0<=us<=250000 and math.isclose(us,end['gpu_us_diagnostic'],rel_tol=1e-12,abs_tol=1e-12),'026 bounded unit timestamp');maximum=max(maximum,us)
  if iteration!=0xffffffff:active[iteration]+=us
 for i in range(64):
  e=B.read(capture/f'frame-{i}/envelope.json');c=B.read(capture/f'frame-{i}/complete.json');whole=((e['timestamp_end']-e['timestamp_begin'])&mask)*period/1000
  B.need(not e['accepted_timing'] and not c['accepted_timing'] and 0<=active[i]<=whole<=180e6 and math.isclose(whole,e['gpu_us_including_pauses_and_readbacks'],rel_tol=1e-12,abs_tol=1e-9) and math.isclose(active[i],c['active_gpu_us_diagnostic'],rel_tol=1e-12,abs_tol=1e-9),'026 actual frame envelope')
 return dict(completed_units=30540,maximum_gpu_unit_us_diagnostic=maximum,active_gpu_us_diagnostic=active,accepted_timing=False)

def reference(proof):
 directory=Path(proof['reference_directory']);q=B.read(directory/'qualification.json');B.need(q['classification']=='STATISTICALLY_ELIGIBLE' and q['levels'][-1]['spp']==16384,'026 exact admitted reference')
 B.rehash({str(directory/name):h for name,h in q['levels'][-1]['all_payload_sha256'].items()});means=np.mean([P.R.Q.L.read_sidecar(directory/f'o.n16384.s{i}.f64')['mean'] for i in range(4)],axis=0)
 luma=np.array([.2126,.7152,.0722]);return {name:means[...,P.R.Q.L.COMPONENTS.index(name),:]@luma for name in ('direct','indirect','total')}

def run(native,out):
 resource.setrlimit(resource.RLIMIT_CPU,(240,240));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
 head=B.committed();B.need(out.is_relative_to(B.BASE) and not out.exists(),'026 exclusive independent audit');n=B.read(native);B.need(n['complete'] and n['valid'],'026 valid native required');B.rehash({str(native.parent/p):h for p,h in n['payload_sha256'].items()});plan=B.read(native.parent/'plan.json');B.need(B.SHA(native.parent/'plan.json')==n['plan_sha256'],'026 plan identity');B.rehash(plan['input_sha256']);out.mkdir()
 r=dict(schema='m001-nrd026-independent-cold-warm-quality/1',cell=n['cell'],depth=n['depth'],spp=n['spp'],source_commit=head,complete=False,valid=False,gpu_executed=True,classification='IMPLEMENTATION_OR_RUNTIME_FAIL',native_receipt=str(native),native_receipt_sha256=B.SHA(native),accepted_timing=False,lane_m_complete=False)
 try:
  capture=native.parent/'capture';proof=plan['proof'];c=B.read(capture/'complete.json');B.need(c['complete'] and c['schema']=='m001-nrd026-native-quality-runtime/1' and c['frames']==64 and c['units']==30540 and c['spp']==n['spp'] and c['vertices']==n['depth'] and c['actual_ray_query_count_instrumented'] is False and all(c[k]==0 for k in ('input_images_uploaded','input_hits_uploaded','inter_stage_readbacks')),'026 actual complete boundary')
  device=B.read(capture/'device.json');B.need(device['vendor_id']==4098 and device['name']=='AMD Radeon 8060S Graphics (RADV STRIX_HALO)' and all(device[k] for k in ('storage_image_read_without_format_enabled','storage_image_write_without_format_enabled','storage_image_extended_formats_enabled')),'026 device identity/features')
  for name in ('geometry-state.bin','frame-state.bin'):B.need((capture/name).read_bytes()==(Path(proof['primary_capture'])/name).read_bytes(),'026 original physical state')
  vertices,metadata=A.geometry(capture/'geometry-state.bin');images=A.jsonl(capture/'images.jsonl');B.need(len(images)==15 and [x['index'] for x in images]==list(range(15)),'026 image coverage');ref=reference(proof);luma=np.array([.2126,.7152,.0722]);rows=[];frame_fields=[];last=None;differences=[];warm=[];active_history=[]
  for i in range(64):
   path=capture/f'frame-{i}';complete=B.read(path/'complete.json');B.need(complete['complete'] and complete['iteration']==i and complete['frame_index']==i and complete['clear']==(i==0) and complete['seed']==O.seed(i) and complete['sdk_dispatches']==(21 if i==0 else 10) and complete['units']==(488 if i==0 else 477),'026 seed/frame/lifecycle')
   for image in images:
    p=path/(image['name']+'.bin');B.need(image['format'] in A.FORMATS and image['texel_bytes']==A.FORMATS[image['format']][0] and image['optimal_features']&0xc003==0xc003 and p.stat().st_size==image['width']*image['height']*image['texel_bytes'] and np.isfinite(np.fromfile(p,dtype=A.FORMATS[image['format']][1])).all(),'026 complete finite pool')
   raw=data(path/'raw-pt.f32','<f4',(180,320,4));denoised=data(path/'denoised.bin','<f4',(180,320,4));final=data(path/'final-rgb.f32','<f4',(180,320,4));hits=data(path/'hits.u32',M.GPU_DTYPE,(57600,));active=hits['flag']==1;history=data(path/'permanent-2.bin','u1',(57600,));B.need(active.any() and np.all(history[active]==min(i+1,31)),'026 continuing active history length');active_history.append(dict(iteration=i,active_pixels=int(active.sum()),history_length=int(history[active][0])))
   fields=frame_audit(path,proof,vertices,metadata,out,i in (0,1,63));frame_fields.append(fields)
   if i==0:
    for j,name in enumerate(('direct','indirect','total')):B.need(np.array_equal(raw[...,j],P.R.Q.L.read_pfm(Path(proof['original_pt_directory'])/(name+'.pfm'))[...,0]),'026 original same-budget PT bytes')
    control={('H01',2):16,('H02',8):64,('H03',2):64}.get((n['cell'],n['depth']))
    if n['spp']==control:
     old=B.BASE/f"m001-nrd025-gpu-{n['cell'].lower()}-b{n['depth']}-v1/capture/frame-0"
     for p in old.rglob('*'):
      if p.is_file() and p.suffix in ('.bin','.f32','.u32'):B.need(p.read_bytes()==(path/p.relative_to(old)).read_bytes(),'026 required025 cold field equality')
   values=dict(direct=raw[...,0].astype(float),indirect=denoised[...,:3].astype(float)@luma,total=final[...,:3].astype(float)@luma);components,errors=Q.score(values,ref);np.savez(out/f'frame-{i}-hdr-errors.npz',**errors)
   direct=components['direct'];B.need(direct['nrmse']<=1e-4 and direct['whole_image_max_absolute']<=1e-5 and direct['gpu_zero_reference_positive']==0,'026 original direct/support correctness')
   rows.append(dict(iteration=i,seed=O.seed(i),quality_pass=M.quality(components)=='PASS',components=components,scoring_exclusions=0))
   if last is not None:differences.append(math.sqrt(math.fsum(float(x)*float(x) for x in (values['indirect']-last).ravel())/57600))
   last=values['indirect']
   if i>=48:warm.append(last)
   print('frame',i,'all fields checked; HDR',rows[-1]['quality_pass'],flush=True)
  d=decision(rows);np.savez(out/'warm-final16-and-consecutive-differences.npz',warm_mean=np.mean(warm,axis=0),warm_variance=np.var(warm,axis=0),consecutive_indirect_rms=np.array(differences))
  r.update(complete=True,valid=True,classification='JOINT_QUALITY_PASS' if d['joint_pass'] else 'QUALITY_FAIL',**d,rows=rows,all_frame_field_checks=frame_fields,active_history=active_history,full_secondary_intersection_frames=[0,1,63],secondary_samples_independently_intersected=sum(x['secondary_samples_independently_intersected'] for x in frame_fields),sdk=sdk_audit(capture,Path(proof['sdk_cpu_capture'])),ownership=A.ledger_report(B.read(capture/'allocation-ledger.json'),c,images),timestamps=timestamp_audit(capture,images),all_pixels_included=True,independent_fsum_metrics_verified=True,quality_evidence_valid=True)
 except Exception as e:r.update(complete=False,valid=False,classification='IMPLEMENTATION_OR_RUNTIME_FAIL',error=type(e).__name__+': '+str(e))
 B.rehash(plan['input_sha256']);B.rehash({str(native.parent/p):h for p,h in n['payload_sha256'].items()});r['payload_sha256']=B.inventory(out);B.write(out/'result.json',r);return r

def frame_audit(path,proof,vertices,metadata,work,intersect):
 spp=proof['spp'];n=57600;raw=data(path/'raw-pt.f32','<f4',(n,4));hits=data(path/'hits.u32',M.GPU_DTYPE,(n,));camera=data(path/'camera.f32','<f4',(20,));B.need((path/'camera.f32').read_bytes()==Path(proof['original_camera']).read_bytes(),'024 actual camera differs')
 oracle_raw=Path(proof['primary_oracle']).read_bytes();B.need(len(oracle_raw)==16+n*16,'024 original oracle shape');oracle=np.frombuffer(oracle_raw,dtype=M.ORACLE_DTYPE,offset=16);primary,maps=M.primary(hits,oracle,metadata,vertices,float(camera[7]));B.need(primary['pass_'] and primary['primitive_mismatches']==0,'024 primary presence/primitive/depth audit')
 active=hits['flag']==1;B.need(np.isfinite(raw).all() and (raw[:,:3]>=0).all() and np.array_equal(raw[:,2],(raw[:,0]+raw[:,1]).astype('<f4')) and (raw[:,3]==1).all(),'024 finite physical PT/support/sum');B.need(np.array_equal(data(path/'source.f32','<f4',(n,)),raw[:,1]),'024 raw indirect export')
 origins=data(path/'secondary-origins.f32','<f4',(n,4));rays=data(path/'secondary-rays.f32','<f4',(n,spp,4));ids=data(path/'secondary-primitives.u32','<u4',(n,spp));stats=data(path/'secondary-stats.f32','<f4',(n,2))
 B.need(np.isfinite(origins).all() and np.isfinite(rays).all() and (origins[:,3]==0).all() and (rays[~active]==0).all() and (ids[~active]==INVALID).all() and (origins[~active]==0).all(),'024 ray fields/miss convention')
 directions=rays[active,:,:3].astype(np.float64);B.need((np.abs(np.einsum('nsi,nsi->ns',directions,directions)-1)<=1e-4).all() and (np.einsum('nsi,ni->ns',directions,hits['n'][active].astype(np.float64))>=-1e-6).all(),'024 nonunit/out-of-lobe actual rays');B.need(((rays[:,:,3]>=0)&(rays[:,:,3]<=65504)).all() and (rays[:,:,3][active][ids[active]==INVALID]==65504).all(),'024 sample hit distances')
 total=np.zeros(n,dtype='<f4')
 for j in range(spp):total+=rays[:,j,3]
 B.need(np.array_equal(total,stats[:,0]) and np.array_equal((total/np.float32(spp)).astype('<f4'),stats[:,1]),'024 all sample-order sum/mean differs')
 np.savez(work/(path.name+'-primary-errors.npz'),**maps)
 maximum_distance_error=None
 if intersect:
  actual_origins=np.repeat(origins[active,:3],spp,axis=0);actual_directions=directions.reshape(-1,3);ignore=np.repeat(hits['prim'][active],spp);distance,expected=closest(actual_origins,actual_directions,ignore,vertices,metadata);gpu=ids[active].reshape(-1);B.need(np.array_equal(expected,gpu),'024 secondary hit-presence/canonical-primitive mismatch')
  expected_distance=np.minimum(distance,65504);observed=rays[active,:,3].reshape(-1).astype(np.float64);error=observed-expected_distance;ulp=np.spacing(observed.astype('<f4')).astype(np.float64);bound=np.maximum(2e-5,32*ulp);B.need((np.abs(error)<=bound).all(),'024 secondary physical distance error')
  full_error=np.zeros((n,spp),dtype='<f8');full_error[active]=error.reshape(-1,spp);full_expected=np.full((n,spp),INVALID,dtype='<u4');full_expected[active]=expected.reshape(-1,spp)
  np.savez(work/(path.name+'-physical-rays.npz'),secondary_distance_error=full_error,secondary_expected_primitive=full_expected,**maps)
  maximum_distance_error=float(np.abs(error).max(initial=0))
 B.need((data(path/'input-errors.u32','<u4',(n,))==0).all(),'024 pre-sanitization input errors')
 noisy=data(path/'noisy-diffuse.bin','<f4',(n,4));B.need(np.array_equal(noisy[:,:3],np.repeat(raw[:,1,None],3,axis=1)) and np.array_equal(noisy[:,3],stats[:,1]),'024 actual official radiance/distance packing')
 normal=np.where(active[:,None],hits['n'],np.array([0,0,1],dtype='<f4')).astype(np.float64);length=np.abs(normal).sum(axis=1);normal/=length[:,None];expected_normal=np.stack([.5+(normal[:,0]+normal[:,1])*.5,.5+(normal[:,1]-normal[:,0])*.5,(normal[:,2]>=0).astype(float)],axis=1)
 packed=data(path/'normal-roughness.bin','<u4',(n,));decoded=np.stack([(packed>>shift)&1023 for shift in (0,10,20)],axis=1);B.need((np.abs(decoded-expected_normal*1023)<=1.00001).all() and (packed>>30==0).all(),'024 actual UNORM normal/roughness/material packing')
 index=np.arange(n);nx=2*(index%320+.5)/320-1;ny=1-2*(index//320+.5)/180;view=camera[4:7].astype(np.float64)+nx[:,None]*camera[11]*camera[8:11]+ny[:,None]*camera[15]*camera[12:15];view/=np.linalg.norm(view,axis=1)[:,None];z=np.full(n,2*float(camera[7]));z[active]=hits['t'][active].astype(np.float64)*np.einsum('ni,i->n',view[active],camera[4:7].astype(np.float64));actual_z=data(path/'view-z.bin','<f4',(n,));z_bound=np.maximum(2e-5,16*np.spacing(z.astype('<f4')).astype(np.float64));B.need(np.isfinite(actual_z).all() and (actual_z>0).all() and (np.abs(actual_z.astype(float)-z)<=z_bound).all(),'024 actual positive viewZ')
 B.need((data(path/'motion.bin','<f4',(n,4))==0).all(),'024 static motion not zero')
 denoised=data(path/'denoised.bin','<f4',(n,4));final=data(path/'final-rgb.f32','<f4',(n,4));B.need(np.isfinite(denoised).all() and np.isfinite(final).all() and (denoised[:,:3]>=0).all() and np.array_equal(final[:,:3],(raw[:,0,None]+denoised[:,:3]).astype('<f4')) and (final[:,3]==1).all(),'024 actual RGB direct+denoised composition')
 return dict(raw_indirect_nonzero_pixels=int(np.count_nonzero(raw[:,1])),denoised_indirect_nonzero_pixels=int(np.count_nonzero(np.any(denoised[:,:3]>0,axis=1))),pixels=n,active_primary_pixels=int(active.sum()),nominal_viewport_spp_slots=n*spp,actual_first_secondary_samples_audited=int(active.sum())*spp,actual_ray_query_count_instrumented=False,primary=primary,secondary_samples_independently_intersected=int(active.sum())*spp if intersect else 0,secondary_primitive_mismatches=0 if intersect else None,maximum_secondary_distance_error=maximum_distance_error,all_secondary_distance_bounds_pass=True if intersect else None,all_sample_sum_mean_exact=True,all_actual_guide_contracts_pass=True,all_pixels_included=True,quality_admitted=False)

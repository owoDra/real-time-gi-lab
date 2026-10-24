"""028 all-frame witness/guide/HDR audit, fixed byte-verified reuse of026 physical frames0/1/63.
Field predicates derive from unchanged024 frame_audit; only physical coverage
is conditional and explicitly reported. All64 primary/input fields require actual new byte identity.
"""
import json
import math
from pathlib import Path
import resource
import numpy as np
import nrd_no_prepass_build as B
import nrd_no_prepass_process as P
import nrd_no_prepass_overlay as O
import nrd_vulkan_audit as A
import closest_primary_metrics as M
import integrated_pt_audit as Q
INVALID=A.INVALID
data=A.data
closest=A.closest

def decision(rows):
 B.need(len(rows)==64 and [r['iteration'] for r in rows]==list(range(64)),'028 complete ordered quality frames')
 cold=rows[0]['quality_pass'];warm=all(r['quality_pass'] for r in rows[48:64])
 return dict(cold_pass=bool(cold),warm_pass=bool(warm),joint_pass=bool(cold and warm))

def sdk_audit(capture,cpu):
 reference=A.jsonl(cpu/'dispatches.jsonl')[:64];actual=A.jsonl(capture/'sdk-dispatches.jsonl');offset=0;total=0
 for iteration,frame in enumerate(reference):
  for j,d in enumerate(frame['dispatches']):
   x=actual[offset];offset+=1
   B.need(all(x[k]==d[k] for k in ('name','identifier','grid','constant_bytes','matches_previous','pipeline')) and x['iteration']==iteration and x['dispatch']==j and len(x['resources'])==len(d['resources']),'028 SDK command differs')
   for a,b in zip(x['resources'],d['resources']):
    image=5+b['pool_index'] if b['type']==31 else 11+b['pool_index'] if b['type']==30 else {6:0,1:1,2:2,0:3,18:4}.get(b['type'])
    B.need(image is not None and a['image']==image and all(a[k]==b[k] for k in ('descriptor_type','type','pool_index')) and a['sdk_reported_name']==b['name'],'028 actual SDK numeric/resource binding')
   raw=(capture/f'frame-{iteration}/constants/{j}.bin').read_bytes();B.need(raw==(cpu/'constants'/d['constant_file']).read_bytes(),'028 actual SDK constants');total+=len(raw)
 B.need(offset==len(actual)==651,'028 SDK dispatch coverage')
 for j in range(15):B.need((capture/f'pipelines/{j}.spv').read_bytes()==(cpu/f'pipelines/{j}.spv').read_bytes(),'028 pipeline differs from025 variant')
 return dict(dispatches=offset,constant_bytes=total,all_pipeline_bytes_exact_to028_config_cpu=True)

def timestamp_audit(capture,images):
 device=B.read(capture/'device.json');bits=device['timestamp_valid_bits'];period=device['timestamp_period_ns'];B.need(1<=bits<=64 and math.isfinite(period) and period>0,'028 device timestamp facts');mask=(1<<bits)-1
 expected=[(0xffffffff,'initialize-images')]
 for i in range(64):
  expected.extend((i,f'producer-{p}') for p in range(0,57600,128));expected.append((i,'pack-guides'));expected.extend((i,f'sdk-{j}') for j in range(21 if i==0 else 10));expected.append((i,'compose-rgb'));expected.extend((i,'readback-'+x['name']) for x in images)
 events=A.jsonl(capture/'dispatches.jsonl');B.need(len(expected)==30540 and len(events)==61080,'028 unit journal coverage');active=[0.]*64;maximum=0.
 for j,((iteration,label),begin,end) in enumerate(zip(expected,events[::2],events[1::2])):
  B.need(begin==dict(event='begin',unit=j,iteration=iteration,label=label) and end['event']=='complete' and end['unit']==j,'028 unit sequence')
  B.need(all(type(end[k]) is int and 0<=end[k]<2**64 for k in ('timestamp_begin','timestamp_end')),'028 timestamp words')
  us=((end['timestamp_end']-end['timestamp_begin'])&mask)*period/1000;B.need(0<=us<=250000 and math.isclose(us,end['gpu_us_diagnostic'],rel_tol=1e-12,abs_tol=1e-12),'028 bounded unit timestamp');maximum=max(maximum,us)
  if iteration!=0xffffffff:active[iteration]+=us
 for i in range(64):
  e=B.read(capture/f'frame-{i}/envelope.json');c=B.read(capture/f'frame-{i}/complete.json');whole=((e['timestamp_end']-e['timestamp_begin'])&mask)*period/1000
  B.need(not e['accepted_timing'] and not c['accepted_timing'] and 0<=active[i]<=whole<=180e6 and math.isclose(whole,e['gpu_us_including_pauses_and_readbacks'],rel_tol=1e-12,abs_tol=1e-9) and math.isclose(active[i],c['active_gpu_us_diagnostic'],rel_tol=1e-12,abs_tol=1e-9),'028 actual frame envelope')
 return dict(completed_units=30540,maximum_gpu_unit_us_diagnostic=maximum,active_gpu_us_diagnostic=active,accepted_timing=False)

def reference(proof):
 directory=Path(proof['reference_directory']);q=B.read(directory/'qualification.json');B.need(q['classification']=='STATISTICALLY_ELIGIBLE' and q['levels'][-1]['spp']==16384,'028 exact admitted reference')
 B.rehash({str(directory/name):h for name,h in q['levels'][-1]['all_payload_sha256'].items()});means=np.mean([P.R.Q.L.read_sidecar(directory/f'o.n16384.s{i}.f64')['mean'] for i in range(4)],axis=0)
 luma=np.array([.2126,.7152,.0722]);return {name:means[...,P.R.Q.L.COMPONENTS.index(name),:]@luma for name in ('direct','indirect','total')}

def run(native,out):
 resource.setrlimit(resource.RLIMIT_CPU,(240,240));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
 head=B.committed();B.need(out.is_relative_to(B.BASE) and not out.exists(),'028 exclusive independent audit');n=B.read(native);B.need(n['complete'] and n['valid'],'028 valid native required');B.rehash({str(native.parent/p):h for p,h in n['payload_sha256'].items()});plan=B.read(native.parent/'plan.json');B.need(B.SHA(native.parent/'plan.json')==n['plan_sha256'],'028 plan identity');B.rehash(plan['input_sha256']);out.mkdir()
 r=dict(schema='m001-nrd028-independent-cold-warm-quality/1',cell=n['cell'],depth=n['depth'],spp=n['spp'],source_commit=head,complete=False,valid=False,gpu_executed=True,classification='IMPLEMENTATION_OR_RUNTIME_FAIL',native_receipt=str(native),native_receipt_sha256=B.SHA(native),accepted_timing=False,lane_m_complete=False)
 try:
  capture=native.parent/'capture';proof=plan['proof'];c=B.read(capture/'complete.json');B.need(c['complete'] and c['schema']=='m001-nrd028-native-quality-runtime/1' and c['frames']==64 and c['units']==30540 and c['spp']==n['spp'] and c['vertices']==n['depth'] and c['actual_ray_query_count_instrumented'] is False and all(c[k]==0 for k in ('input_images_uploaded','input_hits_uploaded','inter_stage_readbacks')),'028 actual complete boundary')
  device=B.read(capture/'device.json');B.need(device['vendor_id']==4098 and device['name']=='AMD Radeon 8060S Graphics (RADV STRIX_HALO)' and all(device[k] for k in ('storage_image_read_without_format_enabled','storage_image_write_without_format_enabled','storage_image_extended_formats_enabled')),'028 device identity/features')
  for name in ('geometry-state.bin','frame-state.bin'):B.need((capture/name).read_bytes()==(Path(proof['primary_capture'])/name).read_bytes(),'028 original physical state')
  images=A.jsonl(capture/'images.jsonl');B.need(len(images)==15 and [x['index'] for x in images]==list(range(15)),'028 image coverage');ref=reference(proof);luma=np.array([.2126,.7152,.0722]);rows=[];frame_fields=[];last=None;differences=[];warm=[];active_history=[]
  for i in range(64):
   path=capture/f'frame-{i}';complete=B.read(path/'complete.json');B.need(complete['complete'] and complete['iteration']==i and complete['frame_index']==i and complete['clear']==(i==0) and complete['seed']==O.seed(i) and complete['sdk_dispatches']==(21 if i==0 else 10) and complete['units']==(488 if i==0 else 477),'028 seed/frame/lifecycle')
   for image in images:
    p=path/(image['name']+'.bin');B.need(image['format'] in A.FORMATS and image['texel_bytes']==A.FORMATS[image['format']][0] and image['optimal_features']&0xc003==0xc003 and p.stat().st_size==image['width']*image['height']*image['texel_bytes'] and np.isfinite(np.fromfile(p,dtype=A.FORMATS[image['format']][1])).all(),'028 complete finite pool')
   raw=data(path/'raw-pt.f32','<f4',(180,320,4));denoised=data(path/'denoised.bin','<f4',(180,320,4));final=data(path/'final-rgb.f32','<f4',(180,320,4));hits=data(path/'hits.u32',M.GPU_DTYPE,(57600,));active=hits['flag']==1;history=data(path/'permanent-2.bin','u1',(57600,));B.need(active.any() and np.all(history[active]==min(i+1,31)),'028 continuing active history length');active_history.append(dict(iteration=i,active_pixels=int(active.sum()),history_length=int(history[active][0])))
   fields=reused_frame(path,proof,i);frame_fields.append(fields)
   B.need(np.isfinite(denoised).all() and np.isfinite(final).all() and (denoised[...,:3]>=0).all() and np.array_equal(final[...,:3],(raw[...,0,None]+denoised[...,:3]).astype('<f4')) and (final[...,3]==1).all(),'028 actual new RGB composition')
   values=dict(direct=raw[...,0].astype(float),indirect=denoised[...,:3].astype(float)@luma,total=final[...,:3].astype(float)@luma);components,errors=Q.score(values,ref);np.savez(out/f'frame-{i}-hdr-errors.npz',**errors)
   direct=components['direct'];B.need(direct['nrmse']<=1e-4 and direct['whole_image_max_absolute']<=1e-5 and direct['gpu_zero_reference_positive']==0,'028 original direct/support correctness')
   rows.append(dict(iteration=i,seed=O.seed(i),quality_pass=M.quality(components)=='PASS',components=components,scoring_exclusions=0))
   if last is not None:differences.append(math.sqrt(math.fsum(float(x)*float(x) for x in (values['indirect']-last).ravel())/57600))
   last=values['indirect']
   if i>=48:warm.append(last)
   print('frame',i,'all fields checked; HDR',rows[-1]['quality_pass'],flush=True)
  d=decision(rows);np.savez(out/'warm-final16-and-consecutive-differences.npz',warm_mean=np.mean(warm,axis=0),warm_variance=np.var(warm,axis=0),consecutive_indirect_rms=np.array(differences))
  r.update(complete=True,valid=True,classification='JOINT_QUALITY_PASS' if d['joint_pass'] else 'QUALITY_FAIL',**d,rows=rows,all_frame_field_checks=frame_fields,active_history=active_history,full_secondary_intersection_frames=[],reused026_full_secondary_intersection_frames=[0,1,63],secondary_samples_independently_intersected=0,reused026_secondary_samples_independently_intersected=sum(x['reused_secondary_samples_independently_intersected'] for x in frame_fields),sdk=sdk_audit(capture,Path(proof['sdk_cpu_capture'])),ownership=A.ledger_report(B.read(capture/'allocation-ledger.json'),c,images),timestamps=timestamp_audit(capture,images),all_pixels_included=True,independent_fsum_metrics_verified=True,quality_evidence_valid=True)
 except Exception as e:r.update(complete=False,valid=False,classification='IMPLEMENTATION_OR_RUNTIME_FAIL',error=type(e).__name__+': '+str(e))
 B.rehash(plan['input_sha256']);B.rehash({str(native.parent/p):h for p,h in n['payload_sha256'].items()});r['payload_sha256']=B.inventory(out);B.write(out/'result.json',r);return r

# Producer/input whitelist covers every witness consumed by026's physical and
# guide predicates; denoiser output/pools deliberately receive new checks.
INPUT_FIELDS=('params.bin','camera.f32','source.f32','secondary-stats.f32',
 'noisy-diffuse.bin','hits.u32','raw-pt.f32','secondary-rays.f32',
 'secondary-primitives.u32','view-z.bin','input-errors.u32','motion.bin',
 'normal-roughness.bin','secondary-origins.f32')

def exact_field(new,old,expected):
 B.need(new.is_file() and old.is_file() and not new.is_symlink() and not old.is_symlink(),'028 missing/aliased actual input field')
 B.need(B.SHA(old)==expected and B.SHA(new)==expected,'028 actual producer/input differs from certified026 byte witness')
 return new.stat().st_size

def reused_frame(path,proof,i):
 parent=proof['reused026'];native=Path(parent['native_receipt']);audit=Path(parent['audit_receipt']);n=B.read(native);r=B.read(audit);old=native.parent/'capture'/f'frame-{i}'
 count=0
 for name in INPUT_FIELDS:count+=exact_field(path/name,old/name,n['payload_sha256'][f'capture/frame-{i}/{name}'])
 row=r['all_frame_field_checks'][i]
 B.need(row['primary']['pass_'] and row['all_sample_sum_mean_exact'] and row['all_actual_guide_contracts_pass'],'028 reused026 field predicates')
 return dict(iteration=i,actual_input_fields_byte_exact=len(INPUT_FIELDS),actual_input_bytes_byte_exact=count,reused026_audit_receipt=str(audit),reused026_primary=row['primary'],reused026_field_predicates=True,reused_secondary_samples_independently_intersected=row['secondary_samples_independently_intersected'],new_secondary_intersections=0)

"""024 independent full actual-ray, guide, SDK, history and ownership audit."""
import json
import math
from pathlib import Path
import struct
import numpy as np
import build_nrd_vulkan as B
import closest_primary_metrics as M
INVALID=np.uint32(0xffffffff)
FORMATS={9:(1,'u1',1),37:(4,'u1',4),64:(4,'<u4',1),97:(8,'<f2',4),100:(4,'<f4',1),109:(16,'<f4',4)}

def jsonl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def data(p,dtype,shape):
 a=np.fromfile(p,dtype=dtype);B.need(a.size==math.prod(shape),'024 field shape: '+str(p));return a.reshape(shape)

def geometry(p):
 raw=p.read_bytes();version,count=struct.unpack_from('<II',raw);B.need(version==1 and count>0 and len(raw)==8+52*count,'024 original geometry shape');a=np.frombuffer(raw,dtype=np.dtype([('v','<f4',(3,3)),('meta','<u4',(4,))]),offset=8);return a['v'].astype(np.float64),a['meta'].copy()

def closest(origins,directions,ignore,vertices,metadata):
 """Double Moller-Trumbore over actual saved rays, no RNG/new samples."""
 count=len(directions);distance=np.full(count,np.inf);primitive=np.full(count,INVALID,dtype=np.uint32)
 B.need(origins.shape==directions.shape==(count,3) and ignore.shape==(count,),'024 actual ray oracle shape')
 for offset in range(0,count,4096):
  o=origins[offset:offset+4096].astype(np.float64);d=directions[offset:offset+4096].astype(np.float64);self_id=ignore[offset:offset+4096];best=np.full(len(o),np.inf);ids=np.full(len(o),INVALID,dtype=np.uint32)
  for v,meta in zip(vertices,metadata):
   edge1=v[1]-v[0];edge2=v[2]-v[0];p=np.cross(d,edge2);det=np.einsum('ij,j->i',p,edge1);inv=np.divide(1.,det,out=np.zeros_like(det),where=det!=0);tvec=o-v[0];u=np.einsum('ij,ij->i',tvec,p)*inv;q=np.cross(tvec,edge1);vv=np.einsum('ij,ij->i',d,q)*inv;t=np.einsum('ij,j->i',q,edge2)*inv
   valid=(det!=0)&(u>=0)&(vv>=0)&(u+vv<=1)&(t>=0)&(t<=1e30)&(self_id!=meta[0])&(t<best);best[valid]=t[valid];ids[valid]=meta[0]
  distance[offset:offset+len(o)]=best;primitive[offset:offset+len(o)]=ids
 return distance,primitive

def ledger_report(ledger,complete,images):
 B.need(ledger['schema']=='n010-allocation-lifetimes/1' and ledger['device_contexts']==1,'024 ledger identity');live={};allocated=[];amount=peak=0
 for j,e in enumerate(ledger['events']):
  B.need(e['sequence']==j and e['device_context']==1 and type(e['bytes']) is int and 0<e['bytes']<=8*1024**3,'024 allocation event range')
  key=e['allocation_id']
  if e['action']=='allocate':B.need(key not in live and key==len(allocated)+1,'024 duplicate/unordered allocation');live[key]=e;allocated.append(e);amount+=e['bytes']
  else:
   B.need(e['action']=='free' and key in live,'024 unmatched allocation free');old=live.pop(key);B.need(all(e[k]==old[k] for k in ('bytes','memory_type','requested_properties','buffer_usage','device_context')),'024 free identity');amount-=e['bytes']
  B.need(e['live_bytes']==amount and 0<=amount<=8*1024**3,'024 live-byte accounting/cap');peak=max(peak,amount)
 B.need(not live and amount==0 and ledger['teardown_zero'] and ledger['live_bytes_at_teardown']==0 and peak==ledger['true_peak_owned_bytes']==complete['aggregate_reserved_peak'] and complete['aggregate_reserved_at_teardown']==0,'024 peak/teardown')
 image_allocations=[e for e in allocated if e['buffer_usage']==15 and e['requested_properties']==1]
 B.need(len(image_allocations)==len(images)==15 and all(e['bytes']==image['owned_allocation_bytes'] and e['memory_type']==image['memory_type'] for e,image in zip(image_allocations,images)),'024 complete image ownership')
 mapped=[e for e in allocated if e['requested_properties']==6 and e['buffer_usage'] in (2,16,32)]
 expected=[32]*7+[16,16,32,16,2,32];B.need(len(mapped)>=13 and [e['buffer_usage'] for e in mapped[-13:]]==expected,'024 full mapped pipeline ownership')
 B.need(any(e['buffer_usage']&0x100000 for e in allocated) and any(e['buffer_usage']&0x20000 for e in allocated),'024 AS/vertex/scratch ownership absent')
 return dict(true_peak_owned_bytes=peak,allocation_pairs=len(allocated),allocation_events=len(ledger['events']),image_allocations=len(image_allocations),teardown_zero=True,driver_private_and_cpu_memory_excluded=True)

def sequence(images):
 rows=[(0xffffffff,'initialize-images')]
 for iteration,count in enumerate((21,10,21)):
  rows.extend((iteration,f'producer-{p}') for p in range(0,57600,128));rows.append((iteration,'pack-guides'));rows.extend((iteration,f'sdk-{j}') for j in range(count));rows.append((iteration,'compose-rgb'));rows.extend((iteration,'readback-'+x['name']) for x in images)
 return rows

def timestamps(events,device,frames,images):
 bits=device['timestamp_valid_bits'];period=device['timestamp_period_ns'];B.need(type(bits) is int and 1<=bits<=64 and math.isfinite(period) and period>0,'024 timestamp facts');mask=(1<<bits)-1
 expected=sequence(images);B.need(len(expected)==1454 and len(events)==2*len(expected),'024 incomplete/extra dispatch journal');active=[0.,0.,0.];maximum=0.
 for j,((iteration,label),begin,end) in enumerate(zip(expected,events[::2],events[1::2])):
  B.need(begin==dict(event='begin',unit=j,iteration=iteration,label=label) and end['event']=='complete' and end['unit']==j,'024 unit order/completion')
  for k in ('timestamp_begin','timestamp_end'):B.need(type(end[k]) is int and 0<=end[k]<2**64,'024 timestamp word')
  us=((end['timestamp_end']-end['timestamp_begin'])&mask)*period/1000;B.need(0<=us<=250000 and math.isclose(us,end['gpu_us_diagnostic'],rel_tol=1e-12,abs_tol=1e-12),'024 per-unit duration');maximum=max(maximum,us)
  if iteration!=0xffffffff:active[iteration]+=us
 for j,path in enumerate(frames):
  e=B.read(path/'envelope.json');whole=((e['timestamp_end']-e['timestamp_begin'])&mask)*period/1000;c=B.read(path/'complete.json');B.need(e['accepted_timing'] is False and c['accepted_timing'] is False and 0<=active[j]<=whole<=180e6 and math.isclose(whole,e['gpu_us_including_pauses_and_readbacks'],rel_tol=1e-12,abs_tol=1e-9) and math.isclose(active[j],c['active_gpu_us_diagnostic'],rel_tol=1e-12,abs_tol=1e-9),'024 complete envelope/active sum')
 return dict(completed_units=len(expected),maximum_gpu_unit_us_diagnostic=maximum,active_gpu_us_diagnostic=active,accepted_timing=False)

def sdk_report(capture,cpu):
 frames=[json.loads(s) for s in (cpu/'dispatches.jsonl').read_text().splitlines()];actual=jsonl(capture/'sdk-dispatches.jsonl');offset=0;constants=0
 for iteration,reference in enumerate((frames[0],frames[1],frames[64])):
  for j,d in enumerate(reference['dispatches']):
   x=actual[offset];offset+=1
   B.need(all(x[k]==d[k] for k in ('name','identifier','grid','constant_bytes','matches_previous')) and x['pipeline']==d['pipeline'] and x['iteration']==iteration and x['dispatch']==j,'024 actual SDK schedule differs from023')
   B.need(len(x['resources'])==len(d['resources']),'024 resource list size')
   for a,b in zip(x['resources'],d['resources']):
    B.need(all(a[k]==b[k] for k in ('descriptor_type','type','pool_index')) and a['sdk_reported_name']==b['name'],'024 numeric resources differ')
    expected=5+b['pool_index'] if b['type']==31 else 11+b['pool_index'] if b['type']==30 else {6:0,1:1,2:2,0:3,18:4}.get(b['type'])
    B.need(expected is not None and a['image']==expected,'024 resource-image binding mismatch')
   p=capture/f'frame-{iteration}/constants/{j}.bin';B.need(p.read_bytes()==(cpu/'constants'/d['constant_file']).read_bytes(),'024 actual SDK constants differ from023');constants+=p.stat().st_size
 B.need(offset==len(actual)==52,'024 all SDK commands')
 for j,p in enumerate(B.read(cpu/'instance.json')['pipelines']):B.need((capture/'pipelines'/f'{j}.spv').read_bytes()==(cpu/'pipelines'/f'{j}.spv').read_bytes(),'024 SDK embedded shader changed')
 return dict(dispatches=offset,constant_bytes=constants,pipeline_bytes_exact_to023=True,all_numeric_resource_bindings_match=True)

def frame_audit(path,proof,vertices,metadata,work):
 spp=proof['spp'];n=57600;raw=data(path/'raw-pt.f32','<f4',(n,4));hits=data(path/'hits.u32',M.GPU_DTYPE,(n,));camera=data(path/'camera.f32','<f4',(20,));B.need((path/'camera.f32').read_bytes()==Path(proof['original_camera']).read_bytes(),'024 actual camera differs')
 oracle_raw=Path(proof['primary_oracle']).read_bytes();B.need(len(oracle_raw)==16+n*16,'024 original oracle shape');oracle=np.frombuffer(oracle_raw,dtype=M.ORACLE_DTYPE,offset=16);primary,maps=M.primary(hits,oracle,metadata,vertices,float(camera[7]));B.need(primary['pass_'] and primary['primitive_mismatches']==0,'024 primary presence/primitive/depth audit')
 active=hits['flag']==1;B.need(np.isfinite(raw).all() and (raw[:,:3]>=0).all() and np.array_equal(raw[:,2],(raw[:,0]+raw[:,1]).astype('<f4')) and (raw[:,3]==1).all() and np.any(raw[:,1]>0),'024 finite physical PT/support/sum');B.need(np.array_equal(data(path/'source.f32','<f4',(n,)),raw[:,1]),'024 raw indirect export')
 origins=data(path/'secondary-origins.f32','<f4',(n,4));rays=data(path/'secondary-rays.f32','<f4',(n,spp,4));ids=data(path/'secondary-primitives.u32','<u4',(n,spp));stats=data(path/'secondary-stats.f32','<f4',(n,2))
 B.need(np.isfinite(origins).all() and np.isfinite(rays).all() and (origins[:,3]==0).all() and (rays[~active]==0).all() and (ids[~active]==INVALID).all() and (origins[~active]==0).all(),'024 ray fields/miss convention')
 directions=rays[active,:,:3].astype(np.float64);B.need((np.abs(np.einsum('nsi,nsi->ns',directions,directions)-1)<=1e-4).all() and (np.einsum('nsi,ni->ns',directions,hits['n'][active].astype(np.float64))>=-1e-6).all(),'024 nonunit/out-of-lobe actual rays');B.need(((rays[:,:,3]>=0)&(rays[:,:,3]<=65504)).all() and (rays[:,:,3][active][ids[active]==INVALID]==65504).all(),'024 sample hit distances')
 total=np.zeros(n,dtype='<f4')
 for j in range(spp):total+=rays[:,j,3]
 B.need(np.array_equal(total,stats[:,0]) and np.array_equal((total/np.float32(spp)).astype('<f4'),stats[:,1]),'024 all sample-order sum/mean differs')
 actual_origins=np.repeat(origins[active,:3],spp,axis=0);actual_directions=directions.reshape(-1,3);ignore=np.repeat(hits['prim'][active],spp);distance,expected=closest(actual_origins,actual_directions,ignore,vertices,metadata);gpu=ids[active].reshape(-1);B.need(np.array_equal(expected,gpu),'024 secondary hit-presence/canonical-primitive mismatch')
 expected_distance=np.minimum(distance,65504);observed=rays[active,:,3].reshape(-1).astype(np.float64);error=observed-expected_distance;ulp=np.spacing(observed.astype('<f4')).astype(np.float64);bound=np.maximum(2e-5,32*ulp);B.need((np.abs(error)<=bound).all(),'024 secondary physical distance error')
 full_error=np.zeros((n,spp),dtype='<f8');full_error[active]=error.reshape(-1,spp);full_expected=np.full((n,spp),INVALID,dtype='<u4');full_expected[active]=expected.reshape(-1,spp)
 np.savez(work/(path.name+'-physical-rays.npz'),secondary_distance_error=full_error,secondary_expected_primitive=full_expected,**maps)
 B.need((data(path/'input-errors.u32','<u4',(n,))==0).all(),'024 pre-sanitization input errors')
 noisy=data(path/'noisy-diffuse.bin','<f4',(n,4));B.need(np.array_equal(noisy[:,:3],np.repeat(raw[:,1,None],3,axis=1)) and np.array_equal(noisy[:,3],stats[:,1]),'024 actual official radiance/distance packing')
 normal=np.where(active[:,None],hits['n'],np.array([0,0,1],dtype='<f4')).astype(np.float64);length=np.abs(normal).sum(axis=1);normal/=length[:,None];expected_normal=np.stack([.5+(normal[:,0]+normal[:,1])*.5,.5+(normal[:,1]-normal[:,0])*.5,(normal[:,2]>=0).astype(float)],axis=1)
 packed=data(path/'normal-roughness.bin','<u4',(n,));decoded=np.stack([(packed>>shift)&1023 for shift in (0,10,20)],axis=1);B.need((np.abs(decoded-expected_normal*1023)<=1.00001).all() and (packed>>30==0).all(),'024 actual UNORM normal/roughness/material packing')
 index=np.arange(n);nx=2*(index%320+.5)/320-1;ny=1-2*(index//320+.5)/180;view=camera[4:7].astype(np.float64)+nx[:,None]*camera[11]*camera[8:11]+ny[:,None]*camera[15]*camera[12:15];view/=np.linalg.norm(view,axis=1)[:,None];z=np.full(n,2*float(camera[7]));z[active]=hits['t'][active].astype(np.float64)*np.einsum('ni,i->n',view[active],camera[4:7].astype(np.float64));actual_z=data(path/'view-z.bin','<f4',(n,));z_bound=np.maximum(2e-5,16*np.spacing(z.astype('<f4')).astype(np.float64));B.need(np.isfinite(actual_z).all() and (actual_z>0).all() and (np.abs(actual_z.astype(float)-z)<=z_bound).all(),'024 actual positive viewZ')
 B.need((data(path/'motion.bin','<f4',(n,4))==0).all(),'024 static motion not zero')
 denoised=data(path/'denoised.bin','<f4',(n,4));final=data(path/'final-rgb.f32','<f4',(n,4));B.need(np.isfinite(denoised).all() and np.isfinite(final).all() and (denoised[:,:3]>=0).all() and np.any(denoised[:,:3]>0) and np.array_equal(final[:,:3],(raw[:,0,None]+denoised[:,:3]).astype('<f4')) and (final[:,3]==1).all(),'024 actual RGB direct+denoised composition')
 return dict(pixels=n,active_primary_pixels=int(active.sum()),nominal_viewport_spp_slots=n*spp,actual_first_secondary_samples_audited=int(active.sum())*spp,actual_ray_query_count_instrumented=False,primary=primary,secondary_primitive_mismatches=0,maximum_secondary_distance_error=float(np.abs(error).max(initial=0)),all_secondary_distance_bounds_pass=True,all_sample_sum_mean_exact=True,all_actual_guide_contracts_pass=True,all_pixels_included=True,quality_admitted=False)

def run(native,out):
 B.committed();B.need(out.is_relative_to(B.BASE) and not out.exists(),'024 exclusive independent audit output');r=B.read(native);B.need(r['complete'] and r['valid'] and r['classification']=='GPU_EXECUTED_AUDIT_REQUIRED','024 valid terminal native required');B.rehash({str(native.parent/p):h for p,h in r['payload_sha256'].items()});plan=B.read(native.parent/'plan.json');B.need(r['plan_sha256']==B.SHA(native.parent/'plan.json'),'024 native-plan identity');B.rehash(plan['input_sha256']);out.mkdir();capture=native.parent/'capture';report=dict(schema='m001-nrd024-independent-native-control/1',cell=r['cell'],depth=r['depth'],source_commit=r['source_commit'],native_receipt=str(native),native_receipt_sha256=B.SHA(native),complete=False,all_pass=False,gpu_executed=True,classification='IMPLEMENTATION_OR_RUNTIME_FAIL',accepted_timing=False,quality_admitted=False,lane_m_complete=False)
 try:
  complete=B.read(capture/'complete.json');B.need(complete['complete'] and complete['gpu_initialized'] and complete['frames']==3 and complete['units']==1454 and complete['actual_ray_query_count_instrumented'] is False and all(complete[k]==0 for k in ('input_images_uploaded','input_hits_uploaded','inter_stage_readbacks')),'024 native claims')
  device=B.read(capture/'device.json');B.need(device['vendor_id']==4098 and device['name']=='AMD Radeon 8060S Graphics (RADV STRIX_HALO)' and device['storage_image_read_without_format_enabled'] and device['storage_image_write_without_format_enabled'] and device['storage_image_extended_formats_enabled'],'024 actual device/features')
  images=jsonl(capture/'images.jsonl');B.need(len(images)==15 and [x['index'] for x in images]==list(range(15)),'024 image inventory')
  vertices,metadata=geometry(capture/'geometry-state.bin');frames=[capture/f'frame-{j}' for j in range(3)]
  for name in ('geometry-state.bin','frame-state.bin'):B.need((capture/name).read_bytes()==(Path(plan['proof']['primary_capture'])/name).read_bytes(),'024 original physical state differs')
  for j,path in enumerate(frames):
   c=B.read(path/'complete.json');B.need(c['complete'] and c['iteration']==j and c['frame_index']==(1 if j==1 else 0) and c['clear']==(j!=1) and c['seed']==(2654435769 if j==1 else 305419896) and c['units']==(477 if j==1 else 488),'024 actual clear/continue/reset sequence')
   for image in images:
    B.need(image['format'] in FORMATS and image['texel_bytes']==FORMATS[image['format']][0] and image['optimal_features']&0xc003==0xc003,'024 texture format features');size=image['width']*image['height']*image['texel_bytes'];p=path/(image['name']+'.bin');B.need(p.stat().st_size==size,'024 full texture field');dtype=FORMATS[image['format']][1];B.need(np.isfinite(np.fromfile(p,dtype=dtype)).all(),'024 nonfinite owned pool')
   B.need(np.any(np.fromfile(path/'permanent-0.bin',dtype='<f2')>0) and np.any(np.fromfile(path/'permanent-2.bin',dtype='u1')>0),'024 empty radiance/history state')
  for path in (frames[0],frames[2]):B.need((path/'raw-pt.f32').read_bytes()==Path(plan['proof']['original_raw']).read_bytes(),'024 raw PT differs from original022same budget')
  reset_files=[p for p in frames[0].rglob('*') if p.is_file() and p.suffix in ('.bin','.f32','.u32')];B.need(all(p.read_bytes()==(frames[2]/p.relative_to(frames[0])).read_bytes() for p in reset_files),'024 reset-to-cold fields/constants not exact')
  B.need((frames[1]/'permanent-2.bin').read_bytes()!=(frames[0]/'permanent-2.bin').read_bytes(),'024 continuing history length did not update')
  audits=[frame_audit(path,plan['proof'],vertices,metadata,out) for path in frames[:2]]
  report.update(complete=True,all_pass=True,classification='NATIVE_NRD_CONTROL_PASS',frames=3,actual_physical_ray_audits=audits,reset_fields_bit_exact=len(reset_files),reset_ray_audit_reused_from_first_frame=True,sdk=sdk_report(capture,Path(plan['proof']['sdk_cpu_capture'])),ownership=ledger_report(B.read(capture/'allocation-ledger.json'),complete,images),timestamps=timestamps(jsonl(capture/'dispatches.jsonl'),device,frames,images),device=device)
 except Exception as e:report['error']=type(e).__name__+': '+str(e)
 B.rehash(plan['input_sha256']);B.rehash({str(native.parent/p):h for p,h in r['payload_sha256'].items()});report['payload_sha256']=B.inventory(out)
 with (out/'result.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 return report

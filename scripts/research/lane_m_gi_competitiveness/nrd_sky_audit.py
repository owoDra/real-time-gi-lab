"""025 strict original runtime gates plus all-frame isolated intervention audit."""
import json
from pathlib import Path
import shutil
import numpy as np
import nrd_vulkan_audit as A
import nrd_sky_build as B

def intervention_arrays(old,new,sky):
    B.need(old.shape==new.shape==sky.shape and old.dtype==new.dtype==np.dtype('u1') and sky.dtype==np.dtype('bool'),'025 material/mask shape')
    B.need(np.array_equal(old[~sky],new[~sky]) and not np.any(new[sky]),'025 intervention changed non-sky material or sky material not zero')
    return dict(changed_bytes=int(np.count_nonzero(old!=new)),sky_bytes=int(sky.sum()),outside_sky_changed_bytes=int(np.count_nonzero((old!=new)&~sky)))

def intervention(capture,out):
    native=B.BASE/'m001-nrd024-gpu-h01-b2-v1/result.json';r=B.read(native)
    diag=B.BASE/'m001-nrd024-h01-b2-failure-cpu-diagnostics-v1/result.json';d=B.read(diag)
    B.rehash({str(native.parent/p):h for p,h in r['payload_sha256'].items()});B.rehash({str(diag.parent/p):h for p,h in d['payload_sha256'].items()})
    B.need(r['complete'] and r['valid'] and d['all_preregistered_remaining_cpu_diagnostics_pass'] and not d['native_control_admitted'],'025 original failed control and diagnostics required')
    rows=[]
    for j in range(3):
        old=native.parent/f'capture/frame-{j}';new=capture/f'frame-{j}'
        files=sorted(str(p.relative_to(old)) for p in old.rglob('*') if p.is_file() and p.suffix in ('.bin','.f32','.u32'))
        B.need(files==sorted(str(p.relative_to(new)) for p in new.rglob('*') if p.is_file() and p.suffix in ('.bin','.f32','.u32')),'025 intervention field coverage')
        exact=[]
        for name in files:
            if name=='permanent-4.bin':continue
            B.need((old/name).read_bytes()==(new/name).read_bytes(),'025 intervention field changed: '+str(j)+'/'+name);exact.append(name)
        tiles=np.fromfile(old/'transient-2.bin',dtype='u1').reshape(12,20);sky=np.repeat(np.repeat(tiles!=0,16,axis=0),16,axis=1)[:180,:320]
        a=np.fromfile(old/'permanent-4.bin',dtype='u1').reshape(180,320);b=np.fromfile(new/'permanent-4.bin',dtype='u1').reshape(180,320)
        diff=intervention_arrays(a,b,sky)
        np.savez(out/f'intervention-frame-{j}.npz',original_material=a,new_material=b,fully_sky_tile_pixels=sky,difference=a!=b)
        rows.append(dict(iteration=j,exact_other_binary_fields=exact,**diff))
    copied=[]
    for j in (0,1):
        p=diag.parent/f'frame-{j}-physical-rays.npz';shutil.copyfile(p,out/p.name);copied.append(dict(path=p.name,reused_from=str(p),sha256=B.SHA(p)))
    return dict(all_three_frames_pass=True,frames=rows,original_failed_native_receipt=str(native),original_failed_native_receipt_sha256=B.SHA(native),original_cpu_diagnostics_receipt=str(diag),original_cpu_diagnostics_receipt_sha256=B.SHA(diag),reused_physical_error_maps=copied),d

def run(native,out):
    head=B.committed();B.need(out.is_relative_to(B.BASE) and not out.exists(),'025 exclusive independent audit output');r=B.read(native)
    B.need(r['complete'] and r['valid'] and r['classification']=='GPU_EXECUTED_AUDIT_REQUIRED','025 valid terminal capture required')
    B.rehash({str(native.parent/p):h for p,h in r['payload_sha256'].items()});plan=B.read(native.parent/'plan.json');B.need(r['plan_sha256']==B.SHA(native.parent/'plan.json') and plan['schema']=='m001-nrd025-one-native-plan/1','025 plan identity');B.rehash(plan['input_sha256']);out.mkdir()
    report=dict(schema='m001-nrd025-independent-sky-variant-control/1',cell=r['cell'],depth=r['depth'],source_commit=head,native_receipt=str(native),native_receipt_sha256=B.SHA(native),complete=False,all_pass=False,gpu_executed=True,classification='IMPLEMENTATION_OR_RUNTIME_FAIL',private_source_variant='SKY_WORLD_POSITION_MATERIAL_ZERO_BEFORE_EARLY_OUT',accepted_timing=False,quality_admitted=False,lane_m_complete=False)
    try:
        capture=native.parent/'capture';complete=B.read(capture/'complete.json');device=B.read(capture/'device.json');images=A.jsonl(capture/'images.jsonl');frames=[capture/f'frame-{j}' for j in range(3)]
        B.need(complete['complete'] and complete['gpu_initialized'] and complete['frames']==3 and complete['units']==1454 and complete['actual_ray_query_count_instrumented'] is False and all(complete[k]==0 for k in ('input_images_uploaded','input_hits_uploaded','inter_stage_readbacks')),'025 actual runtime boundary')
        B.need(device['vendor_id']==4098 and device['name']=='AMD Radeon 8060S Graphics (RADV STRIX_HALO)' and all(device[k] for k in ('storage_image_read_without_format_enabled','storage_image_write_without_format_enabled','storage_image_extended_formats_enabled')),'025 original device/features')
        B.need(len(images)==15 and [x['index'] for x in images]==list(range(15)),'025 image inventory')
        for name in ('geometry-state.bin','frame-state.bin'):B.need((capture/name).read_bytes()==(Path(plan['proof']['primary_capture'])/name).read_bytes(),'025 original physical state')
        for j,path in enumerate(frames):
            c=B.read(path/'complete.json');B.need(c['complete'] and c['iteration']==j and c['frame_index']==(1 if j==1 else 0) and c['clear']==(j!=1) and c['seed']==(2654435769 if j==1 else 305419896) and c['units']==(477 if j==1 else 488),'025 actual clear/continue/reset sequence')
            for image in images:
                B.need(image['format'] in A.FORMATS and image['texel_bytes']==A.FORMATS[image['format']][0] and image['optimal_features']&0xc003==0xc003,'025 format/feature contract')
                p=path/(image['name']+'.bin');B.need(p.stat().st_size==image['width']*image['height']*image['texel_bytes'] and np.isfinite(np.fromfile(p,dtype=A.FORMATS[image['format']][1])).all(),'025 complete finite pool')
            B.need(np.any(np.fromfile(path/'permanent-0.bin',dtype='<f2')>0) and np.any(np.fromfile(path/'permanent-2.bin',dtype='u1')>0),'025 nonzero radiance/history')
        for path in (frames[0],frames[2]):B.need((path/'raw-pt.f32').read_bytes()==Path(plan['proof']['original_raw']).read_bytes(),'025 original022 PT bit equality')
        reset_files=[p for p in frames[0].rglob('*') if p.is_file() and p.suffix in ('.bin','.f32','.u32')]
        B.need(all(p.read_bytes()==(frames[2]/p.relative_to(frames[0])).read_bytes() for p in reset_files),'025 reset-to-cold fields/constants not exact')
        B.need((frames[1]/'permanent-2.bin').read_bytes()!=(frames[0]/'permanent-2.bin').read_bytes(),'025 continuing history did not update')
        if r['cell']=='H01':
            try:proof,old=intervention(capture,out)
            except Exception as e:report['classification']='ISOLATED_INTERVENTION_FAIL';raise
            report['intervention']=proof
            checks={x['name']:x['result'] for x in old['diagnostic_cpu_checks']}
            audits=[dict(checks[f'frame-{j}-full-physical-rays-guides'],reused_from_receipt=proof['original_cpu_diagnostics_receipt'],reused_only_after_all_input_bytes_equal=True) for j in (0,1)]
        else:
            vertices,metadata=A.geometry(capture/'geometry-state.bin');audits=[A.frame_audit(path,plan['proof'],vertices,metadata,out) for path in frames[:2]]
        report.update(complete=True,all_pass=True,classification='NATIVE_NRD_CONTROL_PASS',frames=3,actual_physical_ray_audits=audits,reset_fields_bit_exact=len(reset_files),reset_ray_audit_reused_from_first_frame=True,sdk=A.sdk_report(capture,Path(plan['proof']['sdk_cpu_capture'])),ownership=A.ledger_report(B.read(capture/'allocation-ledger.json'),complete,images),timestamps=A.timestamps(A.jsonl(capture/'dispatches.jsonl'),device,frames,images),device=device)
    except Exception as e:
        report['error']=type(e).__name__+': '+str(e);report['complete']=False;report['all_pass']=False
    B.rehash(plan['input_sha256']);B.rehash({str(native.parent/p):h for p,h in r['payload_sha256'].items()});report['payload_sha256']=B.inventory(out)
    with (out/'result.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    return report

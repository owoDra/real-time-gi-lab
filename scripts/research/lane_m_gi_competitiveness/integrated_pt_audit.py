"""022 independent all-pixel physical, numerical, ownership and image audit."""
import argparse
import json
import math
import os
from pathlib import Path
import struct
import numpy as np
import integrated_pt_process as T
import surface_quadratic_gpu_audit as A
import closest_primary_metrics as M
R,C,F,G,P=T.R,T.C,T.F,T.G,T.P


def capture_arrays(root):
    shapes={'hits':('<u4',(57600,8)),'camera':('<f4',(20,)),'geometry':('<f4',(180,320,8)),'coefficients':('<f4',(3,25,180,320)),'maps':('<u4',(6,180,320)),'sources':('<f4',(180,320)),'stages':('<f4',(3,180,320)),'unclipped':('<f4',(3,180,320)),'raw-pt':('<f4',(180,320,4)),'final':('<f4',(180,320,4))}
    return {name:np.fromfile(root/(name+('.u32' if dtype=='<u4' else '.f32')),dtype=dtype).reshape(shape) for name,(dtype,shape) in shapes.items()}


def score(values,reference):
    errors={name:values[name].astype(float)-reference[name] for name in ('direct','indirect','total')};components={name:P.S.metrics(values[name],reference[name]) for name in errors}
    for name,error in errors.items():
        ref=reference[name];rmse=math.sqrt(math.fsum(float(x)*float(x) for x in error.ravel())/57600);rms=math.sqrt(math.fsum(float(x)*float(x) for x in ref.ravel())/57600);bias=math.fsum(map(float,error.ravel()))/math.fsum(map(float,ref.ravel()))
        R.require(math.isclose(rmse/rms,components[name]['nrmse'],rel_tol=1e-11,abs_tol=1e-30) and math.isclose(bias,components[name]['signed_sum_bias'],rel_tol=1e-11,abs_tol=1e-30),'022 independent fsum metrics differ')
    return components,errors


def audit_gpu(cell,depth,out):
    T.committed();root=T.BASE/(T.tag(cell,depth)+'-v1');out=P.new_root(out)
    r=dict(schema='m001-integrated022-terminal-audit/1',cell=cell,depth=depth,source_commit=G.head(),complete=False,valid=False,gpu_executed=True,classification='STOP_NO_RETRY',accepted_timing=False)
    try:
        receipt=R.read(root/'result.json');plan=R.read(root/'plan.json');launch=R.read(root/'launch/result.json');T.T.pin_inventory(root/'result.json',{})
        R.require(receipt['complete'] and receipt['valid'] and launch['returncode']==0 and not launch['timed_out'],'022 native invalid/partial; no retry')
        R.require(receipt['source_commit']==plan['source_commit']==G.head() and receipt['plan_sha256']==C.sha(root/'plan.json')==R.read(root/'started.json')['plan_sha256'],'022 source/plan/start differs')
        inputs,proof=T.prepare_inputs(cell,depth);inputs.update(T.previous_gate(cell,depth));R.require(inputs==plan['input_sha256'] and proof==plan['proof'] and launch['command']==plan['command']==T.command(proof,root,depth),'022 independent plan/command/input identity differs')
        F.rehash(plan['input_sha256']);native=T.validate_native(root/'capture',plan);data=capture_arrays(root/'capture');arrays=dict(camera=data['camera'],hits=data['hits'])
        state=R.Q.L.read_state(Path(proof['primary_capture']));T.T.M.canonical_metadata(data['hits'],state['meta'])
        camera=T.T.input_arrays(proof)['camera'];camera[17]=1;R.require(np.array_equal(camera,arrays['camera']),'022 original camera/epsilon differs')
        refdir=Path(proof['reference']['directory']);raw=(refdir/'o.n16384.hits').read_bytes();R.require(raw[:8]==b'N008HIT\0' and struct.unpack_from('<II',raw,8)==(320,180) and len(raw)==16+16*57600,'022 reference primary ABI')
        oracle=np.frombuffer(raw,dtype=M.ORACLE_DTYPE,offset=16);gpu=data['hits'].reshape(-1).view(M.GPU_DTYPE)
        primary,primary_errors=M.primary(gpu,oracle,state['meta'],state['verts'],float(state['camera_forward_far'][3]));P.save_arrays(out/'primary-errors.npz',**primary_errors)
        R.require(primary['pass_'] and primary['primitive_mismatches']==0,'022 generated primary mismatch')
        original=next(row for row in proof['levels'] if row['spp']==proof['selected_spp']);raw_pt=data['raw-pt'];final=data['final']
        R.require(np.isfinite(raw_pt).all() and np.isfinite(final).all() and (raw_pt>=0).all() and (final>=0).all() and (raw_pt[...,3]==1).all() and (final[...,3]==1).all(),'022 nonfinite/negative/unwritten physical image')
        raw_checks={};raw_errors={}
        for j,name in enumerate(('direct','indirect','total')):
            old=R.Q.L.read_pfm(Path(original['work'])/'capture'/(name+'.pfm'))[...,0];error=raw_pt[...,j].astype(float)-old;bound=2e-4*max(float(np.abs(old).max()),1e-20);maximum=float(np.abs(error).max());raw_errors[name]=error;raw_checks[name]=dict(maximum_absolute_error=maximum,bound=bound,pass_=maximum<=bound)
        P.save_arrays(out/'raw-pt-original-errors.npz',**raw_errors);R.require(all(x['pass_'] for x in raw_checks.values()),'022 new physical PT differs from original numerical bound')
        R.require(np.array_equal(raw_pt[...,1],data['sources']) and np.array_equal(final[...,0],raw_pt[...,0]) and np.array_equal(final[...,1],data['stages'][-1]) and np.array_equal(final[...,2],np.add(final[...,0],final[...,1],dtype=np.float32)),'022 generated source/direct/indirect/composition differs')
        for prefix,pixels in (('raw-',raw_pt),('',final)):
            for j,name in enumerate(('direct','indirect','total')):
                image=R.Q.L.read_pfm(root/'capture'/(prefix+name+'.pfm'));R.require(image.shape==(180,320,3) and all(np.array_equal(image[...,c],pixels[...,j]) for c in range(3)),'022 PFM export differs')
        geometry=data['geometry'];hit=data['hits'][:,7].reshape(180,320)==1;geometry_report=A.geometry_health(geometry,arrays);masks=A.masks_float32(geometry,data['hits'],data['camera'][16]);coeff_report=A.coefficient_health(data['coefficients'],data['maps'],masks,hit)
        # Unchanged five-image native scalar ABI receives only audit copies of
        # the NEW image/geometry. This path cannot feed the completed GPU run.
        si=out/'shadow-input';si.mkdir();shadow_camera=camera.copy();shadow_camera[17]=5;shadow_camera.tofile(si/'camera.f32');data['hits'].tofile(si/'hits.u32');np.repeat(data['sources'][None],5,axis=0).tofile(si/'sources.f32');geometry.tofile(si/'geometry.f32')
        sl=out/'shadow-launch';sl.mkdir();cmd=[proof['executable'],'--cpu-replay-geometry','--input',str(si),'--out',str(out/'shadow-capture')]
        saved={k:os.environ.get(k) for k in ('VK_ICD_FILENAMES','VK_DRIVER_FILES')}
        try:
            for k in saved:os.environ[k]='/m001-022-unusable-audit-icd.json'
            shadow_run=G.guarded(cmd,sl,120,180)
        finally:
            for k,value in saved.items():
                if value is None:os.environ.pop(k,None)
                else:os.environ[k]=value
        G.write(sl/'result.json',shadow_run);R.require(shadow_run['returncode']==0 and not shadow_run['timed_out'] and R.read(out/'shadow-capture/complete.json')['gpu_initialized'] is False,'022 unchanged CPU oracle failed')
        shadow=A.capture_arrays(out/'shadow-capture');R.require(np.array_equal(data['maps'],shadow['maps']) and np.allclose(data['coefficients'],shadow['coefficients'],rtol=2e-4,atol=2e-5),'022 complete native scalar fit/maps bound')
        P.save_arrays(out/'native-kernel-errors.npz',geometry=data['geometry']-shadow['geometry'],coefficients=data['coefficients']-shadow['coefficients'],stages=data['stages']-shadow['stages'][0],unclipped=data['unclipped']-shadow['unclipped'][0])
        ids=np.flatnonzero(hit);points=np.unique(np.concatenate((np.linspace(0,57599,64,dtype=np.int64),ids[((2*np.arange(64)+1)*len(ids))//128])));svd=[];selectors=[];max_coeff=0.;rank_differences=0;hit_vectors=0;miss_vectors=0
        for stage,stride in enumerate((1,2,4)):
            vectors=[];packed=[]
            for index in points:
                y,x=int(index//320),int(index%320);expected,model,bits,selected=A.svd_coefficients(geometry[...,:3],geometry[...,4:7],hit,masks[stage],y,x,stride);actual=data['coefficients'][stage,:,y,x]
                R.require(np.allclose(actual,expected,rtol=2e-4,atol=2e-5),'022 independent SVD coefficients bound');max_coeff=max(max_coeff,float(np.abs(actual-expected).max()));value=model|(bits<<8)|(selected<<16);rank_differences+=int(value!=int(data['maps'][3+stage,y,x]));packed.append(value);vectors.append(expected)
                if hit[y,x]:hit_vectors+=1
                else:miss_vectors+=1
            svd.append(vectors);selectors.append(packed)
        svd=np.array(svd);P.save_arrays(out/'independent-svd.npz',points=points,coefficients=svd,selector=np.array(selectors,dtype=np.uint32))
        _,_,reference=T.T.images(proof);rows=[];clipping=[];max_svd=0.;max_full=0.;scalar_outputs=0
        for name in ('new-noisy','reference-bias'):
            previous=data['sources'] if name=='new-noisy' else reference['indirect'].astype(np.float32);stage_raw=[];stage_clipped=[];stage_errors=[];clip=[]
            for stage,stride in enumerate((1,2,4)):
                expected=A.replay_stage(previous,data['coefficients'][stage],stride);raw=data['unclipped'][stage] if name=='new-noisy' else expected;clipped=data['stages'][stage] if name=='new-noisy' else np.maximum(raw,np.float32(0));scale=max(float(np.abs(previous).max()),1e-20)
                R.require(np.isfinite(raw).all() and np.isfinite(clipped).all() and (clipped>=0).all() and np.array_equal(clipped,np.maximum(raw,np.float32(0))),'022 clipping/nonfinite image')
                R.require(np.allclose(raw,expected,rtol=2e-5,atol=2e-7*scale) and np.allclose(clipped,np.maximum(expected,0),rtol=2e-5,atol=2e-7*scale),'022 complete ordered float32 stage bound');max_full=max(max_full,float(np.abs(raw.astype(float)-expected).max())/scale)
                if name=='new-noisy':R.require(np.allclose(raw,shadow['unclipped'][0,stage],rtol=2e-5,atol=2e-7*scale) and np.allclose(clipped,shadow['stages'][0,stage],rtol=2e-5,atol=2e-7*scale),'022 complete unchanged scalar stage bound')
                for index,coefficient in zip(points,svd[stage]):
                    y,x=int(index//320),int(index%320);terms=[]
                    for weight,(dy,dx,_) in zip(coefficient,P.B.OFFSETS):
                        yy,xx=y+dy*stride,x+dx*stride;terms.append(float(weight)*float(previous[yy,xx]) if 0<=yy<180 and 0<=xx<320 else 0.)
                    value=math.fsum(terms);error=max(abs(float(raw[y,x])-value),abs(float(clipped[y,x])-max(value,0)));R.require(error<=2e-4*scale,'022 independent SVD stage bound');max_svd=max(max_svd,error/scale);scalar_outputs+=2
                negative=raw<0;clip.append(dict(negative_pixels=int(negative.sum()),minimum=float(raw.min()),negative_absolute_energy=math.fsum(float(-x) for x in raw[negative])));stage_raw.append(raw);stage_clipped.append(clipped);stage_errors.append(raw-expected);previous=clipped
            values={key:final[...,j].astype(float) for j,key in enumerate(('direct','indirect','total'))} if name=='new-noisy' else dict(direct=reference['direct'],indirect=previous.astype(float),total=reference['direct']+previous.astype(float))
            components,errors=score(values,reference);P.save_arrays(out/(name+'-errors.npz'),**errors);P.save_arrays(out/(name+'-stages.npz'),unclipped=np.array(stage_raw),stages=np.array(stage_clipped),ordered_float32_error=np.array(stage_errors));rows.append(dict(name=name,components=components,pass_=P.B.quality(components),scoring_exclusions=0));clipping.append(dict(name=name,stages=clip))
        direct=rows[0]['components']['direct'];R.require(direct['nrmse']<=1e-4 and direct['whole_image_max_absolute']<=1e-5 and direct['gpu_zero_reference_positive']==0,'022 physical direct/support gate failed')
        decision=dict(selected_image_pass=bool(rows[0]['pass_']),reference_bias_pass=bool(rows[1]['pass_']),pass_=bool(rows[0]['pass_'] and rows[1]['pass_']));F.rehash(plan['input_sha256']);T.T.pin_inventory(root/'result.json',{})
        r.update(complete=True,valid=True,classification='INTEGRATED_TARGET_PASS' if decision['pass_'] else 'INTEGRATED_TARGET_QUALITY_FAIL',decision=decision,rows=rows,clipping=clipping,primary=primary,raw_pt_original_numerical_checks=raw_checks,geometry=geometry_report,coefficients=coeff_report,native_device_report=native,independent_fsum_metrics_verified=True,independent_svd_hit_coefficient_vectors=hit_vectors,analytic_miss_coefficient_vectors=miss_vectors,scalar_preclip_clipped_pixel_comparisons=scalar_outputs,maximum_svd_coefficient_absolute_error=max_coeff,maximum_svd_stage_scaled_error=max_svd,maximum_full_stage_scaled_error=max_full,double_svd_rank_model_differences=rank_differences,native_receipt=str(root/'result.json'),native_receipt_sha256=C.sha(root/'result.json'),new_primary_paths=57600,new_indirect_paths=57600*proof['selected_spp'],new_reference_paths=0)
    except Exception as e:r['error']=repr(e)
    finally:r['payload_sha256']={str(p.relative_to(out)):C.sha(p) for p in sorted(out.rglob('*')) if p.is_file()};G.write(out/'result.json',r)
    return r

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cell',choices=('H01','H02','H03'),required=True);ap.add_argument('--depth',type=int,choices=(2,8),required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();r=audit_gpu(a.cell,a.depth,a.out.resolve());print(json.dumps({k:r[k] for k in ('cell','depth','complete','valid','classification','decision','primary','raw_pt_original_numerical_checks','error') if k in r},indent=2));raise SystemExit(0 if r.get('decision',{}).get('pass_') else 1)

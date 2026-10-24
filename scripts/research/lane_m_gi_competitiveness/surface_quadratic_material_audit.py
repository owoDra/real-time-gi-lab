"""020 independent complete-field CPU intake and numerical/image audit."""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import numpy as np
import surface_quadratic_material_replay as T

P,Q=T.P,T.Q
R,C,F,G=T.R,T.C,T.F,T.G


def dot3(a,b):
    return (a[...,0]*b[...,0]+a[...,1]*b[...,1])+a[...,2]*b[...,2]


def expected_geometry(arrays):
    camera=arrays['camera'];w,h=int(camera[18]),int(camera[19]);raw=arrays['hits'].reshape(h,w,8);hit=raw[...,7]==1
    y,x=np.indices((h,w),dtype=np.float32)
    nx=np.float32(2)*((x+np.float32(.5))/np.float32(w))-np.float32(1)
    ny=np.float32(1)-np.float32(2)*((y+np.float32(.5))/np.float32(h))
    ray=(camera[4:7]+camera[8:11]*(nx*camera[11])[...,None])+camera[12:15]*(ny*camera[15])[...,None]
    ray=ray/np.sqrt(dot3(ray,ray))[...,None]
    normal=raw[...,:3].copy().view('<f4');length=np.sqrt(dot3(normal,normal))
    np.divide(normal,length[...,None],out=normal,where=hit[...,None]);normal[~hit]=0
    flip=hit & (dot3(normal,ray)>0);normal[flip]*=np.float32(-1)
    t=raw[...,3].copy().view('<f4');position=np.zeros((h,w,3),dtype=np.float32)
    position[hit]=camera[:3]+ray[hit]*t[hit,None]
    expected=np.zeros((h,w,8),dtype=np.float32);expected[...,:3]=position;expected[...,4:7]=normal
    return expected


def geometry_health(geometry,arrays):
    expected=expected_geometry(arrays);hit=arrays['hits'][:,7].reshape(expected.shape[:2])==1
    R.require(geometry.shape==expected.shape and geometry.dtype==np.float32 and np.isfinite(geometry).all(),'020 geometry ABI/nonfinite')
    R.require((geometry[~hit]==0).all() and (geometry[...,3]==0).all() and (geometry[...,7]==0).all(),'020 miss/padding geometry differs')
    position_error=float(np.abs(geometry[...,:3].astype(float)-expected[...,:3]).max())
    normal_error=float(np.abs(geometry[...,4:7].astype(float)-expected[...,4:7]).max())
    bound=5e-6*max(1.,float(np.abs(expected[...,:3]).max()))
    norms=np.sqrt((geometry[...,4:7].astype(float)**2).sum(axis=2));unit_error=float(np.abs(norms[hit]-1).max()) if hit.any() else 0.
    R.require(position_error<=bound and normal_error<=2e-5 and unit_error<=1e-4,'020 independent camera/normal bound failed')
    return dict(position_max_absolute_error=position_error,position_bound=bound,normal_max_absolute_error=normal_error,normal_max_unit_error=unit_error)


def masks_float32(geometry,raw,epsilon):
    h,w=geometry.shape[:2];raw=raw.reshape(h,w,8);hit=raw[...,7]==1;material=raw[...,5];position=geometry[...,:3];normal=geometry[...,4:7]
    masks=[]
    for stride in (1,2,4):
        stage=[]
        for dy,dx,_ in P.B.OFFSETS:
            sy,sx=dy*stride,dx*stride;steps=max(abs(sy),abs(sx));accept=hit.copy()
            for k in range(1,steps+1):
                yy,xx=math.floor(k*sy/steps+.5),math.floor(k*sx/steps+.5)
                accept &= P.B.shifted(hit,yy,xx)
                accept &= P.B.shifted(material,yy,xx)==material
                accept &= dot3(normal,P.B.shifted(normal,yy,xx))>=np.float32(.999)
                accept &= np.abs(dot3(normal,P.B.shifted(position,yy,xx)-position))<=np.float32(epsilon)
            stage.append(accept)
        masks.append(stage)
    return np.array(masks,dtype=bool)


def coefficient_health(coefficients,maps,masks,hit):
    R.require(coefficients.dtype==np.float32 and coefficients.shape==masks.shape and np.isfinite(coefficients).all(),'020 coefficient ABI/nonfinite')
    R.require((coefficients[~masks]==0).all() and (coefficients[:,:,~hit]==0).all(),'020 nonzero rejected/miss coefficient')
    c=coefficients.astype(float);summation=c.sum(axis=1);l1=np.abs(c).sum(axis=1)
    error=float(np.abs(summation[:,hit]-1).max()) if hit.any() else 0.;max_l1=float(l1.max())
    R.require(error<=2e-4 and max_l1<=4+2e-4,'020 coefficient normalization/L1 bound')
    R.require(maps.shape==(6,)+hit.shape and maps.dtype==np.uint32,'020 map ABI')
    encoded=np.sum(masks.astype(np.uint32)*(np.uint32(1)<<np.arange(25,dtype=np.uint32))[None,:,None,None],axis=1,dtype=np.uint32)
    R.require(np.array_equal(maps[:3],encoded),'020 independent full float32 masks differ')
    selected=maps[3:];model=selected&255;retained=(selected>>8)&255;columns=(selected>>16)&255
    R.require(np.isin(model[:,hit],(0,1,2)).all() and (model[:,~hit]==255).all() and (selected>>24==0).all() and (retained<=63).all() and (columns<=63).all(),'020 invalid selector/rank bits')
    R.require((retained[:,~hit]==0).all() and (columns[:,~hit]==0).all(),'020 miss rank bits')
    return dict(maximum_hit_constant_error=error,maximum_coefficient_l1=max_l1,negative_coefficients=int((c<0).sum()))


def svd_coefficients(position,normal,hit,masks,y,x,stride):
    if not hit[y,x]:return np.zeros(25),255,0,0
    n=normal[y,x].astype(float);helper=np.array([0.,0.,1.]) if abs(n[2])<float(np.float32(.999)) else np.array([0.,1.,0.])
    tangent=np.cross(helper,n);tangent/=np.linalg.norm(tangent);bitangent=np.cross(n,tangent)
    d=[];weights=[]
    for mask,(dy,dx,weight) in zip(masks[:,y,x],P.B.OFFSETS):
        d.append(position[y+dy*stride,x+dx*stride].astype(float)-position[y,x].astype(float) if mask else np.zeros(3));weights.append(weight if mask else 0)
    d=np.array(d);a=np.array(weights,dtype=float);root=np.sqrt(a);scale=max(1e-300,float(np.linalg.norm(d,axis=1).max()))
    if (d==0).all():scale=1.
    u=d@tangent/scale;v=d@bitangent/scale;basis=np.stack([np.ones(25),u,v,u*u,u*v,v*v],axis=1)
    retained=[];affine=None;affine_bits=0
    for column in range(6):
        target=root*basis[:,column]
        if retained:
            design=root[:,None]*basis[:,retained];residual=target-design@np.linalg.lstsq(design,target,rcond=1e-14)[0]
        else:residual=target
        if np.dot(residual,residual)>1e-6*a.sum():retained.append(column)
        if column==2:
            design=root[:,None]*basis[:,retained];e0=np.zeros(len(retained));e0[0]=1
            affine=root*np.linalg.lstsq(design.T,e0,rcond=1e-14)[0];affine_bits=sum(1<<k for k in retained)
    design=root[:,None]*basis[:,retained];e0=np.zeros(len(retained));e0[0]=1
    quadratic=root*np.linalg.lstsq(design.T,e0,rcond=1e-14)[0];bits=sum(1<<k for k in retained)
    if np.abs(quadratic).sum()<=4:return quadratic,0,bits,bits
    if np.abs(affine).sum()<=4:return affine,1,bits,affine_bits
    return a/a.sum(),2,bits,1


def replay_stage(previous,coefficients,stride):
    result=np.zeros_like(previous,dtype=np.float32)
    for c,(dy,dx,_) in zip(coefficients,P.B.OFFSETS):result=result+c*P.B.shifted(previous,dy*stride,dx*stride)
    return result


def capture_arrays(root):
    return dict(geometry=np.fromfile(root/'geometry.f32',dtype='<f4').reshape(180,320,8),coefficients=np.fromfile(root/'coefficients.f32',dtype='<f4').reshape(3,25,180,320),maps=np.fromfile(root/'maps.u32',dtype='<u4').reshape(6,180,320),stages=np.fromfile(root/'stages.f32',dtype='<f4').reshape(5,3,180,320),unclipped=np.fromfile(root/'unclipped.f32',dtype='<f4').reshape(5,3,180,320))


def audit_cpu(cell,depth,out):
    T.committed();root=T.BASE/(T.tag(cell,depth)+'-v1');out=P.new_root(out)
    r=dict(schema='m001-q020-cpu-terminal-audit/1',cell=cell,depth=depth,complete=False,valid=False,gpu_executed=False,source_commit=G.head(),classification='STOP_NO_RETRY')
    try:
        receipt=R.read(root/'result.json');plan=R.read(root/'plan.json');launch=R.read(root/'launch/result.json')
        R.require(receipt['complete'] and receipt['valid'] and launch['returncode']==0 and not launch['timed_out'],'020 native rehearsal invalid')
        R.require(receipt['source_commit']==G.head() and C.sha(root/'plan.json')==receipt['plan_sha256']==R.read(root/'started.json')['plan_sha256'],'020 CPU source/plan/start differs')
        R.require({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}==set(receipt['payload_sha256'])|{'result.json'},'020 new CPU inventory differs')
        F.rehash({str(root/name):digest for name,digest in receipt['payload_sha256'].items()});F.rehash(plan['input_sha256'])
        inputs,proof=T.prepare_inputs(cell,depth);inputs.update(T.previous_gate(cell,depth));arrays=T.input_arrays(proof)
        R.require({p.name for p in (root/'input').iterdir()}=={'camera.f32','hits.u32','sources.f32'},'020 unexpected uploaded-input inventory')
        for name,key in (('camera.f32','camera'),('hits.u32','hits'),('sources.f32','sources')):
            R.require((root/'input'/name).read_bytes()==arrays[key].tobytes(),'020 original input conversion differs');P.pin(root/'input'/name,inputs)
        R.require(inputs==plan['input_sha256'] and proof==plan['proof'],'020 independent source/build/reference plan differs')
        R.require(launch['command']==plan['command'],'020 native command differs')
        R.require({p.name for p in (root/'capture').iterdir()}=={'geometry.f32','coefficients.f32','maps.u32','stages.f32','unclipped.f32','complete.json'},'020 native CPU capture inventory differs')
        completion=R.read(root/'capture/complete.json');R.require(completion['complete'] and completion['gpu_initialized'] is False and completion['pixels']==57600 and completion['images']==5,'020 CPU completion ABI differs')
        data=capture_arrays(root/'capture');geometry=data['geometry'];hit=arrays['hits'][:,7].reshape(180,320)==1
        geometry_report=geometry_health(geometry,arrays);masks=masks_float32(geometry,arrays['hits'],arrays['camera'][16])
        coefficient_report=coefficient_health(data['coefficients'],data['maps'],masks,hit)
        # The actual float32 scalar kernel is replayed on captured geometry.
        shadow_input=out/'shadow-input';shadow_input.mkdir()
        for name in ('camera.f32','hits.u32','sources.f32'):os.link(root/'input'/name,shadow_input/name)
        os.link(root/'capture/geometry.f32',shadow_input/'geometry.f32')
        shadow_launch=out/'shadow-launch';shadow_launch.mkdir();command=[proof['executable'],'--cpu-replay-geometry','--input',str(shadow_input),'--out',str(out/'shadow-capture')]
        saved=os.environ.get('VK_ICD_FILENAMES');os.environ['VK_ICD_FILENAMES']='/nonexistent/q020-cpu-audit.json'
        try:shadow_run=G.guarded(command,shadow_launch,120,180)
        finally:
            if saved is None:os.environ.pop('VK_ICD_FILENAMES',None)
            else:os.environ['VK_ICD_FILENAMES']=saved
        G.write(shadow_launch/'result.json',shadow_run)
        R.require(shadow_run['returncode']==0 and not shadow_run['timed_out'],'020 CPU geometry replay failed; stop')
        R.require(R.read(out/'shadow-capture/complete.json')['gpu_initialized'] is False,'020 audit initialized GPU')
        shadow=capture_arrays(out/'shadow-capture')
        R.require(np.array_equal(data['maps'],shadow['maps']),'020 all float32 kernel selector/mask fields differ')
        R.require(np.allclose(data['coefficients'],shadow['coefficients'],rtol=2e-4,atol=2e-5),'020 all float32 kernel coefficients differ')
        ids=np.flatnonzero(hit);points=np.unique(np.concatenate((np.linspace(0,57599,64,dtype=np.int64),ids[((2*np.arange(64)+1)*len(ids))//128])))
        svd=[];svd_maps=[];coefficient_error=0.;rank_differences=0;svd_hit_vectors=0;analytic_miss_vectors=0
        for stage,stride in enumerate((1,2,4)):
            values=[];selection=[]
            for i in points:
                y,x=int(i//320),int(i%320);expected,model,bits,selected=svd_coefficients(geometry[...,:3],geometry[...,4:7],hit,masks[stage],y,x,stride)
                actual=data['coefficients'][stage,:,y,x];R.require(np.allclose(actual,expected,rtol=2e-4,atol=2e-5),'020 independent SVD coefficient bound failed')
                packed=model|(bits<<8)|(selected<<16);rank_differences+=int(packed!=int(data['maps'][3+stage,y,x]));selection.append(packed)
                coefficient_error=max(coefficient_error,float(np.abs(actual-expected).max()));values.append(expected)
                if hit[y,x]:svd_hit_vectors+=1
                else:analytic_miss_vectors+=1
            svd.append(values);svd_maps.append(selection)
        svd=np.array(svd);P.save_arrays(out/'independent-svd.npz',points=points,coefficients=svd,selector=np.array(svd_maps,dtype=np.uint32))
        with np.load(Path(proof['old_018_work'])/'coefficients.npz',allow_pickle=False) as old:
            old_selector=old['model'].astype(np.uint32)|(old['retained_columns'].astype(np.uint32)<<8)|(old['selected_columns'].astype(np.uint32)<<16)
            changes=dict(model_pixels=int(((data['maps'][3:]&255)!=(old_selector&255)).sum()),retained_rank_pixels=int((((data['maps'][3:]>>8)&255)!=((old_selector>>8)&255)).sum()),selected_rank_pixels=int((((data['maps'][3:]>>16)&255)!=((old_selector>>16)&255)).sum()))
        oldmask=np.load(Path(proof['old_017_work'])/'geometry-masks.npz',allow_pickle=False)
        changes['barrier_taps']=int((masks!=oldmask['masks']).sum());oldmask.close()
        sources,direct,reference=T.images(proof);rows=[];scalar_outputs=0;maximum_svd_stage_scaled_error=0.;maximum_full_stage_scaled_error=0.;clipping=[]
        for image,name in enumerate(T.NAMES):
            previous=sources[image];image_clipping=[]
            for stage,stride in enumerate((1,2,4)):
                raw=data['unclipped'][image,stage];clipped=data['stages'][image,stage]
                R.require(np.isfinite(raw).all() and np.isfinite(clipped).all() and (clipped>=0).all(),'020 image nonfinite/negative')
                R.require(np.array_equal(clipped,np.maximum(raw,np.float32(0))),'020 clipping differs')
                replay=replay_stage(previous,data['coefficients'][stage],stride);scale=max(float(np.abs(previous).max()),1e-20)
                R.require(np.allclose(raw,replay,rtol=2e-5,atol=2e-7*scale) and np.allclose(clipped,np.maximum(replay,0),rtol=2e-5,atol=2e-7*scale),'020 full ordered float32 stage bound failed')
                maximum_full_stage_scaled_error=max(maximum_full_stage_scaled_error,float(np.abs(raw.astype(float)-replay).max())/scale)
                for i,coeff in zip(points,svd[stage]):
                    y,x=int(i//320),int(i%320);terms=[]
                    for weight,(dy,dx,_) in zip(coeff,P.B.OFFSETS):
                        yy,xx=y+dy*stride,x+dx*stride;terms.append(float(weight)*float(previous[yy,xx]) if 0<=yy<180 and 0<=xx<320 else 0.)
                    expected=math.fsum(terms);error=max(abs(float(raw[y,x])-expected),abs(float(clipped[y,x])-max(expected,0)))
                    R.require(error<=2e-4*scale,'020 independent SVD stage bound failed')
                    maximum_svd_stage_scaled_error=max(maximum_svd_stage_scaled_error,error/scale);scalar_outputs+=2
                negative=raw<0;image_clipping.append(dict(negative_pixels=int(negative.sum()),minimum=float(raw.min()),negative_absolute_energy=math.fsum(float(-x) for x in raw[negative])))
                previous=clipped
            components,errors=P.score_images(direct[image],previous.astype(float),reference)
            for key,value in errors.items():
                rmse=math.sqrt(math.fsum(float(x)*float(x) for x in value.ravel())/57600);rms=math.sqrt(math.fsum(float(x)*float(x) for x in reference[key].ravel())/57600)
                bias=math.fsum(map(float,value.ravel()))/math.fsum(map(float,reference[key].ravel()))
                R.require(math.isclose(rmse/rms,components[key]['nrmse'],rel_tol=1e-11,abs_tol=1e-30) and math.isclose(bias,components[key]['signed_sum_bias'],rel_tol=1e-11,abs_tol=1e-30),'020 independent fsum whole-image metrics differ')
            P.save_arrays(out/(name+'-errors.npz'),**errors)
            rows.append(dict(name=name,components=components,pass_=P.B.quality(components),scoring_exclusions=0));clipping.append(dict(name=name,stages=image_clipping))
        decision=T.decision(cell,depth,rows);F.rehash(plan['input_sha256']);F.rehash({str(root/name):digest for name,digest in receipt['payload_sha256'].items()})
        r.update(complete=True,valid=True,classification='CPU_TARGET_PASS' if decision['pass_'] else 'STOP_NO_RETRY',decision=decision,rows=rows,clipping=clipping,geometry=geometry_report,coefficients=coefficient_report,changes_from_018=changes,
                 payloads_rehashed=len(receipt['payload_sha256']),full_coefficients_and_integer_maps_replayed=True,complete_preclip_clipped_stage_error_arrays_verified=45,
                 independent_svd_hit_coefficient_vectors=svd_hit_vectors,analytic_miss_coefficient_vectors=analytic_miss_vectors,scalar_preclip_clipped_pixel_comparisons=scalar_outputs,
                 maximum_svd_coefficient_absolute_error=coefficient_error,double_svd_rank_model_differences=rank_differences,maximum_svd_stage_scaled_error=maximum_svd_stage_scaled_error,maximum_full_stage_scaled_error=maximum_full_stage_scaled_error,
                 independent_fsum_metrics_verified=True,scalar_pixel_ids=points.tolist(),native_receipt=str(root/'result.json'),native_receipt_sha256=C.sha(root/'result.json'),plan_sha256=C.sha(root/'plan.json'),new_render_paths=0,new_reference_paths=0)
    except Exception as error:r['error']=repr(error)
    finally:
        r['payload_sha256']={str(p.relative_to(out)):C.sha(p) for p in sorted(out.rglob('*')) if p.is_file()};G.write(out/'result.json',r)
    return r


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cell',choices=('H01','H02','H03'),required=True);ap.add_argument('--depth',type=int,choices=(2,8),required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    r=audit_cpu(a.cell,a.depth,a.out.resolve());print(json.dumps({k:r[k] for k in ('cell','depth','complete','valid','classification','decision','geometry','coefficients','changes_from_018','maximum_svd_coefficient_absolute_error','double_svd_rank_model_differences','maximum_svd_stage_scaled_error','error') if k in r},indent=2));sys.exit(0 if r['complete'] and r['decision']['pass_'] else 1)

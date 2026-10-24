"""019 independent SVD/all-field fixtures and actual native pre-Vulkan contracts."""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import numpy as np
import surface_quadratic_cpu as P
from test_surface_quadratic_filter import scalar_coefficients


def fixtures(root):
    count=0;vectors=0;outputs=0;max_coefficient_error=0.;max_stage_error=0.;camera_pixels=0
    for directory in sorted(root.iterdir()):
        info=P.R.read(directory/'fixture.json');h,w=info['height'],info['width'];n=h*w
        camera=np.fromfile(directory/'camera.f32',dtype='<f4')
        hits=np.fromfile(directory/'hits.u32',dtype='<u4').reshape(h,w,8)
        geo=np.fromfile(directory/'geometry.f32',dtype='<f4').reshape(h,w,8)
        coefficients=np.fromfile(directory/'coefficients.f32',dtype='<f4').reshape(3,25,h,w)
        maps=np.fromfile(directory/'maps.u32',dtype='<u4').reshape(6,h,w)
        sources=np.fromfile(directory/'sources.f32',dtype='<f4').reshape(h,w)
        stages=np.fromfile(directory/'stages.f32',dtype='<f4').reshape(3,h,w)
        unclipped=np.fromfile(directory/'unclipped.f32',dtype='<f4').reshape(3,h,w)
        pos,normal=geo[...,:3].astype(float),geo[...,4:7].astype(float);hit=hits[...,7]==1;material=hits[...,5]
        masks=P.P.B.geometry_masks(pos,normal,hit,material,float(camera[16]))
        encoded=np.sum(masks.astype(np.uint32)*(np.uint32(1)<<np.arange(25,dtype=np.uint32))[None,:,None,None],axis=1,dtype=np.uint32)
        assert np.array_equal(encoded,maps[:3]),'independent complete scalar barrier maps differ'
        if info['geometry_from_camera']:
            y,x=np.indices((h,w),dtype=np.float32)
            nx=np.float32(2)*((x+np.float32(.5))/np.float32(w))-np.float32(1)
            ny=np.float32(1)-np.float32(2)*((y+np.float32(.5))/np.float32(h))
            ray=(camera[4:7]+camera[8:11]*(nx*camera[11])[...,None])+camera[12:15]*(ny*camera[15])[...,None]
            length=np.sqrt((ray[...,0]*ray[...,0]+ray[...,1]*ray[...,1])+ray[...,2]*ray[...,2]);ray=ray/length[...,None]
            normals=hits[...,:3].copy().view('<f4');nl=np.sqrt((normals[...,0]**2+normals[...,1]**2)+normals[...,2]**2);normals/=nl[...,None]
            dot=(normals[...,0]*ray[...,0]+normals[...,1]*ray[...,1])+normals[...,2]*ray[...,2]
            normals[dot>0]*=-1;t=hits[...,3].copy().view('<f4')
            expected=camera[:3]+ray*t[...,None]
            assert np.allclose(geo[...,:3],expected,rtol=0,atol=5e-6*max(1,float(np.abs(expected).max())))
            assert np.allclose(geo[...,4:7],normals,rtol=0,atol=2e-5)
            camera_pixels+=n
        previous=sources.copy()
        for stage,stride in enumerate((1,2,4)):
            raw=np.zeros((h,w),dtype=np.float32)
            for j,(dy,dx,_) in enumerate(P.P.B.OFFSETS):raw=raw+coefficients[stage,j]*P.P.B.shifted(previous,dy*stride,dx*stride)
            assert np.array_equal(raw,unclipped[stage]) and np.array_equal(np.maximum(raw,0),stages[stage]),'ordered complete stages differ'
            outputs+=n*2
            scale=max(float(np.abs(previous).max()),1e-20)
            for y in range(h):
                for x in range(w):
                    expected,model,bits,selected=scalar_coefficients(pos,normal,hit,material,float(camera[16]),y,x,stride)
                    actual=coefficients[stage,:,y,x]
                    assert np.allclose(actual,expected,rtol=2e-4,atol=2e-5),'independent SVD coefficients differ'
                    assert int(maps[3+stage,y,x])==model|(bits<<8)|(selected<<16),'independent fixture rank/model differs'
                    max_coefficient_error=max(max_coefficient_error,float(np.abs(actual-expected).max()))
                    terms=[]
                    for c,(dy,dx,_) in zip(expected,P.P.B.OFFSETS):
                        yy,xx=y+dy*stride,x+dx*stride
                        terms.append(float(c)*float(previous[yy,xx]) if 0<=yy<h and 0<=xx<w else 0.)
                    value=math.fsum(terms)
                    assert abs(float(unclipped[stage,y,x])-value)<=2e-4*scale,'independent SVD preclip differs'
                    assert abs(float(stages[stage,y,x])-max(value,0))<=2e-4*scale,'independent SVD clip differs'
                    max_stage_error=max(max_stage_error,abs(float(unclipped[stage,y,x])-value));vectors+=1
            previous=stages[stage]
        count+=1
    assert count==16 and vectors>4000
    return dict(independent_fixtures=count,independent_svd_coefficient_vectors=vectors,full_preclip_clipped_pixels_replayed=outputs,independent_camera_pixels=camera_pixels,maximum_coefficient_absolute_error=max_coefficient_error,maximum_svd_preclip_absolute_error=max_stage_error)


def native(binary,out):
    base=out/'native-input';base.mkdir()
    camera=np.array([0,0,0,1e-4,0,0,1,100,1,0,0,1,0,1,0,1,1e-5,5,320,180],dtype='<f4')
    hits=np.zeros((57600,8),dtype='<u4');hits[:,3]=np.float32(np.inf).view('<u4');hits[:,4:7]=np.uint32(0xffffffff)
    source=np.zeros(5*57600,dtype='<f4')
    baseline={'camera.f32':camera.tobytes(),'hits.u32':hits.tobytes(),'sources.f32':source.tobytes()}
    for name,data in baseline.items():(base/name).write_bytes(data)
    rows=[];previous_icd=os.environ.get('VK_ICD_FILENAMES');os.environ['VK_ICD_FILENAMES']='/nonexistent/m001-q019-no-vulkan.json'
    try:
        def run(name,change=None,valid=False,arguments=None,existing=None):
            work=out/name;work.mkdir();inputs=work/'input';inputs.mkdir();change=change or {}
            for filename in baseline:
                if filename in change:
                    if change[filename] is not None:(inputs/filename).write_bytes(change[filename])
                else:os.link(base/filename,inputs/filename)
            target=existing or work/'capture'
            command=[str(binary),*(arguments if arguments is not None else ['--cpu-check','--input',str(inputs),'--out',str(target)])]
            row=P.G.guarded(command,work,120,180);row.update(name=name,expected_returncode=0 if valid else 2)
            assert row['returncode']==row['expected_returncode'] and not row['timed_out'],name+': '+row['stderr']
            if valid:
                assert P.R.read(target/'complete.json')['gpu_initialized'] is False
                for filename in ('stages.f32','unclipped.f32'):assert (np.fromfile(target/filename,dtype='<f4')==0).all()
                if name=='valid-all-miss-cpu':
                    for filename in ('geometry.f32','coefficients.f32'):assert (np.fromfile(target/filename,dtype='<f4')==0).all()
                else:
                    coefficients=np.fromfile(target/'coefficients.f32',dtype='<f4').reshape(3,25,57600)
                    assert np.array_equal(coefficients.sum(axis=1)[:,0],np.ones(3)) and (coefficients[:,:,1:]==0).all()
            elif existing is None:assert not target.exists(),name+' wrote output before rejecting invalid input'
            P.G.write(work/'result.json',row);rows.append(dict(name=name,receipt=str(work/'result.json'),receipt_sha256=P.C.sha(work/'result.json')))
            return target
        run('missing-arguments',arguments=[]);run('missing-camera',{'camera.f32':None});run('camera-byte-size',{'camera.f32':b'bad'})
        for name,index,value in [('nonfinite-camera',0,np.nan),('wrong-dimensions',18,321),('zero-epsilon',16,0),('zero-forward',6,0),('negative-tangent',11,-1),('nonunit-basis',8,2),('wrong-image-count',17,4)]:
            c=camera.copy();c[index]=value;run(name,{'camera.f32':c.tobytes()})
        c=camera.copy();c[8]=0;c[10]=1;run('nonorthogonal-basis',{'camera.f32':c.tobytes()})
        for name,word,value in [('invalid-flag',7,2),('invalid-miss-normal',0,np.float32(1).view('<u4')),('invalid-miss-t',3,0),('invalid-miss-id',4,0)]:
            h=hits.copy();h[0,word]=value;run(name,{'hits.u32':h.tobytes()})
        hit=hits.copy();hit[0]=[0,0,np.float32(1).view('<u4'),np.float32(2).view('<u4'),0,0,0,1]
        for name,word,value in [('zero-hit-normal',2,0),('negative-hit-t',3,np.float32(-1).view('<u4')),('invalid-hit-id',5,0xffffffff)]:
            h=hit.copy();h[0,word]=value;run(name,{'hits.u32':h.tobytes()})
        for name,value in [('negative-source',-1),('nonfinite-source',np.nan)]:
            values=source.copy();values[0]=value;run(name,{'sources.f32':values.tobytes()})
        run('source-byte-size',{'sources.f32':b'bad'})
        run('valid-one-hit-cpu',{'hits.u32':hit.tobytes()},valid=True)
        target=run('valid-all-miss-cpu',valid=True);hashes={str(p):P.C.sha(p) for p in target.iterdir()}
        run('overwrite-refused',existing=target);P.F.rehash(hashes)
        for filename,data in baseline.items():assert (base/filename).read_bytes()==data
    finally:
        if previous_icd is None:os.environ.pop('VK_ICD_FILENAMES',None)
        else:os.environ['VK_ICD_FILENAMES']=previous_icd
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixtures',type=Path,required=True);parser.add_argument('--binary',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    out=P.P.new_root(a.out);r=dict(schema='m001-q019-independent-cpu-kernel-tests/1',complete=False,gpu_executed=False)
    try:r.update(fixtures(a.fixtures),native_contracts=native(a.binary,out),complete=True)
    except Exception as error:r['error']=repr(error)
    finally:P.G.write(out/'result.json',r)
    print(json.dumps({k:v for k,v in r.items() if k!='native_contracts'},indent=2));sys.exit(0 if r['complete'] else 1)

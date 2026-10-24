"""017 geometry-only segment-barrier a-trous kernel; no GPU or file writes."""
import numpy as np

STRIDES=(1,2,4)
KERNEL=(1,4,6,4,1)
OFFSETS=tuple((dy,dx,KERNEL[dy+2]*KERNEL[dx+2]) for dy in range(-2,3) for dx in range(-2,3))


def require(ok,message):
    if not ok:raise ValueError(message)


def validate_geometry(position,normal,hit,material,epsilon):
    require(hit.ndim==2 and min(hit.shape)>0 and hit.dtype==np.bool_,'017 invalid hit shape/type')
    require(position.shape==normal.shape==hit.shape+(3,) and material.shape==hit.shape
            and material.dtype.kind=='u','017 geometry shape/material differs')
    require(np.isfinite(position).all() and np.isfinite(normal).all() and np.isfinite(epsilon) and epsilon>0,
            '017 nonfinite geometry/epsilon')
    require((np.abs(np.linalg.norm(normal[hit],axis=1)-1)<1e-6).all(),'017 nonunit hit normals')


def shifted(a,dy,dx):
    """At each center return a[y+dy,x+dx], with zero outside the viewport."""
    h,w=a.shape[:2];out=np.zeros_like(a)
    ya,yb=max(0,-dy),min(h,h-dy);xa,xb=max(0,-dx),min(w,w-dx)
    if ya<yb and xa<xb:out[ya:yb,xa:xb]=a[ya+dy:yb+dy,xa+dx:xb+dx]
    return out


def geometry_masks(position,normal,hit,material,epsilon):
    validate_geometry(position,normal,hit,material,epsilon)
    compatibility={};stages=[]
    for stride in STRIDES:
        taps=[]
        for dy,dx,_ in OFFSETS:
            dy*=stride;dx*=stride;m=max(abs(dy),abs(dx));mask=hit.copy()
            for k in range(1,m+1):
                # Exact integer form of floor(k*delta/m+.5), including negatives.
                sy=(2*k*dy+m)//(2*m);sx=(2*k*dx+m)//(2*m)
                key=(sy,sx)
                if key not in compatibility:
                    ph=shifted(hit,sy,sx);pn=shifted(normal,sy,sx);pp=shifted(position,sy,sx);pm=shifted(material,sy,sx)
                    compatibility[key]=(hit & ph & (material==pm) & ((normal*pn).sum(axis=2)>=.999)
                                        & (np.abs((normal*(pp-position)).sum(axis=2))<=epsilon))
                mask &= compatibility[key]
            taps.append(mask)
        stages.append(np.stack(taps))
    return np.stack(stages)


def pass_image(image,masks,stride):
    require(image.ndim==2 and np.isfinite(image).all() and (image>=0).all(),'017 invalid radiance image')
    require(stride in STRIDES and masks.dtype==np.bool_ and masks.shape==(25,)+image.shape,'017 invalid pass mask/stride')
    numerator=np.zeros_like(image,dtype=np.float64);denominator=np.zeros_like(image,dtype=np.uint16)
    for mask,(dy,dx,weight) in zip(masks,OFFSETS):
        numerator+=shifted(image,dy*stride,dx*stride)*mask*weight;denominator+=mask.astype(np.uint16)*weight
    output=np.zeros_like(numerator);np.divide(numerator,denominator,out=output,where=denominator>0)
    require(np.isfinite(output).all() and (output>=0).all(),'017 invalid reconstructed radiance')
    return output


def reconstruct(image,masks):
    require(masks.dtype==np.bool_ and masks.shape==(3,25)+image.shape,'017 complete stage masks differ')
    stages=[]
    for stride,mask in zip(STRIDES,masks):
        image=pass_image(image,mask,stride);stages.append(image)
    return np.stack(stages)


def quality(components):
    for key in ('direct','indirect','total'):
        c=components[key]
        require(c['pixels']==57600 and c['scoring_exclusions']==0,'017 incomplete scoring')
        for name in ('nrmse','signed_sum_bias','whole_image_max_absolute'):
            require(c[name] is not None and np.isfinite(c[name]),'017 undefined/nonfinite metric')
    t,i=components['total'],components['indirect']
    return bool(t['nrmse']<=.05 and i['nrmse']<=.10 and abs(i['signed_sum_bias'])<=.05)


def decision(rows,bias):
    passed=[r['spp'] for r in rows if quality(r['components'])]
    first=min(passed) if passed else None
    return dict(first_passing_spp=first,reference_bias_pass=quality(bias),
                pass_=first is not None and first<=64 and quality(bias))

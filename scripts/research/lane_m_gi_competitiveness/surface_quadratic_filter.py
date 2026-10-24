"""018 geometry-only rank-reduced weighted polynomial reconstruction."""
import numpy as np
import geometry_barrier_filter as B

PIVOT=1e-6
L1_LIMIT=4.


def validate_coefficients(coefficients,masks,hit):
    B.require(coefficients.shape==masks.shape and coefficients.dtype==np.float64
              and np.isfinite(coefficients).all(),'018 invalid coefficient shape/value')
    B.require((coefficients[~masks]==0).all() and (coefficients[:,~hit]==0).all(),'018 nonzero rejected coefficient')
    sums=coefficients.sum(axis=0);l1=np.abs(coefficients).sum(axis=0)
    B.require((np.abs(sums[hit]-1)<=1e-8).all() and (l1[hit]<=L1_LIMIT).all(),'018 coefficient normalization/L1 invalid')


def select_model(quadratic,affine,constant,hit):
    B.require(np.isfinite(quadratic).all() and np.isfinite(affine).all() and np.isfinite(constant).all(),
              '018 nonfinite model')
    model=np.full(hit.shape,255,dtype=np.uint8);coefficients=constant.copy();model[hit]=2
    affine_ok=hit & (np.abs(affine).sum(axis=0)<=L1_LIMIT)
    coefficients[:,affine_ok]=affine[:,affine_ok];model[affine_ok]=1
    quadratic_ok=hit & (np.abs(quadratic).sum(axis=0)<=L1_LIMIT)
    coefficients[:,quadratic_ok]=quadratic[:,quadratic_ok];model[quadratic_ok]=0
    return coefficients,model


def fit_pass(position,normal,hit,masks,stride):
    B.require(stride in B.STRIDES and masks.dtype==np.bool_ and masks.shape==(25,)+hit.shape,'018 pass mask/stride differs')
    B.validate_geometry(position,normal,hit,np.zeros(hit.shape,dtype=np.uint32),1.)
    B.require(np.array_equal(masks[12],hit),'018 missing/extra center support')
    helper=np.zeros_like(normal);helper[...,2]=1;helper[np.abs(normal[...,2])>=.999]=[0,1,0]
    tangent=np.cross(helper,normal);length=np.linalg.norm(tangent,axis=2,keepdims=True)
    np.divide(tangent,length,out=tangent,where=length>0);bitangent=np.cross(normal,tangent)
    delta=np.stack([(B.shifted(position,dy*stride,dx*stride)-position)*mask[...,None]
                    for mask,(dy,dx,_) in zip(masks,B.OFFSETS)])
    scale=np.linalg.norm(delta,axis=3).max(axis=0);scale=np.where(scale>0,scale,1.)
    u=(delta*tangent).sum(axis=3)/scale;v=(delta*bitangent).sum(axis=3)/scale
    features=(np.ones_like(u),u,v,u*u,u*v,v*v)
    raw=masks*np.array([w for _,_,w in B.OFFSETS],dtype=float)[:,None,None]
    total=raw.sum(axis=0);constant=np.zeros_like(raw);np.divide(raw,total,out=constant,where=total>0)
    qs=[];centers=[];retained=np.zeros(hit.shape,dtype=np.uint8);affine_bits=None
    coefficients=np.zeros_like(raw)
    for column,feature in enumerate(features):
        residual=feature.copy();evaluation=np.full(hit.shape,1. if column==0 else 0.)
        for _ in range(2):
            for q,center in zip(qs,centers):
                projection=(raw*residual*q).sum(axis=0)
                residual-=projection*q;evaluation-=projection*center
        norm2=(raw*residual*residual).sum(axis=0)
        keep=hit & (norm2>PIVOT*total)
        denominator=np.sqrt(np.where(keep,norm2,1.))
        q=np.where(keep,residual/denominator,0.);center=np.where(keep,evaluation/denominator,0.)
        B.require(np.isfinite(q).all() and np.isfinite(center).all(),'018 nonfinite polynomial factor')
        qs.append(q);centers.append(center);retained[keep]|=np.uint8(1<<column)
        coefficients+=raw*q*center
        if column==2:affine=coefficients.copy();affine_bits=retained.copy()
    selected,model=select_model(coefficients,affine,constant,hit)
    selected_bits=retained.copy();selected_bits[model==1]=affine_bits[model==1];selected_bits[model==2]=1
    selected_bits[~hit]=0
    validate_coefficients(selected,masks,hit)
    return selected,dict(model=model,retained_columns=retained,selected_columns=selected_bits)


def fit(position,normal,hit,masks):
    B.require(masks.dtype==np.bool_ and masks.shape==(3,25)+hit.shape,'018 complete masks differ')
    coefficients=[];maps=[]
    for stride,mask in zip(B.STRIDES,masks):
        c,m=fit_pass(position,normal,hit,mask,stride);coefficients.append(c);maps.append(m)
    return np.stack(coefficients),{key:np.stack([m[key] for m in maps]) for key in maps[0]}


def pass_image(image,coefficients,stride):
    B.require(image.ndim==2 and np.isfinite(image).all() and (image>=0).all(),'018 invalid input image')
    B.require(coefficients.shape==(25,)+image.shape and np.isfinite(coefficients).all() and stride in B.STRIDES,
              '018 invalid application coefficients/stride')
    raw=np.zeros_like(image,dtype=np.float64)
    for c,(dy,dx,_) in zip(coefficients,B.OFFSETS):raw+=c*B.shifted(image,dy*stride,dx*stride)
    B.require(np.isfinite(raw).all(),'018 nonfinite preclip reconstruction')
    return np.maximum(raw,0),raw


def reconstruct(image,coefficients):
    B.require(coefficients.shape==(3,25)+image.shape,'018 incomplete coefficient field')
    stages=[];unclipped=[];clipping=[]
    for stride,coeff in zip(B.STRIDES,coefficients):
        image,raw=pass_image(image,coeff,stride);stages.append(image);unclipped.append(raw)
        negative=raw<0;clipping.append(dict(negative_pixels=int(negative.sum()),minimum=float(raw.min()),
                                          negative_absolute_energy=float(-raw[negative].sum())))
    return np.stack(stages),np.stack(unclipped),clipping

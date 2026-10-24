"""018 actual-kernel checks and independent scalar/SVD replay helper."""
import json
import math
import unittest
import numpy as np
import surface_quadratic_filter as Q
import geometry_barrier_filter as B


def scalar_coefficients(position,normal,hit,material,epsilon,y,x,stride):
    weights=[];points=[];h,w=hit.shape;kernel=[1,4,6,4,1]
    if not hit[y,x]:return np.zeros(25),255,0,0
    for dy in range(-2,3):
        for dx in range(-2,3):
            sy,sx=dy*stride,dx*stride;steps=max(abs(sy),abs(sx));accept=True
            for k in range(1,steps+1):
                yy=y+math.floor(k*sy/steps+.5);xx=x+math.floor(k*sx/steps+.5)
                if not(0<=yy<h and 0<=xx<w) or not hit[yy,xx]:accept=False;break
                if material[yy,xx]!=material[y,x] or np.dot(normal[y,x],normal[yy,xx])<.999:accept=False;break
                if abs(np.dot(normal[y,x],position[yy,xx]-position[y,x]))>epsilon:accept=False;break
            weights.append(kernel[dy+2]*kernel[dx+2] if accept else 0)
            points.append(position[y+sy,x+sx]-position[y,x] if accept else np.zeros(3))
    a=np.array(weights,dtype=float);delta=np.array(points);total=a.sum();root=np.sqrt(a)
    n=normal[y,x];helper=np.array([0.,0.,1.]) if abs(n[2])<.999 else np.array([0.,1.,0.])
    tangent=np.cross(helper,n);tangent/=np.linalg.norm(tangent);bitangent=np.cross(n,tangent)
    scale=max(np.linalg.norm(d) for d in delta);scale=scale if scale>0 else 1.
    u=delta@tangent/scale;v=delta@bitangent/scale
    basis=np.stack([np.ones(25),u,v,u*u,u*v,v*v],axis=1)
    selected=[];affine=None;affine_bits=0
    for column in range(6):
        target=root*basis[:,column]
        if selected:
            design=root[:,None]*basis[:,selected]
            fitted=design@np.linalg.lstsq(design,target,rcond=1e-14)[0];residual=target-fitted
        else:residual=target
        if np.dot(residual,residual)>1e-6*total:selected.append(column)
        if column==2:
            design=root[:,None]*basis[:,selected];e0=np.zeros(len(selected));e0[0]=1
            affine=root*np.linalg.lstsq(design.T,e0,rcond=1e-14)[0];affine_bits=sum(1<<k for k in selected)
    design=root[:,None]*basis[:,selected];e0=np.zeros(len(selected));e0[0]=1
    quadratic=root*np.linalg.lstsq(design.T,e0,rcond=1e-14)[0];bits=sum(1<<k for k in selected)
    if np.abs(quadratic).sum()<=4:return quadratic,0,bits,bits
    if np.abs(affine).sum()<=4:return affine,1,bits,affine_bits
    return a/total,2,bits,1


def fixture(h=9,w=9):
    y,x=np.indices((h,w));position=np.stack((x,y,np.zeros_like(x)),axis=2).astype(float)
    normal=np.zeros_like(position);normal[...,2]=1
    return position,normal,np.ones((h,w),dtype=bool),np.zeros((h,w),dtype=np.uint32)


class Contracts(unittest.TestCase):
    def fit(self,geo):
        masks=B.geometry_masks(*geo,1e-5);coefficient,maps=Q.fit(*geo[:3],masks)
        return coefficient,maps,masks
    def test_independent_scalar_svd_coefficients(self):
        geo=fixture(7,8);coeff,maps,masks=self.fit(geo)
        for stage,stride in enumerate(B.STRIDES):
            for y in range(7):
                for x in range(8):
                    c,model,bits,selected=scalar_coefficients(*geo,1e-5,y,x,stride)
                    np.testing.assert_allclose(coeff[stage,:,y,x],c,rtol=1e-9,atol=1e-10)
                    self.assertEqual(int(maps['model'][stage,y,x]),model)
                    self.assertEqual(int(maps['retained_columns'][stage,y,x]),bits)
                    self.assertEqual(int(maps['selected_columns'][stage,y,x]),selected)
    def test_constant(self):
        c,_,_=self.fit(fixture());stages,raw,_=Q.reconstruct(np.full((9,9),.003),c)
        np.testing.assert_allclose(stages,.003,rtol=1e-10,atol=1e-14);np.testing.assert_array_equal(stages,raw)
    def test_zero(self):
        c,_,_=self.fit(fixture());stages,raw,stats=Q.reconstruct(np.zeros((9,9)),c)
        self.assertTrue((stages==0).all() and (raw==0).all());self.assertTrue(all(x['negative_pixels']==0 for x in stats))
    def test_positive_affine_reproduction(self):
        geo=fixture();c,_,_=self.fit(geo);image=10+.2*geo[0][...,0]+.3*geo[0][...,1]
        stages,_,_=Q.reconstruct(image,c);np.testing.assert_allclose(stages,np.broadcast_to(image,stages.shape),rtol=1e-10,atol=1e-10)
    def test_positive_quadratic_reproduction(self):
        geo=fixture();c,maps,_=self.fit(geo);u,v=geo[0][...,0],geo[0][...,1]
        image=10+.2*u+.3*v+.01*u*u+.02*u*v+.03*v*v
        stages,_,_=Q.reconstruct(image,c);np.testing.assert_allclose(stages,np.broadcast_to(image,stages.shape),rtol=1e-10,atol=1e-10)
        self.assertEqual(int(maps['retained_columns'][0,4,4]),63)
    def test_one_dimensional_rank_and_curvature(self):
        for h,w,column in ((1,9,3),(9,1,5)):
            geo=fixture(h,w);c,maps,_=self.fit(geo);u=geo[0][...,0]+geo[0][...,1];image=2+.3*u+.1*u*u
            stages,_,_=Q.reconstruct(image,c);np.testing.assert_allclose(stages,np.broadcast_to(image,stages.shape),rtol=1e-10,atol=1e-10)
            self.assertTrue((maps['retained_columns'][0]&(1<<column)).any())
    def test_single_pixel_rank(self):
        c,maps,_=self.fit(fixture(1,1));self.assertTrue((maps['retained_columns']==1).all())
        stages,_,_=Q.reconstruct(np.array([[7.]]),c);np.testing.assert_array_equal(stages,7.)
    def test_l1_affine_fallback(self):
        hit=np.ones((1,1),dtype=bool);q=np.zeros((25,1,1));q[0]=5;q[1]=-4;a=np.zeros_like(q);a[0]=2;a[1]=-1;z=np.zeros_like(q);z[12]=1
        c,m=Q.select_model(q,a,z,hit);np.testing.assert_array_equal(c,a);self.assertEqual(m[0,0],1)
    def test_l1_constant_fallback(self):
        hit=np.ones((1,1),dtype=bool);q=np.zeros((25,1,1));q[0]=5;q[1]=-4;z=np.zeros_like(q);z[12]=1
        c,m=Q.select_model(q,q,z,hit);np.testing.assert_array_equal(c,z);self.assertEqual(m[0,0],2)
    def test_signed_coefficients_and_saved_clipping(self):
        c,_,_=self.fit(fixture());negative=np.flatnonzero(c[0,:,4,4]<-1e-8);self.assertTrue(len(negative)>0)
        dy,dx,_=B.OFFSETS[int(negative[0])];image=np.zeros((9,9));image[4+dy,4+dx]=1
        stages,raw,stats=Q.reconstruct(image,c);self.assertLess(raw[0,4,4],0);self.assertEqual(stages[0,4,4],0)
        self.assertGreater(stats[0]['negative_pixels'],0);self.assertGreater(stats[0]['negative_absolute_energy'],0)
    def test_geometry_barriers_with_signed_weights(self):
        for kind in ('miss','material','normal','plane'):
            geo=list(fixture());p,n,h,m=geo
            if kind=='miss':h[:,4]=False
            if kind=='material':m[:,4]=1
            if kind=='normal':n[:,4]=[0,1,0]
            if kind=='plane':p[:,4,2]=.1
            c,_,masks=self.fit(geo);self.assertTrue((c[~masks]==0).all())
            image=np.zeros((9,9));image[:,5:]=1;stages,_,_=Q.reconstruct(image,c);self.assertTrue((stages[:,:,:4]==0).all())
    def test_invalid_normalization_rejected(self):
        c,_,masks=self.fit(fixture());c[0,12,4,4]+=.01
        with self.assertRaises(ValueError):Q.validate_coefficients(c[0],masks[0],np.ones((9,9),dtype=bool))
    def test_invalid_geometry_mask_rejected(self):
        geo=list(fixture());masks=B.geometry_masks(*geo,1e-5);masks[0,12,4,4]=False
        with self.assertRaises(ValueError):Q.fit(*geo[:3],masks)
        geo[1][0,0]=[0,0,2]
        with self.assertRaises(ValueError):Q.fit(*geo[:3],B.geometry_masks(*fixture(),1e-5))
    def test_nonfinite_or_negative_application_rejected(self):
        c,_,_=self.fit(fixture())
        for value in (-1,float('nan'),float('inf')):
            image=np.ones((9,9));image[4,4]=value
            with self.assertRaises(ValueError):Q.reconstruct(image,c)
        c[0,0,0,0]=float('nan')
        with self.assertRaises(ValueError):Q.reconstruct(np.ones((9,9)),c)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
    print(json.dumps(dict(actual_new_contract_tests=result.testsRun,pass_=result.wasSuccessful(),independent_svd_coefficient_rtol=1e-9,independent_svd_coefficient_atol=1e-10)))
    raise SystemExit(0 if result.wasSuccessful() else 1)

"""017 actual-kernel tests and independent scalar replay helper."""
import json
import math
import unittest
import numpy as np
import geometry_barrier_filter as B


def scalar_pixel(image,position,normal,hit,material,epsilon,y,x,stride):
    # Independent direct loops, no vector masks/shift helper/offset table.
    if not hit[y,x]:return 0.
    h,w=hit.shape;num=0.;den=0;kernel=[1,4,6,4,1]
    for dy in range(-2,3):
        for dx in range(-2,3):
            sy,sx=dy*stride,dx*stride;steps=max(abs(sy),abs(sx));okay=True
            for k in range(1,steps+1):
                yy=y+math.floor(k*sy/steps+.5);xx=x+math.floor(k*sx/steps+.5)
                if not(0<=yy<h and 0<=xx<w) or not hit[yy,xx]:okay=False;break
                if material[yy,xx]!=material[y,x] or float(np.dot(normal[y,x],normal[yy,xx]))<.999:okay=False;break
                if abs(float(np.dot(normal[y,x],position[yy,xx]-position[y,x])))>epsilon:okay=False;break
            if okay:
                weight=kernel[dy+2]*kernel[dx+2];num+=float(image[y+sy,x+sx])*weight;den+=weight
    return num/den


def fixture(h=7,w=9):
    y,x=np.indices((h,w));pos=np.stack((x,y,np.zeros_like(x)),axis=2).astype(float)
    normal=np.zeros_like(pos);normal[:,:,2]=1
    return pos,normal,np.ones((h,w),dtype=bool),np.zeros((h,w),dtype=np.uint32)


class Contracts(unittest.TestCase):
    def compare_scalar(self,geo,image):
        masks=B.geometry_masks(*geo,1e-5);stages=B.reconstruct(image,masks);previous=image
        for stride,stage in zip(B.STRIDES,stages):
            expected=np.array([[scalar_pixel(previous,*geo,1e-5,y,x,stride) for x in range(image.shape[1])] for y in range(image.shape[0])])
            np.testing.assert_allclose(stage,expected,rtol=1e-14,atol=1e-14);previous=stage
        return stages
    def test_full_scalar_stencil_and_pass_order(self):
        geo=fixture();image=np.arange(63,dtype=float).reshape(7,9)**2
        self.compare_scalar(geo,image)
    def test_constant(self):
        geo=fixture();result=self.compare_scalar(geo,np.full((7,9),.003));np.testing.assert_allclose(result,.003,rtol=1e-14)
    def test_zero(self):
        result=self.compare_scalar(fixture(),np.zeros((7,9)));self.assertTrue((result==0).all())
    def test_convex_range(self):
        geo=fixture();image=np.arange(63,dtype=float).reshape(7,9);out=self.compare_scalar(geo,image)
        self.assertTrue((out>=0).all() and (out<=62).all())
    def barrier(self,kind):
        geo=list(fixture());pos,n,hit,mat=geo
        if kind=='miss':hit[:,4]=False
        elif kind=='material':mat[:,4]=1
        elif kind=='normal':n[:,4]=[0,1,0]
        elif kind=='plane':pos[:,4,2]=.1
        image=np.zeros((7,9));image[:,5:]=1
        stages=self.compare_scalar(geo,image)
        # No single tap may jump the thin column, even at strides2/4.
        self.assertTrue((stages[:,:,:4]==0).all())
    def test_miss_segment_barrier(self):self.barrier('miss')
    def test_material_segment_barrier(self):self.barrier('material')
    def test_normal_segment_barrier(self):self.barrier('normal')
    def test_plane_segment_barrier(self):self.barrier('plane')
    def test_miss_output_zero(self):
        geo=list(fixture());geo[2][3,4]=False;out=self.compare_scalar(geo,np.ones((7,9)));self.assertTrue((out[:,3,4]==0).all())
    def test_single_pixel_viewport(self):
        geo=fixture(1,1);out=self.compare_scalar(geo,np.array([[7.]]));np.testing.assert_array_equal(out,7.)
    def test_invalid_geometry(self):
        geo=list(fixture());geo[1][0,0]=[0,0,2]
        with self.assertRaises(ValueError):B.geometry_masks(*geo,1e-5)
    def test_nonfinite_geometry(self):
        geo=list(fixture());geo[0][0,0,0]=np.nan
        with self.assertRaises(ValueError):B.geometry_masks(*geo,1e-5)
    def test_invalid_epsilon(self):
        for epsilon in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):B.geometry_masks(*fixture(),epsilon)
    def test_radiance_and_mask_rejection(self):
        masks=B.geometry_masks(*fixture(),1e-5)
        for value in (-1,float('nan'),float('inf')):
            image=np.zeros((7,9));image[0,0]=value
            with self.assertRaises(ValueError):B.reconstruct(image,masks)
        with self.assertRaises(ValueError):B.reconstruct(np.ones((7,9)),masks[:2])
    def test_quality_inclusive_and_bias_conjunction(self):
        def comp(t=.05,i=.1,b=.05):return {k:dict(pixels=57600,scoring_exclusions=0,nrmse=(t if k=='total' else i),signed_sum_bias=b,whole_image_max_absolute=.1) for k in ('direct','indirect','total')}
        c=comp();self.assertTrue(B.quality(c));rows=[dict(spp=16,components=c),dict(spp=1,components=comp(i=.11))]
        self.assertEqual(B.decision(rows,c),dict(first_passing_spp=16,reference_bias_pass=True,pass_=True))
        self.assertFalse(B.decision(rows,comp(b=np.nextafter(.05,1)))['pass_'])
        for c in (comp(t=np.nextafter(.05,1)),comp(i=np.nextafter(.1,1)),comp(b=-np.nextafter(.05,1))):self.assertFalse(B.quality(c))
    def test_undefined_metric_rejection(self):
        c={k:dict(pixels=57600,scoring_exclusions=0,nrmse=.01,signed_sum_bias=0.,whole_image_max_absolute=0.) for k in ('direct','indirect','total')}
        c['total']['nrmse']=None
        with self.assertRaises(ValueError):B.quality(c)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Contracts);result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(actual_new_contract_tests=result.testsRun,pass_=result.wasSuccessful())))
    raise SystemExit(0 if result.wasSuccessful() else 1)

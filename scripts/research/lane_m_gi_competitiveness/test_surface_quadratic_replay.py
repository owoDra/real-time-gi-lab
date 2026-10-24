"""019 new CPU intake/audit numerical and ordered-stop contracts; no M001 run."""
import argparse
import json
from pathlib import Path
import unittest
import numpy as np
import surface_quadratic_replay as T
import surface_quadratic_replay_audit as A

OUT=None


def fixture(h=11,w=11):
    y,x=np.indices((h,w),dtype=np.float32);g=np.zeros((h,w,8),dtype=np.float32);g[...,0]=x;g[...,1]=y;g[...,6]=1
    raw=np.zeros((h,w,8),dtype=np.uint32);raw[...,7]=1
    return g,raw.reshape(-1,8)


def centre_fields(g,raw):
    masks=A.masks_float32(g,raw,1e-5);hit=raw[:,7].reshape(g.shape[:2])==1
    c=np.zeros(masks.shape,dtype=np.float32);c[:,12]=hit
    maps=np.zeros((6,)+hit.shape,dtype=np.uint32)
    maps[:3]=np.sum(masks.astype(np.uint32)*(np.uint32(1)<<np.arange(25,dtype=np.uint32))[None,:,None,None],axis=1,dtype=np.uint32)
    maps[3:,hit]=np.uint32((1<<8)|(1<<16));maps[3:,~hit]=255
    return c,maps,masks,hit


def rows(**changes):
    values=[dict(name=name,pass_=True) for name in T.NAMES]
    for row in values:
        if row['name'] in changes:row['pass_']=changes[row['name']]
    return values


class Contracts(unittest.TestCase):
    def test_fixed_selected_rung_no_upward_rescue(self):
        self.assertFalse(T.decision('H01',2,rows(n16=False,n64=True))['pass_'])
    def test_fixed_selected_rung_no_lower_rung_rescue(self):
        self.assertFalse(T.decision('H01',8,rows(n16=True,n64=False))['pass_'])
    def test_reference_bias_conjunction(self):
        values=rows();values[0]['pass_']=False;self.assertFalse(T.decision('H03',8,values)['pass_'])
    def test_no_missing_or_reordered_rows(self):
        with self.assertRaises(ValueError):T.decision('H01',2,rows()[:-1])
        with self.assertRaises(ValueError):T.decision('H01',2,list(reversed(rows())))
    def test_first_target_has_no_predecessor(self):
        self.assertEqual(T.previous_gate('H01',2,OUT/'absent'),{})
    def test_missing_previous_audit_stops(self):
        with self.assertRaises(FileNotFoundError):T.previous_gate('H01',8,OUT/'absent')
    def prior(self,name,pass_=True):
        root=OUT/name;root.mkdir();native=root/'native';native.mkdir();T.G.write(native/'result.json',dict(complete=True,valid=True,payload_sha256={}))
        audit=root/(T.tag('H01',2)+'-terminal-audit-v1');audit.mkdir();values=rows(n16=pass_)
        r=dict(complete=True,valid=True,source_commit=T.G.head(),decision=T.decision('H01',2,values),rows=values,payload_sha256={},native_receipt=str(native/'result.json'),native_receipt_sha256=T.C.sha(native/'result.json'))
        T.G.write(audit/'result.json',r);return root,native,audit
    def test_failed_previous_science_stops(self):
        root,_,_=self.prior('failed-prior',False)
        with self.assertRaises(ValueError):T.previous_gate('H01',8,root)
    def test_valid_previous_evidence_is_pinned(self):
        root,native,audit=self.prior('valid-prior');inputs=T.previous_gate('H01',8,root)
        self.assertEqual(inputs[str(native/'result.json')],T.C.sha(native/'result.json'));self.assertEqual(inputs[str(audit/'result.json')],T.C.sha(audit/'result.json'))
    def test_previous_native_drift_stops(self):
        root,native,_=self.prior('drift-prior');(native/'result.json').write_text('{}')
        with self.assertRaises(ValueError):T.previous_gate('H01',8,root)
    def test_previous_extra_inventory_stops(self):
        root,_,audit=self.prior('extra-prior');(audit/'extra').write_text('unregistered')
        with self.assertRaises(ValueError):T.previous_gate('H01',8,root)
    def test_real_new_root_refuses_overwrite_and_outside(self):
        with self.assertRaises(ValueError):T.P.new_root(OUT)
        with self.assertRaises(ValueError):T.P.new_root(Path('/tmp/q019-outside'))
    def test_ordered_camera_independent_known_value(self):
        camera=np.array([1,2,3,1e-4,0,0,1,100,1,0,0,1,0,1,0,1,1e-5,5,1,1],dtype=np.float32)
        hit=np.zeros((1,8),dtype=np.uint32);hit[0,2]=np.float32(1).view(np.uint32);hit[0,3]=np.float32(2).view(np.uint32);hit[0,7]=1
        a=dict(camera=camera,hits=hit);expected=A.expected_geometry(a)
        np.testing.assert_array_equal(expected[0,0],[1,2,5,0,0,0,-1,0]);self.assertEqual(A.geometry_health(expected,a)['normal_max_unit_error'],0)
        broken=expected.copy();broken[0,0,0]+=1
        with self.assertRaises(ValueError):A.geometry_health(broken,a)
    def test_float32_segment_barriers_not_hopped(self):
        for kind in ('material','normal','plane','miss'):
            g,raw=fixture();r=raw.reshape(11,11,8)
            if kind=='material':r[:,5,5]=1
            elif kind=='normal':g[:,5,6]=0;g[:,5,5]=1
            elif kind=='plane':g[:,5,2]=.01
            else:r[:,5,7]=0;g[:,5]=0
            m=A.masks_float32(g,raw,1e-5)
            self.assertFalse(m[0,14,4,4]);self.assertFalse(m[1,13,4,4]);self.assertFalse(m[2,13,4,4])
    def test_coefficient_norm_l1_rejected_and_finite(self):
        g,raw=fixture();c,m,masks,hit=centre_fields(g,raw);A.coefficient_health(c,m,masks,hit)
        for kind in ('norm','l1','rejected','nonfinite'):
            bad=c.copy()
            if kind=='norm':bad[0,12,4,4]=1.001
            elif kind=='l1':bad[0,12,4,4]=4;bad[0,13,4,4]=-3
            elif kind=='rejected':bad[0,0,0,0]=.1
            else:bad[0,12,4,4]=np.nan
            with self.assertRaises(ValueError):A.coefficient_health(bad,m,masks,hit)
    def test_mask_and_selector_malformed(self):
        g,raw=fixture();c,m,masks,hit=centre_fields(g,raw)
        for index,value in ((0,0),(3,1<<24)):
            bad=m.copy();bad[index,4,4]=value
            with self.assertRaises(ValueError):A.coefficient_health(c,bad,masks,hit)
    def test_same_accepted_taps_svd_polynomial_moments(self):
        g,raw=fixture();m=A.masks_float32(g,raw,1e-5);m[0,0,4,4]=False;hit=raw[:,7].reshape(11,11)==1
        c,model,bits,selected=A.svd_coefficients(g[...,:3],g[...,4:7],hit,m[0],4,4,1)
        self.assertEqual((model,bits,selected),(0,63,63));self.assertEqual(c[0],0)
        delta=np.array([[dx,dy] for dy in range(-2,3) for dx in range(-2,3)],dtype=float)
        basis=np.stack([np.ones(25),delta[:,0],delta[:,1],delta[:,0]**2,delta[:,0]*delta[:,1],delta[:,1]**2])
        np.testing.assert_allclose(basis@c,[1,0,0,0,0,0],rtol=0,atol=1e-12)
    def test_svd_rank_reduction_and_analytic_miss(self):
        g,raw=fixture(1,9);m=A.masks_float32(g,raw,1e-5);hit=np.ones((1,9),dtype=bool)
        c,model,bits,selected=A.svd_coefficients(g[...,:3],g[...,4:7],hit,m[0],0,4,1)
        self.assertEqual((model,bits,selected),(0,11,11));self.assertAlmostEqual(float(c.sum()),1)
        hit[:]=False;c,model,bits,selected=A.svd_coefficients(g[...,:3],g[...,4:7],hit,m[0],0,4,1)
        self.assertEqual((model,bits,selected),(255,0,0));self.assertTrue((c==0).all())
    def test_ordered_float32_stage_and_signed_negative(self):
        image=np.zeros((5,5),dtype=np.float32);image[2,3]=1;c=np.zeros((25,5,5),dtype=np.float32);c[12]=1;c[13,2,2]=-.25
        raw=A.replay_stage(image,c,1);self.assertEqual(raw.dtype,np.float32);self.assertEqual(float(raw[2,2]),-.25);self.assertEqual(float(np.maximum(raw,0)[2,2]),0)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();OUT=T.P.new_root(a.out);suite=unittest.defaultTestLoader.loadTestsFromTestCase(Contracts);count=suite.countTestCases();r=unittest.TextTestRunner(verbosity=2).run(suite)
    record=dict(schema='m001-q019-cpu-rehearsal-intake-audit-tests/1',complete=r.wasSuccessful(),actual_new_contract_tests=count,gpu_executed=False,m001_rehearsals_executed=0,source_commit=T.G.head(),input_sha256={str(p):T.C.sha(p) for p in T.OWN})
    T.G.write(OUT/'result.json',record);print(json.dumps(record,indent=2));raise SystemExit(0 if record['complete'] else 1)

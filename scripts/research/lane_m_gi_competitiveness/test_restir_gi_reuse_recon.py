"""043 CPU contracts for reusing the fixed 018/022 reconstruction on 042 frames."""
import unittest
import numpy as np
import geometry_barrier_filter as B
import restir_gi_reuse_recon as X


def coefficients(value=None):
    c=np.zeros((3,25,180,320));center=[j for j,(dy,dx,_) in enumerate(B.OFFSETS) if dy==0 and dx==0][0]
    if value is None:c[:,center]=1
    else:c[:]=value
    return c,center


class Contracts(unittest.TestCase):
    def test_partition_of_unity_preserves_constant(self):
        c,_=coefficients(1/25);img=np.full((180,320),.37);out,clip=X.recon(img,c)
        inner=out[16:-16,16:-16];self.assertTrue(np.allclose(inner,.37,rtol=1e-12));self.assertEqual([x['negative_pixels'] for x in clip],[0,0,0])

    def test_identity_coefficients_are_exact(self):
        c,_=coefficients();img=np.random.default_rng(5).random((180,320));out,_=X.recon(img.ravel(),c);self.assertTrue(np.array_equal(out,img))

    def test_negative_preclip_values_are_clipped_and_reported(self):
        c,center=coefficients();c[0,center]=-1;img=np.ones((180,320));out,clip=X.recon(img,c)
        self.assertTrue((out==0).all());self.assertEqual(clip[0]['negative_pixels'],57600);self.assertEqual(clip[1]['negative_pixels'],0)

    def test_scoring_uses_direct_plus_reconstructed_indirect(self):
        ref={k:np.full((180,320),1.) for k in ('direct','indirect','total')};ref['total']=ref['total']*2
        m=X.Q.score(np.ones(57600,np.float32),np.full(57600,1.05),ref)
        self.assertAlmostEqual(m['indirect']['signed_sum_bias'],.05);self.assertAlmostEqual(m['total']['nrmse'],.025)

    def test_evaluation_windows_are_registered(self):
        imgs=np.zeros((4,64,57600,4),np.float32);imgs[...,0]=1;imgs[...,1]=1;imgs[...,2]=1
        c,_=coefficients();ref={k:np.full((180,320),1.) for k in ('direct','indirect')};ref['total']=np.full((180,320),2.)
        summary,rows,clip=X.evaluate(imgs,c,ref)
        self.assertEqual(len(rows),4*2*17);self.assertEqual(sorted({r['frame'] for r in rows}),[0,*range(48,64)])
        self.assertTrue(summary['r1_target_pass'] and summary['r1_pt_target_pass']);self.assertEqual(summary['r2_streams_passing'],{'v1_null_trial':4,'pt':4})


if __name__=='__main__':
    unittest.main()

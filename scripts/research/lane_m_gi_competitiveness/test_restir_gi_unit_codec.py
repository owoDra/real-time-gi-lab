"""041 new unit/codec contracts; no previous successful suite rerun."""
import unittest
import numpy as np
import restir_gi_unit_codec as C
import restir_gi_unit_model as M
from test_restir_gi_local_bridge import fixture as old_fixture


def fixture():
    a=old_fixture();a[8]['radiance']=C.encode(a[7]['radiance_trial'][:,:3]*C.UNIT)
    rgb=C.decode(a[8]['radiance']);cosine=a[9][:,4,1];weight=a[8]['weight']
    color=rgb*cosine[:,None]/M.PI*weight[:,None];a[9][:,3,:3]=color;a[9][:,5,:3]=a[0][:,0,None]+color
    return a


class Contracts(unittest.TestCase):
    def test_exact_black_bin(self):
        values=np.repeat(np.array([C.BLACK_BOUND*.99,C.BLACK_BOUND*1.01],C.F)[:,None],3,axis=1)
        codes=C.encode(values)
        self.assertEqual(codes[0],0);self.assertGreater(codes[1],0)

    def test_scaled_low_signal_and_black(self):
        rgb=np.full((3,3),np.array([0,1e-8,1e-7])[:,None],C.F)
        decoded=C.decode(C.encode(rgb*C.UNIT));self.assertTrue((np.abs(decoded-rgb)<=C.budget(rgb)).all())
        self.assertTrue((decoded[0]==0).all());self.assertTrue((C.D.decode(C.encode(rgb))[2]==0).all())
        a=fixture();a[6]['direction_direct'][0,1,3]=0;a[0][0,1]=a[1][0,1]=0
        a[0][0,2]=a[1][0,2]=a[0][0,0];a[4][:]=a[5][:]=0;a[7]['radiance_trial'][0,:3]=0;a[8]['radiance']=0
        a[9][0,[0,3],:3]=0;a[9][0,[2,5],:3]=a[0][0,0]
        _,summary=M.audit(*a);self.assertEqual(summary['black_secondary_hits'],1)
        self.assertEqual(C.encode(np.zeros((1,3),C.F))[0],0)

    def test_power_of_two_units_roundtrip(self):
        values=np.geomspace(1e-12,C.UPPER,2048).astype(C.F)
        self.assertTrue(np.array_equal(values*C.UNIT/C.UNIT,values))
        self.assertEqual(2**int(np.ceil(np.log2(C.BLACK_BOUND/2e-8))),64)

    def test_uncompressed_physical_shading_and_full_model(self):
        a=fixture();_,summary=M.audit(*a);self.assertEqual(summary['secondary_hits'],1)
        li=C.F(.0000231);cosine=C.F(.137);weight=C.F(7.3)
        self.assertEqual(li*cosine*weight,(li*C.UNIT*cosine*weight)/C.UNIT)

    def test_grid_boundary_fields(self):
        grid=C.critical_grid();self.assertEqual(grid[0],0);self.assertGreater(len(grid),30000)
        self.assertTrue((grid==C.F(1e-6)).any());self.assertTrue((grid==C.F(C.UPPER)).any())

    def test_finite_depth_upper_headroom(self):
        self.assertLess(C.UPPER*float(C.UNIT),143)
        code=C.encode(np.full((1,3),C.F(C.UPPER)*C.UNIT,C.F))
        self.assertLess(int(code[0]>>18),16383)

    def test_actual_underflow_and_unexpected_corruption(self):
        rgb=np.full((2,3),C.F(1e-7));bad,why=C.underflow_failures(rgb,np.array([0,0xffffffff],C.U))
        self.assertTrue(bad.all());self.assertTrue(why[0]);self.assertFalse(why[1])

    def test_reversible_private_shader_and_model_delta(self):
        source=C.shader(C.L.G.HLSL.read_bytes());self.assertIn(b'radiance_trial.xyz*64.0',source);self.assertIn(b')/64.0;',source)
        a=fixture();a[8]['misc']=0
        with self.assertRaisesRegex(ValueError,'packed M'):M.audit(*a)


if __name__=='__main__':unittest.main()

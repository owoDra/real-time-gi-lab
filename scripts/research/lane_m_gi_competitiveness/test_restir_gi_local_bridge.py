"""040 new local representation contracts; old fixtures reused, not old tests."""
import unittest
import numpy as np
import restir_gi_local_model as M
import restir_gi_local_overlay as O
from test_restir_gi_gpu_bridge import fixture as old_fixture


def fixture():
    a=old_fixture();w=a[6]
    local=np.zeros((1,4),M.F);local[:,:3]=w['direction_direct'][:,1,:3]*w['origin_t'][:,1,3,None];local[:,3]=w['origin_t'][:,1,3]
    a[8]['position']=local[:,:3]
    cosine=M.norm(local[:,:3].astype(float))[:,2];weight=a[8]['weight'].astype(float)
    for base,rgb in ((0,a[7]['radiance_trial'][:,:3].astype(float)),(3,M.D.decode(a[8]['radiance']).astype(float))):
        color=rgb*cosine[:,None]/np.pi*weight[:,None]
        a[9][:,base,:3]=color;a[9][:,base+1,1]=cosine;a[9][:,base+2,:3]=a[0][:,0,None]+color
    return a+[local]


class Contracts(unittest.TestCase):
    def test_reversible_actual_sources(self):
        producer=O.producer(O.P.O.PT.read_bytes());host=O.host(O.G.CPP.read_bytes());shader=O.shader(O.G.HLSL.read_bytes())
        self.assertIn(b'continuation_t*wi,continuation_t',producer)
        self.assertIn(b'local-endpoints.f32',host);self.assertIn(b'0xa040a040u',host)
        self.assertIn(b'RTXDI_MakeGIReservoir(localEndpoints[pixel].xyz',shader)
        self.assertIn(b'float3 delta=localEndpoint',shader)

    def test_binary_abi_and_new_streams(self):
        self.assertEqual((M.WITNESS.itemsize,M.CANDIDATE.itemsize,M.D.PACKED.itemsize),(80,128,32))
        self.assertEqual(np.zeros((1,4),M.F).nbytes,16)
        self.assertEqual(M.SEEDS[0],0x12345678^0xa040a040)

    def test_full_physical_local_recovery(self):
        fields,summary=M.audit(*fixture());self.assertEqual(summary['secondary_hits'],1)
        self.assertIn('absolute_direction_failed',fields);self.assertIn('local_endpoint',fields)

    def test_black_hit_keeps_m1(self):
        a=fixture();a[6]['direction_direct'][0,1,3]=0;a[0][0,1]=a[1][0,1]=0
        a[0][0,2]=a[1][0,2]=a[0][0,0];a[4][:]=a[5][:]=0;a[7]['radiance_trial'][0,:3]=0;a[8]['radiance']=0
        a[9][0,[0,3],:3]=0;a[9][0,[2,5],:3]=a[0][0,0]
        _,summary=M.audit(*a);self.assertEqual(summary['black_secondary_hits'],1)

    def test_miss_empty_keeps_raw_trial(self):
        a=fixture();a[6]['origin_t'][0,1,3]=0;a[6]['direction_direct'][0,1,3]=0
        a[6]['position_primitive'][0,1]=[0,0,0,np.array(0xffffffff,M.U).view(M.F)]
        a[6]['normal_kind'][0,1]=[0,0,0,np.array(1,M.U).view(M.F)];a[6]['spawn_front'][0,1]=0
        a[0][0,1]=a[1][0,1]=0;a[0][0,2]=a[1][0,2]=a[0][0,0];a[4][:]=a[5][:]=0
        a[7]['normal_status'][0,3]=np.array(1,M.U).view(M.F);a[7]['endpoint_primitive'][0]=0;a[7]['endpoint_normal'][0]=0;a[7]['radiance_trial'][0,:3]=0
        a[8][:]=np.zeros(1,M.D.PACKED);a[9][:]=0;a[9][0,[2,5],:3]=a[0][0,0];a[9][0,[2,5],3]=1;a[-1][:]=0
        _,summary=M.audit(*a);self.assertEqual(summary['secondary_misses'],1)

    def test_corrupt_local_direction_and_t_fail(self):
        a=fixture();a[-1][0,0]*=-1
        with self.assertRaisesRegex(ValueError,'actual sampled ray'):M.audit(*a)
        a=fixture();a[-1][0,3]=np.nextafter(a[-1][0,3],M.F(np.inf))
        with self.assertRaisesRegex(ValueError,'actual intersection t'):M.audit(*a)

    def test_corrupt_packed_local_position_fails(self):
        a=fixture();a[8]['position'][0,0]=np.nextafter(a[8]['position'][0,0],M.F(np.inf))
        with self.assertRaisesRegex(ValueError,'packed endpoint exact'):M.audit(*a)

    def test_known_short_ray_is_origin_independent(self):
        wi=np.array([[-.6903072595596313,.2926149368286133,-.6617040634155273]],M.F);t=M.F(.001237379154190421)
        delta=wi*t;expected=M.norm(delta.astype(float))
        self.assertTrue(np.isclose(expected,wi,rtol=3e-4,atol=3e-6).all())
        origin=np.full((1,3),M.F(1e6));lost=(origin+delta)-origin
        self.assertEqual(float(np.linalg.norm(lost)),0)
        self.assertGreater(float(np.linalg.norm(delta)),.001)
        self.assertTrue(np.array_equal(delta,wi*t))


if __name__=='__main__':unittest.main()

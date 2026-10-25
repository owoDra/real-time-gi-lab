"""037 new physical float32 bridge contracts; no old successful suite rerun."""
import unittest
import numpy as np
import restir_gi_gpu_model as M
import restir_gi_gpu_overlay as O


def fixture():
    """One actual physical two-sided secondary HIT with a finite lit suffix."""
    f=M.F;seed=M.SEEDS[0]
    triangle=np.array([[[-100,-100,0],[100,-100,0],[0,100,0]],[[-100,-100,1],[0,100,1],[100,-100,1]]],f)
    metadata=np.array([[100,0xffffffff,3,1],[101,0xffffffff,3,1]],M.U)
    p=np.zeros((8,4),f);p[0,:3]=[0,0,.5];p[1]=[1,0,0,1];p[2]=[0,1,0,1];p[3]=[0,0,-1,100];p[5]=[0,0,.25,1]
    p.view(M.U)[6]=[2,1,1,0]
    w=np.zeros((1,2),M.WITNESS);c=np.zeros(1,M.CANDIDATE)
    w['origin_t'][0,0]=[0,0,.5,.5];w['direction_direct'][0,0,:3]=[0,0,-1]
    w['position_primitive'][0,0,3]=np.array(0,M.U).view(f);w['normal_kind'][0,0]=[0,0,1,np.array(2,M.U).view(f)]
    start=M.spawn(np.array([[0,0,0]],f),np.array([[0,0,1]],f))[0]
    w['spawn_front'][0,0,:3]=start;w['spawn_front'][0,0,3]=np.array(1,M.U).view(f)
    wi,rng=M.direction(np.array([[0,0,1]],f),M.mix32(np.array([seed],M.U)));wi=wi[0];t=f((1-start[2])/wi[2]);endpoint=start+wi*t;endpoint[2]=1
    w['origin_t'][0,1,:3]=start;w['origin_t'][0,1,3]=t;w['direction_direct'][0,1,:3]=wi
    w['position_primitive'][0,1,:3]=endpoint;w['position_primitive'][0,1,3]=np.array(1,M.U).view(f)
    w['normal_kind'][0,1]=[0,0,-1,np.array(2,M.U).view(f)]
    second=M.spawn(endpoint[None],np.array([[0,0,-1]],f))[0];w['spawn_front'][0,1,:3]=second;w['spawn_front'][0,1,3]=np.array(1,M.U).view(f)
    for vertex in range(2):
        lv=p[5,:3].astype(float)-w['spawn_front'][0,vertex,:3].astype(float);d2=np.dot(lv,lv);normal=w['normal_kind'][0,vertex,:3]
        w['direction_direct'][0,vertex,3]=f(max(0,np.dot(normal,lv/np.sqrt(d2)))/(np.pi*(1+d2)))
    direct=w['direction_direct'][0,0,3];suffix=w['direction_direct'][0,1,3]
    image=np.array([[direct,suffix,direct+suffix,1]],f);hits=np.zeros((1,8),M.U)
    hits[0,:3]=np.array([0,0,1],f).view(M.U);hits[0,3]=np.array(.5,f).view(M.U);hits[0,4:7]=metadata[0,:3];hits[0,7]=1
    c['origin_pdf'][0]=[*start,wi[2]/M.PI];c['normal_status'][0]=[0,0,1,np.array(2,M.U).view(f)]
    c['endpoint_primitive'][0]=[*endpoint,np.array(1,M.U).view(f)];c['endpoint_normal'][0]=[0,0,-1,0]
    c['radiance_trial'][0]=[suffix,suffix,suffix,1];c['direction_cosine'][0]=[*wi,wi[2]];c['primary_direct'][0]=[0,0,0,direct];c['flags'][0,0]=rng[0]
    # Independently fixed LogLuv quantization for neutral white/grey.
    xyz=np.array([.9504559270516716,1,1.0890577507598784])*float(suffix);den=xyz[0]+15*xyz[1]+3*xyz[2]
    uv=np.array([4*xyz[0],9*xyz[1]])/den
    le=int(np.clip((np.log2(xyz[1])+20)*409.6,0,16383));uvq=np.clip(uv*820,0,511).astype(np.uint32)
    code=(le<<18)|(int(uvq[0])<<9)|int(uvq[1])
    packed=np.zeros(1,M.D.PACKED);packed['position']=endpoint;packed['misc']=1;packed['radiance']=code;packed['weight']=f(1)/c['origin_pdf'][0,3];packed['normal']=0x7fff7fff
    delta=endpoint.astype(float)-start;cosine=delta[2]/np.linalg.norm(delta);weight=float(packed['weight'][0]);decoded=M.D.decode(packed['radiance'])[0]
    output=np.zeros((1,6,4),f)
    for base,rgb in ((0,np.full(3,float(suffix))), (3,decoded*cosine/np.pi*weight)):
        output[0,base]=[*rgb,1];output[0,base+1]=[weight,cosine,1,1];output[0,base+2]=[*(direct+rgb),1]
    return [image,image.copy(),hits,hits.copy(),image[:,1].copy(),image[:,1].copy(),w,c,packed,output,triangle,p.tobytes(),seed,metadata]


class Contracts(unittest.TestCase):
    def test_actual_reversible_overlay(self):
        original=O.O.PT.read_bytes();a=O.producer(original)
        self.assertIn(b'float reflected=direct_light',a);self.assertIn(b'Witness witnesses[]',a)
        self.assertEqual(a,O.producer(original));self.assertEqual(original,O.O.PT.read_bytes())

    def test_binary_abi(self):
        self.assertEqual((M.WITNESS.itemsize,M.CANDIDATE.itemsize,M.D.PACKED.itemsize),(80,128,32))
        self.assertEqual([M.CANDIDATE.fields[x][1] for x in M.CANDIDATE.names],list(range(0,128,16)))

    def test_float_spawn(self):
        p=np.array([[1,-1,0]],M.F);n=np.array([[1,-1,1]],M.F);actual=M.spawn(p,n)
        self.assertEqual(actual[0,0].view(M.U)-p[0,0].view(M.U),4)
        self.assertEqual(actual[0,1].view(M.U)-p[0,1].view(M.U),4)
        self.assertEqual(actual[0,2],M.F(1e-7))

    def test_actual_two_vertex_physical_recovery(self):
        arrays,summary=M.audit(*fixture());self.assertEqual(summary['secondary_hits'],1);self.assertEqual(arrays['status'][0],2)

    def test_black_hit_retains_m1(self):
        a=fixture();a[6]['direction_direct'][0,1,3]=0;a[0][0,1]=a[1][0,1]=0
        a[0][0,2]=a[1][0,2]=a[0][0,0];a[4][:]=a[5][:]=0;a[7]['radiance_trial'][0,:3]=0;a[8]['radiance']=0
        a[9][0,[0,3],:3]=0;a[9][0,[2,5],:3]=a[0][0,0]
        _,summary=M.audit(*a);self.assertEqual(summary['black_secondary_hits'],1)

    def test_original_parity_failure(self):
        a=fixture();a[1][0,1]=np.nextafter(a[1][0,1],M.F(np.inf))
        with self.assertRaisesRegex(ValueError,'bit-exact'):M.audit(*a)

    def test_raw_trial_and_m_cannot_be_confused(self):
        a=fixture();a[6]['origin_t'][0,1,3]=0;a[6]['direction_direct'][0,1,3]=0
        a[6]['position_primitive'][0,1]=[0,0,0,np.array(0xffffffff,M.U).view(M.F)]
        a[6]['normal_kind'][0,1]=[0,0,0,np.array(1,M.U).view(M.F)];a[6]['spawn_front'][0,1]=0
        a[0][0,1]=a[1][0,1]=0;a[0][0,2]=a[1][0,2]=a[0][0,0];a[4][:]=a[5][:]=0
        a[7]['normal_status'][0,3]=np.array(1,M.U).view(M.F);a[7]['endpoint_primitive'][0]=0;a[7]['endpoint_normal'][0]=0;a[7]['radiance_trial'][0,:3]=0
        a[8][:]=np.zeros(1,M.D.PACKED);a[9][:]=0;a[9][0,[2,5],:3]=a[0][0,0];a[9][0,[2,5],3]=1
        _,summary=M.audit(*a);self.assertEqual(summary['secondary_misses'],1)
        a=fixture();a[7]['radiance_trial'][0,3]=0
        with self.assertRaisesRegex(ValueError,'raw trial'):M.audit(*a)
        a=fixture();a[8]['misc']=0
        with self.assertRaisesRegex(ValueError,'packed M'):M.audit(*a)

    def test_visibility_and_primary_double_count_fail(self):
        a=fixture();a[9][0,1,3]=0
        with self.assertRaisesRegex(ValueError,'visibility'):M.audit(*a)
        a=fixture();a[9][0,2,:3]+=a[0][0,0]
        with self.assertRaisesRegex(ValueError,'primary once'):M.audit(*a)


if __name__=='__main__':unittest.main()

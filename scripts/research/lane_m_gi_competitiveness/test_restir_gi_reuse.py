"""042 CPU contracts: frame transforms, null trials, replay primitives and independent visibility."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import numpy as np
import restir_gi_device_model as D
import restir_gi_reuse_model as R

F=np.float32
BASE=Path(__file__).resolve().parents[3]/'out/research/lane-m-gi-competitiveness'


def bank(positions,owners,misc=1,weight=1.,code=0x4000000,normal=0):
    r=np.zeros(R.PITCH,R.PACKED);o=np.zeros((R.PITCH,4),F);n=len(positions)
    r['position'][:n]=positions;r['misc'][:n]=misc;r['weight'][:n]=weight;r['radiance'][:n]=code;r['normal'][:n]=normal;o[:n,:3]=owners
    return R.Bank(r,o)


class SyntheticFrame:
    """Flat receivers on z=0 facing +z with a shared sample cloud; no geometry occludes."""
    def __init__(self,valid=None):
        n=R.N;x,y=np.arange(n)%R.W,np.arange(n)//R.W;self.cur=np.zeros(n,R.SURFACE)
        self.cur['origin'][:,0]=x*F(.01);self.cur['origin'][:,1]=y*F(.01);self.cur['normal'][:,2]=1;self.cur['depth']=5;self.cur['valid']=1 if valid is None else valid;self.cur['primitive']=7
        self.prev=self.cur.copy();self.frame_index=4096+3;self.uniform=int(R.jenkins(self.frame_index))
        self.reservoirs=np.zeros((6,R.PITCH),R.PACKED);self.owners=np.zeros((6,R.PITCH,4),F);self.history={}
    def set(self,array,P,local,M,weight,code,normal):
        ptr=R.pointer(P%R.W,P//R.W);self.reservoirs[array][ptr]=0;self.reservoirs[array]['position'][ptr]=local;self.reservoirs[array]['misc'][ptr]=M
        self.reservoirs[array]['weight'][ptr]=weight;self.reservoirs[array]['radiance'][ptr]=code;self.reservoirs[array]['normal'][ptr]=normal;self.owners[array][ptr,:3]=self.cur['origin'][P]
    def bank(self,variant,stage):
        if stage=='history':return self.history[variant]
        a=variant*3+{'initial':0,'temporal':1,'spatial':2}[stage];return R.Bank(self.reservoirs[a],self.owners[a])


def no_occluder(viewer,receiver,point,mask):
    n=len(mask);return np.ones(n,bool),np.zeros(n,bool),np.ones(n,bool)


class Contracts(unittest.TestCase):
    def test_self_transform_is_bit_exact_and_neighbor_transform_registered(self):
        rng=np.random.default_rng(42);local=rng.normal(size=(64,3)).astype(F);owners=(rng.normal(size=(64,3))*50).astype(F)
        b=bank(local,owners);ptr=np.arange(64)
        self_load=b.load(ptr,owners);self.assertTrue(np.array_equal(R.bits(self_load['pos']),R.bits(local)))
        receiver=(owners+rng.normal(size=(64,3)).astype(F)*F(.1)).astype(F);moved=b.load(ptr,receiver)
        expected=((owners-receiver).astype(F)+local).astype(F)
        self.assertTrue(np.array_equal(R.bits(moved['pos']),R.bits(expected)))
        exact=owners.astype(float)+local-receiver;self.assertLess(np.abs(moved['pos']-exact).max(),1e-4)

    def test_rng_matches_qualified034_sampler_and_sdk_pass_constant(self):
        a=D.Random(17,9,5,-33+12);b=R.Rng(np.arange(153)%17,np.arange(153)//17,5,12)
        for _ in range(4):self.assertTrue(np.array_equal(a.next(),b.next()))
        c=R.Rng([3],[4],7,12);c.next(np.array([0]));self.assertEqual(int(c.index[0]),1)

    def test_reservoir_addresses_match_qualified033_host_maps(self):
        path=BASE/'m001-restir033-cpu-build-v3/host-data/addresses-320x180-0.u32'
        actual=np.fromfile(path,'<u4');x,y=np.arange(R.N)%R.W,np.arange(R.N)//R.W
        self.assertTrue(np.array_equal(actual,np.concatenate((R.pointer(x,y,0),R.pointer(x,y,1)))))
        self.assertEqual((R.ROW,R.PITCH),(5120,61440))

    def test_offset_temporal_pattern_mirror_and_permutation(self):
        pattern={i:R.temporal_offset(i,1) for i in range(8)}
        grid={(-1,-1):0,(1,1):1,(-1,1):2,(1,-1):3,(0,-1):4,(0,1):5,(-1,0):6,(1,0):7}
        for i,(dx,dy) in pattern.items():self.assertEqual(grid[(int(dx),int(dy))],i)
        x,y=R.mirror(np.array([-1,-640,319,320,700]),np.array([-1,0,179,180,-361]))
        self.assertEqual(x.tolist(),[0,0,319,319,60]);self.assertEqual(y.tolist(),[0,0,179,179,0])
        px,py=R.permute(np.array([0,5]),np.array([0,9]),0b0110);self.assertEqual((px.tolist(),py.tolist()),([-1,2],[1,8]))
        raw=np.fromfile(BASE/'m001-restir033-cpu-build-v3/host-data/neighbor-offsets.u8',np.int8).reshape(8192,2)
        decoded=np.maximum(raw.astype(F)/F(127),F(-1));d=(decoded*F(32)).astype(np.int64);self.assertLessEqual(int(np.abs(d).max()),32)

    def test_zero_contribution_rule_and_jacobian_bounds(self):
        ok,j,near=R.validate(np.array([25.,.05,2.,10.,.1]),np.array([True,False,False,False,False]))
        self.assertEqual(ok.tolist(),[True,False,True,True,True]);self.assertEqual(j.tolist(),[1.,1/3,2.,3.,1/3]);self.assertEqual(near.tolist(),[False,False,False,True,True])
        j=R.jacobian(np.zeros((1,3)),np.array([[0.,0.,0.]]),np.array([[0.,0.,1.]],F),np.array([[0.,0.,-1.]],F));self.assertEqual(j.tolist(),[1.])
        j=R.jacobian(np.zeros((1,3)),np.array([[0.,0.,0.]]),np.array([[0.,0.,0.]],F),np.array([[0.,0.,-1.]],F));self.assertEqual(j.tolist(),[0.])

    def test_target_requires_facing_sample_and_positive_cosine(self):
        pos=np.array([[0,0,1],[0,0,1],[0,0,-1],[1,0,1e-9]],F);nrm=np.array([[0,0,-1],[0,0,1],[0,0,1],[0,0,-1]],F)
        t=R.target(pos,np.array([1.,1.,1.,1.]),nrm,np.zeros((4,3),F),np.tile(np.array([0,0,1],F),(4,1)))
        self.assertAlmostEqual(t[0],1/np.pi);self.assertEqual(t[1:3].tolist(),[0.,0.]);self.assertLess(t[3],1e-8)

    def test_null_trial_is_counted_in_temporal_normalization(self):
        fr=SyntheticFrame();P=np.array([1000]);n0=R.encode_normal(np.array([[0,0,-1]],F))[0]
        from restir_gi_unit_codec import encode
        lit=int(encode(np.array([[64.,64.,64.]],F))[0])
        hist_r=np.zeros(R.PITCH,R.PACKED);hist_o=np.zeros((R.PITCH,4),F);ptr=R.pointer(P%R.W,P//R.W)
        hist_r['position'][ptr]=(0,0,1);hist_r['misc'][ptr]=4;hist_r['weight'][ptr]=2.;hist_r['radiance'][ptr]=lit;hist_r['normal'][ptr]=n0;hist_o[ptr,:3]=fr.cur['origin'][P]
        fr.history={0:R.Bank(hist_r,hist_o),1:R.Bank(hist_r,hist_o)}
        fr.set(0,P,fr.cur['normal'][P],0x10001,0.,0,R.encode_normal(-fr.cur['normal'][P]))
        null=R.temporal(fr,0,P,no_occluder);m0=R.temporal(fr,1,P,no_occluder)
        self.assertEqual((int(null['M'][0]),int(m0['M'][0])),(5,4))
        p=R.target(np.array([[0,0,1]],F),D.decode(np.array([lit],np.uint32)).astype(float)@R.LUMA,np.array([[0,0,-1]],F),np.zeros((1,3),F),np.array([[0,0,1]],F))[0]
        self.assertAlmostEqual(null['W'][0],2.*4/5,places=6);self.assertAlmostEqual(m0['W'][0],2.,places=6);self.assertGreater(p,0)

    def test_spatial_replay_counts_only_validated_neighbors(self):
        fr=SyntheticFrame();from restir_gi_unit_codec import encode
        lit=int(encode(np.array([[64.,64.,64.]],F))[0]);n0=R.encode_normal(np.array([[0,0,-1]],F))[0];P=np.arange(R.N)
        local=np.zeros((R.N,3),F);local[:,2]=1;fr.set(1,P,local,1,1.,lit,n0)
        offsets=np.zeros((8192,2),F);e=R.spatial(fr,0,P[:64],no_occluder,offsets)
        self.assertTrue((e['M']==3).all());self.assertTrue(np.allclose(e['W'],1.,rtol=1e-6))

    def test_independent_visibility_tool_classes(self):
        tool=Path(os.environ.get('RESTIR042_TOOL',''))
        if not tool.is_file():self.skipTest('built only by registered preparation')
        with tempfile.TemporaryDirectory() as t:
            t=Path(t);g=np.zeros(2,np.dtype([('v','<f4',(3,3)),('m','<u4',4)]));g['v'][0]=((-1,-1,1),(1,-1,1),(0,2,1));g['v'][1]=((5,5,5),(6,5,5),(5,6,5))
            (t/'g.bin').write_bytes(np.array([1,2],np.uint32).tobytes()+g.tobytes())
            q=np.zeros(5,R.QUERY);q['direction'][:,2]=1;q['tmax']=[2,.5,2,2,1.00000001];q['origin'][3]=(1,-1,0);q['origin'][4]=(0,0,0);q['ignore']=[9,9,0,9,9]
            (t/'q.bin').write_bytes(q.tobytes());run=subprocess.run([str(tool),'--triangles',str(t/'g.bin'),'--queries',str(t/'q.bin'),'--out',str(t/'r.bin')],capture_output=True,text=True)
            self.assertEqual(run.returncode,0);r=np.fromfile(t/'r.bin',np.uint8)
            self.assertEqual(r.tolist(),[7,0,0,6,6])

    def test_agreement_detects_each_reservoir_field(self):
        raw=np.zeros(1,R.PACKED);raw['position']=(1,2,3);raw['misc']=2|(3<<8);raw['weight']=.5;raw['radiance']=0;raw['normal']=0
        e=dict(pos=np.array([[1,2,3]],F),M=np.array([2]),age=np.array([3]),W=np.array([.5]),code=np.array([0],np.uint32),ncode=np.array([0],np.uint32))
        ok,_=R.agree(e,raw);self.assertTrue(ok[0])
        for field,value in (('position',(1,2,4)),('misc',2|(4<<8)),('weight',.6),('unused',1.)):
            bad=raw.copy();bad[field]=value;self.assertFalse(R.agree(e,bad)[0][0],field)

    def test_registered_seed_formula(self):
        self.assertEqual(R.producer_seed(0,0),(0x0a420000*0x9e3779b1&0xffffffff)^0xa042a042)
        self.assertNotEqual(R.producer_seed(0,1),R.producer_seed(1,0))
        self.assertEqual(len({R.producer_seed(s,f) for s in range(20) for f in range(64)}),1280)

    def test_normal_code_roundtrip_within_one_step(self):
        rng=np.random.default_rng(3);n=rng.normal(size=(4096,3)).astype(F);n/=np.linalg.norm(n,axis=1)[:,None];code=R.encode_normal(n)
        self.assertTrue(R.snorm_close(R.encode_normal(R.M.decode_normal(code)),code).all())
        self.assertEqual(int(R.encode_normal(np.zeros((1,3),F))[0]),0)


if __name__=='__main__':
    unittest.main()

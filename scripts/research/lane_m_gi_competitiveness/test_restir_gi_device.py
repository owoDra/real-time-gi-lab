"""034 new CPU contracts. No Vulkan initialization; old033 suite is not imported/run."""
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import unittest
from unittest.mock import patch
import numpy as np
import restir_gi_device_model as M
import restir_gi_device_audit as A
import restir_gi_device_build as D
import restir_gi_device_process as P


class DeviceControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build=Path(os.environ['RESTIR034_TEST_BUILD']);cls.out=cls.build/'new-test-evidence';cls.out.mkdir()
        cls.offsets=(D.OLD/'host-data/neighbor-offsets.u8').read_bytes()

    def test_abi_and_full_address_bijection(self):
        self.assertEqual((M.PACKED.itemsize,M.SURFACE.itemsize),(32,48))
        for w,h in M.DIMENSIONS:
            pitch,row,index=M.layout(w,h);self.assertEqual(len(np.unique(index)),w*h);self.assertTrue((index<pitch).all())
            for y in range(h):
                for x in range(w):self.assertEqual(int(index[y*w+x]),(y//16)*row+(x//16)*256+(y%16)*16+x%16)

    def test_exact_fixture_fields(self):
        for w,h in M.DIMENSIONS:
            root=self.build/f'inputs-{w}x{h}'
            for c in range(8):
                p=root/f'fixture-{c}';surface=np.fromfile(p/'binding-1.bin',M.SURFACE);raw=np.fromfile(p/'binding-3.bin','<f4').reshape(-1,3,4)
                self.assertEqual(len(surface),w*h);self.assertTrue((surface['valid']==1).all());self.assertTrue((surface['material']==0xffffffff).all())
                self.assertTrue((raw[:,0,:3]==surface['position']+[0,0,1]).all())
                self.assertTrue((raw[:,1,2]==(1 if c==4 else -1)).all())
                if c==2:self.assertEqual(raw[:,2,:3].tobytes(),bytes(w*h*12));self.assertTrue((raw[:,0,3]==0).all())
                if c==5:self.assertEqual((p/'binding-2.bin').read_bytes(),bytes(w*h*48))
                if c==6:self.assertTrue((np.fromfile(p/'binding-2.bin',M.SURFACE)['material']==0).all())
                self.assertEqual([len((p/f'binding-{j}.bin').read_bytes()) for j in (6,7,8,9)],[32,32,48,80])
                self.assertEqual(struct.unpack_from('<I',(p/'binding-9.bin').read_bytes(),76)[0],1)

    def test_rng_against_scalar_integer_reference(self):
        mask=(1<<32)-1
        def rotate(x,n):return ((x<<n)|(x>>(32-n)))&mask
        for variant in range(6):
            rng=M.Random(17,9,1,variant);actual=[rng.next(),rng.next()]
            for y in range(9):
                for x in range(17):
                    morton=sum(((x>>b)&1)<<(2*b) | ((y>>b)&1)<<(2*b+1) for b in range(16))
                    v=(morton+0x7ed55d16+(morton<<12))&mask;v=(v^0xc761c23c^(v>>19))&mask
                    v=(v+0x165667b1+(v<<5))&mask;v=((v+0xd3a2646c)^(v<<9))&mask
                    v=(v+0xfd7046c5+(v<<3))&mask;v=(v^0xb55a4f09^(v>>16))&mask
                    seed=(v+1+(33+variant)*31)&mask
                    for draw in range(2):
                        k=rotate(((draw+1)*0xcc9e2d51)&mask,15)*0x1b873593&mask
                        v=(rotate(seed^k,13)*5+0xe6546b64)&mask;v^=4;v^=v>>16;v=v*0x85ebca6b&mask;v^=v>>13;v=v*0xc2b2ae35&mask;v^=v>>16
                        self.assertEqual(float(actual[draw][y*17+x]),(v&0x7fffff)/8388608.)

    def test_mirror_neighbors_and_snrom_offsets(self):
        table=np.frombuffer(self.offsets,np.int8).reshape(8192,2).astype(M.F)/M.F(127)
        starts=np.arange(153,dtype=np.int32)*19
        for offset in (0,1,6,7):
            actual=M.neighbors(17,9,starts,offset,table)
            for p,found in enumerate(actual):
                d=[math.trunc(float(t*M.F(32))) for t in table[(starts[p]+offset)&8191]]
                q=[]
                for a,delta,size in zip((p%17,p//17),d,(17,9)):
                    t=(a+delta)%(size*2);q.append(min(t,size*2-1-t))
                self.assertEqual(int(found),q[1]*17+q[0])

    def test_decode_against_scalar_xyz_reference(self):
        codes=np.array([0,1,0x7fffffff,0x80000000,0x943abcde,0x54321fff],np.uint32);actual=M.decode(codes)
        for code,rgb in zip(codes,actual):
            code=int(code);le=code>>18
            if not le:np.testing.assert_array_equal(rgb,[0,0,0]);continue
            y=2**((le+.5)/409.6-20);u=(((code>>9)&511)+.5)/820;v=((code&511)+.5)/820
            den=6*u-16*v+12;x=9*u/den;cy=4*v/den;X=x*y/cy;Z=(1-x-cy)*y/cy
            expected=np.maximum([3.240969941904522*X-1.537383177570094*y-.4986107602930032*Z,-.9692436362808803*X+1.875967501507721*y+.04155505740717569*Z,.05563007969699373*X-.2039769588889765*y+1.056971514242878*Z],0)
            np.testing.assert_allclose(rgb,expected,rtol=2e-5,atol=2e-6)

    def test_candidate_denominators_and_rejections(self):
        w,h=17,9;n=w*h;raw=np.fromfile(self.build/'inputs-17x9/fixture-0/binding-3.bin','<f4').reshape(n,3,4)
        source=np.zeros(n,M.PACKED);source['weight']=M.PI;source['misc']=4|(1<<8)
        for variant,expected in ((1,9),(2,9),(3,5),(4,5),(5,13)):
            pool=M.candidates(source,raw,w,h,0,variant,1,self.offsets);m,_=M.expected_candidates(pool,0,variant);self.assertTrue((m==expected).all())
        for case in (4,5,6,7):
            for variant in (3,4,5):
                pool=M.candidates(source,raw,w,h,case,variant,1,self.offsets);m,_=M.expected_candidates(pool,case,variant)
                self.assertTrue((m==1).all())
        pool=[dict(rgb=np.ones((n,3),M.F),weight=np.full(n,M.PI),m=np.ones(n,np.uint32),age=np.zeros(n,np.uint32),valid=np.ones(n,bool),origin='current'),dict(rgb=np.ones((n,3),M.F),weight=np.full(n,M.PI),m=np.full(n,2,np.uint32),age=np.ones(n,np.uint32),valid=np.ones(n,bool),origin='neighbor')]
        m,c=M.expected_candidates(pool,0,1);self.assertTrue((m==3).all());np.testing.assert_allclose(c[0]['weight'],M.PI)
        _,c=M.expected_candidates(pool,3,2);np.testing.assert_allclose(c[0]['weight'],3*M.PI);self.assertTrue((c[1]['weight']==0).all())

    def test_full_pixel_audit_detects_state_weight_and_rgb_corruption(self):
        n=153;raw=np.fromfile(self.build/'inputs-17x9/fixture-2/binding-3.bin','<f4').reshape(n,3,4)
        data=np.zeros(n,M.PACKED);data['position']=raw[:,0,:3];data['normal']=0x7fff7fff;data['misc']=1
        results=np.zeros((n,2,4),M.F);results[:,0,3]=1;pool=M.candidates(data,raw,17,9,2,0,0,self.offsets)
        self.assertTrue(A.pixel_audit(data,results,raw,pool,2,0)[0])
        for field,value in [('misc',2),('weight',1),('normal',0),('radiance',0x80000000)]:
            altered=data.copy();altered[field][-1]=value;self.assertFalse(A.pixel_audit(altered,results,raw,pool,2,0)[0])
        altered=results.copy();altered[-1,0,0]=1;self.assertFalse(A.pixel_audit(data,altered,raw,pool,2,0)[0])

    def test_exclusive_order_and_no_gpu_plan_validation(self):
        root=self.out/'exclusive';root.mkdir();(root/'plan.json').write_text('{}');P.pristine(root)
        (root/'gpu.stdout').write_text('partial')
        with self.assertRaises(ValueError):P.pristine(root)
        with self.assertRaises(ValueError):P.root_for('16x9')
        with patch.object(P.B,'read',return_value=dict(complete=False,all_pass=False,classification='INVALID')):
            with self.assertRaises(ValueError):P.previous('320x180')
        self.assertEqual(P.previous('17x9'),{})

    def test_native_invalid_cli_and_overwrite_under_unusable_icd(self):
        exe=str(self.build/'device-controls');source=str(self.build/'inputs-17x9');existing=self.build/'cpu-17x9'
        env=dict(os.environ,VK_DRIVER_FILES='/034-no-driver.json',VK_ICD_FILENAMES='/034-no-driver.json')
        cases=[[],['--gpu'],['--wrong','--input',source,'--out',str(self.out/'bad-mode'),'--shaders',str(D.OLD)],['--cpu-check','--input',source,'--out',str(existing),'--shaders',str(D.OLD)]]
        evidence=[]
        for args in cases:
            p=subprocess.run([exe,*args],env=env,capture_output=True,text=True,timeout=10);self.assertNotEqual(p.returncode,0);self.assertNotIn('Vulkan',p.stderr);evidence.append(dict(args=args,returncode=p.returncode,stderr=p.stderr))
        (self.out/'negative-cli.json').write_text(json.dumps(evidence,indent=2))

    def test_native_invalid_metadata_and_sizes_before_output_creation(self):
        target=self.out/'invalid-inputs';shutil.copytree(self.build/'inputs-17x9',target)
        original=(target/'meta.u32').read_bytes();evidence=[]
        for name in ('dimension','size'):
            if name=='dimension':(target/'meta.u32').write_bytes(struct.pack('<II',18,9))
            else:(target/'meta.u32').write_bytes(original);(target/'fixture-7/binding-8.bin').write_bytes(b'bad')
            output=self.out/('rejected-'+name);args=[str(self.build/'device-controls'),'--cpu-check','--input',str(target),'--out',str(output),'--shaders',str(D.OLD)]
            p=subprocess.run(args,capture_output=True,text=True,timeout=10);self.assertNotEqual(p.returncode,0);self.assertFalse(output.exists());evidence.append(dict(args=args,returncode=p.returncode,stderr=p.stderr))
        (self.out/'negative-input.json').write_text(json.dumps(evidence,indent=2))


if __name__=='__main__':unittest.main()

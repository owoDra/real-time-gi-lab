"""027 adversarial reflection/layout and independent geometry controls."""
import copy
import json
import struct
import tempfile
import unittest
from pathlib import Path
import numpy as np
import nrd_semantics_audit as A

def fixture():
    camera=np.zeros(20);camera[3]=.1;camera[4:7]=[0,0,1];camera[7]=100;camera[8:11]=[1,0,0];camera[11]=1;camera[12:15]=[0,1,0];camera[15]=1;camera[18:20]=2
    hits=np.zeros(4,dtype=A.M.GPU_DTYPE);hits['n']=[0,0,1];hits['t']=2*np.sqrt(1.5);hits['flag']=1
    projection=np.array([[1,0,0,0],[0,1,0,0],[0,0,100/99.9,-10/99.9],[0,0,1,0]],dtype=float)
    values=dict(gRectSizeInv=np.array([.5,.5]),gDenoisingRange=100.,gWorldToClip=projection,gWorldToClipPrev=projection.copy())
    for prefix in ['g','gPrev']:
        values.update({prefix+'FrustumForward':np.array([0,0,1,0]),prefix+'FrustumRight':np.array([1,0,0,0]),prefix+'FrustumUp':np.array([0,1,0,0])})
    return [camera,hits,np.full(4,2.),np.full(4,512|(512<<10)|(1023<<20),dtype='<u4'),np.zeros((4,4)),values]

def actual_spirv():return (A.BASE/'m001-nrd026-gpu-h01-b2-n1-v1/capture/pipelines/9.spv').read_bytes()

def mutate_instruction(raw,op,predicate,change):
    w=list(struct.unpack('<'+'I'*(len(raw)//4),raw));at=5
    while at<len(w):
        n=w[at]>>16
        if w[at]&65535==op and predicate(w[at+1:at+n]):
            change(w,at);return struct.pack('<'+'I'*len(w),*w)
        at+=n
    raise AssertionError('mutation instruction absent')

class Reflection(unittest.TestCase):
    def test_actual_common_members_have_independent_known_offsets(self):
        x=A.reflect(actual_spirv())['fields']
        self.assertEqual([x[k]['offset'] for k in ['gFrustumRight','gFrustumUp','gFrustumForward']],[272,288,304])
        self.assertEqual(x['gWorldToClip']['bytes'],64)
    def test_truncation_rejected(self):
        with self.assertRaises(ValueError):A.reflect(actual_spirv()[:-1])
    def test_wrong_magic_rejected(self):
        with self.assertRaises(ValueError):A.reflect(bytes(4)+actual_spirv()[4:])
    def test_zero_instruction_rejected(self):
        raw=actual_spirv()
        with self.assertRaises(ValueError):A.reflect(raw[:20]+bytes(4)+raw[24:])
    def test_changed_constant_binding_rejected(self):
        raw=mutate_instruction(actual_spirv(),71,lambda a:a[1:]==[33,2],lambda w,i:w.__setitem__(i+3,19))
        with self.assertRaises(ValueError):A.reflect(raw)
    def test_missing_matrix_major_rejected(self):
        raw=mutate_instruction(actual_spirv(),72,lambda a:a[2] in (4,5),lambda w,i:w.__setitem__(i+3,99))
        with self.assertRaises(ValueError):A.reflect(raw)
    def test_out_of_record_offset_rejected(self):
        layout=dict(fields=dict(value=dict(kind='float',count=1,bytes=4,offset=4)))
        with self.assertRaises(ValueError):A.field(bytes(4),layout,'value')
    def test_actual_row_and_column_major_memory_mean_different_matrices(self):
        data=np.arange(16,dtype='<f4').tobytes();f=dict(kind='matrix',count=16,bytes=64,offset=0,major='row');layout=dict(fields=dict(matrix=f))
        row=A.field(data,layout,'matrix');f['major']='column';column=A.field(data,layout,'matrix')
        np.testing.assert_array_equal(row,np.arange(16).reshape(4,4));np.testing.assert_array_equal(column,row.T)
    def test_nonfinite_constant_rejected(self):
        with self.assertRaises(ValueError):A.field(struct.pack('<f',float('nan')),dict(fields=dict(x=dict(kind='float',count=1,bytes=4,offset=0))),'x')

class Geometry(unittest.TestCase):
    def test_known_noncentral_physical_projection(self):
        metrics,maps=A.geometry(*fixture(),width=2,height=2)
        self.assertTrue(metrics['pass_']);np.testing.assert_allclose(maps['sdk_camera_relative_position'],[[-1,1,2],[1,1,2],[-1,-1,2],[1,-1,2]],atol=1e-12)
    def test_mirrored_y_rejected(self):
        x=fixture();x[-1]['gFrustumUp']=-x[-1]['gFrustumUp'];r,_=A.geometry(*x,width=2,height=2);self.assertFalse(r['checks']['position'])
    def test_transposed_projection_rejected(self):
        x=fixture();x[-1]['gWorldToClip']=x[-1]['gWorldToClip'].T;r,_=A.geometry(*x,width=2,height=2);self.assertFalse(r['checks']['gWorldToClip'])
    def test_swapped_primary_normal_rejected(self):
        x=fixture();x[1]['n']=[1,0,0];r,_=A.geometry(*x,width=2,height=2);self.assertFalse(r['checks']['normal'])
    def test_corrupt_material_rejected(self):
        x=fixture();x[3][0]|=1<<30;r,_=A.geometry(*x,width=2,height=2);self.assertFalse(r['checks']['material'])
    def test_corrupt_roughness_rejected(self):
        x=fixture();x[3][0]=512|(512<<10)|(767<<20);r,_=A.geometry(*x,width=2,height=2);self.assertFalse(r['checks']['roughness'])
    def test_sky_domain_and_nonzero_motion_controls(self):
        x=fixture();x[1]['flag'][0]=0;x[2][0]=200;r,_=A.geometry(*x,width=2,height=2);self.assertTrue(r['pass_']);self.assertEqual(r['sky_pixels'],1)
        x[4][0,0]=.01;r,_=A.geometry(*x,width=2,height=2);self.assertFalse(r['checks']['static_motion'])
    def test_sky_inside_range_rejected(self):
        x=fixture();x[1]['flag'][0]=0;r,_=A.geometry(*x,width=2,height=2);self.assertFalse(r['checks']['positive_viewz'])
    def test_existing_output_and_wrong_root_rejected(self):
        with self.assertRaises(ValueError):A.bounds(A.BASE)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):A.bounds(Path(directory)/'new-output')

if __name__=='__main__':unittest.main()

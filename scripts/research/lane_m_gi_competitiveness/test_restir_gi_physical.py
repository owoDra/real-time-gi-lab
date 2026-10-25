"""035 new tests for physical observer and independent record rejection. CPU only."""
import math
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import numpy as np
import restir_gi_physical_overlay as O
import restir_gi_physical_model as M
import restir_gi_physical_process as P


def fixture(miss=False,sky=False,black=False):
    vertices=np.array([[[-10,-10,0],[10,-10,0],[0,10,0]],[[-10,-10,1],[10,-10,1],[0,10,1]]],float)
    offset=1e-12*np.linalg.norm(vertices.max(axis=(0,1))-vertices.min(axis=(0,1)))
    original=np.zeros(1,M.RESULT);primary=original['primary'];primary['t']=-1 if sky else .5;primary['tri']=0xffffffff if sky else 0;primary['front']=0 if sky else 1
    records=np.zeros((1,2),M.VERTEX);r=records[0,0];r['ray_origin']=[0,0,.5];r['direction']=[0,0,-1];r['kind']=1 if sky else 2
    packet=np.zeros(1,M.PACKET);packet['trials']=1
    if not sky:
        r['t']=.5;r['triangle']=0;r['front']=1;r['normal']=[0,0,1];r['spawn']=[0,0,offset];r['reflected']=[.25]*3;original['components'][:,1]=.25
        s=records[0,1];s['ray_origin']=r['spawn'];s['direction']=[0,0,1];s['kind']=1 if miss else 2
        packet['receiver']=r['spawn'];packet['normal']=r['normal'];packet['status']=1 if miss else 2
        if not miss:
            s['t']=1-offset;s['triangle']=1;s['hit_position']=[0,0,1];s['nudged']=[0,0,1];s['spawn']=[0,0,1-offset];s['normal']=[0,0,-1];s['reflected']=[0 if black else .5]*3
            original['components'][:,2]=s['reflected'];packet['endpoint']=s['hit_position'];packet['endpoint_normal']=s['normal'];packet['radiance']=s['reflected'];packet['pdf']=1/math.pi;packet['sdk_m']=1
    return original,original.copy(),records,packet,vertices,offset,primary.copy()


class PhysicalExtraction(unittest.TestCase):
    def test_private_observation_inverse_and_signature(self):
        raw=O.ORIGINAL.read_bytes();data,proof=O.overlay(raw);self.assertTrue(proof['exact_inverse']);self.assertNotEqual(data,raw)
        self.assertIn(b'PathVertex* observations = nullptr',data)
        with self.assertRaises(ValueError):O.overlay(raw.replace(b'class Oracle {',b'class Missing {'))

    def test_binary_layouts(self):self.assertEqual([M.RESULT.itemsize,M.VERTEX.itemsize,M.PACKET.itemsize],[152,192,144])

    def test_hit_recovers_finite_suffix_without_primary_direct(self):
        arrays,row=M.audit_records(*fixture());np.testing.assert_allclose(arrays['recovered'],[[.5]*3]);self.assertEqual(row['secondary_hits'],1);self.assertEqual(row['backfacing_hits'],1)

    def test_miss_keeps_trial_but_official_m_zero(self):
        arrays,row=M.audit_records(*fixture(miss=True));self.assertEqual(row['secondary_misses'],1);self.assertEqual(arrays['trial_count'][0],1);self.assertEqual(arrays['sdk_m'][0],0);self.assertTrue((arrays['recovered']==0).all())

    def test_black_hit_is_distinct_from_miss(self):
        arrays,row=M.audit_records(*fixture(black=True));self.assertEqual(row['black_secondary_hits'],1);self.assertEqual(arrays['sdk_m'][0],1);self.assertTrue((arrays['recovered']==0).all())

    def test_invalid_primary_has_no_secondary_slot(self):
        arrays,row=M.audit_records(*fixture(sky=True));self.assertEqual(row['primary_invalid'],1);self.assertEqual(row['visited_slots'],1);self.assertEqual(arrays['status'][0],0)

    def test_original_rng_counter_and_direct_corruption_rejected(self):
        for name in ('rng','counts','components'):
            data=list(fixture());data[1][name].flat[-1]=17
            with self.assertRaises(ValueError):M.audit_records(*data)

    def test_wrong_endpoint_normal_origin_pdf_and_denominator_rejected(self):
        for name in ('endpoint','endpoint_normal','receiver','pdf','sdk_m','trials','radiance'):
            data=list(fixture());data[3][name].flat[-1]=2
            with self.assertRaises(ValueError):M.audit_records(*data)

    def test_unvisited_miss_and_finite_vertex_corruption_rejected(self):
        for name,value in [('normal',1),('reflected',1),('t',float('nan'))]:
            data=list(fixture(sky=True));data[2][name][0,1]=value
            with self.assertRaises(ValueError):M.audit_records(*data)

    def test_order_requires_previous_complete_audit(self):
        self.assertEqual(P.previous('H01',2),{})
        with patch.object(P.B,'read',return_value=dict(complete=False,all_pass=False,classification='INVALID')):
            with self.assertRaises(ValueError):P.previous('H01',8)
        with self.assertRaises(ValueError):P.canonical('H04',2)

    def test_native_malformed_cli_never_initializes_gpu_or_overwrites(self):
        build=Path(os.environ['RESTIR035_TEST_BUILD']);out=build/'new-negative-cli.json';records=[]
        for args in ([],['--gpu'],['--scene','/035-missing-scene','--out',str(build)],['--scene','/035-missing-scene','--out',str(build/'rejected')]):
            result=subprocess.run([str(build/'physical-extract'),*args],capture_output=True,text=True,timeout=10)
            self.assertNotEqual(result.returncode,0);self.assertNotIn('Vulkan',result.stderr);self.assertFalse((build/'rejected').exists());records.append(dict(args=args,returncode=result.returncode,stderr=result.stderr))
        P.C.write(out,records)


if __name__=='__main__':unittest.main()

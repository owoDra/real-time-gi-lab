#!/usr/bin/env python3
"""CPU-only synthetic tests. These NEVER prove historical GPU causation."""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from component_contract import analyze, checked_file, primary_comparison, INVALID, SEEDS

def pfm(w,h,value):
    return f'PF\n{w} {h}\n-1.0\n'.encode()+struct.pack('<3f',value,value,value)*w*h
def hit_bytes(n,present=True):
    return (struct.pack('<4f4I',0,0,1,2,7,2,3,1) if present else
            struct.pack('<4f4I',0,0,0,float('inf'),INVALID,INVALID,INVALID,0))*n

class ComponentContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.w,self.h=4,3
        self.frame={
            'source_commit':'a'*40,'scene_asset_sha256':'b'*64,
            'frame_state_sha256':'c'*64,'geometry_state_sha256':'d'*64,
            'frame_id':7,'width':self.w,'height':self.h,
            'seeds':SEEDS[:],'spp':512,'backend':'software'
        }
        self.manifest={
            'schema_version':1,'frame':self.frame,
            'cpu_counts':{'primary_hits':12,'secondary_hits':1,
                          'shadow_tested':3,'shadow_blocked':2,
                          'shadow_clear':1,'positive_samples':1},
            'state_files':{},'cpu':{},'gpu':{}
        }
        # CPU serialized triangles: 9 float positions, then 4 identity flags.
        self.cpu_geo=struct.pack('<II9f4I',1,1,
            0,0,0, 1,0,0, 0,1,0, 7,2,3,1)
        self.gpu_geo=struct.pack('<12f4I',
            0,0,0,0, 1,0,0,0, 0,1,0,0, 7,2,3,1)
        for name,raw in (('frame',b'frame state'),('geometry',self.cpu_geo)):
            file=self.root/f'{name}-state.bin'
            file.write_bytes(raw)
            h=hashlib.sha256(raw).hexdigest()
            self.manifest['state_files'][name]={'path':file.name,'sha256':h}
            self.frame['frame_state_sha256' if name=='frame' else 'geometry_state_sha256']=h
        gpu_file=self.root/'gpu_primary_geometry.bin'
        gpu_file.write_bytes(self.gpu_geo)
        self.manifest['state_files']['gpu_primary_geometry']={
            'path':gpu_file.name,'sha256':hashlib.sha256(self.gpu_geo).hexdigest()}
        probe_audit={
            'work_items':1,'gpu_hit_items':1,
            'gpu_positive_contributions':1,
            'gpu_traversal_mismatches':0,
            'gpu_positive_traversal_mismatches':0,
            'gpu_positive_matched_traversal':1,
            'gpu_positive_shadow_blocked':1,
            'gpu_positive_shadow_clear':0,
            'gpu_positive_other_zero':0,
            'gpu_positive_fixed_prediction_mismatches':0,
            'gpu_positive_replay_candidate':1,
            'zero_gpu_but_positive_unshadowed':0,
            'invalid_gpu_hit_flags':0,'invalid_contribution_ids':0}
        self.manifest['probe_work_items']=1
        self.manifest['gpu_probe_audit']=probe_audit
        self.manifest['gpu_probe']={}
        for kind,raw in (
                ('work',bytes(64)),
                ('hits',hit_bytes(1)),
                ('contributions',struct.pack('<2I',0,42)),
                ('audit',json.dumps(probe_audit).encode())):
            filename=self.root/f'gpu_probe_{kind}.bin'
            filename.write_bytes(raw)
            self.manifest['gpu_probe'][kind]={
                'path':filename.name,'sha256':hashlib.sha256(raw).hexdigest()}
        for side in ('cpu','gpu'):
            for part in ('hits','direct','indirect','total'):
                val={'direct':.25,'indirect':.125,'total':.375}.get(part)
                raw=hit_bytes(self.w*self.h) if part=='hits' else pfm(self.w,self.h,val)
                self.set_file(side,part,raw)
        self.save()
    def set_file(self,side,part,raw):
        file=self.root/f'{side}_{part}.{ "bin" if part=="hits" else "pfm" }'
        file.write_bytes(raw)
        self.manifest[side][part]={
            'path':file.name,'sha256':hashlib.sha256(raw).hexdigest()}
    def save(self):
        (self.root/'manifest.json').write_text(json.dumps(self.manifest))
    def go(self):
        self.save()
        return analyze(self.root/'manifest.json')
    def test_matched_not_physical_proof(self):
        r=self.go()
        self.assertTrue(r['primary']['match'])
        self.assertEqual(r['primary']['cpu_hit_pixels'],self.w*self.h)
        self.assertEqual(r['primary']['gpu_hit_pixels'],self.w*self.h)
        self.assertEqual(r['signal']['cpu']['direct']['positive_pixels'],self.w*self.h)
        self.assertEqual(r['signal']['gpu']['indirect']['positive_pixels'],self.w*self.h)
        self.assertTrue(r['reconstruction']['gpu']['passed'])
        self.assertTrue(r['primary_geometry_attestation']['match'])
        self.assertTrue(r['probe_shadow_replay_testable'])
        self.assertTrue(r['gpu_probe_shadowed_positive_detected'])
        self.assertTrue(r['indirect_model_difference_testable'])
        self.assertFalse(r['physical_correctness_proven'])
        self.assertFalse(r['cross_device_state_independently_verified'])
    def test_independent_primary_triangle_device_attestation(self):
        r=self.go()
        self.assertTrue(r['primary_geometry_attestation']['match'])
        self.assertEqual(r['primary_geometry_attestation']['checked_triangles'],1)
        self.assertEqual(r['primary_geometry_attestation']['mismatched_triangles'],0)
    def test_forged_uploaded_geometry_blocks_attribution(self):
        raw=bytearray(self.gpu_geo)
        raw[0]^=0x1
        file=self.root/'gpu_primary_geometry.bin'
        file.write_bytes(raw)
        self.manifest['state_files']['gpu_primary_geometry']['sha256']=hashlib.sha256(raw).hexdigest()
        result=self.go()
        self.assertFalse(result['primary_geometry_attestation']['match'])
        self.assertFalse(result['indirect_model_difference_testable'])
        self.assertIn('gpu_primary_triangle_bytes_mismatch',result['blockers'])
    def test_missing_device_geometry_is_rejected(self):
        del self.manifest['state_files']['gpu_primary_geometry']
        with self.assertRaisesRegex(ValueError,'raw state snapshots'):self.go()
    def test_probe_audit_mismatch_fail_closed(self):
        self.manifest['gpu_probe_audit']['gpu_positive_contributions']=2
        with self.assertRaisesRegex(ValueError,'hashed file'):self.go()
    def test_probe_payload_tamper_rejected(self):
        (self.root/'gpu_probe_contributions.bin').write_bytes(bytes(8))
        with self.assertRaisesRegex(ValueError,'SHA mismatch'):self.go()
    def test_probes_invalid_shadow_sum_rejected(self):
        self.manifest['gpu_probe_audit']['gpu_positive_shadow_blocked']=2
        raw=json.dumps(self.manifest['gpu_probe_audit']).encode()
        file=self.root/'gpu_probe_audit.bin'
        file.write_bytes(raw)
        self.manifest['gpu_probe']['audit']['sha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError,'shadow counts invalid'):self.go()
    def test_indirect_mismatch_is_diagnostic(self):
        self.set_file('gpu','indirect',pfm(self.w,self.h,.25))
        self.set_file('gpu','total',pfm(self.w,self.h,.5))
        r=self.go()
        self.assertTrue(r['indirect_mismatch_detected'])
        self.assertFalse(r['historical_causation_proven'])
    def test_primary_mismatch_blocks_attribution(self):
        self.set_file('gpu','hits',hit_bytes(self.w*self.h,False))
        r=self.go()
        self.assertFalse(r['primary']['match'])
        self.assertEqual(r['primary']['gpu_hit_pixels'],0)
        self.assertEqual(r['primary']['mask_mismatches'],self.w*self.h)
        self.assertFalse(r['indirect_model_difference_testable'])
        self.assertIn('primary_hit_mismatch',r['blockers'])
    def test_reconstruction_mismatch_blocks_attribution(self):
        self.set_file('gpu','total',pfm(self.w,self.h,.7))
        r=self.go()
        self.assertFalse(r['reconstruction']['gpu']['passed'])
        self.assertIn('component_reconstruction_mismatch',r['blockers'])
    def test_bad_sha_rejected(self):
        (self.root/'cpu_direct.pfm').write_bytes(b'invalid')
        with self.assertRaisesRegex(ValueError,'SHA mismatch'):self.go()
    def test_unfrozen_seed_rejected(self):
        self.frame['seeds'][0]+=1
        with self.assertRaises(ValueError):self.go()
    def test_unbalanced_counters_rejected(self):
        self.manifest['cpu_counts']['shadow_blocked']=99
        with self.assertRaisesRegex(ValueError,'counter invariant'):self.go()
    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            checked_file(self.root,{'path':'../outside','sha256':'0'*64})
    def test_identity_difference_is_visible(self):
        a=(0,0,1,2,7,2,3,1)
        b=(0,0,1,2,8,2,3,1)
        r=primary_comparison([a],[b])
        self.assertEqual(r['identity_mismatches'],1)
        self.assertFalse(r['match'])
    def test_forged_fingerprint_rejected(self):
        self.frame['geometry_state_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'geometry state SHA'):self.go()

if __name__=='__main__':
    unittest.main()

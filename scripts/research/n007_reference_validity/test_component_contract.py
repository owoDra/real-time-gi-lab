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
        for name,raw in (('frame',b'frame state'),('geometry',b'geometry state')):
            file=self.root/f'{name}-state.bin'
            file.write_bytes(raw)
            h=hashlib.sha256(raw).hexdigest()
            self.manifest['state_files'][name]={'path':file.name,'sha256':h}
            self.frame['frame_state_sha256' if name=='frame' else 'geometry_state_sha256']=h
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
        self.assertTrue(r['reconstruction']['gpu']['passed'])
        self.assertTrue(r['indirect_model_difference_testable'])
        self.assertFalse(r['physical_correctness_proven'])
        self.assertFalse(r['cross_device_state_independently_verified'])
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

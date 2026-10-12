#!/usr/bin/env python3
"""CPU-only finite campaign tests; synthetic PFMs are never experimental data."""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_reference_ladder import campaign
from check_convergence import SPP,SEEDS

def pfm(path:Path,positive=True,seed_shift=0):
    path.parent.mkdir(parents=True,exist_ok=True)
    values=[]
    for k in range(320*180):
        value=(0.01+seed_shift*1.e-8) if positive and k<2000 else 0.
        values.extend((value,value,value))
    path.write_bytes(b'PF\n320 180\n-1.0\n'+struct.pack('<%df'%len(values),*values))

class LadderTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.binary=self.root/'mock-cpu-generator'
        self.binary.write_bytes(b'fixture')
        self.manifest={'frame':{
            'backend':'software','spp':512,'seeds':list(SEEDS),
            'scene_asset_sha256':'b'*64,
            'frame_state_sha256':'c'*64,
            'source_commit':'a'*40}}
        (self.root/'component-manifest.json').write_text(json.dumps(self.manifest))
        self.good=True
        self.calls=[]
    def emit(self,positive=True):
        self.good=positive
        for i in range(4):
            pfm(self.root/'cpu'/f'seed-{i}'/'total.pfm',positive,i)
    def fake_native(self,cmd,check):
        self.assertTrue(check)
        self.calls.append(int(cmd[cmd.index('--spp')+1]))
        dest=Path(cmd[cmd.index('--out')+1])
        for i in range(4):
            pfm(dest/f'seed-{i}'/'total.pfm',self.good,i)
    def run_one(self):
        with patch('run_reference_ladder.analyze',return_value={
                'primary':{'match':True},
                'primary_geometry_attestation':{'match':True}}),patch(
                'run_reference_ladder.subprocess.run',side_effect=self.fake_native):
            return campaign(self.root,self.binary)
    def test_two_level_early_stop(self):
        self.emit(True)
        result=self.run_one()
        self.assertEqual(result['eligible_at_spp'],1024)
        self.assertEqual(result['status'],'statistical-screen-pass')
        self.assertEqual(self.calls,[1024])
        self.assertEqual([x['spp'] for x in result['rows']],[512,1024])
        self.assertFalse(result['physical_correctness_proven'])
    def test_black_reference_exhausts_frozen_ladder(self):
        self.emit(False)
        result=self.run_one()
        self.assertEqual(result['status'],'statistical-screen-fail')
        self.assertEqual(self.calls,[1024,2048,4096,8192])
        self.assertEqual([x['spp'] for x in result['rows']],list(SPP))
    def test_completed_result_is_read_only(self):
        self.emit(True)
        first=self.run_one()
        self.calls.clear()
        second=self.run_one()
        self.assertEqual(first['manifest_sha256'],second['manifest_sha256'])
        self.assertEqual(self.calls,[])
    def test_preserve_mismatched_provenance(self):
        self.emit(True)
        self.run_one()
        self.manifest['frame']['source_commit']='d'*40
        (self.root/'component-manifest.json').write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,'different source state'):
            self.run_one()

if __name__=='__main__':
    unittest.main()

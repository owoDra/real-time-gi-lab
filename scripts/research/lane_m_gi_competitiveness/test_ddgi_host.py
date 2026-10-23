#!/usr/bin/env python3
"""CPU contract tests against the actual private native binary, with no Vulkan init."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
NATIVE=None
SOURCE=ROOT/'out/research/lane-m-gi-competitiveness/m001-first-heldout-v1/capture'


class NativeContract(unittest.TestCase):
    def setUp(self):
        if NATIVE is None:self.skipTest('run this native CPU suite with --native PRIVATE_BINARY')
        self.temp=tempfile.TemporaryDirectory(prefix='m001-ddgi-contract-',dir=ROOT/'out')
        self.root=Path(self.temp.name);self.state=self.root/'state'
        shutil.copytree(SOURCE/'M001-H01-hwrt',self.state,ignore=lambda _,names:[n for n in names if n not in ('geometry-state.bin','frame-state.bin')])

    def tearDown(self):self.temp.cleanup()

    def call(self,*extra,state=None,out=None):
        # The CPU branch must work even with no usable ICD. This is not a GPU runtime test.
        env=dict(os.environ,VK_ICD_FILENAMES='/nonexistent/m001-no-icd.json',VK_DRIVER_FILES='/nonexistent/m001-no-icd.json')
        return subprocess.run([str(NATIVE),'--cpu-check','--state',str(state or self.state),'--out',str(out or self.root/'check'),*extra],
                              capture_output=True,text=True,timeout=15,env=env)

    def patch(self,file,offset,fmt,value):
        p=self.state/file;b=bytearray(p.read_bytes());struct.pack_into(fmt,b,offset,value);p.write_bytes(b)

    def test_all_three_original_states_and_depths(self):
        for scene in ('H01','H02','H03'):
            for depth,n in ((1,0),(2,1),(8,7)):
                p=self.call('--vertices',str(depth),'--mode','direct' if depth==1 else 'scene',
                            state=SOURCE/('M001-'+scene+'-hwrt'),out=self.root/(scene+'-'+str(depth)))
                self.assertEqual(p.returncode,0,p.stderr)
                d=json.loads((self.root/(scene+'-'+str(depth))/'cpu-contract.json').read_text())
                self.assertEqual(d['stage_count'],n);self.assertFalse(d['gpu_initialized'])

    def test_actual_maximum_and_partial_final_tile(self):
        p=self.call('--grid-side','23','--rays','512','--vertices','8')
        self.assertEqual(p.returncode,0,p.stderr)
        d=json.loads((self.root/'check/cpu-contract.json').read_text())
        self.assertEqual(d['total_rays_per_stage'],23**3*512)
        self.assertEqual(d['tile_count_per_stage'],(23**3*512+4095)//4096)

    def test_existing_output_bytes_survive_refusal(self):
        out=self.root/'check';out.mkdir();p=out/'sentinel';p.write_bytes(b'prior failed evidence\0')
        before=hashlib.sha256(p.read_bytes()).hexdigest();result=self.call()
        self.assertNotEqual(result.returncode,0);self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),before)
        self.assertEqual(list(out.iterdir()),[p])

    def test_truncated_state_refused_before_output(self):
        p=self.state/'geometry-state.bin';p.write_bytes(p.read_bytes()[:-1]);self.assertNotEqual(self.call().returncode,0)
        self.assertFalse((self.root/'check').exists())

    def test_nonfinite_geometry_refused(self):
        self.patch('geometry-state.bin',8,'<f',float('nan'));self.assertNotEqual(self.call().returncode,0)

    def test_one_sided_and_mismatched_primitive_refused(self):
        self.patch('geometry-state.bin',56,'<I',0);self.assertNotEqual(self.call().returncode,0)
        self.patch('geometry-state.bin',56,'<I',1);self.patch('geometry-state.bin',44,'<I',17);self.assertNotEqual(self.call().returncode,0)

    def test_degenerate_triangle_refused(self):
        p=self.state/'geometry-state.bin';raw=bytearray(p.read_bytes());raw[20:32]=raw[8:20];p.write_bytes(raw)
        self.assertNotEqual(self.call().returncode,0)

    def test_corrupted_frame_and_nonfinite_camera_refused(self):
        self.patch('frame-state.bin',116+4,'<I',9999);self.assertNotEqual(self.call().returncode,0)
        shutil.copyfile(SOURCE/'M001-H01-hwrt/frame-state.bin',self.state/'frame-state.bin')
        self.patch('frame-state.bin',20,'<f',float('inf'));self.assertNotEqual(self.call().returncode,0)

    def test_camera_nonunit_basis_refused(self):
        self.patch('frame-state.bin',36,'<f',12);self.assertNotEqual(self.call().returncode,0)

    def test_unsupported_features_budgets_and_duplicate_options_refused(self):
        for extra in [('--vertices','3'),('--grid-side','25'),('--rays','129'),('--mode','temporal'),('--target-state','x'),
                      ('--rays','-1'),('--rays','128x'),('--rays','4294967296'),('--grid-side','2','--grid-side','3')]:
            self.assertNotEqual(self.call(*extra).returncode,0,extra)

    def test_no_gpu_mode_without_explicit_shader_inputs(self):
        p=subprocess.run([str(NATIVE),'--state',str(self.state),'--out',str(self.root/'check')],capture_output=True,text=True,timeout=15)
        self.assertNotEqual(p.returncode,0);self.assertFalse((self.root/'check').exists())


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--native',type=Path,required=True);args=ap.parse_args();NATIVE=args.native.resolve()
    unittest.main(argv=['test_ddgi_host'],verbosity=2)

"""Native CPU-only persistent-resource transition contracts; no GPU context."""
import argparse
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

import ddgi_dynamic_inputs as D

NATIVE=None


class TransitionContract(unittest.TestCase):
    def setUp(self):
        if NATIVE is None:self.skipTest('run native transition suite with --native PRIVATE_BINARY')
        self.temp=tempfile.TemporaryDirectory(dir=D.R.ROOT/'out');self.root=Path(self.temp.name)
        self.source=D.R.LANE/'capture/M001-H01-hwrt';self.target=self.root/'target';self.target.mkdir()
        self.make_target('light')

    def tearDown(self):self.temp.cleanup()

    def make_target(self,kind):
        g,f=D.derive((self.source/'geometry-state.bin').read_bytes(),(self.source/'frame-state.bin').read_bytes(),kind)
        (self.target/'geometry-state.bin').write_bytes(g);(self.target/'frame-state.bin').write_bytes(f)

    def call(self,*extra,out=None):
        env=dict(os.environ,VK_DRIVER_FILES='/nonexistent/m001-no-icd.json',VK_ICD_FILENAMES='/nonexistent/m001-no-icd.json')
        return subprocess.run([str(NATIVE),'--cpu-check','--state',str(self.source),'--target-state',str(self.target),
            '--history-policy','reset-all','--mode','scene','--vertices','2','--out',str(out or self.root/'check'),*extra],
            capture_output=True,text=True,timeout=15,env=env)

    def test_four_frame_light_and_geometry_schedules(self):
        import json
        for kind in D.KINDS:
            self.make_target(kind);out=self.root/kind;p=self.call(out=out);self.assertEqual(p.returncode,0,p.stderr)
            d=json.loads((out/'transition-contract.json').read_text());n=1224 if kind=='geometry' else 0
            self.assertEqual([x['state_index'] for x in d['frames']],[0,1,1,0])
            self.assertEqual([x['moved_primitives'] for x in d['frames']],[0,n,0,n])
            self.assertTrue(all(x['reset_both_atlases'] for x in d['frames']))
            for k,original in enumerate([self.source,self.target,self.target,self.source]):
                for name in ('geometry-state.bin','frame-state.bin'):self.assertEqual((out/f'frames/{k}'/name).read_bytes(),(original/name).read_bytes())

    def test_b8_finite_schedule_via_actual_cli(self):
        # Separate argv avoids passing duplicate --vertices, which must be refused.
        cmd=[str(NATIVE),'--cpu-check','--state',str(self.source),'--target-state',str(self.target),'--history-policy','reset-all','--mode','scene','--vertices','8','--out',str(self.root/'check')]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=15,env=dict(os.environ,VK_DRIVER_FILES='/nonexistent/m001-no-icd.json'))
        self.assertEqual(p.returncode,0,p.stderr)
        import json
        self.assertTrue(all(x['finite_stages']==7 for x in json.loads((self.root/'check/transition-contract.json').read_text())['frames']))

    def test_noop_and_metadata_changes_refused_before_output(self):
        for name in ('geometry-state.bin','frame-state.bin'):shutil.copyfile(self.source/name,self.target/name)
        self.assertNotEqual(self.call().returncode,0)
        self.make_target('light');p=self.target/'geometry-state.bin';raw=bytearray(p.read_bytes());struct.pack_into('<I',raw,48,123);p.write_bytes(raw)
        self.assertNotEqual(self.call().returncode,0);self.assertFalse((self.root/'check').exists())

    def test_unsupported_history_duplicate_target_and_missing_policy(self):
        for extra in [('--history-policy','reuse'),('--target-state',str(self.source)),('--frames','5'),('--vertices','8')]:
            self.assertNotEqual(self.call(*extra).returncode,0)
        p=subprocess.run([str(NATIVE),'--cpu-check','--state',str(self.source),'--target-state',str(self.target),'--out',str(self.root/'check')],capture_output=True,text=True,timeout=15)
        self.assertNotEqual(p.returncode,0);self.assertFalse((self.root/'check').exists())

    def test_existing_transition_output_preserved(self):
        out=self.root/'check';out.mkdir();(out/'failed.bin').write_bytes(b'old failed evidence')
        self.assertNotEqual(self.call().returncode,0);self.assertEqual((out/'failed.bin').read_bytes(),b'old failed evidence');self.assertEqual(len(list(out.iterdir())),1)

    def test_corrupted_target_refused_before_output(self):
        p=self.target/'geometry-state.bin';p.write_bytes(p.read_bytes()[:-1]);self.assertNotEqual(self.call().returncode,0);self.assertFalse((self.root/'check').exists())


class Factory(unittest.TestCase):
    def test_only_registered_fields_change(self):
        source=D.R.LANE/'capture/M001-H01-hwrt';g=(source/'geometry-state.bin').read_bytes();f=(source/'frame-state.bin').read_bytes()
        lg,lf=D.derive(g,f,'light');self.assertEqual(lg,g);self.assertEqual(lf[:100],f[:100]);self.assertEqual(lf[104:],f[104:])
        gg,gf=D.derive(g,f,'geometry');self.assertEqual(gf,f);self.assertEqual(gg[:8],g[:8])
        for j in range(1224):
            start=8+52*j;self.assertEqual(gg[start+36:start+52],g[start+36:start+52])
            for v in range(3):
                a=start+12*v;self.assertEqual(gg[a+4:a+12],g[a+4:a+12]);expected=struct.pack('<f',struct.unpack_from('<f',g,a)[0]+.127)
                self.assertEqual(gg[a:a+4],expected)

    def test_unregistered_factory_rejected(self):
        with self.assertRaises(ValueError):D.derive(b'',b'','tuned')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--native',type=Path,required=True);a=ap.parse_args();NATIVE=a.native.resolve();unittest.main(argv=['transition-test'],verbosity=2)

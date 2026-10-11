import json
import tempfile
import unittest
from pathlib import Path

import inspect_archive as module
from test_inspect_hdr import make_pfm


class TestArchive(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.archive = self.root / 'gi-lab-old-private'
        self.cap = self.archive / 'out/research/n006-interval-aware-allocation/p1m3b-moving-rigid-q8-signed/UTC/Q8_control_reference'
        self.cap.mkdir(parents=True)
        (self.cap / 'frames').mkdir()
        make_pfm(self.cap/'frames/a.pfm', w=320, h=180, lit={0: .01})
        make_pfm(self.cap/'frames/b.pfm', w=320, h=180, lit={0: .02})
        make_pfm(self.cap/'frames/gpu.pfm', w=320, h=180, lit={1: .03})
        self.ev = {'scenario':'moving-rigid', 'p1m3b_holdout_quality':True,
                   'p1m3_fractional_storage':True,'reference_generation':'rendered',
                   'p1m1_canonical_token':0,'frames':[{'image':'frames/gpu.pfm',
                   'reference':{'path':'frames/a.pfm'}, 'reference_independent':{'path':'frames/b.pfm'}}]}
        (self.cap/module.EVIDENCE).write_text(json.dumps(self.ev))

    def tearDown(self):
        self.t.cleanup()

    def test_discovers_archive_and_reads_without_writing(self):
        self.assertEqual(module.find_captures(self.archive), [self.cap])
        before = sorted(str(p) for p in self.archive.rglob('*'))
        result = module.inspect_capture(self.cap)
        after = sorted(str(p) for p in self.archive.rglob('*'))
        self.assertEqual(before, after)
        self.assertEqual(result['diagnostic']['reference_paths'][0]['positive_luminance_pixels'], 1)
        self.assertEqual(result['diagnostic']['candidate']['gpu_only_positive_pixels'], 1)
        self.assertFalse(result['original_summary_verified'])

    def test_missing_expected_reference(self):
        (self.cap/'frames/a.pfm').unlink()
        with self.assertRaisesRegex(ValueError,'Missing reference A PFM'):
            module.inspect_capture(self.cap)

    def test_refuse_path_traversal(self):
        self.ev['frames'][0]['reference']['path']='../../escape.pfm'
        (self.cap/module.EVIDENCE).write_text(json.dumps(self.ev))
        with self.assertRaisesRegex(ValueError,'Unsafe path'):
            module.inspect_capture(self.cap)

    def test_summary_hash_mismatch(self):
        (self.cap.parent/module.ORIGINAL_SUMMARY).write_text('{}')
        with self.assertRaisesRegex(ValueError,'differs'):
            module.inspect_capture(self.cap)

    def test_does_not_mix_other_scenarios(self):
        self.ev['scenario']='deforming-control'
        (self.cap/module.EVIDENCE).write_text(json.dumps(self.ev))
        with self.assertRaisesRegex(ValueError,'Not an original'):
            module.inspect_capture(self.cap)


if __name__=='__main__':
    unittest.main()

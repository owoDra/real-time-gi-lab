import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_historical_summaries as audit


class TestArchive(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.a = Path(self.t.name) / 'a.json'
        self.b = Path(self.t.name) / 'b.json'
        self.a.write_text(json.dumps({'protocol_version': 'n006-p1m3b-moving-rigid-q8-two-reference-signed-v1',
                                      'status': 'invalid-retained', 'scenario': 'moving-rigid', 'failures': ['identical']}))
        ref = dict(positive_rgb_pixels=161, max_luminance=.0001747,
                   nonfinite_rgb_pixels=0, negative_rgb_pixels=0,
                   rgb_channel_sum=.011, PFM_SHA256='a'*64, spp=512)
        self.b.write_text(json.dumps({'protocol_version': 'n006-p1m3c-deforming-reference-eligibility-quality-v1',
                                      'scenario': 'deforming-control',
                                      'reference_preflight': {'reference': ref,
                                                              'reference_independent': dict(ref, positive_rgb_pixels=169),
                                                              'reference_A_B_RMS': 6.3e-8}}))

    def tearDown(self):
        self.t.cleanup()

    def test_support_bound_and_no_pfm_claim(self):
        from hashlib import sha256
        with patch.object(audit, 'M3B_SHA', sha256(self.a.read_bytes()).hexdigest()), \
             patch.object(audit, 'M3C_SHA', sha256(self.b.read_bytes()).hexdigest()):
            result = audit.audit(self.a, self.b)
        self.assertTrue(result['m3c']['forced_full_frame_p99_zero_for_pairwise_luma_error'])
        self.assertEqual(result['m3c']['union_positive_upper_bound'], 330)
        self.assertFalse(result['m3c']['PFM_read'])

    def test_hash_mismatch_blocks_history(self):
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            audit.audit(self.a, self.b)


if __name__ == '__main__':
    unittest.main()

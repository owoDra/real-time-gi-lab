import struct
import tempfile
import unittest
from pathlib import Path

from survey_archive import candidate_for, discover_pairs, survey, summarize_signatures


def make_pfm(path, w=3, h=2, lit=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = [0.0] * (w * h * 3)
    for pos, val in (lit or {}).items():
        rgb[pos*3:pos*3+3] = [val] * 3
    rows = [v for y in range(h-1, -1, -1) for v in rgb[y*w*3:(y+1)*w*3]]
    path.write_bytes(f'PF\n{w} {h}\n-1.0\n'.encode() + struct.pack('<' + 'f' * len(rows), *rows))


class TestSurvey(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.arc = self.root / 'gi-lab-old-private'
        self.n004 = self.arc / 'out/research/lane-n-end-to-end-renderer/004-n004-weakness-atlas/session/cases/lighting/frames'
        self.n001 = self.arc / 'out/research/lane-n-end-to-end-renderer/n001-sample/frames'
        self.n006 = self.arc / 'out/research/n006-interval-aware-allocation/p1m3b-moving-rigid-q8-signed/session/Q8_control_reference/frames'
        make_pfm(self.n004 / 'reference-8bounce.pfm')
        make_pfm(self.n004 / 'current-000.pfm', lit={1: .01})
        make_pfm(self.n001 / 'reference-001.pfm', lit={1: .1})
        make_pfm(self.n001 / 'output-001.pfm', lit={1: .11})
        make_pfm(self.n006 / 'reference-8bounce.pfm')
        make_pfm(self.n006 / 'candidate-000.pfm', lit={2: .02})
        self.n004.joinpath('reference-8bounce-independent.pfm').write_bytes(b'ignored')

    def tearDown(self):
        self.tmp.cleanup()

    def test_selects_only_valid_same_folder_pairs(self):
        pairs = discover_pairs(self.arc)
        self.assertEqual(len(pairs), 3)
        self.assertEqual(candidate_for(self.n004/'reference-8bounce-independent.pfm'), None)

    def test_archive_read_only_and_gpu_only_support(self):
        before = sorted(str(x) for x in self.arc.rglob('*'))
        result = survey(self.arc)
        self.assertEqual(len(result['pairs']), 3)
        self.assertEqual(result['reference_all_black_pairs'], 2)
        self.assertEqual(result['gpu_positive_with_black_reference_pairs'], 2)
        self.assertFalse(result['truncated'])
        self.assertEqual(result['unique_pair_signatures'], 3)
        self.assertEqual(sum(c['inspected_pairs'] for c in result['cohort_summary'].values()), 3)
        self.assertEqual(result['schema_version'], 2)
        self.assertEqual(before, sorted(str(x) for x in self.arc.rglob('*')))
        self.assertEqual(result['pairs'][0]['candidate_only_positive_pixels'] + result['pairs'][1]['candidate_only_positive_pixels'] + result['pairs'][2]['candidate_only_positive_pixels'], 2)

    def test_limit_explicit_truncated(self):
        result = survey(self.arc, 1)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['inspected_pairs'], 1)
        self.assertEqual(result['total_discovered_pairs'], 3)

    def test_default_full_archive_and_duplicate_signature_collapse(self):
        import shutil
        dup = self.arc / 'out/research/lane-n-end-to-end-renderer/003-n003-preflight-calibration/replica/frames'
        dup.mkdir(parents=True)
        shutil.copy2(self.n001 / 'reference-001.pfm', dup / 'reference-001.pfm')
        shutil.copy2(self.n001 / 'output-001.pfm', dup / 'output-001.pfm')
        result = survey(self.arc)
        self.assertEqual(result['inspected_pairs'], 4)
        self.assertFalse(result['truncated'])
        self.assertEqual(result['unique_pair_signatures'], 3)
        self.assertEqual(result['unique_black_reference_signatures'], 2)
        self.assertEqual(sorted(g['count'] for g in result['signature_groups']), [1, 1, 2])

    def test_invalid_max_pairs(self):
        with self.assertRaisesRegex(ValueError, 'nonnegative'):
            survey(self.arc, -1)

    def test_invalid_numeric_pair(self):
        make_pfm(self.n001 / 'output-001.pfm', lit={0: float('nan')})
        result = survey(self.arc)
        self.assertEqual(result['failed_pairs'], 1)
        self.assertIn('nonfinite', result['errors'][0]['error'])

    def test_mismatched_pair(self):
        make_pfm(self.n001 / 'output-001.pfm', w=2, h=2)
        result = survey(self.arc)
        self.assertEqual(result['failed_pairs'], 1)
        self.assertIn('dimensions', result['errors'][0]['error'])


if __name__ == '__main__':
    unittest.main()

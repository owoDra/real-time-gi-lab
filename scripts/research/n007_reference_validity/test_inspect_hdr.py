import math
import struct
import tempfile
import unittest
from pathlib import Path

from inspect_hdr import inspect, read_pfm, percentile


def make_pfm(path, w=100, h=100, lit=None, scale=-1.0):
    data = [0.0] * (w*h*3)
    for pixel, value in (lit or {}).items():
        data[pixel*3:pixel*3+3] = [value] * 3
    stride = w*3
    values = [v for y in range(h-1, -1, -1)
              for v in data[y*stride:(y+1)*stride]]
    path.write_bytes(f'PF\n{w} {h}\n{scale}\n'.encode() +
                     struct.pack(('<' if scale < 0 else '>') + 'f'*len(values), *values))


class TestHDR(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def refs(self, lists):
        paths = []
        for i, lit in enumerate(lists):
            p = self.root / f'r{i}.pfm'
            make_pfm(p, lit=lit)
            paths.append(p)
        return paths

    def test_sparse_zero_full_p99_but_nonzero_conditional(self):
        p = self.refs([{0: .1}, {0: .2}])
        result = inspect(p)
        self.assertEqual(result['pairwise'][0]['whole_frame_abs_luma_p99'], 0)
        self.assertAlmostEqual(result['pairwise'][0]['active_abs_luma_p99'], .1, places=6)
        self.assertIn('insufficient_active_pixel_support', result['problems'])

    def test_black_and_identical(self):
        p = self.refs([{}, {}, {}, {}])
        result = inspect(p)
        self.assertIn('black_reference', result['problems'])
        self.assertIn('identical_independent_replicates', result['problems'])

    def test_nonfinite_and_negative(self):
        p = self.refs([{0: math.nan}, {0: -1}, {0: 1}, {0: 2}])
        result = inspect(p)
        self.assertIn('nonfinite_or_negative_radiance', result['problems'])
        self.assertFalse(result['statistically_eligible'])

    def test_distinct_seed_close_stats(self):
        p = self.refs([{i: .01 + k*1e-8 for i in range(200)} for k in range(4)])
        result = inspect(p)
        self.assertTrue(result['statistically_eligible'])
        self.assertGreater(result['noise_rms_range'][0], 0)

    def test_inconsistent_dimensions(self):
        p = self.refs([{0: 1}, {0: 1}])
        make_pfm(p[1], w=2, h=2)
        with self.assertRaisesRegex(ValueError, 'dimension'):
            inspect(p)

    def test_candidate_outside_reference_active_region(self):
        p = self.refs([{i: .02 + k*1e-8 for i in range(200)} for k in range(4)])
        gpu = self.root/'gpu.pfm'
        make_pfm(gpu, lit={9999: .3})
        result = inspect(p, gpu)
        self.assertEqual(result['candidate']['gpu_only_positive_pixels'], 1)
        self.assertGreater(result['candidate']['vs_first_reference']['whole_frame_rgb_rms'], 0)

    def test_scale_endian_and_hash(self):
        p = self.root / 'big.pfm'
        make_pfm(p, w=1, h=2, lit={0: 1}, scale=2.0)
        img = read_pfm(p)
        self.assertEqual(img['y'][0], 2.0)
        self.assertEqual(len(img['sha256']), 64)

    def test_corrupt_payload(self):
        p = self.root/'bad.pfm'
        p.write_bytes(b'PF\n1 1\n-1.0\n')
        with self.assertRaisesRegex(ValueError, 'malformed payload'):
            read_pfm(p)


if __name__ == '__main__':
    unittest.main()

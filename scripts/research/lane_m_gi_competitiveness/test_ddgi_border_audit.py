import unittest

import numpy as np
import ddgi_border_audit as A


class BorderTests(unittest.TestCase):
    def atlas(self, tile, side=2):
        channels = {8: 4, 16: 2}[tile]
        a = np.arange(side * (tile * side)**2 * channels, dtype='<f4').reshape(side, tile * side, tile * side, channels) + 1
        for z in range(side):
            for ty in range(side):
                for tx in range(side):
                    for y, x, sy, sx in A.border_map(tile):
                        a[z, ty * tile + y, tx * tile + x] = a[z, ty * tile + sy, tx * tile + sx]
        return a

    def test_complete_map_and_interior_only_sources(self):
        for n in (8, 16):
            m = A.border_map(n)
            self.assertEqual(len(m), 4 * n - 4)
            self.assertEqual(len(set(map(tuple, m[:, :2]))), len(m))
            self.assertTrue(((m[:, 2:] >= 1) & (m[:, 2:] <= n - 2)).all())

    def test_manual_corner_and_row_column_golden_coordinates(self):
        for n in (8, 16):
            m = {tuple(p[:2]): tuple(p[2:]) for p in A.border_map(n)}
            self.assertEqual(m[(0, 0)], (n - 2, n - 2))
            self.assertEqual(m[(0, n - 1)], (n - 2, 1))
            self.assertEqual(m[(n - 1, 0)], (1, n - 2))
            self.assertEqual(m[(n - 1, n - 1)], (1, 1))
            self.assertEqual(m[(0, 2)], (1, n - 3))
            self.assertEqual(m[(n - 1, 3)], (n - 2, n - 4))
            self.assertEqual(m[(2, 0)], (n - 3, 1))
            self.assertEqual(m[(3, n - 1)], (n - 4, n - 2))

    def test_all_layers_tiles_and_channels_pass_without_mutation(self):
        for tile in (8, 16):
            a = self.atlas(tile)
            before = a.tobytes()
            self.assertTrue(A.check_atlas(a, tile, 2)['exact_copy_pass'])
            self.assertEqual(a.tobytes(), before)

    def test_single_border_zero_corruption_is_detected(self):
        for tile in (8, 16):
            a = self.atlas(tile)
            a[1, tile, tile + 2, -1] = 0
            r = A.check_atlas(a, tile, 2)
            self.assertFalse(r['exact_copy_pass'])
            self.assertEqual(r['mismatched_components'], 1)
            self.assertEqual(r['mismatched_texels'], 1)
            self.assertEqual(r['zero_nonzero_mismatched_components'], 1)
            self.assertEqual(r['first_mismatch']['destination'], [1, tile, tile + 2, a.shape[-1] - 1])

    def test_neighbor_probe_copy_is_rejected(self):
        a = self.atlas(16)
        a[0, 0, 2] = a[0, 1, 29]
        self.assertEqual(A.check_atlas(a, 16, 2)['mismatched_components'], 2)

    def test_signed_zero_is_not_silently_tolerated(self):
        a = np.zeros((1, 8, 8, 4), dtype='<f4')
        a[0, 0, 0, 0] = -0.0
        r = A.check_atlas(a, 8, 1)
        self.assertFalse(r['exact_copy_pass'])
        self.assertEqual(r['mismatched_components'], 1)
        self.assertEqual(r['maximum_absolute_difference'], 0)

    def test_invalid_shape_and_dtype_rejected(self):
        a = self.atlas(8)
        for b in (a[:, :, :-1], a.astype(np.float64)):
            with self.assertRaises(ValueError):
                A.check_atlas(b, 8, 2)

    def test_nonfinite_rejected(self):
        for value in (float('inf'), float('nan')):
            a = self.atlas(16)
            a[0, 1, 1, 0] = value
            with self.assertRaises(ValueError):
                A.check_atlas(a, 16, 2)

    def test_only_frozen_tile_sizes(self):
        with self.assertRaises(ValueError):
            A.border_map(12)

    def test_complete_explicit_capture_inventory(self):
        c = list(A.captures())
        self.assertEqual(len(c), 32)
        self.assertEqual([sum(x[0] == k for x in c) for k in ('static', 'dynamic', 'quality')], [6, 8, 18])
        self.assertEqual(len(set(x[2] for x in c)), 32)
        self.assertEqual(sum(len(x[3]) for x in c), 44)


if __name__ == '__main__':
    unittest.main()

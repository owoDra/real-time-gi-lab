import unittest
from pathlib import Path

import numpy as np
import ddgi_border_audit as A
import ddgi_border_copy_check as C
import ddgi_border_overlay as O


class CorrectedCopy(unittest.TestCase):
    def pair(self, tile, side):
        channels = {8: 4, 16: 2}[tile]
        before = np.arange(side * (tile * side)**2 * channels, dtype='<f4').reshape(side, tile * side, tile * side, channels) + 1
        for z in range(side):
            for y in range(tile * side):
                for x in range(tile * side):
                    if x % tile in (0, tile - 1) or y % tile in (0, tile - 1):
                        before[z, y, x] = 0
        return before, C.expected_copy(before, tile, side)

    def test_full_copy_includes_all_probes_layers_channels_without_mutation(self):
        for tile in (8, 16):
            for side in (1, 2, 3):
                before, after = self.pair(tile, side)
                old = before.tobytes(), after.tobytes()
                self.assertTrue(C.check_copy(before, after, tile, side)['full_copy_exact'])
                self.assertEqual(old, (before.tobytes(), after.tobytes()))

    def test_changed_interior_rejected_even_with_correct_borders(self):
        for tile in (8, 16):
            before, after = self.pair(tile, 2)
            after[1, tile + 3, tile + 3, -1] += 1
            self.assertTrue(A.check_atlas(after, tile, 2)['exact_copy_pass'])
            with self.assertRaises(ValueError):
                C.check_copy(before, after, tile, 2)

    def test_missing_or_corrupt_copy_rejected(self):
        for tile in (8, 16):
            before, after = self.pair(tile, 2)
            for changed in (before, after.copy()):
                changed[1, tile, tile + 2, -1] = 0
                with self.assertRaises(ValueError):
                    C.check_copy(before, changed, tile, 2)

    def test_uncleared_before_border_rejected(self):
        before, after = self.pair(16, 2)
        before[0, 0, 0] = after[0, 0, 0]
        with self.assertRaises(ValueError):
            C.check_copy(before, after, 16, 2)

    def test_negative_zero_before_border_rejected(self):
        before, after = self.pair(8, 1)
        before[0, 0, 0, 0] = -0.0
        with self.assertRaises(ValueError):
            C.check_copy(before, after, 8, 1)

    def test_complete_black_copy_passes(self):
        for tile in (8, 16):
            a = np.zeros((1, tile, tile, {8: 4, 16: 2}[tile]), dtype='<f4')
            self.assertTrue(C.check_copy(a, a, tile, 1)['full_copy_exact'])


class SourceBoundary(unittest.TestCase):
    def test_sdk_overlay_removes_only_tail_and_inverse_is_exact(self):
        old = A.SDK_SOURCE.read_bytes()
        new = O.interior_shader(old)
        self.assertEqual(new.decode().replace(O.SDK_REPLACEMENT, O.SDK_TAIL).encode(), old)
        self.assertNotIn(O.SDK_TAIL.encode(), new)
        # Full interior computation, including every early return, stays exact.
        marker = b'    if(!isBorderTexel)'
        self.assertEqual(new.split(marker)[1].split(O.SDK_REPLACEMENT.encode())[0], old.split(marker)[1].split(O.SDK_TAIL.encode())[0])

    def test_hosts_overlay_only_loading_and_pre_copy_captures_dispatches(self):
        for name in O.HOST_SHA:
            old = (A.REPO / 'src/research/lane_m_gi_competitiveness' / name).read_bytes()
            new = O.host(old, name).decode()
            self.assertEqual(new.count('copy_border(border_irradiance,'), 1)
            self.assertEqual(new.count('copy_border(border_distance,'), 1)
            self.assertLess(new.index('pre-border-'), new.index('copy_border(border_irradiance,'))
            self.assertLess(new.index('copy_border(border_distance,'), new.index(O.CAPTURE_ANCHOR))
            inverse = new.replace(O.COPY_ADDITION + O.CAPTURE_ANCHOR, O.CAPTURE_ANCHOR).replace(O.KERNEL_ADDITION + O.KERNEL_ANCHOR, O.KERNEL_ANCHOR)
            self.assertEqual(inverse.encode(), old)

    def test_drift_or_repeat_cannot_silently_generate_source(self):
        with self.assertRaises(ValueError):
            O.interior_shader(A.SDK_SOURCE.read_bytes() + b'\n')
        for name in O.HOST_SHA:
            old = (A.REPO / 'src/research/lane_m_gi_competitiveness' / name).read_bytes()
            with self.assertRaises(ValueError):
                O.host(old + b'\n', name)
            with self.assertRaises(ValueError):
                O.host(O.host(old, name), name)

    def test_ambiguous_overlay_rejected(self):
        for source in ('old old', 'missing', 'old new'):
            with self.assertRaises(ValueError):
                O.replace_unique(source, 'old', 'new')

    def test_shader_has_no_barrier_or_interior_lighting_write(self):
        text = (A.REPO / 'shaders/research/lane_m_gi_competitiveness/m001_ddgi_border_copy.hlsl').read_text()
        self.assertNotIn('Barrier(', text)
        for target, tile in (('Irradiance', 8), ('Distance', 16)):
            self.assertEqual(text.count(target + '[id]=' + target + '[source];'), 1)
            self.assertIn(f'if(!border(local.xy,{tile})) return;', text)
            self.assertIn(f'group.xy*{tile}+interior_source(local.xy,{tile})', text)


if __name__ == '__main__':
    unittest.main()

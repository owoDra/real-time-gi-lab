from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from audit_p1a_images import effect_stats, safe_file


class TestP1aImageAudit(unittest.TestCase):
    def test_identical_images_are_zero_effect(self) -> None:
        pixels = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0]
        r = effect_stats(pixels, pixels, [0.0] * 6,
                         width=2, height=1, tile_id=0)
        self.assertEqual(r["changed_channels"], 0)
        self.assertEqual(r["changed_pixels"], 0)
        self.assertEqual(r["global_rgb_rms_gain"], 0.0)

    def test_beneficial_targeted_pixel(self) -> None:
        base = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0]
        candidate = [0.0] * 6
        r = effect_stats(base, candidate, [0.0] * 6,
                         width=2, height=1, tile_id=0)
        self.assertEqual(r["changed_channels"], 3)
        self.assertEqual(r["changed_pixels"], 1)
        self.assertEqual(r["beneficial_pixels"], 1)
        self.assertEqual(r["harmful_pixels"], 0)
        self.assertTrue(r["source_tile_pixel_changed"])
        self.assertGreater(r["global_rgb_rms_gain"], 0)

    def test_worsened_and_nonlocal_effect(self) -> None:
        base = [0.0] * 6
        candidate = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
        r = effect_stats(base, candidate, [0.0] * 6,
                         width=2, height=1, tile_id=0)
        self.assertEqual(r["changed_pixels"], 1)
        self.assertEqual(r["harmful_pixels"], 1)
        self.assertFalse(r["source_tile_pixel_changed"])
        self.assertLess(r["global_rgb_rms_gain"], 0)

    def test_invalid_or_nonfinite_pixels(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid tile"):
            effect_stats([0.0] * 3, [0.0] * 3, [0.0] * 3,
                         width=1, height=1, tile_id=1)
        with self.assertRaisesRegex(ValueError, "non-finite"):
            effect_stats([float("nan")] * 3, [0.0] * 3, [0.0] * 3,
                         width=1, height=1, tile_id=0)

    def test_unsafe_artifact_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "unsafe path"):
                safe_file(Path(td), "../payload")
            with self.assertRaisesRegex(ValueError, "unsafe path"):
                safe_file(Path(td), "/tmp/payload")


if __name__ == "__main__":
    unittest.main()

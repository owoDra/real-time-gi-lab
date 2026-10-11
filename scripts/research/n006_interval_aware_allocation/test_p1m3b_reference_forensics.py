"""P1m3b reference-capture offline PFM forensics regression."""
from __future__ import annotations

import math
import struct
import unittest
from pathlib import Path

from diagnose_p1m3b_reference_capture import (
    OUTPUT_NAME, rgb_diagnostic, safe_artifact,
)

ROOT = Path(__file__).resolve().parents[3]


class ReferenceForensicsTests(unittest.TestCase):
    def test_known_zero_black_and_positive_rgb(self):
        frame = bytes(320 * 180 * 3 * 4)
        result = rgb_diagnostic(frame)
        self.assertEqual(result["positive_rgb_pixels"], 0)
        self.assertEqual(result["positive_channel_values"], 0)
        self.assertEqual(result["max_abs_channel"], 0.0)
        self.assertEqual(result["max_luminance"], 0.0)
        self.assertEqual(result["nonfinite_rgb_pixels"], 0)
        modified = bytearray(frame)
        struct.pack_into("<fff", modified, 0, 0.5, 0.25, 0.0)
        x = rgb_diagnostic(bytes(modified))
        self.assertEqual(x["positive_rgb_pixels"], 1)
        self.assertEqual(x["positive_channel_values"], 2)
        self.assertEqual(x["max_abs_channel"], 0.5)
        self.assertGreater(x["max_luminance"], 0)

    def test_nonfinite_diagnostics_not_hidden(self):
        frame = bytearray(320 * 180 * 3 * 4)
        struct.pack_into("<fff", frame, 0, float("nan"), 0.0, 0.0)
        result = rgb_diagnostic(bytes(frame))
        self.assertEqual(result["nonfinite_rgb_pixels"], 1)
        self.assertEqual(result["positive_rgb_pixels"], 0)
        self.assertRaises(ValueError, rgb_diagnostic, b"not a float frame")

    def test_original_capture_only_no_gpu_execution(self):
        source = (
            ROOT / "scripts/research/n006_interval_aware_allocation"
            / "diagnose_p1m3b_reference_capture.py"
        ).read_text()
        for field in (
            "Q8_control_reference",
            "N001_reference_A",
            "N001_reference_B",
            "n006-candidate-evidence.json",
            "P1_predictor_go",
            "no_new_gpu_or_cpu_reference_run",
            "reference_A_all_black",
            "reference_pair_RGB_RMS",
        ):
            if field == "n006-candidate-evidence.json":
                self.assertIn("EVIDENCE_NAME", source)
            else:
                self.assertIn(field, source)
        self.assertNotIn("subprocess.run", source)
        self.assertEqual(OUTPUT_NAME, "n006-p1m3b-reference-forensics.json")

    def test_reject_escaping_paths(self):
        with self.assertRaises(ValueError):
            safe_artifact(ROOT, "/etc/passwd")
        with self.assertRaises(ValueError):
            safe_artifact(ROOT, "../private.pfm")


if __name__ == "__main__":
    unittest.main()

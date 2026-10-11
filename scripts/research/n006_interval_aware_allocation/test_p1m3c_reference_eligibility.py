"""N006 P1m3c freeze of reference eligibility, unchanged Q8, bounded keys."""
from __future__ import annotations

import ast
import hashlib
import struct
import unittest
from pathlib import Path

from diagnose_p1m3b_reference_capture import rgb_diagnostic
from run_p1m3c_deforming_reference_quality import (
    PROTOCOL, RESULT_NAME, SCENARIO, reference_preflight,
)

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "scripts/research/n006_interval_aware_allocation"
CPP = ROOT / "src/research/n006_interval_aware_allocation/n006_intervention_main.cpp"


class TestP1m3cReferenceEligibility(unittest.TestCase):
    def test_fixed_deforming_preflight(self):
        self.assertEqual(SCENARIO, "deforming-control")
        self.assertEqual(PROTOCOL, "n006-p1m3c-deforming-reference-eligibility-quality-v1")
        self.assertEqual(RESULT_NAME, "n006-p1m3c-deforming-reference-quality-summary.json")

    def test_reference_probe_rejects_identical_black_and_nonfinite(self):
        black = bytes(320 * 180 * 3 * 4)
        values = rgb_diagnostic(black)
        self.assertEqual(values["positive_rgb_pixels"], 0)
        self.assertEqual(values["max_abs_channel"], 0)
        positive = bytearray(black)
        struct.pack_into("<fff", positive, 0, 0.25, 0.25, 0.25)
        metrics = rgb_diagnostic(bytes(positive))
        self.assertEqual(metrics["positive_rgb_pixels"], 1)
        self.assertGreater(metrics["max_luminance"], 0)

    def test_failed_reference_never_advances_to_key_intervention(self):
        text = (SRC / "run_p1m3c_deforming_reference_quality.py").read_text()
        ast.parse(text)
        for marker in (
            'if not preflight["eligible"]:',
            'report["status"] = "reference-ineligible-retained"',
            'return 0',
            'selection = select_prospective_holdout(control0["key_rows"])',
            'save()  # Critical: freeze M0 selected keys before any extra rays.',
            'scenario=SCENARIO',
            'reference_pair(folder, evidence)',
            'case["quality_signal"] = (',
            'case["reproduced"] and gainA > noise and gainB > noise',
            'row["stratum"] == "global_zero_negative"',
            'report["status"] = "quality-not-detectable-stop"',
            'report["status"] = "image-null-stop"',
            '"P1_predictor_go": False, "P2_scheduler_go": False',
        ):
            self.assertIn(marker, text)
        self.assertLess(text.index('if not preflight["eligible"]:'),
                        text.index('selection = select_prospective_holdout'))
        self.assertLess(text.index('selection = select_prospective_holdout'),
                        text.index('for row in selection["selected"]:'))

    def test_separate_opt_in_mode_and_old_scenarios_unchanged(self):
        main = CPP.read_text()
        for check in (
            'else if (arg == "--p1m3c-reference-preflight")',
            'if (p1m3c_reference_preflight &&',
            'p1m3b_holdout_quality || !p1m3_fractional_storage',
            'scenario_name != "deforming-control"',
            'p1m2_tetra_octant_directions',
            '"p1m3c_reference_preflight',
            '"frames/reference-8bounce-independent.pfm"',
            'if (p1m3b_holdout_quality || p1m3c_reference_preflight)',
        ):
            # serializer quotation is C++-escaped, not Python JSON literal
            if check.startswith('"p1m3c'):
                self.assertIn('p1m3c_reference_preflight', main)
            else:
                self.assertIn(check, main)
        self.assertIn(
            '(!(p1m3b_holdout_quality || p1m3c_reference_preflight) && !valid_calibration_key)',
            main,
        )
        original_verify = (SRC / "run_p1m2b_independent_state.py").read_text()
        self.assertIn('allowed_scenarios = ("moving-rigid", "deforming-control")',original_verify)
        self.assertIn('data.get("p1m3c_reference_preflight") is not True',original_verify)
        launcher = (SRC / "run_n006_p1m3c_deforming_reference_quality.sh").read_text()
        for token in ("git pull --ff-only", "mise run build",
                      "unittest discover", "run_p1m3c_deforming_reference_quality.py"):
            self.assertIn(token, launcher)


if __name__ == "__main__":
    unittest.main()

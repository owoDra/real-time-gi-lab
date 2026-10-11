"""P1m3b prospective moving-rigid quality: source and CPU label guard tests."""
from __future__ import annotations

import ast
import struct
import unittest
from pathlib import Path

from run_p1m3b_moving_rigid_signed_quality import (
    MAX_CASES, NOISE_RULE, PROTOCOL, SCENARIO,
    rgb_rms, select_prospective_holdout,
)

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "scripts/research/n006_interval_aware_allocation"
MAIN = ROOT / "src/research/n006_interval_aware_allocation/n006_intervention_main.cpp"
OLD = HERE / "run_p1m2b_independent_state.py"
RUNNER = HERE / "run_p1m3b_moving_rigid_signed_quality.py"


def row(cascade: int, local: int, consumer: int) -> dict[str, int]:
    return {
        "token": (cascade << 30) + local + 1,
        "consumer_pixels": consumer,
        "producer_owner_outputs": 1,
    }


class TestMovingRigidReferenceQuality(unittest.TestCase):
    def test_frozen_scenario_arm_budget_and_noise_rule(self):
        self.assertEqual(SCENARIO, "moving-rigid")
        self.assertEqual(MAX_CASES, 5)
        self.assertEqual(
            PROTOCOL, "n006-p1m3b-moving-rigid-q8-two-reference-signed-v1")
        self.assertIn("both_signed_gains_strictly_exceed_RMS", NOISE_RULE)

    def test_selector_frozen_positive_max_and_tiebreak_plus_global_zero(self):
        rows = sorted([
            *[row(c, 0, 0) for c in range(4)],
            *[row(c, 1, 7) for c in range(4)],
            *[row(c, 2, 7) for c in range(4)],
        ], key=lambda x: x["token"])
        selection = select_prospective_holdout(rows)
        self.assertEqual(len(selection["selected"]), 5)
        self.assertEqual(selection["missing_strata"], [])
        for c in range(4):
            self.assertEqual(selection["selected"][c]["token"], row(c, 1, 7)["token"])
            self.assertEqual(selection["selected"][c]["cascade"], c)
        self.assertEqual(selection["selected"][4]["token"], row(0, 0, 0)["token"])
        self.assertEqual(selection["selected"][4]["stratum"], "global_zero_negative")

    def test_selector_missing_strata_fail_closed_no_posthoc_key(self):
        rows = [row(0, 0, 0), row(1, 0, 2), row(2, 0, 1)]
        chosen = select_prospective_holdout(rows)
        self.assertEqual(len(chosen["selected"]), 3)
        self.assertTrue(any(x["cascade"] == 3 for x in chosen["missing_strata"]))
        for invalid in (
            [], [row(0, 1, 1), row(0, 0, 0)],
            [row(0, 0, 0), row(0, 0, 0)],
            [{"token": True, "consumer_pixels": 0, "producer_owner_outputs": 1}],
            [{"token": 0xffffffff, "consumer_pixels": 0, "producer_owner_outputs": 1}],
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                select_prospective_holdout(invalid)

    def test_full_frame_rgb_rms_float32_and_nonfinite(self):
        blank = b"\x00" * (320 * 180 * 3 * 4)
        self.assertEqual(rgb_rms(blank, blank), 0.0)
        changed = bytearray(blank)
        struct.pack_into("<f", changed, 0, 0.006)
        error = rgb_rms(blank, bytes(changed))
        self.assertGreater(error, 0)
        self.assertLess(error, 0.001)
        struct.pack_into("<f", changed, 0, float("nan"))
        with self.assertRaises(ValueError):
            rgb_rms(blank, bytes(changed))

    def test_reference_generated_only_in_holdout_control_and_validated(self):
        source = MAIN.read_text()
        for guard in (
            'else if (arg == "--p1m3b-holdout-quality")',
            'if (p1m3b_holdout_quality &&',
            'scenario_name != "moving-rigid"',
            'p1m2_tetra_octant_directions',
            '(!skip_reference && p1m1_canonical_token != 0U)',
            'n001_render_reference(readback, settings)',
            'independent_settings.seed_a = 0x517cc1b727220a95ULL',
            'independent_settings.seed_b = 0x8b8b8b8b4f1bbcddULL',
            '"frames/reference-8bounce-independent.pfm"',
            'independent_references.assign(frames.size(), independent)',
            'reference_independent',
            'p1m3b_holdout_quality',
            'p1m3_fractional_storage',
            'if (skip_reference || !(p1m3b_holdout_quality || p1m3c_reference_preflight)) out << "null"',
        ):
            self.assertIn(guard, source)
        old = OLD.read_text()
        self.assertIn("holdout: bool = False", old)
        self.assertIn("require_reference: bool = False", old)
        self.assertIn('data.get("p1m3b_holdout_quality") is not True', old)
        self.assertIn('("rendered" if require_reference else "skipped")', old)

    def test_runner_paired_signed_metrics_consistency_and_bound(self):
        src = RUNNER.read_text()
        ast.parse(src)
        for frag in (
            'for key in ("reference", "reference_independent")',
            'reference_pair(folder0, evidence0)',
            'verified0["key_rows"] != verified1["key_rows"]',
            'select_prospective_holdout(verified0["key_rows"])',
            'save()  # Must happen BEFORE ANY new holdout extra-ray GPU treatment',
            'baseline_A - after_A, baseline_B - after_B',
            'gain_A > threshold and gain_B > threshold',
            'threshold = reference_info["RMS_reference_A_vs_B"]',
            '"holdout-Q8-quality-not-detectable-stop"',
            '"holdout-Q8-zero-influence-stop"',
            'if selected["stratum"] == "global_zero_negative"',
            'candidate["reproduced"] and gain_A > threshold',
            '"P1_predictor_go": False',
            '"P2_scheduler_go": False',
        ):
            self.assertIn(frag, src)
        shell = (HERE / "run_n006_p1m3b_moving_rigid_signed_quality.sh").read_text()
        for frag in ("git pull --ff-only", "mise run build",
                     "unittest discover", "run_p1m3b_moving_rigid_signed_quality.py"):
            self.assertIn(frag, shell)


if __name__ == "__main__":
    unittest.main()

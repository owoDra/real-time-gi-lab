from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT
    / "research/lanes/lane-l-heavy-boundary-calibration/experiments"
    / "005-l002-config.json"
)


class L002ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_candidate_ranking_is_forbidden(self) -> None:
        self.assertFalse(self.config["architecture_ranking_allowed"])
        self.assertEqual(
            self.config["experiment_role"],
            "heavy-boundary-detectable-effect-floor-calibration-only",
        )

    def test_heavy_boundary_shape_is_unchanged(self) -> None:
        self.assertEqual(self.config["recurring_boundary"]["batch_transitions"], 16)
        self.assertEqual(self.config["j002"]["snapshot_count"], 8)
        self.assertEqual(self.config["timing"]["warmup_pairs"], 4)
        self.assertEqual(self.config["timing"]["measured_pairs"], 12)
        self.assertEqual(self.config["timing"]["fresh_process_blocks"], 8)

    def test_synthetic_ladder_and_injection_are_frozen(self) -> None:
        synthetic = self.config["synthetic_effect_calibration"]
        self.assertEqual(
            [(item["id"], item["factor"]) for item in synthetic["factors"]],
            [("plus20", 1.20), ("plus10", 1.10), ("plus5", 1.05)],
        )
        self.assertEqual(
            synthetic["injection_domain"],
            "analysis-only-gpu-timestamp-b-role",
        )
        self.assertFalse(synthetic["measured_gpu_work_modified"])
        self.assertEqual(
            synthetic["raw_samples"],
            "retain-unmodified-measured-values",
        )

    def test_detection_gate_is_strict_and_profile_local(self) -> None:
        gate = self.config["detection_gate"]
        self.assertEqual(gate["minimum_positive_pair_fraction"], 0.75)
        self.assertTrue(gate["require_all_process_medians_above_unity"])
        self.assertTrue(gate["require_all_ab_stratum_medians_above_unity"])
        self.assertTrue(gate["require_all_ba_stratum_medians_above_unity"])
        self.assertTrue(
            gate["control_noise_envelope"][
                "injected_factor_must_exceed_envelope_strictly"
            ]
        )
        self.assertFalse(gate["profile_averaging_allowed"])
        self.assertEqual(gate["contiguous_order"], ["plus20", "plus10", "plus5"])

    def test_no_rerun_or_exclusion(self) -> None:
        timing = self.config["timing"]
        self.assertEqual(timing["sample_exclusion"], "forbidden")
        self.assertEqual(timing["instability_rerun_budget"], 0)
        self.assertEqual(timing["completed_campaign_rerun_budget"], 0)


if __name__ == "__main__":
    unittest.main()

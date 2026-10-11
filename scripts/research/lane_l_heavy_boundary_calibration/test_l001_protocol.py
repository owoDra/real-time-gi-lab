from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT
    / "research/lanes/lane-l-heavy-boundary-calibration/experiments"
    / "002-l001-config.json"
)


class L001ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_scope_is_same_variant_measurement_calibration_only(self) -> None:
        self.assertFalse(self.cfg["architecture_ranking_allowed"])
        self.assertEqual(
            set(self.cfg["controls"]),
            {"primary", "software"},
        )
        self.assertFalse(
            self.cfg["optional_single_runtime_diagnostic"]["enabled"]
        )
        self.assertEqual(
            [item["id"] for item in self.cfg["environments"]],
            [
                "dual-context",
                "single-context-independent-runtime",
            ],
        )

    def test_heavy_boundary_shape_matches_frozen_j004(self) -> None:
        timing = self.cfg["timing"]
        boundary = self.cfg["recurring_boundary"]
        self.assertEqual(int(timing["warmup_pairs"]), 4)
        self.assertEqual(int(timing["measured_pairs"]), 12)
        self.assertEqual(int(timing["fresh_process_blocks"]), 8)
        self.assertEqual(float(timing["settle_seconds"]), 1.0)
        self.assertEqual(
            timing["start_order_by_block"],
            ["AB", "BA", "AB", "BA", "BA", "AB", "BA", "AB"],
        )
        self.assertEqual(int(boundary["batch_transitions"]), 16)
        self.assertEqual(int(boundary["topology_steps_per_cycle"]), 8)
        self.assertFalse(boundary["future_snapshot_prebuild"])
        self.assertFalse(boundary["recurrent_work_moved_to_setup"])

    def test_environment_order_is_counterbalanced(self) -> None:
        orders = self.cfg["timing"]["environment_order_by_block"]
        expected = {
            "dual-context",
            "single-context-independent-runtime",
        }
        self.assertEqual(len(orders), 8)
        first_counts = {name: 0 for name in expected}
        for order in orders:
            self.assertEqual(set(order), expected)
            self.assertEqual(len(order), 2)
            first_counts[order[0]] += 1
        self.assertEqual(set(first_counts.values()), {4})

    def test_control_gate_is_unchanged(self) -> None:
        gate = self.cfg["gpu_control_health"]
        self.assertEqual(
            float(gate["control_max_abs_process_median_ratio"]),
            1.02,
        )
        self.assertEqual(
            float(gate["control_process_median_span_ratio"]),
            1.03,
        )
        self.assertEqual(
            float(gate["control_max_within_process_order_bias_ratio"]),
            1.02,
        )
        self.assertFalse(gate["profile_averaging_allowed"])

    def test_profiles_and_contracts_are_frozen(self) -> None:
        self.assertEqual(
            [item["name"] for item in self.cfg["j002"]["profiles"]],
            [
                "small-global-high",
                "medium-global-representative",
                "medium-local-high",
                "large-global-high",
                "large-local-high",
            ],
        )
        self.assertEqual(
            self.cfg["j002"]["hit_contract"],
            "B001-exact-hit-v1",
        )
        self.assertEqual(
            int(self.cfg["j002"]["validation_ray_prefix_count"]),
            0,
        )

    def test_timing_memory_is_not_decision_evidence(self) -> None:
        self.assertEqual(
            self.cfg["axis_roles"]["timed_memory"],
            "diagnostic-only",
        )
        allocation = self.cfg["allocation_lifetime"]
        self.assertEqual(
            allocation["evidence_pass"],
            "pre-timing-paired-validation",
        )
        self.assertTrue(
            allocation["no_extra_gpu_bookkeeping_in_timed_boundary"]
        )

    def test_zero_rerun_and_exclusion_policy(self) -> None:
        timing = self.cfg["timing"]
        self.assertEqual(timing["sample_exclusion"], "forbidden")
        self.assertEqual(int(timing["instability_rerun_budget"]), 0)
        self.assertEqual(int(timing["completed_campaign_rerun_budget"]), 0)
        self.assertFalse(timing["accepted_timing_validation"])

    def test_python_bytecode_remains_ignored(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("__pycache__/", ignore)
        self.assertIn("*.py[cod]", ignore)


if __name__ == "__main__":
    unittest.main()

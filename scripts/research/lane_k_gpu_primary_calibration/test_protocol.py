from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT / "research/lanes/lane-k-gpu-primary-calibration/experiments"
    / "002-gpu-primary-protocol-config.json"
)


class LaneKProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_controlled_work_mapping_is_exact(self) -> None:
        variants = self.cfg["workload"]["variant_iterations"]
        base = int(variants["baseline"])
        self.assertEqual(base, 200)
        self.assertEqual(int(variants["plus5"]) * 100, base * 105)
        self.assertEqual(int(variants["plus10"]) * 100, base * 110)
        self.assertEqual(int(variants["plus20"]) * 100, base * 120)

    def test_accepted_shape_is_frozen(self) -> None:
        workload = self.cfg["workload"]
        self.assertEqual(int(workload["elements"]), 8192)
        self.assertEqual(int(workload["accepted_batch_dispatches"]), 16)
        self.assertEqual(int(self.cfg["warmup_pairs"]), 4)
        self.assertEqual(int(self.cfg["measured_pairs"]), 12)
        self.assertEqual(int(self.cfg["fresh_process_blocks"]), 8)
        self.assertEqual(int(self.cfg["instability_rerun_budget"]), 0)
        self.assertFalse(bool(self.cfg["accepted_timing_validation"]))
        self.assertEqual(self.cfg["sample_exclusion"], "forbidden")
        self.assertEqual(self.cfg["host_observations"], "diagnostic-only")
        self.assertEqual(self.cfg["axis_roles"]["primary_performance"], "gpu_timestamp")
        self.assertEqual(
            self.cfg["axis_roles"]["cpu_wall"],
            "diagnostic-health-provenance-only",
        )
        self.assertEqual(int(self.cfg["completed_campaign_rerun_budget"]), 0)
        self.assertFalse(bool(self.cfg["diagnostic_individual"]["enabled"]))

    def test_process_order_is_position_balanced(self) -> None:
        orders = self.cfg["comparison_orders"]
        comparisons = set(self.cfg["comparisons"])
        self.assertEqual(len(orders), int(self.cfg["fresh_process_blocks"]))
        slot_counts = {name: Counter() for name in comparisons}
        for order in orders:
            self.assertEqual(set(order), comparisons)
            self.assertEqual(len(order), len(comparisons))
            for slot, name in enumerate(order):
                slot_counts[name][slot] += 1
        for counts in slot_counts.values():
            self.assertEqual(set(counts.values()), {2})

    def test_ab_ba_start_orientation_is_balanced_per_comparison(self) -> None:
        orders = self.cfg["comparison_orders"]
        counts = {
            name: Counter() for name in self.cfg["comparisons"]
        }
        for block, order in enumerate(orders):
            for slot, name in enumerate(order):
                counts[name]["AB" if (block + slot) % 2 == 0 else "BA"] += 1
        for value in counts.values():
            self.assertEqual(value["AB"], 4)
            self.assertEqual(value["BA"], 4)


if __name__ == "__main__":
    unittest.main()


    def test_cpu_wall_can_only_invalidate_structural_health(self) -> None:
        health = self.cfg["cpu_wall_health"]
        self.assertEqual(
            health["decision_use"], "diagnostic-health-provenance-only"
        )
        invalidation = health["invalidation_rules"]
        self.assertTrue(invalidation["require_positive_finite_samples"])
        self.assertTrue(invalidation["require_complete_wall_ge_gpu_timestamp"])
        self.assertTrue(invalidation["require_device_provenance_consistency"])
        self.assertEqual(
            health["repeatability_threshold_effect"], "annotation-only"
        )

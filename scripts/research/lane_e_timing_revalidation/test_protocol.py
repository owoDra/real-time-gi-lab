from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "research/lanes/lane-e-timing-revalidation/experiments/002-e001-config.json"


class ProtocolTests(unittest.TestCase):
    def test_frozen_heavy_boundary_contract(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["plan_version"], "lane-e-timing-revalidation-e001-v3")
        self.assertEqual(config["timing"]["environment"], "dual-context")
        self.assertEqual(config["timing"]["primary_axis"], "gpu_timestamp")
        self.assertEqual(config["timing"]["cpu_wall_role"], "diagnostic-health-provenance-only")
        self.assertEqual(config["timing"]["warmup_pairs"], 4)
        self.assertEqual(config["timing"]["measured_pairs"], 12)
        self.assertEqual(config["timing"]["fresh_process_blocks"], 8)
        orders = config["timing"]["comparison_order_by_block"]
        self.assertEqual(len(orders), 8)
        self.assertEqual(sum(order[0] == "control" for order in orders), 4)
        self.assertEqual(config["timing"]["complete_transitions_per_sample"], 16)
        self.assertEqual(config["timing"]["sample_exclusion"], "forbidden")
        self.assertEqual(config["timing"]["instability_rerun_budget"], 0)
        self.assertEqual(config["timing"]["completed_campaign_rerun_budget"], 0)
        self.assertEqual(config["performance_gate"]["promotion_threshold_percent"], 20)
        self.assertEqual(config["performance_gate"]["non_regression_threshold_percent"], 20)
        self.assertTrue(config["performance_gate"]["lane_k_5_percent_floor_forbidden"])
        self.assertFalse(config["timing"]["future_state_prebuild"])
        self.assertFalse(config["timing"]["recurrent_work_moved_to_setup"])
        self.assertEqual(config["timing"]["expected_fresh_timing_processes"], 160)
        self.assertEqual(config["artifact_schema"]["version"], 2)
        self.assertIn("e001-raw.csv", config["artifact_schema"]["required"])
        self.assertIn("e001-device-provenance.json", config["artifact_schema"]["required"])


if __name__ == "__main__":
    unittest.main()

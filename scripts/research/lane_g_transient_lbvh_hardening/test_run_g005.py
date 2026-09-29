from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATH = Path(__file__).with_name("run_g005.py")
CONFIG = (
    ROOT / "research/lanes/lane-g-transient-lbvh-hardening/experiments"
    / "005-final-deterministic-replay-config.json"
)
spec = importlib.util.spec_from_file_location("run_g005", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class G005Tests(unittest.TestCase):
    def test_matrix_shape_and_variants(self) -> None:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(len(cfg["variants"]), 5)
        self.assertEqual(len(cfg["scenarios"]), 12)
        self.assertEqual(
            cfg["variants"],
            [
                "transient-lbvh",
                "hardened-transient-lbvh",
                "vanilla-software",
                "combined-hwrt",
                "combined-software",
            ],
        )

    def test_lane_e_claim_is_explicitly_forbidden(self) -> None:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertFalse(cfg["lane_e_comparator"]["included"])
        self.assertIn(
            "No Lane E superiority or replacement claim",
            cfg["lane_e_comparator"]["consequence"],
        )

    def test_same_workload_rejects_divergence(self) -> None:
        rows = [
            {field: "1" for field in mod.WORKLOAD_FIELDS},
            {field: "1" for field in mod.WORKLOAD_FIELDS},
        ]
        rows[1]["work_items"] = "2"
        with self.assertRaises(RuntimeError):
            mod.assert_same_workload("static", rows)

    def test_correctness_rejects_nonzero_mismatch(self) -> None:
        row = {field: "0" for field in mod.ZERO_FIELDS}
        row["quality_passed"] = "1"
        self.assertEqual(mod.row_failures(row), [])
        row["hit_mismatches"] = "1"
        self.assertIn("hit_mismatches", mod.row_failures(row))

    def test_no_power_or_timing_decision_path(self) -> None:
        source = PATH.read_text(encoding="utf-8")
        self.assertNotIn("profile_peak", source)
        self.assertNotIn("power_dpm_force_performance_level", source)
        self.assertIn('"timing_used_for_decision": False', source)


if __name__ == "__main__":
    unittest.main()

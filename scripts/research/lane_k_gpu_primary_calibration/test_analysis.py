from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("analysis.py")
spec = importlib.util.spec_from_file_location("lane_k_analysis", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def process_row(
    comparison: str,
    ratio: float,
    order_bias: float = 1.0,
    positive_fraction: float = 1.0,
) -> dict[str, object]:
    axis = {
        "median_log_ratio": math.log(ratio),
        "order_bias_ratio": order_bias,
        "positive_pair_fraction": positive_fraction,
    }
    return {
        "comparison": comparison,
        "gpu": dict(axis),
        "wall": dict(axis),
    }


CRITERIA = {
    "control_max_abs_process_median_ratio": 1.02,
    "control_process_median_span_ratio": 1.03,
    "control_max_within_process_order_bias_ratio": 1.02,
    "candidate_process_effect_span_ratio": 1.05,
    "candidate_max_within_process_order_bias_ratio": 1.03,
    "candidate_min_positive_pair_fraction": 0.75,
}


class LaneKAnalysisTests(unittest.TestCase):
    def test_control_passes_small_role_bias(self) -> None:
        rows = [process_row("control", ratio) for ratio in
                (1.001, 0.999, 1.004, 0.998, 1.002, 1.000, 0.997, 1.003)]
        result = mod.evaluate_control(rows, "gpu", CRITERIA)
        self.assertTrue(result["passed"])
        self.assertLess(result["noise_envelope_ratio"], 1.01)

    def test_control_rejects_large_fresh_process_bias(self) -> None:
        rows = [process_row("control", 1.0) for _ in range(7)]
        rows.append(process_row("control", 1.04))
        result = mod.evaluate_control(rows, "gpu", CRITERIA)
        self.assertFalse(result["passed"])

    def test_candidate_requires_every_process_above_control_noise(self) -> None:
        control_rows = [process_row("control", ratio) for ratio in
                        (1.001, 0.999, 1.004, 0.998, 1.002, 1.000, 0.997, 1.003)]
        control = mod.evaluate_control(control_rows, "gpu", CRITERIA)
        good = [process_row("plus10", 1.06 + index * 0.001) for index in range(8)]
        bad = list(good)
        bad[-1] = process_row("plus10", 1.002)
        self.assertTrue(mod.evaluate_candidate(good, "gpu", CRITERIA, control)["detected"])
        self.assertFalse(mod.evaluate_candidate(bad, "gpu", CRITERIA, control)["detected"])

    def test_candidate_rejects_order_sensitive_effect(self) -> None:
        control = mod.evaluate_control(
            [process_row("control", 1.0) for _ in range(8)], "gpu", CRITERIA
        )
        rows = [process_row("plus20", 1.15) for _ in range(8)]
        rows[2]["gpu"]["order_bias_ratio"] = 1.04
        result = mod.evaluate_candidate(rows, "gpu", CRITERIA, control)
        self.assertFalse(result["detected"])

    def test_resolution_is_contiguous(self) -> None:
        self.assertEqual(
            mod.classify_resolution(
                {"plus20": True, "plus10": True, "plus5": True}, True
            ),
            "5%",
        )
        self.assertEqual(
            mod.classify_resolution(
                {"plus20": True, "plus10": True, "plus5": False}, True
            ),
            "10%",
        )
        self.assertEqual(
            mod.classify_resolution(
                {"plus20": True, "plus10": False, "plus5": False}, True
            ),
            "20%",
        )
        self.assertEqual(
            mod.classify_resolution(
                {"plus20": False, "plus10": False, "plus5": False}, True
            ),
            "target-timing-unsuitable",
        )
        self.assertEqual(
            mod.classify_resolution(
                {"plus20": False, "plus10": True, "plus5": False}, True
            ),
            "inconclusive-nonmonotonic",
        )
        self.assertEqual(
            mod.classify_resolution(
                {"plus20": True, "plus10": False, "plus5": True}, True
            ),
            "inconclusive-nonmonotonic",
        )


if __name__ == "__main__":
    unittest.main()


class LaneKRoleSeparationTests(unittest.TestCase):
    def test_cpu_wall_warning_does_not_veto_gpu_primary_resolution(self) -> None:
        cfg = {
            "fresh_process_blocks": 2,
            "comparisons": {
                "control": "baseline",
                "plus20": "plus20",
                "plus10": "plus10",
                "plus5": "plus5",
            },
            "gpu_primary_criteria": CRITERIA,
            "cpu_wall_health": {"annotation_criteria": CRITERIA},
        }
        rows = []
        for comparison, gpu_ratio in (
            ("control", 1.0),
            ("plus20", 1.15),
            ("plus10", 1.08),
            ("plus5", 1.04),
        ):
            for index in range(2):
                row = process_row(comparison, gpu_ratio)
                row["wall"]["median_log_ratio"] = math.log(
                    1.0 if comparison == "control" else 0.99
                )
                row["wall"]["order_bias_ratio"] = 1.20
                rows.append(row)
        result = mod.summarize_k003(rows, cfg)
        self.assertEqual(result["gpu_primary"]["resolution"], "5%")
        self.assertFalse(result["cpu_wall"]["invalidates_gpu_decision"])
        self.assertTrue(result["cpu_wall"]["warnings"])

    def test_k004_outcome_mapping_is_contiguous(self) -> None:
        self.assertEqual(
            mod.k004_outcome_from_gpu_resolution("5%"),
            "GPU-primary protocol accepted",
        )
        self.assertEqual(
            mod.k004_outcome_from_gpu_resolution("10%"),
            "measurement floor established",
        )
        self.assertEqual(
            mod.k004_outcome_from_gpu_resolution("20%"),
            "measurement floor established",
        )
        self.assertEqual(
            mod.k004_outcome_from_gpu_resolution("baseline-control-failed"),
            "target timing unsuitable",
        )

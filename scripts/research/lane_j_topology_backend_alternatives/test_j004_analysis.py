from __future__ import annotations

import math
import unittest

import j004_analysis as analysis


def process(
    ratio: float,
    *,
    improving_fraction: float,
    order_bias: float = 1.0,
) -> dict[str, object]:
    return {
        "gpu": {
            "median_log_ratio": math.log(ratio),
            "order_bias_ratio": order_bias,
            "improving_pair_fraction": improving_fraction,
        },
        "wall": {
            "median_log_ratio": math.log(ratio),
            "order_bias_ratio": order_bias,
            "improving_pair_fraction": improving_fraction,
        },
    }


class J004AnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.criteria = {
            "promotion_ratio_max": 0.95,
            "nonregression_ratio_max": 1.05,
            "control_max_abs_process_median_ratio": 1.02,
            "control_process_median_span_ratio": 1.03,
            "control_max_within_process_order_bias_ratio": 1.02,
            "candidate_process_effect_span_ratio": 1.05,
            "candidate_max_within_process_order_bias_ratio": 1.03,
            "candidate_min_improving_pair_fraction": 0.75,
        }

    def test_control_noise_and_six_percent_improvement_promote(self) -> None:
        controls = [
            process(1.004, improving_fraction=0.5),
            process(0.997, improving_fraction=0.5),
            process(1.002, improving_fraction=0.5),
            process(0.999, improving_fraction=0.5),
        ]
        control = analysis.evaluate_control(
            controls, "gpu", self.criteria
        )
        self.assertTrue(control["passed"])

        candidates = [
            process(0.94, improving_fraction=0.92),
            process(0.938, improving_fraction=0.92),
            process(0.942, improving_fraction=0.83),
            process(0.939, improving_fraction=0.92),
        ]
        result = analysis.evaluate_candidate(
            candidates, "gpu", self.criteria, control
        )
        self.assertTrue(result["detected_improvement"])
        self.assertTrue(result["promoted"])
        self.assertTrue(result["nonregression"])

    def test_sub_five_percent_effect_does_not_promote(self) -> None:
        controls = [
            process(1.001, improving_fraction=0.5)
            for _ in range(4)
        ]
        control = analysis.evaluate_control(
            controls, "gpu", self.criteria
        )
        candidates = [
            process(0.97, improving_fraction=0.92)
            for _ in range(4)
        ]
        result = analysis.evaluate_candidate(
            candidates, "gpu", self.criteria, control
        )
        self.assertTrue(result["detected_improvement"])
        self.assertFalse(result["promoted"])
        self.assertTrue(result["nonregression"])

    def test_one_process_inside_noise_blocks_detection(self) -> None:
        controls = [
            process(1.01, improving_fraction=0.5),
            process(0.995, improving_fraction=0.5),
            process(1.004, improving_fraction=0.5),
            process(1.002, improving_fraction=0.5),
        ]
        control = analysis.evaluate_control(
            controls, "gpu", self.criteria
        )
        self.assertTrue(control["passed"])
        candidates = [
            process(0.93, improving_fraction=0.92),
            process(0.94, improving_fraction=0.92),
            process(0.995, improving_fraction=0.92),
            process(0.94, improving_fraction=0.92),
        ]
        result = analysis.evaluate_candidate(
            candidates, "gpu", self.criteria, control
        )
        self.assertFalse(result["every_process_beyond_control_noise"])
        self.assertFalse(result["promoted"])

    def test_regression_beyond_five_percent_fails_nonregression(self) -> None:
        controls = [
            process(1.001, improving_fraction=0.5)
            for _ in range(4)
        ]
        control = analysis.evaluate_control(
            controls, "gpu", self.criteria
        )
        candidates = [
            process(1.06, improving_fraction=0.0)
            for _ in range(4)
        ]
        result = analysis.evaluate_candidate(
            candidates, "gpu", self.criteria, control
        )
        self.assertFalse(result["promoted"])
        self.assertFalse(result["nonregression"])


if __name__ == "__main__":
    unittest.main()

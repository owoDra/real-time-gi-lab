from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("run_h001.py")
spec = importlib.util.spec_from_file_location("run_h001", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class H001Tests(unittest.TestCase):
    def test_percentile_linear_interpolation(self) -> None:
        self.assertEqual(mod.percentile([1.0], 0.9), 1.0)
        self.assertAlmostEqual(mod.percentile([1.0, 2.0, 3.0], 0.5), 2.0)
        self.assertAlmostEqual(mod.percentile([1.0, 2.0], 0.25), 1.25)

    def test_summarize_process_detects_small_drift(self) -> None:
        values = [100.0 + (index % 3) for index in range(16)]
        result = mod.summarize_process(values)
        self.assertLess(result["p90_p10_ratio"], 1.10)
        self.assertLess(result["first_last_median_ratio"], 1.10)

    def test_evaluate_axis_passes_balanced_repeatable_rows(self) -> None:
        rows = []
        slots = [0, 1, 2, 3, 3, 2, 1, 0]
        for index, slot in enumerate(slots):
            rows.append({
                "slot": slot,
                "gpu_median": 100.0 + index * 0.25,
                "gpu_p90_p10_ratio": 1.02,
                "gpu_first_last_median_ratio": 1.01,
            })
        criteria = {
            "within_process_p90_p10_max": 1.10,
            "first_last_median_ratio_max": 1.10,
            "fresh_process_median_max_min_max": 1.10,
            "fresh_process_mad_over_median_max": 0.04,
            "slot_position_median_max_min_max": 1.10,
        }
        result = mod.evaluate_axis(rows, "gpu", criteria)
        self.assertTrue(result["passed"])

    def test_evaluate_axis_rejects_fresh_process_band_split(self) -> None:
        rows = []
        slots = [0, 1, 2, 3, 3, 2, 1, 0]
        values = [100.0, 101.0, 99.0, 100.0, 130.0, 131.0, 129.0, 130.0]
        for slot, value in zip(slots, values, strict=True):
            rows.append({
                "slot": slot,
                "gpu_median": value,
                "gpu_p90_p10_ratio": 1.02,
                "gpu_first_last_median_ratio": 1.01,
            })
        criteria = {
            "within_process_p90_p10_max": 1.10,
            "first_last_median_ratio_max": 1.10,
            "fresh_process_median_max_min_max": 1.10,
            "fresh_process_mad_over_median_max": 0.04,
            "slot_position_median_max_min_max": 1.10,
        }
        result = mod.evaluate_axis(rows, "gpu", criteria)
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()

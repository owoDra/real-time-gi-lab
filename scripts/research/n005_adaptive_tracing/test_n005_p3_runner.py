from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_n005_p3 as runner


def frame(rgb: float, gi: float, rays: float = 0.0) -> dict:
    return {
        "metrics": {"rgb_rms_error": rgb},
        "timing_us": {"complete_gi_gpu": gi},
        "extra": {"extra_rays_traced": rays},
    }


class N005P3RunnerTests(unittest.TestCase):
    def test_efficiency_reports_positive_incremental_cost(self) -> None:
        medians = {
            "current": {"frames": [frame(10.0, 100.0)]},
            "uniform-extra-rays": {"frames": [frame(9.0, 120.0, 9216.0)]},
            "adaptive-extra-rays": {"frames": [frame(8.0, 125.0, 9216.0)]},
        }
        view = runner.efficiency_view("decision", [576], medians)
        assert view is not None
        adaptive = view["modes"]["adaptive-extra-rays"]
        self.assertEqual(adaptive["gpu_cost_efficiency_status"], "measured")
        self.assertAlmostEqual(adaptive["median_rgb_rms_improvement_fraction"], 0.2)
        self.assertAlmostEqual(adaptive["median_incremental_complete_gi_gpu_us"], 25.0)

    def test_non_positive_incremental_cost_is_measurement_limited(self) -> None:
        medians = {
            "current": {"frames": [frame(10.0, 100.0)]},
            "uniform-extra-rays": {"frames": [frame(9.0, 100.0, 9216.0)]},
            "adaptive-extra-rays": {"frames": [frame(8.0, 95.0, 9216.0)]},
        }
        view = runner.efficiency_view("decision", [576], medians)
        assert view is not None
        for mode in ("uniform-extra-rays", "adaptive-extra-rays"):
            candidate = view["modes"][mode]
            self.assertEqual(candidate["gpu_cost_efficiency_status"], "measurement-limited")
            self.assertIsNone(
                candidate["quality_improvement_per_incremental_complete_gi_gpu_us"]
            )

    def test_control_has_no_efficiency_score(self) -> None:
        self.assertIsNone(runner.efficiency_view("control", [0], {}))


if __name__ == "__main__":
    unittest.main()

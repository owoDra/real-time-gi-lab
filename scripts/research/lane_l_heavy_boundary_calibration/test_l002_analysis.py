from __future__ import annotations

import unittest

from scripts.research.lane_l_heavy_boundary_calibration import l002_analysis as analysis


def make_rows(
    environment: str,
    process_id: str,
    block: int,
    b_scale: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    pair_orders = ["AB", "BA", "AB", "BA"]
    for pair_index, order in enumerate(pair_orders):
        a = 100.0 + pair_index
        b = a * b_scale
        for role, value in (("A", a), ("B", b)):
            rows.append(
                {
                    "phase": "measured",
                    "pair_index": pair_index,
                    "order": order,
                    "role": role,
                    "gpu_us": value,
                    "complete_wall_us": value + 50.0,
                    "environment": environment,
                    "profile": "p0",
                    "track": "primary",
                    "comparison": "control",
                    "block": block,
                    "process_id": process_id,
                }
            )
    return rows


def config() -> dict[str, object]:
    return {
        "environments": [
            {"id": "dual-context"},
            {"id": "single-context-independent-runtime"},
        ],
        "j002": {"profiles": [{"name": "p0"}]},
        "controls": {"primary": "control"},
        "timing": {"fresh_process_blocks": 2},
        "synthetic_effect_calibration": {
            "factors": [
                {"id": "plus20", "percent": 20, "factor": 1.20},
                {"id": "plus10", "percent": 10, "factor": 1.10},
                {"id": "plus5", "percent": 5, "factor": 1.05},
            ]
        },
        "detection_gate": {
            "process_count_per_control": 2,
            "minimum_positive_pair_fraction": 0.75,
        },
    }


class L002AnalysisTests(unittest.TestCase):
    def test_synthetic_process_multiplies_only_b_gpu_time(self) -> None:
        rows = make_rows("dual-context", "p0", 0, 1.0)
        result = analysis._synthetic_process(rows, 1.10)
        self.assertAlmostEqual(result["median_ratio"], 1.10, places=12)
        self.assertEqual(result["positive_pair_fraction"], 1.0)
        self.assertGreater(result["ab_median_ratio"], 1.0)
        self.assertGreater(result["ba_median_ratio"], 1.0)

    def test_effect_must_strictly_exceed_control_envelope(self) -> None:
        synthetic = [
            {
                "median_ratio": 1.20,
                "ab_median_ratio": 1.20,
                "ba_median_ratio": 1.20,
                "positive_pair_fraction": 1.0,
            },
            {
                "median_ratio": 1.20,
                "ab_median_ratio": 1.20,
                "ba_median_ratio": 1.20,
                "positive_pair_fraction": 1.0,
            },
        ]
        control = {"combined_noise_envelope_ratio": 1.20}
        result = analysis._effect_result(synthetic, 1.20, control, config())
        self.assertFalse(result["factor_beyond_control_noise"])
        self.assertFalse(result["passed"])

    def test_smallest_contiguous_floor_and_tie_break(self) -> None:
        rows: list[dict[str, object]] = []
        for environment in (
            "dual-context",
            "single-context-independent-runtime",
        ):
            rows.extend(make_rows(environment, f"{environment}-b0", 0, 1.00))
            rows.extend(make_rows(environment, f"{environment}-b1", 1, 1.01))

        result = analysis.summarize_l002(rows, config())
        self.assertEqual(result["outcome"], "measurement-floor-established")
        self.assertEqual(result["accepted_floor_percent"], 5)
        self.assertEqual(
            result["accepted_environment"],
            "single-context-independent-runtime",
        )
        for environment in result["environment_results"].values():
            self.assertTrue(environment["effects"]["plus20"]["accepted_contiguously"])
            self.assertTrue(environment["effects"]["plus10"]["accepted_contiguously"])
            self.assertTrue(environment["effects"]["plus5"]["accepted_contiguously"])


if __name__ == "__main__":
    unittest.main()

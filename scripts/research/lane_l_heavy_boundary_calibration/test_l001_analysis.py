from __future__ import annotations

import math
import unittest

from scripts.research.lane_l_heavy_boundary_calibration import l001_analysis as analysis


def process_row(
    environment: str,
    profile: str,
    track: str,
    ratio: float,
    order_bias: float = 1.0,
) -> dict[str, object]:
    axis = {
        "median_log_ratio": math.log(ratio),
        "order_bias_ratio": order_bias,
        "improving_pair_fraction": 0.5,
    }
    return {
        "environment": environment,
        "profile": profile,
        "track": track,
        "comparison": "control",
        "gpu": dict(axis),
        "wall": dict(axis),
    }


CONFIG = {
    "environments": [
        {"id": "dual-context"},
        {"id": "single-context-independent-runtime"},
    ],
    "j002": {
        "profiles": [
            {"name": "p0"},
            {"name": "p1"},
        ]
    },
    "controls": {
        "primary": "lane-e-object-local-hwrt-rebuild",
        "software": "lane-e-object-local-software-b003-rebuild",
    },
    "timing": {"fresh_process_blocks": 8},
    "gpu_control_health": {
        "control_max_abs_process_median_ratio": 1.02,
        "control_process_median_span_ratio": 1.03,
        "control_max_within_process_order_bias_ratio": 1.02,
    },
}


def complete_rows(
    dual_ratio: float = 1.0,
    single_ratio: float = 1.0,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for environment, ratio in (
        ("dual-context", dual_ratio),
        ("single-context-independent-runtime", single_ratio),
    ):
        for profile in ("p0", "p1"):
            for track in ("primary", "software"):
                rows.extend(
                    process_row(environment, profile, track, ratio)
                    for _ in range(8)
                )
    return rows


class L001AnalysisTests(unittest.TestCase):
    def test_both_environments_pass_without_ranking(self) -> None:
        result = analysis.summarize_l001(complete_rows(), CONFIG)
        self.assertEqual(result["outcome"], "multiple-usable-environments")
        self.assertFalse(result["architecture_ranking_performed"])
        self.assertFalse(result["l002_required"])
        self.assertEqual(len(result["usable_environments"]), 2)

    def test_single_context_pass_dual_context_fail(self) -> None:
        result = analysis.summarize_l001(
            complete_rows(dual_ratio=1.04, single_ratio=1.0),
            CONFIG,
        )
        self.assertEqual(result["outcome"], "usable-environment-established")
        self.assertEqual(
            result["usable_environments"],
            ["single-context-independent-runtime"],
        )
        self.assertFalse(result["l002_required"])

    def test_one_failed_profile_rejects_whole_environment(self) -> None:
        rows = complete_rows()
        for row in rows:
            if (
                row["environment"] == "single-context-independent-runtime"
                and row["profile"] == "p1"
                and row["track"] == "software"
            ):
                row["gpu"]["median_log_ratio"] = math.log(1.04)
        result = analysis.summarize_l001(rows, CONFIG)
        self.assertFalse(
            result["environment_results"][
                "single-context-independent-runtime"
            ]["passed"]
        )

    def test_both_fail_requires_l002(self) -> None:
        result = analysis.summarize_l001(
            complete_rows(dual_ratio=1.04, single_ratio=0.96),
            CONFIG,
        )
        self.assertEqual(result["outcome"], "measurement-limited")
        self.assertTrue(result["l002_required"])
        self.assertEqual(result["usable_environments"], [])


if __name__ == "__main__":
    unittest.main()

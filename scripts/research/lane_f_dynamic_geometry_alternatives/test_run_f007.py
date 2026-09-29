from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).with_name("run_f007.py")
SPEC = importlib.util.spec_from_file_location("lane_f_run_f007", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(
    variant: str,
    scenario: str,
    repeat: int,
    gpu: float,
    wall: float,
    peak: int,
) -> dict[str, object]:
    result: dict[str, object] = {
        "variant": variant,
        "scenario": scenario,
        "repeat": repeat,
        "complete_gpu_us": gpu,
        "complete_frame_wall_us": wall,
        "peak_resident_bytes": peak,
        "quality_passed": "1",
        "storage_failures": "0",
        "grid_overflow": "0",
        "moved_primitives": "796" if scenario in MODULE.DYNAMIC_SCENARIOS else "0",
        "segment_membership_changes": (
            "796" if scenario in MODULE.DYNAMIC_SCENARIOS else "0"
        ),
    }
    for field in MODULE.NUMERIC_FIELDS:
        result.setdefault(field, 0.0)
    result["complete_gpu_us"] = gpu
    result["complete_frame_wall_us"] = wall
    result["peak_resident_bytes"] = peak
    return result


def stable_matrix(
    candidate_gpu: dict[str, float],
    grid_gpu: dict[str, float] | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    grid_gpu = grid_gpu or candidate_gpu
    for repeat in range(5):
        for scenario in MODULE.SCENARIOS:
            vanilla_gpu = 1000.0 if scenario in MODULE.DYNAMIC_SCENARIOS else 600.0
            vanilla_wall = 1200.0 if scenario == "moving-rigid" else vanilla_gpu * 1.2
            hwrt_gpu = 200.0 if scenario not in MODULE.DYNAMIC_SCENARIOS else 1100.0
            software_gpu = 400.0 if scenario not in MODULE.DYNAMIC_SCENARIOS else 900.0
            rows.append(row("vanilla-software", scenario, repeat, vanilla_gpu, vanilla_wall, 1000))
            rows.append(row("combined-hwrt", scenario, repeat, hwrt_gpu, hwrt_gpu * 1.2, 2200))
            rows.append(row("combined-software", scenario, repeat, software_gpu, software_gpu * 1.2, 1200))
            rows.append(row(
                "transient-lbvh",
                scenario,
                repeat,
                candidate_gpu[scenario],
                800.0 if scenario == "moving-rigid" else candidate_gpu[scenario] * 1.2,
                2400,
            ))
            rows.append(row(
                "transient-grid",
                scenario,
                repeat,
                grid_gpu[scenario],
                800.0 if scenario == "moving-rigid" else grid_gpu[scenario] * 1.2,
                2600,
            ))
    return rows


class F007RunnerTests(unittest.TestCase):
    def test_exact_twenty_percent_repeatability_is_stable(self) -> None:
        rows = [
            row("transient-lbvh", "static", i, value, 100.0, 1000)
            for i, value in enumerate((100.0, 101.0, 102.0, 103.0, 120.0))
        ]
        summary, unstable = MODULE.summarize(rows)
        self.assertFalse(unstable)
        self.assertEqual(
            summary["transient-lbvh"]["static"]["complete_gpu_us"]["median"],
            102.0,
        )

    def test_over_twenty_percent_is_unstable(self) -> None:
        rows = [
            row("transient-grid", "static", i, value, 100.0, 1000)
            for i, value in enumerate((100.0, 101.0, 102.0, 103.0, 121.0))
        ]
        _, unstable = MODULE.summarize(rows)
        self.assertTrue(unstable)

    def test_rigid_primary_checks_dynamic_stress_and_wall(self) -> None:
        candidate: dict[str, float] = {}
        for scenario in MODULE.SCENARIOS:
            if scenario in ("static", "camera-motion", "light-motion"):
                candidate[scenario] = 205.0
            elif scenario in MODULE.STABLE_STRESS:
                candidate[scenario] = 205.0
            else:
                candidate[scenario] = 850.0

        rows = stable_matrix(candidate)
        summary, unstable = MODULE.summarize(rows)
        self.assertFalse(unstable)
        gates = MODULE.evaluate_candidate(summary, "transient-lbvh")
        self.assertTrue(gates["rigid_primary"])

        # One dynamic-stress regression must reject rigid-primary.
        bad = dict(candidate)
        bad["dense-moving"] = 1060.0
        rows = stable_matrix(bad)
        summary, _ = MODULE.summarize(rows)
        gates = MODULE.evaluate_candidate(summary, "transient-lbvh")
        self.assertFalse(gates["rigid_primary"])
        self.assertFalse(
            gates["dynamic_stress_gpu"]["dense-moving"]["passed"]
        )

    def test_tie_rule_prefers_faster_candidate_at_five_percent(self) -> None:
        lbvh: dict[str, float] = {}
        grid: dict[str, float] = {}
        for scenario in MODULE.SCENARIOS:
            if scenario in ("static", "camera-motion", "light-motion"):
                lbvh[scenario] = grid[scenario] = 205.0
            elif scenario in MODULE.STABLE_STRESS:
                lbvh[scenario] = grid[scenario] = 205.0
            else:
                lbvh[scenario] = 800.0
                grid[scenario] = 850.0
        rows = stable_matrix(lbvh, grid)
        summary, unstable = MODULE.summarize(rows)
        self.assertFalse(unstable)
        gates = {
            candidate: MODULE.evaluate_candidate(summary, candidate)
            for candidate in MODULE.CANDIDATES
        }
        self.assertTrue(gates["transient-lbvh"]["rigid_primary"])
        self.assertTrue(gates["transient-grid"]["rigid_primary"])
        decision = MODULE.decide_primary(summary, gates)
        self.assertEqual(decision["selected"], "transient-lbvh")
        self.assertEqual(
            decision["reason"],
            "moving-rigid-complete-gpu-diff-at-least-5-percent",
        )


if __name__ == "__main__":
    unittest.main()

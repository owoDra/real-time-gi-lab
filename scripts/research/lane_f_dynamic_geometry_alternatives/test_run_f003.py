from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).with_name("run_f003.py")
SPEC = importlib.util.spec_from_file_location("lane_f_run_f003", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(variant: str, scenario: str, repeat: int, gpu: float, wall: float, peak: int) -> dict[str, object]:
    result: dict[str, object] = {
        "variant": variant,
        "scenario": scenario,
        "repeat": repeat,
        "complete_gpu_us": gpu,
        "complete_frame_wall_us": wall,
        "peak_resident_bytes": peak,
        "quality_passed": "1",
        "storage_failures": "0",
    }
    for field in MODULE.NUMERIC_FIELDS:
        result.setdefault(field, 0.0)
    result["complete_gpu_us"] = gpu
    result["complete_frame_wall_us"] = wall
    result["peak_resident_bytes"] = peak
    return result


class F003RunnerTests(unittest.TestCase):
    def test_stability_uses_process_level_complete_gpu(self) -> None:
        rows = [
            row("transient-lbvh", "static", i, value, 100.0, 1000)
            for i, value in enumerate((100.0, 101.0, 102.0, 103.0, 119.0))
        ]
        summary, unstable = MODULE.summarize(rows)
        self.assertFalse(unstable)
        self.assertEqual(summary["transient-lbvh"]["static"]["complete_gpu_us"]["median"], 102.0)

    def test_over_twenty_percent_is_unstable(self) -> None:
        rows = [
            row("transient-lbvh", "static", i, value, 100.0, 1000)
            for i, value in enumerate((100.0, 101.0, 102.0, 103.0, 121.0))
        ]
        _, unstable = MODULE.summarize(rows)
        self.assertTrue(unstable)


if __name__ == "__main__":
    unittest.main()

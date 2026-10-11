from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).with_name("run_f002.py")
SPEC = importlib.util.spec_from_file_location("lane_f_run_f002", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class F002RunnerTests(unittest.TestCase):
    def test_summary_uses_process_level_medians(self) -> None:
        rows = []
        for value in (10.0, 11.0, 12.0, 13.0, 14.0):
            rows.append(
                {
                    "primitive_count": 880,
                    "is_nrep": 1,
                    "reset_us": 1.0,
                    "input_us": 1.0,
                    "aabb_us": 1.0,
                    "morton_us": 1.0,
                    "sort_us": 4.0,
                    "topology_us": 1.0,
                    "bounds_us": 1.0,
                    "builder_gpu_us": value,
                    "peak_resident_bytes": 1024,
                }
            )
        summary, unstable = MODULE.summarize_process_rows(rows)
        self.assertEqual(summary["880"]["builder_gpu_us"]["median"], 12.0)
        self.assertFalse(unstable)

    def test_summary_marks_over_twenty_percent_spread_unstable(self) -> None:
        rows = []
        for value in (10.0, 10.1, 10.2, 10.3, 12.1):
            rows.append(
                {
                    "primitive_count": 1000,
                    "is_nrep": 0,
                    "reset_us": 1.0,
                    "input_us": 1.0,
                    "aabb_us": 1.0,
                    "morton_us": 1.0,
                    "sort_us": 4.0,
                    "topology_us": 1.0,
                    "bounds_us": 1.0,
                    "builder_gpu_us": value,
                    "peak_resident_bytes": 1024,
                }
            )
        _, unstable = MODULE.summarize_process_rows(rows)
        self.assertTrue(unstable)


if __name__ == "__main__":
    unittest.main()

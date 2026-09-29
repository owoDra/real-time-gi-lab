from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("run_g002.py")
spec = importlib.util.spec_from_file_location("run_g002", MODULE_PATH)
assert spec and spec.loader
g002 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g002)


class G002HarnessTests(unittest.TestCase):
    def test_robust_stats(self) -> None:
        stats = g002.robust_stats([10.0, 11.0, 9.0])
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["median"], 10.0)
        self.assertAlmostEqual(stats["max_min_ratio"], 11.0 / 9.0)
        self.assertEqual(stats["mad"], 1.0)

    def test_plan_reverse_is_exact_reverse(self) -> None:
        canonical = g002.planned_cases(["a", "b"], ["x", "y"], "canonical")
        reverse = g002.planned_cases(["a", "b"], ["x", "y"], "reverse")
        self.assertEqual(reverse, list(reversed(canonical)))

    def test_empty_stats(self) -> None:
        stats = g002.robust_stats([])
        self.assertEqual(stats["count"], 0)
        self.assertIsNone(stats["median"])


if __name__ == "__main__":
    unittest.main()

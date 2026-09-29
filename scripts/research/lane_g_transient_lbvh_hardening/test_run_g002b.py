from __future__ import annotations
import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("run_g002b.py")
spec = importlib.util.spec_from_file_location("run_g002b", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class G002bTests(unittest.TestCase):
    def test_orientation(self) -> None:
        self.assertEqual(mod.orientation("ABBA"), ["A", "B", "B", "A"])
        self.assertEqual(mod.orientation("BAAB"), ["B", "A", "A", "B"])

    def test_robust(self) -> None:
        result = mod.robust([1.0, 1.01, 0.99, 1.02, 1.0])
        self.assertAlmostEqual(result["median"], 1.0)
        self.assertLess(result["max_min_ratio"], 1.10)
        self.assertLess(result["mad_over_median"], 0.05)

if __name__ == "__main__":
    unittest.main()

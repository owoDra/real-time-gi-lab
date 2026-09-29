from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("run_g002c.py")
spec = importlib.util.spec_from_file_location("run_g002c", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class G002cTests(unittest.TestCase):
    def test_orientation(self) -> None:
        self.assertEqual(mod.orientation("ABBA"), ["A", "B", "B", "A"])
        self.assertEqual(mod.orientation("BAAB"), ["B", "A", "A", "B"])

    def test_profile_peak_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "power_dpm_force_performance_level").write_text(
                "profile_peak\n", encoding="utf-8"
            )
            snapshot = mod.require_profile_peak(root)
            self.assertEqual(
                snapshot["power_dpm_force_performance_level"], "profile_peak"
            )

    def test_profile_peak_gate_rejects_auto(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "power_dpm_force_performance_level").write_text(
                "auto\n", encoding="utf-8"
            )
            with self.assertRaises(RuntimeError):
                mod.require_profile_peak(root)


if __name__ == "__main__":
    unittest.main()

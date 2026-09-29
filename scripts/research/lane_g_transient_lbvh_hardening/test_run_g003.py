from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("run_g003.py")
spec = importlib.util.spec_from_file_location("run_g003", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class G003RunnerTests(unittest.TestCase):
    def test_frozen_variants(self) -> None:
        self.assertEqual(
            mod.VARIANTS,
            ("transient-lbvh", "hardened-transient-lbvh", "vanilla-software"),
        )

    def test_release_set_is_only_g001_setup_only_hwrt(self) -> None:
        self.assertEqual(
            mod.RELEASED_NAMES,
            {
                "static-hwrt.vertices",
                "static-hwrt.instance",
                "static-hwrt.scratch",
            },
        )


if __name__ == "__main__":
    unittest.main()

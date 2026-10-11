from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class ShaderContractTests(unittest.TestCase):
    def test_quantized_search_keeps_tie_candidates(self) -> None:
        source = (
            ROOT / "shaders/research/integration/i001_quantized_bvh8.comp.glsl"
        ).read_text(encoding="utf-8")
        self.assertIn("best_t + tolerance", source)
        self.assertIn("token_enter > best_t + tolerance", source)

    def test_hwrt_search_keeps_tie_candidates(self) -> None:
        source = (
            ROOT / "shaders/research/integration/i001_hwrt.comp.glsl"
        ).read_text(encoding="utf-8")
        self.assertIn("best_t + tolerance", source)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHADER = ROOT / "shaders/research/lane_k_gpu_primary_calibration/k001_calibration.comp.glsl"


class LaneKShaderContractTests(unittest.TestCase):
    def test_runtime_iteration_delta_remains_observable(self) -> None:
        source = SHADER.read_text(encoding="utf-8")
        self.assertIn("pc.work_iterations", source)
        self.assertIn("iteration < pc.work_iterations", source)
        self.assertIn("source_index", source)
        self.assertIn("state_buffer.values[index] = value", source)
        self.assertNotIn("#define WORK_ITERATIONS", source)


if __name__ == "__main__":
    unittest.main()

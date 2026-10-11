"""N006 P1m2a tetra-octant direction distribution: pre-GPU static contracts."""
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHADERS = ROOT / "shaders/research/n006_interval_aware_allocation"
RUNTIME = ROOT / "src/research/n006_interval_aware_allocation/n006_runtime.cpp"
HEADER = ROOT / "src/research/n006_interval_aware_allocation/n006_runtime.hpp"
CLI = ROOT / "src/research/n006_interval_aware_allocation/n006_intervention_main.cpp"
CMAKE = ROOT / "src/research/lane_n_end_to_end_renderer/CMakeLists.txt"
RUNNER = ROOT / "scripts/research/n006_interval_aware_allocation"
FIXED = (0, 3, 5, 6)
TOKENS = (3221225474, 3223322625, 3223324678)
MASK = (1 << 32) - 1


def mix32(x: int) -> int:
    x ^= x >> 16
    x = (x * 0x7feb352d) & MASK
    x ^= x >> 15
    x = (x * 0x846ca68b) & MASK
    x ^= x >> 16
    return x


def offset_direction(token: int, ordinal: int) -> tuple[float, float, float]:
    key = token - 1
    x, y, z, c = key & 1023, (key >> 10) & 1023, (key >> 20) & 1023, key >> 30
    hash_key = (
        x * 0x9e3779b9 ^ y * 0x85ebca6b ^
        z * 0xc2b2ae35 ^ c * 0x27d4eb2d ^ ordinal * 0x165667b1
    ) & MASK
    h0 = mix32(hash_key)
    h1 = mix32(h0 ^ 0xa511e9b3)
    h2 = mix32(h0 ^ 0x63d83595)
    h3 = mix32(h0 ^ 0x9e3779b9)
    o = FIXED[ordinal]
    v = 1.0 / math.sqrt(3)
    center = [v if (o & (1 << i)) else -v for i in range(3)]
    noise = [2.0 * ((float(h) + 0.5) / 4294967296.0) - 1.0
             for h in (h1, h2, h3)]
    vec = [center[i] + 0.125 * noise[i] for i in range(3)]
    length = math.sqrt(sum(t*t for t in vec))
    return tuple(v/length for v in vec)


class TestP1m2aDirectionCalibration(unittest.TestCase):
    def test_frozen_distinct_directions_preserve_four_selected_octants(self):
        self.assertEqual(FIXED, (0, 3, 5, 6))
        self.assertEqual(TOKENS, (3221225474, 3223322625, 3223324678))
        for token in TOKENS:
            rays = [offset_direction(token, i) for i in range(4)]
            for idx, vec in enumerate(rays):
                self.assertAlmostEqual(sum(v*v for v in vec), 1.0, places=12)
                self.assertEqual(
                    sum((1 << j) for j in range(3) if vec[j] > 0), FIXED[idx]
                )
            self.assertEqual(len(set(rays)), 4)
            self.assertAlmostEqual(sum(sum(v) for v in rays), 0.0, delta=0.50)

    def test_m1a_original_shader_is_left_untouched(self):
        m1 = (SHADERS / "n006_p1m1_canonical_key_extra.comp.glsl").read_text()
        m2 = (SHADERS / "n006_p1m2a_tetra_octant_extra.comp.glsl").read_text()
        legacy = (SHADERS / "n006_extra_producer.comp.glsl").read_text()
        pat = r"vec3 extra_direction\(WorkItem item, uint ordinal\) \{.*?\n\}"
        expr = lambda s: re.sub(r"\s+", "", re.search(pat, s, re.S).group())
        self.assertEqual(expr(m1), expr(legacy))
        self.assertNotEqual(expr(m1), expr(m2))
        for mark in (
            "const uint octants[4] = uint[4](0u, 3u, 5u, 6u)",
            "return normalize(center + 0.125 * jitter)",
            "mix32(h0 ^ 0xa511e9b3u)",
            "mix32(h0 ^ 0x63d83595u)",
            "mix32(h0 ^ 0x9e3779b9u)",
            "item.ray_index = pc.rays_per_probe + extra",
            "work.items[base_count + extra] = item",
        ):
            self.assertIn(mark, m2)
        self.assertNotIn("work.items[output_id * pc.rays_per_probe] =", m2)

    def test_only_opt_in_m2a_and_same_m1_invariants(self):
        cpp, header, main, cmake = (
            RUNTIME.read_text(), HEADER.read_text(),
            CLI.read_text(), CMAKE.read_text()
        )
        self.assertIn("p1m2_tetra_octant_directions", header)
        self.assertIn("p1m2_tetra_octant_enabled", cpp)
        self.assertIn("n006_p1m2a_tetra_octant_extra.spv", cpp)
        self.assertIn("state_->p1m2_tetra_octant_stage.reset()", cpp)
        self.assertIn("request.p1m2_tetra_octant_directions", cpp)
        self.assertIn("request.p1m1_canonical_key_intervention", cpp)
        self.assertIn("trace.merged_sample_count != 12U", cpp)
        self.assertIn("n006_same_base_identity(base, item)", cpp)
        self.assertIn("--p1m2-tetra-octant-directions", main)
        self.assertIn("p1m2_tetra_octant_directions ? \"true\" : \"false\"", main)
        self.assertIn("phos-n006-p1m2a-shaders", cmake)
        runner = (RUNNER / "run_p1m1a_canonical_probe_pilot.py").read_text()
        self.assertIn('direction_mode == "p1m2a-tetra"', runner)
        self.assertIn('data.get("p1m2_tetra_octant_directions", False)', runner)
        self.assertIn('if require_ray_fate and frozen_null and label != "control":', runner)
        self.assertIn("image_delta(", runner)
        pilot = (RUNNER / "run_p1m2a_tetra_octant_pilot.py").read_text()
        self.assertIn("frozen_null=False", pilot)
        self.assertIn('direction_mode="p1m2a-tetra"', pilot)
        self.assertIn("n006-p1m2a-tetra-octant-jitter-static-c3-v1", pilot)


if __name__ == "__main__":
    unittest.main()

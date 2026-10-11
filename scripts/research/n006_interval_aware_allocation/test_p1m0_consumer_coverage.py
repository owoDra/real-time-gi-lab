"""P1m0 exact-source pretrace coverage diagnostic static contracts.

No GPU execution or input PFM oracle in this test module.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SHADER = ROOT / "shaders/research/n006_interval_aware_allocation/n006_p1m0_consumer_coverage.comp.glsl"
COMPOSITE = ROOT / "shaders/research/lane_n_end_to_end_renderer/n001_composite.comp.glsl"
CANONICAL = ROOT / "shaders/research/n006_interval_aware_allocation/n006_canonical_index.comp.glsl"
CMAKE = ROOT / "src/research/lane_n_end_to_end_renderer/CMakeLists.txt"

class TestP1m0CoverageStaticContracts(unittest.TestCase):
    def test_source_pixel_to_key_arithmetic_exactly_mirrors_composite(self):
        import re
        def compact(value: str) -> str:
            return re.sub(r"\\s+", "", value)
        diagnostic = compact(SHADER.read_text())
        for relative in (
            "shaders/research/lane_n_end_to_end_renderer/n001_composite.comp.glsl",
            "shaders/research/lane_n_end_to_end_renderer/n003_composite_software.comp.glsl",
        ):
            composite = compact((ROOT / relative).read_text())
            steps = [
                "float nx = (2.0 * (float(pixel.x) + 0.5) / float(p.counts.y)) - 1.0;",
                "float ny = 1.0 - (2.0 * (float(pixel.y) + 0.5) / float(p.counts.z));",
                "vec3 view_direction = normalize(p.camera_forward_far.xyz + p.camera_right_tan_x.xyz * (nx * p.camera_right_tan_x.w) + p.camera_up_tan_y.xyz * (ny * p.camera_up_tan_y.w));",
                "vec3 position = p.camera_pos_near.xyz + view_direction * hit.normal_t.w;",
                "float spacing = p.scene_origin_spacing.w * float(1u << cascade);",
                "ivec3 probe = ivec3(floor((position - p.scene_origin_spacing.xyz) / spacing));",
            ]
            for expr in steps:
                with self.subTest(shader=relative, expression=expr):
                    self.assertIn(compact(expr), composite)
                    self.assertIn(compact(expr), diagnostic)
            self.assertIn(compact(
                "hit.metadata.w != 1u || isnan(hit.normal_t.w) || isinf(hit.normal_t.w)"),
                diagnostic)

    def test_diagnostic_checks_postframe_byte_equality(self):
        runtime = (ROOT / "src/research/n006_interval_aware_allocation"
                   / "n006_runtime.cpp").read_text()
        self.assertIn("hits_before != hits_after || image_before != image_after", runtime)
        self.assertIn("state_->last_canonical_frame", runtime)
        cli = (ROOT / "src/research/n006_interval_aware_allocation"
               / "n006_intervention_main.cpp").read_text()
        self.assertIn('--p1m0-consumer-coverage', cli)
        self.assertIn('runtime.p1m0_consumer_coverage()', cli)

    def test_diagnostic_uses_existing_key_packing_and_bounded_slots(self):
        diagnostic = SHADER.read_text()
        canonical = CANONICAL.read_text()
        for key in ("0x7feb352du", "0x846ca68bu", "0xfffffffeu",
                    "0xffffffffu"):
            self.assertIn(key, diagnostic)
            self.assertIn(key, canonical)
        for invariant in (
            "pc.max_probe > pc.hash_capacity",
            "pc.consumer_capacity < pc.hash_capacity",
            "atomicAdd(consumers.values[slot], 1u)",
            "if (key == 0u)",
            "if (key == token)",
            "atomicAdd(stats.data[5], 1u)",
            "atomicAdd(stats.data[6], 1u)",
            "atomicAdd(stats.data[7], 1u)",
        ):
            self.assertIn(invariant, diagnostic)
        # No output storage, original GI ray/work buffer or input mutations.
        self.assertNotIn("writeonly buffer Image", diagnostic)
        self.assertNotIn("buffer WorkItem", diagnostic)
        self.assertIn("readonly buffer PrimaryHits", diagnostic)
        self.assertIn("readonly buffer KeyTokens", diagnostic)

    def test_new_target_is_n006_only(self):
        self.assertIn("n006_p1m0_consumer_coverage", CMAKE.read_text())
        self.assertTrue(SHADER.is_file())

if __name__ == "__main__":
    unittest.main()

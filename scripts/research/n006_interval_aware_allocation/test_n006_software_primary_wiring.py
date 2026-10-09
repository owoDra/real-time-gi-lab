"""N006-only integration contract: software primary and shadows require no HWRT."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
N001 = ROOT / "src/research/lane_n_end_to_end_renderer/n001_runtime.cpp"
N006 = ROOT / "src/research/n006_interval_aware_allocation/n006_runtime.cpp"
CMAKE = ROOT / "src/research/lane_n_end_to_end_renderer/CMakeLists.txt"
SHADER = ROOT / "shaders/research/lane_n_end_to_end_renderer"


class TestSoftwarePrimaryWiring(unittest.TestCase):
    def test_historical_targets_are_not_opted_in(self):
        cmake = CMAKE.read_text(encoding="utf-8")
        self.assertEqual(cmake.count("PHOS_GI_N006_SOFTWARE_PRIMARY=1"), 1)
        target = cmake.split("target_compile_definitions(phos-n006-intervention PRIVATE", 1)[1]
        self.assertIn("PHOS_GI_N006_SOFTWARE_PRIMARY=1", target.split(")", 1)[0])
        self.assertIn("phos-n003-comparison-shaders", cmake)

    def test_no_hwrt_descriptor_in_software_primary_or_composite(self):
        for name in ("n003_primary_software.comp.glsl",
                     "n003_composite_software.comp.glsl"):
            shader = (SHADER / name).read_text(encoding="utf-8")
            self.assertNotIn("GL_EXT_ray_query", shader)
            self.assertNotIn("accelerationStructureEXT", shader)
            self.assertIn("BvhNode", shader)

    def test_accepted_hwrt_path_remains_conditional_else_branch(self):
        source = N001.read_text(encoding="utf-8")
        self.assertIn("#ifdef PHOS_GI_N006_SOFTWARE_PRIMARY", source)
        self.assertIn("uses_lane_e_final_software(options.variant)", source)
        self.assertIn("n003_primary_software.spv", source)
        self.assertIn("n003_composite_software.spv", source)
        self.assertIn("n001_primary.spv", source)
        self.assertIn("n001_composite.spv", source)
        self.assertIn("n006_primary_cpu->rebuild(translated)", source)

    def test_refresh_happens_after_geometry_update(self):
        source = N006.read_text(encoding="utf-8")
        self.assertLess(source.index("impl.update_dynamic_geometry(target_state)"),
                        source.index("impl.n006_refresh_software_primary()"))
        self.assertIn("dynamic_update.gpu_us += primary_gpu_us;", source)
        self.assertIn("impl.options.variant == I001Variant::LaneEFinalSoftware", source)


if __name__ == "__main__":
    unittest.main()

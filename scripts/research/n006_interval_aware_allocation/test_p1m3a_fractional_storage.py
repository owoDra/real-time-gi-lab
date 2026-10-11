"""N006 P1m3a Q8 alternative representation: static + integer boundary tests."""
import ast
import unittest
from pathlib import Path

from run_p1m3a_fractional_storage import FROZEN, Q8, q8_value, PROTOCOL

ROOT = Path(__file__).resolve().parents[3]
SHADERS = ROOT / "shaders/research/n006_interval_aware_allocation"
ACCEPTED = ROOT / "shaders/research/lane_n_end_to_end_renderer/imported/integration"
CPP = ROOT / "src/research/n006_interval_aware_allocation/n006_runtime.cpp"
HEADER = ROOT / "src/research/n006_interval_aware_allocation/n006_runtime.hpp"
CLI = ROOT / "src/research/n006_interval_aware_allocation/n006_intervention_main.cpp"
CMAKE = ROOT / "src/research/lane_n_end_to_end_renderer/CMakeLists.txt"
HERE = ROOT / "scripts/research/n006_interval_aware_allocation"


class TestP1m3aQuantizationBoundary(unittest.TestCase):
    def test_fixed_Q8_sum_and_negative_calibration(self):
        self.assertEqual(PROTOCOL, "n006-p1m3a-fractional-q8-storage-calibration-v1")
        self.assertEqual(Q8, 256)
        self.assertEqual(sum(len(v) for v in FROZEN.values()), 4)
        for scenario, rows in FROZEN.items():
            for token, consumers, owners, base, extra, changed in rows:
                self.assertGreater(token, 0)
                self.assertGreater(owners, 0)
                self.assertGreater(consumers, 0)
                self.assertEqual(
                    q8_value(base + extra, 12) != q8_value(base, 8), changed,
                    (scenario, token),
                )
        self.assertEqual(q8_value(0, 8), 0)
        self.assertEqual(q8_value(2, 12), 43)
        self.assertEqual(q8_value(10, 8), 320)
        self.assertEqual(q8_value(10, 12), 213)
        self.assertEqual(q8_value(1, 8), 32)
        self.assertEqual(q8_value(1, 12), 21)
        self.assertEqual(q8_value(65535 * 8, 8), 65535 * Q8)
        self.assertEqual(q8_value(65535 * 12, 12), 65535 * Q8)

    def test_frozen_key_matrix_exact_and_explicit_negative_case(self):
        self.assertEqual(FROZEN, {
            "camera-motion": (
                (1084233745, 36, 2, 0, 2, True),
                (3223324678, 919, 84, 10, 0, True),
                (2152730633, 153, 1, 0, 0, False),
            ),
            "light-motion": (
                (3223324678, 875, 125, 1, 0, True),
            ),
        })

    def test_new_glsl_version_is_first_real_line(self):
        # glslang fails if a comment or literal '\\n' precedes #version.
        # Guard all P1m3a entrypoints before the user-local GPU build.
        for name in (
            "n006_p1m3_fractional_storage_update.comp.glsl",
            "n006_p1m3_fractional_weight_storage.comp.glsl",
        ):
            with self.subTest(shader=name):
                body = (SHADERS / name).read_bytes()
                self.assertTrue(
                    body.startswith(b"#version 460\n"),
                    f"{name}: GLSL #version must be byte 0 followed by a newline",
                )
                self.assertNotIn(b"\\n#version", body)

    def test_production_storage_is_intact_new_shader_is_Q8_only(self):
        orig = (ACCEPTED / "i001_storage_update.comp.glsl").read_text()
        q8 = (SHADERS / "n006_p1m3_fractional_storage_update.comp.glsl").read_text()
        self.assertIn("uint sample_value = (merged.x + merged.y / 2u) / merged.y;", orig)
        self.assertIn("const uint S = 256u;", q8)
        self.assertIn("uint sample_value = (merged.x * S + merged.y / 2u) / merged.y;", q8)
        self.assertIn("atomicAdd(slots.values[slot].data.z, S);", q8)
        self.assertIn("atomicAdd(stats.data[3], 1u)", q8)
        self.assertNotIn("const uint S = 256u;", orig)
        accepted_w = (SHADERS / "n006_canonical_weight_storage.comp.glsl").read_text()
        q8_w = (SHADERS / "n006_p1m3_fractional_weight_storage.comp.glsl").read_text()
        self.assertIn("slot.data.z != 1u", accepted_w)
        self.assertIn("slot.data.z != 256u", q8_w)
        self.assertIn("owner_count * 256u", q8_w)
        self.assertIn("owner_count > 0xffffffffu / 256u", q8_w)
        self.assertNotIn("slot.data.z != 256u", accepted_w)

    def test_new_stage_attaches_to_same_work_accum_instrumented_pipeline(self):
        cpp = CPP.read_text()
        header = HEADER.read_text()
        cli = CLI.read_text()
        cmake = CMAKE.read_text()
        for must in (
            "p1m3_fractional_storage_stage",
            "p1m3_fractional_weight_stage",
            "state_->p1m3_fractional_storage",
            "n006_p1m3_fractional_storage_update.spv",
            "n006_p1m3_fractional_weight_storage.spv",
            "p1m3_fractional_storage_stage.reset()",
            "p1m3_fractional_weight_stage.reset()",
            "impl.storage_update_stage.get()",
            "state_->canonical_weight_stage.get()",
        ):
            self.assertIn(must, cpp)
        self.assertIn("bool p1m3_fractional_storage = false", header)
        for must in (
            "--p1m3-fractional-storage",
            "if (p1m3_fractional_storage)",
            "!p1m2b_independent_state ||",
            "(!p1m3b_holdout_quality && !valid_calibration_key)",
            "p1m1_canonical_token == 2152730633U",
            "p1m1_canonical_token == 1084233745U",
        ):
            self.assertIn(must, cli)
        self.assertIn("state_->p1m3_fractional_storage", cpp)
        self.assertIn("phos-n006-p1m3a-shaders", cmake)
        self.assertIn("phos-n006-p1m2a-shaders", cmake)

    def test_runner_isolated_controls_repro_gate_and_no_quality_label(self):
        src = (HERE / "run_p1m3a_fractional_storage.py").read_text()
        ast.parse(src)
        for must in (
            "for replica in range(2):",
            'controls[0]["key_rows"] != controls[1]["key_rows"]',
            'case["coverage_sha256"] != controls[0]["coverage_sha256"]',
            'q8_value(original_base + original_extra, 12)',
            'repeated_payload != changed_payload',
            'expected_sha(VARIANT, scenario)',
            'if not predicted:',
            'summary["status"] = "fractional-storage-mechanism-go-only"',
            'summary["status"] = "fractional-storage-mechanism-stop"',
            'data.get("p1m3_fractional_storage") is not True',
            '"signed_quality_gain_established": False',
        ):
            self.assertIn(must, src)
        launcher = (HERE / "run_n006_p1m3a_fractional_storage.sh").read_text()
        for must in ("git pull --ff-only", "mise run build",
                     "unittest discover", "run_p1m3a_fractional_storage.py"):
            self.assertIn(must, launcher)


if __name__ == "__main__":
    unittest.main()

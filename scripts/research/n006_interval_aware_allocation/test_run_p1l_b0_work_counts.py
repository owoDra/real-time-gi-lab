from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_p1l_b0_work_counts as b0
from test_run_p1l_a1b_sampled_hit import (
    BYTES, GPU, synthetic_run,
)
from run_p1l_a1b_sampled_hit import SCENE_EXPECTATIONS


def fake_metric(count: int, value: int) -> dict:
    return {
        "sum": count * value, "mean": float(value),
        "p50": float(value), "p90": float(value), "p99": float(value),
        "max": value, "nonzero": count if value else 0,
    }


def fake_profile(scenario: str) -> dict:
    owners, keys = SCENE_EXPECTATIONS[scenario]
    rays = sum(keys) * 8
    pixels = 320 * 180
    primary = {name: fake_metric(pixels, 0)
               for name in b0.LABELS["primary"]}
    primary["node_pops"] = fake_metric(pixels, 10)
    shadow = {name: fake_metric(pixels, 0)
              for name in b0.LABELS["shadow"]}
    shadow["valid_pixels"] = fake_metric(pixels, 1)
    shadow["positive_cosine"] = fake_metric(pixels, 1)
    shadow["shadow_queries"] = fake_metric(pixels, 1)
    shadow["node_pops"] = fake_metric(pixels, 10)
    shadow["storage_lookups"] = fake_metric(pixels, 4)
    secondary = {name: fake_metric(rays, 0)
                 for name in b0.LABELS["secondary"]}
    secondary["instance_tests"] = fake_metric(rays, 1)
    secondary["dda_cells"] = fake_metric(rays, 2)
    secondary["hash_probes"] = fake_metric(rays, 3)
    secondary["quant_node_pops"] = fake_metric(rays, 4)
    return {
        "diagnostic_only": True,
        "uninstrumented_gpu_timing": True,
        "output_byte_identical": True,
        "pixels": pixels,
        "secondary_rays": rays,
        "primary": primary, "shadow": shadow, "secondary": secondary,
    }


def fake_case(scenario="light-motion") -> dict:
    raw = synthetic_run("lane-e-final-software", scenario)
    raw["frames"] = raw["frames"][:1]
    raw["p1l_stage_probe"] = False
    raw["p1l_stage_fast"] = False
    raw["p1l_b0_counts"] = True
    raw["p1l_hit_diagnostic_frame"] = 0
    raw["frames"][0]["p1l_b0_counts"] = fake_profile(scenario)
    return raw


class TestN006P1lB0WorkCounts(unittest.TestCase):
    def _audit(self, raw: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frames").mkdir()
            (root / "frames/candidate-000.pfm").write_bytes(BYTES)
            digest = hashlib.sha256(BYTES).hexdigest()
            with patch("run_p1l_a1b_sampled_hit.expected_sha", return_value=digest):
                return b0.audit_case(raw, root, GPU, raw["scenario"])

    def test_smoke_order_and_bound(self):
        self.assertEqual(b0.SMOKE, ("light-motion", "camera-motion"))
        self.assertEqual(len(b0.SCENARIOS), 5)
        self.assertEqual(b0.TIMEOUT_SECONDS, 600)

    def test_all_scenes_have_acceptance_and_sampled_first_cpu_hit(self):
        for scenario in b0.SCENARIOS:
            with self.subTest(scenario=scenario):
                result = self._audit(fake_case(scenario))
                self.assertEqual(result["actual_secondary_rays"],
                                 sum(SCENE_EXPECTATIONS[scenario][1]) * 8)
                self.assertEqual(result["diagnostic_counts"]["primary"]
                                 ["node_pops"]["mean"], 10.0)

    def test_missing_exact_image_rejected(self):
        raw = fake_case()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frames").mkdir()
            (root / "frames/candidate-000.pfm").write_bytes(b"wrong")
            with self.assertRaisesRegex(ValueError, "bit-identical"):
                b0.audit_case(raw, root, GPU, raw["scenario"])

    def test_wrong_backend_rejected(self):
        raw = fake_case()
        raw["variant"] = "lane-e-final-hwrt"
        with self.assertRaisesRegex(ValueError, "source contract"):
            self._audit(raw)

    def test_missing_sampled_cpu_hit_rejected(self):
        raw = fake_case()
        raw["frames"][0]["hit_diagnostics"] = None
        with self.assertRaisesRegex(ValueError, "sampled first"):
            self._audit(raw)

    def test_instrumented_image_mismatch_rejected(self):
        raw = fake_case()
        raw["frames"][0]["p1l_b0_counts"]["output_byte_identical"] = False
        with self.assertRaisesRegex(ValueError, "byte parity"):
            self._audit(raw)

    def test_shader_overflow_rejected(self):
        raw = fake_case()
        diag = raw["frames"][0]["p1l_b0_counts"]["secondary"]["overflow"]
        diag.update(fake_metric(raw["frames"][0]["p1l_b0_counts"]
                                ["secondary_rays"], 1))
        with self.assertRaisesRegex(ValueError, "overflow"):
            self._audit(raw)

    def test_missing_histogram_rejected(self):
        raw = fake_case()
        del raw["frames"][0]["p1l_b0_counts"]["secondary"]["hash_probes"]
        with self.assertRaisesRegex(ValueError, "missing/extra"):
            self._audit(raw)

    def test_synthetic_distribution_mean_mismatch_rejected(self):
        raw = fake_case()
        raw["frames"][0]["p1l_b0_counts"]["shadow"]["node_pops"]["mean"] += 1
        with self.assertRaisesRegex(ValueError, "distribution"):
            self._audit(raw)

    def test_no_regular_paths_change(self):
        root = Path(__file__).resolve().parents[3]
        source = (root / "src/research/n006_interval_aware_allocation"
                  / "n006_intervention_main.cpp").read_text(encoding="utf-8")
        self.assertIn('arg == "--p1l-b0-counts"', source)
        self.assertIn("b0_profile = runtime.p1l_b0_work_counts()", source)
        self.assertIn("if (p1l_b0_counts)", source)
        runtime = (root / "src/research/n006_interval_aware_allocation"
                   / "n006_runtime.cpp").read_text(encoding="utf-8")
        self.assertIn("instrumented output divergence", runtime)
        for shader in ("n006_p1l_primary_count.comp.glsl",
                       "n006_p1l_composite_count.comp.glsl",
                       "n006_p1l_e003_count.comp.glsl"):
            self.assertTrue(
                (root / "shaders/research/n006_interval_aware_allocation"
                 / shader).is_file(), shader)


if __name__ == "__main__":
    unittest.main()

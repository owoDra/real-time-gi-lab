from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_p1l_b1b_work_counts as b1b
from test_run_p1l_a1b_sampled_hit import (
    BYTES, GPU, synthetic_run,
)
from run_p1l_a1b_sampled_hit import SCENE_EXPECTATIONS


def metric(value: int) -> dict:
    return {
        "sum": value * b1b.PIXELS, "mean": float(value),
        "p50": float(value), "p90": float(value), "p99": float(value),
        "max": value, "nonzero": b1b.PIXELS if value else 0,
    }


def delta(value: int) -> dict:
    return {
        "signed_total": value * b1b.PIXELS,
        "mean": float(value), "p50": float(value),
        "p90": float(value), "p99": float(value),
        "min": value, "max": value,
        "fewer": b1b.PIXELS if value < 0 else 0,
        "equal": b1b.PIXELS if value == 0 else 0,
        "more": b1b.PIXELS if value > 0 else 0,
    }


def profile() -> dict:
    original = {
        "node_pops": metric(10), "triangle_tests": metric(4),
        "hit": metric(1), "stack_overflow": metric(0),
    }
    candidate = {
        "node_pops": metric(8), "triangle_tests": metric(3),
        "hit": metric(1), "stack_overflow": metric(0),
    }
    return {
        "diagnostic_only": True, "uninstrumented_gpu_timing": True,
        "original_hit_byte_exact": True, "near_first_hit_byte_exact": True,
        "pixels": b1b.PIXELS,
        "original": original, "near_first": candidate,
        "delta": {
            "node_pops": delta(-2),
            "triangle_tests": delta(-1),
        },
    }


def fake_run(scene="light-motion") -> dict:
    raw = synthetic_run(backend=b1b.VARIANT, scene=scene)
    raw.update({
        "p1l_stage_probe": False, "p1l_stage_fast": False,
        "p1l_b0_counts": False, "p1l_b1b_counts": True,
        "p1l_b1_pattern": "", "p1l_hit_diagnostic_frame": 0,
    })
    raw["frames"] = raw["frames"][:1]
    raw["frames"][0]["p1l_b1b_counts"] = profile()
    return raw


class TestN006P1lB1bWorkCounts(unittest.TestCase):
    def audit(self, raw: dict) -> dict:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "frames").mkdir()
            (root / "frames/candidate-000.pfm").write_bytes(BYTES)
            with patch(
                "run_p1l_a1b_sampled_hit.expected_sha",
                return_value=hashlib.sha256(BYTES).hexdigest(),
            ):
                return b1b.audit_case(raw, root, GPU, raw["scenario"])

    def test_all_five_scenes_pass_count_only(self):
        self.assertEqual(len(b1b.SCENARIOS), 5)
        self.assertEqual(b1b.TIMEOUT_SECONDS, 600)
        for scene in b1b.SCENARIOS:
            with self.subTest(scene=scene):
                out = self.audit(fake_run(scene))
                self.assertEqual(out["diagnostic_counts"]["delta"]
                                 ["node_pops"]["signed_total"],
                                 -2 * b1b.PIXELS)
                self.assertEqual(out["actual_secondary_rays"],
                                 sum(SCENE_EXPECTATIONS[scene][1]) * 8)
                self.assertEqual(out["decision_hint"],
                                 "MECHANISM_ONLY_NOT_GPU_SPEEDUP")

    def test_wrong_backend_fails(self):
        raw = fake_run()
        raw["variant"] = "lane-e-final-hwrt"
        with self.assertRaisesRegex(ValueError, "source contract"):
            self.audit(raw)

    def test_near_first_hit_byte_mismatch_fails(self):
        raw = fake_run()
        raw["frames"][0]["p1l_b1b_counts"]["near_first_hit_byte_exact"] = False
        with self.assertRaisesRegex(ValueError, "byte-exact"):
            self.audit(raw)

    def test_bad_original_hit_byte_mismatch_fails(self):
        raw = fake_run()
        raw["frames"][0]["p1l_b1b_counts"]["original_hit_byte_exact"] = False
        with self.assertRaisesRegex(ValueError, "byte-exact"):
            self.audit(raw)

    def test_malformed_distribution_fails(self):
        raw = fake_run()
        raw["frames"][0]["p1l_b1b_counts"]["original"]["node_pops"]["p90"] = 100
        with self.assertRaisesRegex(ValueError, "distribution"):
            self.audit(raw)

    def test_invalid_signed_total_fails(self):
        raw = fake_run()
        raw["frames"][0]["p1l_b1b_counts"]["delta"]["node_pops"]["signed_total"] = 0
        with self.assertRaisesRegex(ValueError, "delta invariant"):
            self.audit(raw)

    def test_pixels_must_partition_to_fewer_equal_more(self):
        raw = fake_run()
        raw["frames"][0]["p1l_b1b_counts"]["delta"]["triangle_tests"]["equal"] = 1
        with self.assertRaisesRegex(ValueError, "delta invariant"):
            self.audit(raw)

    def test_stack_overflow_fails(self):
        raw = fake_run()
        raw["frames"][0]["p1l_b1b_counts"]["near_first"]["stack_overflow"] = metric(1)
        with self.assertRaisesRegex(ValueError, "stack overflow"):
            self.audit(raw)

    def test_original_and_candidate_hit_flags_must_agree(self):
        raw = fake_run()
        raw["frames"][0]["p1l_b1b_counts"]["near_first"]["hit"] = metric(0)
        with self.assertRaisesRegex(ValueError, "hit flags"):
            self.audit(raw)

    def test_unsampled_oracle_fails(self):
        raw = fake_run()
        raw["frames"][0]["hit_diagnostics"] = None
        with self.assertRaisesRegex(ValueError, "sampled first"):
            self.audit(raw)

    def test_contradictory_opt_in_fails(self):
        raw = fake_run()
        raw["p1l_b0_counts"] = True
        with self.assertRaisesRegex(ValueError, "source contract"):
            self.audit(raw)

    def test_count_shader_isolated(self):
        root = Path(__file__).resolve().parents[3]
        shader = (root / "shaders/research/n006_interval_aware_allocation"
                  / "n006_p1l_b1b_primary_near_first_count.comp.glsl")
        self.assertTrue(shader.is_file())
        text = shader.read_text(encoding="utf-8")
        self.assertIn("p1l.samples[id]", text)
        self.assertIn("dot(center_x - origin, direction)", text)
        original = (root / "shaders/research/n006_interval_aware_allocation"
                    / "n006_p1l_primary_count.comp.glsl").read_text()
        self.assertNotIn("dot(center_x - origin, direction)", original)


if __name__ == "__main__":
    unittest.main()

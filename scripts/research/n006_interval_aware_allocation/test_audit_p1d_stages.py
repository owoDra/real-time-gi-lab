from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_p1d_stages import compare, finite_us, load_raw, under, PIPELINE, STAGES


def sample(gi=100.0, hash_gpu=0.0):
    timing = {key: 2.0 for key in STAGES}
    timing["complete_gi_gpu"] = gi
    timing["complete_renderer_gpu"] = gi + 3.0
    return {"timing": timing, "hash_gpu_us": hash_gpu}


class TestP1dOfflineAudit(unittest.TestCase):
    def test_known_hash_and_pipeline_are_separate(self):
        control = sample(100.0)
        hashed = sample(128.0, 8.0)
        hashed["timing"]["traversal_gpu"] += 5.0
        result = compare(control, hashed)
        self.assertEqual(result["complete_gi_delta_us"], 28.0)
        self.assertEqual(result["hash_stage_including_clear_us"], 8.0)
        self.assertTrue(result["hash_nested_inside_ray_prepare_gpu"])
        self.assertEqual(result["ray_prepare_delta_excluding_hash_us"], -8.0)
        self.assertEqual(result["subtotal_selected_pipeline_delta_including_hash_us"], 5.0)
        self.assertEqual(result["subtotal_selected_pipeline_delta_excluding_hash_us"], -3.0)
        self.assertEqual(result["unattributed_complete_gi_delta_us"], 23.0)

    def test_cpu_dynamic_wall_not_counted_as_gpu(self):
        control = sample()
        hashed = sample(110.0, 8.0)
        hashed["timing"]["dynamic_update_wall"] += 100000
        result = compare(control, hashed)
        self.assertEqual(result["unattributed_complete_gi_delta_us"], 10.0)

    def test_hash_interval_nested_inside_ray_prepare(self):
        current = sample(200.0)
        hashed = sample(222.0, 20.0)
        hashed["timing"]["ray_prepare_gpu"] += 23.0
        values = compare(current, hashed)
        self.assertEqual(values["ray_prepare_delta_excluding_hash_us"], 3.0)
        self.assertEqual(values["subtotal_selected_pipeline_delta_including_hash_us"], 23.0)
        self.assertEqual(values["unattributed_complete_gi_delta_us"], -1.0)

    def test_raw_current_uses_frozen_summary_gpu_us_field(self):
        # Regression: capture() writes complete_gi_gpu_us but the raw renderer
        # writes timing_us.complete_gi_gpu. These names must be translated.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pair-0-current"
            (root / "frames").mkdir(parents=True)
            image = b"synthetic exact-byte image"
            (root / "frames/candidate-000.pfm").write_bytes(image)
            timing = {key: 2.0 for key in STAGES}
            timing["complete_gi_gpu"] = 100.125
            timing["complete_renderer_gpu"] = 103.625
            gpu = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
            evidence = {
                "protocol_version": "n006-p1-intervention-v1",
                "mode": "current",
                "scenario": "deforming-control",
                "source_warmup_frames": 1,
                "reference_generation": "skipped",
                "device": {"name": gpu},
                "source": {"internal_correctness": True},
                "frames": [{
                    "internal_correctness": True,
                    "image": "frames/candidate-000.pfm",
                    "extra": {
                        "base_prefix_correct": True,
                        "extra_work_correct": True,
                        "extra_rays_traced": 0,
                        "gpu_hash_probe": {"executed": False},
                    },
                    "hit_diagnostics": {"substantive_mismatches": 0},
                    "stats": {
                        "visible_owners": 4172, "overflow": 0,
                        "storage_failures": 0,
                    },
                    "timing_us": timing,
                }],
            }
            (root / "n006-candidate-evidence.json").write_text(
                json.dumps(evidence), encoding="utf-8")
            expected = {
                "complete_gi_gpu_us": 100.125,
                "complete_renderer_gpu_us": 103.625,
                "image_sha256": hashlib.sha256(image).hexdigest(),
            }
            result = load_raw(Path(tmp), 0, "current", expected, gpu)
            self.assertEqual(result["timing"]["complete_gi_gpu"], 100.125)

    def test_timing_invalid(self):
        with self.assertRaisesRegex(ValueError, "invalid"):
            finite_us({"x": float("nan")}, "x")
        with self.assertRaisesRegex(ValueError, "invalid"):
            finite_us({"x": -1}, "x")

    def test_reject_escape(self):
        with self.assertRaisesRegex(ValueError, "untrusted"):
            under(Path("/tmp"), "../fake")
        with self.assertRaisesRegex(ValueError, "untrusted"):
            under(Path("/tmp"), "/absolute")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_p1l_b1_near_first as b1
from run_p1l_a1b_sampled_hit import SCENE_EXPECTATIONS, STAGE_FIELDS
from test_run_p1l_a1b_sampled_hit import BYTES, GPU, synthetic_frame, synthetic_run


def fake_run(scene: str = "static", pattern: str = b1.PREFLIGHT) -> dict:
    raw = synthetic_run(backend=b1.VARIANT, scene=scene)
    raw.update({
        "p1l_stage_probe": False,
        "p1l_stage_fast": False,
        "p1l_b0_counts": False,
        "p1l_b1_pattern": pattern,
        "p1l_hit_diagnostic_frame": 1,
        "three_arm_pattern": "",
    })
    raw["frames"] = []
    for i, arm in enumerate(pattern):
        frame = synthetic_frame(i, scene)
        frame["hit_diagnostics"] = (
            {"substantive_mismatches": 0} if i == 1 else None)
        frame["p1l_b1_arm"] = int(arm)
        frame["p1l_b1_primary_exact"] = True
        frame["p1l_b0_counts"] = None
        raw["frames"].append(frame)
    return raw


class TestN006P1lB1NearFirst(unittest.TestCase):
    def audit(self, raw: dict) -> dict:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "frames").mkdir()
            for idx in range(len(raw["frames"])):
                (root / f"frames/candidate-{idx:03d}.pfm").write_bytes(BYTES)
            digest = hashlib.sha256(BYTES).hexdigest()
            with patch("run_p1l_a1b_sampled_hit.expected_sha",
                       return_value=digest):
                with patch("run_p1l_b1_near_first.expected_sha",
                           return_value=digest):
                    return b1.audit_run(raw, root, GPU, raw["scenario"],
                                        raw["p1l_b1_pattern"])

    def test_frozen_balanced_six_abba_blocks(self):
        self.assertEqual(b1.PREFLIGHT, "01")
        self.assertEqual(b1.BALANCED, "0110"*6)
        self.assertEqual(len(b1.BALANCED), 24)
        self.assertEqual(b1.PROCESSES, 3)
        self.assertEqual(b1.TIMEOUT_SECONDS, 600)

    def test_all_five_scene_preflights(self):
        for scene in b1.SCENARIOS:
            with self.subTest(scene=scene):
                result = self.audit(fake_run(scene))
                self.assertEqual(result["measured_frames"], 2)
                self.assertEqual(result["sampled_cpu_hit_candidate_frame"], 1)
                self.assertTrue(result["baseline_primary_bytes_equal_all_frames"])
                self.assertEqual(result["frames"][1]["canonical_rays"],
                                 sum(SCENE_EXPECTATIONS[scene][1])*8)

    def test_all_scenes_matched_schedule(self):
        for scene in b1.SCENARIOS:
            with self.subTest(scene=scene):
                result = self.audit(fake_run(scene, b1.BALANCED))
                self.assertEqual(len(result["frames"]), 24)
                self.assertEqual(sum(f["arm"] for f in result["frames"]), 12)

    def test_false_primary_byte_exact_rejected(self):
        raw = fake_run()
        raw["frames"][1]["p1l_b1_primary_exact"] = False
        with self.assertRaisesRegex(ValueError, "byte parity"):
            self.audit(raw)

    def test_wrong_software_primary_arm_rejected(self):
        raw = fake_run()
        raw["frames"][1]["p1l_b1_arm"] = 0
        with self.assertRaisesRegex(ValueError, "primary arm"):
            self.audit(raw)

    def test_unsampled_n004_oracle_rejected(self):
        raw = fake_run()
        raw["frames"][0]["hit_diagnostics"] = {"substantive_mismatches": 0}
        with self.assertRaisesRegex(ValueError, "unsampled frame"):
            self.audit(raw)

    def test_no_candidate_cpu_oracle_rejected(self):
        raw = fake_run()
        raw["frames"][1]["hit_diagnostics"] = None
        with self.assertRaisesRegex(ValueError, "sampled first canonical"):
            self.audit(raw)

    def test_bad_image_sha_rejected(self):
        raw = fake_run()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "frames").mkdir()
            (root / "frames/candidate-000.pfm").write_bytes(BYTES)
            (root / "frames/candidate-001.pfm").write_bytes(b"corruption")
            with self.assertRaisesRegex(ValueError, "bit-identical"):
                b1.audit_run(raw, root, GPU, raw["scenario"], b1.PREFLIGHT)

    def test_false_target_warmup_maintenance_rejected(self):
        raw = fake_run()
        raw["target_state_warmup"]["maintenance_gpu_us"][4] = 20
        with self.assertRaisesRegex(ValueError, "warmup"):
            self.audit(raw)

    def test_original_a1b_mode_rejected(self):
        raw = fake_run()
        raw["p1l_stage_fast"] = True
        with self.assertRaisesRegex(ValueError, "source/backend"):
            self.audit(raw)

    def test_strict_15_process_aggregation(self):
        with self.assertRaisesRegex(ValueError, "15 complete"):
            b1.aggregate([])

    def test_all_180_pairs_and_gate_decision(self):
        samples = []
        for scene in b1.SCENARIOS:
            for attempt in range(3):
                run = self.audit(fake_run(scene, b1.BALANCED))
                run["attempt"] = attempt
                for frame in run["frames"]:
                    if frame["arm"] == 1:
                        # Synthetic candidate saves 10% primary and does not
                        # change other stages: non-regression at frame level.
                        prev = frame["gpu_us"]["primary_visibility_gpu"]
                        frame["gpu_us"]["primary_visibility_gpu"] = prev*0.9
                        frame["gpu_us"]["complete_gi_gpu"] -= prev*0.1
                        frame["gpu_us"]["complete_renderer_gpu"] -= prev*0.1
                samples.append(run)
        agg = b1.aggregate(samples)
        self.assertEqual(agg["processes"], 15)
        self.assertEqual(agg["measured_frames"], 360)
        self.assertEqual(agg["paired_samples"], 180)
        self.assertEqual(len(agg["winning_scenes"]), 5)
        self.assertEqual(agg["decision"], "ACCEPT_EXPLORATORY")
        for scene in b1.SCENARIOS:
            p = agg["scenarios"][scene]
            self.assertEqual(p["metrics"]["primary_visibility_gpu"]
                             ["faster_pairs"], 36)
            self.assertEqual(p["metrics"]["traversal_gpu"]
                             ["faster_pairs"], 0)
            self.assertEqual(len(p["pairs"]), 36)
            self.assertEqual(len(p["metrics"]["primary_visibility_gpu"]
                                 ["per_process_median_delta_us"]), 3)

    def test_reject_mixed_sign_primary_regression(self):
        samples = []
        for scene in b1.SCENARIOS:
            for attempt in range(3):
                run = self.audit(fake_run(scene, b1.BALANCED))
                run["attempt"] = attempt
                for frame in run["frames"]:
                    if frame["arm"] == 1:
                        frame["gpu_us"]["primary_visibility_gpu"] *= 1.02
                samples.append(run)
        self.assertEqual(b1.aggregate(samples)["decision"], "REJECT_OR_REFINE")


if __name__ == "__main__":
    unittest.main()

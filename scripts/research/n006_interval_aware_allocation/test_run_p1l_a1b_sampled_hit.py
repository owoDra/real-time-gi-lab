from __future__ import annotations

import hashlib
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_p1l_a1b_sampled_hit as p1l
from run_p1e_timing import STAGES


GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
BYTES = b"P1l synthetic bit-identical floating point HDR payload"


def synthetic_frame(index: int, scene: str) -> dict:
    owners, keys = p1l.SCENE_EXPECTATIONS[scene]
    outputs = sum(keys)
    times = {key: 1.0 for key in STAGES}
    times["traversal_maintenance_gpu"] = 0.0
    times["storage_update_gpu"] = 3.0
    build = 5.0
    times["complete_gi_gpu"] = sum(times[k] for k in STAGES) + build
    times["composite_gpu"] = 2.0
    times["complete_renderer_gpu"] = times["complete_gi_gpu"] + 2.0
    return {
        "index": index, "motion_fraction": 1.0, "owner_budget": 0,
        "internal_correctness": True,
        "image": f"frames/candidate-{index:03d}.pfm",
        "hit_diagnostics": ({"substantive_mismatches": 0} if index == 0 else None),
        "stats": {
            "visible_owners": owners, "work_items": outputs * 8,
            "outputs": outputs, "storage_updates": outputs,
            "overflow": 0, "storage_failures": 0,
            "topology_mutations": 0,
        },
        "extra": {
            "base_prefix_correct": True, "extra_work_correct": True,
            "extra_rays_traced": 0,
            "gpu_hash_probe": {"executed": False},
            "canonical": {
                "executed": True, "copyback_executed": True,
                "hash_slots": 32768, "scratch_bytes": 4489304,
                "original_work_items": owners * 32,
                "original_outputs": owners * 4,
                "canonical_work_items": outputs * 8,
                "canonical_outputs": outputs,
                "unique_by_cascade": list(keys),
                "duplicates": owners * 4 - outputs,
                "weighted_owner_total": owners * 4,
                "owner_weight_errors": 0, "invalid_keys": 0,
                "failed_inserts": 0, "index_overflows": 0,
                "collision_steps": 550,
                "total_canonical_gpu_us": build,
                "owner_weight_storage_gpu_us": 2.0,
            },
        },
        "timing_us": times,
    }


def synthetic_run(backend="lane-e-final-hwrt", scene="deforming-control") -> dict:
    owners, _ = p1l.SCENE_EXPECTATIONS[scene]
    return {
        "protocol_version": "n006-p1-intervention-v1",
        "variant": backend, "scenario": scene,
        "p1l_stage_probe": False, "p1l_stage_fast": True,
        "p1l_hit_diagnostic_frame": 0,
        "source_warmup_frames": 32, "source_warmups_correct": True,
        "source": {"internal_correctness": True, "hit_diagnostics": None},
        "mode": "current", "three_arm_pattern": "",
        "reference_generation": "skipped",
        "device": {"name": GPU},
        "target_state_warmup": {
            "frames": 8, "correct": True,
            "last_traversal_maintenance_gpu": 0,
            "last_visible_owners": owners, "last_work_items": owners * 32,
            "maintenance_gpu_us": [1500.0] + [0.0] * 7,
        },
        "frames": [synthetic_frame(i, scene) for i in range(12)],
    }


class TestN006P1lA1bSampledHit(unittest.TestCase):
    def _audit(self, raw):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frames").mkdir()
            for idx in range(12):
                (root / f"frames/candidate-{idx:03d}.pfm").write_bytes(BYTES)
            digest = hashlib.sha256(BYTES).hexdigest()
            with patch("run_p1l_a1b_sampled_hit.expected_sha",
                       return_value=digest):
                return p1l.validate_run(
                    raw, root, GPU, raw["variant"], raw["scenario"])

    def test_protocol_cases_exact(self):
        self.assertEqual(len(p1l.MATRIX), 10)
        self.assertEqual(p1l.PROCESSES_PER_CASE, 3)
        self.assertEqual(p1l.MEASURED_FRAMES, 12)
        self.assertEqual(p1l.SOURCE_WARMUPS, 32)
        self.assertEqual(p1l.TARGET_WARMUPS, 8)
        self.assertEqual(p1l.PROCESS_TIMEOUT_SECONDS, 600)

    def test_actual_frozen_rigid_sha_differs_by_backend(self):
        self.assertNotEqual(
            p1l.expected_sha("lane-e-final-hwrt", "moving-rigid"),
            p1l.expected_sha("lane-e-final-software", "moving-rigid"))
        self.assertEqual(
            p1l.expected_sha("lane-e-final-hwrt", "static"),
            p1l.expected_sha("lane-e-final-software", "static"))

    def test_all_ten_case_variable_owner_counters_and_complete_closure(self):
        for backend, scene in p1l.MATRIX:
            with self.subTest(backend=backend, scenario=scene):
                result = self._audit(synthetic_run(backend, scene))
                owners, keys = p1l.SCENE_EXPECTATIONS[scene]
                self.assertEqual(len(result["frames"]), 12)
                self.assertEqual(result["frames"][0]["canonical_ray_work_items"],
                                 sum(keys) * 8)
                self.assertEqual(result["frames"][0]["original_ray_work_items"],
                                 owners * 32)
                self.assertAlmostEqual(result["frames"][0]["stage_closure_us"], 0)
                self.assertEqual(result["target_first_maintenance_gpu_us"], 1500.0)

    def test_missing_sampled_cpu_hit_rejected(self):
        raw = synthetic_run()
        raw["frames"][0]["hit_diagnostics"] = None
        with self.assertRaisesRegex(ValueError, "sampled first canonical"):
            self._audit(raw)

    def test_false_unsampled_cpu_hit_rejected(self):
        raw = synthetic_run()
        raw["frames"][6]["hit_diagnostics"] = {"substantive_mismatches": 0}
        with self.assertRaisesRegex(ValueError, "unsampled frame"):
            self._audit(raw)

    def test_sampled_cpu_hit_mismatch_rejected(self):
        raw = synthetic_run()
        raw["frames"][0]["hit_diagnostics"]["substantive_mismatches"] = 1
        with self.assertRaisesRegex(ValueError, "sampled first canonical"):
            self._audit(raw)

    def test_old_full_oracle_protocol_rejected(self):
        raw = synthetic_run()
        raw["p1l_stage_fast"] = False
        raw["p1l_stage_probe"] = True
        with self.assertRaisesRegex(ValueError, "process source/backend"):
            self._audit(raw)

    def test_missing_owner_weight_rejected(self):
        raw = synthetic_run()
        raw["frames"][7]["extra"]["canonical"]["weighted_owner_total"] = 0
        with self.assertRaisesRegex(ValueError, "owner/hash/storage"):
            self._audit(raw)

    def test_wrong_copyback_arm_rejected(self):
        raw = synthetic_run()
        raw["frames"][2]["extra"]["canonical"]["copyback_executed"] = False
        with self.assertRaisesRegex(ValueError, "owner/hash/storage"):
            self._audit(raw)

    def test_incorrect_scene_cardinality_rejected(self):
        raw = synthetic_run(scene="static")
        raw["frames"][9]["stats"]["visible_owners"] = 4172
        with self.assertRaisesRegex(ValueError, "owner/hash/storage"):
            self._audit(raw)

    def test_current_mode_measured_frame_rejected(self):
        raw = synthetic_run()
        raw["frames"][1]["extra"]["canonical"]["executed"] = False
        with self.assertRaisesRegex(ValueError, "owner/hash/storage"):
            self._audit(raw)

    def test_cold_measured_traversal_rejected(self):
        raw = synthetic_run()
        raw["frames"][0]["timing_us"]["traversal_maintenance_gpu"] = 100.0
        with self.assertRaisesRegex(ValueError, "maintenance"):
            self._audit(raw)

    def test_bad_stage_closure_rejected(self):
        raw = synthetic_run()
        raw["frames"][6]["timing_us"]["complete_gi_gpu"] += 3
        with self.assertRaisesRegex(ValueError, "timestamps"):
            self._audit(raw)

    def test_bad_composite_closure_rejected(self):
        raw = synthetic_run()
        raw["frames"][1]["timing_us"]["complete_renderer_gpu"] += 3
        with self.assertRaisesRegex(ValueError, "timestamps"):
            self._audit(raw)

    def test_reject_second_target_warmup_maintenance(self):
        raw = synthetic_run()
        raw["target_state_warmup"]["maintenance_gpu_us"][1] = 8.0
        with self.assertRaisesRegex(ValueError, "warmup repeated"):
            self._audit(raw)

    def test_reject_bad_image_bytes(self):
        raw = synthetic_run()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "frames").mkdir()
            for idx in range(12):
                (directory / f"frames/candidate-{idx:03d}.pfm").write_bytes(BYTES)
            (directory / "frames/candidate-003.pfm").write_bytes(b"BAD")
            with patch("run_p1l_a1b_sampled_hit.expected_sha",
                       return_value=hashlib.sha256(BYTES).hexdigest()):
                with self.assertRaisesRegex(ValueError, "bit-identical"):
                    p1l.validate_run(raw, directory, GPU,
                                     raw["variant"], raw["scenario"])

    def test_summary_requires_complete_30_processes(self):
        with self.assertRaisesRegex(ValueError, "30-process"):
            p1l.summarize([])

    def test_all_thirty_process_aggregate(self):
        all_runs = []
        for backend, scene in p1l.MATRIX:
            for attempt in range(3):
                entry = self._audit(synthetic_run(backend, scene))
                entry["attempt"] = attempt
                all_runs.append(entry)
        summarized = p1l.summarize(all_runs)
        self.assertEqual(summarized["fresh_processes"], 30)
        self.assertEqual(summarized["measured_frames"], 360)
        static = summarized["per_case_gpu_stage_summary"][
            "lane-e-final-hwrt/static"]
        self.assertEqual(static["traversal_gpu"]["count"], 36)
        self.assertEqual(len(static["traversal_gpu"]["per_process_medians_us"]), 3)
        self.assertEqual(
            summarized["software_over_hwrt_median_ratios_unpaired"]
                      ["deforming-control"]["traversal_gpu"], 1.0)


if __name__ == "__main__":
    unittest.main()

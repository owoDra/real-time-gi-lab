from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_p1h_matched_canonical import (
    EXPECTED_CANONICAL_KEYS,
    EXPECTED_CANONICAL_RAYS,
    EXPECTED_OUTPUTS,
    EXPECTED_RAYS,
    MASK,
    PROCESSES,
    STAGES,
    WORK_STAGES,
    audit_process,
    summarize,
)
from run_p1d_hash_cost import EXPECTED_DUPLICATES, EXPECTED_KEYS


def example(index: int):
    canonical = MASK[index] == "1"
    gpu = {k: 1.0 for k in STAGES}
    gpu["traversal_maintenance_gpu"] = 0.0
    gpu["storage_update_gpu"] = 3.0
    gpu["dynamic_update_wall"] = 0.0
    count = EXPECTED_CANONICAL_RAYS if canonical else EXPECTED_RAYS
    outputs = EXPECTED_CANONICAL_KEYS if canonical else EXPECTED_OUTPUTS
    build = 5.0 if canonical else 0.0
    gpu["complete_gi_gpu"] = sum(gpu[k] for k in STAGES) + build
    gpu["composite_gpu"] = 2.0
    gpu["complete_renderer_gpu"] = gpu["complete_gi_gpu"] + 2.0
    return {
        "index": index,
        "motion_fraction": 1.0,
        "owner_budget": 0,
        "internal_correctness": True,
        "image": f"frames/candidate-{index:03d}.pfm",
        "hit_diagnostics": {"substantive_mismatches": 0},
        "stats": {
            "visible_owners": 4172, "work_items": count,
            "outputs": outputs, "storage_updates": outputs,
            "overflow": 0, "storage_failures": 0,
            "topology_mutations": 0, "moved_primitives": 796,
        },
        "timing_us": gpu,
        "extra": {
            "base_prefix_correct": True,
            "extra_work_correct": True,
            "extra_rays_traced": 0,
            "gpu_hash_probe": {"executed": False},
            "canonical": (
                {
                    "executed": True,
                    "original_work_items": EXPECTED_RAYS,
                    "original_outputs": EXPECTED_OUTPUTS,
                    "canonical_work_items": EXPECTED_CANONICAL_RAYS,
                    "canonical_outputs": EXPECTED_CANONICAL_KEYS,
                    "duplicates": sum(EXPECTED_DUPLICATES),
                    "unique_by_cascade": list(EXPECTED_KEYS),
                    "invalid_keys": 0, "failed_inserts": 0,
                    "index_overflows": 0, "owner_weight_errors": 0,
                    "weighted_owner_total": EXPECTED_OUTPUTS,
                    "scratch_bytes": 8421464,
                    "total_canonical_gpu_us": build,
                    "owner_weight_storage_gpu_us": 2.0,
                }
                if canonical else {"executed": False}
            )
        },
    }


def sample():
    return {
        "protocol_version": "n006-p1-intervention-v1",
        "scenario": "deforming-control",
        "mode": "current",
        "device": {"name": "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"},
        "source_warmup_frames": 32,
        "reference_generation": "skipped",
        "source": {"internal_correctness": True},
        "target_state_warmup": {
            "frames": 8, "correct": True,
            "last_traversal_maintenance_gpu": 0,
            "last_visible_owners": 4172,
            "last_work_items": EXPECTED_RAYS,
        },
        "frames": [example(i) for i in range(12)],
    }


class TestN006P1h(unittest.TestCase):
    def test_frozen_schedule_and_processes(self):
        self.assertEqual(PROCESSES, 3)
        self.assertEqual(MASK, "011001100110")
        self.assertEqual(len(WORK_STAGES), 7)
        for start in range(0, 12, 2):
            self.assertEqual(set(MASK[start:start+2]), {"0", "1"})

    def _audit(self, payload):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "frames").mkdir()
            contents = b"identical mocked PFM bytes for all frames"
            digest = hashlib.sha256(contents).hexdigest()
            for index in range(12):
                (base / f"frames/candidate-{index:03d}.pfm").write_bytes(contents)
            with patch("run_p1h_matched_canonical.EXPECTED_IMAGE_SHA256", digest):
                return audit_process(
                    payload, base, "AMD Radeon 8060S Graphics (RADV STRIX_HALO)")

    def test_all_twelve_frames_and_six_pairs(self):
        result = self._audit(sample())
        self.assertEqual(result["pair_count"], 6)
        self.assertEqual(len(result["frames"]), 12)
        self.assertEqual(result["frames"][0]["actual_gpu_rays"], EXPECTED_RAYS)
        self.assertEqual(result["frames"][1]["actual_gpu_rays"], EXPECTED_CANONICAL_RAYS)
        self.assertAlmostEqual(result["frames"][1]["gpu_stage_closure_error_us"], 0.0)
        self.assertEqual(result["frames"][1]["owner_restore_gpu_us_nested_in_storage_update"], 2.0)
        self.assertAlmostEqual(
            result["frames"][1]["post_producer_gi_work_gpu_us"]
            - result["frames"][0]["post_producer_gi_work_gpu_us"], 5.0)

    def test_reject_cold_target_update(self):
        data = sample()
        data["frames"][3]["timing_us"]["traversal_maintenance_gpu"] = 10.0
        with self.assertRaisesRegex(ValueError, "rebuilds"):
            self._audit(data)

    def test_reject_missing_storage_reweight(self):
        data = sample()
        data["frames"][5]["extra"]["canonical"]["weighted_owner_total"] = 1
        with self.assertRaisesRegex(ValueError, "canonical"):
            self._audit(data)

    def test_reject_double_counted_owner_restore(self):
        data = sample()
        data["frames"][1]["timing_us"]["complete_gi_gpu"] += 2.0
        with self.assertRaisesRegex(ValueError, "GPU stage"):
            self._audit(data)

    def test_reject_failed_warmup(self):
        data = sample()
        data["target_state_warmup"]["last_traversal_maintenance_gpu"] = 1.0
        with self.assertRaisesRegex(ValueError, "warmup"):
            self._audit(data)

    def test_reject_wrong_motion(self):
        data = sample()
        data["frames"][2]["motion_fraction"] = 0.95
        with self.assertRaisesRegex(ValueError, "correctness"):
            self._audit(data)

    def test_summary_requires_all_three_processes(self):
        with self.assertRaisesRegex(ValueError, "three"):
            summarize([self._audit(sample())])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_p1k_three_arm import (
    BACKENDS, CANONICAL_RAYS, EXPECTED_SHA, KEYS, OUTPUTS,
    PATTERN, RAYS, REPEATS, SCRATCH, STAGES, audit_run, summarize,
)


def frame(index: int) -> dict:
    arm = PATTERN[index]
    canonical = arm != "0"
    count = CANONICAL_RAYS if canonical else RAYS
    outputs = sum(KEYS) if canonical else OUTPUTS
    timing = {name: 1.0 for name in STAGES}
    timing["traversal_maintenance_gpu"] = 0.0
    timing["storage_update_gpu"] = 3.0
    extra_gpu = 5.0 if canonical else 0.0
    timing["complete_gi_gpu"] = sum(timing[k] for k in STAGES) + extra_gpu
    timing["composite_gpu"] = 2.0
    timing["complete_renderer_gpu"] = timing["complete_gi_gpu"] + 2.0
    return {
        "index": index, "motion_fraction": 1.0, "owner_budget": 0,
        "internal_correctness": True,
        "image": f"frames/candidate-{index:03d}.pfm",
        "hit_diagnostics": {"substantive_mismatches": 0},
        "stats": {
            "visible_owners": 4172, "work_items": count,
            "outputs": outputs, "storage_updates": outputs,
            "moved_primitives": 796, "topology_mutations": 0,
            "storage_failures": 0, "overflow": 0,
        },
        "timing_us": timing,
        "extra": {
            "base_prefix_correct": True, "extra_work_correct": True,
            "extra_rays_traced": 0,
            "gpu_hash_probe": {"executed": False},
            "canonical": ({
                "executed": True, "copyback_executed": arm == "1",
                "hash_slots": 32768, "scratch_bytes": SCRATCH,
                "unique_by_cascade": list(KEYS),
                "canonical_outputs": sum(KEYS),
                "canonical_work_items": CANONICAL_RAYS,
                "original_outputs": OUTPUTS, "original_work_items": RAYS,
                "duplicates": OUTPUTS - sum(KEYS),
                "weighted_owner_total": OUTPUTS,
                "owner_weight_errors": 0, "invalid_keys": 0,
                "failed_inserts": 0, "index_overflows": 0,
                "total_canonical_gpu_us": extra_gpu,
                "owner_weight_storage_gpu_us": 2.0,
            } if canonical else {"executed": False}),
        }
    }


def source(backend=BACKENDS[0]) -> dict:
    return {
        "protocol_version": "n006-p1-intervention-v1",
        "variant": backend, "scenario": "deforming-control",
        "mode": "current", "three_arm_pattern": PATTERN,
        "reference_generation": "skipped", "source_warmup_frames": 32,
        "source": {"internal_correctness": True},
        "target_state_warmup": {
            "frames": 8, "correct": True,
            "last_traversal_maintenance_gpu": 0,
            "last_visible_owners": 4172,
            "last_work_items": RAYS,
        },
        "frames": [frame(i) for i in range(len(PATTERN))],
    }


class TestN006P1kThreeArm(unittest.TestCase):
    def _run(self, record):
        contents = b"same HDR PFM bytes"
        digest = hashlib.sha256(contents).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "frames").mkdir()
            for i in range(len(PATTERN)):
                (directory / f"frames/candidate-{i:03d}.pfm").write_bytes(contents)
            with patch("run_p1k_three_arm.EXPECTED_SHA", digest):
                return audit_run(record, directory, record["variant"])

    def test_balanced_six_permutations(self):
        self.assertEqual(len(PATTERN), 18)
        self.assertEqual([PATTERN[i:i + 3] for i in range(0, 18, 3)],
                         ["012", "120", "201", "021", "102", "210"])
        self.assertEqual(REPEATS, 3)
        self.assertEqual(len(BACKENDS), 2)

    def test_valid_triplets_and_gpu_closure(self):
        audited = self._run(source())
        self.assertEqual(len(audited["frames"]), 18)
        self.assertEqual(len(audited["triplets"]), 6)
        self.assertEqual(audited["frames"][0]["actual_rays"], RAYS)
        self.assertEqual(audited["frames"][1]["actual_rays"], CANONICAL_RAYS)
        self.assertEqual(audited["frames"][2]["actual_rays"], CANONICAL_RAYS)
        self.assertEqual(audited["frames"][2]["stage_closure_us"], 0.0)
        delta = audited["triplets"][0]["deltas_us"]["direct_minus_copyback"]
        self.assertEqual(delta["post_producer_gpu_us"], 0.0)

    def test_reject_missing_original_owner_weight(self):
        invalid = source()
        invalid["frames"][5]["extra"]["canonical"]["weighted_owner_total"] = 0
        with self.assertRaisesRegex(ValueError, "copyback / lean"):
            self._run(invalid)

    def test_reject_direct_that_still_copies(self):
        invalid = source()
        invalid["frames"][2]["extra"]["canonical"]["copyback_executed"] = True
        with self.assertRaisesRegex(ValueError, "copyback / lean"):
            self._run(invalid)

    def test_reject_copyback_that_does_not_copy(self):
        invalid = source()
        invalid["frames"][1]["extra"]["canonical"]["copyback_executed"] = False
        with self.assertRaisesRegex(ValueError, "copyback / lean"):
            self._run(invalid)

    def test_reject_precanonical_timing_overlap(self):
        invalid = source()
        invalid["frames"][0]["timing_us"]["complete_gi_gpu"] += 2.0
        with self.assertRaisesRegex(ValueError, "closure"):
            self._run(invalid)

    def test_reject_extra_dynamic_maintenance(self):
        invalid = source()
        invalid["frames"][4]["timing_us"]["traversal_maintenance_gpu"] = 4.0
        with self.assertRaisesRegex(ValueError, "maintenance"):
            self._run(invalid)

    def test_reject_stale_source_pattern(self):
        invalid = source()
        invalid["three_arm_pattern"] = "012"
        with self.assertRaisesRegex(ValueError, "source/backend"):
            self._run(invalid)

    def test_six_process_summary_requires_both_backends(self):
        runs = [self._run(source(BACKENDS[0])) for _ in range(6)]
        with self.assertRaisesRegex(ValueError, "three completed"):
            summarize(runs)

    def test_summary_aggregates_36_triplets(self):
        runs = [self._run(source(name)) for name in BACKENDS for _ in range(REPEATS)]
        result = summarize(runs)
        self.assertEqual(result["measured_frames"], 108)
        self.assertEqual(result["triplets"], 36)
        self.assertEqual(result["by_backend"][BACKENDS[0]]["triplets"], 18)
        self.assertEqual(
            result["by_backend"][BACKENDS[1]]["contrasts"]
                  ["direct_minus_copyback"]["post_producer_gpu_us"]["n"], 18)


if __name__ == "__main__":
    unittest.main()

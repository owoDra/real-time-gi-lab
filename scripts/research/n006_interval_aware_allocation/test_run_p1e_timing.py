from __future__ import annotations

import unittest

from run_p1e_timing import MASK, STAGES, timing
from run_p1d_hash_cost import EXPECTED_KEYS, EXPECTED_DUPLICATES


def probe(active: bool):
    if not active:
        return {"executed": False}
    return {
        "executed": True,
        "unique_by_cascade": list(EXPECTED_KEYS),
        "duplicate_by_cascade": list(EXPECTED_DUPLICATES),
        "unique_keys": sum(EXPECTED_KEYS),
        "duplicate_outputs": sum(EXPECTED_DUPLICATES),
        "invalid_keys": 0,
        "failed_inserts": 0,
        "collision_steps": 12,
        "hash_slots": 524288,
        "scratch_bytes": 2097216,
        "complete_hash_gpu_us": 25.0,
    }


def frame(active: bool):
    t = {key: 1.0 for key in STAGES}
    t["dynamic_update_wall"] = 5000.0
    total = sum(t.values()) - t["dynamic_update_wall"] + (25.0 if active else 0.0)
    t["complete_gi_gpu"] = total
    t["composite_gpu"] = 2.0
    t["complete_renderer_gpu"] = total + 2.0
    return {"timing_us": t, "extra": {"gpu_hash_probe": probe(active)}}


class TestP1eTiming(unittest.TestCase):
    def test_frozen_schedule(self):
        self.assertEqual(MASK, "011001100110")
        self.assertEqual(sum(x == "1" for x in MASK), 6)
        for k in range(0, 12, 2):
            self.assertEqual({MASK[k], MASK[k + 1]}, {"0", "1"})

    def test_disjoint_hash_stages_reconstruct_complete_gi(self):
        x = timing(frame(True), True)
        self.assertAlmostEqual(x["stage_closure_error_gpu"], 0.0)
        self.assertEqual(x["hash_gpu"], 25.0)
        self.assertEqual(x["ray_prepare_gpu"], 1.0)
        self.assertEqual(x["dynamic_update_wall_cpu_only"], 5000.0)

    def test_current_has_no_hash_stage(self):
        x = timing(frame(False), False)
        self.assertEqual(x["hash_gpu"], 0.0)
        self.assertAlmostEqual(x["stage_closure_error_gpu"], 0.0)

    def test_reject_double_counted_hash_inside_prepare(self):
        f = frame(True)
        f["timing_us"]["ray_prepare_gpu"] += 25.0
        with self.assertRaisesRegex(ValueError, "non-overlapping"):
            timing(f, True)

    def test_reject_wrong_hash_flag(self):
        with self.assertRaisesRegex(ValueError, "wrong per-frame"):
            timing(frame(True), False)

    def test_reject_missing_stage(self):
        f = frame(False)
        del f["timing_us"]["traversal_maintenance_gpu"]
        with self.assertRaisesRegex(ValueError, "missing/invalid"):
            timing(f, False)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from audit_p1d_stages import compare, finite_us, under, PIPELINE, STAGES


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
        self.assertEqual(result["subtotal_selected_nonoverlapping_pipeline_delta_us"], 5.0)
        self.assertEqual(result["unattributed_complete_gi_delta_us"], 15.0)

    def test_cpu_dynamic_wall_not_counted_as_gpu(self):
        control = sample()
        hashed = sample(110.0, 8.0)
        hashed["timing"]["dynamic_update_wall"] += 100000
        result = compare(control, hashed)
        self.assertEqual(result["unattributed_complete_gi_delta_us"], 2.0)

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

from __future__ import annotations

import copy
import unittest

from run_p1g_canonical import (
    BASE_RAYS, CANONICAL_RAYS, CANONICAL_COUNT, validate, image_difference,
)
from run_p1d_hash_cost import EXPECTED_KEYS


def sample():
    gpu = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
    def frame(index, canonical):
        count = CANONICAL_RAYS if canonical else BASE_RAYS
        outputs = CANONICAL_COUNT if canonical else 4172 * 4
        return {
            "index": index,
            "motion_fraction": 1,
            "owner_budget": 0,
            "internal_correctness": True,
            "hit_diagnostics": {"substantive_mismatches": 0},
            "stats": {"visible_owners": 4172, "work_items": count,
                      "outputs": outputs, "storage_updates": outputs,
                      "overflow": 0, "storage_failures": 0},
            "timing_us": {"complete_gi_gpu": 2000.0},
            "extra": {
                "base_prefix_correct": True, "extra_work_correct": True,
                "extra_rays_traced": 0,
                "gpu_hash_probe": {"executed": False},
                "canonical": ({"executed": True,
                               "canonical_work_items": CANONICAL_RAYS,
                               "canonical_outputs": CANONICAL_COUNT,
                               "original_work_items": BASE_RAYS,
                               "original_outputs": 4172 * 4,
                               "duplicates": 16688-CANONICAL_COUNT,
                               "unique_by_cascade": list(EXPECTED_KEYS),
                               "invalid_keys": 0, "failed_inserts": 0,
                               "index_overflows": 0,
                               "owner_weight_errors": 0,
                               "weighted_owner_total": 4172 * 4,
                               "owner_weight_storage_gpu_us": 5.0,
                               "total_canonical_gpu_us": 90.0,
                               "scratch_bytes": 7000000}
                              if canonical else {"executed": False})
            }
        }
    return {
        "protocol_version": "n006-p1-intervention-v1",
        "mode": "current", "scenario": "deforming-control",
        "source_warmup_frames": 32,
        "reference_generation": "skipped",
        "source": {"internal_correctness": True},
        "device": {"name": gpu},
        "frames": [frame(0, False), frame(1, True)],
    }


class TestN006P1g(unittest.TestCase):
    def test_accept_real_compacted_work(self):
        r = validate(sample(), "AMD Radeon 8060S Graphics (RADV STRIX_HALO)")
        self.assertEqual(r["canonical_ray_work_items"], 24232)
        self.assertEqual(r["original_ray_work_items"], 133504)
        self.assertAlmostEqual(r["ray_count_reduction_fraction"], 0.8184923298178332)

    def test_no_false_speed_claim(self):
        r = validate(sample(), "AMD Radeon 8060S Graphics (RADV STRIX_HALO)")
        self.assertIn("NOT a controlled A/B", r["timing_claim"])

    def test_reject_unchanged_gpu_work(self):
        data = sample()
        data["frames"][1]["stats"]["work_items"] = BASE_RAYS
        with self.assertRaisesRegex(ValueError, "canonicalization"):
            validate(data, "AMD Radeon 8060S Graphics (RADV STRIX_HALO)")

    def test_reject_hash_failure(self):
        data = sample()
        data["frames"][1]["extra"]["canonical"]["failed_inserts"] = 1
        with self.assertRaisesRegex(ValueError, "canonicalization"):
            validate(data, "AMD Radeon 8060S Graphics (RADV STRIX_HALO)")

    def test_reject_counter_overflow(self):
        data = sample()
        data["frames"][1]["extra"]["canonical"]["index_overflows"] = 1
        with self.assertRaisesRegex(ValueError, "canonicalization"):
            validate(data, "AMD Radeon 8060S Graphics (RADV STRIX_HALO)")

    def test_reject_owner_weighting_error(self):
        data = sample()
        data["frames"][1]["extra"]["canonical"]["owner_weight_errors"] = 1
        with self.assertRaisesRegex(ValueError, "canonicalization"):
            validate(data, "AMD Radeon 8060S Graphics (RADV STRIX_HALO)")

    def test_reject_weighted_owner_count_mismatch(self):
        data = sample()
        data["frames"][1]["extra"]["canonical"]["weighted_owner_total"] = 16687
        with self.assertRaisesRegex(ValueError, "canonicalization"):
            validate(data, "AMD Radeon 8060S Graphics (RADV STRIX_HALO)")

    def test_image_difference_small_float_ulp(self):
        class Image:
            width = 1
            height = 1
            pixels = (0.0, 0.0, 0.0)
        a = Image()
        b = Image()
        b.pixels = (1.0e-7, 0.0, 0.0)
        report = image_difference(a, b)
        self.assertEqual(report["changed_pixels"], 1)
        self.assertEqual(report["changed_channels"], 1)
        self.assertEqual(report["channels_absolute_delta_above_1e-6"], 0)
        self.assertAlmostEqual(report["rgb_rms_delta"], (1e-14 / 3) ** 0.5)

    def test_reject_wrong_baseline(self):
        data = sample()
        data["frames"][0]["stats"]["outputs"] = CANONICAL_COUNT
        with self.assertRaisesRegex(ValueError, "baseline"):
            validate(data, "AMD Radeon 8060S Graphics (RADV STRIX_HALO)")

    def test_reject_stale_reference(self):
        data = sample()
        data["reference_generation"] = "generated"
        with self.assertRaisesRegex(ValueError, "source"):
            validate(data, "AMD Radeon 8060S Graphics (RADV STRIX_HALO)")


if __name__ == "__main__":
    unittest.main()

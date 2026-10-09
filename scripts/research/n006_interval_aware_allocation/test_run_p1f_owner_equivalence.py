from __future__ import annotations

import copy
import unittest

from run_p1f_owner_equivalence import (
    EXPECTED_DUPLICATE,
    EXPECTED_OWNERS,
    EXPECTED_UNIQUE,
    validate,
)


def sample():
    return {
        "protocol_version": "n006-p1f-owner-equivalence-v1",
        "base_work_items": EXPECTED_OWNERS * 32,
        "owner_outputs": EXPECTED_OWNERS * 4,
        "visible_owners": EXPECTED_OWNERS,
        "rays_per_probe": 8,
        "cascade_count": 4,
        "all_gpu_storage_slots_reconstructed": True,
        "cascades": [{
            "cascade": c,
            "unique_probe_keys": EXPECTED_UNIQUE[c],
            "owner_outputs": EXPECTED_OWNERS,
            "shared_keys": EXPECTED_UNIQUE[c] // 2,
            "divergent_merged_keys": 0,
            "divergent_owner_outputs": 0,
            "divergent_rounded_mean_keys": 0,
            "zero_sample_outputs": 0,
            "missing_or_bad_gpu_storage_keys": 0,
        } for c in range(4)],
    }


class TestP1fEquivalence(unittest.TestCase):
    def test_accept_identical_results(self):
        result = validate(sample())
        self.assertEqual(result["unique_probe_keys"], 3029)
        self.assertEqual(result["distinct_ray_inputs_if_canonical"], 24232)
        self.assertTrue(result["fully_equivalent"])
        self.assertEqual(result["divergent_merged_keys"], 0)

    def test_retain_divergent_output_as_negative_result(self):
        original = sample()
        original["cascades"][3]["divergent_merged_keys"] = 2
        original["cascades"][3]["divergent_owner_outputs"] = 3
        result = validate(original)
        self.assertFalse(result["fully_equivalent"])
        self.assertEqual(result["divergent_owner_outputs"], 3)

    def test_reject_storage_mismatch(self):
        original = sample()
        original["cascades"][0]["missing_or_bad_gpu_storage_keys"] = 1
        with self.assertRaisesRegex(ValueError, "storage"):
            validate(original)

    def test_reject_unexpected_owner_output_count(self):
        original = sample()
        original["cascades"][2]["owner_outputs"] -= 1
        with self.assertRaisesRegex(ValueError, "cardinality"):
            validate(original)

    def test_reject_wrong_probe_population(self):
        original = sample()
        original["cascades"][2]["unique_probe_keys"] += 1
        with self.assertRaisesRegex(ValueError, "cardinality"):
            validate(original)

    def test_reject_missing_cascade(self):
        original = sample()
        original["cascades"].pop()
        with self.assertRaisesRegex(ValueError, "four"):
            validate(original)

    def test_reject_misreported_storage_completeness(self):
        original = sample()
        original["all_gpu_storage_slots_reconstructed"] = False
        with self.assertRaisesRegex(ValueError, "storage contract"):
            validate(original)


if __name__ == "__main__":
    unittest.main()

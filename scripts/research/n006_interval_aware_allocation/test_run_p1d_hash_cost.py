import copy
import unittest

from run_p1d_hash_cost import (
    EXPECTED_DUPLICATES,
    EXPECTED_KEYS,
    ORDER,
    validate_hash,
)


def good_probe():
    return {
        "executed": True,
        "hash_slots": 65536,
        "scratch_bytes": 65536 * 4 + 64,
        "unique_keys": sum(EXPECTED_KEYS),
        "duplicate_outputs": sum(EXPECTED_DUPLICATES),
        "invalid_keys": 0,
        "failed_inserts": 0,
        "collision_steps": 137,
        "complete_hash_gpu_us": 17.0,
        "unique_by_cascade": list(EXPECTED_KEYS),
        "duplicate_by_cascade": list(EXPECTED_DUPLICATES),
    }


class TestP1dGpuHash(unittest.TestCase):
    def test_frozen_run_order(self):
        self.assertEqual(ORDER, (("current", "hash"), ("hash", "current"),
                                 ("current", "hash")))

    def test_accept_valid_probe(self):
        validate_hash(good_probe())

    def test_reject_missing_unique_key(self):
        item = good_probe()
        item["unique_by_cascade"][2] -= 1
        with self.assertRaisesRegex(ValueError, "unique key"):
            validate_hash(item)

    def test_reject_invalid_insertion(self):
        item = good_probe()
        item["failed_inserts"] += 1
        with self.assertRaisesRegex(ValueError, "total count"):
            validate_hash(item)

    def test_reject_missing_gpu_timestamp(self):
        item = good_probe()
        item["complete_hash_gpu_us"] = 0.0
        with self.assertRaisesRegex(ValueError, "timestamp"):
            validate_hash(item)

    def test_reject_non_power_of_two_table(self):
        item = good_probe()
        item["hash_slots"] = 60000
        with self.assertRaisesRegex(ValueError, "slot capacity"):
            validate_hash(item)

    def test_reject_bad_scratch_reporting(self):
        item = good_probe()
        item["scratch_bytes"] = 50
        with self.assertRaisesRegex(ValueError, "scratch"):
            validate_hash(item)


if __name__ == "__main__":
    unittest.main()

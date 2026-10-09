from __future__ import annotations

import copy
import unittest

from run_p1j_lean_hash import (
    LEAN_HASH_SLOTS,
    LEAN_SCRATCH_BYTES,
    LEGACY_SCRATCH_BYTES,
    validate_lean_case,
)
from run_p1i_cross_backend import MATRIX


def example():
    case = {
        "status": "pass",
        "additional_scratch_bytes": LEAN_SCRATCH_BYTES,
        "byte_identical_pfm_sha256": "synthetic-exact-image",
    }
    raw = {
        "frames": [
            {"extra": {"canonical": {"executed": False}}},
            {"extra": {"canonical": {
                "executed": True,
                "hash_slots": LEAN_HASH_SLOTS,
                "scratch_bytes": LEAN_SCRATCH_BYTES,
                "collision_steps": 17,
            }}},
        ]
    }
    return case, raw


class TestN006P1jLeanHash(unittest.TestCase):
    def test_frozen_ten_case_matrix_and_expected_scratch(self):
        self.assertEqual(len(MATRIX), 10)
        self.assertEqual(LEAN_HASH_SLOTS, 32768)
        self.assertEqual(LEGACY_SCRATCH_BYTES, 8421464)
        self.assertEqual(LEAN_SCRATCH_BYTES, 4489304)

    def test_valid_case_keeps_parity_and_counts(self):
        case, evidence = example()
        result = validate_lean_case(case, evidence)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["hash_slots"], 32768)
        self.assertEqual(result["hash_collision_steps"], 17)
        self.assertEqual(result["scratch_saved_bytes"], 3932160)
        self.assertAlmostEqual(result["scratch_saved_fraction"], 3932160/8421464)

    def test_reject_old_unreduced_table(self):
        case, evidence = example()
        evidence["frames"][1]["extra"]["canonical"]["hash_slots"] = 524288
        with self.assertRaisesRegex(ValueError, "slot/scratch"):
            validate_lean_case(case, evidence)

    def test_reject_scratch_accounting_mismatch(self):
        case, evidence = example()
        evidence["frames"][1]["extra"]["canonical"]["scratch_bytes"] += 4
        with self.assertRaisesRegex(ValueError, "slot/scratch"):
            validate_lean_case(case, evidence)

    def test_reject_missing_collision_count(self):
        case, evidence = example()
        del evidence["frames"][1]["extra"]["canonical"]["collision_steps"]
        with self.assertRaisesRegex(ValueError, "slot/scratch"):
            validate_lean_case(case, evidence)

    def test_reject_canonical_current_control(self):
        case, evidence = example()
        evidence["frames"][0]["extra"]["canonical"]["executed"] = True
        with self.assertRaisesRegex(ValueError, "original current"):
            validate_lean_case(case, evidence)

    def test_reject_incomplete_frame_count(self):
        case, evidence = example()
        evidence["frames"].pop()
        with self.assertRaisesRegex(ValueError, "frames"):
            validate_lean_case(case, evidence)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

import finalize_e001


class FinalizeE001Tests(unittest.TestCase):
    def test_timestamp_serialization_accepts_known_precision_difference(self) -> None:
        self.assertTrue(
            finalize_e001.timestamp_serialization_matches(
                "10.019",
                "10.019036293029785",
            )
        )

    def test_timestamp_serialization_accepts_exact_match(self) -> None:
        self.assertTrue(
            finalize_e001.timestamp_serialization_matches(
                "10.019036293029785",
                "10.019036293029785",
            )
        )

    def test_timestamp_serialization_rejects_real_difference(self) -> None:
        self.assertFalse(
            finalize_e001.timestamp_serialization_matches(
                "10.018",
                "10.019036293029785",
            )
        )

    def test_frozen_process_identity_sets_are_complete(self) -> None:
        self.assertEqual(len(finalize_e001.expected_timing_process_ids()), 160)
        self.assertEqual(len(finalize_e001.expected_validation_process_ids()), 20)


if __name__ == "__main__":
    unittest.main()

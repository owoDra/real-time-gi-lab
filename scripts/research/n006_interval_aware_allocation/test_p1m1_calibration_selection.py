"""P1m1: frozen zero/min-positive/max-positive calibration selection tests.

No GPU evidence is used in these synthetic cases.
"""
from __future__ import annotations
import unittest

import p1m1_calibration_selection as select


class TestP1m1FrozenCalibrationKeys(unittest.TestCase):
    @staticmethod
    def rows() -> list[dict[str, int]]:
        out = []
        for cascade in range(4):
            base = 1 + (cascade << 30)
            for i, pixels in enumerate((0, 1, 1, 19, 8)):
                out.append({
                    "token": base + i,
                    "consumer_pixels": pixels,
                    "producer_owner_outputs": 1 + i,
                })
        return out

    def test_selects_exactly_12_distinct_strata_without_quality_inputs(self):
        result = select.select_calibration_keys(self.rows())
        self.assertEqual(result["status"], "ready_calibration_only")
        self.assertEqual(len(result["selected"]), 12)
        for cascade in range(4):
            items = [x for x in result["selected"] if x["cascade"] == cascade]
            base = 1 + (cascade << 30)
            self.assertEqual([x["stratum"] for x in items],
                             ["zero", "low_positive", "high_positive"])
            self.assertEqual([x["token"] for x in items],
                             [base, base+1, base+3])
            self.assertEqual([x["consumer_pixels"] for x in items], [0, 1, 19])
        self.assertEqual(result["unavailable"], [])

    def test_same_positive_counts_cannot_be_misrepresented_as_two_strata(self):
        data = self.rows()
        for item in data:
            if item["consumer_pixels"] > 0:
                item["consumer_pixels"] = 1
        result = select.select_calibration_keys(data)
        self.assertEqual(result["status"], "incomplete_strata_no_intervention")
        self.assertEqual(result["actual_selection_count"], 4)
        self.assertIn("insufficient_positive_variation",
                      {e["reason"] for e in result["unavailable"]})

    def test_missing_zero_stratum_is_explicit_not_silently_substituted(self):
        data = self.rows()
        for item in data:
            if item["consumer_pixels"] == 0:
                item["consumer_pixels"] = 2
        result = select.select_calibration_keys(data)
        self.assertEqual(result["status"], "incomplete_strata_no_intervention")
        self.assertEqual(result["actual_selection_count"], 8)
        self.assertEqual(sum(x["stratum"] == "zero"
                             for x in result["unavailable"]), 4)

    def test_bad_token_order_and_multiplicity_fail_closed(self):
        for mutation in ("duplicate", "unsorted", "invalid_cascade",
                         "zero_owner", "bool_token"):
            with self.subTest(mutation=mutation):
                data = self.rows()
                if mutation == "duplicate":
                    data[1]["token"] = data[0]["token"]
                elif mutation == "unsorted":
                    data[1]["token"], data[2]["token"] = (
                        data[2]["token"], data[1]["token"])
                elif mutation == "invalid_cascade":
                    data[-1]["token"] = 0xffffffff
                elif mutation == "zero_owner":
                    data[1]["producer_owner_outputs"] = 0
                else:
                    data[0]["token"] = True
                with self.assertRaises(ValueError):
                    select.select_calibration_keys(data)


if __name__ == "__main__":
    unittest.main()

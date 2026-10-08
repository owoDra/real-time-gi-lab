from __future__ import annotations

import copy
import unittest

from run_p1b_influence import TARGETS, trace_check


def good_trace() -> dict:
    return {
        "available": True,
        "tile_id": 22890,
        "cascade": 3,
        "output_id": 42,
        "probe_x": 2,
        "probe_y": 3,
        "probe_z": 4,
        "base_ray_count": 8,
        "extra_ray_count": 4,
        "base_radiance_sum16": 100,
        "extra_radiance_sum16": 0,
        "base_zero_rays": 0,
        "extra_zero_rays": 4,
        "base_output_mean16": 13,
        "target_output_mean16": 8,
        "shared_probe_outputs": 2,
        "before_storage_sum16": 27,
        "after_storage_sum16": 22,
        "before_storage_mean16": 13.5,
        "after_storage_mean16": 11.0,
        "observed_storage_sum16": 22,
        "observed_storage_outputs": 2,
    }


class TestN006P1bInfluence(unittest.TestCase):
    def test_selected_control_pair_is_frozen(self) -> None:
        self.assertEqual(TARGETS, ((22890, 0), (22890, 3)))

    def test_valid_trace(self) -> None:
        x = trace_check(good_trace(), 22890, 3)
        self.assertEqual(x["shared_probe_outputs"], 2)
        self.assertTrue(x["output_mean_16bit_changed"])
        self.assertTrue(x["storage_probe_sum_16bit_changed"])
        self.assertFalse(x["ray_integer_total_changed"])

    def test_wrong_identity(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "identity"):
            trace_check(good_trace(), 22890, 0)

    def test_no_trace(self) -> None:
        x = good_trace()
        x["available"] = False
        with self.assertRaisesRegex(RuntimeError, "no influence trace"):
            trace_check(x, 22890, 3)

    def test_storage_mismatch(self) -> None:
        x = copy.deepcopy(good_trace())
        x["observed_storage_sum16"] = 21
        with self.assertRaisesRegex(RuntimeError, "storage aggregation"):
            trace_check(x, 22890, 3)

    def test_count_mismatch(self) -> None:
        x = copy.deepcopy(good_trace())
        x["extra_ray_count"] = 3
        with self.assertRaisesRegex(RuntimeError, "ray-count"):
            trace_check(x, 22890, 3)


if __name__ == "__main__":
    unittest.main()

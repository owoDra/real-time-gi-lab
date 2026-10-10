"""Isolated B1c audit gates; B1a historical runner defaults stay unchanged."""
from __future__ import annotations
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import run_p1l_b1_near_first as b1
from test_run_p1l_b1_near_first import fake_run
from test_run_p1l_a1b_sampled_hit import BYTES, GPU

class TestB1cAxisProxy(unittest.TestCase):
    def audit(self, raw):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "frames").mkdir()
            for i in range(len(raw["frames"])):
                (folder / f"frames/candidate-{i:03d}.pfm").write_bytes(BYTES)
            digest = hashlib.sha256(BYTES).hexdigest()
            with patch("run_p1l_a1b_sampled_hit.expected_sha", return_value=digest):
                with patch("run_p1l_b1_near_first.expected_sha", return_value=digest):
                    return b1.audit_run(raw, folder, GPU, raw["scenario"],
                                        raw["p1l_b1_pattern"], axis_proxy=True)

    def sample(self):
        obj = fake_run(scene="moving-rigid")
        obj["p1l_b1c_axis_proxy"] = True
        obj["p1l_b1c_axis_pack_cpu_us"] = 57.2
        obj["p1l_b1c_axis_packed_nodes"] = 1000
        return obj

    def test_correct_packed_axis_preflight(self):
        result = self.audit(self.sample())
        self.assertTrue(result["b1c_axis_proxy"])
        self.assertEqual(result["b1c_axis_pack_cpu_us"], 57.2)
        self.assertEqual(result["b1c_axis_packed_nodes"], 1000)

    def test_missing_opt_in_is_fail_closed(self):
        raw = self.sample()
        raw.pop("p1l_b1c_axis_proxy")
        with self.assertRaises(ValueError):
            self.audit(raw)

    def test_missing_cpu_packing_is_fail_closed(self):
        raw = self.sample()
        raw["p1l_b1c_axis_packed_nodes"] = 0
        with self.assertRaises(ValueError):
            self.audit(raw)

    def test_historical_b1a_synthetic_still_supported(self):
        raw = fake_run()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "frames").mkdir()
            for i in range(len(raw["frames"])):
                (folder / f"frames/candidate-{i:03d}.pfm").write_bytes(BYTES)
            digest = hashlib.sha256(BYTES).hexdigest()
            with patch("run_p1l_a1b_sampled_hit.expected_sha", return_value=digest):
                with patch("run_p1l_b1_near_first.expected_sha", return_value=digest):
                    result = b1.audit_run(raw, folder, GPU, raw["scenario"],
                                          raw["p1l_b1_pattern"])
        self.assertFalse(result["b1c_axis_proxy"])

if __name__ == "__main__":
    unittest.main()

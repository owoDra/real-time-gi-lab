from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("run_f001.py")
SPEC = importlib.util.spec_from_file_location("run_f001", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class F001AggregationTests(unittest.TestCase):
    def make_row(self, complete: float) -> dict[str, str]:
        row = {field: "10.0" for field in MODULE.SUMMARY_FIELDS}
        row["complete_gpu_us"] = str(complete)
        return row

    def test_median_and_stability(self) -> None:
        rows = [
            self.make_row(100.0),
            self.make_row(102.0),
            self.make_row(101.0),
            self.make_row(99.0),
            self.make_row(103.0),
        ]
        summary = MODULE.summarize_group(rows)
        self.assertEqual(summary["complete_gpu_us"]["median"], 101.0)
        self.assertFalse(summary["unstable"])

    def test_instability_gate_is_strictly_over_1_20(self) -> None:
        rows = [
            self.make_row(100.0),
            self.make_row(120.0),
            self.make_row(110.0),
            self.make_row(105.0),
            self.make_row(115.0),
        ]
        self.assertFalse(MODULE.summarize_group(rows)["unstable"])
        rows[-1] = self.make_row(121.0)
        self.assertTrue(MODULE.summarize_group(rows)["unstable"])

    def test_frozen_historical_anchor(self) -> None:
        self.assertEqual(
            MODULE.HISTORICAL_I001_GPU_US["vanilla-software"]["moving-rigid"],
            3302.675,
        )
        self.assertAlmostEqual(
            MODULE.HISTORICAL_HWRT_STRESS_RATIO["sparse-stress"],
            0.4581,
        )

    def test_prior_validation_requires_same_commit_and_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            current = base / "current"
            prior = base / "prior"
            current.mkdir()
            prior.mkdir()
            payload = {
                "passed": True,
                "plan_version": MODULE.PLAN_VERSION,
                "branch": MODULE.EXPECTED_BRANCH,
                "git_commit": "abc",
                "target_gpu": MODULE.EXPECTED_GPU,
            }
            (prior / "f001-validation.json").write_text(
                __import__("json").dumps(payload),
                encoding="utf-8",
            )
            old_root = MODULE.ROOT
            try:
                # Model the on-disk hierarchy expected by find_prior_validation.
                lane_base = (
                    base
                    / "out/research/lane-f-dynamic-geometry-alternatives"
                    / MODULE.EXPERIMENT
                )
                lane_base.mkdir(parents=True)
                actual_prior = lane_base / "20260101T000000Z"
                actual_prior.mkdir()
                (actual_prior / "f001-validation.json").write_text(
                    __import__("json").dumps(payload),
                    encoding="utf-8",
                )
                MODULE.ROOT = base
                found, loaded = MODULE.find_prior_validation("abc", current)
                self.assertEqual(found, actual_prior)
                self.assertTrue(loaded["passed"])
            finally:
                MODULE.ROOT = old_root


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "scripts/research/lane_e_timing_revalidation/run_e001.py"
CONFIG = ROOT / "research/lanes/lane-e-timing-revalidation/experiments/002-e001-config.json"


class RunnerContractTests(unittest.TestCase):
    def test_target_processes_use_vulkan_wrapper(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn('"scripts/run_with_vulkan.sh"', source)

    def test_partial_measured_process_is_zero_rerun(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn('"campaign-invalid-no-rerun"', source)
        self.assertIn('row.get("phase") == "measured"', source)
        self.assertIn("cannot be rerun", source)

    def test_completed_child_is_recovered_without_rerun(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn("recovered_complete = False", source)
        self.assertIn("health_check_timing_rows(partial_rows)", source)
        self.assertIn("do not\n                                    # rerun a completed process", source)

    def test_resume_is_source_commit_pinned(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn(
            'progress.get("git_commit") != git("rev-parse", "HEAD")',
            source,
        )

    def test_formal_shape_retains_every_raw_row(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["timing"]["expected_fresh_timing_processes"], 160)
        self.assertEqual(config["timing"]["warmup_pairs"], 4)
        self.assertEqual(config["timing"]["measured_pairs"], 12)
        self.assertEqual(config["timing"]["complete_transitions_per_sample"], 16)
        self.assertIn("len(raw_rows) != 5120", source)

    def test_allocation_lifetime_is_a_hard_gate(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn('row.get("allocation_lifetime_complete") != "1"', source)


if __name__ == "__main__":
    unittest.main()

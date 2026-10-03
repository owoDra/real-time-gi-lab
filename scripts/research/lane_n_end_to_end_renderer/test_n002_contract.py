from __future__ import annotations

import copy
import unittest
from pathlib import Path

import n002_contract as contract

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "research/lanes/lane-n-end-to-end-renderer/experiments/002-n002-config.json"


class N002ContractTest(unittest.TestCase):
    def test_frozen_config_and_playback(self) -> None:
        config = contract.load_config(CONFIG)
        manifest = contract.build_playback_manifest(config)
        self.assertEqual(len(manifest["frames"]), 5)
        self.assertEqual(
            [frame["runtime_scenario"] for frame in manifest["frames"]],
            [
                "static",
                "camera-motion",
                "light-motion",
                "moving-rigid",
                "deforming-control",
            ],
        )
        self.assertEqual(len(manifest["playback_sha256"]), 64)

    def test_topology_remains_mandatory(self) -> None:
        config = contract.load_config(CONFIG)
        completion = config["completion"]
        self.assertIn("topology-changing-high-churn", completion["required_scenarios"])
        self.assertEqual(
            completion["pending_after_this_phase"],
            ["topology-changing-high-churn"],
        )

    def test_cannot_smuggle_performance_threshold_into_core(self) -> None:
        config = contract.load_config(CONFIG)
        modified = copy.deepcopy(config)
        modified["timing_boundary"]["formal_performance_threshold"] = 0.95
        with self.assertRaises(contract.ContractError):
            contract.validate_config(modified)

    def test_cannot_drop_topology_completion_gate(self) -> None:
        config = contract.load_config(CONFIG)
        modified = copy.deepcopy(config)
        modified["completion"]["pending_after_this_phase"] = []
        with self.assertRaises(contract.ContractError):
            contract.validate_config(modified)


if __name__ == "__main__":
    unittest.main()

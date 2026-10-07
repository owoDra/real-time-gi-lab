from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import n005_p3_contract as contract


class N005P3ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = (
            ROOT
            / "research/lanes/n005-adaptive-tracing/experiments/"
              "003-p3-formal-comparison-config.json"
        )
        cls.config = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_repository_config_is_frozen(self) -> None:
        contract.validate_config(copy.deepcopy(self.config))

    def test_completed_campaign_rerun_is_forbidden(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["completed_campaign_rerun_budget"] = 1
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)

    def test_candidate_threshold_drift_is_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["candidate"]["normalized_depth_threshold"] = 0.02
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)

    def test_repetition_count_drift_is_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["repetition"]["count"] = 3
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)

    def test_mode_order_drift_is_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["repetition"]["mode_order_rotation"][0] = [
            "adaptive-extra-rays", "uniform-extra-rays", "current"
        ]
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)

    def test_reference_seed_cannot_be_formal_sample(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["reference"]["seed_is_formal_repetition"] = True
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)

    def test_sample_exclusion_cannot_be_enabled(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["decision_discipline"]["sample_exclusion"] = "allowed"
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)


if __name__ == "__main__":
    unittest.main()

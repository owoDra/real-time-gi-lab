from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import n005_p2_contract as contract


class N005P2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = (
            ROOT
            / "research/lanes/n005-adaptive-tracing/experiments/"
              "002-p2-equal-budget-candidates-config.json"
        )
        cls.config = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_repository_config_is_frozen(self) -> None:
        contract.validate_config(copy.deepcopy(self.config))

    def test_threshold_drift_is_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["candidate"]["normalized_depth_threshold"] = 0.02
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)

    def test_budget_drift_is_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["candidate"]["owner_budget_per_active_frame"] = 575
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)

    def test_control_extra_work_is_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["state_change_schedule"]["static"] = [576]
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)

    def test_equal_actual_ray_gate_is_required(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["equal_budget_gate"]["uniform_adaptive_must_match"] = False
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)


if __name__ == "__main__":
    unittest.main()

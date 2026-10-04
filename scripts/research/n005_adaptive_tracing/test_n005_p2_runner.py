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
import run_n005_p2 as runner


class N005P2RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = (
            ROOT
            / "research/lanes/n005-adaptive-tracing/experiments/"
              "002-p2-equal-budget-candidates-config.json"
        )
        cls.config = json.loads(path.read_text(encoding="utf-8"))
        contract.validate_config(copy.deepcopy(cls.config))

    def frame(self, rays: int, *, eligible: int = 800, selected: int = 576) -> dict:
        return {
            "internal_correctness": True,
            "stats": {"overflow": 0, "storage_failures": 0},
            "extra": {
                "base_prefix_correct": True,
                "extra_work_correct": True,
                "extra_rays_requested": rays,
                "extra_rays_traced": rays,
                "extra_work_items": rays,
                "eligible_owner_count": eligible if rays else 0,
                "selected_owner_count": selected if rays else 0,
            },
        }

    def analyzed(self, frames: list[dict]) -> dict:
        return {
            "source": {"internal_correctness": True},
            "frames": frames,
        }

    def test_active_frame_accepts_frozen_9216_rays(self) -> None:
        analyzed = self.analyzed([self.frame(9216)])
        runner.validate_mode_case(
            "camera-abrupt-reveal",
            "adaptive-extra-rays",
            [576],
            analyzed,
            self.config,
        )

    def test_inactive_control_rejects_extra_rays(self) -> None:
        analyzed = self.analyzed([self.frame(9216)])
        with self.assertRaises(contract.ContractError):
            runner.validate_mode_case(
                "static",
                "adaptive-extra-rays",
                [0],
                analyzed,
                self.config,
            )

    def test_adaptive_eligibility_shortfall_is_rejected(self) -> None:
        analyzed = self.analyzed([self.frame(9216, eligible=575)])
        with self.assertRaises(contract.ContractError):
            runner.validate_mode_case(
                "camera-gradual-motion",
                "adaptive-extra-rays",
                [576],
                analyzed,
                self.config,
            )

    def test_uniform_adaptive_actual_ray_mismatch_is_rejected(self) -> None:
        uniform = {"frames": [self.frame(9216)]}
        adaptive = {"frames": [self.frame(9200)]}
        with self.assertRaises(contract.ContractError):
            runner.validate_equal_budget("camera-gradual-motion", uniform, adaptive)

    def test_equal_budget_accepts_matching_zero_and_active_frames(self) -> None:
        uniform = {"frames": [self.frame(9216), self.frame(0)]}
        adaptive = {"frames": [self.frame(9216), self.frame(0)]}
        runner.validate_equal_budget("camera-abrupt-reveal", uniform, adaptive)


if __name__ == "__main__":
    unittest.main()

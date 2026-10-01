from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT
    / "research/lanes/lane-m-topology-backend-crossover/experiments"
    / "001-topology-backend-crossover-config.json"
)


class ProtocolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_lane_l_floor_and_decision_gate_are_exact(self) -> None:
        gate = self.config["performance_gate"]
        self.assertEqual(gate["threshold"], 0.20)
        self.assertEqual(gate["promotion_ratio_max"], 0.80)
        self.assertEqual(gate["regression_ratio_min"], 1.20)
        self.assertEqual(gate["minimum_directional_pair_fraction"], 0.75)
        self.assertTrue(
            gate["effect_must_exceed_fresh_control_noise_envelope_strictly"]
        )
        self.assertTrue(gate["sub20_ranking_forbidden"])

    def test_memory_is_hard_guard(self) -> None:
        memory = self.config["memory_gate"]
        self.assertEqual(memory["persistent_ratio_max"], 1.25)
        self.assertEqual(memory["true_peak_ratio_max"], 1.25)
        self.assertTrue(memory["allocation_lifetime_accounting_complete"])
        self.assertEqual(memory["decision"], "hard")

    def test_sample_shape_and_zero_rerun_are_frozen(self) -> None:
        timing = self.config["timing"]
        self.assertEqual(timing["warmup_pairs"], 4)
        self.assertEqual(timing["measured_pairs"], 12)
        self.assertEqual(timing["fresh_process_blocks"], 8)
        self.assertEqual(
            self.config["recurrent_boundary"]["batch_transitions"], 16
        )
        self.assertEqual(timing["sample_exclusion"], "forbidden")
        self.assertEqual(timing["instability_rerun_budget"], 0)
        self.assertEqual(timing["completed_campaign_rerun_budget"], 0)
        self.assertFalse(timing["accepted_timing_validation"])

    def test_j002_materialized_contract_pins_full_profile_set(self) -> None:
        profiles = {
            item["name"] for item in self.config["j002"]["profiles"]
        }
        self.assertEqual(
            profiles,
            {
                "small-global-high",
                "medium-global-representative",
                "medium-local-high",
                "large-global-high",
                "large-local-high",
            },
        )
        scenario_profiles = {
            item["profile"] for item in self.config["scenarios"]
        }
        self.assertTrue(scenario_profiles <= profiles)
        self.assertEqual(
            scenario_profiles,
            {
                "medium-global-representative",
                "large-global-high",
                "large-local-high",
            },
        )

    def test_scenarios_cover_representative_high_churn_and_guard(self) -> None:
        scenarios = {
            item["id"]: item for item in self.config["scenarios"]
        }
        self.assertEqual(
            scenarios["topology-changing-object-local"]["base_primitive_count"],
            796,
        )
        self.assertEqual(
            scenarios["topology-changing-object-local"][
                "nominal_replacement_fraction"
            ],
            0.25,
        )
        self.assertEqual(
            scenarios["high-churn-global"]["base_primitive_count"], 8192
        )
        self.assertEqual(
            scenarios["high-churn-global"]["nominal_replacement_fraction"],
            0.50,
        )
        self.assertEqual(
            scenarios["high-churn-local"]["locality"], "local"
        )
        self.assertFalse(
            scenarios["stable-no-change-guard"][
                "topology_mutation_required"
            ]
        )

    def test_all_three_backends_and_conditional_direct_pair_are_frozen(self) -> None:
        self.assertEqual(
            self.config["timing"]["first_stage_comparisons"],
            ["control", "lbvh", "clustered"],
        )
        direct = self.config["conditional_direct_crossover"]
        self.assertEqual(direct["control_comparison"], "lbvh-control")
        self.assertEqual(
            direct["candidate_comparison"], "clustered-vs-lbvh"
        )
        self.assertTrue(direct["same_20_percent_gate"])

    def test_no_duplicate_lane_m_formal_runtime_source(self) -> None:
        # Lane M must extend the qualified J004 orchestration at build time
        # rather than fork a second 2k+ line formal process source.
        duplicate = (
            ROOT
            / "src/research/lane_m_topology_backend_crossover"
            / "m001_formal_process.cpp"
        )
        self.assertFalse(duplicate.exists())


if __name__ == "__main__":
    unittest.main()

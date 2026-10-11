"""P1m2b pre-GPU selection and strict separate mode contracts."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

from run_p1m2b_independent_state import (
    SCENARIOS, ARMS, MAX_TREATMENT_CELLS, select_frozen_keys,
)

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "scripts/research/n006_interval_aware_allocation"
CLI = ROOT / "src/research/n006_interval_aware_allocation/n006_intervention_main.cpp"
RUNTIME = ROOT / "src/research/n006_interval_aware_allocation/n006_runtime.cpp"
SHADERS = ROOT / "shaders/research/n006_interval_aware_allocation"


def token(cascade: int, local: int) -> int:
    return (cascade << 30) + local + 1


def row(cascade: int, local: int, consumers: int) -> dict[str, int]:
    return {
        "token": token(cascade, local),
        "consumer_pixels": consumers,
        "producer_owner_outputs": 1,
    }


class TestIndependentStateM2b(unittest.TestCase):
    def test_max_and_zero_selection_token_tiebreak_and_bounded(self):
        rows = sorted([
            *[row(c, 0, 0) for c in range(4)],
            *[row(c, 1, 9) for c in range(4)],
            *[row(c, 2, 9) for c in range(4)],
        ], key=lambda x: x["token"])
        selected = select_frozen_keys(rows)
        self.assertEqual(len(selected["selected"]), 8)
        self.assertEqual(len(selected["missing_strata"]), 0)
        for cascade in range(4):
            chosen = [x for x in selected["selected"]
                      if x["cascade"] == cascade]
            self.assertEqual(chosen[0]["stratum"], "max_consumer")
            self.assertEqual(chosen[0]["token"], token(cascade, 1))
            self.assertEqual(chosen[1]["stratum"], "zero_consumer")
            self.assertEqual(chosen[1]["token"], token(cascade, 0))

    def test_unavailable_strata_and_all_zero_dedupe(self):
        rows = [row(0, 0, 0), row(1, 0, 4), row(2, 0, 1)]
        chosen = select_frozen_keys(rows)
        self.assertEqual(len(chosen["selected"]), 3)
        self.assertEqual(len({x["token"] for x in chosen["selected"]}), 3)
        self.assertTrue(any(x.get("reason") == "same_key_deduplicated"
                            for x in chosen["missing_strata"]))
        self.assertTrue(any(x.get("stratum") == "zero_consumer" and
                            x["cascade"] == 1
                            for x in chosen["missing_strata"]))
        self.assertTrue(any(x["cascade"] == 3 for x in chosen["missing_strata"]))

    def test_reject_unsorted_duplicate_invalid_and_unsupported_rows(self):
        for rows in (
            [], [row(0, 1, 1), row(0, 0, 1)],
            [row(0, 0, 1), row(0, 0, 1)],
            [{"token": 0, "consumer_pixels": 0,
              "producer_owner_outputs": 1}],
            [{"token": 0xffffffff, "consumer_pixels": 0,
              "producer_owner_outputs": 1}],
            [row(0, 0, -1)],
            [{"token": 1, "consumer_pixels": 0,
              "producer_owner_outputs": 0}],
            [{"token": 1, "consumer_pixels": True,
              "producer_owner_outputs": 1}],
        ):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                select_frozen_keys(rows)

    def test_critical_runner_invariants_and_python_parse(self):
        self.assertEqual(SCENARIOS, ("camera-motion", "light-motion"))
        self.assertEqual(ARMS, ("p1m1a-original", "p1m2a-tetra"))
        self.assertEqual(MAX_TREATMENT_CELLS, 32)
        source = (RUNNER / "run_p1m2b_independent_state.py").read_text()
        ast.parse(source)
        for guard in (
            'for replica in (0, 1):',
            'controls[0]["key_rows"] != controls[1]["key_rows"]',
            "frozen = select_frozen_keys(controls[0][\"key_rows\"])",
            "Selection table is persisted BEFORE any extra GPU work",
            "summary[\"total_treatment_cells\"] >= MAX_TREATMENT_CELLS",
            "if delta[\"changed_rgb_pixels\"]:",
            "again != payload",
            '"bounded-observable-null-stop"',
            '"observable-influence-screen-complete"',
            'hashlib.sha256(image.read_bytes()).hexdigest()',
            'audit_coverage(raw_coverage, scenario)',
            'FROZEN_M0[scenario]',
            'expected_sha(VARIANT, scenario)',
            'data.get("p1m2b_independent_state") is not True',
            'data.get("p1m2_tetra_octant_directions") is not',
            '"--p1m2b-independent-state"',
            'trace.get("merged_sample_count") != 12',
        ):
            self.assertIn(guard, source)

    def test_cli_new_mode_is_explicit_only_and_old_static_guard_retained(self):
        main = CLI.read_text()
        for guard in (
            'else if (arg == "--p1m2b-independent-state")',
            'if (p1m2b_independent_state &&',
            'scenario_name != "camera-motion" && scenario_name != "light-motion"',
            '!p1m2b_independent_state && !accepted_token',
            '!p1m2b_independent_state && scenario_name != "static"',
            'source_warmup_frames != 32U',
            'target_state_warmup_frames != 8U',
            'target_frames != 1U',
            '"  \\"p1m2b_independent_state\\":"',
        ):
            self.assertIn(guard, main)
        self.assertIn('p1m1_canonical_token == 3221225474U', main)
        self.assertIn('p1m1_canonical_token == 3223322625U', main)
        self.assertIn('p1m1_canonical_token == 3223324678U', main)
        self.assertIn('request.p1m2_tetra_octant_directions', RUNTIME.read_text())
        self.assertIn('n006_p1m1_canonical_key_extra.spv', RUNTIME.read_text())
        self.assertIn('n006_p1m2a_tetra_octant_extra.spv', RUNTIME.read_text())
        self.assertNotEqual(
            (SHADERS / "n006_p1m1_canonical_key_extra.comp.glsl").read_text(),
            (SHADERS / "n006_p1m2a_tetra_octant_extra.comp.glsl").read_text(),
        )

    def test_shell_requires_branch_tests_and_one_runner(self):
        run = (RUNNER / "run_n006_p1m2b_independent_state.sh").read_text()
        for phrase in (
            'git pull --ff-only', 'mise run build', "unittest discover",
            'run_p1m2b_independent_state.py',
            'research-n006-interval-aware-allocation',
        ):
            self.assertIn(phrase, run)
        self.assertNotIn(".github/workflows", run)


if __name__ == "__main__":
    unittest.main()

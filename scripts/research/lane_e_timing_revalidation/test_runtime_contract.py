from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "src/research/integration/i001_runtime.cpp"


class RuntimeContractTests(unittest.TestCase):
    def test_stable_classes_do_not_hide_idle_owner_mutations(self) -> None:
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn(
            "const bool has_expected_dynamic_owner =\n"
            "            options.scenario == I001Scenario::MovingRigid ||\n"
            "            options.scenario == I001Scenario::DeformingControl;",
            source,
        )
        self.assertIn("if (has_expected_dynamic_owner)", source)

    def test_dynamic_update_is_reversible(self) -> None:
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn(
            "target_state == geometry_is_target",
            source,
        )
        self.assertIn(
            "target_state ? moving.delta_x : -moving.delta_x",
            source,
        )
        self.assertIn("geometry_is_target = target_state;", source)

    def test_reallocation_reports_direct_old_new_overlap(self) -> None:
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn(
            "old_bytes +\n"
            "            static_cast<std::size_t>(replacement.allocation_size)",
            source,
        )


if __name__ == "__main__":
    unittest.main()

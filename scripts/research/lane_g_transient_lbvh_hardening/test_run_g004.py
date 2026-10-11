from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATH = Path(__file__).with_name("run_g004.py")
CONFIG = (
    ROOT / "research/lanes/lane-g-transient-lbvh-hardening/experiments"
    / "004-integration-hardening-config.json"
)
spec = importlib.util.spec_from_file_location("run_g004", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def passing_row() -> dict[str, str]:
    row = {field: "0" for field in mod.ZERO_QUALITY_FIELDS}
    row.update({
        "quality_passed": "1",
        "moved_primitives": "796",
        "dynamic_groups": "1",
        "deformed_primitives": "0",
        "topology_replaced_primitives": "0",
    })
    return row


class G004Tests(unittest.TestCase):
    def test_frozen_matrix_has_16_cases(self) -> None:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(len(cfg["cases"]), 16)

    def test_geometry_classes_are_separate(self) -> None:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        moving = [
            case for case in cfg["cases"]
            if case["scenario"] == "moving-rigid"
        ]
        self.assertEqual(
            {case["geometry_class"] for case in moving},
            {
                "representative-rigid",
                "rigid-large-few",
                "rigid-small-many32",
                "deforming",
                "topology-replace25",
            },
        )

    def test_representative_dynamic_row_passes(self) -> None:
        case = {
            "scenario": "moving-rigid",
            "geometry_class": "representative-rigid",
        }
        self.assertEqual(mod.semantic_failures(case, passing_row()), [])

    def test_deforming_requires_deformed_counter(self) -> None:
        case = {
            "scenario": "moving-rigid",
            "geometry_class": "deforming",
        }
        row = passing_row()
        self.assertIn("deformed_primitives", mod.semantic_failures(case, row))
        row["deformed_primitives"] = "796"
        self.assertEqual(mod.semantic_failures(case, row), [])

    def test_topology_requires_replacement_counter(self) -> None:
        case = {
            "scenario": "moving-rigid",
            "geometry_class": "topology-replace25",
        }
        row = passing_row()
        self.assertIn(
            "topology_replaced_primitives",
            mod.semantic_failures(case, row),
        )
        row["topology_replaced_primitives"] = "199"
        self.assertEqual(mod.semantic_failures(case, row), [])

    def test_stable_case_rejects_dynamic_work(self) -> None:
        case = {
            "scenario": "static",
            "geometry_class": "representative-rigid",
        }
        row = passing_row()
        self.assertIn(
            "unexpected_dynamic_work",
            mod.semantic_failures(case, row),
        )

    def test_no_power_state_manipulation(self) -> None:
        source = PATH.read_text(encoding="utf-8")
        self.assertNotIn("profile_peak", source)
        self.assertNotIn("power_dpm_force_performance_level", source)


if __name__ == "__main__":
    unittest.main()

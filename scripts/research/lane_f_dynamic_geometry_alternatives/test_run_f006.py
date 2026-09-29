from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).with_name("run_f006.py")
SPEC = importlib.util.spec_from_file_location("lane_f_run_f006", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(
    variant: str,
    geometry_class: str,
    repeat: int,
    gpu: float,
    peak: int,
) -> dict[str, object]:
    result: dict[str, object] = {
        "variant": variant,
        "geometry_class": geometry_class,
        "repeat": repeat,
        "complete_gpu_us": gpu,
        "complete_frame_wall_us": gpu * 1.2,
        "peak_resident_bytes": peak,
        "quality_passed": "1",
        "storage_failures": "0",
        "grid_overflow": "0",
        "moved_primitives": "796",
        "dynamic_groups": "1",
        "deformed_primitives": "0",
        "topology_replaced_primitives": "0",
    }
    for field in MODULE.NUMERIC_FIELDS:
        result.setdefault(field, 0.0)
    result["complete_gpu_us"] = gpu
    result["peak_resident_bytes"] = peak
    return result


class F006RunnerTests(unittest.TestCase):
    def test_twenty_percent_exactly_is_stable(self) -> None:
        rows = [
            row("transient-lbvh", "rigid-large-few", i, value, 1000)
            for i, value in enumerate((100.0, 101.0, 102.0, 103.0, 120.0))
        ]
        summary, unstable = MODULE.summarize(rows)
        self.assertFalse(unstable)
        self.assertEqual(
            summary["transient-lbvh"]["rigid-large-few"]["complete_gpu_us"]["median"],
            102.0,
        )

    def test_over_twenty_percent_is_unstable(self) -> None:
        rows = [
            row("transient-grid", "deforming", i, value, 1000)
            for i, value in enumerate((100.0, 101.0, 102.0, 103.0, 121.0))
        ]
        _, unstable = MODULE.summarize(rows)
        self.assertTrue(unstable)

    def test_gate_is_per_candidate_and_geometry_class(self) -> None:
        rows: list[dict[str, object]] = []
        for geometry_class in MODULE.GEOMETRY_CLASSES:
            for repeat in range(5):
                rows.append(
                    row("vanilla-software", geometry_class, repeat, 100.0, 1000)
                )
                rows.append(
                    row("transient-lbvh", geometry_class, repeat, 104.0, 2500)
                )
                rows.append(
                    row("transient-grid", geometry_class, repeat, 106.0, 2500)
                )
        summary, unstable = MODULE.summarize(rows)
        self.assertFalse(unstable)
        gates = MODULE.evaluate_gates(summary)
        self.assertTrue(gates["transient-lbvh"]["all_f006_classes_pass"])
        self.assertFalse(gates["transient-grid"]["all_f006_classes_pass"])


if __name__ == "__main__":
    unittest.main()

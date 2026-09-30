from __future__ import annotations

import math
import unittest

from analysis import classify_memory, classify_performance, control_envelope, summarize_process


def process_rows(ratio: float, block: int, comparison: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for pair in range(16):
        phase = "warmup" if pair < 4 else "measured"
        order = "AB" if pair % 2 == 0 else "BA"
        rows.append({
            "phase": phase,
            "pair_index": pair,
            "role": "A",
            "order": order,
            "block": block,
            "scenario": "moving-rigid",
            "track": "hwrt",
            "comparison": comparison,
            "gpu_us": 100.0,
        })
        rows.append({
            "phase": phase,
            "pair_index": pair,
            "role": "B",
            "order": order,
            "block": block,
            "scenario": "moving-rigid",
            "track": "hwrt",
            "comparison": comparison,
            "gpu_us": 100.0 * ratio,
        })
    return rows


class AnalysisTests(unittest.TestCase):
    def test_process_summary_uses_measured_pairs_only(self) -> None:
        summary = summarize_process(process_rows(0.75, 0, "candidate"))
        self.assertAlmostEqual(summary["median_ratio"], 0.75)
        self.assertEqual(summary["negative_pair_fraction"], 1.0)

    def test_detects_twenty_percent_improvement(self) -> None:
        controls = [
            summarize_process(process_rows(1.0, block, "control"))
            for block in range(8)
        ]
        candidates = [
            summarize_process(process_rows(0.75, block, "candidate"))
            for block in range(8)
        ]
        result = classify_performance(candidates, control_envelope(controls))
        self.assertEqual(result["classification"], ">=20% detected improvement")

    def test_sub_twenty_percent_is_measurement_limited(self) -> None:
        controls = [
            summarize_process(process_rows(1.0, block, "control"))
            for block in range(8)
        ]
        candidates = [
            summarize_process(process_rows(0.85, block, "candidate"))
            for block in range(8)
        ]
        result = classify_performance(candidates, control_envelope(controls))
        self.assertEqual(
            result["classification"],
            "<20% difference / measurement-limited",
        )

    def test_twenty_percent_regression_is_detected(self) -> None:
        controls = [
            summarize_process(process_rows(1.0, block, "control"))
            for block in range(8)
        ]
        candidates = [
            summarize_process(process_rows(1.25, block, "candidate"))
            for block in range(8)
        ]
        result = classify_performance(candidates, control_envelope(controls))
        self.assertEqual(result["classification"], "detected >=20% regression")

    def test_large_effect_inside_control_noise_is_measurement_limited(self) -> None:
        controls = [
            summarize_process(
                process_rows(1.40 if block == 0 else 1.0, block, "control")
            )
            for block in range(8)
        ]
        candidates = [
            summarize_process(process_rows(0.75, block, "candidate"))
            for block in range(8)
        ]
        result = classify_performance(candidates, control_envelope(controls))
        self.assertEqual(
            result["classification"],
            "<20% difference / measurement-limited",
        )

    def test_incomplete_allocation_lifetime_is_memory_regression(self) -> None:
        rows: list[dict[str, object]] = []
        for block in range(8):
            for pair in range(12):
                for role in ("A", "B"):
                    rows.append({
                        "phase": "measured",
                        "block": block,
                        "pair_index": pair,
                        "role": role,
                        "persistent_bytes": 100,
                        "true_peak_bytes": 100,
                        "old_new_overlap_bytes": 0,
                        "allocation_lifetime_complete":
                            0 if (block, pair, role) == (7, 11, "B") else 1,
                    })
        result = classify_memory(rows)
        self.assertEqual(result["classification"], "regression")

    def test_memory_improvement_requires_no_pair_regression(self) -> None:
        rows: list[dict[str, object]] = []
        for block in range(8):
            for pair in range(12):
                candidate_persistent = 90
                if block == 7 and pair == 11:
                    candidate_persistent = 110
                for role, persistent, peak, transient, scratch, allocations in [
                    ("A", 100, 100, 100, 0, 1),
                    ("B", candidate_persistent, 95, 100, 0, 1),
                ]:
                    rows.append({
                        "phase": "measured",
                        "block": block,
                        "pair_index": pair,
                        "role": role,
                        "persistent_bytes": persistent,
                        "transient_bytes": transient,
                        "scratch_bytes": scratch,
                        "true_peak_bytes": peak,
                        "old_new_overlap_bytes": 0,
                        "allocation_count": allocations,
                        "allocation_lifetime_complete": 1,
                    })
        result = classify_memory(rows)
        self.assertEqual(result["classification"], "neutral")

    def test_memory_hard_guard_uses_worst_pair(self) -> None:
        rows: list[dict[str, object]] = []
        for block in range(8):
            for pair in range(12):
                for role, persistent, peak in [
                    ("A", 100, 100),
                    ("B", 100, 100 if not (block == 7 and pair == 11) else 126),
                ]:
                    rows.append({
                        "phase": "measured",
                        "block": block,
                        "pair_index": pair,
                        "role": role,
                        "persistent_bytes": persistent,
                        "transient_bytes": 100,
                        "scratch_bytes": 0,
                        "true_peak_bytes": peak,
                        "old_new_overlap_bytes": 0,
                        "allocation_count": 1,
                        "allocation_lifetime_complete": 1,
                    })
        result = classify_memory(rows)
        self.assertEqual(result["classification"], "regression")


if __name__ == "__main__":
    unittest.main()

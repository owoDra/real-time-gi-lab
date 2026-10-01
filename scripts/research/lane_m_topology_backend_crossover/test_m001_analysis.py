from __future__ import annotations

import unittest

import m001_analysis as a


def rows(
    ratio: float,
    comparison: str,
    scenario: str = "topology-changing-object-local",
    track: str = "primary",
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for block in range(8):
        for pair in range(12):
            order = "AB" if pair % 2 == 0 else "BA"
            for role, gpu in (("A", 100.0), ("B", 100.0 * ratio)):
                output.append({
                    "phase": "measured",
                    "pair_index": pair,
                    "order": order,
                    "role": role,
                    "gpu_us": gpu,
                    "scenario": scenario,
                    "track": track,
                    "comparison": comparison,
                    "block": block,
                    "persistent_bytes": 1000 if role == "A" else 1200,
                    "true_peak_resident_bytes": 2000 if role == "A" else 2400,
                    "allocation_lifetime_complete": 1,
                })
    return output


class AnalysisTest(unittest.TestCase):
    def test_exact_20_percent_improvement_is_detected(self) -> None:
        control = a.control_envelope([
            a.summarize_process(rows(1.0, "control")[i:i + 24])
            for i in range(0, 192, 24)
        ])
        candidates = [
            a.summarize_process(rows(0.8, "lbvh")[i:i + 24])
            for i in range(0, 192, 24)
        ]
        result = a.classify_performance(candidates, control)
        self.assertEqual(result["classification"], ">=20% detected improvement")

    def test_sub20_is_never_ranked(self) -> None:
        control = a.control_envelope([
            a.summarize_process(rows(1.0, "control")[i:i + 24])
            for i in range(0, 192, 24)
        ])
        candidates = [
            a.summarize_process(rows(0.81, "lbvh")[i:i + 24])
            for i in range(0, 192, 24)
        ]
        result = a.classify_performance(candidates, control)
        self.assertEqual(
            result["classification"],
            "<20% difference / measurement-limited",
        )

    def test_memory_125_is_allowed_but_above_is_not(self) -> None:
        candidate = rows(0.8, "lbvh")
        self.assertTrue(a.classify_memory(candidate)["passed"])
        for row in candidate:
            if row["role"] == "B":
                row["persistent_bytes"] = 1251
        self.assertFalse(a.classify_memory(candidate)["passed"])

    def test_direct_stage_applies_memory_hard_guard(self) -> None:
        direct = (
            rows(1.0, "lbvh-control")
            + rows(0.70, "clustered-vs-lbvh")
        )
        for row in direct:
            if (
                row["comparison"] == "clustered-vs-lbvh"
                and row["role"] == "B"
            ):
                row["persistent_bytes"] = 1300
        result = a.summarize_direct_stage(direct)
        record = result["results"]["topology-changing-object-local"]["primary"]
        self.assertFalse(record["memory"]["passed"])
        self.assertIn("memory hard-guard fail", record["decision"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("run_g001.py")
spec = importlib.util.spec_from_file_location("run_g001", MODULE_PATH)
assert spec and spec.loader
g001 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g001)


def row(**overrides: str) -> dict[str, str]:
    base = {
        "variant": "transient-lbvh",
        "scenario": "sparse-moving",
        "name": "stream.rays",
        "owner": "shared-integration",
        "role": "producer-stream",
        "capacity_kind": "scenario-sized",
        "allocation_lifetime": "runtime",
        "use_lifetime": "frame",
        "logical_size_known": "1",
        "logical_bytes": "1024",
        "allocation_bytes": "2048",
    }
    base.update(overrides)
    return base


class G001ClassificationTests(unittest.TestCase):
    def test_candidate_specific(self) -> None:
        classification, _ = g001.classify(
            row(owner="transient-lbvh", role="radix-sort-scratch"),
            "sparse-moving",
            {},
        )
        self.assertEqual(classification, "candidate-specific")

    def test_shared_integration(self) -> None:
        classification, _ = g001.classify(row(), "moving-rigid", {})
        self.assertEqual(classification, "shared integration")

    def test_setup_only_retention(self) -> None:
        value = row(
            owner="static-hwrt",
            allocation_lifetime="runtime",
            use_lifetime="setup-only",
        )
        classification, _ = g001.classify(value, "moving-rigid", {})
        self.assertEqual(classification, "duplicative/non-overlapping lifetime")

    def test_dense_retention(self) -> None:
        sparse = row()
        dense = row(
            scenario="dense-moving",
            logical_bytes="1536",
            allocation_bytes="2048",
        )
        classification, _ = g001.classify(
            sparse,
            "sparse-moving",
            {("transient-lbvh", "stream.rays"): dense},
        )
        self.assertEqual(
            classification, "dense-only capacity retained in sparse workload"
        )

    def test_equal_logical_payload_is_not_dense_retention(self) -> None:
        sparse = row()
        dense = row(
            scenario="dense-moving",
            logical_bytes="1024",
            allocation_bytes="2048",
        )
        classification, _ = g001.classify(
            sparse,
            "sparse-moving",
            {("transient-lbvh", "stream.rays"): dense},
        )
        self.assertEqual(classification, "shared integration")


if __name__ == "__main__":
    unittest.main()

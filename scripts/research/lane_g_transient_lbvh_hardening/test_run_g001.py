from __future__ import annotations

import importlib.util
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
        "logical_size_known": "1",
        "logical_bytes": "1024",
        "allocation_bytes": "2048",
    }
    base.update(overrides)
    return base


def test_candidate_specific_classification() -> None:
    value = row(owner="transient-lbvh", role="radix-sort-scratch")
    classification, _ = g001.classify(value, "sparse-moving", {})
    assert classification == "candidate-specific"


def test_shared_classification() -> None:
    classification, _ = g001.classify(row(), "moving-rigid", {})
    assert classification == "shared integration"


def test_dense_retention_is_only_marked_with_smaller_sparse_logical_payload() -> None:
    sparse = row()
    dense = row(
        scenario="dense-moving",
        logical_bytes="4096",
        allocation_bytes="2048",
    )
    classification, _ = g001.classify(
        sparse, "sparse-moving", {("transient-lbvh", "stream.rays"): dense}
    )
    assert classification == "dense-only capacity retained in sparse workload"


def test_equal_logical_payload_is_not_called_dense_retention() -> None:
    sparse = row()
    dense = row(
        scenario="dense-moving",
        logical_bytes="1024",
        allocation_bytes="2048",
    )
    classification, _ = g001.classify(
        sparse, "sparse-moving", {("transient-lbvh", "stream.rays"): dense}
    )
    assert classification == "shared integration"

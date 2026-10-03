#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import n003_comparison_contract as comparison
import run_n003_diagnostics as diagnostics

ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-comparison-config.json"
)


def expect_error(fn, label: str) -> None:
    try:
        fn()
    except comparison.ContractError:
        return
    raise AssertionError(f"expected ContractError: {label}")


def role() -> dict[str, object]:
    cpu = {field: 0.0 for field in diagnostics.CPU_FIELDS}
    host = {
        "scene_surface_capacity": 100,
        "scene_triangle_capacity": 200,
        "dynamic_selection_capacity": 20,
        "candidate_structure_capacity": 80,
        "renderer_owned_total": 400,
    }
    return {
        "cpu_wall_diagnostic_us": cpu,
        "host_memory_bytes": host,
    }


def payload(config: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "protocol_version": diagnostics.PROTOCOL_VERSION,
        "formal_decision_axis": False,
        "source_warmup_frames": config["timing"]["source_warmup_frames"],
        "host_memory_scope": (
            "renderer-owned-vector-and-BVH-capacity-only; "
            "allocator-bookkeeping-and-opaque-driver-host-memory-excluded"
        ),
        "device": {
            "name": config["target_gpu"],
            "driver_name": "radv",
            "driver_info": "test",
            "api_version": 1,
            "timestamp_period_ns": 1.0,
        },
        "scenarios": {
            scenario: {"A": role(), "B": role()}
            for scenario in comparison.EXPECTED_SCENARIOS
        },
    }


def validate(value: dict[str, object], config: dict[str, object]) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "n003-diagnostics.json").write_text(
            json.dumps(value), encoding="utf-8"
        )
        diagnostics.validate_artifact(root, config)


def main() -> None:
    config = comparison.load_config(CONFIG)
    valid = payload(config)
    validate(valid, config)

    broken = copy.deepcopy(valid)
    broken["scenarios"]["static"]["A"]["host_memory_bytes"]["renderer_owned_total"] += 1
    expect_error(lambda: validate(broken, config), "host total mismatch")

    broken = copy.deepcopy(valid)
    del broken["scenarios"]["camera-motion"]["B"]["cpu_wall_diagnostic_us"]["packing_cpu"]
    expect_error(lambda: validate(broken, config), "missing CPU diagnostic field")

    broken = copy.deepcopy(valid)
    broken["formal_decision_axis"] = True
    expect_error(lambda: validate(broken, config), "formal diagnostics mutation")

    print("N003 diagnostics contract tests: PASS")


if __name__ == "__main__":
    main()

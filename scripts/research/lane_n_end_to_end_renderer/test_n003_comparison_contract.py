#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path

import n003_comparison_contract as contract

ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-comparison-config.json"
)


def expect_error(fn, label: str) -> None:
    try:
        fn()
    except contract.ContractError:
        return
    raise AssertionError(f"expected ContractError: {label}")


def sample(timing: float) -> dict[str, object]:
    return {
        "timing_us": {
            "complete_gi_gpu": timing,
            "complete_renderer_gpu": timing + 10.0,
            "stages": {},
        },
        "stats": {
            "work_items": 1000,
            "outputs": 125,
            "requested_work_items": 1000,
            "requested_outputs": 125,
            "overflow": 0,
            "visible_owners": 31,
            "moved_primitives": 796,
            "topology_mutations": 1,
            "topology_replaced_primitives": 398,
            "backend_rebuilds": 1,
            "storage_allocations": 10,
            "storage_updates": 125,
            "storage_invalidations": 2,
            "storage_failures": 0,
        },
        "memory_bytes": {
            "persistent": 100,
            "transient": 200,
            "scratch": 50,
            "old_new_overlap": 0,
            "true_lifetime_peak": 350,
            "radiance_storage_persistent": 40,
            "producer_stream_capacity": 60,
            "image_transient": 20,
        },
        "correctness": {"passed": True},
    }


def pair(config: dict[str, object], order: str, ratio: float = 1.10) -> dict[str, object]:
    scenarios: dict[str, object] = {}
    for scenario in contract.EXPECTED_SCENARIOS:
        a = sample(100.0)
        b = sample(100.0 * ratio)
        if scenario != "topology-changing-high-churn":
            for role in (a, b):
                role["stats"]["topology_mutations"] = 0
                role["stats"]["topology_replaced_primitives"] = 0
                role["stats"]["backend_rebuilds"] = 0
        scenarios[scenario] = {"A": a, "B": b}
    return {
        "schema_version": 1,
        "protocol_version": contract.PROTOCOL_VERSION,
        "roles": copy.deepcopy(contract.EXPECTED_ROLES),
        "execution_start_order": order,
        "source_warmup_frames": 32,
        "device": {
            "name": config["target_gpu"],
            "driver_name": "radv",
            "driver_info": "test",
            "api_version": 1,
            "timestamp_period_ns": 1.0,
        },
        "scenarios": scenarios,
    }


def synthetic_blocks(config: dict[str, object]) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for block_index, start in enumerate(contract.EXPECTED_ORDERS):
        micros: list[dict[str, object]] = []
        for micro_index, order in enumerate(contract.micro_orders(start, 5)):
            micros.append(
                {
                    "micro": micro_index,
                    "order": order,
                    "pair": pair(config, order),
                }
            )
        blocks.append(
            {
                "block": block_index,
                "outer_start_order": start,
                "micro_pairs": micros,
            }
        )
    return blocks


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    contract.validate_config(config)

    changed = copy.deepcopy(config)
    changed["timing"]["scenario_threshold_fraction"]["static"] = 0.08
    expect_error(lambda: contract.validate_config(changed), "static threshold mutation")

    changed = copy.deepcopy(config)
    changed["timing"]["scenario_timing_eligible"]["moving-rigid"] = True
    changed["timing"]["scenario_threshold_fraction"]["moving-rigid"] = 0.20
    expect_error(lambda: contract.validate_config(changed), "moving-rigid timing enable")

    changed = copy.deepcopy(config)
    changed["timing"]["gpu_profile_changes"] = "allowed"
    expect_error(lambda: contract.validate_config(changed), "GPU profile mutation")

    changed = copy.deepcopy(config)
    changed["timing"]["sample_exclusion"] = "allowed"
    expect_error(lambda: contract.validate_config(changed), "sample exclusion")

    valid_pair = pair(config, "AB")
    contract.validate_pair(valid_pair, config, "AB")

    broken = copy.deepcopy(valid_pair)
    broken["scenarios"]["static"]["B"]["stats"]["work_items"] += 1
    expect_error(
        lambda: contract.validate_pair(broken, config, "AB"),
        "producer workload mismatch",
    )

    blocks = synthetic_blocks(config)
    summary = contract.summarize(blocks, config)
    if summary["per_scenario"]["moving-rigid"]["timing_status"] != "measurement-limited":
        raise AssertionError("moving-rigid timing status changed")
    for axis in contract.TIMING_AXES:
        moving = summary["per_scenario"]["moving-rigid"]["axes"][axis]
        if moving["formal_material_change_detected"]:
            raise AssertionError("moving-rigid emitted a formal timing claim")
        static = summary["per_scenario"]["static"]["axes"][axis]
        if not static["formal_material_change_detected"]:
            raise AssertionError("eligible synthetic 10% static effect was not detected")
        if static["formal_direction"] != "current-faster":
            raise AssertionError("ratio orientation changed")

    if summary["aggregate_winner"] is not None:
        raise AssertionError("aggregate winner must remain absent")

    print("N003 comparison contract tests: PASS")


if __name__ == "__main__":
    main()

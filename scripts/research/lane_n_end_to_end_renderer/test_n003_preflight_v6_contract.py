#!/usr/bin/env python3
from __future__ import annotations

import copy
from pathlib import Path

import n003_preflight_v6_contract as contract

ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-preflight-calibration-v6-config.json"
)


def expect_error(config: dict, label: str) -> None:
    try:
        contract.validate_config(config)
    except contract.ContractError:
        return
    raise AssertionError(f"expected ContractError for {label}")


def timing(total: float) -> dict:
    stages = {stage: 0.0 for stage in contract.TIMING_STAGES}
    stages["renderer_prerequisite_attributable_to_gi"] = total * 0.25
    stages["frame_init_visibility"] = total * 0.25
    stages["producer"] = total * 0.25
    stages["traversal"] = total * 0.20
    stages["synchronization"] = total * 0.05
    return {
        "complete_gi_gpu": total,
        "complete_renderer_gpu": total * 1.05,
        "stages": stages,
    }


def pair(config: dict, order: str, ratio: float) -> dict:
    scenarios = {}
    for scenario in contract.EXPECTED_SCENARIOS:
        scenarios[scenario] = {
            "A": timing(100.0),
            "B": timing(100.0 * ratio),
        }
    return {
        "schema_version": 1,
        "protocol_version": contract.PROBE_PROTOCOL_VERSION,
        "source_warmup_frames": 32,
        "warmup_validation_position": "after-first-source-frame",
        "start_order": order,
        "device": {
            "name": config["target_gpu"],
            "driver_name": "radv",
            "driver_info": "test",
            "api_version": 1,
            "timestamp_period_ns": 1.0,
        },
        "scenarios": scenarios,
    }


def blocks(config: dict, per_block_ratios: list[list[float]]) -> list[dict]:
    result = []
    for block_index, ratios in enumerate(per_block_ratios):
        outer = config["timing_calibration"]["outer_start_orders"][block_index]
        orders = contract.micro_orders(outer, len(ratios))
        result.append(
            {
                "block": block_index,
                "outer_start_order": outer,
                "micro_pairs": [
                    {
                        "micro": micro_index,
                        "order": orders[micro_index],
                        "pair": pair(config, orders[micro_index], ratio),
                    }
                    for micro_index, ratio in enumerate(ratios)
                ],
            }
        )
    return result


def main() -> int:
    config = contract.load_config(CONFIG)

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["gpu_profile_changes"] = "allowed"
    expect_error(changed, "GPU profile mutation")

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["micro_pairs_per_block"] = 3
    expect_error(changed, "micro-pair count")

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["material_change_threshold"]["timing_unsuitable_above_fraction"] = 0.25
    expect_error(changed, "post-hoc timing ceiling")

    stable = contract.summarize(blocks(config, [[1.0] * 5 for _ in range(8)]), config)
    assert stable["derived_material_change_threshold_fraction"] == 0.01
    assert stable["worst_p95_block_effect_fraction"] == 0.0
    assert stable["control_formal_claim_trigger_count"] == 0
    assert stable["timing_suitable_for_n003_formal_claims"] is True

    # One transient micro-pair in every block remains in raw evidence but cannot
    # move the median-of-five decision sample.
    isolated = contract.summarize(
        blocks(config, [[1.0, 1.0, 2.0, 1.0, 1.0] for _ in range(8)]),
        config,
    )
    assert isolated["derived_material_change_threshold_fraction"] == 0.01
    assert isolated["worst_p95_block_effect_fraction"] == 0.0
    assert isolated["timing_suitable_for_n003_formal_claims"] is True
    assert (
        isolated["per_scenario"]["static"]["complete_gi_gpu"]
        ["raw_micro_pair_p95_effect_fraction"]
        > 0.0
    )

    # If the instability is the majority of a block it must survive aggregation
    # and fail the same 20% suitability gate.
    majority_bad = contract.summarize(
        blocks(config, [[1.0, 2.0, 2.0, 2.0, 1.0] for _ in range(8)]),
        config,
    )
    assert majority_bad["timing_suitable_for_n003_formal_claims"] is False

    print("N003 preflight v6 contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

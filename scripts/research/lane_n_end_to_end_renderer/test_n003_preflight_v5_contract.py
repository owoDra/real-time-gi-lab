#!/usr/bin/env python3
from __future__ import annotations

import copy
from pathlib import Path

import n003_preflight_v4_contract as v4
import n003_preflight_v5_contract as contract

ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-preflight-calibration-v5-config.json"
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


def pair(config: dict, order: str, ratio: float = 1.0) -> dict:
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


def blocks(config: dict, ratios: list[float]) -> list[dict]:
    orders = config["timing_calibration"]["start_orders"]
    return [
        {"block": index, "pair": pair(config, orders[index], ratio)}
        for index, ratio in enumerate(ratios)
    ]


def main() -> int:
    config = contract.load_config(CONFIG)

    normalized = contract.normalized_v4_config(config)
    v4.validate_config(normalized)

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["gpu_performance_state"]["required_level"] = "high"
    expect_error(changed, "performance level")

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["gpu_performance_state"]["require_unchanged_across_campaign"] = False
    expect_error(changed, "performance state continuity")

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["material_change_threshold"]["timing_unsuitable_above_fraction"] = 0.25
    expect_error(changed, "post-hoc timing ceiling")

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["comparison_unit"] = "same-process-hot-adjacent-A-A"
    expect_error(changed, "clock-pinned comparison identity")

    stable = contract.summarize(blocks(config, [1.0] * 8), config)
    assert stable["derived_material_change_threshold_fraction"] == 0.01
    assert stable["worst_p95_pair_effect_fraction"] == 0.0
    assert stable["control_formal_claim_trigger_count"] == 0
    assert stable["timing_suitable_for_n003_formal_claims"] is True
    assert stable["campaign_protocol_version"] == contract.PROTOCOL_VERSION
    assert stable["measurement_probe_protocol"] == contract.PROBE_PROTOCOL_VERSION

    noisy = contract.summarize(
        blocks(config, [0.5, 2.0, 0.55, 1.9, 0.6, 1.8, 0.65, 1.7]),
        config,
    )
    assert noisy["timing_suitable_for_n003_formal_claims"] is False

    print("N003 preflight v5 contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

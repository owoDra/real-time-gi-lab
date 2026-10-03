#!/usr/bin/env python3
from __future__ import annotations

import copy
from pathlib import Path

import n003_preflight_v4_contract as contract

ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-preflight-calibration-v4-config.json"
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
        "protocol_version": contract.PROTOCOL_VERSION,
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

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["source_warmup_frames"] = 1
    expect_error(changed, "warm-up count")

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["warmup_validation_position"] = "after-all-warmup"
    expect_error(changed, "warm-up validation position")

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["stage_diagnostic_active_floor_us"] = 0.0
    expect_error(changed, "stage diagnostic floor")

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["material_change_threshold"]["minimum_fraction"] = 0.05
    expect_error(changed, "post-hoc minimum threshold")

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["start_orders"] = ["AB"] * 8
    expect_error(changed, "start-order schedule")

    stable_blocks = blocks(config, [1.0] * 8)
    stable = contract.summarize(stable_blocks, config)
    assert stable["derived_material_change_threshold_fraction"] == 0.01
    assert stable["worst_p95_pair_effect_fraction"] == 0.0
    assert stable["control_formal_claim_trigger_count"] == 0
    assert stable["stage_below_floor_mismatch_count"] == 0
    assert stable["timing_suitable_for_n003_formal_claims"] is True

    # Floating-point remainder noise below 1 us must be diagnostic-inactive.
    tiny = blocks(config, [1.0] * 8)
    tiny[0]["pair"]["scenarios"]["static"]["A"]["stages"]["synchronization"] = 1.0e-12
    tiny_result = contract.summarize(tiny, config)
    assert tiny_result["stage_below_floor_mismatch_count"] == 0
    assert tiny_result["timing_suitable_for_n003_formal_claims"] is True

    noisy_blocks = blocks(
        config,
        [0.98, 1.02, 0.99, 1.01, 0.98, 1.02, 0.99, 1.01],
    )
    noisy = contract.summarize(noisy_blocks, config)
    assert 0.01 <= noisy["derived_material_change_threshold_fraction"] <= 0.20
    assert noisy["timing_suitable_for_n003_formal_claims"] is True

    bad_blocks = blocks(
        config,
        [0.5, 2.0, 0.55, 1.9, 0.6, 1.8, 0.65, 1.7],
    )
    bad = contract.summarize(bad_blocks, config)
    assert bad["timing_suitable_for_n003_formal_claims"] is False

    malformed = pair(config, "AB")
    malformed["warmup_validation_position"] = "after-all-warmup"
    try:
        contract.validate_pair(malformed, config, "AB")
    except contract.ContractError:
        pass
    else:
        raise AssertionError("wrong warm-up validation position must fail")

    print("N003 preflight v4 contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

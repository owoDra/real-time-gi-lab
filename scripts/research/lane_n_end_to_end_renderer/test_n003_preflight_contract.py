#!/usr/bin/env python3
from __future__ import annotations

import copy
import math
from pathlib import Path

import n001_contract as image_contract
import n003_preflight_contract as contract

ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-preflight-calibration-config.json"
)


def expect_error(config: dict, label: str) -> None:
    try:
        contract.validate_config(config)
    except contract.ContractError:
        return
    raise AssertionError(f"expected ContractError for {label}")


def member_timing(value: float, ratio: float = 1.0) -> tuple[dict, dict]:
    a = {
        scenario: {
            "complete_gi_gpu": value,
            "complete_renderer_gpu": value * 1.1,
        }
        for scenario in contract.EXPECTED_SCENARIOS
    }
    b = {
        scenario: {
            "complete_gi_gpu": value * ratio,
            "complete_renderer_gpu": value * 1.1 * ratio,
        }
        for scenario in contract.EXPECTED_SCENARIOS
    }
    return a, b


def paired_blocks(ratios: list[float]) -> list[dict]:
    blocks = []
    for block, ratio in enumerate(ratios):
        a, b = member_timing(100.0, ratio)
        blocks.append({"block": block, "A": {"timing": a}, "B": {"timing": b}})
    return blocks


def member_quality() -> dict:
    return {
        scenario: {
            "rgb_rms_error": 1.0e-5,
            "p99_abs_luminance_error": 2.0e-5,
            "scale_aware_affected_pixel_fraction": 0.01,
        }
        for scenario in contract.EXPECTED_SCENARIOS
    }


def main() -> int:
    config = contract.load_config(CONFIG)

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["fresh_process_pair_blocks"] = 6
    expect_error(changed, "fresh-process pair count")

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["material_change_threshold"]["minimum_fraction"] = 0.05
    expect_error(changed, "imported timing threshold")

    changed = copy.deepcopy(config)
    changed["quality_interpretation"]["legacy_affected_pixel_fraction_role"] = "primary"
    expect_error(changed, "legacy affected metric role")

    stable = contract.summarize_timing(paired_blocks([1.0] * 8), config)
    assert stable["worst_noise_fraction"] == 0.0
    assert stable["worst_p95_pair_effect_fraction"] == 0.0
    assert stable["derived_material_change_threshold_fraction"] == 0.01
    assert stable["control_formal_claim_trigger_count"] == 0
    assert stable["timing_suitable_for_n003_formal_claims"] is True

    # Symmetric paired jitter has near-zero bias but non-zero robust MAD.
    logs = [-0.020, -0.015, -0.010, -0.005, 0.005, 0.010, 0.015, 0.020]
    jitter = contract.summarize_timing(
        paired_blocks([math.exp(value) for value in logs]), config
    )
    assert 0.05 < jitter["worst_noise_fraction"] < 0.07
    assert jitter["derived_material_change_threshold_fraction"] == 0.06
    assert jitter["control_formal_claim_trigger_count"] == 0
    assert jitter["timing_suitable_for_n003_formal_claims"] is True

    # A consistently biased A/A control must be visible to the calibration.
    biased = contract.summarize_timing(paired_blocks([1.25] * 8), config)
    assert biased["derived_material_change_threshold_fraction"] > 0.20
    assert biased["timing_suitable_for_n003_formal_claims"] is False

    reference = image_contract.PFMImage(
        2,
        1,
        (0.0, 0.0, 0.0, 0.001, 0.001, 0.001),
    )
    output = image_contract.PFMImage(
        2,
        1,
        (0.00001, 0.00001, 0.00001, 0.001, 0.001, 0.001),
    )
    affected = contract.scale_aware_affected_pixel_fraction(output, reference, config)
    assert affected == 0.5

    quality_blocks = []
    for block in range(8):
        quality_blocks.append(
            {
                "block": block,
                "A": {"quality": member_quality()},
                "B": {"quality": member_quality()},
            }
        )
    quality = contract.summarize_quality(quality_blocks, config)
    assert quality["scale_aware_campaign_has_signal"] is True
    assert quality["material_change_rule"]["required_concordant_primary_metrics"] == 2

    print("N003 paired-control preflight contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

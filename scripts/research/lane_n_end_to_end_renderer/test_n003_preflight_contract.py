#!/usr/bin/env python3
from __future__ import annotations

import copy
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


def timing_blocks(value: float) -> list[dict]:
    blocks = []
    for block in range(6):
        timing = {
            scenario: {
                "complete_gi_gpu": value,
                "complete_renderer_gpu": value * 1.1,
            }
            for scenario in contract.EXPECTED_SCENARIOS
        }
        blocks.append({"block": block, "timing": timing})
    return blocks


def main() -> int:
    config = contract.load_config(CONFIG)

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["fresh_process_blocks"] = 5
    expect_error(changed, "fresh-process block count")

    changed = copy.deepcopy(config)
    changed["timing_calibration"]["material_change_threshold"]["minimum_fraction"] = 0.05
    expect_error(changed, "imported timing threshold")

    changed = copy.deepcopy(config)
    changed["quality_interpretation"]["legacy_affected_pixel_fraction_role"] = "primary"
    expect_error(changed, "legacy affected metric role")

    stable = contract.summarize_timing(timing_blocks(100.0), config)
    assert stable["worst_noise_fraction"] == 0.0
    assert stable["derived_material_change_threshold_fraction"] == 0.01
    assert stable["timing_suitable_for_n003_formal_claims"] is True

    noisy_blocks = timing_blocks(100.0)
    noisy_blocks[-1]["timing"]["static"]["complete_gi_gpu"] = 104.0
    noisy = contract.summarize_timing(noisy_blocks, config)
    assert 0.039 < noisy["worst_noise_fraction"] < 0.041
    assert noisy["derived_material_change_threshold_fraction"] == 0.12

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
    for block in range(6):
        quality_blocks.append(
            {
                "quality": {
                    scenario: {
                        "rgb_rms_error": 1.0e-5,
                        "p99_abs_luminance_error": 2.0e-5,
                        "scale_aware_affected_pixel_fraction": 0.01,
                    }
                    for scenario in contract.EXPECTED_SCENARIOS
                }
            }
        )
    quality = contract.summarize_quality(quality_blocks, config)
    assert quality["scale_aware_campaign_has_signal"] is True
    assert quality["material_change_rule"]["required_concordant_primary_metrics"] == 2

    print("N003 preflight contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path

import n003_quality_contract as contract
import run_n003_quality as quality

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


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    contract.validate_config(config)

    changed = copy.deepcopy(config)
    changed["quality"]["material_error_relative_change_fraction"] = 0.20
    expect_error(lambda: contract.validate_config(changed), "error material threshold")

    changed = copy.deepcopy(config)
    changed["quality"]["material_affected_fraction_absolute_change"] = 0.01
    expect_error(lambda: contract.validate_config(changed), "affected material threshold")

    changed = copy.deepcopy(config)
    changed["quality"]["material_change_requires_primary_metric_count"] = 1
    expect_error(lambda: contract.validate_config(changed), "quality concordance count")

    changed = copy.deepcopy(config)
    changed["quality"]["reference"]["min_spp"] = 128
    expect_error(lambda: contract.validate_config(changed), "reference minimum spp")

    if quality.error_direction(0.89, 1.0, 0.10) != "current-better":
        raise AssertionError("10% error rule no longer detects current improvement")
    if quality.error_direction(1.0, 0.89, 0.10) != "vanilla-better":
        raise AssertionError("10% error rule no longer detects vanilla improvement")
    if quality.error_direction(0.95, 1.0, 0.10) is not None:
        raise AssertionError("sub-threshold error difference became material")
    if quality.affected_direction(0.01, 0.016, 0.005) != "current-better":
        raise AssertionError("affected-fraction absolute rule changed")
    if quality.affected_direction(0.010, 0.014, 0.005) is not None:
        raise AssertionError("sub-threshold affected difference became material")

    print("N003 quality contract tests: PASS")


if __name__ == "__main__":
    main()

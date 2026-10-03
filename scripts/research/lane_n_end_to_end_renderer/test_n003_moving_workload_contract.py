#!/usr/bin/env python3
from __future__ import annotations

import copy
from pathlib import Path

import n003_moving_workload_contract as contract

ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-moving-workload-diagnostic-config.json"
)


def stats(seed: int = 0) -> dict[str, int]:
    return {field: seed + index for index, field in enumerate(contract.REQUIRED_STAT_FIELDS)}


def pair(config: dict, order: str, source_seed: int = 0, target_seed: int = 100) -> dict:
    return {
        "schema_version": 1,
        "protocol_version": contract.PROTOCOL_VERSION,
        "source_warmup_frames": 32,
        "start_order": order,
        "device": {
            "name": config["target_gpu"],
            "driver_name": "radv",
            "driver_info": "test",
            "api_version": 1,
            "timestamp_period_ns": 1.0,
        },
        "A": {
            "source_stats": stats(source_seed),
            "target_stats": stats(target_seed),
            "complete_gi_gpu_us": 100.0,
            "complete_renderer_gpu_us": 110.0,
        },
        "B": {
            "source_stats": stats(source_seed),
            "target_stats": stats(target_seed),
            "complete_gi_gpu_us": 105.0,
            "complete_renderer_gpu_us": 115.0,
        },
    }


def blocks(config: dict) -> list[dict]:
    return [
        {
            "block": index,
            "start_order": order,
            "pair": pair(config, order),
        }
        for index, order in enumerate(contract.EXPECTED_ORDERS)
    ]


def expect_error(config: dict, label: str) -> None:
    try:
        contract.validate_config(config)
    except contract.ContractError:
        return
    raise AssertionError(f"expected ContractError for {label}")


def main() -> int:
    config = contract.load_config(CONFIG)

    changed = copy.deepcopy(config)
    changed["diagnostic"]["gpu_profile_changes"] = "allowed"
    expect_error(changed, "GPU profile changes")

    changed = copy.deepcopy(config)
    changed["diagnostic"]["host_gpu_policy"] = "profile_peak"
    expect_error(changed, "host GPU policy")

    invariant = contract.summarize(blocks(config), config)
    assert invariant["workload_invariant"] is True
    assert "not explained" in invariant["interpretation"]

    mismatch_blocks = blocks(config)
    mismatch_blocks[3]["pair"]["B"]["target_stats"]["work_items"] += 1
    mismatch = contract.summarize(mismatch_blocks, config)
    assert mismatch["workload_invariant"] is False
    field = mismatch["phase_fields"]["target_stats"]["work_items"]
    assert field["invariant"] is False
    assert field["a_b_mismatch_blocks"] == [3]

    print("N003 moving workload diagnostic contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

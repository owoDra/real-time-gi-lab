from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import n003_preflight_v4_contract as v4

SCHEMA_VERSION = 5
PROTOCOL_VERSION = "paired-control-v5-clock-pinned"
PROBE_PROTOCOL_VERSION = "paired-control-v4"
EXPECTED_SCENARIOS = v4.EXPECTED_SCENARIOS
TIMING_TOTALS = v4.TIMING_TOTALS
TIMING_STAGES = v4.TIMING_STAGES
ContractError = v4.ContractError


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def normalized_v4_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(config)
    normalized["schema_version"] = 4
    normalized["protocol_version"] = PROBE_PROTOCOL_VERSION
    timing = normalized["timing_calibration"]
    timing["comparison_unit"] = "same-process-hot-adjacent-A-A"
    timing.pop("measurement_probe_protocol", None)
    timing.pop("gpu_performance_state", None)
    normalized["artifact_contract"] = {
        "required": [
            "n003-preflight-v4-config.json",
            "n003-preflight-v4-progress.json",
            "n003-preflight-v4-raw.json",
            "n003-preflight-v4-summary.json",
        ]
    }
    return normalized


def load_config(path: Path) -> dict[str, Any]:
    import json

    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("N003 preflight v5 schema_version changed")
    if config.get("experiment") != "N003-preflight" or config.get("phase") != "calibration":
        raise ContractError("N003 preflight v5 identity mismatch")
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N003 preflight v5 protocol mismatch")

    timing = _mapping(config.get("timing_calibration"), "timing_calibration")
    if timing.get("comparison_unit") != "same-process-hot-adjacent-A-A-clock-pinned":
        raise ContractError("N003 preflight v5 comparison unit changed")
    if timing.get("measurement_probe_protocol") != PROBE_PROTOCOL_VERSION:
        raise ContractError("N003 preflight v5 probe protocol changed")

    performance = _mapping(timing.get("gpu_performance_state"), "gpu_performance_state")
    if performance.get("driver") != "amdgpu":
        raise ContractError("N003 preflight v5 requires amdgpu")
    if performance.get("sysfs_node") != "power_dpm_force_performance_level":
        raise ContractError("N003 preflight v5 DPM sysfs node changed")
    if performance.get("required_level") != "profile_peak":
        raise ContractError("N003 preflight v5 requires profile_peak")
    if performance.get("require_unchanged_across_campaign") is not True:
        raise ContractError("N003 preflight v5 performance state must remain fixed")
    expected_clock_nodes = ["pp_dpm_sclk", "pp_dpm_mclk", "pp_dpm_fclk", "pp_dpm_socclk"]
    if performance.get("record_clock_state_nodes") != expected_clock_nodes:
        raise ContractError("N003 preflight v5 clock provenance set changed")

    v4.validate_config(normalized_v4_config(config))


def validate_pair(pair: dict[str, Any], config: dict[str, Any], expected_order: str) -> None:
    validate_config(config)
    v4.validate_pair(pair, normalized_v4_config(config), expected_order)


def summarize(blocks: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    result = v4.summarize(blocks, normalized_v4_config(config))
    result["campaign_protocol_version"] = PROTOCOL_VERSION
    result["measurement_probe_protocol"] = PROBE_PROTOCOL_VERSION
    return result

from __future__ import annotations

import copy
import json
import math
import statistics
from pathlib import Path
from typing import Any

import n003_preflight_v4_contract as v4

SCHEMA_VERSION = 6
PROTOCOL_VERSION = "paired-control-v6-replicated-median"
PROBE_PROTOCOL_VERSION = "paired-control-v4"
EXPECTED_SCENARIOS = v4.EXPECTED_SCENARIOS
TIMING_TOTALS = v4.TIMING_TOTALS
TIMING_STAGES = v4.TIMING_STAGES
EXPECTED_OUTER_ORDERS = ["AB", "BA", "AB", "BA", "BA", "AB", "BA", "AB"]
ContractError = v4.ContractError


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def _sequence(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be an array")
    return value


def _number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ContractError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ContractError(f"{label} must be finite")
    return result


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def micro_orders(start_order: str, count: int) -> list[str]:
    if start_order not in {"AB", "BA"} or count <= 0:
        raise ContractError("invalid N003 v6 micro-order request")
    other = "BA" if start_order == "AB" else "AB"
    return [start_order if index % 2 == 0 else other for index in range(count)]


def normalized_v4_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(config)
    normalized["schema_version"] = 4
    normalized["protocol_version"] = PROBE_PROTOCOL_VERSION
    timing = normalized["timing_calibration"]
    timing["comparison_unit"] = "same-process-hot-adjacent-A-A"
    timing["fresh_process_pair_blocks"] = 8
    timing["start_orders"] = list(EXPECTED_OUTER_ORDERS)
    timing["settle_seconds_between_pairs"] = float(timing["settle_seconds_between_outer_blocks"])
    timing["primary_statistic"] = "median-paired-log-ratio"
    timing["noise_estimator"] = "abs-median-log-bias-plus-3x-1.4826-MAD"
    timing["formal_claim_requires"] = {
        "magnitude_at_least_derived_threshold": True,
        "minimum_same_direction_pair_fraction": float(
            config["timing_calibration"]["formal_claim_requires"]["minimum_same_direction_block_fraction"]
        ),
    }
    timing["control_sanity"] = {
        "must_not_trigger_formal_claim": True,
        "maximum_p95_pair_effect_fraction": float(
            config["timing_calibration"]["control_sanity"]["maximum_p95_block_effect_fraction"]
        ),
    }
    for key in (
        "measurement_probe_protocol", "outer_blocks", "micro_pairs_per_block",
        "outer_start_orders", "micro_order_rule", "settle_seconds_between_outer_blocks",
        "raw_micro_pair_effect_role", "all_micro_pairs_retained", "gpu_profile_changes",
        "host_gpu_policy",
    ):
        timing.pop(key, None)
    normalized["artifact_contract"] = {
        "required": [
            "n003-preflight-v4-config.json", "n003-preflight-v4-progress.json",
            "n003-preflight-v4-raw.json", "n003-preflight-v4-summary.json",
        ]
    }
    return normalized


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("N003 preflight v6 schema_version changed")
    if config.get("experiment") != "N003-preflight" or config.get("phase") != "calibration":
        raise ContractError("N003 preflight v6 identity mismatch")
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N003 preflight v6 protocol mismatch")

    source = _mapping(config.get("source_of_truth"), "source_of_truth")
    if source.get("v5_status") != (
        "withdrawn-before-target-run: changing GPU power/performance profile is prohibited on the target host because it can trigger safety shutdown"
    ):
        raise ContractError("N003 preflight v6 must retain the v5 safety withdrawal")

    timing = _mapping(config.get("timing_calibration"), "timing_calibration")
    if timing.get("comparison_unit") != "five-micro-pair-block-median-A-A":
        raise ContractError("N003 preflight v6 comparison unit changed")
    if timing.get("measurement_probe_protocol") != PROBE_PROTOCOL_VERSION:
        raise ContractError("N003 preflight v6 probe protocol changed")
    if timing.get("outer_blocks") != 8 or timing.get("micro_pairs_per_block") != 5:
        raise ContractError("N003 preflight v6 requires 8 blocks x 5 micro-pairs")
    if _sequence(timing.get("outer_start_orders"), "outer_start_orders") != EXPECTED_OUTER_ORDERS:
        raise ContractError("N003 preflight v6 outer order schedule changed")
    if timing.get("micro_order_rule") != "alternate-from-outer-start-order":
        raise ContractError("N003 preflight v6 micro-order rule changed")
    if timing.get("primary_statistic") != "median-of-five-micro-pair-log-ratios-then-median-across-eight-blocks":
        raise ContractError("N003 preflight v6 primary statistic changed")
    if timing.get("noise_estimator") != "abs-median-block-log-bias-plus-3x-1.4826-MAD":
        raise ContractError("N003 preflight v6 noise estimator changed")
    if timing.get("raw_micro_pair_effect_role") != "diagnostic-only":
        raise ContractError("N003 preflight v6 raw micro-pair role changed")
    if timing.get("sample_exclusion") != "forbidden" or timing.get("all_micro_pairs_retained") is not True:
        raise ContractError("N003 preflight v6 must retain every micro-pair")
    if timing.get("gpu_profile_changes") != "forbidden" or timing.get("host_gpu_policy") != "leave-unchanged":
        raise ContractError("N003 preflight v6 must leave host GPU policy unchanged")
    if timing.get("completed_campaign_rerun_budget") != 0:
        raise ContractError("N003 preflight v6 completed rerun budget changed")

    threshold = _mapping(timing.get("material_change_threshold"), "threshold")
    if _number(threshold.get("minimum_fraction"), "threshold.minimum") != 0.01:
        raise ContractError("N003 preflight v6 minimum threshold changed")
    if _number(threshold.get("round_up_step_fraction"), "threshold.step") != 0.005:
        raise ContractError("N003 preflight v6 threshold step changed")
    if _number(threshold.get("timing_unsuitable_above_fraction"), "threshold.ceiling") != 0.20:
        raise ContractError("N003 preflight v6 timing ceiling changed")

    formal = _mapping(timing.get("formal_claim_requires"), "formal")
    if formal.get("magnitude_at_least_derived_threshold") is not True:
        raise ContractError("N003 preflight v6 magnitude rule changed")
    if _number(formal.get("minimum_same_direction_block_fraction"), "formal.direction") != 0.75:
        raise ContractError("N003 preflight v6 direction rule changed")
    control = _mapping(timing.get("control_sanity"), "control")
    if control.get("must_not_trigger_formal_claim") is not True:
        raise ContractError("N003 preflight v6 control trigger rule changed")
    if _number(control.get("maximum_p95_block_effect_fraction"), "control.p95") != 0.20:
        raise ContractError("N003 preflight v6 control p95 ceiling changed")

    v4.validate_config(normalized_v4_config(config))
    artifact = _mapping(config.get("artifact_contract"), "artifact_contract")
    required = set(_sequence(artifact.get("required"), "artifact_contract.required"))
    if required != {
        "n003-preflight-v6-config.json", "n003-preflight-v6-progress.json",
        "n003-preflight-v6-raw.json", "n003-preflight-v6-summary.json",
    }:
        raise ContractError("N003 preflight v6 artifact contract changed")


def validate_pair(pair: dict[str, Any], config: dict[str, Any], expected_order: str) -> None:
    validate_config(config)
    v4.validate_pair(pair, normalized_v4_config(config), expected_order)


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lo = math.floor(position)
    hi = math.ceil(position)
    if lo == hi:
        return ordered[lo]
    weight = position - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def _ceil_to_step(value: float, step: float) -> float:
    return math.ceil((value - 1.0e-15) / step) * step


def _stats_from_block_logs(block_logs: list[float], raw_micro_logs: list[float]) -> dict[str, Any]:
    median_log = float(statistics.median(block_logs))
    deviations = [abs(value - median_log) for value in block_logs]
    mad = float(statistics.median(deviations))
    robust_sigma = 1.4826 * mad
    noise_fraction = math.expm1(abs(median_log) + 3.0 * robust_sigma)
    block_ratios = [math.exp(value) for value in block_logs]
    raw_ratios = [math.exp(value) for value in raw_micro_logs]
    positive = sum(value > 0.0 for value in block_logs) / len(block_logs)
    negative = sum(value < 0.0 for value in block_logs) / len(block_logs)
    return {
        "block_log_ratios": block_logs,
        "block_ratios_B_over_A": block_ratios,
        "median_log_ratio": median_log,
        "median_effect_fraction": abs(math.exp(median_log) - 1.0),
        "mad_block_log_ratio": mad,
        "robust_sigma_block_log_ratio": robust_sigma,
        "noise_fraction": noise_fraction,
        "p95_block_effect_fraction": _percentile([abs(value - 1.0) for value in block_ratios], 0.95),
        "raw_micro_pair_p95_effect_fraction": _percentile([abs(value - 1.0) for value in raw_ratios], 0.95),
        "positive_block_fraction": positive,
        "negative_block_fraction": negative,
        "same_direction_block_fraction": max(positive, negative),
    }


def summarize(blocks: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    timing_cfg = config["timing_calibration"]
    outer_count = int(timing_cfg["outer_blocks"])
    micro_count = int(timing_cfg["micro_pairs_per_block"])
    if len(blocks) != outer_count:
        raise ContractError(f"N003 preflight v6 expected {outer_count} outer blocks")

    for block_index, block in enumerate(blocks):
        if block.get("block") != block_index:
            raise ContractError("N003 preflight v6 outer block index mismatch")
        expected_start = EXPECTED_OUTER_ORDERS[block_index]
        if block.get("outer_start_order") != expected_start:
            raise ContractError("N003 preflight v6 outer start order mismatch")
        micros = _sequence(block.get("micro_pairs"), f"block[{block_index}].micro_pairs")
        if len(micros) != micro_count:
            raise ContractError("N003 preflight v6 micro-pair count mismatch")
        expected_micro_orders = micro_orders(expected_start, micro_count)
        for micro_index, micro in enumerate(micros):
            if micro.get("micro") != micro_index or micro.get("order") != expected_micro_orders[micro_index]:
                raise ContractError("N003 preflight v6 micro-pair order/index mismatch")
            validate_pair(_mapping(micro.get("pair"), "micro.pair"), config, expected_micro_orders[micro_index])

    per_scenario: dict[str, Any] = {}
    worst_noise = 0.0
    worst_p95_block = 0.0
    for scenario in EXPECTED_SCENARIOS:
        axes: dict[str, Any] = {}
        for axis in TIMING_TOTALS:
            block_logs: list[float] = []
            raw_logs: list[float] = []
            for block in blocks:
                micro_logs: list[float] = []
                for micro in block["micro_pairs"]:
                    entry = micro["pair"]["scenarios"][scenario]
                    log_ratio = math.log(float(entry["B"][axis]) / float(entry["A"][axis]))
                    micro_logs.append(log_ratio)
                    raw_logs.append(log_ratio)
                block_logs.append(float(statistics.median(micro_logs)))
            stats = _stats_from_block_logs(block_logs, raw_logs)
            worst_noise = max(worst_noise, stats["noise_fraction"])
            worst_p95_block = max(worst_p95_block, stats["p95_block_effect_fraction"])
            axes[axis] = stats
        per_scenario[scenario] = axes

    threshold_cfg = timing_cfg["material_change_threshold"]
    derived = _ceil_to_step(
        max(float(threshold_cfg["minimum_fraction"]), worst_noise),
        float(threshold_cfg["round_up_step_fraction"]),
    )
    direction_floor = float(timing_cfg["formal_claim_requires"]["minimum_same_direction_block_fraction"])
    trigger_count = 0
    for axes in per_scenario.values():
        for stats in axes.values():
            trigger = stats["median_effect_fraction"] >= derived and stats["same_direction_block_fraction"] >= direction_floor
            stats["would_trigger_formal_claim"] = trigger
            trigger_count += int(trigger)

    floor_us = float(timing_cfg["stage_diagnostic_active_floor_us"])
    stage_mismatches = 0
    stage_diagnostics: dict[str, Any] = {}
    worst_stage = {"scenario": None, "stage": None, "p95_block_effect_fraction": 0.0}
    for scenario in EXPECTED_SCENARIOS:
        scenario_stages: dict[str, Any] = {}
        for stage in TIMING_STAGES:
            block_logs: list[float] = []
            raw_logs: list[float] = []
            mismatches = 0
            for block in blocks:
                micro_logs: list[float] = []
                for micro in block["micro_pairs"]:
                    entry = micro["pair"]["scenarios"][scenario]
                    a = float(entry["A"]["stages"][stage])
                    b = float(entry["B"]["stages"][stage])
                    a_active = a >= floor_us
                    b_active = b >= floor_us
                    if not a_active and not b_active:
                        continue
                    if a_active != b_active:
                        mismatches += 1
                        continue
                    value = math.log(b / a)
                    micro_logs.append(value)
                    raw_logs.append(value)
                if micro_logs:
                    block_logs.append(float(statistics.median(micro_logs)))
            stage_mismatches += mismatches
            block_ratios = [math.exp(value) for value in block_logs]
            raw_ratios = [math.exp(value) for value in raw_logs]
            p95_block = _percentile([abs(value - 1.0) for value in block_ratios], 0.95)
            scenario_stages[stage] = {
                "active_block_count": len(block_logs),
                "raw_active_micro_pair_count": len(raw_logs),
                "below_floor_mismatch_count": mismatches,
                "diagnostic_active_floor_us": floor_us,
                "median_block_ratio_B_over_A": float(statistics.median(block_ratios)) if block_ratios else None,
                "p95_block_effect_fraction": p95_block,
                "raw_micro_pair_p95_effect_fraction": _percentile([abs(value - 1.0) for value in raw_ratios], 0.95),
            }
            if p95_block > worst_stage["p95_block_effect_fraction"]:
                worst_stage = {"scenario": scenario, "stage": stage, "p95_block_effect_fraction": p95_block}
        stage_diagnostics[scenario] = scenario_stages

    suitable = (
        derived <= float(threshold_cfg["timing_unsuitable_above_fraction"])
        and worst_p95_block <= float(timing_cfg["control_sanity"]["maximum_p95_block_effect_fraction"])
        and trigger_count == 0
        and stage_mismatches == 0
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "measurement_probe_protocol": PROBE_PROTOCOL_VERSION,
        "primary_statistic": timing_cfg["primary_statistic"],
        "noise_estimator": timing_cfg["noise_estimator"],
        "worst_noise_fraction": worst_noise,
        "derived_material_change_threshold_fraction": derived,
        "worst_p95_block_effect_fraction": worst_p95_block,
        "control_p95_block_ceiling_fraction": float(timing_cfg["control_sanity"]["maximum_p95_block_effect_fraction"]),
        "minimum_same_direction_block_fraction": direction_floor,
        "control_formal_claim_trigger_count": trigger_count,
        "stage_below_floor_mismatch_count": stage_mismatches,
        "worst_stage_diagnostic": worst_stage,
        "timing_suitable_for_n003_formal_claims": suitable,
        "per_scenario": per_scenario,
        "stage_diagnostics": stage_diagnostics,
    }

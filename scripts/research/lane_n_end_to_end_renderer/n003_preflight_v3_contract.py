from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 3
PROTOCOL_VERSION = "paired-control-v3"
EXPECTED_SCENARIOS = [
    "static",
    "camera-motion",
    "light-motion",
    "moving-rigid",
    "stable-topology-deforming",
    "topology-changing-high-churn",
]
TIMING_TOTALS = ["complete_gi_gpu", "complete_renderer_gpu"]
TIMING_STAGES = [
    "renderer_prerequisite_attributable_to_gi",
    "frame_init_visibility",
    "producer",
    "ray_prepare",
    "geometry_prepare_upload",
    "acceleration_structure_maintenance",
    "traversal",
    "gather",
    "radiance_storage",
    "merge_resolve",
    "synchronization",
]


class ContractError(RuntimeError):
    pass


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


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("N003 preflight v3 schema_version changed")
    if config.get("experiment") != "N003-preflight" or config.get("phase") != "calibration":
        raise ContractError("N003 preflight v3 identity mismatch")
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N003 preflight v3 protocol mismatch")
    if config.get("target_gpu") != "AMD Radeon 8060S Graphics (RADV STRIX_HALO)":
        raise ContractError("N003 preflight v3 target GPU changed")

    source = _mapping(config.get("source_of_truth"), "source_of_truth")
    if source.get("issue") != 31 or source.get("parent_issue") != 26:
        raise ContractError("N003 preflight v3 issue identity mismatch")
    completion = source.get("n002_completion_commit")
    if not isinstance(completion, str) or len(completion) != 40:
        raise ContractError("N003 preflight v3 requires a full N002 completion commit")

    baseline = _mapping(config.get("baseline"), "baseline")
    if _sequence(baseline.get("required_scenarios"), "baseline.required_scenarios") != EXPECTED_SCENARIOS:
        raise ContractError("N003 preflight v3 scenario order changed")
    if not isinstance(baseline.get("scene_sha256"), str) or len(baseline["scene_sha256"]) != 64:
        raise ContractError("N003 preflight v3 scene digest invalid")

    timing = _mapping(config.get("timing_calibration"), "timing_calibration")
    if timing.get("comparison_unit") != "same-process-prewarmed-A-A":
        raise ContractError("N003 preflight v3 comparison unit changed")
    if timing.get("primary_axis") != "gpu_timestamp":
        raise ContractError("N003 preflight v3 primary axis must be GPU timestamp")
    if timing.get("cpu_wall_role") != "diagnostic-only":
        raise ContractError("N003 preflight v3 CPU wall role changed")
    if timing.get("fresh_process_pair_blocks") != 8:
        raise ContractError("N003 preflight v3 requires eight fresh-process pair blocks")
    if timing.get("source_warmup_frames") != 32:
        raise ContractError("N003 preflight v3 requires 32 source-state warm-up frames")
    if _sequence(timing.get("start_orders"), "timing.start_orders") != [
        "AB", "BA", "AB", "BA", "BA", "AB", "BA", "AB"
    ]:
        raise ContractError("N003 preflight v3 start-order schedule changed")
    if _sequence(timing.get("required_totals"), "timing.required_totals") != TIMING_TOTALS:
        raise ContractError("N003 preflight v3 timing totals changed")
    if _sequence(timing.get("required_stages"), "timing.required_stages") != TIMING_STAGES:
        raise ContractError("N003 preflight v3 timing stages changed")
    if timing.get("sample_exclusion") != "forbidden":
        raise ContractError("N003 preflight v3 sample exclusion must remain forbidden")
    if timing.get("completed_campaign_rerun_budget") != 0:
        raise ContractError("N003 preflight v3 completed rerun budget changed")
    if timing.get("primary_statistic") != "median-paired-log-ratio":
        raise ContractError("N003 preflight v3 primary statistic changed")
    if timing.get("noise_estimator") != "abs-median-log-bias-plus-3x-1.4826-MAD":
        raise ContractError("N003 preflight v3 noise estimator changed")

    threshold = _mapping(timing.get("material_change_threshold"), "timing.material_change_threshold")
    if _number(threshold.get("minimum_fraction"), "threshold.minimum") != 0.01:
        raise ContractError("N003 preflight v3 minimum timing threshold changed")
    if _number(threshold.get("round_up_step_fraction"), "threshold.step") != 0.005:
        raise ContractError("N003 preflight v3 timing threshold step changed")
    if _number(threshold.get("timing_unsuitable_above_fraction"), "threshold.ceiling") != 0.20:
        raise ContractError("N003 preflight v3 timing suitability ceiling changed")

    formal = _mapping(timing.get("formal_claim_requires"), "timing.formal_claim_requires")
    if formal.get("magnitude_at_least_derived_threshold") is not True:
        raise ContractError("N003 preflight v3 formal magnitude rule changed")
    if _number(formal.get("minimum_same_direction_pair_fraction"), "formal.direction") != 0.75:
        raise ContractError("N003 preflight v3 direction rule changed")
    control = _mapping(timing.get("control_sanity"), "timing.control_sanity")
    if control.get("must_not_trigger_formal_claim") is not True:
        raise ContractError("N003 preflight v3 control trigger rule changed")
    if _number(control.get("maximum_p95_pair_effect_fraction"), "control.p95") != 0.20:
        raise ContractError("N003 preflight v3 control p95 ceiling changed")

    quality = _mapping(config.get("quality_interpretation"), "quality_interpretation")
    if quality.get("status") != "accepted-from-v2":
        raise ContractError("N003 preflight v3 quality evidence status changed")
    if quality.get("legacy_affected_pixel_fraction_role") != "diagnostic-only":
        raise ContractError("N003 preflight v3 legacy quality role changed")
    if quality.get("aggregate_winner_score") is not False:
        raise ContractError("N003 preflight v3 aggregate quality winner score is forbidden")
    if quality.get("individual_black_reference_frames_valid") is not True:
        raise ContractError("N003 preflight v3 must retain black reference frames")


def validate_pair(pair: dict[str, Any], config: dict[str, Any], expected_order: str) -> None:
    validate_config(config)
    if pair.get("schema_version") != 1 or pair.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N003 preflight v3 pair artifact identity mismatch")
    if pair.get("source_warmup_frames") != config["timing_calibration"]["source_warmup_frames"]:
        raise ContractError("N003 preflight v3 pair warm-up count mismatch")
    if pair.get("start_order") != expected_order:
        raise ContractError("N003 preflight v3 pair start order mismatch")
    device = _mapping(pair.get("device"), "pair.device")
    if device.get("name") != config["target_gpu"]:
        raise ContractError("N003 preflight v3 pair ran on the wrong GPU")
    for key in ("driver_name", "driver_info"):
        if not isinstance(device.get(key), str) or not device[key]:
            raise ContractError(f"N003 preflight v3 device.{key} missing")
    if _number(device.get("timestamp_period_ns"), "device.timestamp_period_ns") <= 0.0:
        raise ContractError("N003 preflight v3 timestamp period must be positive")

    scenarios = _mapping(pair.get("scenarios"), "pair.scenarios")
    if list(scenarios.keys()) != EXPECTED_SCENARIOS:
        raise ContractError("N003 preflight v3 pair scenario order mismatch")
    for scenario in EXPECTED_SCENARIOS:
        entry = _mapping(scenarios.get(scenario), f"pair.scenarios.{scenario}")
        for role in ("A", "B"):
            timing = _mapping(entry.get(role), f"{scenario}.{role}")
            for axis in TIMING_TOTALS:
                if _number(timing.get(axis), f"{scenario}.{role}.{axis}") <= 0.0:
                    raise ContractError(f"N003 preflight v3 {scenario}.{role}.{axis} must be positive")
            stages = _mapping(timing.get("stages"), f"{scenario}.{role}.stages")
            if list(stages.keys()) != TIMING_STAGES:
                raise ContractError(f"N003 preflight v3 {scenario}.{role} stage set changed")
            for stage in TIMING_STAGES:
                if _number(stages.get(stage), f"{scenario}.{role}.{stage}") < 0.0:
                    raise ContractError(f"N003 preflight v3 {scenario}.{role}.{stage} must be non-negative")
            accounted = sum(float(stages[stage]) for stage in TIMING_STAGES)
            if accounted > float(timing["complete_gi_gpu"]) + 2.0:
                raise ContractError(f"N003 preflight v3 {scenario}.{role} stage accounting exceeds complete GI")
            if float(timing["complete_renderer_gpu"]) + 1.0e-9 < float(timing["complete_gi_gpu"]):
                raise ContractError(f"N003 preflight v3 {scenario}.{role} renderer boundary is smaller than GI")


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


def _axis_stats(a_values: list[float], b_values: list[float]) -> dict[str, Any]:
    ratios = [b / a for a, b in zip(a_values, b_values, strict=True)]
    logs = [math.log(value) for value in ratios]
    median_log = float(statistics.median(logs))
    deviations = [abs(value - median_log) for value in logs]
    mad = float(statistics.median(deviations))
    robust_sigma = 1.4826 * mad
    null_log_bound = abs(median_log) + 3.0 * robust_sigma
    noise_fraction = math.expm1(null_log_bound)
    median_ratio = math.exp(median_log)
    median_effect = abs(median_ratio - 1.0)
    pair_effects = [abs(value - 1.0) for value in ratios]
    positive = sum(value > 1.0 for value in ratios) / len(ratios)
    negative = sum(value < 1.0 for value in ratios) / len(ratios)
    return {
        "ratios_B_over_A": ratios,
        "paired_log_ratios": logs,
        "median_log_ratio": median_log,
        "median_effect_fraction": median_effect,
        "mad_log_ratio": mad,
        "robust_sigma_log_ratio": robust_sigma,
        "noise_fraction": noise_fraction,
        "p95_pair_effect_fraction": _percentile(pair_effects, 0.95),
        "positive_pair_fraction": positive,
        "negative_pair_fraction": negative,
        "same_direction_pair_fraction": max(positive, negative),
    }


def summarize(blocks: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    expected = int(config["timing_calibration"]["fresh_process_pair_blocks"])
    if len(blocks) != expected:
        raise ContractError(f"N003 preflight v3 expected {expected} blocks, got {len(blocks)}")

    orders = config["timing_calibration"]["start_orders"]
    for index, block in enumerate(blocks):
        pair = _mapping(block.get("pair"), f"block[{index}].pair")
        validate_pair(pair, config, orders[index])

    per_scenario: dict[str, Any] = {}
    worst_noise = 0.0
    worst_p95 = 0.0
    for scenario in EXPECTED_SCENARIOS:
        axes: dict[str, Any] = {}
        for axis in TIMING_TOTALS:
            a_values = [float(block["pair"]["scenarios"][scenario]["A"][axis]) for block in blocks]
            b_values = [float(block["pair"]["scenarios"][scenario]["B"][axis]) for block in blocks]
            stats = _axis_stats(a_values, b_values)
            worst_noise = max(worst_noise, stats["noise_fraction"])
            worst_p95 = max(worst_p95, stats["p95_pair_effect_fraction"])
            axes[axis] = stats
        per_scenario[scenario] = axes

    threshold_cfg = config["timing_calibration"]["material_change_threshold"]
    derived = _ceil_to_step(
        max(float(threshold_cfg["minimum_fraction"]), worst_noise),
        float(threshold_cfg["round_up_step_fraction"]),
    )
    direction_floor = float(
        config["timing_calibration"]["formal_claim_requires"]["minimum_same_direction_pair_fraction"]
    )
    trigger_count = 0
    for axes in per_scenario.values():
        for stats in axes.values():
            trigger = (
                stats["median_effect_fraction"] >= derived and
                stats["same_direction_pair_fraction"] >= direction_floor
            )
            stats["would_trigger_formal_claim"] = trigger
            trigger_count += int(trigger)

    stage_zero_mismatches = 0
    stage_diagnostics: dict[str, Any] = {}
    worst_stage = {"scenario": None, "stage": None, "p95_pair_effect_fraction": 0.0}
    for scenario in EXPECTED_SCENARIOS:
        scenario_stages: dict[str, Any] = {}
        for stage in TIMING_STAGES:
            ratios: list[float] = []
            mismatches = 0
            for block in blocks:
                entry = block["pair"]["scenarios"][scenario]
                a = float(entry["A"]["stages"][stage])
                b = float(entry["B"]["stages"][stage])
                if a == 0.0 and b == 0.0:
                    continue
                if a <= 0.0 or b <= 0.0:
                    mismatches += 1
                    continue
                ratios.append(b / a)
            stage_zero_mismatches += mismatches
            p95 = _percentile([abs(value - 1.0) for value in ratios], 0.95)
            scenario_stages[stage] = {
                "active_pair_count": len(ratios),
                "zero_mismatch_count": mismatches,
                "p95_pair_effect_fraction": p95,
                "median_ratio_B_over_A": float(statistics.median(ratios)) if ratios else None,
            }
            if p95 > worst_stage["p95_pair_effect_fraction"]:
                worst_stage = {"scenario": scenario, "stage": stage, "p95_pair_effect_fraction": p95}
        stage_diagnostics[scenario] = scenario_stages

    unsuitable_above = float(threshold_cfg["timing_unsuitable_above_fraction"])
    p95_ceiling = float(config["timing_calibration"]["control_sanity"]["maximum_p95_pair_effect_fraction"])
    suitable = (
        derived <= unsuitable_above and
        worst_p95 <= p95_ceiling and
        trigger_count == 0 and
        stage_zero_mismatches == 0
    )
    return {
        "noise_estimator": config["timing_calibration"]["noise_estimator"],
        "worst_noise_fraction": worst_noise,
        "derived_material_change_threshold_fraction": derived,
        "worst_p95_pair_effect_fraction": worst_p95,
        "control_p95_ceiling_fraction": p95_ceiling,
        "minimum_same_direction_pair_fraction": direction_floor,
        "control_formal_claim_trigger_count": trigger_count,
        "stage_zero_mismatch_count": stage_zero_mismatches,
        "worst_stage_diagnostic": worst_stage,
        "timing_suitable_for_n003_formal_claims": suitable,
        "per_scenario": per_scenario,
        "stage_diagnostics": stage_diagnostics,
    }

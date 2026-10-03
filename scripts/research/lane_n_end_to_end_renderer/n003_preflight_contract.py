from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

import n001_contract as image_contract

SCHEMA_VERSION = 2
EXPECTED_SCENARIOS = [
    "static",
    "camera-motion",
    "light-motion",
    "moving-rigid",
    "stable-topology-deforming",
    "topology-changing-high-churn",
]
TIMING_TOTALS = ["complete_gi_gpu", "complete_renderer_gpu"]
PRIMARY_QUALITY_METRICS = [
    "rgb_rms_error",
    "p99_abs_luminance_error",
    "scale_aware_affected_pixel_fraction",
]
LUMA = (0.2126, 0.7152, 0.0722)


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
    number = float(value)
    if not math.isfinite(number):
        raise ContractError(f"{label} must be finite")
    return number


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


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("unsupported N003 preflight schema_version")
    if config.get("experiment") != "N003-preflight" or config.get("phase") != "calibration":
        raise ContractError("N003 preflight identity mismatch")
    if config.get("protocol_version") != "paired-control-v2":
        raise ContractError("N003 preflight protocol_version mismatch")

    source = _mapping(config.get("source_of_truth"), "source_of_truth")
    commit = source.get("n002_completion_commit")
    if not isinstance(commit, str) or len(commit) != 40:
        raise ContractError("N003 preflight requires a full N002 completion commit")
    if source.get("v1_preflight_commit") != "422945ea32164e487e8562214dc7568f6e2ad9a6":
        raise ContractError("N003 preflight v1 provenance changed")
    if source.get("issue") != 31 or source.get("parent_issue") != 26:
        raise ContractError("N003 preflight issue identity mismatch")

    if config.get("target_gpu") != "AMD Radeon 8060S Graphics (RADV STRIX_HALO)":
        raise ContractError("N003 preflight target GPU changed")

    baseline = _mapping(config.get("baseline"), "baseline")
    if baseline.get("runner") != "scripts/research/lane_n_end_to_end_renderer/run_n002_full.py":
        raise ContractError("N003 preflight baseline runner mismatch")
    if baseline.get("config") != "research/lanes/lane-n-end-to-end-renderer/experiments/002-n002-full-config.json":
        raise ContractError("N003 preflight baseline config mismatch")
    if _sequence(baseline.get("required_scenarios"), "baseline.required_scenarios") != EXPECTED_SCENARIOS:
        raise ContractError("N003 preflight scenario order mismatch")

    timing = _mapping(config.get("timing_calibration"), "timing_calibration")
    if timing.get("primary_axis") != "gpu_timestamp":
        raise ContractError("N003 preflight primary timing axis must be GPU timestamp")
    if timing.get("cpu_wall_role") != "diagnostic-only":
        raise ContractError("N003 preflight CPU wall role changed")
    if timing.get("validation_mode") != "same-as-n002-full-baseline":
        raise ContractError("N003 preflight validation mode changed")
    if timing.get("comparison_unit") != "paired-fresh-process-A-A":
        raise ContractError("N003 preflight comparison unit changed")
    if timing.get("fresh_process_pair_blocks") != 8:
        raise ContractError("N003 preflight requires eight fresh-process A/A pairs")
    if _number(timing.get("settle_seconds_between_pairs"), "settle_seconds_between_pairs") < 0.0:
        raise ContractError("N003 preflight settle time must be non-negative")
    if _sequence(timing.get("required_totals"), "timing.required_totals") != TIMING_TOTALS:
        raise ContractError("N003 preflight timing totals mismatch")
    if timing.get("sample_exclusion") != "forbidden":
        raise ContractError("N003 preflight sample exclusion must remain forbidden")
    if timing.get("completed_campaign_rerun_budget") != 0:
        raise ContractError("N003 preflight completed rerun budget must remain zero")
    if timing.get("primary_statistic") != "median-paired-log-ratio":
        raise ContractError("N003 preflight primary statistic changed")
    if timing.get("noise_estimator") != "abs-median-log-bias-plus-3x-1.4826-MAD":
        raise ContractError("N003 preflight noise estimator changed")

    threshold = _mapping(timing.get("material_change_threshold"), "timing.material_change_threshold")
    if _number(threshold.get("minimum_fraction"), "threshold minimum") != 0.01:
        raise ContractError("N003 preflight minimum timing threshold changed")
    if _number(threshold.get("round_up_step_fraction"), "threshold step") != 0.005:
        raise ContractError("N003 preflight timing threshold step changed")
    if _number(threshold.get("timing_unsuitable_above_fraction"), "threshold unsuitable") != 0.20:
        raise ContractError("N003 preflight timing suitability ceiling changed")

    formal = _mapping(timing.get("formal_claim_requires"), "timing.formal_claim_requires")
    if _number(formal.get("minimum_same_direction_pair_fraction"), "same-direction fraction") != 0.75:
        raise ContractError("N003 preflight same-direction criterion changed")
    if formal.get("magnitude_at_least_derived_threshold") is not True:
        raise ContractError("N003 preflight magnitude criterion changed")

    control = _mapping(timing.get("control_sanity"), "timing.control_sanity")
    if control.get("must_not_trigger_formal_claim") is not True:
        raise ContractError("N003 preflight control trigger rule changed")
    if _number(control.get("maximum_p95_pair_effect_fraction"), "control p95 ceiling") != 0.20:
        raise ContractError("N003 preflight control p95 ceiling changed")

    quality = _mapping(config.get("quality_interpretation"), "quality_interpretation")
    if _number(quality.get("relative_luminance_floor"), "quality relative floor") != 0.0001:
        raise ContractError("N003 preflight relative luminance floor changed")
    if _number(quality.get("scale_aware_affected_relative_threshold"), "quality affected threshold") != 0.05:
        raise ContractError("N003 preflight scale-aware affected threshold changed")
    if quality.get("legacy_affected_pixel_fraction_role") != "diagnostic-only":
        raise ContractError("legacy affected-pixel metric must remain diagnostic-only")
    if _sequence(quality.get("primary_metrics"), "quality.primary_metrics") != PRIMARY_QUALITY_METRICS:
        raise ContractError("N003 preflight primary quality metrics changed")
    if quality.get("aggregate_winner_score") is not False:
        raise ContractError("N003 preflight forbids an aggregate quality winner score")
    if quality.get("individual_black_reference_frames_valid") is not True:
        raise ContractError("N003 preflight must retain black reference frames")
    material = _mapping(quality.get("material_change"), "quality.material_change")
    if material.get("required_concordant_primary_metrics") != 2:
        raise ContractError("N003 preflight quality concordance rule changed")
    if _number(material.get("error_metric_min_relative_change"), "quality error change") != 0.10:
        raise ContractError("N003 preflight quality error threshold changed")
    if _number(material.get("scale_aware_affected_fraction_min_absolute_change"), "quality affected delta") != 0.005:
        raise ContractError("N003 preflight quality affected-fraction threshold changed")

    artifact = _mapping(config.get("artifact_contract"), "artifact_contract")
    required = set(_sequence(artifact.get("required"), "artifact_contract.required"))
    if required != {
        "n003-preflight-config.json",
        "n003-preflight-progress.json",
        "n003-preflight-raw.json",
        "n003-preflight-summary.json",
    }:
        raise ContractError("N003 preflight artifact contract mismatch")


def _ceil_to_step(value: float, step: float) -> float:
    if value < 0.0 or step <= 0.0:
        raise ContractError("invalid threshold rounding input")
    return math.ceil((value - 1.0e-15) / step) * step


def _member(block: dict[str, Any], role: str) -> dict[str, Any]:
    return _mapping(block.get(role), f"block.{role}")


def summarize_timing(blocks: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    expected_blocks = int(config["timing_calibration"]["fresh_process_pair_blocks"])
    if len(blocks) != expected_blocks:
        raise ContractError(
            f"N003 preflight expected {expected_blocks} A/A pair blocks, got {len(blocks)}"
        )

    per_scenario: dict[str, dict[str, Any]] = {}
    worst_noise = 0.0
    worst_p95_pair_effect = 0.0
    deferred_claim_inputs: list[tuple[dict[str, Any], float, float]] = []

    for scenario in EXPECTED_SCENARIOS:
        axis_summary: dict[str, Any] = {}
        for axis in TIMING_TOTALS:
            ratios: list[float] = []
            logs: list[float] = []
            for block in blocks:
                a_timing = _mapping(_member(block, "A").get("timing"), "block.A.timing")
                b_timing = _mapping(_member(block, "B").get("timing"), "block.B.timing")
                a_frame = _mapping(a_timing.get(scenario), f"A.timing.{scenario}")
                b_frame = _mapping(b_timing.get(scenario), f"B.timing.{scenario}")
                a = _number(a_frame.get(axis), f"A.{scenario}.{axis}")
                b = _number(b_frame.get(axis), f"B.{scenario}.{axis}")
                if a <= 0.0 or b <= 0.0:
                    raise ContractError(f"N003 preflight {scenario}.{axis} must be positive")
                ratio = b / a
                ratios.append(ratio)
                logs.append(math.log(ratio))

            median_log = float(statistics.median(logs))
            abs_deviations = [abs(value - median_log) for value in logs]
            mad_log = float(statistics.median(abs_deviations))
            robust_sigma_log = 1.4826 * mad_log
            noise_log = abs(median_log) + 3.0 * robust_sigma_log
            noise_fraction = math.exp(noise_log) - 1.0
            pair_effects = [math.exp(abs(value)) - 1.0 for value in logs]
            p95_pair_effect = _percentile(pair_effects, 0.95)
            positive_fraction = sum(value > 0.0 for value in logs) / len(logs)
            negative_fraction = sum(value < 0.0 for value in logs) / len(logs)
            same_direction_fraction = max(positive_fraction, negative_fraction)
            median_effect_fraction = math.exp(abs(median_log)) - 1.0

            worst_noise = max(worst_noise, noise_fraction)
            worst_p95_pair_effect = max(worst_p95_pair_effect, p95_pair_effect)
            summary = {
                "ratios_B_over_A": ratios,
                "paired_log_ratios": logs,
                "median_log_ratio": median_log,
                "median_effect_fraction": median_effect_fraction,
                "mad_log_ratio": mad_log,
                "robust_sigma_log_ratio": robust_sigma_log,
                "noise_fraction": noise_fraction,
                "p95_pair_effect_fraction": p95_pair_effect,
                "positive_pair_fraction": positive_fraction,
                "negative_pair_fraction": negative_fraction,
                "same_direction_pair_fraction": same_direction_fraction,
            }
            axis_summary[axis] = summary
            deferred_claim_inputs.append((summary, median_effect_fraction, same_direction_fraction))
        per_scenario[scenario] = axis_summary

    threshold_cfg = config["timing_calibration"]["material_change_threshold"]
    derived = _ceil_to_step(
        max(float(threshold_cfg["minimum_fraction"]), worst_noise),
        float(threshold_cfg["round_up_step_fraction"]),
    )
    direction_min = float(
        config["timing_calibration"]["formal_claim_requires"]["minimum_same_direction_pair_fraction"]
    )
    control_trigger_count = 0
    for summary, magnitude, direction_fraction in deferred_claim_inputs:
        trigger = magnitude >= derived and direction_fraction >= direction_min
        summary["would_trigger_formal_claim"] = trigger
        control_trigger_count += int(trigger)

    unsuitable_above = float(threshold_cfg["timing_unsuitable_above_fraction"])
    p95_ceiling = float(
        config["timing_calibration"]["control_sanity"]["maximum_p95_pair_effect_fraction"]
    )
    suitable = (
        derived <= unsuitable_above
        and worst_p95_pair_effect <= p95_ceiling
        and control_trigger_count == 0
    )
    return {
        "protocol_version": config["protocol_version"],
        "primary_statistic": config["timing_calibration"]["primary_statistic"],
        "noise_estimator": config["timing_calibration"]["noise_estimator"],
        "worst_noise_fraction": worst_noise,
        "worst_p95_pair_effect_fraction": worst_p95_pair_effect,
        "derived_material_change_threshold_fraction": derived,
        "minimum_same_direction_pair_fraction": direction_min,
        "control_formal_claim_trigger_count": control_trigger_count,
        "timing_suitable_for_n003_formal_claims": suitable,
        "timing_unsuitable_above_fraction": unsuitable_above,
        "control_p95_ceiling_fraction": p95_ceiling,
        "per_scenario": per_scenario,
    }


def scale_aware_affected_pixel_fraction(
    output: image_contract.PFMImage,
    reference: image_contract.PFMImage,
    config: dict[str, Any],
) -> float:
    validate_config(config)
    if output.width != reference.width or output.height != reference.height:
        raise ContractError("N003 preflight output/reference dimensions mismatch")
    quality = config["quality_interpretation"]
    relative_floor = float(quality["relative_luminance_floor"])
    relative_threshold = float(quality["scale_aware_affected_relative_threshold"])
    affected = 0
    count = output.width * output.height
    for pixel in range(count):
        base = pixel * 3
        out_y = sum(output.pixels[base + channel] * LUMA[channel] for channel in range(3))
        ref_y = sum(reference.pixels[base + channel] * LUMA[channel] for channel in range(3))
        absolute = abs(out_y - ref_y)
        threshold = relative_threshold * max(abs(ref_y), relative_floor)
        if absolute >= threshold:
            affected += 1
    return affected / count


def summarize_quality(blocks: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    if not blocks:
        raise ContractError("N003 preflight quality summary requires blocks")
    members: list[dict[str, Any]] = []
    for block in blocks:
        members.extend((_member(block, "A"), _member(block, "B")))

    per_scenario: dict[str, dict[str, Any]] = {}
    scale_aware_campaign_has_signal = False
    for scenario in EXPECTED_SCENARIOS:
        metrics: dict[str, Any] = {}
        for metric in PRIMARY_QUALITY_METRICS:
            values: list[float] = []
            for member in members:
                quality = _mapping(member.get("quality"), "member.quality")
                frame = _mapping(quality.get(scenario), f"quality.{scenario}")
                value = _number(frame.get(metric), f"{scenario}.{metric}")
                if value < 0.0:
                    raise ContractError(f"N003 preflight {scenario}.{metric} must be non-negative")
                values.append(value)
            median = float(statistics.median(values))
            max_abs_deviation = max(abs(value - median) for value in values)
            relative_deviation = (
                max(abs(value / median - 1.0) for value in values)
                if median > 0.0
                else 0.0
            )
            metrics[metric] = {
                "values": values,
                "median": median,
                "max_abs_deviation": max_abs_deviation,
                "max_abs_relative_deviation": relative_deviation,
            }
            if metric == "scale_aware_affected_pixel_fraction" and max(values) > 0.0:
                scale_aware_campaign_has_signal = True
        per_scenario[scenario] = metrics
    if not scale_aware_campaign_has_signal:
        raise ContractError(
            "N003 preflight scale-aware affected metric remained zero for the whole campaign"
        )
    return {
        "primary_metrics": PRIMARY_QUALITY_METRICS,
        "scale_aware_campaign_has_signal": True,
        "material_change_rule": config["quality_interpretation"]["material_change"],
        "per_scenario": per_scenario,
    }

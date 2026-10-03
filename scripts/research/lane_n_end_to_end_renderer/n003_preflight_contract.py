from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

import n001_contract as image_contract

SCHEMA_VERSION = 1
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


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("unsupported N003 preflight schema_version")
    if config.get("experiment") != "N003-preflight" or config.get("phase") != "calibration":
        raise ContractError("N003 preflight identity mismatch")

    source = _mapping(config.get("source_of_truth"), "source_of_truth")
    commit = source.get("n002_completion_commit")
    if not isinstance(commit, str) or len(commit) != 40:
        raise ContractError("N003 preflight requires a full N002 completion commit")
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
    if timing.get("fresh_process_blocks") != 6:
        raise ContractError("N003 preflight requires six fresh-process blocks")
    if _number(timing.get("settle_seconds"), "settle_seconds") < 0.0:
        raise ContractError("N003 preflight settle_seconds must be non-negative")
    if _sequence(timing.get("required_totals"), "timing.required_totals") != TIMING_TOTALS:
        raise ContractError("N003 preflight timing totals mismatch")
    if timing.get("sample_exclusion") != "forbidden":
        raise ContractError("N003 preflight sample exclusion must remain forbidden")
    if timing.get("completed_campaign_rerun_budget") != 0:
        raise ContractError("N003 preflight completed rerun budget must remain zero")
    if timing.get("noise_statistic") != "max-absolute-relative-deviation-from-across-block-median":
        raise ContractError("N003 preflight noise statistic changed")

    threshold = _mapping(timing.get("material_change_threshold"), "timing.material_change_threshold")
    if _number(threshold.get("multiplier_over_worst_noise"), "threshold multiplier") != 3.0:
        raise ContractError("N003 preflight timing noise multiplier changed")
    if _number(threshold.get("minimum_fraction"), "threshold minimum") != 0.01:
        raise ContractError("N003 preflight minimum timing threshold changed")
    if _number(threshold.get("round_up_step_fraction"), "threshold step") != 0.005:
        raise ContractError("N003 preflight timing threshold step changed")
    if _number(threshold.get("timing_unsuitable_above_fraction"), "threshold unsuitable") != 0.20:
        raise ContractError("N003 preflight timing suitability ceiling changed")

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


def summarize_timing(blocks: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    expected_blocks = int(config["timing_calibration"]["fresh_process_blocks"])
    if len(blocks) != expected_blocks:
        raise ContractError(
            f"N003 preflight expected {expected_blocks} timing blocks, got {len(blocks)}"
        )

    per_scenario: dict[str, dict[str, Any]] = {}
    worst_noise = 0.0
    for scenario in EXPECTED_SCENARIOS:
        axis_summary: dict[str, Any] = {}
        for axis in TIMING_TOTALS:
            values: list[float] = []
            for block in blocks:
                frames = _mapping(block.get("timing"), "block.timing")
                frame = _mapping(frames.get(scenario), f"timing.{scenario}")
                value = _number(frame.get(axis), f"{scenario}.{axis}")
                if value <= 0.0:
                    raise ContractError(f"N003 preflight {scenario}.{axis} must be positive")
                values.append(value)
            median = float(statistics.median(values))
            deviations = [abs(value / median - 1.0) for value in values]
            maximum = max(deviations)
            worst_noise = max(worst_noise, maximum)
            axis_summary[axis] = {
                "values_us": values,
                "median_us": median,
                "min_us": min(values),
                "max_us": max(values),
                "span_ratio": max(values) / min(values),
                "max_abs_relative_deviation": maximum,
            }
        per_scenario[scenario] = axis_summary

    threshold_cfg = config["timing_calibration"]["material_change_threshold"]
    raw_threshold = max(
        float(threshold_cfg["minimum_fraction"]),
        float(threshold_cfg["multiplier_over_worst_noise"]) * worst_noise,
    )
    derived = _ceil_to_step(
        raw_threshold,
        float(threshold_cfg["round_up_step_fraction"]),
    )
    unsuitable_above = float(threshold_cfg["timing_unsuitable_above_fraction"])
    return {
        "noise_statistic": config["timing_calibration"]["noise_statistic"],
        "worst_noise_fraction": worst_noise,
        "derived_material_change_threshold_fraction": derived,
        "timing_suitable_for_n003_formal_claims": derived <= unsuitable_above,
        "timing_unsuitable_above_fraction": unsuitable_above,
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
    per_scenario: dict[str, dict[str, Any]] = {}
    scale_aware_campaign_has_signal = False
    for scenario in EXPECTED_SCENARIOS:
        metrics: dict[str, Any] = {}
        for metric in PRIMARY_QUALITY_METRICS:
            values: list[float] = []
            for block in blocks:
                quality = _mapping(block.get("quality"), "block.quality")
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

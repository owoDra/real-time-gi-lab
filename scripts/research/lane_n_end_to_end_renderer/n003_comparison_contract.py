from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
PROTOCOL_VERSION = "current-vs-vanilla-v1"
EXPECTED_SCENARIOS = [
    "static",
    "camera-motion",
    "light-motion",
    "moving-rigid",
    "stable-topology-deforming",
    "topology-changing-high-churn",
]
EXPECTED_ORDERS = ["AB", "BA", "AB", "BA", "BA", "AB", "BA", "AB"]
EXPECTED_ROLES = {
    "A": "current-lane-e-final-hwrt",
    "B": "vanilla-software-bvh",
}
TIMING_AXES = ("complete_gi_gpu", "complete_renderer_gpu")
WORKLOAD_FIELDS = (
    "work_items",
    "outputs",
    "requested_work_items",
    "requested_outputs",
    "overflow",
    "visible_owners",
)
TOPOLOGY_FIELDS = (
    "moved_primitives",
    "topology_mutations",
    "topology_replaced_primitives",
    "backend_rebuilds",
)
MEMORY_FIELDS = (
    "persistent",
    "transient",
    "scratch",
    "old_new_overlap",
    "true_lifetime_peak",
    "radiance_storage_persistent",
    "producer_stream_capacity",
    "image_transient",
)
EXPECTED_THRESHOLDS = {
    "static": 0.07,
    "camera-motion": 0.015,
    "light-motion": 0.05,
    "moving-rigid": None,
    "stable-topology-deforming": 0.025,
    "topology-changing-high-churn": 0.015,
}


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


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ContractError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0.0):
        raise ContractError(f"{label} must be finite{' and positive' if positive else ''}")
    return result


def _integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ContractError(f"{label} must be a non-negative integer")
    return value


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("N003 comparison schema_version changed")
    if config.get("experiment") != "N003-current-vs-vanilla" or config.get("phase") != "comparison":
        raise ContractError("N003 comparison identity changed")
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N003 comparison protocol changed")
    if config.get("target_gpu") != "AMD Radeon 8060S Graphics (RADV STRIX_HALO)":
        raise ContractError("N003 comparison target GPU changed")
    if _sequence(config.get("scenarios"), "scenarios") != EXPECTED_SCENARIOS:
        raise ContractError("N003 comparison scenario order changed")

    source = _mapping(config.get("source_of_truth"), "source_of_truth")
    if source.get("parent_issue") != 26 or source.get("issue") != 38 or source.get("preflight_issue") != 31:
        raise ContractError("N003 comparison source-of-truth issues changed")

    baseline = _mapping(config.get("baseline"), "baseline")
    if _mapping(baseline.get("roles"), "baseline.roles") != EXPECTED_ROLES:
        raise ContractError("N003 comparison role identity changed")
    different = _mapping(baseline.get("intentionally_different"), "baseline.intentionally_different")
    if "software-BVH" not in str(different.get("B")):
        raise ContractError("N003 vanilla baseline must remain software-BVH")

    timing = _mapping(config.get("timing"), "timing")
    if timing.get("probe_binary") != "build/phos-n003-comparison":
        raise ContractError("N003 comparison probe binary changed")
    if timing.get("source_warmup_frames") != 32:
        raise ContractError("N003 comparison warm-up count changed")
    if timing.get("outer_blocks") != 8 or timing.get("micro_pairs_per_block") != 5:
        raise ContractError("N003 comparison requires 8 blocks x 5 micro-pairs")
    if _sequence(timing.get("outer_start_orders"), "outer_start_orders") != EXPECTED_ORDERS:
        raise ContractError("N003 comparison outer order changed")
    if timing.get("micro_order_rule") != "alternate-from-outer-start-order":
        raise ContractError("N003 comparison micro order rule changed")
    if timing.get("sample_exclusion") != "forbidden" or timing.get("all_micro_pairs_retained") is not True:
        raise ContractError("N003 comparison must retain every micro-pair")
    if timing.get("completed_campaign_rerun_budget") != 0:
        raise ContractError("N003 comparison completed campaign rerun budget changed")
    if timing.get("gpu_profile_changes") != "forbidden" or timing.get("host_gpu_policy") != "leave-unchanged":
        raise ContractError("N003 comparison must not change host GPU policy")
    if timing.get("ratio") != "B-vanilla-over-A-current":
        raise ContractError("N003 comparison ratio orientation changed")
    if _number(timing.get("minimum_same_direction_block_fraction"), "direction floor") != 0.75:
        raise ContractError("N003 comparison direction floor changed")
    if timing.get("aggregate_winner") != "forbidden":
        raise ContractError("N003 comparison aggregate timing winner must remain forbidden")

    thresholds = _mapping(timing.get("scenario_threshold_fraction"), "scenario thresholds")
    eligibility = _mapping(timing.get("scenario_timing_eligible"), "scenario eligibility")
    if set(thresholds) != set(EXPECTED_SCENARIOS) or set(eligibility) != set(EXPECTED_SCENARIOS):
        raise ContractError("N003 comparison scenario threshold keys changed")
    for scenario, expected in EXPECTED_THRESHOLDS.items():
        actual = thresholds[scenario]
        if expected is None:
            if actual is not None or eligibility[scenario] is not False:
                raise ContractError("moving-rigid timing must remain measurement-limited")
        else:
            if _number(actual, f"threshold[{scenario}]") != expected or eligibility[scenario] is not True:
                raise ContractError(f"N003 comparison threshold/eligibility changed for {scenario}")
    if timing.get("moving_rigid_interpretation") != "measurement-limited-descriptive-only":
        raise ContractError("moving-rigid timing interpretation changed")

    quality = _mapping(config.get("quality"), "quality")
    if quality.get("primary_metrics") != [
        "rgb_rms_error",
        "p99_abs_luminance_error",
        "scale_aware_affected_pixel_fraction",
    ]:
        raise ContractError("N003 comparison quality metrics changed")
    if _number(quality.get("scale_aware_fraction"), "quality scale fraction") != 0.05:
        raise ContractError("N003 quality scale fraction changed")
    if _number(quality.get("scale_aware_floor"), "quality scale floor") != 0.0001:
        raise ContractError("N003 quality scale floor changed")
    if quality.get("aggregate_winner") != "forbidden":
        raise ContractError("N003 aggregate quality winner must remain forbidden")

    correctness = _mapping(config.get("correctness"), "correctness")
    for key in (
        "require_same_device",
        "require_same_producer_workload",
        "require_zero_storage_failures",
        "require_internal_quality_pass",
        "topology_requires_exact_same_mutation_schedule",
    ):
        if correctness.get(key) is not True:
            raise ContractError(f"N003 correctness gate {key} changed")

    required = set(_sequence(_mapping(config.get("artifact_contract"), "artifact contract").get("required"), "required artifacts"))
    if required != {
        "n003-comparison-config.json",
        "n003-comparison-progress.json",
        "n003-comparison-raw.json",
        "n003-comparison-summary.json",
    }:
        raise ContractError("N003 comparison artifact contract changed")


def micro_orders(start_order: str, count: int) -> list[str]:
    if start_order not in {"AB", "BA"} or count <= 0:
        raise ContractError("invalid N003 comparison micro-order request")
    other = "BA" if start_order == "AB" else "AB"
    return [start_order if index % 2 == 0 else other for index in range(count)]


def validate_pair(pair: dict[str, Any], config: dict[str, Any], expected_order: str) -> None:
    validate_config(config)
    if pair.get("schema_version") != 1 or pair.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N003 comparison pair protocol changed")
    if _mapping(pair.get("roles"), "pair.roles") != EXPECTED_ROLES:
        raise ContractError("N003 comparison pair role mapping changed")
    if pair.get("execution_start_order") != expected_order:
        raise ContractError("N003 comparison pair execution order mismatch")
    if pair.get("source_warmup_frames") != 32:
        raise ContractError("N003 comparison pair warm-up changed")

    device = _mapping(pair.get("device"), "pair.device")
    if device.get("name") != config["target_gpu"]:
        raise ContractError("N003 comparison pair ran on the wrong GPU")
    for key in ("driver_name", "driver_info"):
        if not isinstance(device.get(key), str) or not device[key]:
            raise ContractError(f"N003 comparison device {key} missing")
    _integer(device.get("api_version"), "device.api_version")
    _number(device.get("timestamp_period_ns"), "device.timestamp_period_ns", positive=True)

    scenarios = _mapping(pair.get("scenarios"), "pair.scenarios")
    if list(scenarios) != EXPECTED_SCENARIOS:
        raise ContractError("N003 comparison pair scenario order changed")
    for scenario in EXPECTED_SCENARIOS:
        entry = _mapping(scenarios[scenario], f"scenario[{scenario}]")
        a = _mapping(entry.get("A"), f"{scenario}.A")
        b = _mapping(entry.get("B"), f"{scenario}.B")
        for role_name, sample in (("A", a), ("B", b)):
            timing = _mapping(sample.get("timing_us"), f"{scenario}.{role_name}.timing")
            for axis in TIMING_AXES:
                _number(timing.get(axis), f"{scenario}.{role_name}.{axis}", positive=True)
            stats = _mapping(sample.get("stats"), f"{scenario}.{role_name}.stats")
            for field in WORKLOAD_FIELDS + TOPOLOGY_FIELDS + (
                "storage_allocations", "storage_updates", "storage_invalidations", "storage_failures"
            ):
                _integer(stats.get(field), f"{scenario}.{role_name}.stats.{field}")
            if stats["storage_failures"] != 0:
                raise ContractError(f"N003 comparison storage failure in {scenario}/{role_name}")
            memory = _mapping(sample.get("memory_bytes"), f"{scenario}.{role_name}.memory")
            for field in MEMORY_FIELDS:
                _integer(memory.get(field), f"{scenario}.{role_name}.memory.{field}")
            correctness = _mapping(sample.get("correctness"), f"{scenario}.{role_name}.correctness")
            if correctness.get("passed") is not True:
                raise ContractError(f"N003 comparison correctness failed in {scenario}/{role_name}")

        a_stats = a["stats"]
        b_stats = b["stats"]
        for field in WORKLOAD_FIELDS:
            if a_stats[field] != b_stats[field]:
                raise ContractError(f"N003 comparison workload mismatch: {scenario}.{field}")
        if scenario == "topology-changing-high-churn":
            for field in TOPOLOGY_FIELDS:
                if a_stats[field] != b_stats[field]:
                    raise ContractError(f"N003 comparison topology mismatch: {field}")
            if a_stats["topology_mutations"] != 1 or a_stats["backend_rebuilds"] != 1:
                raise ContractError("N003 comparison topology transition count changed")


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = fraction * (len(ordered) - 1)
    lo = math.floor(position)
    hi = math.ceil(position)
    if lo == hi:
        return ordered[lo]
    weight = position - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def summarize(blocks: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    if len(blocks) != 8:
        raise ContractError("N003 comparison requires eight outer blocks")

    for block_index, block in enumerate(blocks):
        if block.get("block") != block_index or block.get("outer_start_order") != EXPECTED_ORDERS[block_index]:
            raise ContractError("N003 comparison outer block identity mismatch")
        micros = _sequence(block.get("micro_pairs"), f"block[{block_index}].micro_pairs")
        if len(micros) != 5:
            raise ContractError("N003 comparison requires five micro-pairs per block")
        orders = micro_orders(EXPECTED_ORDERS[block_index], 5)
        for micro_index, micro in enumerate(micros):
            if micro.get("micro") != micro_index or micro.get("order") != orders[micro_index]:
                raise ContractError("N003 comparison micro identity/order mismatch")
            validate_pair(_mapping(micro.get("pair"), "micro.pair"), config, orders[micro_index])

    per_scenario: dict[str, Any] = {}
    direction_floor = float(config["timing"]["minimum_same_direction_block_fraction"])
    for scenario in EXPECTED_SCENARIOS:
        eligible = bool(config["timing"]["scenario_timing_eligible"][scenario])
        threshold = config["timing"]["scenario_threshold_fraction"][scenario]
        axes: dict[str, Any] = {}
        for axis in TIMING_AXES:
            block_logs: list[float] = []
            raw_ratios: list[float] = []
            for block in blocks:
                micro_logs: list[float] = []
                for micro in block["micro_pairs"]:
                    entry = micro["pair"]["scenarios"][scenario]
                    ratio = float(entry["B"]["timing_us"][axis]) / float(entry["A"]["timing_us"][axis])
                    raw_ratios.append(ratio)
                    micro_logs.append(math.log(ratio))
                block_logs.append(float(statistics.median(micro_logs)))

            median_log = float(statistics.median(block_logs))
            median_ratio = math.exp(median_log)
            positive = sum(value > 0.0 for value in block_logs) / len(block_logs)
            negative = sum(value < 0.0 for value in block_logs) / len(block_logs)
            same_direction = max(positive, negative)
            effect = abs(median_ratio - 1.0)
            formal = bool(
                eligible
                and threshold is not None
                and effect >= float(threshold)
                and same_direction >= direction_floor
            )
            direction = None
            if formal:
                direction = "current-faster" if median_ratio > 1.0 else "vanilla-faster"
            axes[axis] = {
                "block_ratios_vanilla_over_current": [math.exp(value) for value in block_logs],
                "median_ratio_vanilla_over_current": median_ratio,
                "median_effect_fraction": effect,
                "p95_raw_micro_pair_effect_fraction": _percentile(
                    [abs(value - 1.0) for value in raw_ratios], 0.95
                ),
                "positive_block_fraction": positive,
                "negative_block_fraction": negative,
                "same_direction_block_fraction": same_direction,
                "frozen_threshold_fraction": threshold,
                "timing_eligible": eligible,
                "formal_material_change_detected": formal,
                "formal_direction": direction,
            }

        memory_samples: dict[str, Any] = {}
        for role in ("A", "B"):
            role_memory: dict[str, Any] = {}
            for field in MEMORY_FIELDS:
                values = [
                    int(micro["pair"]["scenarios"][scenario][role]["memory_bytes"][field])
                    for block in blocks for micro in block["micro_pairs"]
                ]
                role_memory[field] = {
                    "value": values[0],
                    "invariant": all(value == values[0] for value in values),
                }
            memory_samples[role] = role_memory
        per_scenario[scenario] = {
            "timing_status": "eligible" if eligible else "measurement-limited",
            "axes": axes,
            "memory": memory_samples,
        }

    return {
        "ratio_orientation": "B-vanilla-over-A-current",
        "per_scenario": per_scenario,
        "aggregate_winner": None,
    }

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Iterable


def median(values: Iterable[float]) -> float:
    data = list(values)
    if not data:
        raise ValueError("median requires at least one value")
    return float(statistics.median(data))


def ratio_from_log(value: float) -> float:
    return math.exp(abs(value))


def summarize_process(rows: list[dict[str, object]]) -> dict[str, object]:
    measured = [row for row in rows if row["phase"] == "measured"]
    if not measured:
        raise ValueError("process has no measured rows")

    pairs: dict[int, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in measured:
        pair_index = int(row["pair_index"])
        role = str(row["role"])
        if role not in {"A", "B"}:
            raise ValueError(f"invalid role: {role}")
        if role in pairs[pair_index]:
            raise ValueError(f"duplicate role {role} for pair {pair_index}")
        pairs[pair_index][role] = row

    axis_values: dict[str, dict[str, object]] = {}
    for axis, field in (("gpu", "gpu_us"), ("wall", "complete_wall_us")):
        logs: list[float] = []
        ratios: list[float] = []
        a_values: list[float] = []
        b_values: list[float] = []
        by_order: dict[str, list[float]] = {"AB": [], "BA": []}

        for pair_index in sorted(pairs):
            pair = pairs[pair_index]
            if set(pair) != {"A", "B"}:
                raise ValueError(f"pair {pair_index} is incomplete")
            a = float(pair["A"][field])
            b = float(pair["B"][field])
            if a <= 0.0 or b <= 0.0:
                raise ValueError("timings must be positive")
            order_a = str(pair["A"]["order"])
            order_b = str(pair["B"]["order"])
            if order_a != order_b or order_a not in by_order:
                raise ValueError(f"pair {pair_index} has invalid order metadata")
            log_ratio = math.log(b / a)
            logs.append(log_ratio)
            ratios.append(b / a)
            a_values.append(a)
            b_values.append(b)
            by_order[order_a].append(log_ratio)

        if not by_order["AB"] or not by_order["BA"]:
            raise ValueError("process must contain both AB and BA measured pairs")

        med = median(logs)
        mean_log = float(statistics.fmean(logs))
        total_ratio = sum(b_values) / sum(a_values)
        positive_fraction = sum(1 for value in logs if value > 0.0) / len(logs)
        ab_median = median(by_order["AB"])
        ba_median = median(by_order["BA"])
        axis_values[axis] = {
            "pair_count": len(logs),
            "median_log_ratio": med,
            "median_ratio": math.exp(med),
            "geometric_mean_ratio": math.exp(mean_log),
            "total_duration_ratio": total_ratio,
            "positive_pair_fraction": positive_fraction,
            "ab_median_log_ratio": ab_median,
            "ba_median_log_ratio": ba_median,
            "order_bias_ratio": math.exp(abs(ab_median - ba_median)),
            "a_median_us": median(a_values),
            "b_median_us": median(b_values),
            "a_mean_us": float(statistics.fmean(a_values)),
            "b_mean_us": float(statistics.fmean(b_values)),
            "a_total_us": sum(a_values),
            "b_total_us": sum(b_values),
        }

    first = measured[0]
    return {
        "comparison": first["comparison"],
        "candidate": first["candidate"],
        "block": int(first["block"]),
        "slot": int(first["slot"]),
        "process_id": first["process_id"],
        "gpu": axis_values["gpu"],
        "wall": axis_values["wall"],
    }


def evaluate_control(
    process_rows: list[dict[str, object]],
    axis: str,
    criteria: dict[str, float],
) -> dict[str, object]:
    if not process_rows:
        raise ValueError("control evaluation requires process rows")
    logs = [float(row[axis]["median_log_ratio"]) for row in process_rows]
    max_abs = max(abs(value) for value in logs)
    span_ratio = math.exp(max(logs) - min(logs))
    max_order_bias = max(float(row[axis]["order_bias_ratio"]) for row in process_rows)

    max_abs_limit = math.log(float(criteria["control_max_abs_process_median_ratio"]))
    passed = (
        max_abs <= max_abs_limit
        and span_ratio <= float(criteria["control_process_median_span_ratio"])
        and max_order_bias
        <= float(criteria["control_max_within_process_order_bias_ratio"])
    )
    return {
        "passed": passed,
        "process_count": len(process_rows),
        "process_median_ratios": [math.exp(value) for value in logs],
        "max_abs_process_median_ratio": math.exp(max_abs),
        "process_median_span_ratio": span_ratio,
        "max_within_process_order_bias_ratio": max_order_bias,
        "noise_envelope_log": max_abs,
        "noise_envelope_ratio": math.exp(max_abs),
    }


def evaluate_candidate(
    process_rows: list[dict[str, object]],
    axis: str,
    criteria: dict[str, float],
    control: dict[str, object],
) -> dict[str, object]:
    if not process_rows:
        raise ValueError("candidate evaluation requires process rows")
    logs = [float(row[axis]["median_log_ratio"]) for row in process_rows]
    noise = float(control["noise_envelope_log"])
    effect_span_ratio = math.exp(max(logs) - min(logs))
    min_positive_fraction = min(
        float(row[axis]["positive_pair_fraction"]) for row in process_rows
    )
    max_order_bias = max(float(row[axis]["order_bias_ratio"]) for row in process_rows)
    detected = (
        bool(control["passed"])
        and min(logs) > noise
        and min_positive_fraction
        >= float(criteria["candidate_min_positive_pair_fraction"])
        and effect_span_ratio <= float(criteria["candidate_process_effect_span_ratio"])
        and max_order_bias
        <= float(criteria["candidate_max_within_process_order_bias_ratio"])
    )
    return {
        "detected": detected,
        "process_count": len(process_rows),
        "process_median_ratios": [math.exp(value) for value in logs],
        "minimum_process_median_ratio": math.exp(min(logs)),
        "campaign_median_ratio": math.exp(median(logs)),
        "process_effect_span_ratio": effect_span_ratio,
        "minimum_positive_pair_fraction": min_positive_fraction,
        "max_within_process_order_bias_ratio": max_order_bias,
        "control_noise_envelope_ratio": float(control["noise_envelope_ratio"]),
    }


def classify_resolution(
    detections: dict[str, bool],
    control_passed: bool,
) -> str:
    if not control_passed:
        return "baseline-control-failed"
    p20 = bool(detections.get("plus20", False))
    p10 = bool(detections.get("plus10", False))
    p5 = bool(detections.get("plus5", False))
    if (p10 or p5) and not p20:
        return "inconclusive-nonmonotonic"
    if p5 and not p10:
        return "inconclusive-nonmonotonic"
    if not p20:
        return "target-timing-unsuitable"
    if p5 and p10 and p20:
        return "5%"
    if p10 and p20:
        return "10%"
    return "20%"


def summarize_accepted(
    process_rows: list[dict[str, object]],
    config: dict[str, object],
) -> dict[str, object]:
    by_comparison: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in process_rows:
        by_comparison[str(row["comparison"])].append(row)

    expected = int(config["fresh_process_blocks"])
    for name in config["comparisons"]:
        if len(by_comparison[name]) != expected:
            raise ValueError(
                f"{name}: expected {expected} fresh processes, got "
                f"{len(by_comparison[name])}"
            )

    result: dict[str, object] = {"axes": {}}
    criteria_by_axis = config["repeatability_criteria"]
    for axis in ("gpu", "wall"):
        criteria = criteria_by_axis[axis]
        control = evaluate_control(by_comparison["control"], axis, criteria)
        comparisons: dict[str, object] = {"control": control}
        detections: dict[str, bool] = {}
        for name in ("plus20", "plus10", "plus5"):
            evaluated = evaluate_candidate(
                by_comparison[name], axis, criteria, control
            )
            comparisons[name] = evaluated
            detections[name] = bool(evaluated["detected"])
        result["axes"][axis] = {
            "comparisons": comparisons,
            "resolution": classify_resolution(detections, bool(control["passed"])),
        }
    return result

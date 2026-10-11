from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Iterable


def median(values: Iterable[float]) -> float:
    data = list(values)
    if not data:
        raise ValueError("median requires data")
    return float(statistics.median(data))


def summarize_process(rows: list[dict[str, object]]) -> dict[str, object]:
    measured = [row for row in rows if row["phase"] == "measured"]
    if not measured:
        raise ValueError("process has no measured rows")

    pairs: dict[int, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in measured:
        pair_index = int(row["pair_index"])
        role = str(row["role"])
        if role not in {"A", "B"} or role in pairs[pair_index]:
            raise ValueError("invalid or duplicate pair role")
        pairs[pair_index][role] = row

    axes: dict[str, dict[str, object]] = {}
    for axis, field in (("gpu", "gpu_us"), ("wall", "complete_wall_us")):
        logs: list[float] = []
        a_values: list[float] = []
        b_values: list[float] = []
        by_order: dict[str, list[float]] = {"AB": [], "BA": []}
        improving = 0

        for pair_index in sorted(pairs):
            pair = pairs[pair_index]
            if set(pair) != {"A", "B"}:
                raise ValueError(f"incomplete pair {pair_index}")
            a = float(pair["A"][field])
            b = float(pair["B"][field])
            if not math.isfinite(a) or not math.isfinite(b) or a <= 0 or b <= 0:
                raise ValueError("timings must be positive finite values")
            order_a = str(pair["A"]["order"])
            order_b = str(pair["B"]["order"])
            if order_a != order_b or order_a not in by_order:
                raise ValueError("pair order metadata mismatch")

            value = math.log(b / a)
            logs.append(value)
            by_order[order_a].append(value)
            a_values.append(a)
            b_values.append(b)
            if value < 0:
                improving += 1

        if not by_order["AB"] or not by_order["BA"]:
            raise ValueError("process must contain both AB and BA measured pairs")

        med = median(logs)
        ab_med = median(by_order["AB"])
        ba_med = median(by_order["BA"])
        axes[axis] = {
            "pair_count": len(logs),
            "median_log_ratio": med,
            "median_ratio": math.exp(med),
            "geometric_mean_ratio": math.exp(float(statistics.fmean(logs))),
            "total_duration_ratio": sum(b_values) / sum(a_values),
            "improving_pair_fraction": improving / len(logs),
            "ab_median_log_ratio": ab_med,
            "ba_median_log_ratio": ba_med,
            "order_bias_ratio": math.exp(abs(ab_med - ba_med)),
            "a_median_us": median(a_values),
            "b_median_us": median(b_values),
            "a_total_us": sum(a_values),
            "b_total_us": sum(b_values),
        }

    first = measured[0]
    return {
        "track": first["track"],
        "profile": first["profile"],
        "comparison": first["comparison"],
        "block": int(first["block"]),
        "process_id": first["process_id"],
        "gpu": axes["gpu"],
        "wall": axes["wall"],
    }


def evaluate_control(
    process_rows: list[dict[str, object]],
    axis: str,
    criteria: dict[str, float],
) -> dict[str, object]:
    logs = [float(row[axis]["median_log_ratio"]) for row in process_rows]
    if not logs:
        raise ValueError("control evaluation requires process rows")
    max_abs = max(abs(value) for value in logs)
    span_ratio = math.exp(max(logs) - min(logs))
    max_order_bias = max(float(row[axis]["order_bias_ratio"]) for row in process_rows)
    passed = (
        max_abs <= math.log(float(criteria["control_max_abs_process_median_ratio"]))
        and span_ratio <= float(criteria["control_process_median_span_ratio"])
        and max_order_bias <= float(criteria["control_max_within_process_order_bias_ratio"])
    )
    return {
        "passed": passed,
        "process_count": len(logs),
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
    logs = [float(row[axis]["median_log_ratio"]) for row in process_rows]
    if not logs:
        raise ValueError("candidate evaluation requires process rows")

    noise = float(control["noise_envelope_log"])
    span_ratio = math.exp(max(logs) - min(logs))
    max_order_bias = max(float(row[axis]["order_bias_ratio"]) for row in process_rows)
    min_improving_fraction = min(
        float(row[axis]["improving_pair_fraction"])
        for row in process_rows
    )
    campaign_ratio = math.exp(median(logs))

    repeatable = (
        span_ratio <= float(criteria["candidate_process_effect_span_ratio"])
        and max_order_bias <= float(criteria["candidate_max_within_process_order_bias_ratio"])
    )
    beyond_noise = max(logs) < -noise
    detected_improvement = (
        bool(control["passed"])
        and repeatable
        and beyond_noise
        and min_improving_fraction
        >= float(criteria["candidate_min_improving_pair_fraction"])
    )
    promoted = (
        detected_improvement
        and campaign_ratio <= float(criteria["promotion_ratio_max"])
    )
    nonregression = (
        bool(control["passed"])
        and repeatable
        and campaign_ratio <= float(criteria["nonregression_ratio_max"])
    )

    return {
        "process_count": len(logs),
        "process_median_ratios": [math.exp(value) for value in logs],
        "campaign_median_ratio": campaign_ratio,
        "process_effect_span_ratio": span_ratio,
        "max_within_process_order_bias_ratio": max_order_bias,
        "minimum_improving_pair_fraction": min_improving_fraction,
        "control_noise_envelope_ratio": float(control["noise_envelope_ratio"]),
        "every_process_beyond_control_noise": beyond_noise,
        "repeatable": repeatable,
        "detected_improvement": detected_improvement,
        "promoted": promoted,
        "nonregression": nonregression,
    }


def summarize_profile(
    process_rows: list[dict[str, object]],
    config: dict[str, object],
) -> dict[str, object]:
    by_comparison: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in process_rows:
        by_comparison[str(row["comparison"])].append(row)

    expected = int(config["timing"]["fresh_process_blocks"])
    for name in ("control", "candidate"):
        if len(by_comparison[name]) != expected:
            raise ValueError(
                f"{name}: expected {expected} processes, got {len(by_comparison[name])}"
            )

    criteria = config["gpu_primary_criteria"]
    gpu_control = evaluate_control(by_comparison["control"], "gpu", criteria)
    gpu_candidate = evaluate_candidate(
        by_comparison["candidate"], "gpu", criteria, gpu_control
    )

    # CPU wall is intentionally diagnostic only. The annotation thresholds
    # are frozen in the execution config and can never veto a GPU-primary
    # decision.
    wall_criteria = config["cpu_wall_health"]["annotation_criteria"]
    wall_control = evaluate_control(
        by_comparison["control"], "wall", wall_criteria
    )
    wall_candidate = evaluate_candidate(
        by_comparison["candidate"], "wall", {
            **criteria,
            **wall_criteria,
        }, wall_control
    )

    return {
        "gpu_primary": {
            "control": gpu_control,
            "candidate": gpu_candidate,
        },
        "cpu_wall": {
            "decision_use": "diagnostic-health-provenance-only",
            "control": wall_control,
            "candidate": wall_candidate,
            "invalidates_gpu_decision": False,
        },
    }


def class_decisions(
    profile_summaries: dict[str, dict[str, object]],
    config: dict[str, object],
) -> dict[str, object]:
    classes = config["selector"]["classes"]
    decisions: dict[str, object] = {}

    all_profiles = set(profile_summaries)
    for class_name, members_value in classes.items():
        members = [str(value) for value in members_value]
        others = sorted(all_profiles - set(members))
        member_pass = all(
            bool(
                profile_summaries[name]["gpu_primary"]["candidate"]["promoted"]
            )
            for name in members
        )
        other_nonregression = all(
            bool(
                profile_summaries[name]["gpu_primary"]["candidate"]["nonregression"]
            )
            for name in others
        )
        decisions[class_name] = {
            "profiles": members,
            "other_profiles": others,
            "all_class_profiles_promoted": member_pass,
            "all_other_profiles_nonregressing": other_nonregression,
            "retained": member_pass and other_nonregression,
        }

    return decisions

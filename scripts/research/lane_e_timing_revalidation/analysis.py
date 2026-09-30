from __future__ import annotations

import math
import statistics
from collections import defaultdict


def median(values: list[float]) -> float:
    if not values:
        raise ValueError("median requires data")
    return float(statistics.median(values))


def summarize_process(rows: list[dict[str, object]]) -> dict[str, object]:
    measured = [row for row in rows if str(row["phase"]) == "measured"]
    pairs: dict[int, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in measured:
        pair = int(row["pair_index"])
        role = str(row["role"])
        if role not in {"A", "B"} or role in pairs[pair]:
            raise ValueError("invalid or duplicate pair role")
        pairs[pair][role] = row
    if len(pairs) != 12:
        raise ValueError(f"expected 12 measured pairs, got {len(pairs)}")

    logs: list[float] = []
    by_order: dict[str, list[float]] = {"AB": [], "BA": []}
    positive = 0
    negative = 0
    for pair in sorted(pairs):
        roles = pairs[pair]
        if set(roles) != {"A", "B"}:
            raise ValueError(f"incomplete pair {pair}")
        a = float(roles["A"]["gpu_us"])
        b = float(roles["B"]["gpu_us"])
        if not math.isfinite(a) or not math.isfinite(b) or a <= 0 or b <= 0:
            raise ValueError("GPU timings must be positive finite")
        order_a = str(roles["A"]["order"])
        order_b = str(roles["B"]["order"])
        if order_a != order_b or order_a not in by_order:
            raise ValueError("pair order mismatch")
        value = math.log(b / a)
        logs.append(value)
        by_order[order_a].append(value)
        positive += value > 0
        negative += value < 0

    if not by_order["AB"] or not by_order["BA"]:
        raise ValueError("each process requires measured AB and BA strata")

    med = median(logs)
    ab = median(by_order["AB"])
    ba = median(by_order["BA"])
    first = measured[0]
    return {
        "scenario": first["scenario"],
        "track": first["track"],
        "comparison": first["comparison"],
        "block": int(first["block"]),
        "median_log_ratio": med,
        "median_ratio": math.exp(med),
        "ab_median_ratio": math.exp(ab),
        "ba_median_ratio": math.exp(ba),
        "order_bias_ratio": math.exp(abs(ab - ba)),
        "positive_pair_fraction": positive / len(logs),
        "negative_pair_fraction": negative / len(logs),
    }


def control_envelope(processes: list[dict[str, object]]) -> dict[str, float]:
    if len(processes) != 8:
        raise ValueError(f"expected 8 control processes, got {len(processes)}")
    ratios = [float(row["median_ratio"]) for row in processes]
    max_abs = max(max(value, 1.0 / value) for value in ratios)
    span = max(ratios) / min(ratios)
    order_bias = max(float(row["order_bias_ratio"]) for row in processes)
    return {
        "max_abs_process_median_ratio": max_abs,
        "process_median_span_ratio": span,
        "max_within_process_order_bias_ratio": order_bias,
        "combined_noise_envelope_ratio": max(max_abs, span, order_bias),
    }


def classify_performance(
    candidate_processes: list[dict[str, object]],
    control: dict[str, float],
    threshold: float = 0.20,
    min_directional_fraction: float = 0.75,
) -> dict[str, object]:
    if len(candidate_processes) != 8:
        raise ValueError(
            f"expected 8 candidate processes, got {len(candidate_processes)}"
        )
    logs = [math.log(float(row["median_ratio"])) for row in candidate_processes]
    overall = math.exp(median(logs))
    envelope = float(control["combined_noise_envelope_ratio"])

    improvement_direction = (
        all(float(row["median_ratio"]) < 1.0 for row in candidate_processes)
        and all(float(row["ab_median_ratio"]) < 1.0 for row in candidate_processes)
        and all(float(row["ba_median_ratio"]) < 1.0 for row in candidate_processes)
        and min(float(row["negative_pair_fraction"]) for row in candidate_processes)
        >= min_directional_fraction
    )
    regression_direction = (
        all(float(row["median_ratio"]) > 1.0 for row in candidate_processes)
        and all(float(row["ab_median_ratio"]) > 1.0 for row in candidate_processes)
        and all(float(row["ba_median_ratio"]) > 1.0 for row in candidate_processes)
        and min(float(row["positive_pair_fraction"]) for row in candidate_processes)
        >= min_directional_fraction
    )

    improvement_effect = (1.0 / overall) if overall < 1.0 else 1.0
    regression_effect = overall if overall > 1.0 else 1.0
    improvement = (
        overall <= (1.0 - threshold)
        and improvement_effect > envelope
        and improvement_direction
    )
    regression = (
        overall >= (1.0 + threshold)
        and regression_effect > envelope
        and regression_direction
    )

    if improvement:
        classification = ">=20% detected improvement"
    elif regression:
        classification = "detected >=20% regression"
    else:
        classification = "<20% difference / measurement-limited"

    return {
        "classification": classification,
        "candidate_control_ratio": overall,
        "improvement_fraction": 1.0 - overall,
        "regression_fraction": overall - 1.0,
        "control_noise_envelope_ratio": envelope,
        "improvement_direction_gate": improvement_direction,
        "regression_direction_gate": regression_direction,
        "effect_exceeds_control_noise": max(improvement_effect, regression_effect)
        > envelope,
    }


def classify_memory(rows: list[dict[str, object]]) -> dict[str, object]:
    measured = [row for row in rows if str(row["phase"]) == "measured"]
    pairs: dict[tuple[int, int], dict[str, dict[str, object]]] = defaultdict(dict)
    for row in measured:
        key = (int(row["block"]), int(row["pair_index"]))
        pairs[key][str(row["role"])] = row
    persistent_ratios: list[float] = []
    peak_ratios: list[float] = []
    overlap_ratios: list[float] = []
    for key, pair in pairs.items():
        if set(pair) != {"A", "B"}:
            raise ValueError(f"incomplete memory pair {key}")
        a_p = float(pair["A"]["persistent_bytes"])
        b_p = float(pair["B"]["persistent_bytes"])
        a_peak = float(pair["A"]["true_peak_bytes"])
        b_peak = float(pair["B"]["true_peak_bytes"])
        if a_p <= 0 or a_peak <= 0:
            raise ValueError("control memory must be positive")
        persistent_ratios.append(b_p / a_p)
        peak_ratios.append(b_peak / a_peak)
        a_overlap = float(pair["A"]["old_new_overlap_bytes"])
        b_overlap = float(pair["B"]["old_new_overlap_bytes"])
        overlap_ratios.append(
            b_overlap / a_overlap if a_overlap > 0 else (1.0 if b_overlap == 0 else math.inf)
        )
    if not persistent_ratios:
        raise ValueError("memory classification requires measured pairs")

    persistent_median = median(persistent_ratios)
    peak_median = median(peak_ratios)
    persistent_max = max(persistent_ratios)
    peak_max = max(peak_ratios)
    lifetime_complete = all(
        int(row.get("allocation_lifetime_complete", 0)) == 1
        for row in measured
    )
    hard_regression = (
        persistent_max > 1.25
        or peak_max > 1.25
        or not lifetime_complete
    )
    if hard_regression:
        classification = "regression"
    elif persistent_median <= 1.0 and peak_median <= 1.0 and (
        persistent_median < 1.0 or peak_median < 1.0
    ):
        classification = "improvement"
    else:
        classification = "neutral"
    return {
        "classification": classification,
        "persistent_ratio_median": persistent_median,
        "persistent_ratio_max": persistent_max,
        "true_peak_ratio_median": peak_median,
        "true_peak_ratio_max": peak_max,
        "old_new_overlap_ratio_median": median(overlap_ratios),
        "allocation_lifetime_accounting_complete": lifetime_complete,
    }


def summarize_campaign(
    raw_rows: list[dict[str, object]],
) -> dict[str, object]:
    by_process: dict[tuple[str, str, str, int], list[dict[str, object]]] = defaultdict(list)
    for row in raw_rows:
        key = (
            str(row["scenario"]),
            str(row["track"]),
            str(row["comparison"]),
            int(row["block"]),
        )
        by_process[key].append(row)

    process_rows = [summarize_process(rows) for rows in by_process.values()]
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in process_rows:
        grouped[(str(row["scenario"]), str(row["track"]), str(row["comparison"]))].append(row)

    results: dict[str, object] = {}
    scenarios = sorted({str(row["scenario"]) for row in process_rows})
    tracks = sorted({str(row["track"]) for row in process_rows})
    for scenario in scenarios:
        results[scenario] = {}
        for track in tracks:
            controls = grouped[(scenario, track, "control")]
            candidates = grouped[(scenario, track, "candidate")]
            envelope = control_envelope(controls)
            perf = classify_performance(candidates, envelope)
            candidate_raw = [
                row for row in raw_rows
                if str(row["scenario"]) == scenario
                and str(row["track"]) == track
                and str(row["comparison"]) == "candidate"
            ]
            memory = classify_memory(candidate_raw)
            results[scenario][track] = {
                "control": envelope,
                "performance": perf,
                "memory": memory,
            }
    return {"process_rows": process_rows, "results": results}

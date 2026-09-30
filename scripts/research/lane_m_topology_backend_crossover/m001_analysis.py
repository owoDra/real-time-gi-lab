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
    faster = 0
    slower = 0
    for pair in sorted(pairs):
        roles = pairs[pair]
        if set(roles) != {"A", "B"}:
            raise ValueError(f"incomplete pair {pair}")
        a = float(roles["A"]["gpu_us"])
        b = float(roles["B"]["gpu_us"])
        if not math.isfinite(a) or not math.isfinite(b) or a <= 0 or b <= 0:
            raise ValueError("GPU timings must be positive finite")
        order = str(roles["A"]["order"])
        if order != str(roles["B"]["order"]) or order not in by_order:
            raise ValueError("pair order mismatch")
        value = math.log(b / a)
        logs.append(value)
        by_order[order].append(value)
        faster += value < 0
        slower += value > 0

    if not by_order["AB"] or not by_order["BA"]:
        raise ValueError("each process requires AB and BA measured strata")

    first = measured[0]
    med = median(logs)
    ab = median(by_order["AB"])
    ba = median(by_order["BA"])
    return {
        "scenario": str(first["scenario"]),
        "track": str(first["track"]),
        "comparison": str(first["comparison"]),
        "block": int(first["block"]),
        "median_ratio": math.exp(med),
        "ab_median_ratio": math.exp(ab),
        "ba_median_ratio": math.exp(ba),
        "order_bias_ratio": math.exp(abs(ab - ba)),
        "faster_pair_fraction": faster / len(logs),
        "slower_pair_fraction": slower / len(logs),
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
    logs = [
        math.log(float(row["median_ratio"]))
        for row in candidate_processes
    ]
    overall = math.exp(median(logs))
    envelope = float(control["combined_noise_envelope_ratio"])

    improvement_direction = (
        all(float(row["median_ratio"]) < 1.0 for row in candidate_processes)
        and all(float(row["ab_median_ratio"]) < 1.0 for row in candidate_processes)
        and all(float(row["ba_median_ratio"]) < 1.0 for row in candidate_processes)
        and min(float(row["faster_pair_fraction"]) for row in candidate_processes)
        >= min_directional_fraction
    )
    regression_direction = (
        all(float(row["median_ratio"]) > 1.0 for row in candidate_processes)
        and all(float(row["ab_median_ratio"]) > 1.0 for row in candidate_processes)
        and all(float(row["ba_median_ratio"]) > 1.0 for row in candidate_processes)
        and min(float(row["slower_pair_fraction"]) for row in candidate_processes)
        >= min_directional_fraction
    )

    improvement_effect = 1.0 / overall if overall < 1.0 else 1.0
    regression_effect = overall if overall > 1.0 else 1.0
    improvement = (
        overall <= 1.0 - threshold
        and improvement_effect > envelope
        and improvement_direction
    )
    regression = (
        overall >= 1.0 + threshold
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
        "control_noise_envelope_ratio": envelope,
        "improvement_direction_gate": improvement_direction,
        "regression_direction_gate": regression_direction,
        "effect_exceeds_control_noise": max(
            improvement_effect, regression_effect
        ) > envelope,
    }


def classify_memory(rows: list[dict[str, object]]) -> dict[str, object]:
    measured = [row for row in rows if str(row["phase"]) == "measured"]
    pairs: dict[tuple[int, int], dict[str, dict[str, object]]] = defaultdict(dict)
    for row in measured:
        key = (int(row["block"]), int(row["pair_index"]))
        pairs[key][str(row["role"])] = row

    persistent: list[float] = []
    peaks: list[float] = []
    for key, roles in pairs.items():
        if set(roles) != {"A", "B"}:
            raise ValueError(f"incomplete memory pair {key}")
        a_p = float(roles["A"]["persistent_bytes"])
        b_p = float(roles["B"]["persistent_bytes"])
        a_peak = float(roles["A"]["true_peak_resident_bytes"])
        b_peak = float(roles["B"]["true_peak_resident_bytes"])
        if a_p <= 0 or a_peak <= 0:
            raise ValueError("control memory must be positive")
        persistent.append(b_p / a_p)
        peaks.append(b_peak / a_peak)

    if not persistent:
        raise ValueError("memory classification requires measured pairs")
    lifetime_complete = all(
        int(row["allocation_lifetime_complete"]) == 1
        for row in measured
    )
    p_max = max(persistent)
    peak_max = max(peaks)
    passed = p_max <= 1.25 and peak_max <= 1.25 and lifetime_complete
    return {
        "passed": passed,
        "classification": "pass" if passed else "hard-guard-fail",
        "persistent_ratio_median": median(persistent),
        "persistent_ratio_max": p_max,
        "true_peak_ratio_median": median(peaks),
        "true_peak_ratio_max": peak_max,
        "allocation_lifetime_accounting_complete": lifetime_complete,
    }


def summarize_first_stage(
    raw_rows: list[dict[str, object]],
) -> dict[str, object]:
    by_process: dict[
        tuple[str, str, str, int], list[dict[str, object]]
    ] = defaultdict(list)
    for row in raw_rows:
        key = (
            str(row["scenario"]),
            str(row["track"]),
            str(row["comparison"]),
            int(row["block"]),
        )
        by_process[key].append(row)
    process_rows = [summarize_process(rows) for rows in by_process.values()]

    grouped: dict[
        tuple[str, str, str], list[dict[str, object]]
    ] = defaultdict(list)
    for row in process_rows:
        grouped[
            (str(row["scenario"]), str(row["track"]), str(row["comparison"]))
        ].append(row)

    results: dict[str, object] = {}
    scenarios = sorted({str(row["scenario"]) for row in process_rows})
    tracks = sorted({str(row["track"]) for row in process_rows})
    for scenario in scenarios:
        results[scenario] = {}
        for track in tracks:
            controls = grouped[(scenario, track, "control")]
            envelope = control_envelope(controls)
            results[scenario][track] = {"control": envelope, "candidates": {}}
            for candidate in ("lbvh", "clustered"):
                processes = grouped[(scenario, track, candidate)]
                perf = classify_performance(processes, envelope)
                candidate_raw = [
                    row for row in raw_rows
                    if str(row["scenario"]) == scenario
                    and str(row["track"]) == track
                    and str(row["comparison"]) == candidate
                ]
                memory = classify_memory(candidate_raw)
                results[scenario][track]["candidates"][candidate] = {
                    "performance": perf,
                    "memory": memory,
                    "incumbent_promotion_gate": (
                        perf["classification"] == ">=20% detected improvement"
                        and memory["passed"]
                    ),
                }

    stable = results.get("stable-no-change-guard", {})
    for scenario, by_track in results.items():
        if scenario == "stable-no-change-guard":
            continue
        for track, record in by_track.items():
            stable_track = stable[track]
            for candidate, candidate_record in record["candidates"].items():
                guard = stable_track["candidates"][candidate]
                stable_ok = (
                    guard["performance"]["classification"]
                    != "detected >=20% regression"
                    and guard["memory"]["passed"]
                )
                candidate_record["stable_guard_passed"] = stable_ok
                candidate_record["promotion_eligible"] = (
                    candidate_record["incumbent_promotion_gate"] and stable_ok
                )

    return {"process_rows": process_rows, "results": results}


def summarize_direct_stage(
    raw_rows: list[dict[str, object]],
) -> dict[str, object]:
    by_process: dict[
        tuple[str, str, str, int], list[dict[str, object]]
    ] = defaultdict(list)
    for row in raw_rows:
        key = (
            str(row["scenario"]),
            str(row["track"]),
            str(row["comparison"]),
            int(row["block"]),
        )
        by_process[key].append(row)
    process_rows = [summarize_process(rows) for rows in by_process.values()]
    grouped: dict[
        tuple[str, str, str], list[dict[str, object]]
    ] = defaultdict(list)
    for row in process_rows:
        grouped[
            (str(row["scenario"]), str(row["track"]), str(row["comparison"]))
        ].append(row)

    results: dict[str, object] = {}
    keys = sorted({
        (str(row["scenario"]), str(row["track"]))
        for row in process_rows
    })
    for scenario, track in keys:
        envelope = control_envelope(
            grouped[(scenario, track, "lbvh-control")]
        )
        perf = classify_performance(
            grouped[(scenario, track, "clustered-vs-lbvh")],
            envelope,
        )
        if perf["classification"] == ">=20% detected improvement":
            decision = "clustered detectably faster than LBVH"
        elif perf["classification"] == "detected >=20% regression":
            decision = "LBVH detectably faster than clustered"
        else:
            decision = "<20% difference / measurement-limited; do not rank"
        results.setdefault(scenario, {})[track] = {
            "control": envelope,
            "performance": perf,
            "decision": decision,
        }
    return {"process_rows": process_rows, "results": results}

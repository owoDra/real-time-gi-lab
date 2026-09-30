from __future__ import annotations

import importlib.util
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
J004_ANALYSIS = (
    ROOT
    / "scripts/research/lane_j_topology_backend_alternatives/j004_analysis.py"
)

_spec = importlib.util.spec_from_file_location(
    "lane_j_j004_analysis_for_l002", J004_ANALYSIS
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load frozen J004 analysis")
_j004 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_j004)


def median(values: list[float]) -> float:
    if not values:
        raise ValueError("median requires data")
    return float(statistics.median(values))


def summarize_control_process(rows: list[dict[str, object]]) -> dict[str, object]:
    return _j004.summarize_process(rows)


def _synthetic_process(
    rows: list[dict[str, object]],
    factor: float,
) -> dict[str, object]:
    measured = [row for row in rows if str(row["phase"]) == "measured"]
    if not measured:
        raise ValueError("process has no measured rows")

    pairs: dict[int, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in measured:
        pair_index = int(row["pair_index"])
        role = str(row["role"])
        if role not in {"A", "B"} or role in pairs[pair_index]:
            raise ValueError("invalid or duplicate pair role")
        pairs[pair_index][role] = row

    logs: list[float] = []
    by_order: dict[str, list[float]] = {"AB": [], "BA": []}
    positive = 0
    for pair_index in sorted(pairs):
        pair = pairs[pair_index]
        if set(pair) != {"A", "B"}:
            raise ValueError(f"incomplete pair {pair_index}")
        a = float(pair["A"]["gpu_us"])
        b = float(pair["B"]["gpu_us"]) * factor
        if not math.isfinite(a) or not math.isfinite(b) or a <= 0.0 or b <= 0.0:
            raise ValueError("timings must be positive finite values")
        order_a = str(pair["A"]["order"])
        order_b = str(pair["B"]["order"])
        if order_a != order_b or order_a not in by_order:
            raise ValueError("pair order metadata mismatch")
        value = math.log(b / a)
        logs.append(value)
        by_order[order_a].append(value)
        if value > 0.0:
            positive += 1

    if not by_order["AB"] or not by_order["BA"]:
        raise ValueError("process must contain both AB and BA measured pairs")

    med = median(logs)
    ab_med = median(by_order["AB"])
    ba_med = median(by_order["BA"])
    first = measured[0]
    return {
        "environment": first["environment"],
        "profile": first["profile"],
        "track": first["track"],
        "block": int(first["block"]),
        "process_id": first["process_id"],
        "factor": factor,
        "pair_count": len(logs),
        "median_log_ratio": med,
        "median_ratio": math.exp(med),
        "ab_median_log_ratio": ab_med,
        "ab_median_ratio": math.exp(ab_med),
        "ba_median_log_ratio": ba_med,
        "ba_median_ratio": math.exp(ba_med),
        "order_bias_ratio": math.exp(abs(ab_med - ba_med)),
        "positive_pair_fraction": positive / len(logs),
    }


def _control_envelope(
    process_rows: list[dict[str, object]],
) -> dict[str, object]:
    criteria = {
        "control_max_abs_process_median_ratio": float("inf"),
        "control_process_median_span_ratio": float("inf"),
        "control_max_within_process_order_bias_ratio": float("inf"),
    }
    control = _j004.evaluate_control(process_rows, "gpu", criteria)
    envelope = max(
        float(control["max_abs_process_median_ratio"]),
        float(control["process_median_span_ratio"]),
        float(control["max_within_process_order_bias_ratio"]),
    )
    return {
        **control,
        "combined_noise_envelope_ratio": envelope,
    }


def _effect_result(
    synthetic_process_rows: list[dict[str, object]],
    factor: float,
    control: dict[str, object],
    config: dict[str, object],
) -> dict[str, object]:
    expected = int(config["detection_gate"]["process_count_per_control"])
    if len(synthetic_process_rows) != expected:
        raise ValueError(
            f"expected {expected} synthetic processes, got {len(synthetic_process_rows)}"
        )

    min_positive = min(
        float(row["positive_pair_fraction"]) for row in synthetic_process_rows
    )
    min_process = min(float(row["median_ratio"]) for row in synthetic_process_rows)
    min_ab = min(float(row["ab_median_ratio"]) for row in synthetic_process_rows)
    min_ba = min(float(row["ba_median_ratio"]) for row in synthetic_process_rows)
    envelope = float(control["combined_noise_envelope_ratio"])

    factor_beyond_noise = factor > envelope
    all_process_positive = min_process > 1.0
    all_ab_positive = min_ab > 1.0
    all_ba_positive = min_ba > 1.0
    positive_fraction_pass = min_positive >= float(
        config["detection_gate"]["minimum_positive_pair_fraction"]
    )
    passed = (
        factor_beyond_noise
        and all_process_positive
        and all_ab_positive
        and all_ba_positive
        and positive_fraction_pass
    )

    return {
        "passed": passed,
        "factor": factor,
        "control_noise_envelope_ratio": envelope,
        "factor_beyond_control_noise": factor_beyond_noise,
        "minimum_process_median_ratio": min_process,
        "all_process_medians_above_unity": all_process_positive,
        "minimum_ab_stratum_median_ratio": min_ab,
        "all_ab_stratum_medians_above_unity": all_ab_positive,
        "minimum_ba_stratum_median_ratio": min_ba,
        "all_ba_stratum_medians_above_unity": all_ba_positive,
        "minimum_positive_pair_fraction": min_positive,
        "positive_pair_fraction_pass": positive_fraction_pass,
    }


def summarize_l002(
    raw_rows: list[dict[str, object]],
    config: dict[str, object],
) -> dict[str, object]:
    by_process: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in raw_rows:
        by_process[str(row["process_id"])].append(row)

    grouped_processes: dict[
        tuple[str, str, str],
        list[tuple[dict[str, object], list[dict[str, object]]]],
    ] = defaultdict(list)
    for rows in by_process.values():
        control_process = summarize_control_process(rows)
        first = rows[0]
        key = (
            str(first["environment"]),
            str(first["profile"]),
            str(first["track"]),
        )
        grouped_processes[key].append((control_process, rows))

    environments = [str(item["id"]) for item in config["environments"]]
    profiles = [str(item["name"]) for item in config["j002"]["profiles"]]
    tracks = list(config["controls"].keys())
    factors = list(config["synthetic_effect_calibration"]["factors"])
    expected_processes = int(config["timing"]["fresh_process_blocks"])

    environment_results: dict[str, object] = {}
    synthetic_flat: list[dict[str, object]] = []

    for environment in environments:
        controls: dict[str, object] = {}
        effect_environment_pass = {str(item["id"]): True for item in factors}
        for profile in profiles:
            controls[profile] = {}
            for track in tracks:
                entries = grouped_processes[(environment, profile, track)]
                if len(entries) != expected_processes:
                    raise ValueError(
                        f"{environment}/{profile}/{track}: expected "
                        f"{expected_processes} processes, got {len(entries)}"
                    )
                control_process_rows = [entry[0] for entry in entries]
                control = _control_envelope(control_process_rows)
                effects: dict[str, object] = {}
                for factor_spec in factors:
                    effect_id = str(factor_spec["id"])
                    factor = float(factor_spec["factor"])
                    synthetic = [
                        _synthetic_process(rows, factor) for _, rows in entries
                    ]
                    effect = _effect_result(synthetic, factor, control, config)
                    effects[effect_id] = effect
                    effect_environment_pass[effect_id] = (
                        effect_environment_pass[effect_id] and bool(effect["passed"])
                    )
                    for row in synthetic:
                        synthetic_flat.append(
                            {
                                **row,
                                "effect_id": effect_id,
                                "effect_percent": int(factor_spec["percent"]),
                                "control_noise_envelope_ratio":
                                    control["combined_noise_envelope_ratio"],
                                "effect_pass": effect["passed"],
                            }
                        )
                controls[profile][track] = {
                    "control": control,
                    "effects": effects,
                }

        contiguous = True
        floor_percent = None
        effect_summary: dict[str, object] = {}
        for factor_spec in factors:
            effect_id = str(factor_spec["id"])
            passed_all_controls = bool(effect_environment_pass[effect_id])
            contiguous = contiguous and passed_all_controls
            accepted_contiguously = contiguous
            if accepted_contiguously:
                floor_percent = int(factor_spec["percent"])
            effect_summary[effect_id] = {
                "percent": int(factor_spec["percent"]),
                "factor": float(factor_spec["factor"]),
                "all_required_controls_pass": passed_all_controls,
                "accepted_contiguously": accepted_contiguously,
            }

        environment_results[environment] = {
            "floor_percent": floor_percent,
            "has_accepted_floor": floor_percent is not None,
            "effects": effect_summary,
            "controls": controls,
        }

    usable = [
        {
            "environment": env,
            "floor_percent": int(result["floor_percent"]),
        }
        for env, result in environment_results.items()
        if result["floor_percent"] is not None
    ]

    if not usable:
        outcome = "target-timing-unsuitable-up-to-20-percent"
        accepted_environment = None
        accepted_floor = None
    else:
        minimum_floor = min(item["floor_percent"] for item in usable)
        tied = [
            item["environment"]
            for item in usable
            if item["floor_percent"] == minimum_floor
        ]
        preferred = "single-context-independent-runtime"
        accepted_environment = (
            preferred if preferred in tied else sorted(tied)[0]
        )
        accepted_floor = minimum_floor
        outcome = "measurement-floor-established"

    return {
        "architecture_ranking_performed": False,
        "synthetic_injection_is_analysis_only": True,
        "outcome": outcome,
        "accepted_environment": accepted_environment,
        "accepted_floor_percent": accepted_floor,
        "usable_environments": usable,
        "environment_results": environment_results,
        "synthetic_process_rows": synthetic_flat,
    }

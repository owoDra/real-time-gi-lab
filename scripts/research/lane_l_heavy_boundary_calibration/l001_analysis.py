from __future__ import annotations

import importlib.util
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
J004_ANALYSIS = (
    ROOT
    / "scripts/research/lane_j_topology_backend_alternatives/j004_analysis.py"
)

_spec = importlib.util.spec_from_file_location("lane_j_j004_analysis_for_l001", J004_ANALYSIS)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load frozen J004 analysis")
_j004 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_j004)


def summarize_process(rows: list[dict[str, object]]) -> dict[str, object]:
    return _j004.summarize_process(rows)


def summarize_l001(
    process_rows: list[dict[str, object]],
    config: dict[str, object],
) -> dict[str, object]:
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in process_rows:
        key = (
            str(row["environment"]),
            str(row["profile"]),
            str(row["track"]),
        )
        grouped[key].append(row)

    criteria = config["gpu_control_health"]
    expected_processes = int(config["timing"]["fresh_process_blocks"])
    profiles = [str(item["name"]) for item in config["j002"]["profiles"]]
    tracks = tuple(config["controls"].keys())
    environments = [str(item["id"]) for item in config["environments"]]

    environment_results: dict[str, object] = {}
    for environment in environments:
        controls: dict[str, object] = {}
        environment_passed = True
        for profile in profiles:
            controls[profile] = {}
            for track in tracks:
                rows = grouped[(environment, profile, track)]
                if len(rows) != expected_processes:
                    raise ValueError(
                        f"{environment}/{profile}/{track}: expected "
                        f"{expected_processes} processes, got {len(rows)}"
                    )
                gpu = _j004.evaluate_control(rows, "gpu", criteria)
                wall = _j004.evaluate_control(rows, "wall", criteria)
                controls[profile][track] = {
                    "gpu_primary": gpu,
                    "cpu_wall": {
                        "decision_use": "diagnostic-health-provenance-only",
                        "control": wall,
                    },
                }
                environment_passed = environment_passed and bool(gpu["passed"])
        environment_results[environment] = {
            "passed": environment_passed,
            "required_control_count": len(profiles) * len(tracks),
            "controls": controls,
        }

    dual = bool(environment_results["dual-context"]["passed"])
    single = bool(
        environment_results["single-context-independent-runtime"]["passed"]
    )
    if single and not dual:
        outcome = "usable-environment-established"
        accepted = ["single-context-independent-runtime"]
        l002_required = False
    elif dual and not single:
        outcome = "usable-environment-established"
        accepted = ["dual-context"]
        l002_required = False
    elif dual and single:
        outcome = "multiple-usable-environments"
        accepted = [
            "dual-context",
            "single-context-independent-runtime",
        ]
        l002_required = False
    else:
        outcome = "measurement-limited"
        accepted = []
        l002_required = True

    return {
        "architecture_ranking_performed": False,
        "outcome": outcome,
        "usable_environments": accepted,
        "l002_required": l002_required,
        "environment_results": environment_results,
    }

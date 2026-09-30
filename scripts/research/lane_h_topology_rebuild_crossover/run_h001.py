#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-h-topology-rebuild-crossover"
CONFIG = (
    ROOT / "research/lanes/lane-h-topology-rebuild-crossover/experiments"
    / "001-safe-timing-methodology-config.json"
)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def percentile(values: Iterable[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires at least one sample")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be in [0, 1]")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def ratio_high_low(a: float, b: float) -> float:
    if a <= 0.0 or b <= 0.0:
        raise ValueError("timing samples must be positive")
    return max(a, b) / min(a, b)


def robust(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("robust requires samples")
    median = statistics.median(values)
    if median <= 0.0:
        raise ValueError("median must be positive")
    mad = statistics.median(abs(value - median) for value in values)
    return {
        "min": min(values),
        "median": median,
        "max": max(values),
        "max_min_ratio": max(values) / min(values),
        "mad": mad,
        "mad_over_median": mad / median,
    }


def summarize_process(values: list[float]) -> dict[str, float]:
    if len(values) < 8:
        raise ValueError("H001 requires enough measured frames for drift checks")
    p10 = percentile(values, 0.10)
    p90 = percentile(values, 0.90)
    first = statistics.median(values[:4])
    last = statistics.median(values[-4:])
    return {
        "median": statistics.median(values),
        "p10": p10,
        "p90": p90,
        "p90_p10_ratio": p90 / p10,
        "first4_median": first,
        "last4_median": last,
        "first_last_median_ratio": ratio_high_low(first, last),
    }


def evaluate_axis(
    process_rows: list[dict[str, object]],
    prefix: str,
    criteria: dict[str, float],
) -> dict[str, object]:
    medians = [float(row[f"{prefix}_median"]) for row in process_rows]
    fresh = robust(medians)

    slots: dict[int, list[float]] = {}
    for row in process_rows:
        slots.setdefault(int(row["slot"]), []).append(float(row[f"{prefix}_median"]))
    if sorted(slots) != [0, 1, 2, 3]:
        raise RuntimeError("counterbalanced slot coverage is incomplete")
    slot_medians = {str(slot): statistics.median(values) for slot, values in slots.items()}
    slot_ratio = max(slot_medians.values()) / min(slot_medians.values())

    within_ratios = [float(row[f"{prefix}_p90_p10_ratio"]) for row in process_rows]
    drift_ratios = [
        float(row[f"{prefix}_first_last_median_ratio"]) for row in process_rows
    ]

    passed = (
        max(within_ratios) <= criteria["within_process_p90_p10_max"]
        and max(drift_ratios) <= criteria["first_last_median_ratio_max"]
        and fresh["max_min_ratio"] <= criteria["fresh_process_median_max_min_max"]
        and fresh["mad_over_median"]
        <= criteria["fresh_process_mad_over_median_max"]
        and slot_ratio <= criteria["slot_position_median_max_min_max"]
    )
    return {
        "fresh_process": fresh,
        "worst_within_process_p90_p10_ratio": max(within_ratios),
        "worst_first_last_median_ratio": max(drift_ratios),
        "slot_position_medians": slot_medians,
        "slot_position_median_max_min_ratio": slot_ratio,
        "passed": passed,
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_mem_available() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def host_snapshot() -> dict[str, object]:
    try:
        load = os.getloadavg()
    except OSError:
        load = (None, None, None)
    return {
        "loadavg_1m": load[0],
        "loadavg_5m": load[1],
        "loadavg_15m": load[2],
        "mem_available_bytes": read_mem_available(),
        "monotonic_ns": time.monotonic_ns(),
    }


def run_process(
    executable: Path,
    scene: Path,
    root: Path,
    case: dict[str, str],
    block: int,
    slot: int,
    symbol: str,
    variant: str,
    warmup_frames: int,
    measured_frames: int,
    settle_seconds: float,
    validation: bool,
    expected_gpu: str,
) -> tuple[list[dict[str, object]], dict[str, object], dict[str, object]]:
    if settle_seconds > 0.0:
        time.sleep(settle_seconds)

    case_dir = (
        root / case["id"] / f"block-{block:02d}"
        / f"slot-{slot}-{symbol}-{variant}"
    )
    case_dir.mkdir(parents=True, exist_ok=False)

    command = [
        "bash", str(ROOT / "scripts/run_with_vulkan.sh"), str(executable),
        "--scene", str(scene),
        "--variant", variant,
        "--scenario", case["scenario"],
        "--geometry-class", case["geometry_class"],
        "--warmup-frames", str(warmup_frames),
        "--measured-frames", str(measured_frames),
    ]
    if validation:
        command.append("--validation")

    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(case_dir)
    before = host_snapshot()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    after = host_snapshot()
    (case_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (case_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"H001 {case['id']} block={block} slot={slot} variant={variant} failed"
        )

    device = json.loads((case_dir / "h001-device.json").read_text(encoding="utf-8"))
    if device.get("device") != expected_gpu:
        raise RuntimeError(f"wrong GPU: {device.get('device')!r}")

    raw_rows: list[dict[str, object]] = []
    for row in read_csv(case_dir / "h001-frames.csv"):
        enriched: dict[str, object] = dict(row)
        enriched.update({
            "case_id": case["id"],
            "block": block,
            "slot": slot,
            "symbol": symbol,
        })
        raw_rows.append(enriched)

    observation = {
        "case_id": case["id"],
        "block": block,
        "slot": slot,
        "symbol": symbol,
        "variant": variant,
        "before": before,
        "after": after,
    }
    return raw_rows, observation, device


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=ROOT / os.environ.get("PHOS_GI_BUILD_DIR", "build/release"),
    )
    parser.add_argument(
        "--scene",
        type=Path,
        default=ROOT / "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf",
    )
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument(
        "--validation",
        action="store_true",
        help="diagnostic only; accepted H001 timing is frozen with validation disabled",
    )
    args = parser.parse_args()

    if git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError(f"H001 must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("H001 requires a clean worktree")

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if args.validation and not cfg["validation_for_accepted_timing"]:
        print("H001 diagnostic validation run: not accepted timing evidence", file=sys.stderr)

    executable = args.build_dir / "phos-lane-h-h001"
    if not executable.is_file():
        raise RuntimeError(f"missing executable: {executable}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    root = args.artifact_dir or (Path(env_root) if env_root else None)
    if root is None:
        root = (
            ROOT / "out/research/lane-h-topology-rebuild-crossover"
            / "001-safe-timing-methodology" / stamp
        )
    # The shared research recorder pre-creates PHOS_RESEARCH_ARTIFACT_DIR.
    # Direct runs still require a fresh root to prevent accidental evidence mixing.
    if env_root:
        root.mkdir(parents=True, exist_ok=True)
    else:
        root.mkdir(parents=True, exist_ok=False)

    all_raw: list[dict[str, object]] = []
    observations: list[dict[str, object]] = []
    devices: list[dict[str, object]] = []

    for case in cfg["cases"]:
        for block, order in enumerate(cfg["block_orders"]):
            for slot, symbol in enumerate(order):
                variant = cfg["variants"][symbol]
                raw, observation, device = run_process(
                    executable=executable,
                    scene=args.scene,
                    root=root,
                    case=case,
                    block=block,
                    slot=slot,
                    symbol=symbol,
                    variant=variant,
                    warmup_frames=int(cfg["warmup_frames"]),
                    measured_frames=int(cfg["measured_frames"]),
                    settle_seconds=float(cfg["settle_seconds"]),
                    validation=args.validation,
                    expected_gpu=cfg["target_gpu"],
                )
                all_raw.extend(raw)
                observations.append(observation)
                devices.append(device)

    process_rows: list[dict[str, object]] = []
    for case in cfg["cases"]:
        for symbol, variant in cfg["variants"].items():
            matching = [
                row for row in all_raw
                if row["case_id"] == case["id"]
                and row["symbol"] == symbol
                and row["phase"] == "measured"
            ]
            by_process: dict[tuple[int, int], list[dict[str, object]]] = {}
            for row in matching:
                by_process.setdefault((int(row["block"]), int(row["slot"])), []).append(row)
            if len(by_process) != int(cfg["process_blocks"]):
                raise RuntimeError(
                    f"{case['id']} {variant}: expected {cfg['process_blocks']} process repeats"
                )
            for (block, slot), rows in sorted(by_process.items()):
                rows.sort(key=lambda row: int(row["frame_index"]))
                gpu = [float(row["complete_gpu_us"]) for row in rows]
                wall = [float(row["complete_frame_wall_us"]) for row in rows]
                if len(gpu) != int(cfg["measured_frames"]):
                    raise RuntimeError("measured frame count mismatch")
                gpu_summary = summarize_process(gpu)
                wall_summary = summarize_process(wall)
                process_rows.append({
                    "case_id": case["id"],
                    "scenario": case["scenario"],
                    "geometry_class": case["geometry_class"],
                    "symbol": symbol,
                    "variant": variant,
                    "block": block,
                    "slot": slot,
                    **{f"gpu_{key}": value for key, value in gpu_summary.items()},
                    **{f"wall_{key}": value for key, value in wall_summary.items()},
                })

    row_summaries: list[dict[str, object]] = []
    campaign_pass = True
    for case in cfg["cases"]:
        for symbol, variant in cfg["variants"].items():
            rows = [
                row for row in process_rows
                if row["case_id"] == case["id"] and row["symbol"] == symbol
            ]
            gpu = evaluate_axis(rows, "gpu", cfg["repeatability_criteria"]["gpu"])
            wall = evaluate_axis(rows, "wall", cfg["repeatability_criteria"]["wall"])
            passed = bool(gpu["passed"] and wall["passed"])
            campaign_pass = campaign_pass and passed
            row_summaries.append({
                "case_id": case["id"],
                "scenario": case["scenario"],
                "geometry_class": case["geometry_class"],
                "symbol": symbol,
                "variant": variant,
                "gpu": gpu,
                "wall": wall,
                "repeatability_passed": passed,
            })

    write_csv(root / "h001-raw.csv", all_raw)
    write_csv(root / "h001-process-summary.csv", process_rows)
    (root / "h001-host-observations.json").write_text(
        json.dumps(observations, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "h001-config.json").write_text(
        json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {
        "schema_version": 1,
        "plan_version": cfg["plan_version"],
        "git_commit": git("rev-parse", "HEAD"),
        "target_gpu": cfg["target_gpu"],
        "validation": args.validation,
        "all_samples_retained": True,
        "instability_rerun_budget": cfg["instability_rerun_budget"],
        "row_summaries": row_summaries,
        "repeatability_passed": campaign_pass and not args.validation,
        "decision": (
            "PASS" if campaign_pass and not args.validation else
            "DIAGNOSTIC_ONLY" if args.validation else "INCONCLUSIVE"
        ),
        "h003_allowed": campaign_pass and not args.validation,
    }
    (root / "h001-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "h001-run-metadata.json").write_text(
        json.dumps({
            "git_commit": summary["git_commit"],
            "branch": EXPECTED_BRANCH,
            "artifact_root": str(root.relative_to(ROOT)) if root.is_relative_to(ROOT) else str(root),
            "command": " ".join(sys.argv),
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"H001 artifacts: {root}")
    print(f"H001 decision: {summary['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

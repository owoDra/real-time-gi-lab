#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[3]
LANE = "lane-g-transient-lbvh-hardening"
EXPERIMENT = "002-timing-repeatability-diagnosis"
EXPECTED_BRANCH = "research-lane-g-transient-lbvh-hardening"
EXPECTED_GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
CONFIG_PATH = (
    ROOT / "research/lanes/lane-g-transient-lbvh-hardening/experiments"
    / "002-timing-repeatability-diagnosis-config.json"
)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def read_first(pattern: str) -> tuple[str | None, str | None]:
    matches = sorted(glob.glob(pattern))
    for path in matches:
        value = read_text(path)
        if value:
            return path, value
    return None, None


def system_snapshot() -> dict[str, object]:
    snapshot: dict[str, object] = {
        "monotonic_ns": time.monotonic_ns(),
        "loadavg": list(os.getloadavg()),
    }
    probes = {
        "gpu_temp_millic": "/sys/class/drm/card*/device/hwmon/hwmon*/temp1_input",
        "gpu_power_microw": "/sys/class/drm/card*/device/hwmon/hwmon*/power1_average",
        "gpu_busy_percent": "/sys/class/drm/card*/device/gpu_busy_percent",
        "gpu_sclk": "/sys/class/drm/card*/device/pp_dpm_sclk",
        "gpu_mclk": "/sys/class/drm/card*/device/pp_dpm_mclk",
        "gpu_perf_level": "/sys/class/drm/card*/device/power_dpm_force_performance_level",
    }
    for key, pattern in probes.items():
        path, value = read_first(pattern)
        snapshot[key] = value
        snapshot[f"{key}_path"] = path
    cpu_freqs: list[int] = []
    for path in sorted(glob.glob(
        "/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq"
    )):
        value = read_text(path)
        if value and value.isdigit():
            cpu_freqs.append(int(value))
    if cpu_freqs:
        snapshot["cpu_freq_khz_min"] = min(cpu_freqs)
        snapshot["cpu_freq_khz_median"] = statistics.median(cpu_freqs)
        snapshot["cpu_freq_khz_max"] = max(cpu_freqs)
    return snapshot


def robust_stats(values: Iterable[float]) -> dict[str, float | int | None]:
    xs = list(values)
    if not xs:
        return {
            "count": 0, "min": None, "median": None, "max": None,
            "max_min_ratio": None, "mad": None, "mad_over_median": None,
            "cv": None,
        }
    median = statistics.median(xs)
    mad = statistics.median(abs(value - median) for value in xs)
    mean = statistics.fmean(xs)
    std = statistics.stdev(xs) if len(xs) >= 2 else 0.0
    return {
        "count": len(xs),
        "min": min(xs),
        "median": median,
        "max": max(xs),
        "max_min_ratio": max(xs) / min(xs) if min(xs) > 0.0 else None,
        "mad": mad,
        "mad_over_median": mad / median if median > 0.0 else None,
        "cv": std / mean if mean > 0.0 else None,
    }


def planned_cases(
    variants: list[str],
    scenarios: list[str],
    order: str,
) -> list[tuple[str, str]]:
    cases = [(variant, scenario) for variant in variants for scenario in scenarios]
    if order == "reverse":
        cases.reverse()
    elif order != "canonical":
        raise ValueError(f"unknown order: {order}")
    return cases


def run_process(
    executable: Path,
    scene: Path,
    root: Path,
    *,
    phase: str,
    variant: str,
    scenario: str,
    warmup_frames: int,
    measured_frames: int,
    process_index: int,
    campaign: int = 0,
    order: str = "isolated",
    sequence_index: int = 0,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    case_dir = (
        root / phase / order / f"campaign-{campaign:02d}"
        / f"{sequence_index:03d}-{variant}-{scenario}-p{process_index:02d}"
    )
    case_dir.mkdir(parents=True, exist_ok=False)
    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--scene", str(scene),
        "--variant", variant,
        "--scenario", scenario,
        "--warmup-frames", str(warmup_frames),
        "--measured-frames", str(measured_frames),
    ]
    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(case_dir)

    before = system_snapshot()
    proc = subprocess.run(
        command, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    after = system_snapshot()
    (case_dir / "process.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (case_dir / "process.stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"G002 {phase} {variant}/{scenario} process {process_index} "
            f"failed with {proc.returncode}"
        )

    device = json.loads(
        (case_dir / "g002-device.json").read_text(encoding="utf-8")
    )
    if device.get("device") != EXPECTED_GPU:
        raise RuntimeError(
            f"G002 target GPU mismatch: {device.get('device')!r}"
        )
    rows = read_csv(case_dir / "g002-frames.csv")
    if len(rows) != measured_frames:
        raise RuntimeError(
            f"G002 measured frame count mismatch: {len(rows)} != {measured_frames}"
        )

    enriched: list[dict[str, object]] = []
    for row in rows:
        item: dict[str, object] = dict(row)
        item.update({
            "phase": phase,
            "process_index": process_index,
            "campaign": campaign,
            "order": order,
            "sequence_index": sequence_index,
        })
        enriched.append(item)

    telemetry = {
        "phase": phase,
        "variant": variant,
        "scenario": scenario,
        "warmup_frames": warmup_frames,
        "measured_frames": measured_frames,
        "process_index": process_index,
        "campaign": campaign,
        "order": order,
        "sequence_index": sequence_index,
        "before": before,
        "after": after,
        "returncode": proc.returncode,
    }
    return enriched, telemetry


def summarize_groups(
    rows: list[dict[str, object]],
    keys: list[str],
) -> list[dict[str, object]]:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in rows:
        key = tuple(row[k] for k in keys)
        grouped.setdefault(key, []).append(row)
    result: list[dict[str, object]] = []
    for key, group in sorted(grouped.items(), key=lambda item: str(item[0])):
        summary: dict[str, object] = dict(zip(keys, key))
        gpu = [float(row["complete_gpu_us"]) for row in group]
        wall = [float(row["complete_frame_wall_us"]) for row in group]
        summary["complete_gpu_us"] = robust_stats(gpu)
        summary["complete_frame_wall_us"] = robust_stats(wall)
        for field in (
            "producer_us", "traversal_maintenance_gpu_us", "dynamic_builder_us",
            "static_traversal_us", "dynamic_traversal_us", "traversal_us",
            "radiance_us", "storage_update_us", "resolve_us",
        ):
            summary[field] = robust_stats(float(row[field]) for row in group)
        result.append(summary)
    return result


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
    parser.add_argument(
        "--phase",
        choices=("same-process", "fresh-process", "warmup-sweep", "full-matrix-order", "all"),
        default="all",
    )
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()

    branch = git("branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"G002 must run on {EXPECTED_BRANCH}, got {branch}")
    if git("status", "--porcelain"):
        raise RuntimeError("G002 requires a clean worktree")
    commit = git("rev-parse", "HEAD")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    executable = args.build_dir / "phos-lane-g-g002"
    if not executable.is_file():
        raise RuntimeError(f"missing G002 executable: {executable}")
    if not args.scene.is_file():
        raise RuntimeError(f"missing scene: {args.scene}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = args.artifact_dir or ROOT / "out/research" / LANE / EXPERIMENT / stamp
    root.mkdir(parents=True, exist_ok=False)

    variants = list(config["variants"])
    anchors = list(config["anchor_scenarios"])
    full_scenarios = list(config["full_scenarios"])
    selected_phases = (
        ["same-process", "fresh-process", "warmup-sweep", "full-matrix-order"]
        if args.phase == "all" else [args.phase]
    )

    all_rows: list[dict[str, object]] = []
    telemetry: list[dict[str, object]] = []

    if "same-process" in selected_phases:
        phase_cfg = config["phases"]["same-process"]
        for sequence, (variant, scenario) in enumerate(
            planned_cases(variants, anchors, "canonical")
        ):
            rows, state = run_process(
                executable, args.scene, root,
                phase="same-process", variant=variant, scenario=scenario,
                warmup_frames=int(phase_cfg["warmup_frames"]),
                measured_frames=int(phase_cfg["measured_frames"]),
                process_index=0, sequence_index=sequence,
            )
            all_rows.extend(rows)
            telemetry.append(state)

    if "fresh-process" in selected_phases:
        phase_cfg = config["phases"]["fresh-process"]
        repeats = int(phase_cfg["process_repeats"])
        for sequence, (variant, scenario) in enumerate(
            planned_cases(variants, anchors, "canonical")
        ):
            for repeat in range(repeats):
                rows, state = run_process(
                    executable, args.scene, root,
                    phase="fresh-process", variant=variant, scenario=scenario,
                    warmup_frames=int(phase_cfg["warmup_frames"]),
                    measured_frames=1,
                    process_index=repeat, sequence_index=sequence,
                )
                all_rows.extend(rows)
                telemetry.append(state)

    if "warmup-sweep" in selected_phases:
        phase_cfg = config["phases"]["warmup-sweep"]
        repeats = int(phase_cfg["process_repeats"])
        sequence = 0
        for warmup in phase_cfg["warmup_frames"]:
            for variant, scenario in planned_cases(variants, anchors, "canonical"):
                for repeat in range(repeats):
                    rows, state = run_process(
                        executable, args.scene, root,
                        phase="warmup-sweep", variant=variant, scenario=scenario,
                        warmup_frames=int(warmup), measured_frames=1,
                        process_index=repeat, sequence_index=sequence,
                        order=f"warmup-{warmup}",
                    )
                    all_rows.extend(rows)
                    telemetry.append(state)
                sequence += 1

    if "full-matrix-order" in selected_phases:
        phase_cfg = config["phases"]["full-matrix-order"]
        campaigns = int(phase_cfg["campaign_repeats"])
        for order in phase_cfg["orders"]:
            cases = planned_cases(variants, full_scenarios, order)
            for campaign in range(campaigns):
                for sequence, (variant, scenario) in enumerate(cases):
                    rows, state = run_process(
                        executable, args.scene, root,
                        phase="full-matrix-order", variant=variant, scenario=scenario,
                        warmup_frames=int(phase_cfg["warmup_frames"]),
                        measured_frames=1, process_index=0, campaign=campaign,
                        order=order, sequence_index=sequence,
                    )
                    all_rows.extend(rows)
                    telemetry.append(state)

    write_csv(root / "g002-raw.csv", all_rows)
    with (root / "g002-system-telemetry.jsonl").open("w", encoding="utf-8") as handle:
        for item in telemetry:
            handle.write(json.dumps(item, sort_keys=True) + "\n")

    summaries: dict[str, object] = {}
    phase_rows = lambda name: [row for row in all_rows if row["phase"] == name]

    if "same-process" in selected_phases:
        summaries["same-process"] = summarize_groups(
            phase_rows("same-process"),
            ["variant", "scenario", "frame_kind"],
        )
    if "fresh-process" in selected_phases:
        summaries["fresh-process"] = summarize_groups(
            phase_rows("fresh-process"),
            ["variant", "scenario", "frame_kind"],
        )
    if "warmup-sweep" in selected_phases:
        summaries["warmup-sweep"] = summarize_groups(
            phase_rows("warmup-sweep"),
            ["variant", "scenario", "warmup_frames", "frame_kind"],
        )
    if "full-matrix-order" in selected_phases:
        summaries["full-matrix-order"] = summarize_groups(
            phase_rows("full-matrix-order"),
            ["variant", "scenario", "order", "frame_kind"],
        )

    flags = config["diagnostic_flags"]
    warning = float(flags["max_min_warning_ratio"])
    protocol_ratio = float(flags["candidate_protocol_max_min_ratio"])
    protocol_mad = float(flags["candidate_protocol_mad_over_median"])
    order_ratio = float(flags["order_sensitivity_ratio"])

    diagnosis: dict[str, object] = {
        "f007_warning_ratio": warning,
        "candidate_protocol_max_min_ratio": protocol_ratio,
        "candidate_protocol_mad_over_median": protocol_mad,
        "outlier_deletion": False,
    }

    fresh_unstable: list[str] = []
    if "fresh-process" in summaries:
        for group in summaries["fresh-process"]:
            stats = group["complete_gpu_us"]
            ratio = stats["max_min_ratio"]
            if ratio is not None and ratio > warning:
                fresh_unstable.append(f"{group['variant']}/{group['scenario']}")
    diagnosis["fresh_process_f007_unstable_groups"] = fresh_unstable
    diagnosis["controls_unstable_too"] = any(
        not value.startswith("transient-lbvh/") for value in fresh_unstable
    )

    protocol_warmups: list[int] = []
    if "warmup-sweep" in summaries:
        by_warmup: dict[int, list[dict[str, object]]] = {}
        for group in summaries["warmup-sweep"]:
            by_warmup.setdefault(int(group["warmup_frames"]), []).append(group)
        for warmup, groups in sorted(by_warmup.items()):
            acceptable = True
            for group in groups:
                stats = group["complete_gpu_us"]
                ratio = stats["max_min_ratio"]
                mad = stats["mad_over_median"]
                if (
                    ratio is None or mad is None
                    or ratio > protocol_ratio
                    or mad > protocol_mad
                ):
                    acceptable = False
                    break
            if acceptable:
                protocol_warmups.append(warmup)
    diagnosis["warmups_meeting_anchor_repeatability_criteria"] = protocol_warmups
    diagnosis["smallest_candidate_warmup"] = (
        min(protocol_warmups) if protocol_warmups else None
    )

    order_sensitive: list[dict[str, object]] = []
    if "full-matrix-order" in summaries:
        values: dict[tuple[str, str, str], float] = {}
        for group in summaries["full-matrix-order"]:
            values[(group["variant"], group["scenario"], group["order"])] = float(
                group["complete_gpu_us"]["median"]
            )
        for variant in variants:
            for scenario in full_scenarios:
                a = values.get((variant, scenario, "canonical"))
                b = values.get((variant, scenario, "reverse"))
                if a and b:
                    ratio = max(a, b) / min(a, b)
                    if ratio > order_ratio:
                        order_sensitive.append({
                            "variant": variant,
                            "scenario": scenario,
                            "canonical_median_us": a,
                            "reverse_median_us": b,
                            "ratio": ratio,
                        })
    diagnosis["order_sensitive_groups"] = order_sensitive

    diagnosis["freeze_ready"] = (
        "warmup-sweep" in summaries
        and "full-matrix-order" in summaries
        and bool(protocol_warmups)
        and not order_sensitive
    )
    diagnosis["freeze_note"] = (
        "A protocol may be frozen only after reviewing telemetry and same/fresh "
        "process evidence; freeze_ready is a mechanical precondition, not an "
        "automatic architecture decision."
    )

    write_json(root / "g002-summary.json", {
        "schema_version": 1,
        "plan_version": "lane-g-g002-v1",
        "git_commit": commit,
        "branch": branch,
        "target_gpu": EXPECTED_GPU,
        "phases": selected_phases,
        "summaries": summaries,
        "diagnosis": diagnosis,
    })
    write_json(root / "g002-config.json", config)
    write_json(root / "metadata.json", {
        "git_commit": commit,
        "branch": branch,
        "artifact_root": str(root.relative_to(ROOT)),
        "command": " ".join(sys.argv),
    })
    print(f"G002 artifacts: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

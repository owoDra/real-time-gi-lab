#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import analysis

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-k-gpu-primary-calibration"
CONFIG = (
    ROOT / "research/lanes/lane-k-gpu-primary-calibration/experiments"
    / "002-gpu-primary-protocol-config.json"
)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def host_snapshot() -> dict[str, object]:
    try:
        load = list(os.getloadavg())
    except OSError:
        load = [None, None, None]
    available = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                available = int(line.split()[1]) * 1024
                break
    except (OSError, ValueError, IndexError):
        pass
    return {
        "loadavg_1m": load[0],
        "loadavg_5m": load[1],
        "loadavg_15m": load[2],
        "mem_available_bytes": available,
        "monotonic_ns": time.monotonic_ns(),
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


def flatten_process(row: dict[str, object]) -> dict[str, object]:
    out = {
        "comparison": row["comparison"],
        "candidate": row["candidate"],
        "block": row["block"],
        "slot": row["slot"],
        "process_id": row["process_id"],
    }
    for axis in ("gpu", "wall"):
        for key, value in row[axis].items():
            out[f"{axis}_{key}"] = value
    return out


def expected_units(
    config: dict[str, object], variant: str, batch_dispatches: int
) -> int:
    workload = config["workload"]
    return (
        int(workload["elements"])
        * int(workload["variant_iterations"][variant])
        * batch_dispatches
    )


def run_process(
    executable: Path,
    root: Path,
    config: dict[str, object],
    suite: str,
    comparison: str,
    candidate: str,
    block: int,
    slot: int,
    batch_dispatches: int,
    warmup_pairs: int,
    measured_pairs: int,
) -> tuple[list[dict[str, object]], dict[str, object], dict[str, object]]:
    time.sleep(float(config["settle_seconds"]))
    start_order = "AB" if (block + slot) % 2 == 0 else "BA"
    process_id = f"{suite}-b{block:02d}-s{slot:02d}-{comparison}"
    process_root = root / "processes" / process_id
    process_root.mkdir(parents=True, exist_ok=False)

    command = [
        "bash", str(ROOT / "scripts/run_with_vulkan.sh"), str(executable),
        "--mode", "measure",
        "--candidate", candidate,
        "--start-order", start_order,
        "--elements", str(config["workload"]["elements"]),
        "--batch-dispatches", str(batch_dispatches),
        "--warmup-pairs", str(warmup_pairs),
        "--measured-pairs", str(measured_pairs),
    ]
    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(process_root)

    before = host_snapshot()
    proc = subprocess.run(
        command, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    after = host_snapshot()
    (process_root / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (process_root / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"K003 process {process_id} failed; campaign is invalid, do not timing-rerun"
        )

    device = json.loads((process_root / "k001-device.json").read_text(encoding="utf-8"))
    if device.get("device") != config["target_gpu"]:
        raise RuntimeError(f"wrong GPU in {process_id}: {device.get('device')!r}")

    rows: list[dict[str, object]] = []
    for raw in read_csv(process_root / "k001-samples.csv"):
        role = raw["role"]
        variant = "baseline" if role == "A" else candidate
        if raw["variant"] != variant:
            raise RuntimeError(f"{process_id}: role/variant mismatch")
        units = int(raw["controlled_work_units"])
        if units != expected_units(config, variant, batch_dispatches):
            raise RuntimeError(f"{process_id}: controlled work unit mismatch")
        gpu_us = float(raw["gpu_us"])
        wall_us = float(raw["complete_wall_us"])
        if not math.isfinite(gpu_us) or gpu_us <= 0.0:
            raise RuntimeError(f"{process_id}: invalid GPU timestamp sample")
        if not math.isfinite(wall_us) or wall_us <= 0.0:
            raise RuntimeError(f"{process_id}: invalid complete CPU-wall sample")
        if wall_us < gpu_us:
            raise RuntimeError(
                f"{process_id}: complete CPU wall is smaller than GPU timestamp"
            )
        enriched: dict[str, object] = dict(raw)
        enriched.update({
            "suite": suite,
            "comparison": comparison,
            "candidate": candidate,
            "block": block,
            "slot": slot,
            "process_id": process_id,
            "start_order": start_order,
        })
        rows.append(enriched)

    observation = {
        "suite": suite,
        "comparison": comparison,
        "candidate": candidate,
        "block": block,
        "slot": slot,
        "process_id": process_id,
        "start_order": start_order,
        "before": before,
        "after": after,
    }
    return rows, observation, device


def same_device(devices: list[dict[str, object]]) -> bool:
    if not devices:
        return False
    first = devices[0]
    keys = (
        "device", "api_version", "driver_version", "vendor_id", "device_id",
        "driver_name", "driver_info", "timestamp_period_ns"
    )
    if any(first.get(key) in (None, "") for key in keys):
        return False
    return all(all(device.get(key) == first.get(key) for key in keys) for device in devices)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=ROOT / os.environ.get("PHOS_GI_BUILD_DIR", "build/release"),
    )
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()

    if git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError(f"K003 must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("K003 requires a clean worktree")

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config.get("plan_version") != "lane-k-k002-v1":
        raise RuntimeError("K003 requires frozen plan lane-k-k002-v1")
    if config["accepted_timing_validation"]:
        raise RuntimeError("frozen K002 accepted timing must disable validation layers")
    if int(config["instability_rerun_budget"]) != 0:
        raise RuntimeError("Lane K v1 instability rerun budget must remain zero")
    if int(config["completed_campaign_rerun_budget"]) != 0:
        raise RuntimeError("Lane K v1 completed-campaign rerun budget must remain zero")
    if config["axis_roles"]["primary_performance"] != "gpu_timestamp":
        raise RuntimeError("K002 primary axis must remain GPU timestamp")
    if config["axis_roles"]["cpu_wall"] != "diagnostic-health-provenance-only":
        raise RuntimeError("K002 CPU wall role changed")

    executable = args.build_dir / "phos-lane-k-k001"
    if not executable.is_file():
        raise RuntimeError(f"missing executable: {executable}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    root = args.artifact_dir or (Path(env_root) if env_root else None)
    if root is None:
        root = ROOT / "out/research/lane-k-gpu-primary-calibration/003-target-calibration" / stamp
    root.mkdir(parents=True, exist_ok=bool(env_root))
    (root / "k003-config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo:
        proc = subprocess.run(
            [vulkaninfo, "--summary"], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        (root / "k003-vulkaninfo-summary.txt").write_text(proc.stdout, encoding="utf-8")

    all_rows: list[dict[str, object]] = []
    observations: list[dict[str, object]] = []
    devices: list[dict[str, object]] = []
    progress = {
        "state": "running",
        "git_commit": git("rev-parse", "HEAD"),
        "plan_version": config["plan_version"],
        "completed_processes": [],
    }

    def save_progress() -> None:
        (root / "k003-progress.json").write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    save_progress()
    try:
        batch = int(config["workload"]["accepted_batch_dispatches"])
        orders = config["comparison_orders"]
        comparisons = config["comparisons"]
        for block, order in enumerate(orders):
            for slot, comparison in enumerate(order):
                progress["current"] = {
                    "suite": "accepted",
                    "block": block,
                    "slot": slot,
                    "comparison": comparison,
                }
                save_progress()
                rows, obs, device = run_process(
                    executable, root, config, "accepted", comparison,
                    comparisons[comparison], block, slot, batch,
                    int(config["warmup_pairs"]), int(config["measured_pairs"])
                )
                all_rows.extend(rows)
                observations.append(obs)
                devices.append(device)
                progress["completed_processes"].append(obs["process_id"])
                save_progress()

        diagnostic = config["diagnostic_individual"]
        if diagnostic["enabled"]:
            diag_comparisons = diagnostic["comparisons"]
            for block in range(int(diagnostic["fresh_process_blocks"])):
                order = diag_comparisons if block % 2 == 0 else list(reversed(diag_comparisons))
                for slot, comparison in enumerate(order):
                    progress["current"] = {
                        "suite": "individual-diagnostic",
                        "block": block,
                        "slot": slot,
                        "comparison": comparison,
                    }
                    save_progress()
                    rows, obs, device = run_process(
                        executable, root, config, "individual-diagnostic",
                        comparison, comparisons[comparison], block, slot,
                        int(config["workload"]["diagnostic_individual_dispatches"]),
                        int(diagnostic["warmup_pairs"]),
                        int(diagnostic["measured_pairs"])
                    )
                    all_rows.extend(rows)
                    observations.append(obs)
                    devices.append(device)
                    progress["completed_processes"].append(obs["process_id"])
                    save_progress()
    except BaseException:
        progress["state"] = "invalid-or-interrupted"
        save_progress()
        raise

    if not same_device(devices):
        raise RuntimeError("K003 device/driver/API provenance changed during campaign")

    process_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in all_rows:
        process_groups[str(row["process_id"])].append(row)
    process_rows = [analysis.summarize_process(rows) for rows in process_groups.values()]

    accepted_process_rows = [
        row for row in process_rows
        if str(row["process_id"]).startswith("accepted-")
    ]
    accepted_summary = analysis.summarize_k003(accepted_process_rows, config)

    diagnostic_process_rows = [
        row for row in process_rows
        if str(row["process_id"]).startswith("individual-diagnostic-")
    ]
    diagnostic_by_comparison: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in diagnostic_process_rows:
        diagnostic_by_comparison[str(row["comparison"])].append(row)
    diagnostic_summary: dict[str, object] = {"decision_use": "diagnostic-only", "axes": {}}
    if diagnostic_process_rows:
        for axis in ("gpu", "wall"):
            criteria = config["repeatability_criteria"][axis]
            control = analysis.evaluate_control(
                diagnostic_by_comparison["control"], axis, criteria
            )
            plus20 = analysis.evaluate_candidate(
                diagnostic_by_comparison["plus20"], axis, criteria, control
            )
            diagnostic_summary["axes"][axis] = {
                "control": control,
                "plus20": plus20,
            }

    write_csv(root / "k003-raw.csv", all_rows)
    write_csv(
        root / "k003-process-summary.csv",
        [flatten_process(row) for row in process_rows],
    )
    (root / "k003-host-observations.json").write_text(
        json.dumps(observations, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "k003-devices.json").write_text(
        json.dumps(devices, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    summary = {
        "schema_version": 1,
        "plan_version": config["plan_version"],
        "git_commit": git("rev-parse", "HEAD"),
        "branch": EXPECTED_BRANCH,
        "target_gpu": config["target_gpu"],
        "all_samples_retained": True,
        "sample_exclusion": "none",
        "instability_rerun_budget": 0,
        "device_provenance_consistent": True,
        "axis_roles": config["axis_roles"],
        "accepted": accepted_summary,
        "individual_diagnostic": diagnostic_summary,
        "individual_diagnostic_processes": [
            flatten_process(row) for row in diagnostic_process_rows
        ],
    }
    (root / "k003-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    progress["state"] = "complete"
    progress.pop("current", None)
    save_progress()
    print(f"K003 artifacts: {root}")
    print(json.dumps(accepted_summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

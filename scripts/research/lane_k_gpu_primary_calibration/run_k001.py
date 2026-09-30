#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-k-gpu-primary-calibration"
TARGET_GPU_DISPLAY = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def artifact_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    env = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if env:
        return Path(env)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "out/research/lane-k-gpu-primary-calibration/001-calibration-workload" / stamp


def run_profile(
    executable: Path,
    root: Path,
    name: str,
    elements: int,
    batch_dispatches: int,
    validation: bool,
) -> dict[str, object]:
    profile = root / name
    profile.mkdir(parents=True, exist_ok=False)
    command = [
        "bash", str(ROOT / "scripts/run_with_vulkan.sh"), str(executable),
        "--mode", "validate",
        "--elements", str(elements),
        "--batch-dispatches", str(batch_dispatches),
    ]
    if validation:
        command.append("--validation")
    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(profile)
    proc = subprocess.run(
        command, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    (profile / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (profile / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"K001 validation profile {name} failed")

    device = json.loads((profile / "k001-device.json").read_text(encoding="utf-8"))
    if device.get("device") != TARGET_GPU_DISPLAY:
        raise RuntimeError(f"wrong GPU: {device.get('device')!r}")

    with (profile / "k001-validation.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 4 or not all(row["correct"] == "true" for row in rows):
        raise RuntimeError(f"K001 validation profile {name} correctness failed")

    units = {row["variant"]: int(row["controlled_work_units"]) for row in rows}
    base = units["baseline"]
    expected = {"plus5": 105, "plus10": 110, "plus20": 120}
    for variant, percent in expected.items():
        if units[variant] * 100 != base * percent:
            raise RuntimeError(f"K001 {variant} controlled work ratio mismatch")

    return {
        "name": name,
        "elements": elements,
        "batch_dispatches": batch_dispatches,
        "device": device,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=ROOT / os.environ.get("PHOS_GI_BUILD_DIR", "build/release"),
    )
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--validation", action="store_true")
    args = parser.parse_args()

    if git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError(f"K001 must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("K001 requires a clean worktree")

    executable = args.build_dir / "phos-lane-i-k001"
    if not executable.is_file():
        raise RuntimeError(f"missing executable: {executable}")

    root = artifact_root(args.artifact_dir)
    root.mkdir(parents=True, exist_ok=bool(os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")))

    profiles = [
        run_profile(executable, root, "accepted-shape", 8192, 16, args.validation),
        run_profile(executable, root, "single-dispatch-control", 8192, 1, args.validation),
    ]

    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo:
        proc = subprocess.run(
            [vulkaninfo, "--summary"], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        (root / "k001-vulkaninfo-summary.txt").write_text(proc.stdout, encoding="utf-8")

    summary = {
        "schema_version": 1,
        "experiment": "K001",
        "git_commit": git("rev-parse", "HEAD"),
        "branch": EXPECTED_BRANCH,
        "target_gpu": TARGET_GPU_DISPLAY,
        "validation_layers": args.validation,
        "all_profiles_correct": True,
        "controlled_work_ratios_verified": True,
        "profiles": profiles,
    }
    (root / "k001-validation-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"K001 validation artifacts: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

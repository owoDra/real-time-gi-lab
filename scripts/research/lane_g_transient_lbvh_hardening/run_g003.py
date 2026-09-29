#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-g-transient-lbvh-hardening"
EXPECTED_GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
VARIANTS = ("transient-lbvh", "hardened-transient-lbvh", "vanilla-software")
SCENARIOS = ("static", "moving-rigid", "sparse-stress", "sparse-moving", "dense-moving")
RELEASED_NAMES = {
    "static-hwrt.vertices",
    "static-hwrt.instance",
    "static-hwrt.scratch",
}


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_case(
    executable: Path,
    scene: Path,
    variant: str,
    scenario: str,
    output: Path,
) -> tuple[dict[str, str], list[dict[str, str]], dict[str, object]]:
    output.mkdir(parents=True, exist_ok=False)
    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--scene", str(scene),
        "--variant", variant,
        "--scenario", scenario,
        "--validation",
    ]
    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(output)
    proc = subprocess.run(
        command, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    (output / "process.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (output / "process.stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"G003 {variant}/{scenario} failed with {proc.returncode}")

    frame_rows = read_rows(output / "g003-frame.csv")
    allocation_rows = read_rows(output / "g003-allocations.csv")
    if len(frame_rows) != 1:
        raise RuntimeError("G003 frame artifact must contain exactly one row")
    frame = frame_rows[0]
    device = json.loads((output / "g003-device.json").read_text(encoding="utf-8"))

    if frame["device"] != EXPECTED_GPU or device["device"] != EXPECTED_GPU:
        raise RuntimeError(f"wrong target GPU for {variant}/{scenario}")
    if frame["quality_passed"] != "1" or int(frame["storage_failures"]) != 0:
        raise RuntimeError(f"correctness failed for {variant}/{scenario}")

    counted = sum(
        int(row["allocation_bytes"])
        for row in allocation_rows
        if row["counted_in_f007_peak"] == "1"
    )
    peak = int(frame["peak_resident_bytes"])
    if counted != peak:
        raise RuntimeError(
            f"G003 accounting mismatch for {variant}/{scenario}: "
            f"census={counted}, peak={peak}"
        )
    return frame, allocation_rows, device


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
    args = parser.parse_args()

    if git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError(f"G003 must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("G003 requires a clean worktree")

    commit = git("rev-parse", "HEAD")
    executable = args.build_dir / "phos-lane-g-g003"
    if not executable.is_file():
        raise RuntimeError(f"missing G003 executable: {executable}")
    if not args.scene.is_file():
        raise RuntimeError(f"missing scene: {args.scene}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = args.artifact_dir or (
        ROOT / "out/research/lane-g-transient-lbvh-hardening"
        / "003-memory-reduction-candidates" / stamp
    )
    root.mkdir(parents=True, exist_ok=False)

    frames: list[dict[str, str]] = []
    allocations: list[dict[str, str]] = []
    devices: list[dict[str, object]] = []
    for variant in VARIANTS:
        for scenario in SCENARIOS:
            frame, rows, device = run_case(
                executable,
                args.scene,
                variant,
                scenario,
                root / variant / scenario,
            )
            frames.append(frame)
            allocations.extend(rows)
            devices.append(device)

    frame_by_key = {(row["variant"], row["scenario"]): row for row in frames}
    alloc_by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in allocations:
        alloc_by_key.setdefault((row["variant"], row["scenario"]), []).append(row)

    scenarios: dict[str, object] = {}
    exact_delta_pass = True
    no_memory_regression = True
    sparse_gate_pass = True
    at_least_one_sparse_improvement = False

    for scenario in SCENARIOS:
        baseline = int(frame_by_key[("transient-lbvh", scenario)]["peak_resident_bytes"])
        hardened = int(
            frame_by_key[("hardened-transient-lbvh", scenario)]["peak_resident_bytes"]
        )
        vanilla = int(frame_by_key[("vanilla-software", scenario)]["peak_resident_bytes"])

        baseline_rows = alloc_by_key[("transient-lbvh", scenario)]
        hardened_rows = alloc_by_key[("hardened-transient-lbvh", scenario)]
        expected_released = sum(
            int(row["allocation_bytes"])
            for row in baseline_rows
            if row["name"] in RELEASED_NAMES and row["use_lifetime"] == "setup-only"
        )
        observed_released = baseline - hardened
        remaining_hardened_names = {row["name"] for row in hardened_rows}
        released_absent = not (RELEASED_NAMES & remaining_hardened_names)
        attributable = observed_released == expected_released and released_absent
        exact_delta_pass = exact_delta_pass and attributable

        improvement = (baseline - hardened) / baseline
        ratio_vs_vanilla = hardened / vanilla
        no_regression = hardened <= baseline * 1.10
        no_memory_regression = no_memory_regression and no_regression

        if scenario in {"sparse-stress", "sparse-moving"}:
            sparse_gate_pass = sparse_gate_pass and ratio_vs_vanilla <= 3.0
            at_least_one_sparse_improvement = (
                at_least_one_sparse_improvement or improvement >= 0.10
            )

        scenarios[scenario] = {
            "baseline_peak_bytes": baseline,
            "hardened_peak_bytes": hardened,
            "vanilla_peak_bytes": vanilla,
            "expected_released_setup_only_bytes": expected_released,
            "observed_peak_delta_bytes": observed_released,
            "released_allocations_absent": released_absent,
            "attribution_exact": attributable,
            "memory_improvement_fraction": improvement,
            "hardened_ratio_vs_vanilla": ratio_vs_vanilla,
            "no_gt_10pct_memory_regression": no_regression,
        }

    correctness = all(
        row["quality_passed"] == "1" and int(row["storage_failures"]) == 0
        for row in frames
    )
    all_devices = all(device["device"] == EXPECTED_GPU for device in devices)
    memory_gates_pass = (
        correctness
        and all_devices
        and exact_delta_pass
        and sparse_gate_pass
        and at_least_one_sparse_improvement
        and no_memory_regression
    )

    summary = {
        "schema_version": 1,
        "plan_version": "lane-g-g003a-v1",
        "git_commit": commit,
        "target_gpu": EXPECTED_GPU,
        "candidate": "immutable-static-hwrt-build-input-release",
        "all_runs_retained": True,
        "correctness_passed": correctness,
        "all_devices_exact": all_devices,
        "allocation_attribution_exact": exact_delta_pass,
        "sparse_memory_ceiling_passed": sparse_gate_pass,
        "at_least_one_sparse_improvement_ge_10pct": at_least_one_sparse_improvement,
        "no_required_memory_regression_gt_10pct": no_memory_regression,
        "memory_gates_passed": memory_gates_pass,
        "formal_timing_gate": "inconclusive-g002-no-safe-decision-valid-protocol",
        "formally_retained": False,
        "scenarios": scenarios,
        "note": (
            "G003a evaluates deterministic correctness and memory only. "
            "Timing is intentionally not promoted from unstable G002 evidence."
        ),
    }

    write_rows(root / "g003-raw-frames.csv", frames)
    write_rows(root / "g003-raw-allocations.csv", allocations)
    (root / "g003-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "g003-device.json").write_text(
        json.dumps({"target_gpu": EXPECTED_GPU, "devices": devices}, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "metadata.json").write_text(
        json.dumps({
            "git_commit": commit,
            "branch": EXPECTED_BRANCH,
            "artifact_root": str(root.relative_to(ROOT)),
            "validation": True,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"G003 artifacts: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCENE = ROOT / "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"
PLAN_VERSION = "lane-f-plan-v1"
EXPECTED_BRANCH = "research-lane-f-dynamic-geometry-alternatives"
EXPECTED_GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
EXPERIMENT = "002-pure-gpu-transient-lbvh-builder"
FROZEN_CONFIG = (
    ROOT
    / "research/lanes/lane-f-dynamic-geometry-alternatives/experiments"
    / "002-transient-lbvh-builder-config.json"
)
HISTORICAL_CEILING_US = 2972.4075


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def artifact_root() -> Path:
    value = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if value:
        return Path(value)
    return (
        ROOT
        / "out/research/lane-f-dynamic-geometry-alternatives"
        / EXPERIMENT
        / "manual"
    )


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def validation_error_count(stdout: str, stderr: str) -> int:
    combined = stdout + "\n" + stderr
    markers = ("Validation Error", "[Vulkan Validation] ERROR", "VUID-")
    return sum(
        1
        for line in combined.splitlines()
        if any(marker in line for marker in markers)
    )


def run_builder(
    executable: Path,
    scene: Path,
    output_dir: Path,
    warmup_builds: int,
    measured_builds: int,
    validation: bool,
) -> tuple[list[dict[str, str]], dict[str, object], int, float]:
    output_dir.mkdir(parents=True, exist_ok=False)
    csv_path = output_dir / "f002-process.csv"
    device_path = output_dir / "f002-device.json"
    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--scene",
        str(scene),
        "--output",
        str(csv_path),
        "--device-output",
        str(device_path),
        "--warmup-builds",
        str(warmup_builds),
        "--measured-builds",
        str(measured_builds),
    ]
    if validation:
        command.append("--validation")

    started = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    wall_us = (time.perf_counter() - started) * 1_000_000.0
    sys.stdout.write(proc.stdout)
    sys.stdout.flush()
    sys.stderr.write(proc.stderr)
    sys.stderr.flush()
    (output_dir / "process.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (output_dir / "process.stderr.log").write_text(proc.stderr, encoding="utf-8")

    errors = validation_error_count(proc.stdout, proc.stderr) if validation else 0
    if proc.returncode != 0:
        raise RuntimeError(f"F002 builder process failed with {proc.returncode}")
    if errors:
        raise RuntimeError(f"F002 emitted {errors} Vulkan validation errors")
    if not csv_path.is_file() or not device_path.is_file():
        raise RuntimeError("F002 process did not produce required artifacts")

    rows = read_csv(csv_path)
    device = json.loads(device_path.read_text(encoding="utf-8"))
    if device.get("device") != EXPECTED_GPU:
        raise RuntimeError(
            f"F002 target GPU mismatch: {device.get('device')!r} != {EXPECTED_GPU!r}"
        )
    if not rows or any(row.get("validation_passed") != "1" for row in rows):
        raise RuntimeError("F002 structural validation did not pass")
    return rows, device, errors, wall_us


def find_prior_validation(
    current_root: Path,
    branch: str,
    commit: str,
) -> tuple[str, dict[str, object]] | None:
    experiment_root = current_root.parent
    if not experiment_root.is_dir():
        return None
    for candidate in sorted(experiment_root.iterdir(), reverse=True):
        if candidate == current_root or not candidate.is_dir():
            continue
        validation_path = candidate / "f002-validation.json"
        device_path = candidate / "f002-device.json"
        if not validation_path.is_file() or not device_path.is_file():
            continue
        try:
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            device = json.loads(device_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if (
            validation.get("passed") is True
            and validation.get("plan_version") == PLAN_VERSION
            and validation.get("branch") == branch
            and validation.get("git_commit") == commit
            and device.get("device") == EXPECTED_GPU
            and device.get("validation") is True
        ):
            return str(candidate), validation
    return None


def summarize_process_rows(
    rows: list[dict[str, object]],
) -> tuple[dict[str, object], bool]:
    grouped: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(int(row["primitive_count"]), []).append(row)

    summaries: dict[str, object] = {}
    any_unstable = False
    timing_fields = (
        "reset_us",
        "input_us",
        "aabb_us",
        "morton_us",
        "sort_us",
        "topology_us",
        "bounds_us",
        "builder_gpu_us",
    )
    for primitive_count, group in sorted(grouped.items()):
        summary: dict[str, object] = {}
        for field in timing_fields:
            values = [float(row[field]) for row in group]
            summary[field] = {
                "min": min(values),
                "median": statistics.median(values),
                "max": max(values),
            }
        builder_values = [float(row["builder_gpu_us"]) for row in group]
        unstable = (
            min(builder_values) > 0.0
            and max(builder_values) / min(builder_values) > 1.20
        )
        summary["unstable"] = unstable
        summary["process_repeats"] = len(group)
        summary["is_nrep"] = any(int(row["is_nrep"]) == 1 for row in group)
        summary["peak_builder_bytes"] = max(
            int(row["peak_resident_bytes"]) for row in group
        )
        summaries[str(primitive_count)] = summary
        any_unstable = any_unstable or unstable
    return summaries, any_unstable


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="build/release")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--validation-only", action="store_true")
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()

    if args.validation_only and args.skip_validation:
        raise RuntimeError("--validation-only and --skip-validation are exclusive")
    if args.repeats != 5 and not args.validation_only:
        raise RuntimeError("F002 accepted timing requires exactly 5 process repeats")

    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"F002 must run on {EXPECTED_BRANCH}, got {branch}")
    if dirty:
        raise RuntimeError("F002 target evidence requires a clean Git tree")

    executable = ROOT / args.build_dir / "phos-lane-f-f002-lbvh"
    if not executable.is_file():
        raise RuntimeError(f"F002 executable not found: {executable}")
    if not FROZEN_CONFIG.is_file():
        raise RuntimeError(f"F002 frozen config missing: {FROZEN_CONFIG}")

    config = json.loads(FROZEN_CONFIG.read_text(encoding="utf-8"))
    config.update(
        {
            "branch": branch,
            "git_commit": commit,
            "dirty": dirty,
            "scene": str(args.scene),
            "artifact_root": str(root),
            "command": " ".join(sys.argv),
        }
    )
    write_json(root / "f002-config.json", config)

    if args.validation_only:
        rows, device, errors, wall_us = run_builder(
            executable,
            args.scene,
            root / "validation-process",
            1,
            1,
            True,
        )
        passed = errors == 0 and all(
            row.get("validation_passed") == "1" for row in rows
        )
        validation = {
            "schema_version": 1,
            "plan_version": PLAN_VERSION,
            "experiment": "F002",
            "branch": branch,
            "git_commit": commit,
            "dirty": dirty,
            "target_gpu": EXPECTED_GPU,
            "passed": passed,
            "validation_errors": errors,
            "sizes_checked": [int(row["primitive_count"]) for row in rows],
            "process_wall_us": wall_us,
            "structural_checks": {
                "sort_mismatches": sum(int(row["sort_mismatches"]) for row in rows),
                "root_count_mismatches": sum(
                    int(row["root_count_mismatches"]) for row in rows
                ),
                "root_bounds_mismatches": sum(
                    int(row["root_bounds_mismatches"]) for row in rows
                ),
            },
        }
        write_json(root / "f002-validation.json", validation)
        device.update(
            {
                "plan_version": PLAN_VERSION,
                "branch": branch,
                "git_commit": commit,
            }
        )
        write_json(root / "f002-device.json", device)
        write_csv(root / "f002-raw.csv", [])
        write_json(
            root / "f002-summary.json",
            {
                "schema_version": 1,
                "plan_version": PLAN_VERSION,
                "status": "validation-pass" if passed else "validation-fail",
                "formal_gate": "not-evaluated-validation-only",
            },
        )
        if not passed:
            return 3
        print("F002 validation passed on all frozen sweep sizes.")
        return 0

    if not args.skip_validation:
        raise RuntimeError(
            "F002 timing requires --skip-validation after a passing validation artifact"
        )
    prior = find_prior_validation(root, branch, commit)
    if prior is None:
        raise RuntimeError(
            "F002 timing requires a passing prior validation artifact from the same commit/GPU"
        )
    validation_artifact, validation_payload = prior
    write_json(
        root / "f002-validation.json",
        {
            **validation_payload,
            "reused_from_artifact": validation_artifact,
        },
    )

    accepted_rows: list[dict[str, object]] = []
    device_payload: dict[str, object] | None = None
    for repeat in range(args.repeats):
        rows, device, _, process_wall_us = run_builder(
            executable,
            args.scene,
            root / f"repeat-{repeat:02d}",
            10,
            100,
            False,
        )
        if device_payload is None:
            device_payload = device
        elif (
            device.get("device") != device_payload.get("device")
            or device.get("driver_name") != device_payload.get("driver_name")
            or device.get("driver_info") != device_payload.get("driver_info")
            or device.get("api_version_raw") != device_payload.get("api_version_raw")
            or device.get("nrep") != device_payload.get("nrep")
        ):
            raise RuntimeError("F002 device/workload identity changed across repeats")

        for row in rows:
            primitive_count = int(row["primitive_count"])
            is_nrep = int(row["is_nrep"]) == 1
            enriched: dict[str, object] = dict(row)
            enriched.update(
                {
                    "schema_version": 1,
                    "plan_version": PLAN_VERSION,
                    "branch": branch,
                    "git_commit": commit,
                    "dirty": False,
                    "artifact_root": str(root),
                    "command": " ".join(sys.argv),
                    "experiment": "F002",
                    "variant": "transient-lbvh-builder",
                    "scenario": "representative-nrep" if is_nrep else "diagnostic-sweep",
                    "geometry_class": "rigid-representative" if is_nrep else "diagnostic-scale",
                    "repeat": repeat,
                    "validation_state": "passed-prior-same-commit-gpu",
                    "target_gpu": device["device"],
                    "driver_name": device["driver_name"],
                    "driver_info": device["driver_info"],
                    "api_version": device["api_version"],
                    "scene": str(args.scene),
                    "dynamic_primitive_count": primitive_count,
                    "dynamic_object_count": (
                        1
                        if is_nrep
                        else (primitive_count + int(device["nrep"]) - 1)
                        // int(device["nrep"])
                    ),
                    "topology_delta_count": 0,
                    "complete_gpu_us": row["builder_gpu_us"],
                    "complete_frame_wall_us": "",
                    "persistent_bytes": row["template_bytes"],
                    "transient_bytes": (
                        int(row["working_geometry_bytes"])
                        + int(row["aabb_bytes"])
                        + int(row["key_bytes"])
                        + int(row["node_bytes"])
                    ),
                    "scratch_bytes": (
                        int(row["histogram_bytes"])
                        + int(row["prefix_bytes"])
                        + int(row["ready_bytes"])
                    ),
                    "peak_resident_bytes": row["peak_builder_bytes"],
                    "process_wall_us": process_wall_us,
                    "validation_errors": 0,
                    "hit_mismatches": 0,
                    "traversal_runtime_errors": 0,
                    "candidate_node_bytes": row["node_bytes"],
                    "candidate_sort_bytes": (
                        int(row["key_bytes"])
                        + int(row["histogram_bytes"])
                        + int(row["prefix_bytes"])
                    ),
                }
            )
            accepted_rows.append(enriched)

    if device_payload is None:
        raise RuntimeError("F002 did not capture device metadata")

    write_csv(root / "f002-raw.csv", accepted_rows)
    summaries, any_unstable = summarize_process_rows(accepted_rows)
    nrep = int(device_payload["nrep"])
    nrep_summary = summaries.get(str(nrep))
    if nrep_summary is None:
        raise RuntimeError("F002 timing did not contain Nrep row")
    nrep_builder = float(nrep_summary["builder_gpu_us"]["median"])

    summary = {
        "schema_version": 1,
        "plan_version": PLAN_VERSION,
        "status": "unstable-rerun-required" if any_unstable else "target-run-complete",
        "branch": branch,
        "git_commit": commit,
        "dirty": False,
        "target_gpu": EXPECTED_GPU,
        "repeats": args.repeats,
        "warmup_builds_per_size_per_process": 10,
        "measured_builds_per_size_per_process": 100,
        "validation_artifact": validation_artifact,
        "nrep": nrep,
        "sizes": summaries,
        "nrep_builder_gpu_us": nrep_builder,
        "historical_ceiling_us_reference_only": HISTORICAL_CEILING_US,
        "historical_reference_ratio": nrep_builder / HISTORICAL_CEILING_US,
        "formal_gate": {
            "status": "pending-f001-baseline-repeatability-inconclusive",
            "formula": (
                "median_builder_gpu_at_Nrep < "
                "0.90 * stable_run_local_vanilla_moving_complete_gpu"
            ),
            "reason": (
                "F001 vanilla-software/moving-rigid was unstable in both "
                "the initial timing artifact and the one permitted identical rerun"
            ),
        },
        "unstable": any_unstable,
    }
    write_json(root / "f002-summary.json", summary)

    device_payload.update(
        {
            "plan_version": PLAN_VERSION,
            "branch": branch,
            "git_commit": commit,
        }
    )
    write_json(root / "f002-device.json", device_payload)

    if any_unstable:
        print(
            "F002 timing contains builder_gpu max/min > 1.20; "
            "one identical full rerun is required."
        )
        return 4

    print(
        "F002 complete: pure GPU LBVH builder measured; "
        f"Nrep={nrep}, median={nrep_builder:.3f} us. "
        "Formal feasibility gate remains pending because the frozen "
        "run-local vanilla moving comparator is inconclusive."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCENE = ROOT / "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"
VARIANTS = (
    "vanilla-software",
    "combined-hwrt",
    "combined-software",
    "depth-reuse-hwrt",
    "bounded-hwrt",
)
SCENARIOS = ("static", "camera-motion", "light-motion", "moving-rigid")


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
    return ROOT / "out/research/integration-gate/001-dynamic-end-to-end/manual"


def run_one(
    executable: Path,
    scene: Path,
    variant: str,
    scenario: str,
    output_dir: Path,
    validation: bool,
    bounded_owner_capacity: int = 1280,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=False)
    command = [
        str(executable),
        "--scene",
        str(scene),
        "--variant",
        variant,
        "--scenario",
        scenario,
    ]
    if variant == "bounded-hwrt":
        command.extend([
            "--bounded-owner-capacity",
            str(bounded_owner_capacity),
        ])
    if validation:
        command.append("--validation")

    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(output_dir)
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    sys.stdout.write(proc.stdout)
    sys.stdout.flush()
    sys.stderr.write(proc.stderr)
    sys.stderr.flush()
    (output_dir / "process.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (output_dir / "process.stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"I001 {variant}/{scenario} "
            f"{'validation' if validation else 'timing'} failed with {proc.returncode}"
        )

    csv_path = output_dir / "i001-frame.csv"
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise RuntimeError(f"{csv_path} must contain exactly one data row")
    row = rows[0]
    if row.get("quality_passed") != "1":
        raise RuntimeError(f"I001 quality gate failed for {variant}/{scenario}")
    if int(row.get("storage_failures", "0")) != 0:
        raise RuntimeError(f"I001 storage failures for {variant}/{scenario}")
    return row


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the repeatable representative I001 integration matrix."
    )
    parser.add_argument("--build-dir", type=Path, default=Path("build/release"))
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()

    if args.repeats < 3:
        parser.error("--repeats must be >= 3 for accepted representative timing")

    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    if dirty:
        raise RuntimeError("formal I001 matrix requires a clean checkout")
    if branch != "research-integration-gate":
        raise RuntimeError(
            f"formal I001 matrix requires research-integration-gate, got {branch!r}"
        )

    executable = (ROOT / args.build_dir / "phos-i001").resolve()
    if not executable.is_file():
        raise RuntimeError(f"missing I001 executable: {executable}")
    scene = args.scene.resolve()
    if not scene.is_file():
        raise RuntimeError(f"missing I001 scene: {scene}")

    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)

    if not args.skip_validation:
        for variant in VARIANTS:
            for scenario in SCENARIOS:
                run_one(
                    executable,
                    scene,
                    variant,
                    scenario,
                    root / "validation" / variant / scenario,
                    True,
                    1280,
                )

    accepted: list[dict[str, str]] = []
    for repeat in range(args.repeats):
        for variant in VARIANTS:
            for scenario in SCENARIOS:
                row = run_one(
                    executable,
                    scene,
                    variant,
                    scenario,
                    root / "timing" / f"repeat-{repeat + 1}" / variant / scenario,
                    False,
                    1280,
                )
                row = dict(row)
                row["repeat"] = str(repeat + 1)
                row["git_commit"] = commit
                accepted.append(row)

    columns = ["git_commit", "repeat", *accepted[0].keys()]
    # git_commit/repeat were appended after the binary's native columns.
    columns = list(dict.fromkeys(columns))
    with (root / "i001-representative.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(accepted)

    medians: dict[str, dict[str, dict[str, float]]] = {}
    for variant in VARIANTS:
        medians[variant] = {}
        for scenario in SCENARIOS:
            rows = [
                row for row in accepted
                if row["variant"] == variant and row["scenario"] == scenario
            ]
            medians[variant][scenario] = {
                "complete_gpu_us": statistics.median(
                    float(row["complete_gpu_us"]) for row in rows
                ),
                "incremental_gi_us": statistics.median(
                    float(row["incremental_gi_us"]) for row in rows
                ),
                "peak_resident_bytes": statistics.median(
                    int(row["peak_resident_bytes"]) for row in rows
                ),
            }

    overflow_rows: list[dict[str, object]] = []
    for repeat in range(args.repeats):
        failed = run_one(
            executable,
            scene,
            "bounded-hwrt",
            "static",
            root / "overflow" / f"repeat-{repeat + 1}" / "bounded-512",
            False,
            512,
        )
        if int(failed["overflow"]) != 1:
            raise RuntimeError("forced 512-owner bounded run did not overflow")
        if int(failed["requested_work_items"]) <= int(failed["work_items"]):
            raise RuntimeError("forced overflow did not clamp work-item count")

        retry = run_one(
            executable,
            scene,
            "combined-hwrt",
            "static",
            root / "overflow" / f"repeat-{repeat + 1}" / "full-retry",
            False,
            1280,
        )
        overflow_rows.append({
            "git_commit": commit,
            "repeat": repeat + 1,
            "bounded_owner_capacity": 512,
            "failed_attempt_gpu_us": float(failed["complete_gpu_us"]),
            "retry_gpu_us": float(retry["complete_gpu_us"]),
            "total_retry_gpu_us":
                float(failed["complete_gpu_us"]) +
                float(retry["complete_gpu_us"]),
            "failed_attempt_peak_resident_bytes":
                int(failed["peak_resident_bytes"]),
            "retry_peak_resident_bytes":
                int(retry["peak_resident_bytes"]),
            "retry_peak_resident_bytes_max":
                max(
                    int(failed["peak_resident_bytes"]),
                    int(retry["peak_resident_bytes"]),
                ),
            "requested_work_items": int(failed["requested_work_items"]),
            "clamped_work_items": int(failed["work_items"]),
            "retry_quality_passed": int(retry["quality_passed"]),
        })

    overflow_columns = list(overflow_rows[0].keys())
    with (root / "i001-overflow-retry.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=overflow_columns)
        writer.writeheader()
        writer.writerows(overflow_rows)

    summary = {
        "schema_version": 1,
        "status": "representative-sponza-ready",
        "branch": branch,
        "git_commit": commit,
        "dirty": dirty,
        "repeats": args.repeats,
        "validation_run": not args.skip_validation,
        "scene": str(scene),
        "variants": list(VARIANTS),
        "scenarios": list(SCENARIOS),
        "medians": medians,
        "overflow_retry": {
            "bounded_owner_capacity": 512,
            "median_total_retry_gpu_us": statistics.median(
                row["total_retry_gpu_us"] for row in overflow_rows
            ),
            "median_peak_resident_bytes": statistics.median(
                row["retry_peak_resident_bytes_max"] for row in overflow_rows
            ),
            "all_retry_quality_passed": all(
                row["retry_quality_passed"] == 1 for row in overflow_rows
            ),
        },
        "pending_before_i001_closeout": [
            "sparse stress",
            "dense stress",
            "large-world stress",
            "vertical-world stress",
            "final fixed-gate decision",
        ],
    }
    (root / "i001-representative-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "I001 representative matrix complete; "
        "dynamic/stress/overflow gates remain pending."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

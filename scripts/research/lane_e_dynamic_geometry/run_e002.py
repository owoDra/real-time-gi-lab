#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET_BRANCH = "research-lane-e-dynamic-geometry"
TARGET_DEVICE = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
SCENARIO = "moving-rigid"
CONTROL = "combined-hwrt"
CANDIDATES = (
    "rigid-instance-hwrt-update",
    "rigid-instance-hwrt-build",
)
VARIANTS = (CONTROL, *CANDIDATES)

ACCOUNTING_FIELDS = (
    "surface_update_gpu_us",
    "instance_transfer_gpu_us",
    "geometry_transfer_gpu_us",
    "blas_update_us",
    "tlas_update_us",
)
SUMMARY_FIELDS = (
    "setup_wall_us",
    "dynamic_update_wall_us",
    "geometry_prepare_cpu_us",
    "surface_update_gpu_us",
    "instance_transfer_wall_us",
    "instance_transfer_gpu_us",
    "geometry_transfer_wall_us",
    "geometry_transfer_gpu_us",
    "blas_update_us",
    "tlas_update_us",
    "traversal_maintenance_gpu_us",
    "producer_us",
    "traversal_us",
    "storage_update_us",
    "invalidation_us",
    "resolve_us",
    "complete_gpu_us",
    "persistent_bytes",
    "scratch_bytes",
    "peak_resident_bytes",
)

BOUNDARY_IMPROVEMENT_REQUIRED = 0.20
TRAVERSAL_REGRESSION_LIMIT = 0.10
POLICY_TIE_BAND = 0.05


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
    return ROOT / "out/research/lane-e-dynamic-geometry/002-hwrt-rigid-instance/manual"


def run_one(
    executable: Path,
    scene: Path,
    variant: str,
    output_dir: Path,
    validation: bool,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=False)
    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--scene",
        str(scene),
        "--variant",
        variant,
        "--scenario",
        SCENARIO,
    ]
    if validation:
        command.append("--validation")

    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(output_dir)
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    (output_dir / "stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (output_dir / "stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"{variant} {'validation' if validation else 'timing'} failed "
            f"with exit code {proc.returncode}: {proc.stderr.strip()}"
        )
    if validation and "Validation Error" in proc.stderr:
        raise RuntimeError(f"{variant} emitted Vulkan validation errors")

    csv_path = output_dir / "i001-frame.csv"
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise RuntimeError(f"{csv_path} must contain exactly one data row")
    row = rows[0]
    if row.get("device") != TARGET_DEVICE:
        raise RuntimeError(
            f"unexpected target device for {variant}: {row.get('device')!r}"
        )
    if row.get("scenario") != SCENARIO:
        raise RuntimeError(f"{variant} did not run {SCENARIO}")
    if row.get("quality_passed") != "1":
        raise RuntimeError(f"{variant} quality gate failed")
    if int(row.get("storage_failures", "1")) != 0:
        raise RuntimeError(f"{variant} storage failures are non-zero")
    return row


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def median(rows: list[dict[str, str]], key: str) -> float:
    return statistics.median(f(row, key) for row in rows)


def dynamic_boundary(row: dict[str, str]) -> float:
    return (
        f(row, "dynamic_update_wall_us")
        + f(row, "complete_gpu_us")
        - f(row, "traversal_maintenance_gpu_us")
    )


def accounting_error(row: dict[str, str]) -> tuple[float, float]:
    named = sum(f(row, key) for key in ACCOUNTING_FIELDS)
    total = f(row, "traversal_maintenance_gpu_us")
    return abs(named - total), max(2.0, abs(total) * 0.01)


def check_architecture_integrity(
    row: dict[str, str],
    variant: str,
) -> None:
    if variant not in CANDIDATES:
        return
    if f(row, "geometry_transfer_gpu_us") != 0.0:
        raise RuntimeError(
            f"{variant} rewrote rigid geometry: "
            f"{row['geometry_transfer_gpu_us']} us"
        )
    if f(row, "blas_update_us") != 0.0:
        raise RuntimeError(
            f"{variant} updated the rigid BLAS: {row['blas_update_us']} us"
        )


def summarize_group(rows: list[dict[str, str]]) -> dict[str, object]:
    medians = {key: median(rows, key) for key in SUMMARY_FIELDS}
    medians["complete_dynamic_boundary_us"] = statistics.median(
        dynamic_boundary(row) for row in rows
    )
    return {
        "repeat_count": len(rows),
        "moved_primitives": int(rows[0]["moved_primitives"]),
        "segment_membership_changes": int(rows[0]["segment_membership_changes"]),
        "medians_us": medians,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, default=Path("build/release"))
    parser.add_argument(
        "--scene",
        type=Path,
        default=Path("assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"),
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--validation-only", action="store_true")
    args = parser.parse_args()

    if args.repeats < 3 and not args.validation_only:
        raise RuntimeError("accepted E002 timing requires at least 3 process repeats")

    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    if branch != TARGET_BRANCH:
        raise RuntimeError(f"E002 must run on {TARGET_BRANCH}, got {branch!r}")
    if dirty:
        raise RuntimeError("formal E002 runs require a clean checkout")

    executable = (ROOT / args.build_dir / "phos-i001").resolve()
    scene = (ROOT / args.scene).resolve()
    if not executable.is_file():
        raise RuntimeError(f"missing executable: {executable}")
    if not scene.is_file():
        raise RuntimeError(f"missing scene: {scene}")

    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)

    validation_rows: list[dict[str, str]] = []
    for variant in VARIANTS:
        row = dict(
            run_one(
                executable,
                scene,
                variant,
                root / "validation" / variant,
                True,
            )
        )
        if not validation_rows:
            print(f"GPU: {row['device']}")
        error, tolerance = accounting_error(row)
        if error > tolerance:
            raise RuntimeError(
                f"{variant} validation accounting mismatch: "
                f"{error:.6f} us > {tolerance:.6f} us"
            )
        check_architecture_integrity(row, variant)
        row["phase"] = "validation"
        row["repeat"] = "0"
        validation_rows.append(row)

    moved_counts = {int(row["moved_primitives"]) for row in validation_rows}
    membership_counts = {
        int(row["segment_membership_changes"]) for row in validation_rows
    }
    if len(moved_counts) != 1 or len(membership_counts) != 1:
        raise RuntimeError("E002 variants did not exercise the same rigid workload")

    validation_summary = {
        "git_branch": branch,
        "git_commit": commit,
        "git_dirty": dirty,
        "target_device": TARGET_DEVICE,
        "pairs": len(validation_rows),
        "all_quality_passed": all(
            row["quality_passed"] == "1" for row in validation_rows
        ),
        "all_storage_failures_zero": all(
            int(row["storage_failures"]) == 0 for row in validation_rows
        ),
        "same_workload": True,
        "moved_primitives": next(iter(moved_counts)),
        "segment_membership_changes": next(iter(membership_counts)),
        "architecture_integrity_passed": True,
        "accounting_passed": True,
    }
    (root / "e002-validation-summary.json").write_text(
        json.dumps(validation_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if args.validation_only:
        print("E002 validation-only matrix: PASS")
        return 0

    timing_rows: list[dict[str, str]] = []
    for repeat in range(1, args.repeats + 1):
        repeat_rows: list[dict[str, str]] = []
        for variant in VARIANTS:
            row = dict(
                run_one(
                    executable,
                    scene,
                    variant,
                    root / "timing" / f"repeat-{repeat}" / variant,
                    False,
                )
            )
            error, tolerance = accounting_error(row)
            if error > tolerance:
                raise RuntimeError(
                    f"{variant} repeat {repeat} accounting mismatch: "
                    f"{error:.6f} us > {tolerance:.6f} us"
                )
            check_architecture_integrity(row, variant)
            row["phase"] = "timing"
            row["repeat"] = str(repeat)
            row["git_commit"] = commit
            repeat_rows.append(row)

        if len({int(row["moved_primitives"]) for row in repeat_rows}) != 1:
            raise RuntimeError(
                f"E002 repeat {repeat} moved-primitive workload diverged"
            )
        if len(
            {int(row["segment_membership_changes"]) for row in repeat_rows}
        ) != 1:
            raise RuntimeError(
                f"E002 repeat {repeat} membership workload diverged"
            )
        timing_rows.extend(repeat_rows)

    fieldnames = list(timing_rows[0].keys())
    with (root / "e002-results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(timing_rows)

    selected: dict[str, list[dict[str, str]]] = {
        variant: [row for row in timing_rows if row["variant"] == variant]
        for variant in VARIANTS
    }
    groups = {
        variant: summarize_group(rows)
        for variant, rows in selected.items()
    }

    control_boundary = groups[CONTROL]["medians_us"][
        "complete_dynamic_boundary_us"
    ]
    control_traversal = groups[CONTROL]["medians_us"]["traversal_us"]

    promotion: dict[str, object] = {}
    passing: list[str] = []
    for variant in CANDIDATES:
        boundary = groups[variant]["medians_us"][
            "complete_dynamic_boundary_us"
        ]
        traversal = groups[variant]["medians_us"]["traversal_us"]
        boundary_improvement = (
            (control_boundary - boundary) / control_boundary
            if control_boundary > 0.0
            else 0.0
        )
        traversal_regression = (
            (traversal - control_traversal) / control_traversal
            if control_traversal > 0.0
            else 0.0
        )
        passed = (
            boundary_improvement >= BOUNDARY_IMPROVEMENT_REQUIRED
            and traversal_regression <= TRAVERSAL_REGRESSION_LIMIT
        )
        promotion[variant] = {
            "complete_dynamic_boundary_improvement_ratio": boundary_improvement,
            "traversal_regression_ratio": traversal_regression,
            "promotion_gate_passed": passed,
        }
        if passed:
            passing.append(variant)

    selected_policy: str | None = None
    selection_reason = "neither candidate passed the frozen promotion gate"
    if len(passing) == 1:
        selected_policy = passing[0]
        selection_reason = "only one candidate passed the frozen promotion gate"
    elif len(passing) == 2:
        update_boundary = groups[CANDIDATES[0]]["medians_us"][
            "complete_dynamic_boundary_us"
        ]
        build_boundary = groups[CANDIDATES[1]]["medians_us"][
            "complete_dynamic_boundary_us"
        ]
        relative_difference = (
            abs(update_boundary - build_boundary)
            / min(update_boundary, build_boundary)
        )
        if relative_difference <= POLICY_TIE_BAND:
            selected_policy = "rigid-instance-hwrt-update"
            selection_reason = (
                "both passed and were within the frozen 5% tie band; "
                "select UPDATE"
            )
        else:
            selected_policy = (
                "rigid-instance-hwrt-update"
                if update_boundary < build_boundary
                else "rigid-instance-hwrt-build"
            )
            selection_reason = (
                "both passed; selected the lower complete dynamic boundary"
            )

    summary = {
        "status": "measurement-complete-result-review-required",
        "git_branch": branch,
        "git_commit": commit,
        "git_dirty": dirty,
        "target_device": TARGET_DEVICE,
        "scenario": SCENARIO,
        "repeats": args.repeats,
        "fixed_gates": {
            "boundary_improvement_required": BOUNDARY_IMPROVEMENT_REQUIRED,
            "traversal_regression_limit": TRAVERSAL_REGRESSION_LIMIT,
            "policy_tie_band": POLICY_TIE_BAND,
            "accounting_tolerance": (
                "max(2 us, 1% of traversal_maintenance_gpu_us)"
            ),
            "candidate_geometry_transfer_gpu_us": 0.0,
            "candidate_blas_update_us": 0.0,
        },
        "groups": groups,
        "promotion": promotion,
        "selected_policy": selected_policy,
        "selection_reason": selection_reason,
        "next_step": (
            "inspect E002 result, publish the fixed-gate decision, then "
            "continue to E003 software object-local ownership"
        ),
    }
    (root / "e002-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        "E002 validation and repeated timing complete; "
        "inspect artifacts before publishing result."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

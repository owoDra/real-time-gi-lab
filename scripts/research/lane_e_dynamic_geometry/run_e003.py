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
CONTROL = "combined-software"
BINARY_CONTROL = "rigid-instance-software-binary"
CANDIDATE = "rigid-instance-software-quantized"
VARIANTS = (CONTROL, BINARY_CONTROL, CANDIDATE)
INSTANCE_VARIANTS = (BINARY_CONTROL, CANDIDATE)

ACCOUNTING_FIELDS = (
    "surface_update_gpu_us",
    "instance_transfer_gpu_us",
    "geometry_transfer_gpu_us",
    "hierarchy_upload_gpu_us",
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
    "membership_update_cpu_us",
    "hierarchy_refit_cpu_us",
    "hierarchy_rebuild_cpu_us",
    "hierarchy_occupancy_cpu_us",
    "packing_cpu_us",
    "hierarchy_upload_gpu_us",
    "traversal_maintenance_gpu_us",
    "producer_us",
    "traversal_us",
    "storage_update_us",
    "invalidation_us",
    "resolve_us",
    "complete_gpu_us",
    "persistent_bytes",
    "transient_bytes",
    "peak_resident_bytes",
)

BOUNDARY_IMPROVEMENT_REQUIRED = 0.50
TRAVERSAL_REGRESSION_LIMIT = 0.15
PERSISTENT_MEMORY_RATIO_LIMIT = 1.25


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def artifact_root() -> Path:
    value = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if value:
        return Path(value)
    return (
        ROOT
        / "out/research/lane-e-dynamic-geometry"
        / "003-software-object-local/manual"
    )


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
    (output_dir / "stdout.txt").write_text(
        proc.stdout, encoding="utf-8"
    )
    (output_dir / "stderr.txt").write_text(
        proc.stderr, encoding="utf-8"
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"{variant} "
            f"{'validation' if validation else 'timing'} "
            f"failed with exit code {proc.returncode}: "
            f"{proc.stderr.strip()}"
        )
    if validation and "Validation Error" in proc.stderr:
        raise RuntimeError(
            f"{variant} emitted Vulkan validation errors"
        )

    csv_path = output_dir / "i001-frame.csv"
    with csv_path.open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise RuntimeError(
            f"{csv_path} must contain exactly one data row"
        )
    row = rows[0]
    if row.get("device") != TARGET_DEVICE:
        raise RuntimeError(
            f"unexpected target device for {variant}: "
            f"{row.get('device')!r}"
        )
    if row.get("scenario") != SCENARIO:
        raise RuntimeError(
            f"{variant} did not run {SCENARIO}"
        )
    if row.get("quality_passed") != "1":
        raise RuntimeError(
            f"{variant} quality gate failed"
        )
    if int(row.get("storage_failures", "1")) != 0:
        raise RuntimeError(
            f"{variant} storage failures are non-zero"
        )
    return row


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def median(
    rows: list[dict[str, str]],
    key: str,
) -> float:
    return statistics.median(
        f(row, key) for row in rows
    )


def dynamic_boundary(
    row: dict[str, str],
) -> float:
    return (
        f(row, "dynamic_update_wall_us")
        + f(row, "complete_gpu_us")
        - f(
            row,
            "traversal_maintenance_gpu_us",
        )
    )


def accounting_error(
    row: dict[str, str],
) -> tuple[float, float]:
    named = sum(
        f(row, key)
        for key in ACCOUNTING_FIELDS
    )
    total = f(
        row,
        "traversal_maintenance_gpu_us",
    )
    return (
        abs(named - total),
        max(2.0, abs(total) * 0.01),
    )


def check_architecture_integrity(
    row: dict[str, str],
    variant: str,
) -> None:
    if variant not in INSTANCE_VARIANTS:
        return

    zero_fields = (
        "geometry_transfer_gpu_us",
        "membership_update_cpu_us",
        "hierarchy_refit_cpu_us",
        "hierarchy_rebuild_cpu_us",
        "packing_cpu_us",
        "hierarchy_upload_gpu_us",
    )
    for key in zero_fields:
        if f(row, key) != 0.0:
            raise RuntimeError(
                f"{variant} violated E003 immutable "
                f"rigid ownership: {key}={row[key]}"
            )

    if "instance_transfer_gpu_us" not in row:
        raise RuntimeError(
            f"{variant} did not report instance transfer"
        )
    if f(row, "instance_transfer_gpu_us") < 0.0:
        raise RuntimeError(
            f"{variant} reported negative instance transfer"
        )


def summarize_group(
    rows: list[dict[str, str]],
) -> dict[str, object]:
    medians = {
        key: median(rows, key)
        for key in SUMMARY_FIELDS
    }
    medians["complete_dynamic_boundary_us"] = (
        statistics.median(
            dynamic_boundary(row)
            for row in rows
        )
    )
    return {
        "repeat_count": len(rows),
        "moved_primitives": int(
            rows[0]["moved_primitives"]
        ),
        "segment_membership_changes": int(
            rows[0]["segment_membership_changes"]
        ),
        "medians_us": medians,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=Path("build/release"),
    )
    parser.add_argument(
        "--scene",
        type=Path,
        default=Path(
            "assets/Vulkan-Samples-Assets/"
            "scenes/sponza/Sponza01.gltf"
        ),
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--validation-only",
        action="store_true",
    )
    args = parser.parse_args()

    if (
        args.repeats < 3
        and not args.validation_only
    ):
        raise RuntimeError(
            "accepted E003 timing requires "
            "at least 3 process repeats"
        )

    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    dirty = bool(
        git("status", "--porcelain")
    )
    if branch != TARGET_BRANCH:
        raise RuntimeError(
            f"E003 must run on {TARGET_BRANCH}, "
            f"got {branch!r}"
        )
    if dirty:
        raise RuntimeError(
            "formal E003 runs require "
            "a clean checkout"
        )

    executable = (
        ROOT / args.build_dir / "phos-i001"
    ).resolve()
    scene = (
        ROOT / args.scene
    ).resolve()
    if not executable.is_file():
        raise RuntimeError(
            f"missing executable: {executable}"
        )
    if not scene.is_file():
        raise RuntimeError(
            f"missing scene: {scene}"
        )

    root = artifact_root()
    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    validation_rows: list[
        dict[str, str]
    ] = []
    for variant in VARIANTS:
        row = dict(
            run_one(
                executable,
                scene,
                variant,
                root
                / "validation"
                / variant,
                True,
            )
        )
        if not validation_rows:
            print(f"GPU: {row['device']}")
        error, tolerance = (
            accounting_error(row)
        )
        if error > tolerance:
            raise RuntimeError(
                f"{variant} validation "
                f"accounting mismatch: "
                f"{error:.6f} us > "
                f"{tolerance:.6f} us"
            )
        check_architecture_integrity(
            row,
            variant,
        )
        row["phase"] = "validation"
        row["repeat"] = "0"
        validation_rows.append(row)

    moved_counts = {
        int(row["moved_primitives"])
        for row in validation_rows
    }
    membership_counts = {
        int(
            row[
                "segment_membership_changes"
            ]
        )
        for row in validation_rows
    }
    if (
        len(moved_counts) != 1
        or len(membership_counts) != 1
    ):
        raise RuntimeError(
            "E003 variants did not exercise "
            "the same rigid workload"
        )

    validation_summary = {
        "git_branch": branch,
        "git_commit": commit,
        "git_dirty": dirty,
        "target_device": TARGET_DEVICE,
        "pairs": len(validation_rows),
        "all_quality_passed": all(
            row["quality_passed"] == "1"
            for row in validation_rows
        ),
        "all_storage_failures_zero": all(
            int(row["storage_failures"]) == 0
            for row in validation_rows
        ),
        "same_workload": True,
        "moved_primitives":
            next(iter(moved_counts)),
        "segment_membership_changes":
            next(iter(membership_counts)),
        "architecture_integrity_passed":
            True,
        "accounting_passed": True,
    }
    (
        root
        / "e003-validation-summary.json"
    ).write_text(
        json.dumps(
            validation_summary,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    if args.validation_only:
        print(
            "E003 validation-only matrix: PASS"
        )
        return 0

    timing_rows: list[
        dict[str, str]
    ] = []
    for repeat in range(
        1,
        args.repeats + 1,
    ):
        repeat_rows: list[
            dict[str, str]
        ] = []
        for variant in VARIANTS:
            row = dict(
                run_one(
                    executable,
                    scene,
                    variant,
                    root
                    / "timing"
                    / f"repeat-{repeat}"
                    / variant,
                    False,
                )
            )
            error, tolerance = (
                accounting_error(row)
            )
            if error > tolerance:
                raise RuntimeError(
                    f"{variant} repeat "
                    f"{repeat} accounting "
                    f"mismatch: "
                    f"{error:.6f} us > "
                    f"{tolerance:.6f} us"
                )
            check_architecture_integrity(
                row,
                variant,
            )
            row["phase"] = "timing"
            row["repeat"] = str(repeat)
            row["git_commit"] = commit
            repeat_rows.append(row)

        if len(
            {
                int(row["moved_primitives"])
                for row in repeat_rows
            }
        ) != 1:
            raise RuntimeError(
                f"E003 repeat {repeat} "
                "moved-primitive workload diverged"
            )
        if len(
            {
                int(
                    row[
                        "segment_membership_changes"
                    ]
                )
                for row in repeat_rows
            }
        ) != 1:
            raise RuntimeError(
                f"E003 repeat {repeat} "
                "membership workload diverged"
            )
        timing_rows.extend(repeat_rows)

    fieldnames = list(
        timing_rows[0].keys()
    )
    with (
        root / "e003-results.csv"
    ).open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(timing_rows)

    selected = {
        variant: [
            row
            for row in timing_rows
            if row["variant"] == variant
        ]
        for variant in VARIANTS
    }
    groups = {
        variant:
            summarize_group(rows)
        for variant, rows
        in selected.items()
    }

    control_boundary = (
        groups[CONTROL]["medians_us"][
            "complete_dynamic_boundary_us"
        ]
    )
    control_traversal = (
        groups[CONTROL]["medians_us"][
            "traversal_us"
        ]
    )
    control_memory = (
        groups[CONTROL]["medians_us"][
            "persistent_bytes"
        ]
    )

    candidate_boundary = (
        groups[CANDIDATE]["medians_us"][
            "complete_dynamic_boundary_us"
        ]
    )
    candidate_traversal = (
        groups[CANDIDATE]["medians_us"][
            "traversal_us"
        ]
    )
    candidate_memory = (
        groups[CANDIDATE]["medians_us"][
            "persistent_bytes"
        ]
    )

    boundary_improvement = (
        (
            control_boundary
            - candidate_boundary
        )
        / control_boundary
        if control_boundary > 0.0
        else 0.0
    )
    traversal_regression = (
        (
            candidate_traversal
            - control_traversal
        )
        / control_traversal
        if control_traversal > 0.0
        else 0.0
    )
    persistent_memory_ratio = (
        candidate_memory
        / control_memory
        if control_memory > 0.0
        else float("inf")
    )

    promotion_passed = (
        boundary_improvement
        >= BOUNDARY_IMPROVEMENT_REQUIRED
        and traversal_regression
        <= TRAVERSAL_REGRESSION_LIMIT
        and persistent_memory_ratio
        <= PERSISTENT_MEMORY_RATIO_LIMIT
    )

    binary_traversal = (
        groups[BINARY_CONTROL]["medians_us"][
            "traversal_us"
        ]
    )
    binary_memory = (
        groups[BINARY_CONTROL]["medians_us"][
            "persistent_bytes"
        ]
    )

    summary = {
        "status":
            "measurement-complete-result-review-required",
        "git_branch": branch,
        "git_commit": commit,
        "git_dirty": dirty,
        "target_device": TARGET_DEVICE,
        "scenario": SCENARIO,
        "repeats": args.repeats,
        "fixed_gates": {
            "boundary_improvement_required":
                BOUNDARY_IMPROVEMENT_REQUIRED,
            "traversal_regression_limit":
                TRAVERSAL_REGRESSION_LIMIT,
            "persistent_memory_ratio_limit":
                PERSISTENT_MEMORY_RATIO_LIMIT,
            "accounting_tolerance":
                "max(2 us, 1% of "
                "traversal_maintenance_gpu_us)",
            "candidate_geometry_transfer_gpu_us":
                0.0,
            "candidate_membership_update_cpu_us":
                0.0,
            "candidate_hierarchy_refit_cpu_us":
                0.0,
            "candidate_hierarchy_rebuild_cpu_us":
                0.0,
            "candidate_packing_cpu_us":
                0.0,
            "candidate_hierarchy_upload_gpu_us":
                0.0,
        },
        "groups": groups,
        "promotion": {
            CANDIDATE: {
                "complete_dynamic_boundary_improvement_ratio":
                    boundary_improvement,
                "traversal_regression_ratio":
                    traversal_regression,
                "persistent_memory_ratio":
                    persistent_memory_ratio,
                "promotion_gate_passed":
                    promotion_passed,
            }
        },
        "binary_mechanism_control": {
            "traversal_ratio_vs_quantized":
                (
                    binary_traversal
                    / candidate_traversal
                    if candidate_traversal > 0.0
                    else float("inf")
                ),
            "persistent_memory_ratio_vs_quantized":
                (
                    binary_memory
                    / candidate_memory
                    if candidate_memory > 0.0
                    else float("inf")
                ),
        },
        "selected_policy":
            (
                CANDIDATE
                if promotion_passed
                else None
            ),
        "next_step":
            (
                "inspect E003 result and publish "
                "the frozen-gate decision before "
                "starting E004 deforming boundary"
            ),
    }
    (
        root / "e003-summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "E003 validation and repeated timing "
        "complete; inspect artifacts before "
        "publishing result."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

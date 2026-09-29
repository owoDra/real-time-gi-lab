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
VARIANTS = ("vanilla-software", "combined-hwrt", "combined-software")
SCENARIOS = ("moving-rigid", "deforming-control")

GPU_MAINTENANCE_COMPONENTS = (
    "surface_update_gpu_us",
    "geometry_transfer_gpu_us",
    "blas_update_us",
    "tlas_update_us",
    "hierarchy_upload_gpu_us",
)
SUMMARY_FIELDS = (
    "setup_wall_us",
    "dynamic_update_wall_us",
    "geometry_prepare_cpu_us",
    "surface_update_gpu_us",
    "geometry_transfer_wall_us",
    "geometry_transfer_gpu_us",
    "blas_update_us",
    "tlas_update_us",
    "membership_update_cpu_us",
    "hierarchy_refit_cpu_us",
    "hierarchy_rebuild_cpu_us",
    "hierarchy_occupancy_cpu_us",
    "packing_cpu_us",
    "hierarchy_upload_gpu_us",
    "software_bvh_rebuild_cpu_us",
    "traversal_maintenance_gpu_us",
    "producer_us",
    "traversal_us",
    "storage_update_us",
    "invalidation_us",
    "resolve_us",
    "complete_gpu_us",
)


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
    return ROOT / "out/research/lane-e-dynamic-geometry/001-dynamic-ownership-decomposition/manual"


def run_one(
    executable: Path,
    scene: Path,
    variant: str,
    scenario: str,
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
        scenario,
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
            f"{variant}/{scenario} {'validation' if validation else 'timing'} failed "
            f"with exit code {proc.returncode}: {proc.stderr.strip()}"
        )
    if validation and "Validation Error" in proc.stderr:
        raise RuntimeError(f"{variant}/{scenario} emitted Vulkan validation errors")

    csv_path = output_dir / "i001-frame.csv"
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise RuntimeError(f"{csv_path} must contain exactly one data row")
    row = rows[0]
    if row.get("device") != TARGET_DEVICE:
        raise RuntimeError(
            f"unexpected target device for {variant}/{scenario}: {row.get('device')!r}"
        )
    if row.get("quality_passed") != "1":
        raise RuntimeError(f"{variant}/{scenario} quality gate failed")
    if int(row.get("storage_failures", "1")) != 0:
        raise RuntimeError(f"{variant}/{scenario} storage failures are non-zero")
    return row


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def accounting_error(row: dict[str, str]) -> tuple[float, float]:
    named = sum(f(row, key) for key in GPU_MAINTENANCE_COMPONENTS)
    total = f(row, "traversal_maintenance_gpu_us")
    return abs(named - total), max(2.0, abs(total) * 0.01)


def median(rows: list[dict[str, str]], key: str) -> float:
    return statistics.median(f(row, key) for row in rows)


def summarize_group(rows: list[dict[str, str]]) -> dict[str, object]:
    medians = {key: median(rows, key) for key in SUMMARY_FIELDS}
    medians["storage_pipeline_gpu_us"] = (
        medians["storage_update_us"]
        + medians["invalidation_us"]
        + medians["resolve_us"]
    )
    medians["producer_storage_gpu_us"] = (
        medians["producer_us"] + medians["storage_pipeline_gpu_us"]
    )
    medians["complete_dynamic_boundary_us"] = statistics.median(
        f(row, "dynamic_update_wall_us")
        + f(row, "complete_gpu_us")
        - f(row, "traversal_maintenance_gpu_us")
        for row in rows
    )
    maintenance = medians["traversal_maintenance_gpu_us"]
    component_ratios: dict[str, float] = {}
    if maintenance > 0.0:
        component_ratios = {
            key: medians[key] / maintenance for key in GPU_MAINTENANCE_COMPONENTS
        }
    dominant = [
        key for key, ratio in component_ratios.items() if ratio >= 0.40
    ]
    material = [
        key for key, ratio in component_ratios.items() if ratio >= 0.10
    ]
    if not dominant and maintenance > 0.0:
        dominance: object = "distributed"
    elif dominant:
        dominance = dominant[0] if len(dominant) == 1 else dominant
    else:
        dominance = "none"

    return {
        "repeat_count": len(rows),
        "medians_us": medians,
        "gpu_maintenance_component_ratios": component_ratios,
        "dominant_maintenance": dominance,
        "material_maintenance_components": material,
        "moved_primitives": int(rows[0]["moved_primitives"]),
        "segment_membership_changes": int(rows[0]["segment_membership_changes"]),
        "hierarchy_refit_segments_median": statistics.median(
            int(row["hierarchy_refit_segments"]) for row in rows
        ),
        "hierarchy_rebuilt_segments_median": statistics.median(
            int(row["hierarchy_rebuilt_segments"]) for row in rows
        ),
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
        raise RuntimeError("accepted E001 timing requires at least 3 process repeats")

    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    if branch != TARGET_BRANCH:
        raise RuntimeError(f"E001 must run on {TARGET_BRANCH}, got {branch!r}")
    if dirty:
        raise RuntimeError("formal E001 runs require a clean checkout")

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
        for scenario in SCENARIOS:
            row = run_one(
                executable,
                scene,
                variant,
                scenario,
                root / "validation" / f"{variant}-{scenario}",
                True,
            )
            row = dict(row)
            if not validation_rows:
                print(f"GPU: {row['device']}")
            row["phase"] = "validation"
            row["repeat"] = "0"
            validation_rows.append(row)

    validation_summary = {
        "git_branch": branch,
        "git_commit": commit,
        "git_dirty": dirty,
        "target_device": TARGET_DEVICE,
        "pairs": len(validation_rows),
        "all_quality_passed": all(row["quality_passed"] == "1" for row in validation_rows),
        "all_storage_failures_zero": all(
            int(row["storage_failures"]) == 0 for row in validation_rows
        ),
    }
    (root / "e001-validation-summary.json").write_text(
        json.dumps(validation_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if args.validation_only:
        print("E001 validation-only matrix: PASS")
        return 0

    timing_rows: list[dict[str, str]] = []
    for repeat in range(1, args.repeats + 1):
        for variant in VARIANTS:
            for scenario in SCENARIOS:
                row = run_one(
                    executable,
                    scene,
                    variant,
                    scenario,
                    root / "timing" / f"repeat-{repeat}" / f"{variant}-{scenario}",
                    False,
                )
                error, tolerance = accounting_error(row)
                if error > tolerance:
                    raise RuntimeError(
                        f"{variant}/{scenario} repeat {repeat} accounting mismatch: "
                        f"{error:.6f} us > {tolerance:.6f} us"
                    )
                row = dict(row)
                row["phase"] = "timing"
                row["repeat"] = str(repeat)
                row["git_commit"] = commit
                timing_rows.append(row)

    fieldnames = list(timing_rows[0].keys())
    with (root / "e001-results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(timing_rows)

    groups: dict[str, object] = {}
    for variant in VARIANTS:
        for scenario in SCENARIOS:
            selected = [
                row
                for row in timing_rows
                if row["variant"] == variant and row["scenario"] == scenario
            ]
            groups[f"{variant}/{scenario}"] = summarize_group(selected)

    summary = {
        "status": "measurement-complete-result-review-required",
        "git_branch": branch,
        "git_commit": commit,
        "git_dirty": dirty,
        "target_device": TARGET_DEVICE,
        "repeats": args.repeats,
        "fixed_gates": {
            "validation_pairs_must_pass": True,
            "accounting_tolerance": "max(2 us, 1% of traversal_maintenance_gpu_us)",
            "dominant_component_ratio": 0.40,
            "material_component_ratio": 0.10,
        },
        "groups": groups,
        "next_step": (
            "inspect rigid and deforming groups separately, publish E001 result, "
            "then select the measured ownership bottleneck for E002/E003"
        ),
    }
    (root / "e001-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("E001 validation and repeated timing complete; inspect artifacts before publishing result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

HWRT_CONTROL = "combined-hwrt"
HWRT_CANDIDATE = "lane-e-final-hwrt"
SOFTWARE_CONTROL = "combined-software"
SOFTWARE_CANDIDATE = "lane-e-final-software"
VARIANTS = (
    HWRT_CONTROL,
    HWRT_CANDIDATE,
    SOFTWARE_CONTROL,
    SOFTWARE_CANDIDATE,
)
SCENARIOS = (
    "static",
    "camera-motion",
    "light-motion",
    "moving-rigid",
    "deforming-control",
)
STABLE_SCENARIOS = (
    "static",
    "camera-motion",
    "light-motion",
)

STABLE_HWRT_COMPLETE_REGRESSION_LIMIT = 0.10
STABLE_SOFTWARE_COMPLETE_REGRESSION_LIMIT = 0.15
RIGID_HWRT_BOUNDARY_IMPROVEMENT_REQUIRED = 0.20
RIGID_HWRT_TRAVERSAL_REGRESSION_LIMIT = 0.10
RIGID_SOFTWARE_BOUNDARY_IMPROVEMENT_REQUIRED = 0.50
RIGID_SOFTWARE_TRAVERSAL_REGRESSION_LIMIT = 0.15
DEFORMING_HWRT_BOUNDARY_IMPROVEMENT_REQUIRED = 0.05
DEFORMING_HWRT_TRAVERSAL_REGRESSION_LIMIT = 0.10
DEFORMING_SOFTWARE_BOUNDARY_IMPROVEMENT_REQUIRED = 0.40
DEFORMING_SOFTWARE_TRAVERSAL_REGRESSION_LIMIT = 0.15
MEMORY_RATIO_LIMIT = 1.25

SUMMARY_FIELDS = (
    "setup_wall_us",
    "dynamic_update_wall_us",
    "geometry_prepare_cpu_us",
    "surface_update_gpu_us",
    "geometry_transfer_wall_us",
    "geometry_transfer_gpu_us",
    "instance_transfer_wall_us",
    "instance_transfer_gpu_us",
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
    "persistent_bytes",
    "transient_bytes",
    "scratch_bytes",
    "peak_resident_bytes",
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
        / "005-integration-replay/manual"
    )


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


def run_one(
    executable: Path,
    scene: Path,
    scenario: str,
    variant: str,
    output_dir: Path,
    validation: bool,
) -> dict[str, str]:
    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )
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
    (output_dir / "stdout.txt").write_text(
        proc.stdout,
        encoding="utf-8",
    )
    (output_dir / "stderr.txt").write_text(
        proc.stderr,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"{scenario}/{variant} "
            f"{'validation' if validation else 'timing'} "
            f"failed with exit code {proc.returncode}: "
            f"{proc.stderr.strip()}"
        )
    if validation and "Validation Error" in proc.stderr:
        raise RuntimeError(
            f"{scenario}/{variant} emitted Vulkan validation errors"
        )

    csv_path = output_dir / "i001-frame.csv"
    with csv_path.open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise RuntimeError(
            f"{csv_path} must contain exactly one data row"
        )
    row = rows[0]
    if row.get("device") != TARGET_DEVICE:
        raise RuntimeError(
            f"unexpected target device for "
            f"{scenario}/{variant}: {row.get('device')!r}"
        )
    if row.get("scenario") != scenario:
        raise RuntimeError(
            f"{variant} did not run {scenario}"
        )
    if row.get("variant") != variant:
        raise RuntimeError(
            f"{scenario} returned unexpected variant "
            f"{row.get('variant')!r}"
        )
    if row.get("quality_passed") != "1":
        raise RuntimeError(
            f"{scenario}/{variant} quality gate failed"
        )
    if int(row.get("storage_failures", "1")) != 0:
        raise RuntimeError(
            f"{scenario}/{variant} storage failures are non-zero"
        )
    return row


def accounting_fields(
    scenario: str,
    variant: str,
) -> tuple[str, ...]:
    if scenario in STABLE_SCENARIOS:
        return ()
    if scenario == "moving-rigid":
        if variant == HWRT_CANDIDATE:
            return (
                "surface_update_gpu_us",
                "instance_transfer_gpu_us",
                "tlas_update_us",
            )
        if variant == SOFTWARE_CANDIDATE:
            return (
                "surface_update_gpu_us",
                "instance_transfer_gpu_us",
            )
    if scenario == "deforming-control":
        if variant == HWRT_CANDIDATE:
            return (
                "surface_update_gpu_us",
                "geometry_transfer_gpu_us",
                "blas_update_us",
                "tlas_update_us",
            )
        if variant == SOFTWARE_CANDIDATE:
            return (
                "surface_update_gpu_us",
                "geometry_transfer_gpu_us",
                "instance_transfer_gpu_us",
                "hierarchy_upload_gpu_us",
            )

    if variant == HWRT_CONTROL:
        return (
            "surface_update_gpu_us",
            "geometry_transfer_gpu_us",
            "blas_update_us",
            "tlas_update_us",
        )
    if variant == SOFTWARE_CONTROL:
        return (
            "surface_update_gpu_us",
            "geometry_transfer_gpu_us",
            "hierarchy_upload_gpu_us",
        )
    raise RuntimeError(
        f"no E005 accounting rule for {scenario}/{variant}"
    )


def check_accounting(
    row: dict[str, str],
    scenario: str,
    variant: str,
) -> None:
    total = f(
        row,
        "traversal_maintenance_gpu_us",
    )
    fields = accounting_fields(
        scenario,
        variant,
    )
    if not fields:
        if total != 0.0:
            raise RuntimeError(
                f"{scenario}/{variant} performed stable-frame "
                f"dynamic maintenance: {total} us"
            )
        return

    named = sum(
        f(row, key) for key in fields
    )
    tolerance = max(
        2.0,
        abs(total) * 0.01,
    )
    error = abs(named - total)
    if error > tolerance:
        raise RuntimeError(
            f"{scenario}/{variant} accounting mismatch: "
            f"{error:.6f} us > {tolerance:.6f} us"
        )


def require_zero(
    row: dict[str, str],
    scenario: str,
    variant: str,
    fields: tuple[str, ...],
) -> None:
    for key in fields:
        if f(row, key) != 0.0:
            raise RuntimeError(
                f"{scenario}/{variant} expected {key}=0, "
                f"got {row[key]}"
            )


def check_architecture_integrity(
    row: dict[str, str],
    scenario: str,
    variant: str,
) -> None:
    if variant not in (
        HWRT_CANDIDATE,
        SOFTWARE_CANDIDATE,
    ):
        return

    if scenario in STABLE_SCENARIOS:
        require_zero(
            row,
            scenario,
            variant,
            (
                "traversal_maintenance_gpu_us",
                "dynamic_update_wall_us",
                "geometry_prepare_cpu_us",
                "surface_update_gpu_us",
                "geometry_transfer_wall_us",
                "geometry_transfer_gpu_us",
                "instance_transfer_wall_us",
                "instance_transfer_gpu_us",
                "blas_update_us",
                "tlas_update_us",
                "membership_update_cpu_us",
                "hierarchy_refit_cpu_us",
                "hierarchy_rebuild_cpu_us",
                "packing_cpu_us",
                "hierarchy_upload_gpu_us",
                "software_bvh_rebuild_cpu_us",
            ),
        )
        return

    if scenario == "moving-rigid":
        if variant == HWRT_CANDIDATE:
            require_zero(
                row,
                scenario,
                variant,
                (
                    "geometry_transfer_gpu_us",
                    "blas_update_us",
                    "membership_update_cpu_us",
                    "hierarchy_refit_cpu_us",
                    "hierarchy_rebuild_cpu_us",
                    "packing_cpu_us",
                    "hierarchy_upload_gpu_us",
                ),
            )
            if f(row, "instance_transfer_gpu_us") <= 0.0:
                raise RuntimeError(
                    "E005 rigid HWRT did not upload instance state"
                )
            if f(row, "tlas_update_us") <= 0.0:
                raise RuntimeError(
                    "E005 rigid HWRT did not update TLAS"
                )
        else:
            require_zero(
                row,
                scenario,
                variant,
                (
                    "geometry_transfer_gpu_us",
                    "membership_update_cpu_us",
                    "hierarchy_refit_cpu_us",
                    "hierarchy_rebuild_cpu_us",
                    "packing_cpu_us",
                    "hierarchy_upload_gpu_us",
                    "blas_update_us",
                    "tlas_update_us",
                ),
            )
            if f(row, "instance_transfer_gpu_us") <= 0.0:
                raise RuntimeError(
                    "E005 rigid software did not upload instance state"
                )
        return

    if scenario == "deforming-control":
        if variant == HWRT_CANDIDATE:
            if f(row, "geometry_transfer_gpu_us") <= 0.0:
                raise RuntimeError(
                    "E005 deforming HWRT did not upload local geometry"
                )
            if f(row, "blas_update_us") <= 0.0:
                raise RuntimeError(
                    "E005 deforming HWRT did not update local BLAS"
                )
            if f(row, "tlas_update_us") <= 0.0:
                raise RuntimeError(
                    "E005 deforming HWRT did not update TLAS"
                )
        else:
            if f(row, "geometry_transfer_gpu_us") <= 0.0:
                raise RuntimeError(
                    "E005 deforming software did not upload local geometry"
                )
            if f(row, "hierarchy_upload_gpu_us") <= 0.0:
                raise RuntimeError(
                    "E005 deforming software did not upload local hierarchy"
                )
            if f(row, "instance_transfer_gpu_us") <= 0.0:
                raise RuntimeError(
                    "E005 deforming software did not update instance bounds"
                )
            if (
                f(row, "membership_update_cpu_us") <= 0.0
                and f(row, "hierarchy_refit_cpu_us") <= 0.0
                and f(row, "hierarchy_rebuild_cpu_us") <= 0.0
            ):
                raise RuntimeError(
                    "E005 deforming software did not maintain local hierarchy"
                )
        return

    raise RuntimeError(
        f"unsupported E005 scenario: {scenario}"
    )


def assert_same_workload(
    rows: list[dict[str, str]],
    scenario: str,
) -> None:
    exact_fields = (
        "work_items",
        "outputs",
        "requested_work_items",
        "requested_outputs",
        "visible_owners",
        "moved_primitives",
        "segment_membership_changes",
    )
    for key in exact_fields:
        values = {row[key] for row in rows}
        if len(values) != 1:
            raise RuntimeError(
                f"E005 {scenario} workload diverged for {key}: "
                f"{sorted(values)}"
            )


def summarize_group(
    rows: list[dict[str, str]],
) -> dict[str, object]:
    medians = {
        key: median(rows, key)
        for key in SUMMARY_FIELDS
    }
    if rows[0]["scenario"] in (
        "moving-rigid",
        "deforming-control",
    ):
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
        "medians": medians,
    }


def ratio_regression(
    candidate: float,
    control: float,
) -> float:
    if control <= 0.0:
        return float("inf")
    return (
        candidate - control
    ) / control


def ratio_improvement(
    candidate: float,
    control: float,
) -> float:
    if control <= 0.0:
        return 0.0
    return (
        control - candidate
    ) / control


def memory_gate(
    candidate: dict[str, float],
    control: dict[str, float],
) -> dict[str, object]:
    persistent = (
        candidate["persistent_bytes"]
        / control["persistent_bytes"]
        if control["persistent_bytes"] > 0.0
        else float("inf")
    )
    peak = (
        candidate["peak_resident_bytes"]
        / control["peak_resident_bytes"]
        if control["peak_resident_bytes"] > 0.0
        else float("inf")
    )
    return {
        "persistent_ratio": persistent,
        "peak_resident_ratio": peak,
        "passed": (
            persistent <= MEMORY_RATIO_LIMIT
            and peak <= MEMORY_RATIO_LIMIT
        ),
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
            "accepted E005 timing requires at least 3 process repeats"
        )

    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    dirty = bool(
        git("status", "--porcelain")
    )
    if branch != TARGET_BRANCH:
        raise RuntimeError(
            f"E005 must run on {TARGET_BRANCH}, got {branch!r}"
        )
    if dirty:
        raise RuntimeError(
            "formal E005 runs require a clean checkout"
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
    for scenario in SCENARIOS:
        scenario_rows: list[
            dict[str, str]
        ] = []
        for variant in VARIANTS:
            row = dict(
                run_one(
                    executable,
                    scene,
                    scenario,
                    variant,
                    root
                    / "validation"
                    / scenario
                    / variant,
                    True,
                )
            )
            if not validation_rows:
                print(f"GPU: {row['device']}")
            check_accounting(
                row,
                scenario,
                variant,
            )
            check_architecture_integrity(
                row,
                scenario,
                variant,
            )
            row["phase"] = "validation"
            row["repeat"] = "0"
            scenario_rows.append(row)
            validation_rows.append(row)
        assert_same_workload(
            scenario_rows,
            scenario,
        )

    validation_summary = {
        "git_branch": branch,
        "git_commit": commit,
        "git_dirty": dirty,
        "target_device": TARGET_DEVICE,
        "pairs": len(validation_rows),
        "scenarios": list(SCENARIOS),
        "all_quality_passed": all(
            row["quality_passed"] == "1"
            for row in validation_rows
        ),
        "all_storage_failures_zero": all(
            int(row["storage_failures"]) == 0
            for row in validation_rows
        ),
        "same_workload": True,
        "architecture_integrity_passed": True,
        "accounting_passed": True,
    }
    (
        root
        / "e005-validation-summary.json"
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
            "E005 validation-only matrix: PASS"
        )
        return 0

    timing_rows: list[
        dict[str, str]
    ] = []
    for repeat in range(
        1,
        args.repeats + 1,
    ):
        for scenario in SCENARIOS:
            scenario_rows: list[
                dict[str, str]
            ] = []
            for variant in VARIANTS:
                row = dict(
                    run_one(
                        executable,
                        scene,
                        scenario,
                        variant,
                        root
                        / "timing"
                        / f"repeat-{repeat}"
                        / scenario
                        / variant,
                        False,
                    )
                )
                check_accounting(
                    row,
                    scenario,
                    variant,
                )
                check_architecture_integrity(
                    row,
                    scenario,
                    variant,
                )
                row["phase"] = "timing"
                row["repeat"] = str(repeat)
                row["git_commit"] = commit
                scenario_rows.append(row)
                timing_rows.append(row)
            assert_same_workload(
                scenario_rows,
                scenario,
            )

    fieldnames = list(
        timing_rows[0].keys()
    )
    with (
        root / "e005-results.csv"
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

    grouped: dict[
        tuple[str, str],
        list[dict[str, str]],
    ] = {}
    for scenario in SCENARIOS:
        for variant in VARIANTS:
            grouped[(scenario, variant)] = [
                row
                for row in timing_rows
                if row["scenario"] == scenario
                and row["variant"] == variant
            ]

    groups = {
        scenario: {
            variant:
                summarize_group(
                    grouped[(scenario, variant)]
                )
            for variant in VARIANTS
        }
        for scenario in SCENARIOS
    }

    stable_gates: dict[str, object] = {}
    memory_gates: dict[str, object] = {}
    hwrt_all = True
    software_all = True

    for scenario in STABLE_SCENARIOS:
        h_control = groups[scenario][HWRT_CONTROL]["medians"]
        h_candidate = groups[scenario][HWRT_CANDIDATE]["medians"]
        s_control = groups[scenario][SOFTWARE_CONTROL]["medians"]
        s_candidate = groups[scenario][SOFTWARE_CANDIDATE]["medians"]

        h_regression = ratio_regression(
            h_candidate["complete_gpu_us"],
            h_control["complete_gpu_us"],
        )
        s_regression = ratio_regression(
            s_candidate["complete_gpu_us"],
            s_control["complete_gpu_us"],
        )
        h_pass = (
            h_regression
            <= STABLE_HWRT_COMPLETE_REGRESSION_LIMIT
        )
        s_pass = (
            s_regression
            <= STABLE_SOFTWARE_COMPLETE_REGRESSION_LIMIT
        )
        stable_gates[scenario] = {
            "hwrt_complete_gpu_regression_ratio":
                h_regression,
            "hwrt_passed": h_pass,
            "software_complete_gpu_regression_ratio":
                s_regression,
            "software_passed": s_pass,
        }
        hwrt_all = hwrt_all and h_pass
        software_all = software_all and s_pass

    dynamic_gates: dict[str, object] = {}
    dynamic_specs = {
        "moving-rigid": {
            "hwrt_boundary":
                RIGID_HWRT_BOUNDARY_IMPROVEMENT_REQUIRED,
            "hwrt_traversal":
                RIGID_HWRT_TRAVERSAL_REGRESSION_LIMIT,
            "software_boundary":
                RIGID_SOFTWARE_BOUNDARY_IMPROVEMENT_REQUIRED,
            "software_traversal":
                RIGID_SOFTWARE_TRAVERSAL_REGRESSION_LIMIT,
        },
        "deforming-control": {
            "hwrt_boundary":
                DEFORMING_HWRT_BOUNDARY_IMPROVEMENT_REQUIRED,
            "hwrt_traversal":
                DEFORMING_HWRT_TRAVERSAL_REGRESSION_LIMIT,
            "software_boundary":
                DEFORMING_SOFTWARE_BOUNDARY_IMPROVEMENT_REQUIRED,
            "software_traversal":
                DEFORMING_SOFTWARE_TRAVERSAL_REGRESSION_LIMIT,
        },
    }
    for scenario, spec in dynamic_specs.items():
        h_control = groups[scenario][HWRT_CONTROL]["medians"]
        h_candidate = groups[scenario][HWRT_CANDIDATE]["medians"]
        s_control = groups[scenario][SOFTWARE_CONTROL]["medians"]
        s_candidate = groups[scenario][SOFTWARE_CANDIDATE]["medians"]

        h_boundary = ratio_improvement(
            h_candidate["complete_dynamic_boundary_us"],
            h_control["complete_dynamic_boundary_us"],
        )
        h_traversal = ratio_regression(
            h_candidate["traversal_us"],
            h_control["traversal_us"],
        )
        s_boundary = ratio_improvement(
            s_candidate["complete_dynamic_boundary_us"],
            s_control["complete_dynamic_boundary_us"],
        )
        s_traversal = ratio_regression(
            s_candidate["traversal_us"],
            s_control["traversal_us"],
        )

        h_pass = (
            h_boundary >= spec["hwrt_boundary"]
            and h_traversal <= spec["hwrt_traversal"]
        )
        s_pass = (
            s_boundary >= spec["software_boundary"]
            and s_traversal <= spec["software_traversal"]
        )
        dynamic_gates[scenario] = {
            "hwrt_boundary_improvement_ratio":
                h_boundary,
            "hwrt_traversal_regression_ratio":
                h_traversal,
            "hwrt_passed": h_pass,
            "software_boundary_improvement_ratio":
                s_boundary,
            "software_traversal_regression_ratio":
                s_traversal,
            "software_passed": s_pass,
        }
        hwrt_all = hwrt_all and h_pass
        software_all = software_all and s_pass

    for scenario in SCENARIOS:
        h_control = groups[scenario][HWRT_CONTROL]["medians"]
        h_candidate = groups[scenario][HWRT_CANDIDATE]["medians"]
        s_control = groups[scenario][SOFTWARE_CONTROL]["medians"]
        s_candidate = groups[scenario][SOFTWARE_CANDIDATE]["medians"]
        h_memory = memory_gate(
            h_candidate,
            h_control,
        )
        s_memory = memory_gate(
            s_candidate,
            s_control,
        )
        memory_gates[scenario] = {
            "hwrt": h_memory,
            "software": s_memory,
        }
        hwrt_all = hwrt_all and bool(
            h_memory["passed"]
        )
        software_all = software_all and bool(
            s_memory["passed"]
        )

    summary = {
        "status":
            "measurement-complete-result-review-required",
        "git_branch": branch,
        "git_commit": commit,
        "git_dirty": dirty,
        "target_device": TARGET_DEVICE,
        "repeats": args.repeats,
        "scenarios": list(SCENARIOS),
        "fixed_gates": {
            "stable_hwrt_complete_regression_limit":
                STABLE_HWRT_COMPLETE_REGRESSION_LIMIT,
            "stable_software_complete_regression_limit":
                STABLE_SOFTWARE_COMPLETE_REGRESSION_LIMIT,
            "rigid_hwrt_boundary_improvement_required":
                RIGID_HWRT_BOUNDARY_IMPROVEMENT_REQUIRED,
            "rigid_hwrt_traversal_regression_limit":
                RIGID_HWRT_TRAVERSAL_REGRESSION_LIMIT,
            "rigid_software_boundary_improvement_required":
                RIGID_SOFTWARE_BOUNDARY_IMPROVEMENT_REQUIRED,
            "rigid_software_traversal_regression_limit":
                RIGID_SOFTWARE_TRAVERSAL_REGRESSION_LIMIT,
            "deforming_hwrt_boundary_improvement_required":
                DEFORMING_HWRT_BOUNDARY_IMPROVEMENT_REQUIRED,
            "deforming_hwrt_traversal_regression_limit":
                DEFORMING_HWRT_TRAVERSAL_REGRESSION_LIMIT,
            "deforming_software_boundary_improvement_required":
                DEFORMING_SOFTWARE_BOUNDARY_IMPROVEMENT_REQUIRED,
            "deforming_software_traversal_regression_limit":
                DEFORMING_SOFTWARE_TRAVERSAL_REGRESSION_LIMIT,
            "persistent_and_peak_memory_ratio_limit":
                MEMORY_RATIO_LIMIT,
            "accounting_tolerance":
                "max(2 us, 1% of traversal_maintenance_gpu_us)",
        },
        "groups": groups,
        "stable_gates": stable_gates,
        "dynamic_gates": dynamic_gates,
        "memory_gates": memory_gates,
        "final_hwrt_accepted": hwrt_all,
        "final_software_accepted": software_all,
        "topology_changing_disposition":
            "object-local rebuild boundary; no topology-changing timing claim",
        "next_step":
            "publish final Lane E architecture decision and close Issue #15 if accepted gates remain satisfied",
    }
    (
        root / "e005-summary.json"
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
        "E005 validation and repeated timing complete; "
        "inspect artifacts before publishing the final Lane E result."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

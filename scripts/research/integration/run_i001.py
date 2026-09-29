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
STRESS_VARIANTS = (
    "vanilla-software",
    "combined-hwrt",
    "combined-software",
)
STRESS_SCENARIOS = (
    "sparse-stress",
    "dense-stress",
    "large-world-stress",
    "vertical-world-stress",
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

    combined_log = proc.stdout + "\n" + proc.stderr
    validation_error_markers = (
        "Validation Error",
        "[Vulkan Validation] ERROR",
        "VUID-",
    )
    validation_error_count = (
        sum(combined_log.count(marker) for marker in validation_error_markers)
        if validation
        else 0
    )

    csv_path = output_dir / "i001-frame.csv"
    rows: list[dict[str, str]] = []
    if csv_path.is_file():
        with csv_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

    if proc.returncode != 0:
        detail = ""
        if len(rows) == 1:
            row = rows[0]
            quality_fields = (
                "visibility_mismatches",
                "producer_semantic_errors",
                "hit_mismatches",
                "traversal_runtime_errors",
                "missing_probes",
                "leaked_probes",
                "stale_storage_slots",
                "resolved_output_mismatches",
                "radiance_rms_error",
                "radiance_max_abs_error",
                "temporal_rms_error",
                "temporal_max_abs_error",
                "storage_failures",
                "overflow",
            )
            detail = ", ".join(
                f"{field}={row.get(field, 'missing')}"
                for field in quality_fields
            )
        elif "I001 quality diagnostics [" in proc.stderr:
            diagnostic_lines = [
                line.strip()
                for line in proc.stderr.splitlines()
                if line.startswith("I001 quality diagnostics [")
            ]
            if diagnostic_lines:
                detail = diagnostic_lines[-1]
        raise RuntimeError(
            f"I001 {variant}/{scenario} "
            f"{'validation' if validation else 'timing'} failed with "
            f"{proc.returncode}"
            + (f": {detail}" if detail else "")
        )

    if validation_error_count != 0:
        raise RuntimeError(
            f"I001 Vulkan validation emitted {validation_error_count} "
            f"error marker(s) for {variant}/{scenario}"
        )

    if not csv_path.is_file():
        raise RuntimeError(f"missing I001 artifact after successful run: {csv_path}")
    if len(rows) != 1:
        raise RuntimeError(f"{csv_path} must contain exactly one data row")
    row = rows[0]
    row["validation_errors"] = str(validation_error_count)
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
    parser.add_argument(
        "--validation-only",
        action="store_true",
        help="Run the complete diagnostic validation matrix and stop before timing.",
    )
    args = parser.parse_args()

    if args.validation_only and args.skip_validation:
        parser.error("--validation-only cannot be combined with --skip-validation")

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
        validation_failures: list[str] = []

        def validate_case(
            variant: str,
            scenario: str,
            output_dir: Path,
            bounded_owner_capacity: int,
        ) -> dict[str, str] | None:
            try:
                return run_one(
                    executable,
                    scene,
                    variant,
                    scenario,
                    output_dir,
                    True,
                    bounded_owner_capacity,
                )
            except Exception as error:
                validation_failures.append(
                    f"{variant}/{scenario}"
                    f" (capacity={bounded_owner_capacity}): {error}"
                )
                return None

        for variant in VARIANTS:
            for scenario in SCENARIOS:
                validate_case(
                    variant,
                    scenario,
                    root / "validation" / variant / scenario,
                    1280,
                )
        for variant in STRESS_VARIANTS:
            for scenario in STRESS_SCENARIOS:
                validate_case(
                    variant,
                    scenario,
                    root / "validation-stress" / variant / scenario,
                    1280,
                )

        overflow_validation = validate_case(
            "bounded-hwrt",
            "static",
            root / "validation-overflow" / "bounded-512",
            512,
        )
        if (
            overflow_validation is not None
            and int(overflow_validation["overflow"]) != 1
        ):
            validation_failures.append(
                "bounded-hwrt/static (capacity=512): "
                "validation run did not force overflow"
            )

        if validation_failures:
            raise RuntimeError(
                "I001 validation matrix failed:\n  - "
                + "\n  - ".join(validation_failures)
            )

        if args.validation_only:
            print("I001 complete validation matrix: PASS")
            return 0

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

    stress_rows: list[dict[str, str]] = []
    for repeat in range(args.repeats):
        for variant in STRESS_VARIANTS:
            for scenario in STRESS_SCENARIOS:
                row = run_one(
                    executable,
                    scene,
                    variant,
                    scenario,
                    root / "stress" / f"repeat-{repeat + 1}" / variant / scenario,
                    False,
                    1280,
                )
                row = dict(row)
                row["repeat"] = str(repeat + 1)
                row["git_commit"] = commit
                stress_rows.append(row)

    columns = ["git_commit", "repeat", *accepted[0].keys()]
    # git_commit/repeat were appended after the binary's native columns.
    columns = list(dict.fromkeys(columns))
    with (root / "i001-representative.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(accepted)

    stress_columns = ["git_commit", "repeat", *stress_rows[0].keys()]
    stress_columns = list(dict.fromkeys(stress_columns))
    with (root / "i001-stress.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=stress_columns)
        writer.writeheader()
        writer.writerows(stress_rows)

    medians: dict[str, dict[str, dict[str, float]]] = {}
    for variant in VARIANTS:
        medians[variant] = {}
        for scenario in SCENARIOS:
            rows = [
                row for row in accepted
                if row["variant"] == variant and row["scenario"] == scenario
            ]
            medians[variant][scenario] = {
                "setup_wall_us": statistics.median(
                    float(row["setup_wall_us"]) for row in rows
                ),
                "complete_gpu_us": statistics.median(
                    float(row["complete_gpu_us"]) for row in rows
                ),
                "incremental_gi_us": statistics.median(
                    float(row["incremental_gi_us"]) for row in rows
                ),
                "peak_resident_bytes": statistics.median(
                    int(row["peak_resident_bytes"]) for row in rows
                ),
                "stream_capacity_bytes": statistics.median(
                    int(row["stream_capacity_bytes"]) for row in rows
                ),
                "dynamic_update_wall_us": statistics.median(
                    float(row["dynamic_update_wall_us"]) for row in rows
                ),
                "traversal_maintenance_gpu_us": statistics.median(
                    float(row["traversal_maintenance_gpu_us"]) for row in rows
                ),
            }

    stress_medians: dict[str, dict[str, dict[str, float]]] = {}
    for variant in STRESS_VARIANTS:
        stress_medians[variant] = {}
        for scenario in STRESS_SCENARIOS:
            rows = [
                row for row in stress_rows
                if row["variant"] == variant and row["scenario"] == scenario
            ]
            stress_medians[variant][scenario] = {
                "setup_wall_us": statistics.median(
                    float(row["setup_wall_us"]) for row in rows
                ),
                "complete_gpu_us": statistics.median(
                    float(row["complete_gpu_us"]) for row in rows
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
            "failed_attempt_setup_wall_us":
                float(failed["setup_wall_us"]),
            "retry_setup_wall_us":
                float(retry["setup_wall_us"]),
            "total_retry_setup_wall_us":
                float(failed["setup_wall_us"]) +
                float(retry["setup_wall_us"]),
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

    representative_primary_pass = all(
        medians["combined-hwrt"][scenario]["complete_gpu_us"] <=
        0.90 * medians["vanilla-software"][scenario]["complete_gpu_us"]
        for scenario in SCENARIOS
    )
    primary_stress_pass = all(
        stress_medians["combined-hwrt"][scenario]["complete_gpu_us"] <=
        1.05 * stress_medians["vanilla-software"][scenario]["complete_gpu_us"]
        for scenario in STRESS_SCENARIOS
    )
    primary_memory_ratio = max(
        medians["combined-hwrt"][scenario]["peak_resident_bytes"] /
        medians["vanilla-software"][scenario]["peak_resident_bytes"]
        for scenario in SCENARIOS
    )

    fallback_representative_ratio = statistics.mean(
        medians["combined-software"][scenario]["complete_gpu_us"]
        for scenario in SCENARIOS
    ) / statistics.mean(
        medians["vanilla-software"][scenario]["complete_gpu_us"]
        for scenario in SCENARIOS
    )
    fallback_memory_ratio = max(
        medians["combined-software"][scenario]["peak_resident_bytes"] /
        medians["vanilla-software"][scenario]["peak_resident_bytes"]
        for scenario in SCENARIOS
    )
    vanilla_moving_update = medians["vanilla-software"]["moving-rigid"][
        "dynamic_update_wall_us"
    ]
    fallback_moving_update = medians["combined-software"]["moving-rigid"][
        "dynamic_update_wall_us"
    ]
    fallback_moving_pass = (
        vanilla_moving_update > 0.0 and
        fallback_moving_update <= 1.05 * vanilla_moving_update
    )

    depth_reuse_pass = all(
        medians["depth-reuse-hwrt"][scenario]["incremental_gi_us"] <=
        0.90 * medians["combined-hwrt"][scenario]["incremental_gi_us"]
        for scenario in SCENARIOS
    )

    bounded_memory_ratio = max(
        medians["bounded-hwrt"][scenario]["stream_capacity_bytes"] /
        medians["combined-hwrt"][scenario]["stream_capacity_bytes"]
        for scenario in SCENARIOS
    )
    bounded_normal_no_overflow = all(
        int(row["overflow"]) == 0
        for row in accepted
        if row["variant"] == "bounded-hwrt"
    )
    bounded_timing_pass = (
        bounded_normal_no_overflow and
        all(
            medians["bounded-hwrt"][scenario]["complete_gpu_us"] <=
            1.05 * medians["combined-hwrt"][scenario]["complete_gpu_us"]
            for scenario in SCENARIOS
        )
    )
    overflow_retry_pass = all(
        row["retry_quality_passed"] == 1 for row in overflow_rows
    )

    summary = {
        "schema_version": 1,
        "status": "target-run-complete",
        "branch": branch,
        "git_commit": commit,
        "dirty": dirty,
        "repeats": args.repeats,
        "validation_run": not args.skip_validation,
        "scene": str(scene),
        "variants": list(VARIANTS),
        "scenarios": list(SCENARIOS),
        "stress_scenarios": list(STRESS_SCENARIOS),
        "medians": medians,
        "stress_medians": stress_medians,
        "fixed_gates": {
            "target_gpu_primary": {
                "representative_timing_pass": representative_primary_pass,
                "stress_timing_pass": primary_stress_pass,
                "peak_memory_ratio": primary_memory_ratio,
                "memory_le_3x_pass": primary_memory_ratio <= 3.0,
                "unqualified_memory_le_1_5x":
                    primary_memory_ratio <= 1.5,
                "pass":
                    representative_primary_pass and
                    primary_stress_pass and
                    primary_memory_ratio <= 3.0,
            },
            "software_fallback": {
                "representative_timing_ratio":
                    fallback_representative_ratio,
                "representative_timing_pass":
                    fallback_representative_ratio <= 0.90,
                "peak_memory_ratio": fallback_memory_ratio,
                "memory_pass": fallback_memory_ratio <= 1.15,
                "moving_update_pass": fallback_moving_pass,
                "pass":
                    fallback_representative_ratio <= 0.90 and
                    fallback_memory_ratio <= 1.15 and
                    fallback_moving_pass,
            },
            "renderer_depth_reuse": {
                "pass": depth_reuse_pass,
            },
            "bounded_capacity": {
                "stream_memory_ratio": bounded_memory_ratio,
                "memory_pass": bounded_memory_ratio <= 0.60,
                "normal_no_overflow_pass": bounded_normal_no_overflow,
                "normal_timing_pass": bounded_timing_pass,
                "overflow_retry_pass": overflow_retry_pass,
                "pass":
                    bounded_memory_ratio <= 0.60 and
                    bounded_normal_no_overflow and
                    bounded_timing_pass and
                    overflow_retry_pass,
            },
        },
        "overflow_retry": {
            "bounded_owner_capacity": 512,
            "median_total_retry_setup_wall_us": statistics.median(
                row["total_retry_setup_wall_us"] for row in overflow_rows
            ),
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
            "artifact inspection",
            "final result publication",
        ],
    }
    (root / "i001-representative-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "I001 full target matrix complete; inspect fixed gates and publish result."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

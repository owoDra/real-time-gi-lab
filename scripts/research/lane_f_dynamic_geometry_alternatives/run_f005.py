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
PLAN_VERSION = "lane-f-plan-v1"
EXPECTED_BRANCH = "research-lane-f-dynamic-geometry-alternatives"
EXPECTED_GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
EXPERIMENT = "005-end-to-end-sorted-two-level-grid"
CONFIG = (
    ROOT / "research/lanes/lane-f-dynamic-geometry-alternatives/experiments"
    / "005-end-to-end-sorted-two-level-grid-config.json"
)
VARIANTS = ("transient-grid", "vanilla-software", "combined-hwrt", "combined-software")
CONTROLS = ("vanilla-software", "combined-hwrt", "combined-software")
SCENARIOS = (
    "static",
    "camera-motion",
    "light-motion",
    "moving-rigid",
    "sparse-stress",
    "dense-stress",
    "large-world-stress",
    "vertical-world-stress",
)
HISTORICAL_I001_GPU_US = {
    "vanilla-software": {
        "static": 593.969,
        "camera-motion": 604.268,
        "light-motion": 603.186,
        "moving-rigid": 3302.675,
    },
    "combined-hwrt": {
        "static": 202.465,
        "camera-motion": 213.886,
        "light-motion": 206.512,
        "moving-rigid": 4100.230,
    },
    "combined-software": {
        "static": 391.544,
        "camera-motion": 396.714,
        "light-motion": 378.279,
        "moving-rigid": 3566.897,
    },
}
NUMERIC_FIELDS = (
    "setup_wall_us",
    "complete_frame_wall_us",
    "renderer_depth_us",
    "frame_init_us",
    "visibility_reuse_us",
    "producer_us",
    "ray_prepare_us",
    "traversal_maintenance_gpu_us",
    "dynamic_update_wall_us",
    "dynamic_builder_reset_us",
    "dynamic_builder_input_us",
    "dynamic_builder_aabb_us",
    "dynamic_builder_overlap_us",
    "dynamic_builder_prefix_us",
    "dynamic_builder_emit_us",
    "dynamic_builder_morton_us",
    "dynamic_builder_sort_us",
    "dynamic_builder_topology_us",
    "dynamic_builder_bounds_us",
    "dynamic_builder_ranges_us",
    "dynamic_builder_us",
    "static_traversal_us",
    "dynamic_traversal_us",
    "cross_structure_merge_us",
    "traversal_us",
    "radiance_us",
    "merge_us",
    "storage_update_us",
    "invalidation_us",
    "resolve_us",
    "complete_gpu_us",
    "incremental_gi_us",
    "persistent_bytes",
    "transient_bytes",
    "scratch_bytes",
    "peak_resident_bytes",
    "stream_capacity_bytes",
    "storage_capacity_bytes",
    "grid_pair_stream_bytes",
    "grid_sort_scratch_bytes",
    "grid_emitted_references",
    "grid_max_references_per_triangle",
    "grid_visited_macro_cells",
    "grid_visited_local_cells",
    "grid_empty_cell_steps",
    "grid_tested_primitive_references",
    "grid_cell_ranges",
    "grid_macro_ranges",
    "grid_overflow",
)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def artifact_root() -> Path:
    value = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if value:
        return Path(value)
    return (
        ROOT / "out/research/lane-f-dynamic-geometry-alternatives"
        / EXPERIMENT / "manual"
    )


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def read_single_csv(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if len(rows) != 1:
        raise RuntimeError(f"{path} must contain exactly one row")
    row = rows[0]
    if None in row:
        raise RuntimeError(
            f"{path} CSV schema mismatch: data contains extra columns "
            f"not present in header: {row[None]}"
        )
    if not reader.fieldnames or "quality_passed" not in reader.fieldnames:
        raise RuntimeError(
            f"{path} CSV schema mismatch: quality_passed column is missing"
        )
    return row


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def validation_error_count(stdout: str, stderr: str) -> int:
    combined = stdout + "\n" + stderr
    markers = ("Validation Error", "[Vulkan Validation] ERROR", "VUID-")
    return sum(
        1 for line in combined.splitlines()
        if any(marker in line for marker in markers)
    )


def run_case(
    build_dir: Path,
    scene: Path,
    variant: str,
    scenario: str,
    output_dir: Path,
    validation: bool,
) -> tuple[dict[str, str], dict[str, object], int]:
    output_dir.mkdir(parents=True, exist_ok=False)
    if variant == "transient-grid":
        executable = build_dir / "phos-lane-f-f005"
        command = [
            "bash", str(ROOT / "scripts/run_with_vulkan.sh"), str(executable),
            "--scene", str(scene), "--scenario", scenario,
        ]
        csv_name = "f005-candidate-frame.csv"
        device_name = "f005-candidate-device.json"
    else:
        executable = build_dir / "phos-lane-f-i001-control"
        command = [
            "bash", str(ROOT / "scripts/run_with_vulkan.sh"), str(executable),
            "--scene", str(scene), "--variant", variant, "--scenario", scenario,
        ]
        csv_name = "f001-control-frame.csv"
        device_name = "f001-control-device.json"
    if not executable.is_file():
        raise RuntimeError(f"missing executable: {executable}")
    if validation:
        command.append("--validation")
    else:
        command.append("--no-quality")

    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(output_dir)
    proc = subprocess.run(
        command, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    sys.stdout.write(proc.stdout)
    sys.stdout.flush()
    sys.stderr.write(proc.stderr)
    sys.stderr.flush()
    (output_dir / "process.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (output_dir / "process.stderr.log").write_text(proc.stderr, encoding="utf-8")

    errors = validation_error_count(proc.stdout, proc.stderr) if validation else 0
    if proc.returncode != 0:
        raise RuntimeError(
            f"F005 {variant}/{scenario} "
            f"{'validation' if validation else 'timing'} failed with {proc.returncode}"
        )
    if errors:
        raise RuntimeError(
            f"F005 {variant}/{scenario} emitted {errors} validation errors"
        )

    row = read_single_csv(output_dir / csv_name)
    device = json.loads((output_dir / device_name).read_text(encoding="utf-8"))
    if row.get("quality_passed") != "1":
        raise RuntimeError(f"F005 quality failed for {variant}/{scenario}")
    if int(row.get("storage_failures", "0")) != 0:
        raise RuntimeError(f"F005 storage failure for {variant}/{scenario}")
    if int(row.get("grid_overflow", "0")) != 0:
        raise RuntimeError(f"F005 grid overflow for {variant}/{scenario}")
    if device.get("device") != EXPECTED_GPU:
        raise RuntimeError(
            f"F005 target GPU mismatch: {device.get('device')!r}"
        )
    return row, device, errors


def find_prior_validation(root: Path, branch: str, commit: str) -> str | None:
    parent = root.parent
    if not parent.is_dir():
        return None
    for candidate in sorted(parent.iterdir(), reverse=True):
        if candidate == root or not candidate.is_dir():
            continue
        path = candidate / "f005-validation.json"
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            payload.get("passed") is True
            and payload.get("plan_version") == PLAN_VERSION
            and payload.get("branch") == branch
            and payload.get("git_commit") == commit
            and payload.get("target_gpu") == EXPECTED_GPU
        ):
            return str(candidate)
    return None


def normalize_row(
    row: dict[str, str],
    device: dict[str, object],
    *,
    branch: str,
    commit: str,
    root: Path,
    variant: str,
    scenario: str,
    repeat: int,
    validation_state: str,
    scene: Path,
) -> dict[str, object]:
    output: dict[str, object] = dict(row)
    output.update(
        {
            "schema_version": 1,
            "plan_version": PLAN_VERSION,
            "experiment": "F005",
            "branch": branch,
            "git_commit": commit,
            "dirty": False,
            "artifact_root": str(root),
            "command": " ".join(sys.argv),
            "variant": variant,
            "scenario": scenario,
            "geometry_class": "rigid-representative" if scenario == "moving-rigid"
                else "stable-control",
            "repeat": repeat,
            "target_gpu": device["device"],
            "driver_name": device["driver_name"],
            "driver_info": device["driver_info"],
            "api_version": device["api_version"],
            "validation_state": validation_state,
            "validation_errors": 0,
            "scene": str(scene),
            "dynamic_primitive_count": (
                int(row.get("moved_primitives", "0"))
                if scenario == "moving-rigid" else 0
            ),
            "dynamic_object_count": 1 if scenario == "moving-rigid" else 0,
            "topology_delta_count": 0,
        }
    )
    # Old unchanged I001 controls do not expose the Lane-F-specific phase
    # columns. Fill explicit N/A zeros so one frozen schema can hold all rows.
    for field in (
        "dynamic_builder_reset_us",
        "dynamic_builder_input_us",
        "dynamic_builder_aabb_us",
        "dynamic_builder_overlap_us",
        "dynamic_builder_prefix_us",
        "dynamic_builder_emit_us",
        "dynamic_builder_morton_us",
        "dynamic_builder_sort_us",
        "dynamic_builder_topology_us",
        "dynamic_builder_bounds_us",
        "dynamic_builder_ranges_us",
        "dynamic_builder_us",
        "static_traversal_us",
        "dynamic_traversal_us",
        "cross_structure_merge_us",
    ):
        output.setdefault(field, "0")
    if variant == "combined-hwrt":
        output["static_traversal_us"] = row["traversal_us"]
    return output


def summarize(rows: list[dict[str, object]]) -> tuple[dict[str, object], bool]:
    by_case: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in rows:
        by_case.setdefault((str(row["variant"]), str(row["scenario"])), []).append(row)

    summary: dict[str, object] = {v: {} for v in VARIANTS}
    any_unstable = False
    for (variant, scenario), group in sorted(by_case.items()):
        case: dict[str, object] = {}
        fields = set(NUMERIC_FIELDS)
        fields.update(
            {
                "shared_persistent_bytes",
                "static_hwrt_persistent_bytes",
                "dynamic_candidate_persistent_bytes",
                "dynamic_candidate_transient_bytes",
                "dynamic_candidate_scratch_bytes",
                "current_frame_geometry_bytes",
                "grid_pair_stream_bytes",
                "grid_sort_scratch_bytes",
                "host_persistent_bytes",
                "host_transient_bytes",
                "grid_emitted_references",
                "grid_max_references_per_triangle",
                "grid_visited_macro_cells",
                "grid_visited_local_cells",
                "grid_empty_cell_steps",
                "grid_tested_primitive_references",
                "grid_cell_ranges",
                "grid_macro_ranges",
                "grid_overflow",
            }
        )
        for field in sorted(fields):
            values = [
                float(row[field])
                for row in group
                if field in row and str(row[field]) not in ("", "None")
            ]
            if values:
                case[field] = {
                    "min": min(values),
                    "median": statistics.median(values),
                    "max": max(values),
                }
        gpu = [float(row["complete_gpu_us"]) for row in group]
        unstable = min(gpu) > 0.0 and max(gpu) / min(gpu) > 1.20
        case["unstable"] = unstable
        case["process_repeats"] = len(group)
        case["correctness_passed"] = all(
            str(row.get("quality_passed", "0")) == "1"
            and int(str(row.get("storage_failures", "0"))) == 0
            and int(str(row.get("grid_overflow", "0"))) == 0
            for row in group
        )
        summary[variant][scenario] = case
        any_unstable = any_unstable or unstable
    return summary, any_unstable


def med(summary: dict[str, object], variant: str, scenario: str, field: str) -> float:
    return float(summary[variant][scenario][field]["median"])


def evaluate_gates(summary: dict[str, object]) -> dict[str, object]:
    candidate = "transient-grid"
    hwrt = "combined-hwrt"
    vanilla = "vanilla-software"
    gates: dict[str, object] = {}

    for scenario in ("static", "camera-motion", "light-motion"):
        ratio = med(summary, candidate, scenario, "complete_gpu_us") / med(
            summary, hwrt, scenario, "complete_gpu_us"
        )
        gates[f"{scenario}_gpu"] = {
            "ratio": ratio, "limit": 1.05, "passed": ratio <= 1.05
        }

    for scenario in (
        "sparse-stress", "dense-stress",
        "large-world-stress", "vertical-world-stress",
    ):
        ratio = med(summary, candidate, scenario, "complete_gpu_us") / med(
            summary, hwrt, scenario, "complete_gpu_us"
        )
        gates[f"{scenario}_gpu"] = {
            "ratio": ratio, "limit": 1.05, "passed": ratio <= 1.05
        }

    moving_gpu = med(summary, candidate, "moving-rigid", "complete_gpu_us") / med(
        summary, vanilla, "moving-rigid", "complete_gpu_us"
    )
    moving_wall = med(
        summary, candidate, "moving-rigid", "complete_frame_wall_us"
    ) / med(summary, vanilla, "moving-rigid", "complete_frame_wall_us")
    gates["moving_gpu"] = {
        "ratio": moving_gpu, "limit": 0.90, "passed": moving_gpu <= 0.90
    }
    gates["moving_wall"] = {
        "ratio": moving_wall, "limit": 0.90, "passed": moving_wall <= 0.90
    }

    memory_cases: dict[str, object] = {}
    for scenario in SCENARIOS:
        ratio = med(summary, candidate, scenario, "peak_resident_bytes") / med(
            summary, vanilla, scenario, "peak_resident_bytes"
        )
        memory_cases[scenario] = {
            "ratio": ratio, "limit": 3.0, "passed": ratio <= 3.0
        }
    gates["memory"] = memory_cases
    gates["correctness"] = all(
        bool(summary[v][s]["correctness_passed"])
        for v in VARIANTS for s in SCENARIOS
    )
    gates["all_f005_required_gates_pass"] = (
        gates["correctness"]
        and all(
            value["passed"]
            for key, value in gates.items()
            if key not in ("correctness", "memory", "all_f005_required_gates_pass")
            and isinstance(value, dict) and "passed" in value
        )
        and all(v["passed"] for v in memory_cases.values())
    )
    return gates


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
    if not args.validation_only and args.repeats != 5:
        raise RuntimeError("F005 accepted timing requires exactly 5 process repeats")

    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"F005 must run on {EXPECTED_BRANCH}, got {branch}")
    if dirty:
        raise RuntimeError("F005 target evidence requires a clean Git tree")
    if not CONFIG.is_file():
        raise RuntimeError(f"F005 frozen config missing: {CONFIG}")

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
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
    write_json(root / "f005-config.json", config)
    build_dir = ROOT / args.build_dir

    if args.validation_only:
        results: list[dict[str, object]] = []
        device_identity: dict[str, object] | None = None
        for variant in VARIANTS:
            for scenario in SCENARIOS:
                row, device, errors = run_case(
                    build_dir, args.scene, variant, scenario,
                    root / "validation" / variant / scenario, True
                )
                if device_identity is None:
                    device_identity = device
                elif (
                    device.get("device") != device_identity.get("device")
                    or device.get("driver_name") != device_identity.get("driver_name")
                    or device.get("driver_info") != device_identity.get("driver_info")
                    or device.get("api_version") != device_identity.get("api_version")
                ):
                    raise RuntimeError(
                        "F005 validation device/driver/API changed inside campaign"
                    )
                results.append(
                    {
                        "variant": variant,
                        "scenario": scenario,
                        "quality_passed": row.get("quality_passed") == "1",
                        "storage_failures": int(row.get("storage_failures", "0")),
                        "grid_overflow": int(row.get("grid_overflow", "0")),
                        "validation_errors": errors,
                    }
                )
        passed = all(
            item["quality_passed"]
            and item["storage_failures"] == 0
            and item["grid_overflow"] == 0
            and item["validation_errors"] == 0
            for item in results
        )
        payload = {
            "schema_version": 1,
            "plan_version": PLAN_VERSION,
            "experiment": "F005",
            "branch": branch,
            "git_commit": commit,
            "dirty": dirty,
            "target_gpu": EXPECTED_GPU,
            "driver_name": device_identity.get("driver_name") if device_identity else None,
            "driver_info": device_identity.get("driver_info") if device_identity else None,
            "api_version": device_identity.get("api_version") if device_identity else None,
            "passed": passed,
            "cases": results,
        }
        write_json(root / "f005-validation.json", payload)
        write_json(root / "f005-device.json", device_identity or {})
        write_csv(root / "f005-raw.csv", [])
        write_json(
            root / "f005-summary.json",
            {
                "schema_version": 1,
                "plan_version": PLAN_VERSION,
                "status": "validation-pass" if passed else "validation-fail",
            },
        )
        print(f"F005 validation {'passed' if passed else 'failed'} for {len(results)} cases.")
        return 0 if passed else 3

    if not args.skip_validation:
        raise RuntimeError(
            "F005 timing requires --skip-validation after a passing same-commit validation"
        )
    prior = find_prior_validation(root, branch, commit)
    if prior is None:
        raise RuntimeError(
            "F005 timing requires a passing prior validation artifact from same commit/GPU"
        )
    validation_payload = json.loads(
        (Path(prior) / "f005-validation.json").read_text(encoding="utf-8")
    )
    validation_payload["reused_from_artifact"] = prior
    write_json(root / "f005-validation.json", validation_payload)

    raw: list[dict[str, object]] = []
    identity: dict[str, object] | None = None
    for repeat in range(args.repeats):
        for variant in VARIANTS:
            for scenario in SCENARIOS:
                row, device, _ = run_case(
                    build_dir, args.scene, variant, scenario,
                    root / f"repeat-{repeat:02d}" / variant / scenario, False
                )
                if identity is None:
                    identity = device
                    if (
                        validation_payload.get("driver_name") != device.get("driver_name")
                        or validation_payload.get("driver_info") != device.get("driver_info")
                        or validation_payload.get("api_version") != device.get("api_version")
                    ):
                        raise RuntimeError(
                            "F005 timing driver/API differs from the passing validation artifact"
                        )
                elif (
                    device.get("device") != identity.get("device")
                    or device.get("driver_name") != identity.get("driver_name")
                    or device.get("driver_info") != identity.get("driver_info")
                    or device.get("api_version") != identity.get("api_version")
                ):
                    raise RuntimeError("F005 device/driver/API changed inside campaign")
                raw.append(
                    normalize_row(
                        row, device,
                        branch=branch, commit=commit, root=root,
                        variant=variant, scenario=scenario, repeat=repeat,
                        validation_state="passed-prior-same-commit-gpu",
                        scene=args.scene,
                    )
                )

    write_csv(root / "f005-raw.csv", raw)
    summary, any_unstable = summarize(raw)
    gates = evaluate_gates(summary)
    moving_builder = med(summary, "transient-grid", "moving-rigid", "dynamic_builder_us")
    moving_dynamic_traversal = med(
        summary, "transient-grid", "moving-rigid", "dynamic_traversal_us"
    )

    status = "unstable-rerun-required" if any_unstable else "target-run-complete"
    # Gate ratios are retained for diagnosis, but an unstable campaign is not
    # decision-valid under lane-f-plan-v1. The rerun budget is tracked by the
    # experiment record/Issue, not inferred from a single artifact.
    formal = (
        "timing-inconclusive-unstable"
        if any_unstable
        else (
            "f005-gates-pass"
            if gates["all_f005_required_gates_pass"]
            else "f005-gates-fail"
        )
    )
    payload = {
        "schema_version": 1,
        "plan_version": PLAN_VERSION,
        "experiment": "F005",
        "status": status,
        "formal_architecture_status": formal,
        "branch": branch,
        "git_commit": commit,
        "dirty": False,
        "target_gpu": EXPECTED_GPU,
        "driver_name": identity.get("driver_name") if identity else None,
        "driver_info": identity.get("driver_info") if identity else None,
        "api_version": identity.get("api_version") if identity else None,
        "artifact_root": str(root),
        "command": " ".join(sys.argv),
        "scene": str(args.scene),
        "repeats": args.repeats,
        "warmup_frames_per_process": 1,
        "measured_frames_per_process": 1,
        "validation_artifact": prior,
        "historical_i001_gpu_us": HISTORICAL_I001_GPU_US,
        "medians": summary,
        "gates": gates,
        "moving_dynamic_builder_us": moving_builder,
        "moving_dynamic_traversal_us": moving_dynamic_traversal,
        "unstable": any_unstable,
    }
    write_json(root / "f005-summary.json", payload)
    write_json(root / "f005-device.json", identity or {})

    if any_unstable:
        print(
            "F005 timing contains complete_gpu max/min > 1.20; "
            "one identical full rerun is allowed by lane-f-plan-v1."
        )
        return 4

    print(
        "F005 complete: accepted sorted two-level grid matrix measured. "
        f"moving builder={moving_builder:.3f} us, "
        f"dynamic traversal={moving_dynamic_traversal:.3f} us, "
        f"status={formal}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

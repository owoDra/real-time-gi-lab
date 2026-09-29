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
EXPERIMENT = "006-geometry-class-crossover-controls"
CONFIG = (
    ROOT / "research/lanes/lane-f-dynamic-geometry-alternatives/experiments"
    / "006-geometry-class-crossover-controls-config.json"
)

VARIANTS = ("transient-lbvh", "transient-grid", "vanilla-software")
CANDIDATES = ("transient-lbvh", "transient-grid")
GEOMETRY_CLASSES = (
    "rigid-large-few",
    "rigid-small-many32",
    "deforming",
    "topology-replace25",
)

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
    "shared_persistent_bytes",
    "static_hwrt_persistent_bytes",
    "dynamic_candidate_persistent_bytes",
    "dynamic_candidate_transient_bytes",
    "dynamic_candidate_scratch_bytes",
    "current_frame_geometry_bytes",
    "grid_pair_stream_bytes",
    "grid_sort_scratch_bytes",
    "grid_emitted_references",
    "grid_references_per_dynamic_triangle",
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
            f"{path} CSV schema mismatch: extra data columns {row[None]}"
        )
    required = {"variant", "geometry_class", "quality_passed", "complete_gpu_us"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise RuntimeError(f"{path} CSV schema missing required F006 columns")
    return row


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
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


def run_case(
    build_dir: Path,
    scene: Path,
    variant: str,
    geometry_class: str,
    output_dir: Path,
    validation: bool,
) -> tuple[dict[str, str], dict[str, object], int]:
    output_dir.mkdir(parents=True, exist_ok=False)
    executable = build_dir / "phos-lane-f-f006"
    if not executable.is_file():
        raise RuntimeError(f"missing executable: {executable}")

    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--scene",
        str(scene),
        "--variant",
        variant,
        "--geometry-class",
        geometry_class,
    ]
    command.append("--validation" if validation else "--no-quality")

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

    errors = validation_error_count(proc.stdout, proc.stderr) if validation else 0
    if proc.returncode != 0:
        raise RuntimeError(
            f"F006 {variant}/{geometry_class} "
            f"{'validation' if validation else 'timing'} failed with {proc.returncode}"
        )
    if errors:
        raise RuntimeError(
            f"F006 {variant}/{geometry_class} emitted {errors} validation errors"
        )

    row = read_single_csv(output_dir / "f006-frame.csv")
    device = json.loads(
        (output_dir / "f006-device.json").read_text(encoding="utf-8")
    )
    if row.get("variant") != variant:
        raise RuntimeError(
            f"F006 variant identity mismatch: {row.get('variant')!r} != {variant!r}"
        )
    if row.get("geometry_class") != geometry_class:
        raise RuntimeError(
            "F006 geometry-class identity mismatch: "
            f"{row.get('geometry_class')!r} != {geometry_class!r}"
        )
    if row.get("quality_passed") != "1":
        raise RuntimeError(f"F006 quality failed for {variant}/{geometry_class}")
    if int(row.get("storage_failures", "0")) != 0:
        raise RuntimeError(f"F006 storage failure for {variant}/{geometry_class}")
    if int(row.get("grid_overflow", "0")) != 0:
        raise RuntimeError(f"F006 grid overflow for {variant}/{geometry_class}")
    if device.get("device") != EXPECTED_GPU:
        raise RuntimeError(
            f"F006 target GPU mismatch: {device.get('device')!r}"
        )
    return row, device, errors


def find_prior_validation(root: Path, branch: str, commit: str) -> str | None:
    parent = root.parent
    if not parent.is_dir():
        return None
    for candidate in sorted(parent.iterdir(), reverse=True):
        if candidate == root or not candidate.is_dir():
            continue
        path = candidate / "f006-validation.json"
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


def prior_unstable_timing_count(root: Path, branch: str, commit: str) -> int:
    parent = root.parent
    if not parent.is_dir():
        return 0
    count = 0
    for candidate in parent.iterdir():
        if candidate == root or not candidate.is_dir():
            continue
        path = candidate / "f006-summary.json"
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            payload.get("plan_version") == PLAN_VERSION
            and payload.get("branch") == branch
            and payload.get("git_commit") == commit
            and payload.get("target_gpu") == EXPECTED_GPU
            and payload.get("unstable") is True
        ):
            count += 1
    return count


def normalize_row(
    row: dict[str, str],
    device: dict[str, object],
    *,
    branch: str,
    commit: str,
    root: Path,
    variant: str,
    geometry_class: str,
    repeat: int,
    validation_state: str,
    scene: Path,
) -> dict[str, object]:
    output: dict[str, object] = dict(row)
    dynamic_count = int(row.get("moved_primitives", "0") or "0")
    emitted_references = int(row.get("grid_emitted_references", "0") or "0")
    output.update(
        {
            "schema_version": 1,
            "plan_version": PLAN_VERSION,
            "experiment": "F006",
            "branch": branch,
            "git_commit": commit,
            "dirty": False,
            "artifact_root": str(root),
            "command": " ".join(sys.argv),
            "variant": variant,
            "scenario": "moving-rigid",
            "geometry_class": geometry_class,
            "repeat": repeat,
            "target_gpu": device["device"],
            "driver_name": device["driver_name"],
            "driver_info": device["driver_info"],
            "api_version": device["api_version"],
            "validation_state": validation_state,
            "validation_errors": 0,
            "scene": str(scene),
            "dynamic_primitive_count": dynamic_count,
            "dynamic_object_count": int(row.get("dynamic_groups", "0") or "0"),
            "topology_delta_count": int(
                row.get("topology_replaced_primitives", "0") or "0"
            ),
            "grid_references_per_dynamic_triangle": (
                emitted_references / dynamic_count if dynamic_count > 0 else 0.0
            ),
        }
    )
    for field in NUMERIC_FIELDS:
        output.setdefault(field, "0")
    return output


def summarize(rows: list[dict[str, object]]) -> tuple[dict[str, object], bool]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(
            (str(row["variant"]), str(row["geometry_class"])), []
        ).append(row)

    summary: dict[str, object] = {variant: {} for variant in VARIANTS}
    any_unstable = False
    for (variant, geometry_class), group in sorted(grouped.items()):
        case: dict[str, object] = {}
        fields = set(NUMERIC_FIELDS)
        fields.update(
            {
                "dynamic_groups",
                "deformed_primitives",
                "topology_replaced_primitives",
                "moved_primitives",
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
        summary[variant][geometry_class] = case
        any_unstable = any_unstable or unstable
    return summary, any_unstable


def med(
    summary: dict[str, object],
    variant: str,
    geometry_class: str,
    field: str,
) -> float:
    return float(summary[variant][geometry_class][field]["median"])


def evaluate_gates(summary: dict[str, object]) -> dict[str, object]:
    results: dict[str, object] = {}
    vanilla = "vanilla-software"
    for candidate in CANDIDATES:
        class_results: dict[str, object] = {}
        all_pass = True
        for geometry_class in GEOMETRY_CLASSES:
            gpu_ratio = (
                med(summary, candidate, geometry_class, "complete_gpu_us")
                / med(summary, vanilla, geometry_class, "complete_gpu_us")
            )
            memory_ratio = (
                med(summary, candidate, geometry_class, "peak_resident_bytes")
                / med(summary, vanilla, geometry_class, "peak_resident_bytes")
            )
            correctness = bool(
                summary[candidate][geometry_class]["correctness_passed"]
            ) and bool(summary[vanilla][geometry_class]["correctness_passed"])
            passed = (
                correctness
                and gpu_ratio <= 1.05
                and memory_ratio <= 3.0
            )
            class_results[geometry_class] = {
                "correctness": correctness,
                "complete_gpu_ratio_vs_extended_vanilla": gpu_ratio,
                "complete_gpu_limit": 1.05,
                "memory_ratio_vs_extended_vanilla": memory_ratio,
                "memory_limit": 3.0,
                "passed": passed,
            }
            all_pass = all_pass and passed
        results[candidate] = {
            "classes": class_results,
            "all_f006_classes_pass": all_pass,
            "general_dynamic_claim_requires_rigid_primary": True,
        }
    return results


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
        raise RuntimeError("F006 accepted timing requires exactly 5 process repeats")

    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"F006 must run on {EXPECTED_BRANCH}, got {branch}")
    if dirty:
        raise RuntimeError("F006 target evidence requires a clean Git tree")
    if not CONFIG.is_file():
        raise RuntimeError(f"F006 frozen config missing: {CONFIG}")

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
    write_json(root / "f006-config.json", config)
    build_dir = ROOT / args.build_dir

    if args.validation_only:
        results: list[dict[str, object]] = []
        identity: dict[str, object] | None = None
        for variant in VARIANTS:
            for geometry_class in GEOMETRY_CLASSES:
                row, device, errors = run_case(
                    build_dir,
                    args.scene,
                    variant,
                    geometry_class,
                    root / "validation" / variant / geometry_class,
                    True,
                )
                if identity is None:
                    identity = device
                elif (
                    device.get("device") != identity.get("device")
                    or device.get("driver_name") != identity.get("driver_name")
                    or device.get("driver_info") != identity.get("driver_info")
                    or device.get("api_version") != identity.get("api_version")
                ):
                    raise RuntimeError(
                        "F006 validation device/driver/API changed inside campaign"
                    )
                results.append(
                    {
                        "variant": variant,
                        "geometry_class": geometry_class,
                        "quality_passed": row.get("quality_passed") == "1",
                        "storage_failures": int(row.get("storage_failures", "0")),
                        "grid_overflow": int(row.get("grid_overflow", "0")),
                        "validation_errors": errors,
                        "dynamic_primitives": int(row.get("moved_primitives", "0")),
                        "dynamic_groups": int(row.get("dynamic_groups", "0")),
                        "deformed_primitives": int(
                            row.get("deformed_primitives", "0")
                        ),
                        "topology_replaced_primitives": int(
                            row.get("topology_replaced_primitives", "0")
                        ),
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
            "experiment": "F006",
            "branch": branch,
            "git_commit": commit,
            "dirty": dirty,
            "target_gpu": EXPECTED_GPU,
            "driver_name": identity.get("driver_name") if identity else None,
            "driver_info": identity.get("driver_info") if identity else None,
            "api_version": identity.get("api_version") if identity else None,
            "passed": passed,
            "cases": results,
        }
        write_json(root / "f006-validation.json", payload)
        write_json(root / "f006-device.json", identity or {})
        write_csv(root / "f006-raw.csv", [])
        write_json(
            root / "f006-summary.json",
            {
                "schema_version": 1,
                "plan_version": PLAN_VERSION,
                "status": "validation-pass" if passed else "validation-fail",
            },
        )
        print(
            f"F006 validation {'passed' if passed else 'failed'} "
            f"for {len(results)} cases."
        )
        return 0 if passed else 3

    if not args.skip_validation:
        raise RuntimeError(
            "F006 timing requires --skip-validation after a passing "
            "same-commit validation"
        )
    prior = find_prior_validation(root, branch, commit)
    if prior is None:
        raise RuntimeError(
            "F006 timing requires a passing prior validation artifact "
            "from same commit/GPU"
        )
    validation_payload = json.loads(
        (Path(prior) / "f006-validation.json").read_text(encoding="utf-8")
    )
    validation_payload["reused_from_artifact"] = prior
    write_json(root / "f006-validation.json", validation_payload)

    raw: list[dict[str, object]] = []
    identity: dict[str, object] | None = None
    for repeat in range(args.repeats):
        for variant in VARIANTS:
            for geometry_class in GEOMETRY_CLASSES:
                row, device, _ = run_case(
                    build_dir,
                    args.scene,
                    variant,
                    geometry_class,
                    root / f"repeat-{repeat:02d}" / variant / geometry_class,
                    False,
                )
                if identity is None:
                    identity = device
                    if (
                        validation_payload.get("driver_name")
                        != device.get("driver_name")
                        or validation_payload.get("driver_info")
                        != device.get("driver_info")
                        or validation_payload.get("api_version")
                        != device.get("api_version")
                    ):
                        raise RuntimeError(
                            "F006 timing driver/API differs from validation artifact"
                        )
                elif (
                    device.get("device") != identity.get("device")
                    or device.get("driver_name") != identity.get("driver_name")
                    or device.get("driver_info") != identity.get("driver_info")
                    or device.get("api_version") != identity.get("api_version")
                ):
                    raise RuntimeError("F006 device/driver/API changed inside campaign")

                raw.append(
                    normalize_row(
                        row,
                        device,
                        branch=branch,
                        commit=commit,
                        root=root,
                        variant=variant,
                        geometry_class=geometry_class,
                        repeat=repeat,
                        validation_state="passed-prior-same-commit-gpu",
                        scene=args.scene,
                    )
                )

    write_csv(root / "f006-raw.csv", raw)
    summary, any_unstable = summarize(raw)
    gates = evaluate_gates(summary)

    prior_unstable = prior_unstable_timing_count(root, branch, commit)
    rerun_exhausted = any_unstable and prior_unstable >= 1
    status = (
        "timing-inconclusive-unstable"
        if rerun_exhausted
        else ("unstable-rerun-required" if any_unstable else "target-run-complete")
    )
    formal = (
        "timing-inconclusive-unstable"
        if any_unstable
        else "f006-controls-complete"
    )
    payload = {
        "schema_version": 1,
        "plan_version": PLAN_VERSION,
        "experiment": "F006",
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
        "medians": summary,
        "gates": gates,
        "unstable": any_unstable,
        "prior_identical_unstable_campaigns": prior_unstable,
        "identical_rerun_exhausted": rerun_exhausted,
    }
    write_json(root / "f006-summary.json", payload)
    write_json(root / "f006-device.json", identity or {})

    if any_unstable:
        if rerun_exhausted:
            print(
                "F006 timing remains unstable after the one permitted identical "
                "full rerun; timing is INCONCLUSIVE under lane-f-plan-v1."
            )
            return 5
        print(
            "F006 timing contains complete_gpu max/min >1.20; "
            "one identical full rerun is allowed by lane-f-plan-v1."
        )
        return 4

    print("F006 complete: geometry-class crossover controls measured.")
    for candidate in CANDIDATES:
        print(
            f"  {candidate}: all_f006_classes_pass="
            f"{gates[candidate]['all_f006_classes_pass']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
EXPERIMENT = "007-final-integration-replay"
CONFIG = (
    ROOT / "research/lanes/lane-f-dynamic-geometry-alternatives/experiments"
    / "007-final-integration-replay-config.json"
)

VARIANTS = (
    "transient-lbvh",
    "transient-grid",
    "vanilla-software",
    "combined-hwrt",
    "combined-software",
)
CANDIDATES = ("transient-lbvh", "transient-grid")
SCENARIOS = (
    "static",
    "camera-motion",
    "light-motion",
    "moving-rigid",
    "sparse-stress",
    "dense-stress",
    "large-world-stress",
    "vertical-world-stress",
    "sparse-moving",
    "dense-moving",
    "large-world-moving",
    "vertical-world-moving",
)
STABLE_STRESS = (
    "sparse-stress",
    "dense-stress",
    "large-world-stress",
    "vertical-world-stress",
)
DYNAMIC_STRESS = (
    "sparse-moving",
    "dense-moving",
    "large-world-moving",
    "vertical-world-moving",
)
DYNAMIC_SCENARIOS = ("moving-rigid",) + DYNAMIC_STRESS

HISTORICAL_I001 = {
    "source_result": "research/integration/results/001-dynamic-end-to-end.md",
    "measurement_commit": "3a1aa9c25ffcec583459409aca4c526b17b53e3c",
    "artifact": (
        "out/research/integration-gate/001-dynamic-end-to-end/"
        "20260929T060025Z"
    ),
    "representative_complete_gpu_us": {
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
    },
    "stable_stress_hwrt_vs_vanilla_percent": {
        "sparse-stress": -54.19,
        "dense-stress": -66.60,
        "large-world-stress": -63.60,
        "vertical-world-stress": -60.54,
    },
    "note": (
        "The committed I001 result records absolute representative medians and "
        "stable-stress HWRT-vs-vanilla percentages, but not absolute historical "
        "stress medians for all three variants."
    ),
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
    required = {
        "variant",
        "scenario",
        "quality_passed",
        "complete_gpu_us",
        "complete_frame_wall_us",
        "peak_resident_bytes",
    }
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise RuntimeError(f"{path} CSV schema missing required F007 columns")
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
    scenario: str,
    output_dir: Path,
    validation: bool,
) -> tuple[dict[str, str], dict[str, object], int]:
    output_dir.mkdir(parents=True, exist_ok=False)
    executable = build_dir / "phos-lane-f-f007"
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
        "--scenario",
        scenario,
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
            f"F007 {variant}/{scenario} "
            f"{'validation' if validation else 'timing'} failed with {proc.returncode}"
        )
    if errors:
        raise RuntimeError(
            f"F007 {variant}/{scenario} emitted {errors} validation errors"
        )

    row = read_single_csv(output_dir / "f007-frame.csv")
    device = json.loads(
        (output_dir / "f007-device.json").read_text(encoding="utf-8")
    )
    if row.get("variant") != variant:
        raise RuntimeError(
            f"F007 variant identity mismatch: {row.get('variant')!r} != {variant!r}"
        )
    if row.get("scenario") != scenario:
        raise RuntimeError(
            f"F007 scenario identity mismatch: {row.get('scenario')!r} != {scenario!r}"
        )
    if row.get("quality_passed") != "1":
        raise RuntimeError(f"F007 quality failed for {variant}/{scenario}")
    if int(row.get("storage_failures", "0")) != 0:
        raise RuntimeError(f"F007 storage failure for {variant}/{scenario}")
    if int(row.get("grid_overflow", "0")) != 0:
        raise RuntimeError(f"F007 grid overflow for {variant}/{scenario}")
    if device.get("device") != EXPECTED_GPU:
        raise RuntimeError(
            f"F007 target GPU mismatch: {device.get('device')!r}"
        )

    moved = int(row.get("moved_primitives", "0"))
    membership = int(row.get("segment_membership_changes", "0"))
    if scenario in DYNAMIC_SCENARIOS:
        if moved != 796:
            raise RuntimeError(
                f"F007 dynamic workload identity mismatch for {variant}/{scenario}: "
                f"moved={moved}, expected 796"
            )
        if membership <= 0:
            raise RuntimeError(
                f"F007 dynamic workload did not change segment membership for "
                f"{variant}/{scenario}"
            )
    elif moved != 0:
        raise RuntimeError(
            f"F007 stable workload unexpectedly moved primitives for "
            f"{variant}/{scenario}: {moved}"
        )
    return row, device, errors


def find_prior_validation(root: Path, branch: str, commit: str) -> str | None:
    parent = root.parent
    if not parent.is_dir():
        return None
    for candidate in sorted(parent.iterdir(), reverse=True):
        if candidate == root or not candidate.is_dir():
            continue
        path = candidate / "f007-validation.json"
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
        path = candidate / "f007-summary.json"
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
    scenario: str,
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
            "experiment": "F007",
            "branch": branch,
            "git_commit": commit,
            "dirty": False,
            "artifact_root": str(root),
            "command": " ".join(sys.argv),
            "variant": variant,
            "scenario": scenario,
            "geometry_class": (
                "representative-rigid"
                if scenario in DYNAMIC_SCENARIOS
                else "stable-control"
            ),
            "repeat": repeat,
            "target_gpu": device["device"],
            "driver_name": device["driver_name"],
            "driver_info": device["driver_info"],
            "api_version": device["api_version"],
            "validation_state": validation_state,
            "validation_errors": 0,
            "scene": str(scene),
            "dynamic_primitive_count": dynamic_count,
            "dynamic_object_count": (
                int(row.get("dynamic_groups", "0") or "0")
                if scenario in DYNAMIC_SCENARIOS else 0
            ),
            "topology_delta_count": 0,
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
            (str(row["variant"]), str(row["scenario"])), []
        ).append(row)

    summary: dict[str, object] = {variant: {} for variant in VARIANTS}
    any_unstable = False
    for (variant, scenario), group in sorted(grouped.items()):
        case: dict[str, object] = {}
        fields = set(NUMERIC_FIELDS)
        fields.update(
            {
                "dynamic_groups",
                "deformed_primitives",
                "topology_replaced_primitives",
                "moved_primitives",
                "segment_membership_changes",
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


def med(
    summary: dict[str, object],
    variant: str,
    scenario: str,
    field: str,
) -> float:
    return float(summary[variant][scenario][field]["median"])


def evaluate_candidate(
    summary: dict[str, object],
    candidate: str,
) -> dict[str, object]:
    gates: dict[str, object] = {}

    correctness = all(
        bool(summary[candidate][scenario]["correctness_passed"])
        for scenario in SCENARIOS
    )
    gates["correctness"] = correctness

    for scenario in ("static", "camera-motion", "light-motion"):
        ratio = (
            med(summary, candidate, scenario, "complete_gpu_us")
            / med(summary, "combined-hwrt", scenario, "complete_gpu_us")
        )
        gates[f"{scenario}_gpu"] = {
            "ratio": ratio,
            "limit": 1.05,
            "passed": ratio <= 1.05,
            "comparator": "combined-hwrt",
        }

    moving_gpu = (
        med(summary, candidate, "moving-rigid", "complete_gpu_us")
        / med(summary, "vanilla-software", "moving-rigid", "complete_gpu_us")
    )
    moving_wall = (
        med(summary, candidate, "moving-rigid", "complete_frame_wall_us")
        / med(
            summary,
            "vanilla-software",
            "moving-rigid",
            "complete_frame_wall_us",
        )
    )
    gates["moving_rigid_gpu"] = {
        "ratio": moving_gpu,
        "limit": 0.90,
        "passed": moving_gpu <= 0.90,
        "comparator": "vanilla-software",
    }
    gates["moving_rigid_wall"] = {
        "ratio": moving_wall,
        "limit": 0.90,
        "passed": moving_wall <= 0.90,
        "comparator": "vanilla-software",
    }

    stable_stress: dict[str, object] = {}
    for scenario in STABLE_STRESS:
        ratio = (
            med(summary, candidate, scenario, "complete_gpu_us")
            / med(summary, "combined-hwrt", scenario, "complete_gpu_us")
        )
        stable_stress[scenario] = {
            "ratio": ratio,
            "limit": 1.05,
            "passed": ratio <= 1.05,
            "comparator": "combined-hwrt",
        }
    gates["stable_stress_gpu"] = stable_stress

    dynamic_stress: dict[str, object] = {}
    for scenario in DYNAMIC_STRESS:
        ratio = (
            med(summary, candidate, scenario, "complete_gpu_us")
            / med(summary, "vanilla-software", scenario, "complete_gpu_us")
        )
        dynamic_stress[scenario] = {
            "ratio": ratio,
            "limit": 1.05,
            "passed": ratio <= 1.05,
            "comparator": "vanilla-software",
        }
    gates["dynamic_stress_gpu"] = dynamic_stress

    memory: dict[str, object] = {}
    for scenario in SCENARIOS:
        ratio = (
            med(summary, candidate, scenario, "peak_resident_bytes")
            / med(summary, "vanilla-software", scenario, "peak_resident_bytes")
        )
        memory[scenario] = {
            "ratio": ratio,
            "limit": 3.0,
            "passed": ratio <= 3.0,
            "comparator": "vanilla-software",
        }
    gates["memory"] = memory

    gates["rigid_primary"] = (
        correctness
        and all(
            bool(gates[key]["passed"])
            for key in (
                "static_gpu",
                "camera-motion_gpu",
                "light-motion_gpu",
                "moving_rigid_gpu",
                "moving_rigid_wall",
            )
        )
        and all(item["passed"] for item in stable_stress.values())
        and all(item["passed"] for item in dynamic_stress.values())
        and all(item["passed"] for item in memory.values())
    )
    gates["general_dynamic"] = False
    gates["general_dynamic_reason"] = (
        "F006 formal generalization timing is inconclusive after its permitted rerun"
    )
    return gates


def decide_primary(
    summary: dict[str, object],
    candidate_gates: dict[str, object],
) -> dict[str, object]:
    survivors = [
        candidate
        for candidate in CANDIDATES
        if candidate_gates[candidate]["rigid_primary"]
    ]
    if not survivors:
        return {
            "selected": None,
            "reason": "no-transient-candidate-passed-all-rigid-primary-gates",
            "survivors": [],
        }
    if len(survivors) == 1:
        return {
            "selected": survivors[0],
            "reason": "only-transient-candidate-passing-all-rigid-primary-gates",
            "survivors": survivors,
        }

    lbvh_gpu = med(summary, "transient-lbvh", "moving-rigid", "complete_gpu_us")
    grid_gpu = med(summary, "transient-grid", "moving-rigid", "complete_gpu_us")
    faster = "transient-lbvh" if lbvh_gpu < grid_gpu else "transient-grid"
    slower_gpu = max(lbvh_gpu, grid_gpu)
    faster_gpu = min(lbvh_gpu, grid_gpu)
    gpu_improvement = (
        (slower_gpu - faster_gpu) / slower_gpu if slower_gpu > 0.0 else 0.0
    )
    if gpu_improvement >= 0.05:
        return {
            "selected": faster,
            "reason": "moving-rigid-complete-gpu-diff-at-least-5-percent",
            "moving_gpu_improvement_fraction": gpu_improvement,
            "survivors": survivors,
        }

    max_memory = {
        candidate: max(
            med(summary, candidate, scenario, "peak_resident_bytes")
            for scenario in SCENARIOS
        )
        for candidate in survivors
    }
    lower = min(max_memory, key=max_memory.get)
    higher = max(max_memory.values())
    lower_value = min(max_memory.values())
    memory_improvement = (
        (higher - lower_value) / higher if higher > 0.0 else 0.0
    )
    if memory_improvement >= 0.10:
        return {
            "selected": lower,
            "reason": "maximum-peak-memory-diff-at-least-10-percent",
            "memory_improvement_fraction": memory_improvement,
            "maximum_peak_resident_bytes": max_memory,
            "survivors": survivors,
        }

    return {
        "selected": "transient-lbvh",
        "reason": "frozen-tie-rule-retains-primary-lbvh-family",
        "moving_gpu_improvement_fraction": gpu_improvement,
        "memory_improvement_fraction": memory_improvement,
        "maximum_peak_resident_bytes": max_memory,
        "survivors": survivors,
    }


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
        raise RuntimeError("F007 accepted timing requires exactly 5 process repeats")

    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"F007 must run on {EXPECTED_BRANCH}, got {branch}")
    if dirty:
        raise RuntimeError("F007 target evidence requires a clean Git tree")
    if not CONFIG.is_file():
        raise RuntimeError(f"F007 frozen config missing: {CONFIG}")

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
    write_json(root / "f007-config.json", config)
    build_dir = ROOT / args.build_dir

    if args.validation_only:
        results: list[dict[str, object]] = []
        identity: dict[str, object] | None = None
        for variant in VARIANTS:
            for scenario in SCENARIOS:
                row, device, errors = run_case(
                    build_dir,
                    args.scene,
                    variant,
                    scenario,
                    root / "validation" / variant / scenario,
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
                        "F007 validation device/driver/API changed inside campaign"
                    )
                results.append(
                    {
                        "variant": variant,
                        "scenario": scenario,
                        "quality_passed": row.get("quality_passed") == "1",
                        "storage_failures": int(row.get("storage_failures", "0")),
                        "grid_overflow": int(row.get("grid_overflow", "0")),
                        "validation_errors": errors,
                        "dynamic_primitives": int(
                            row.get("moved_primitives", "0")
                        ),
                        "segment_membership_changes": int(
                            row.get("segment_membership_changes", "0")
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
            "experiment": "F007",
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
        write_json(root / "f007-validation.json", payload)
        write_json(root / "f007-device.json", identity or {})
        write_csv(root / "f007-raw.csv", [])
        write_json(
            root / "f007-summary.json",
            {
                "schema_version": 1,
                "plan_version": PLAN_VERSION,
                "status": "validation-pass" if passed else "validation-fail",
            },
        )
        print(
            f"F007 validation {'passed' if passed else 'failed'} "
            f"for {len(results)} cases."
        )
        return 0 if passed else 3

    if not args.skip_validation:
        raise RuntimeError(
            "F007 timing requires --skip-validation after a passing "
            "same-commit validation"
        )
    prior = find_prior_validation(root, branch, commit)
    if prior is None:
        raise RuntimeError(
            "F007 timing requires a passing prior validation artifact "
            "from same commit/GPU"
        )
    validation_payload = json.loads(
        (Path(prior) / "f007-validation.json").read_text(encoding="utf-8")
    )
    validation_payload["reused_from_artifact"] = prior
    write_json(root / "f007-validation.json", validation_payload)

    raw: list[dict[str, object]] = []
    identity: dict[str, object] | None = None
    for repeat in range(args.repeats):
        for variant in VARIANTS:
            for scenario in SCENARIOS:
                row, device, _ = run_case(
                    build_dir,
                    args.scene,
                    variant,
                    scenario,
                    root / f"repeat-{repeat:02d}" / variant / scenario,
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
                            "F007 timing driver/API differs from validation artifact"
                        )
                elif (
                    device.get("device") != identity.get("device")
                    or device.get("driver_name") != identity.get("driver_name")
                    or device.get("driver_info") != identity.get("driver_info")
                    or device.get("api_version") != identity.get("api_version")
                ):
                    raise RuntimeError("F007 device/driver/API changed inside campaign")

                raw.append(
                    normalize_row(
                        row,
                        device,
                        branch=branch,
                        commit=commit,
                        root=root,
                        variant=variant,
                        scenario=scenario,
                        repeat=repeat,
                        validation_state="passed-prior-same-commit-gpu",
                        scene=args.scene,
                    )
                )

    write_csv(root / "f007-raw.csv", raw)
    summary, any_unstable = summarize(raw)
    candidate_gates = {
        candidate: evaluate_candidate(summary, candidate)
        for candidate in CANDIDATES
    }
    decision = decide_primary(summary, candidate_gates)

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
        else "f007-final-decision-complete"
    )

    payload = {
        "schema_version": 1,
        "plan_version": PLAN_VERSION,
        "experiment": "F007",
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
        "historical_i001": HISTORICAL_I001,
        "medians": summary,
        "candidate_gates": candidate_gates,
        "decision": decision if not any_unstable else {
            "selected": None,
            "reason": "formal-decision-deferred-because-campaign-is-unstable",
        },
        "unstable": any_unstable,
        "prior_identical_unstable_campaigns": prior_unstable,
        "identical_rerun_exhausted": rerun_exhausted,
    }
    write_json(root / "f007-summary.json", payload)
    write_json(root / "f007-device.json", identity or {})

    if any_unstable:
        if rerun_exhausted:
            print(
                "F007 timing remains unstable after the one permitted identical "
                "full rerun; final timing decision is INCONCLUSIVE under "
                "lane-f-plan-v1."
            )
            return 5
        print(
            "F007 timing contains complete_gpu max/min >1.20; "
            "one identical full rerun is allowed by lane-f-plan-v1."
        )
        return 4

    print("F007 complete: final integration timing is stable.")
    for candidate in CANDIDATES:
        print(
            f"  {candidate}: rigid_primary="
            f"{candidate_gates[candidate]['rigid_primary']}"
        )
    print(
        "  selected="
        f"{decision.get('selected')} ({decision.get('reason')})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
EXPERIMENT = "001-workload-census-baseline-replay"
VARIANTS = ("vanilla-software", "combined-hwrt", "combined-software")
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
REPRESENTATIVE = ("static", "camera-motion", "light-motion", "moving-rigid")
WORKLOAD_IDS = {
    "static": 16139458794081967227,
    "camera-motion": 15809339685104866027,
    "light-motion": 16301245569441789499,
    "moving-rigid": 16139458794081967227,
}
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
# I001's committed final report retained stress ratios rather than absolute
# medians. Preserve those ratios as the historical drift anchor instead of
# inventing unavailable absolute numbers.
HISTORICAL_HWRT_STRESS_RATIO = {
    "sparse-stress": 1.0 - 0.5419,
    "dense-stress": 1.0 - 0.6660,
    "large-world-stress": 1.0 - 0.6360,
    "vertical-world-stress": 1.0 - 0.6054,
}
SUMMARY_FIELDS = (
    "setup_wall_us",
    "complete_frame_wall_us",
    "renderer_depth_us",
    "frame_init_us",
    "visibility_reuse_us",
    "producer_us",
    "ray_prepare_us",
    "traversal_maintenance_gpu_us",
    "dynamic_update_wall_us",
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


def write_raw(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns = list(dict.fromkeys(key for row in rows for key in row.keys()))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def run_process(
    command: list[str],
    output_dir: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    output_dir.mkdir(parents=True, exist_ok=False)
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
    return proc


def validation_error_count(proc: subprocess.CompletedProcess[str]) -> int:
    combined = proc.stdout + "\n" + proc.stderr
    markers = ("Validation Error", "[Vulkan Validation] ERROR", "VUID-")
    return sum(
        1
        for line in combined.splitlines()
        if any(marker in line for marker in markers)
    )


def run_census(
    executable: Path,
    scene: Path,
    root: Path,
    validation: bool,
    process_name: str,
) -> dict[str, object]:
    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--scene",
        str(scene),
    ]
    if validation:
        command.append("--validation")
    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(root)
    proc = run_process(command, root / process_name, env)
    if proc.returncode != 0:
        raise RuntimeError(f"F001 census failed with {proc.returncode}")
    errors = validation_error_count(proc) if validation else 0
    if errors:
        raise RuntimeError(f"F001 census emitted {errors} Vulkan validation errors")
    path = root / "f001-census.json"
    if not path.is_file():
        raise RuntimeError("F001 census did not produce f001-census.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("device") != EXPECTED_GPU:
        raise RuntimeError(
            f"F001 target GPU mismatch: {payload.get('device')!r} != {EXPECTED_GPU!r}"
        )
    return payload


def run_control(
    executable: Path,
    scene: Path,
    variant: str,
    scenario: str,
    output_dir: Path,
    validation: bool,
) -> tuple[dict[str, str], dict[str, object]]:
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
    proc = run_process(command, output_dir, env)
    errors = validation_error_count(proc) if validation else 0
    csv_path = output_dir / "f001-control-frame.csv"
    rows: list[dict[str, str]] = []
    if csv_path.is_file():
        with csv_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

    if proc.returncode != 0:
        raise RuntimeError(
            f"F001 control {variant}/{scenario} "
            f"{'validation' if validation else 'timing'} failed with {proc.returncode}"
        )
    if errors:
        raise RuntimeError(
            f"F001 control {variant}/{scenario} emitted {errors} validation errors"
        )
    if len(rows) != 1:
        raise RuntimeError(f"{csv_path} must contain exactly one data row")

    row = rows[0]
    row["validation_errors"] = str(errors)
    row["scene"] = str(scene)
    row["plan_version"] = PLAN_VERSION
    row["source_workload_id"] = str(WORKLOAD_IDS.get(scenario, ""))
    if row.get("device") != EXPECTED_GPU:
        raise RuntimeError(
            f"F001 target GPU mismatch for {variant}/{scenario}: {row.get('device')!r}"
        )
    if row.get("quality_passed") != "1":
        raise RuntimeError(f"F001 quality failed for {variant}/{scenario}")
    if int(row.get("storage_failures", "0")) != 0:
        raise RuntimeError(f"F001 storage failures for {variant}/{scenario}")

    device_path = output_dir / "f001-control-device.json"
    if not device_path.is_file():
        raise RuntimeError(f"missing control device metadata: {device_path}")
    device = json.loads(device_path.read_text(encoding="utf-8"))
    return row, device


def summarize_group(rows: list[dict[str, str]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for field in SUMMARY_FIELDS:
        values = [float(row[field]) for row in rows]
        result[field] = {
            "min": min(values),
            "median": statistics.median(values),
            "max": max(values),
        }
    complete = [float(row["complete_gpu_us"]) for row in rows]
    ratio = max(complete) / min(complete) if min(complete) > 0.0 else float("inf")
    result["complete_gpu_max_min_ratio"] = ratio
    result["unstable"] = ratio > 1.20
    return result


def find_prior_validation(
    commit: str,
    current_root: Path,
) -> tuple[Path, dict[str, object]]:
    base = ROOT / "out/research/lane-f-dynamic-geometry-alternatives" / EXPERIMENT
    if not base.is_dir():
        raise RuntimeError("no prior F001 artifact directory exists")
    for candidate in sorted(base.iterdir(), reverse=True):
        try:
            same = candidate.resolve() == current_root.resolve()
        except OSError:
            same = False
        if same or not candidate.is_dir():
            continue
        path = candidate / "f001-validation.json"
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            payload.get("passed") is True
            and payload.get("plan_version") == PLAN_VERSION
            and payload.get("branch") == EXPECTED_BRANCH
            and payload.get("git_commit") == commit
            and payload.get("target_gpu") == EXPECTED_GPU
        ):
            return candidate, payload
    raise RuntimeError(
        "accepted timing requires a prior passing F001 validation artifact "
        "from the same commit/GPU"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lane F F001 workload census + run-local I001 baseline replay."
    )
    parser.add_argument("--build-dir", type=Path, default=Path("build/release"))
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--validation-only", action="store_true")
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()

    if args.validation_only and args.skip_validation:
        parser.error("--validation-only cannot be combined with --skip-validation")
    if not args.validation_only and args.repeats != 5:
        parser.error("accepted F001 timing requires exactly --repeats 5")

    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"F001 must run on {EXPECTED_BRANCH}, got {branch}")
    if dirty:
        raise RuntimeError("F001 target evidence requires a clean Git tree")

    build_dir = (ROOT / args.build_dir).resolve()
    census_exe = build_dir / "phos-lane-f-f001-census"
    control_exe = build_dir / "phos-lane-f-i001-control"
    for path in (census_exe, control_exe):
        if not path.is_file():
            raise RuntimeError(f"missing Lane F executable: {path}")
    scene = args.scene.resolve()
    if not scene.is_file():
        raise RuntimeError(f"missing scene: {scene}")

    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": 1,
        "plan_version": PLAN_VERSION,
        "branch": EXPECTED_BRANCH,
        "git_commit": commit,
        "scene": str(scene),
        "variants": list(VARIANTS),
        "scenarios": list(SCENARIOS),
        "process_repeats": args.repeats,
        "warmup_frames_per_process": 1,
        "measured_frames_per_process": 1,
        "moving_selection": "algorithmic mirror of I001 choose_moving_selection",
        "aabb_extent_metric": "per-triangle AABB diagonal length",
        "triangle_aspect_metric": "longest_edge_squared / twice_triangle_area",
        "distribution_p95": "sorted floor(0.95 * (n - 1))",
        "dynamic_hit_fraction_denominator": "all valid A001 work-item rays",
        "historical_i001_measurement_commit": "3a1aa9c25ffcec583459409aca4c526b17b53e3c",
        "historical_i001_gpu_us": HISTORICAL_I001_GPU_US,
        "historical_hwrt_stress_ratio": HISTORICAL_HWRT_STRESS_RATIO,
        "historical_stress_absolute_note": (
            "I001 committed final report retained HWRT-vs-vanilla stress ratios "
            "but not absolute stress medians; F001 records ratio drift rather "
            "than inventing missing absolute values."
        ),
    }
    write_json(root / "f001-config.json", config)

    validation_artifact: str | None = None
    if args.skip_validation:
        source_root, prior = find_prior_validation(commit, root)
        reused = dict(prior)
        reused["reused_from_artifact"] = str(source_root)
        write_json(root / "f001-validation.json", reused)
        validation_artifact = str(source_root)
    else:
        validation_failures: list[str] = []
        validation_rows: list[dict[str, str]] = []
        validation_device: dict[str, object] | None = None
        census: dict[str, object] | None = None
        try:
            census = run_census(
                census_exe,
                scene,
                root,
                True,
                "census-validation-process",
            )
        except Exception as error:
            validation_failures.append(f"census: {error}")

        for variant in VARIANTS:
            for scenario in SCENARIOS:
                try:
                    row, device = run_control(
                        control_exe,
                        scene,
                        variant,
                        scenario,
                        root / "validation" / variant / scenario,
                        True,
                    )
                    row["phase"] = "validation"
                    row["git_commit"] = commit
                    validation_rows.append(row)
                    if validation_device is None:
                        validation_device = device
                except Exception as error:
                    validation_failures.append(f"{variant}/{scenario}: {error}")

        validation_payload = {
            "schema_version": 1,
            "plan_version": PLAN_VERSION,
            "branch": branch,
            "git_commit": commit,
            "dirty": dirty,
            "target_gpu": EXPECTED_GPU,
            "case_count": 1 + len(VARIANTS) * len(SCENARIOS),
            "passed": not validation_failures,
            "failures": validation_failures,
        }
        write_json(root / "f001-validation.json", validation_payload)
        write_raw(root / "f001-raw.csv", validation_rows)

        if validation_device is not None:
            validation_device.update({
                "plan_version": PLAN_VERSION,
                "branch": branch,
                "git_commit": commit,
            })
            write_json(root / "f001-device.json", validation_device)

        validation_summary = {
            "schema_version": 1,
            "plan_version": PLAN_VERSION,
            "status": "validation-pass" if not validation_failures else "validation-fail",
            "branch": branch,
            "git_commit": commit,
            "dirty": dirty,
            "target_gpu": EXPECTED_GPU,
            "census": census,
            "validation": validation_payload,
            "candidate_gate": "not-applicable-f001",
        }
        write_json(root / "f001-summary.json", validation_summary)

        if validation_failures:
            raise RuntimeError(
                "F001 validation failed:\n  - " + "\n  - ".join(validation_failures)
            )
        if args.validation_only:
            print("F001 validation/correctness preflight: PASS")
            return 0

    census = run_census(
        census_exe,
        scene,
        root,
        False,
        "census-timing-process",
    )
    accepted: list[dict[str, str]] = []
    device_payload: dict[str, object] | None = None
    for repeat in range(1, args.repeats + 1):
        for variant in VARIANTS:
            for scenario in SCENARIOS:
                output_dir = (
                    root / "timing" / f"repeat-{repeat}" / variant / scenario
                )
                row, device = run_control(
                    control_exe,
                    scene,
                    variant,
                    scenario,
                    output_dir,
                    False,
                )
                row["phase"] = "timing"
                row["repeat"] = str(repeat)
                row["git_commit"] = commit
                accepted.append(row)
                if device_payload is None:
                    device_payload = device

    write_raw(root / "f001-raw.csv", accepted)

    medians: dict[str, dict[str, object]] = {}
    any_unstable = False
    for variant in VARIANTS:
        medians[variant] = {}
        for scenario in SCENARIOS:
            group = [
                row for row in accepted
                if row["variant"] == variant and row["scenario"] == scenario
            ]
            summary = summarize_group(group)
            medians[variant][scenario] = summary
            any_unstable = any_unstable or bool(summary["unstable"])

    historical_delta: dict[str, dict[str, float]] = {}
    for variant in VARIANTS:
        historical_delta[variant] = {}
        for scenario in REPRESENTATIVE:
            current = float(
                medians[variant][scenario]["complete_gpu_us"]["median"]
            )
            historical = HISTORICAL_I001_GPU_US[variant][scenario]
            historical_delta[variant][scenario] = current / historical - 1.0

    stress_ratio_drift: dict[str, dict[str, float]] = {}
    for scenario, historical_ratio in HISTORICAL_HWRT_STRESS_RATIO.items():
        vanilla = float(
            medians["vanilla-software"][scenario]["complete_gpu_us"]["median"]
        )
        hwrt = float(
            medians["combined-hwrt"][scenario]["complete_gpu_us"]["median"]
        )
        current_ratio = hwrt / vanilla
        stress_ratio_drift[scenario] = {
            "historical_hwrt_over_vanilla": historical_ratio,
            "run_local_hwrt_over_vanilla": current_ratio,
            "ratio_delta": current_ratio - historical_ratio,
        }

    vanilla_moving = float(
        medians["vanilla-software"]["moving-rigid"]["complete_gpu_us"]["median"]
    )
    summary_payload = {
        "schema_version": 1,
        "plan_version": PLAN_VERSION,
        "status": "unstable-rerun-required" if any_unstable else "target-run-complete",
        "branch": branch,
        "git_commit": commit,
        "dirty": dirty,
        "target_gpu": EXPECTED_GPU,
        "repeats": args.repeats,
        "validation_artifact": validation_artifact,
        "census": census,
        "medians": medians,
        "historical_complete_gpu_delta_ratio": historical_delta,
        "historical_stress_ratio_drift": stress_ratio_drift,
        "f002_builder_feasibility_ceiling_us": 0.90 * vanilla_moving,
        "unstable": any_unstable,
        "fixed_gate_note": (
            "F001 has no candidate promotion gate; correctness and baseline "
            "provenance must be accepted before F002."
        ),
    }
    write_json(root / "f001-summary.json", summary_payload)

    if device_payload is None:
        raise RuntimeError("F001 did not capture device metadata")
    device_payload.update({
        "plan_version": PLAN_VERSION,
        "branch": branch,
        "git_commit": commit,
    })
    write_json(root / "f001-device.json", device_payload)

    if any_unstable:
        print(
            "F001 timing contains complete_gpu max/min > 1.20; "
            "one identical full rerun is required."
        )
        return 4

    print(
        "F001 complete: census and run-local controls recorded; "
        f"F002 Nrep={census['dynamic_primitive_count']}, "
        f"builder ceiling={0.90 * vanilla_moving:.3f} us"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

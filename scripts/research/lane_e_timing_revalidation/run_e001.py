#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
from pathlib import Path

import analysis

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-e-timing-revalidation"
CONFIG = ROOT / "research/lanes/lane-e-timing-revalidation/experiments/002-e001-config.json"
FREEZE = ROOT / "research/lanes/lane-e-timing-revalidation/experiments/003-e001-execution-freeze.json"
CAMPAIGN_ROOT = ROOT / "out/research/lane-e-timing-revalidation/001-timing-revalidation"
SCENARIOS = [
    "static",
    "camera-motion",
    "light-motion",
    "moving-rigid",
    "stable-topology-deforming",
]
TRACKS = ["hwrt", "software"]
COMPARISONS = ["control", "candidate"]


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def verify_freeze(config: dict[str, object]) -> dict[str, object]:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if freeze.get("plan_version") != config["plan_version"]:
        raise RuntimeError("execution freeze/config plan version mismatch")
    if freeze.get("status") != "frozen-before-target-candidate-timing":
        raise RuntimeError("E001 execution freeze is not target-ready")
    for path, expected in freeze["frozen_blobs"].items():
        actual = git("hash-object", path)
        if actual != expected:
            raise RuntimeError(
                f"E001 frozen source drift: {path}: {actual} != {expected}"
            )
    return freeze


def validate_config(config: dict[str, object]) -> None:
    timing = config["timing"]
    gate = config["performance_gate"]
    if config["plan_version"] != "lane-e-timing-revalidation-e001-v3":
        raise RuntimeError("unexpected E001 plan version")
    if timing["environment"] != "dual-context":
        raise RuntimeError("E001 must use dual-context")
    if timing["primary_axis"] != "gpu_timestamp":
        raise RuntimeError("GPU timestamp must remain primary")
    if timing["cpu_wall_role"] != "diagnostic-health-provenance-only":
        raise RuntimeError("CPU wall role drifted")
    if (
        int(timing["warmup_pairs"]) != 4
        or int(timing["measured_pairs"]) != 12
        or int(timing["fresh_process_blocks"]) != 8
        or int(timing["complete_transitions_per_sample"]) != 16
    ):
        raise RuntimeError("E001 sample shape drifted")
    if timing["sample_exclusion"] != "forbidden":
        raise RuntimeError("sample exclusion must remain forbidden")
    if int(timing["instability_rerun_budget"]) != 0:
        raise RuntimeError("instability rerun budget must remain zero")
    if int(timing["completed_campaign_rerun_budget"]) != 0:
        raise RuntimeError("completed campaign rerun budget must remain zero")
    if int(gate["promotion_threshold_percent"]) != 20:
        raise RuntimeError("promotion threshold must remain 20%")
    if int(gate["non_regression_threshold_percent"]) != 20:
        raise RuntimeError("non-regression threshold must remain 20%")
    if not bool(gate["lane_k_5_percent_floor_forbidden"]):
        raise RuntimeError("Lane K 5% floor must remain forbidden")
    if bool(timing["future_state_prebuild"]):
        raise RuntimeError("future-state prebuild must remain forbidden")
    if bool(timing["recurrent_work_moved_to_setup"]):
        raise RuntimeError("recurrent work cannot move to setup")
    orders = timing["comparison_order_by_block"]
    if len(orders) != 8:
        raise RuntimeError("comparison order must cover 8 blocks")
    if sum(order[0] == "control" for order in orders) != 4:
        raise RuntimeError("comparison process position is not 4/4 counterbalanced")


def command_for(
    executable: Path,
    scene: Path,
    output: Path,
    scenario: str,
    track: str,
    comparison: str,
    *,
    validation: bool,
    block: int = 0,
    start_order: str = "AB",
    config: dict[str, object],
) -> list[str]:
    timing = config["timing"]
    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--scene",
        str(scene),
        "--output",
        str(output),
        "--scenario",
        scenario,
        "--track",
        track,
        "--comparison",
        comparison,
    ]
    if validation:
        command.append("--validation")
    else:
        command += [
            "--block",
            str(block),
            "--start-order",
            start_order,
            "--warmup-pairs",
            str(timing["warmup_pairs"]),
            "--measured-pairs",
            str(timing["measured_pairs"]),
            "--transitions",
            str(timing["complete_transitions_per_sample"]),
            "--settle-seconds",
            str(timing["settle_seconds_before_process"]),
        ]
    return command


def run_process(command: list[str], log_path: Path) -> None:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"process failed ({proc.returncode}): {' '.join(command)}\n{proc.stdout}"
        )


def validate_rows(rows: list[dict[str, object]]) -> None:
    if len(rows) != 4:
        raise RuntimeError(f"validation process must return 4 rows, got {len(rows)}")
    by_state: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        if row["quality_passed"] != "1":
            raise RuntimeError("quality_passed != 1")
        for key in [
            "hit_mismatch",
            "nearest_hit_tie_mismatch",
            "visibility_mismatch",
            "producer_semantic_error",
            "traversal_runtime_error",
            "storage_failure",
            "static_owner_mutation",
            "unrelated_owner_mutation",
        ]:
            if int(row[key]) != 0:
                raise RuntimeError(f"validation {key} != 0")
        by_state.setdefault(str(row["state"]), []).append(row)

    for state, state_rows in by_state.items():
        if len(state_rows) != 2:
            raise RuntimeError(f"{state} validation does not have A/B rows")
        a, b = sorted(state_rows, key=lambda row: row["role"])
        for key in ["workload_digest", "resolved_output_digest", "geometry_input_digest"]:
            if a[key] != b[key]:
                raise RuntimeError(f"{state} validation digest mismatch for {key}")
        for row in state_rows:
            current = int(row["current_bytes"])
            peak = int(row["true_peak_bytes"])
            if row.get("allocation_lifetime_complete") != "1":
                raise RuntimeError(
                    f"{state} allocation lifetime accounting is incomplete"
                )
            if current <= 0 or peak < current:
                raise RuntimeError(
                    f"{state} allocation byte accounting is invalid"
                )
        for key in [
            "device_name",
            "driver_name",
            "driver_info",
            "api_version",
            "timestamp_period_ns",
        ]:
            if a[key] != b[key]:
                raise RuntimeError(f"{state} validation provenance mismatch for {key}")


def health_check_timing_rows(rows: list[dict[str, object]]) -> None:
    if len(rows) != 32:
        raise RuntimeError(f"timing process must return 32 rows, got {len(rows)}")
    measured = [row for row in rows if row["phase"] == "measured"]
    warmup = [row for row in rows if row["phase"] == "warmup"]
    if len(measured) != 24 or len(warmup) != 8:
        raise RuntimeError("timing warmup/measured row shape drifted")
    pairs: dict[tuple[str, int], set[str]] = {}
    for row in rows:
        gpu = float(row["gpu_us"])
        wall = float(row["wall_us"])
        if not math.isfinite(gpu) or not math.isfinite(wall) or gpu <= 0 or wall <= 0:
            raise RuntimeError("non-positive/non-finite timing")
        if wall < gpu:
            raise RuntimeError("complete CPU wall is smaller than GPU timestamp")
        if row.get("allocation_lifetime_complete") != "1":
            raise RuntimeError("timed allocation lifetime accounting is incomplete")
        key = (str(row["phase"]), int(row["pair_index"]))
        pairs.setdefault(key, set()).add(str(row["role"]))
    if any(roles != {"A", "B"} for roles in pairs.values()):
        raise RuntimeError("incomplete timing pair structure")


def same_provenance(rows: list[dict[str, object]]) -> dict[str, object]:
    keys = ["device_name", "driver_name", "driver_info", "api_version", "timestamp_period_ns"]
    values = {}
    for key in keys:
        unique = {str(row[key]) for row in rows}
        if len(unique) != 1:
            raise RuntimeError(f"campaign provenance changed for {key}: {sorted(unique)}")
        values[key] = next(iter(unique))
    return values


def memory_summary_rows(summary: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for scenario, tracks in summary["results"].items():
        for track, result in tracks.items():
            memory = result["memory"]
            rows.append({"scenario": scenario, "track": track, **memory})
    return rows


def process_summary_rows(summary: dict[str, object]) -> list[dict[str, object]]:
    return sorted(
        summary["process_rows"],
        key=lambda row: (
            str(row["scenario"]),
            str(row["track"]),
            str(row["comparison"]),
            int(row["block"]),
        ),
    )


def final_class_outcomes(summary: dict[str, object]) -> dict[str, object]:
    outcomes: dict[str, object] = {}
    falsified = False
    for scenario in ["moving-rigid", "stable-topology-deforming"]:
        track_results = summary["results"][scenario]
        classifications = {
            track: result["performance"]["classification"]
            for track, result in track_results.items()
        }
        if any(value == "detected >=20% regression" for value in classifications.values()):
            status = "fresh same-run evidence falsifies previous Lane E performance claim"
            falsified = True
        elif all(value == ">=20% detected improvement" for value in classifications.values()):
            status = f"{scenario} timing revalidated"
        else:
            status = "measurement-limited"
        outcomes[scenario] = {
            "status": status,
            "tracks": classifications,
            "memory": {
                track: result["memory"]["classification"]
                for track, result in track_results.items()
            },
        }

    stable_regressions = []
    for scenario in ["static", "camera-motion", "light-motion"]:
        for track, result in summary["results"][scenario].items():
            if result["performance"]["classification"] == "detected >=20% regression":
                stable_regressions.append(f"{scenario}/{track}")

    return {
        "classes": outcomes,
        "stable_guard_regressions": stable_regressions,
        "fresh_same_run_evidence_falsifies_previous_lane_e_performance_claim": falsified,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=ROOT / os.environ.get("PHOS_GI_BUILD_DIR", "build/release"),
    )
    parser.add_argument(
        "--scene",
        type=Path,
        default=ROOT / "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf",
    )
    parser.add_argument("--validation-only", action="store_true")
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--resume-root", type=Path)
    args = parser.parse_args()

    if git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError(f"E001 must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("E001 requires a clean worktree")

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    validate_config(config)
    freeze = verify_freeze(config)

    executable = args.build_dir / "phos-lane-e-e001-process"
    scene = args.scene.resolve()
    if not executable.is_file():
        raise RuntimeError(f"missing executable: {executable}")
    if not scene.is_file():
        raise RuntimeError(f"missing scene: {scene}")

    if args.resume_root:
        root = args.resume_root.resolve()
        if not root.is_dir():
            raise RuntimeError(f"resume root does not exist: {root}")
    else:
        env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
        root = args.artifact_dir or (Path(env_root) if env_root else None)
        if root is None:
            raise RuntimeError("use research:record or pass --artifact-dir")
        root = root.resolve()
        root.mkdir(parents=True, exist_ok=True)

    summary_path = root / "e001-summary.json"
    if summary_path.exists():
        raise RuntimeError("completed campaign rerun budget is zero")

    if not args.validation_only:
        formal_root = (
            ROOT
            / "out/research/lane-e-timing-revalidation"
            / "001-timing-revalidation"
        )
        completed = sorted(formal_root.glob("*/e001-summary.json"))
        completed = [path for path in completed if path.parent != root]
        if completed:
            raise RuntimeError(
                "E001 completed-campaign rerun budget is zero; existing summary: "
                + ", ".join(str(path.relative_to(ROOT)) for path in completed)
            )
        incomplete = []
        invalid = []
        for path in formal_root.glob("*/e001-progress.json"):
            if path.parent == root:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            state = str(payload.get("state"))
            if state in {"validation-complete", "validation-failed"}:
                # These artifacts contain no accepted timing evidence.
                continue
            if state == "campaign-invalid-no-rerun":
                invalid.append(path.parent)
                continue
            if state != "complete":
                timing_rows = []
                for csv_path in path.parent.glob("timing/*.csv"):
                    if csv_path.stat().st_size > 0:
                        timing_rows.extend(read_csv(csv_path))
                if any(row.get("phase") == "measured" for row in timing_rows):
                    invalid.append(path.parent)
                elif payload.get("git_commit") == git("rev-parse", "HEAD"):
                    incomplete.append(path.parent)
                # A pre-measured interrupted artifact from an older source
                # commit may be superseded only by the new prospective freeze.
        if invalid:
            raise RuntimeError(
                "E001 contains measured rows from an invalid interrupted campaign; "
                "zero-rerun policy forbids a new campaign: "
                + ", ".join(str(path.relative_to(ROOT)) for path in invalid)
            )
        if incomplete and not args.resume_root:
            raise RuntimeError(
                "E001 has an interrupted same-source campaign; resume exactly that "
                "artifact root with --resume-root instead of starting fresh: "
                + ", ".join(str(path.relative_to(ROOT)) for path in incomplete)
            )

    progress_path = root / "e001-progress.json"
    if progress_path.exists():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if progress.get("plan_version") != config["plan_version"]:
            raise RuntimeError("resume root uses a different frozen plan")
        if progress.get("git_commit") != git("rev-parse", "HEAD"):
            raise RuntimeError("resume root was created by a different source commit")
        if progress.get("state") == "campaign-invalid-no-rerun":
            raise RuntimeError("invalid E001 campaign cannot be resumed")
        if progress.get("state") == "complete":
            raise RuntimeError("completed E001 campaign cannot be resumed")
    else:
        progress = {
            "schema_version": 1,
            "plan_version": config["plan_version"],
            "git_commit": git("rev-parse", "HEAD"),
            "state": "validating",
            "completed_validations": [],
            "completed_processes": [],
        }

    def save_progress() -> None:
        progress_path.write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    save_progress()
    (root / "e001-config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "e001-source-provenance.json").write_text(
        json.dumps(
            {
                "git_commit": git("rev-parse", "HEAD"),
                "plan_version": config["plan_version"],
                "frozen_blobs": freeze["frozen_blobs"],
                "execution_freeze_blob": git("hash-object", str(FREEZE.relative_to(ROOT))),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "e001-input-provenance.json").write_text(
        json.dumps(
            {
                "scene": str(scene),
                "scene_sha256": sha256_file(scene),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    validation_rows: list[dict[str, object]] = []
    try:
        for scenario in SCENARIOS:
            for track in TRACKS:
                for comparison in COMPARISONS:
                    process_id = f"{scenario}-{track}-{comparison}"
                    output = root / "validation" / f"{process_id}.csv"
                    log = root / "validation" / f"{process_id}.log"
                    output.parent.mkdir(parents=True, exist_ok=True)
                    if process_id not in progress["completed_validations"]:
                        progress["current"] = {
                            "phase": "validation",
                            "process_id": process_id,
                        }
                        save_progress()
                        run_process(
                            command_for(
                                executable,
                                scene,
                                output,
                                scenario,
                                track,
                                comparison,
                                validation=True,
                                config=config,
                            ),
                            log,
                        )
                        rows = read_csv(output)
                        validate_rows(rows)
                        progress["completed_validations"].append(process_id)
                        save_progress()
                    rows = read_csv(output)
                    validate_rows(rows)
                    for row in rows:
                        row["process_id"] = process_id
                    validation_rows.extend(rows)

        provenance = same_provenance(validation_rows)
        if provenance["device_name"] != config["target_gpu"]:
            raise RuntimeError(
                f"unexpected target device: {provenance['device_name']}"
            )
        write_csv(root / "e001-validation-summary.csv", validation_rows)
        (root / "e001-validation-summary.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "process_count": 20,
                    "row_count": len(validation_rows),
                    "correctness_zero_fields_passed": True,
                    "workload_identity_match": True,
                    "resolved_output_identity_match": True,
                    "geometry_input_digest_match": True,
                    "allocation_lifetime_accounting_complete": True,
                    "device_driver_api_timestamp_provenance_consistent": True,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "e001-device-provenance.json").write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        if args.validation_only:
            progress["state"] = "validation-complete"
            progress.pop("current", None)
            save_progress()
            print("GPU:", provenance["device_name"])
            print(f"E001 validation artifacts: {root}")
            return 0

        progress["state"] = "timing"
        save_progress()
        raw_rows: list[dict[str, object]] = []
        timing = config["timing"]
        start_orders = timing["start_order_by_block"]
        comparison_orders = timing["comparison_order_by_block"]

        for scenario in SCENARIOS:
            for track in TRACKS:
                for block in range(8):
                    for comparison in comparison_orders[block]:
                        process_id = f"{scenario}-{track}-{comparison}-b{block:02d}"
                        output = root / "timing" / f"{process_id}.csv"
                        log = root / "timing" / f"{process_id}.log"
                        output.parent.mkdir(parents=True, exist_ok=True)
                        if process_id not in progress["completed_processes"]:
                            recovered_complete = False
                            if output.exists() and output.stat().st_size > 0:
                                partial_rows = read_csv(output)
                                try:
                                    health_check_timing_rows(partial_rows)
                                except RuntimeError:
                                    if any(
                                        row.get("phase") == "measured"
                                        for row in partial_rows
                                    ):
                                        progress["state"] = "campaign-invalid-no-rerun"
                                        progress["invalid_process_id"] = process_id
                                        save_progress()
                                        raise RuntimeError(
                                            "partial E001 process contains measured rows "
                                            f"and cannot be rerun: {process_id}"
                                        )
                                    output.unlink()
                                else:
                                    # The child finished and flushed the full
                                    # process before the parent progress update.
                                    # Recover it as immutable evidence; do not
                                    # rerun a completed process.
                                    progress["completed_processes"].append(process_id)
                                    progress["state"] = "timing"
                                    save_progress()
                                    recovered_complete = True
                            if not recovered_complete:
                                progress["current"] = {
                                    "phase": "timing",
                                    "process_id": process_id,
                                }
                                save_progress()
                                try:
                                        run_process(
                                        command_for(
                                            executable,
                                            scene,
                                            output,
                                            scenario,
                                            track,
                                            comparison,
                                            validation=False,
                                            block=block,
                                            start_order=start_orders[block],
                                            config=config,
                                        ),
                                        log,
                                    )
                                except BaseException:
                                    partial_rows = (
                                        read_csv(output)
                                        if output.exists() and output.stat().st_size > 0
                                        else []
                                    )
                                    if any(
                                        row.get("phase") == "measured"
                                        for row in partial_rows
                                    ):
                                        progress["state"] = "campaign-invalid-no-rerun"
                                        progress["invalid_process_id"] = process_id
                                    else:
                                        progress["state"] = "interrupted-resumable-missing-process"
                                    save_progress()
                                    raise
                                rows = read_csv(output)
                                health_check_timing_rows(rows)
                                progress["completed_processes"].append(process_id)
                                progress["state"] = "timing"
                                save_progress()
                        rows = read_csv(output)
                        health_check_timing_rows(rows)
                        for row in rows:
                            row["process_id"] = process_id
                        raw_rows.extend(rows)

        if len(progress["completed_processes"]) != 160:
            raise RuntimeError("formal timing requires exactly 160 fresh processes")
        if len(raw_rows) != 5120:
            raise RuntimeError(
                f"formal timing requires 5120 retained raw rows, got {len(raw_rows)}"
            )
        timing_provenance = same_provenance(raw_rows)
        if timing_provenance != provenance:
            raise RuntimeError("validation/timing device provenance changed")

        result = analysis.summarize_campaign(raw_rows)
        decisions = final_class_outcomes(result)

        write_csv(root / "e001-raw.csv", raw_rows)
        write_csv(
            root / "e001-control-raw.csv",
            [row for row in raw_rows if row["comparison"] == "control"],
        )
        write_csv(
            root / "e001-candidate-raw.csv",
            [row for row in raw_rows if row["comparison"] == "candidate"],
        )
        write_csv(root / "e001-process-summary.csv", process_summary_rows(result))
        write_csv(root / "e001-memory-summary.csv", memory_summary_rows(result))

        summary = {
            "schema_version": 2,
            "plan_version": config["plan_version"],
            "git_commit": git("rev-parse", "HEAD"),
            "branch": EXPECTED_BRANCH,
            "target_gpu": config["target_gpu"],
            "accepted_environment": "dual-context",
            "primary_axis": "gpu_timestamp",
            "cpu_wall_role": "diagnostic-health-provenance-only",
            "heavy_boundary_floor_percent": 20,
            "sample_exclusion": "none",
            "instability_rerun_budget": 0,
            "completed_campaign_rerun_budget": 0,
            "validation_process_count": 20,
            "timing_process_count": 160,
            "raw_row_count": len(raw_rows),
            "all_samples_retained": True,
            "correctness": "PASS",
            "results": result["results"],
            "decision": decisions,
        }
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        required = [str(name) for name in config["artifact_schema"]["required"]]
        missing = [name for name in required if not (root / name).is_file()]
        if missing:
            raise RuntimeError(f"E001 required artifacts missing: {missing}")

        progress["state"] = "complete"
        progress.pop("current", None)
        save_progress()

        print("GPU:", provenance["device_name"])
        print(f"E001 artifacts: {root}")
        print(json.dumps(decisions, indent=2, sort_keys=True))
        return 0
    except BaseException:
        if progress.get("state") not in {
            "campaign-invalid-no-rerun",
            "interrupted-resumable-missing-process",
        }:
            progress["state"] = (
                "validation-failed"
                if progress.get("current", {}).get("phase") == "validation"
                else "interrupted-resumable-missing-process"
            )
        save_progress()
        raise


if __name__ == "__main__":
    raise SystemExit(main())

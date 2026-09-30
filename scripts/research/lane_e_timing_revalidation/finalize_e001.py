#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import analysis
import run_e001 as runner

FREEZE_REL = Path(
    "research/lanes/lane-e-timing-revalidation/experiments/"
    "003-e001-execution-freeze.json"
)


def timestamp_serialization_matches(validation: str, timing: str) -> bool:
    """Accept only the known C++ stream-precision rendering difference."""
    if validation == timing:
        return True
    try:
        # Validation used the default ostream precision (6 significant digits);
        # timing used std::setprecision(17) on the same float value.
        return format(float(timing), ".6g") == validation
    except ValueError:
        return False


def expected_timing_process_ids() -> set[str]:
    return {
        f"{scenario}-{track}-{comparison}-b{block:02d}"
        for scenario in runner.SCENARIOS
        for track in runner.TRACKS
        for block in range(8)
        for comparison in runner.COMPARISONS
    }


def expected_validation_process_ids() -> set[str]:
    return {
        f"{scenario}-{track}-{comparison}"
        for scenario in runner.SCENARIOS
        for track in runner.TRACKS
        for comparison in runner.COMPARISONS
    }


def verify_measured_source(
    source: dict[str, object],
    progress: dict[str, object],
    config: dict[str, object],
) -> str:
    if source["plan_version"] != config["plan_version"]:
        raise RuntimeError("source/config plan version mismatch")
    source_commit = str(source["git_commit"])
    if progress.get("git_commit") != source_commit:
        raise RuntimeError("progress/source commit mismatch")
    if progress.get("plan_version") != config["plan_version"]:
        raise RuntimeError("progress/config plan version mismatch")

    runner.git("cat-file", "-e", f"{source_commit}^{{commit}}")
    for path, expected_blob in source["frozen_blobs"].items():
        actual_blob = runner.git("rev-parse", f"{source_commit}:{path}")
        if actual_blob != expected_blob:
            raise RuntimeError(
                f"measured source blob mismatch: {path}: "
                f"{actual_blob} != {expected_blob}"
            )
    freeze_blob = runner.git("rev-parse", f"{source_commit}:{FREEZE_REL}")
    if freeze_blob != source["execution_freeze_blob"]:
        raise RuntimeError("measured execution-freeze blob mismatch")
    return source_commit


def validate_validation_summary(
    root: Path,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows = runner.read_csv(root / "e001-validation-summary.csv")
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["process_id"]), []).append(row)
    if set(grouped) != expected_validation_process_ids():
        raise RuntimeError("validation process identity set is incomplete")
    for process_rows in grouped.values():
        runner.validate_rows(process_rows)
    if len(rows) != 80:
        raise RuntimeError(f"expected 80 validation rows, got {len(rows)}")

    summary = json.loads(
        (root / "e001-validation-summary.json").read_text(encoding="utf-8")
    )
    if (
        summary.get("passed") is not True
        or int(summary.get("process_count", 0)) != 20
        or int(summary.get("row_count", 0)) != 80
    ):
        raise RuntimeError("validation summary is not an accepted PASS")
    return rows, runner.same_provenance(rows)


def load_timing_rows(
    root: Path,
    progress: dict[str, object],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    timing_dir = root / "timing"
    files = sorted(timing_dir.glob("*.csv"))
    file_ids = {path.stem for path in files}
    expected_ids = expected_timing_process_ids()
    if len(files) != 160 or file_ids != expected_ids:
        raise RuntimeError("timing process file set is not exactly the frozen 160")

    completed = [str(value) for value in progress.get("completed_processes", [])]
    if len(completed) != 160 or set(completed) != expected_ids:
        raise RuntimeError("progress does not record exactly 160 completed processes")

    raw_rows: list[dict[str, object]] = []
    for path in files:
        rows = runner.read_csv(path)
        runner.health_check_timing_rows(rows)
        if len(rows) != 32:
            raise RuntimeError(f"{path.name}: expected 32 rows, got {len(rows)}")
        for row in rows:
            row["process_id"] = path.stem
        raw_rows.extend(rows)

    if len(raw_rows) != 5120:
        raise RuntimeError(f"expected 5120 timing rows, got {len(raw_rows)}")
    return raw_rows, runner.same_provenance(raw_rows)


def compare_provenance(
    validation: dict[str, object],
    timing: dict[str, object],
) -> dict[str, object]:
    exact_keys = ["device_name", "driver_name", "driver_info", "api_version"]
    for key in exact_keys:
        if str(validation[key]) != str(timing[key]):
            raise RuntimeError(
                f"real validation/timing provenance mismatch for {key}: "
                f"{validation[key]!r} != {timing[key]!r}"
            )

    validation_timestamp = str(validation["timestamp_period_ns"])
    timing_timestamp = str(timing["timestamp_period_ns"])
    if not timestamp_serialization_matches(
        validation_timestamp,
        timing_timestamp,
    ):
        raise RuntimeError(
            "timestamp period differs beyond the known serialization bug: "
            f"{validation_timestamp!r} != {timing_timestamp!r}"
        )

    return {
        "exact_fields": exact_keys,
        "timestamp_period_ns": {
            "validation_rendering": validation_timestamp,
            "timing_rendering": timing_timestamp,
            "accepted_reason": (
                "validation used default ostream precision while timing used "
                "std::setprecision(17) on the same runtime float"
            ),
            "default_6_significant_digit_rendering_matches": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()

    if runner.git("branch", "--show-current") != runner.EXPECTED_BRANCH:
        raise RuntimeError(f"must run on {runner.EXPECTED_BRANCH}")
    if runner.git("status", "--porcelain"):
        raise RuntimeError("finalization requires a clean worktree")
    if not root.is_dir():
        raise RuntimeError(f"artifact root does not exist: {root}")
    if (root / "e001-summary.json").exists():
        raise RuntimeError("campaign is already finalized")

    config = json.loads((root / "e001-config.json").read_text(encoding="utf-8"))
    runner.validate_config(config)
    source = json.loads(
        (root / "e001-source-provenance.json").read_text(encoding="utf-8")
    )
    progress_path = root / "e001-progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8"))

    source_commit = verify_measured_source(source, progress, config)

    input_provenance = json.loads(
        (root / "e001-input-provenance.json").read_text(encoding="utf-8")
    )
    scene = Path(str(input_provenance["scene"]))
    if not scene.is_file():
        raise RuntimeError(f"measured input scene is missing: {scene}")
    if runner.sha256_file(scene) != input_provenance["scene_sha256"]:
        raise RuntimeError("measured input scene digest changed")

    validation_rows, validation_provenance = validate_validation_summary(root)
    if validation_provenance["device_name"] != config["target_gpu"]:
        raise RuntimeError("validation did not run on the frozen target GPU")

    raw_rows, timing_provenance = load_timing_rows(root, progress)
    provenance_recovery = compare_provenance(
        validation_provenance,
        timing_provenance,
    )

    result = analysis.summarize_campaign(raw_rows)
    decisions = runner.final_class_outcomes(result)

    runner.write_csv(root / "e001-raw.csv", raw_rows)
    runner.write_csv(
        root / "e001-control-raw.csv",
        [row for row in raw_rows if row["comparison"] == "control"],
    )
    runner.write_csv(
        root / "e001-candidate-raw.csv",
        [row for row in raw_rows if row["comparison"] == "candidate"],
    )
    runner.write_csv(
        root / "e001-process-summary.csv",
        runner.process_summary_rows(result),
    )
    runner.write_csv(
        root / "e001-memory-summary.csv",
        runner.memory_summary_rows(result),
    )

    recovery = {
        "schema_version": 1,
        "plan_version": config["plan_version"],
        "measured_source_commit": source_commit,
        "measurement_rerun": False,
        "validation_process_count": 20,
        "timing_process_count": 160,
        "raw_row_count": len(raw_rows),
        "reason": "post-measurement provenance serialization recovery",
        "provenance": provenance_recovery,
    }
    (root / "e001-finalization-recovery.json").write_text(
        json.dumps(recovery, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "schema_version": 2,
        "plan_version": config["plan_version"],
        "git_commit": source_commit,
        "branch": runner.EXPECTED_BRANCH,
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
        "postprocessing_recovery": "e001-finalization-recovery.json",
        "results": result["results"],
        "decision": decisions,
    }
    (root / "e001-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    required = [str(name) for name in config["artifact_schema"]["required"]]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise RuntimeError(f"E001 required artifacts missing: {missing}")

    progress["state"] = "complete"
    progress.pop("current", None)
    progress["postprocessing_recovery"] = {
        "file": "e001-finalization-recovery.json",
        "measurement_rerun": False,
    }
    progress_path.write_text(
        json.dumps(progress, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("GPU:", validation_provenance["device_name"])
    print(f"E001 finalized artifacts: {root}")
    print(json.dumps(decisions, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

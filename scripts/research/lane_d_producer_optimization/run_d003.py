#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import statistics
import subprocess

CASES = ("static", "camera-motion", "light-motion")
VARIANTS = ("baseline-a001", "two-pass-staged", "packed-one-pass")


def median(values: list[float]) -> float:
    if not values:
        raise ValueError("median requires values")
    return float(statistics.median(values))


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="build/release")
    parser.add_argument(
        "--scene",
        default="assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf",
    )
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--validation", action="store_true")
    args = parser.parse_args()

    if args.iterations <= 0:
        parser.error("--iterations must be positive")
    if args.repeats <= 0:
        parser.error("--repeats must be positive")

    executable = (
        Path(args.build_dir)
        / "src/research/lane_d_producer_optimization"
        / "phos-lane-d-d003"
    )
    if not executable.exists():
        raise SystemExit(
            f"D003 executable not found: {executable}; run 'mise run build' first"
        )
    if not Path(args.scene).exists():
        raise SystemExit(
            f"D003 scene not found: {args.scene}; run 'mise run assets' first"
        )

    artifact_root = Path(
        os.environ.get(
            "PHOS_RESEARCH_ARTIFACT_DIR",
            (
                "out/research/lane-d-producer-optimization/"
                "003-one-pass-owner-selection/manual"
            ),
        )
    )
    artifact_root.mkdir(parents=True, exist_ok=True)
    commit = git_head()

    rows: list[dict[str, object]] = []
    raw_runs: list[dict[str, object]] = []

    for repeat in range(args.repeats):
        for case in CASES:
            output_dir = artifact_root / f"repeat-{repeat + 1:02d}" / case
            output_dir.mkdir(parents=True, exist_ok=True)

            command = [
                "bash",
                "scripts/run_with_vulkan.sh",
                str(executable),
                "--scene",
                args.scene,
                "--case",
                case,
                "--iterations",
                str(args.iterations),
                "--output-dir",
                str(output_dir),
            ]
            if args.validation:
                command.append("--validation")

            env = os.environ.copy()
            env["PHOS_RESEARCH_GIT_COMMIT"] = commit
            print("+", " ".join(command), flush=True)
            completed = subprocess.run(command, env=env)
            if completed.returncode:
                return completed.returncode

            metrics_path = output_dir / "metrics.json"
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            if not metrics.get("cross_variant_correct", False):
                raise SystemExit(
                    f"D003 correctness gate failed: repeat={repeat + 1} case={case}"
                )

            raw_runs.append(
                {
                    "repeat": repeat + 1,
                    "case": case,
                    "metrics_path": str(metrics_path.resolve()),
                    "metrics": metrics,
                }
            )

            baseline = metrics["baseline_a001"]
            bt = baseline["timings_us"]
            bm = baseline["memory"]
            rows.append(
                {
                    "repeat": repeat + 1,
                    "case": case,
                    "variant": "baseline-a001",
                    "correct": baseline["correct"],
                    "visible_probe_count": baseline["visible_probe_count"],
                    "work_item_count": baseline["work_item_count"],
                    "overflow_flag": baseline["overflow_flag"],
                    "workload_id": baseline["workload_id"],
                    "visibility_reset_us": "",
                    "visibility_select_us": "",
                    "producer_reset_us": "",
                    "producer_emit_us": bt["producer_emit"],
                    "finalize_us": "",
                    "producer_total_us": bt["producer_total"],
                    "end_to_end_us": bt["end_to_end"],
                    "persistent_bytes": bm["persistent_bytes"],
                    "transient_bytes": bm["transient_bytes"],
                    "visibility_bytes": bm["visibility_bytes"],
                    "stream_capacity_bytes": bm["stream_capacity_bytes"],
                    "actual_stream_bytes": int(baseline["work_item_count"]) * 64,
                    "producer_scratch_bytes": "",
                }
            )

            two = metrics["two-pass-staged"]
            tt = two["timings_us"]
            tm = two["memory"]
            rows.append(
                {
                    "repeat": repeat + 1,
                    "case": case,
                    "variant": "two-pass-staged",
                    "correct": two["correct"],
                    "visible_probe_count": two["visible_probe_count"],
                    "work_item_count": two["work_item_count"],
                    "overflow_flag": two["overflow_flag"],
                    "workload_id": two["workload_id"],
                    "visibility_reset_us": (
                        tt["visibility_reset"] + tt["owner_reset"]
                    ),
                    "visibility_select_us": (
                        tt["visibility_depth"] + tt["visibility_owner"]
                    ),
                    "producer_reset_us": tt["producer_reset"],
                    "producer_emit_us": tt["producer_emit"],
                    "finalize_us": tt["finalize"],
                    "producer_total_us": tt["producer_total"],
                    "end_to_end_us": tt["end_to_end"],
                    "persistent_bytes": tm["persistent_bytes"],
                    "transient_bytes": tm["transient_bytes"],
                    "visibility_bytes": tm["visibility_bytes"],
                    "stream_capacity_bytes": tm["stream_capacity_bytes"],
                    "actual_stream_bytes": tm["actual_stream_bytes"],
                    "producer_scratch_bytes": tm["producer_scratch_bytes"],
                }
            )

            packed = metrics["packed-one-pass"]
            pt = packed["timings_us"]
            pm = packed["memory"]
            rows.append(
                {
                    "repeat": repeat + 1,
                    "case": case,
                    "variant": "packed-one-pass",
                    "correct": packed["correct"],
                    "visible_probe_count": packed["visible_probe_count"],
                    "work_item_count": packed["work_item_count"],
                    "overflow_flag": packed["overflow_flag"],
                    "workload_id": packed["workload_id"],
                    "visibility_reset_us": pt["visibility_reset"],
                    "visibility_select_us": pt["visibility_select"],
                    "producer_reset_us": pt["producer_reset"],
                    "producer_emit_us": pt["producer_emit"],
                    "finalize_us": pt["finalize"],
                    "producer_total_us": pt["producer_total"],
                    "end_to_end_us": pt["end_to_end"],
                    "persistent_bytes": pm["persistent_bytes"],
                    "transient_bytes": pm["transient_bytes"],
                    "visibility_bytes": pm["visibility_bytes"],
                    "stream_capacity_bytes": pm["stream_capacity_bytes"],
                    "actual_stream_bytes": pm["actual_stream_bytes"],
                    "producer_scratch_bytes": pm["producer_scratch_bytes"],
                }
            )

    fieldnames = list(rows[0].keys())
    with (artifact_root / "d003.csv").open(
        "w", newline="", encoding="utf-8"
    ) as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    timing_fields = (
        "producer_emit_us",
        "producer_total_us",
        "end_to_end_us",
    )
    detailed_fields = (
        "visibility_reset_us",
        "visibility_select_us",
        "producer_reset_us",
        "finalize_us",
    )

    aggregate: dict[str, dict[str, dict[str, object]]] = {}
    for case in CASES:
        aggregate[case] = {}
        for variant in VARIANTS:
            selected = [
                row
                for row in rows
                if row["case"] == case and row["variant"] == variant
            ]
            if len(selected) != args.repeats:
                raise SystemExit(
                    f"missing D003 rows: case={case} variant={variant}"
                )
            sample = selected[0]
            timings = {
                field: median([float(row[field]) for row in selected])
                for field in timing_fields
            }
            for field in detailed_fields:
                values = [
                    float(row[field])
                    for row in selected
                    if row[field] != ""
                ]
                timings[field] = median(values) if values else None

            aggregate[case][variant] = {
                "all_correct": all(bool(row["correct"]) for row in selected),
                "repeats": len(selected),
                "visible_probe_count": sample["visible_probe_count"],
                "work_item_count": sample["work_item_count"],
                "overflow_flag_max": max(
                    int(row["overflow_flag"]) for row in selected
                ),
                "timings_us_median": timings,
                "memory": {
                    "persistent_bytes": sample["persistent_bytes"],
                    "transient_bytes": sample["transient_bytes"],
                    "visibility_bytes": sample["visibility_bytes"],
                    "stream_capacity_bytes": sample["stream_capacity_bytes"],
                    "actual_stream_bytes": sample["actual_stream_bytes"],
                    "producer_scratch_bytes": sample[
                        "producer_scratch_bytes"
                    ],
                },
            }

    summary = {
        "experiment": "003-one-pass-owner-selection",
        "required_feature": "shaderBufferInt64Atomics",
        "git_commit": commit,
        "scene": args.scene,
        "iterations": args.iterations,
        "repeats": args.repeats,
        "validation": args.validation,
        "artifact_root": str(artifact_root.resolve()),
        "aggregate": aggregate,
        "runs": raw_runs,
    }
    (artifact_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        "D003 correctness passed for "
        f"{args.repeats} repeats x {len(CASES)} cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

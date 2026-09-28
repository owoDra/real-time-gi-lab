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
VARIANTS = ("full", "depth-reuse", "owner-reuse")


def median(values: list[float]) -> float:
    if not values:
        raise ValueError("median requires at least one value")
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
        / "phos-lane-d-producer-optimization"
    )
    if not executable.exists():
        raise SystemExit(
            f"D001 executable not found: {executable}; run 'mise run build' first"
        )
    if not Path(args.scene).exists():
        raise SystemExit(
            f"D001 scene not found: {args.scene}; run 'mise run assets' first"
        )

    artifact_root = Path(
        os.environ.get(
            "PHOS_RESEARCH_ARTIFACT_DIR",
            (
                "out/research/lane-d-producer-optimization/"
                "001-visibility-reuse/manual"
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
                    f"D001 correctness gate failed: repeat={repeat + 1} case={case}"
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
            baseline_t = baseline["timings_us"]
            baseline_m = baseline["memory"]
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
                    "producer_total_us": baseline_t["producer_total"],
                    "incremental_producer_us": baseline_t["producer_total"],
                    "standalone_producer_us": baseline_t["producer_total"],
                    "incremental_end_to_end_us": baseline_t["end_to_end"],
                    "standalone_end_to_end_us": baseline_t["end_to_end"],
                    "producer_emit_us": baseline_t["producer_emit"],
                    "visibility_depth_us": baseline_t["visibility_depth"],
                    "visibility_owner_us": baseline_t["visibility_owner"],
                    "renderer_prerequisite_us": 0.0,
                    "persistent_bytes": baseline_m["persistent_bytes"],
                    "transient_bytes": baseline_m["transient_bytes"],
                    "stream_capacity_bytes": baseline_m["max_stream_bytes"],
                    "actual_stream_bytes": (
                        int(baseline["work_item_count"]) * 64
                    ),
                    "reused_visibility_bytes": 0,
                    "producer_scratch_bytes": "",
                }
            )

            for variant_name in VARIANTS:
                variant = metrics["variants"][variant_name]
                timings = variant["timings_us"]
                memory = variant["memory"]
                rows.append(
                    {
                        "repeat": repeat + 1,
                        "case": case,
                        "variant": variant_name,
                        "correct": variant["correct"],
                        "visible_probe_count": variant["visible_probe_count"],
                        "work_item_count": variant["work_item_count"],
                        "overflow_flag": variant["overflow_flag"],
                        "workload_id": variant["workload_id"],
                        "producer_total_us": timings["standalone_producer"],
                        "incremental_producer_us": timings[
                            "incremental_producer"
                        ],
                        "standalone_producer_us": timings[
                            "standalone_producer"
                        ],
                        "incremental_end_to_end_us": timings[
                            "incremental_end_to_end"
                        ],
                        "standalone_end_to_end_us": timings[
                            "standalone_end_to_end"
                        ],
                        "producer_emit_us": timings["producer_emit"],
                        "visibility_depth_us": timings["visibility_depth"],
                        "visibility_owner_us": timings["visibility_owner"],
                        "renderer_prerequisite_us": timings[
                            "renderer_prerequisite"
                        ],
                        "persistent_bytes": memory[
                            "gi_owned_persistent_bytes"
                        ],
                        "transient_bytes": memory[
                            "gi_owned_transient_bytes"
                        ],
                        "stream_capacity_bytes": memory[
                            "stream_capacity_bytes"
                        ],
                        "actual_stream_bytes": memory["actual_stream_bytes"],
                        "reused_visibility_bytes": memory[
                            "reused_visibility_bytes"
                        ],
                        "producer_scratch_bytes": memory[
                            "producer_scratch_bytes"
                        ],
                    }
                )

    fieldnames = list(rows[0].keys())
    with (artifact_root / "d001.csv").open(
        "w", newline="", encoding="utf-8"
    ) as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    aggregate: dict[str, dict[str, dict[str, object]]] = {}
    timing_fields = (
        "incremental_producer_us",
        "standalone_producer_us",
        "incremental_end_to_end_us",
        "standalone_end_to_end_us",
        "producer_emit_us",
        "visibility_depth_us",
        "visibility_owner_us",
        "renderer_prerequisite_us",
    )

    for case in CASES:
        aggregate[case] = {}
        for variant in ("baseline-a001", *VARIANTS):
            selected = [
                row
                for row in rows
                if row["case"] == case and row["variant"] == variant
            ]
            if len(selected) != args.repeats:
                raise SystemExit(
                    f"missing D001 rows: case={case} variant={variant}"
                )

            sample = selected[0]
            aggregate[case][variant] = {
                "all_correct": all(bool(row["correct"]) for row in selected),
                "repeats": len(selected),
                "visible_probe_count": sample["visible_probe_count"],
                "work_item_count": sample["work_item_count"],
                "overflow_flag_max": max(
                    int(row["overflow_flag"]) for row in selected
                ),
                "timings_us_median": {
                    field: median(
                        [float(row[field]) for row in selected]
                    )
                    for field in timing_fields
                },
                "memory": {
                    "persistent_bytes": sample["persistent_bytes"],
                    "transient_bytes": sample["transient_bytes"],
                    "stream_capacity_bytes": sample["stream_capacity_bytes"],
                    "actual_stream_bytes": sample["actual_stream_bytes"],
                    "reused_visibility_bytes": sample[
                        "reused_visibility_bytes"
                    ],
                    "producer_scratch_bytes": sample[
                        "producer_scratch_bytes"
                    ],
                },
            }

    summary = {
        "experiment": "001-visibility-reuse",
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
        "D001 correctness passed for "
        f"{args.repeats} repeats x {len(CASES)} cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

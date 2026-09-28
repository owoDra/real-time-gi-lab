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
VARIANTS = (
    "owner-atomic-full",
    "workgroup-full",
    "owner-atomic-depth-reuse",
    "workgroup-depth-reuse",
)


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
        / "phos-lane-d-d004"
    )
    if not executable.exists():
        raise SystemExit(
            f"D004 executable not found: {executable}; run 'mise run build' first"
        )
    if not Path(args.scene).exists():
        raise SystemExit(
            f"D004 scene not found: {args.scene}; run 'mise run assets' first"
        )

    artifact_root = Path(
        os.environ.get(
            "PHOS_RESEARCH_ARTIFACT_DIR",
            (
                "out/research/lane-d-producer-optimization/"
                "004-work-allocation-contention/manual"
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
                    f"D004 correctness gate failed: repeat={repeat + 1} case={case}"
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
                    "git_commit": commit,
                    "repeat": repeat + 1,
                    "case": case,
                    "variant": "baseline-a001",
                    "correct": baseline["correct"],
                    "visible_probe_count": baseline["visible_probe_count"],
                    "active_allocation_groups": baseline[
                        "active_allocation_groups"
                    ],
                    "global_reservation_atomics": baseline[
                        "global_reservation_atomics"
                    ],
                    "shader_shared_scratch_bytes": 0,
                    "work_item_count": baseline["work_item_count"],
                    "overflow_flag": baseline["overflow_flag"],
                    "workload_id": baseline["workload_id"],
                    "producer_emit_us": bt["producer_emit"],
                    "producer_total_us": bt["producer_total"],
                    "incremental_producer_us": bt["producer_total"],
                    "standalone_producer_us": bt["producer_total"],
                    "incremental_end_to_end_us": bt["end_to_end"],
                    "standalone_end_to_end_us": bt["end_to_end"],
                    "persistent_bytes": bm["persistent_bytes"],
                    "transient_bytes": bm["transient_bytes"],
                    "stream_capacity_bytes": bm["stream_capacity_bytes"],
                    "actual_stream_bytes": int(baseline["work_item_count"]) * 64,
                    "reused_visibility_bytes": 0,
                    "producer_scratch_bytes": "",
                }
            )

            for name in VARIANTS:
                variant = metrics["variants"][name]
                vt = variant["timings_us"]
                vm = variant["memory"]
                rows.append(
                    {
                        "git_commit": commit,
                        "repeat": repeat + 1,
                        "case": case,
                        "variant": name,
                        "correct": variant["correct"],
                        "visible_probe_count": variant[
                            "visible_probe_count"
                        ],
                        "active_allocation_groups": variant[
                            "active_allocation_groups"
                        ],
                        "global_reservation_atomics": variant[
                            "global_reservation_atomics"
                        ],
                        "shader_shared_scratch_bytes": variant[
                            "shader_shared_scratch_bytes"
                        ],
                        "work_item_count": variant["work_item_count"],
                        "overflow_flag": variant["overflow_flag"],
                        "workload_id": variant["workload_id"],
                        "producer_emit_us": vt["producer_emit"],
                        "producer_total_us": vt["standalone_producer"],
                        "incremental_producer_us": vt[
                            "incremental_producer"
                        ],
                        "standalone_producer_us": vt[
                            "standalone_producer"
                        ],
                        "incremental_end_to_end_us": vt[
                            "incremental_end_to_end"
                        ],
                        "standalone_end_to_end_us": vt[
                            "standalone_end_to_end"
                        ],
                        "persistent_bytes": vm["persistent_bytes"],
                        "transient_bytes": vm["transient_bytes"],
                        "stream_capacity_bytes": vm[
                            "stream_capacity_bytes"
                        ],
                        "actual_stream_bytes": vm["actual_stream_bytes"],
                        "reused_visibility_bytes": vm[
                            "reused_visibility_bytes"
                        ],
                        "producer_scratch_bytes": vm[
                            "producer_scratch_bytes"
                        ],
                    }
                )

    fieldnames = list(rows[0].keys())
    with (artifact_root / "d004.csv").open(
        "w", newline="", encoding="utf-8"
    ) as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    timing_fields = (
        "producer_emit_us",
        "producer_total_us",
        "incremental_producer_us",
        "standalone_producer_us",
        "incremental_end_to_end_us",
        "standalone_end_to_end_us",
    )

    aggregate: dict[str, dict[str, dict[str, object]]] = {}
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
                    f"missing D004 rows: case={case} variant={variant}"
                )

            sample = selected[0]
            aggregate[case][variant] = {
                "all_correct": all(bool(row["correct"]) for row in selected),
                "repeats": len(selected),
                "visible_probe_count": sample["visible_probe_count"],
                "active_allocation_groups": sample[
                    "active_allocation_groups"
                ],
                "global_reservation_atomics": sample[
                    "global_reservation_atomics"
                ],
                "shader_shared_scratch_bytes": sample[
                    "shader_shared_scratch_bytes"
                ],
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
        "experiment": "004-work-allocation-contention",
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
        "D004 correctness passed for "
        f"{args.repeats} repeats x {len(CASES)} cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

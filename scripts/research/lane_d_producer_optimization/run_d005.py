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
NORMAL_VARIANTS = (
    "baseline-a001",
    "owner-slot-full",
    "owner-slot-bounded",
    "owner-slot-bounded-depth-reuse",
    "fallback-full",
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
        / "phos-lane-d-d005"
    )
    if not executable.exists():
        raise SystemExit(
            f"D005 executable not found: {executable}; run 'mise run build' first"
        )
    if not Path(args.scene).exists():
        raise SystemExit(
            f"D005 scene not found: {args.scene}; run 'mise run assets' first"
        )

    artifact_root = Path(
        os.environ.get(
            "PHOS_RESEARCH_ARTIFACT_DIR",
            (
                "out/research/lane-d-producer-optimization/"
                "005-stream-capacity-overflow/manual"
            ),
        )
    )
    artifact_root.mkdir(parents=True, exist_ok=True)
    commit = git_head()

    rows: list[dict[str, object]] = []
    overflow_rows: list[dict[str, object]] = []
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
            if not (
                metrics.get("normal_correct", False)
                and metrics.get("overflow_safe", False)
                and metrics.get("fallback_correct", False)
            ):
                raise SystemExit(
                    f"D005 correctness/overflow gate failed: "
                    f"repeat={repeat + 1} case={case}"
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
                    "owner_capacity": "",
                    "visible_owner_count": baseline["visible_owner_count"],
                    "overflow_flag": baseline["overflow_flag"],
                    "work_item_count": baseline["work_item_count"],
                    "output_count": baseline["output_count"],
                    "producer_emit_us": bt["producer_emit"],
                    "producer_total_us": bt["producer_total"],
                    "end_to_end_us": bt["end_to_end"],
                    "persistent_bytes": bm["persistent_bytes"],
                    "transient_bytes": bm["transient_bytes"],
                    "resident_bytes": bm["resident_bytes"],
                    "stream_capacity_bytes": bm["stream_capacity_bytes"],
                    "contribution_capacity_bytes": "",
                    "output_capacity": "",
                    "work_capacity": "",
                    "actual_stream_bytes": int(baseline["work_item_count"]) * 64,
                    "reused_visibility_bytes": 0,
                }
            )

            for name in (
                "owner-slot-full",
                "owner-slot-bounded",
                "owner-slot-bounded-depth-reuse",
                "fallback-full",
            ):
                variant = metrics[name]
                vt = variant["timings_us"]
                vm = variant["memory"]
                rows.append(
                    {
                        "git_commit": commit,
                        "repeat": repeat + 1,
                        "case": case,
                        "variant": name,
                        "correct": variant["correct"],
                        "owner_capacity": variant["owner_capacity"],
                        "visible_owner_count": variant["visible_owner_count"],
                        "overflow_flag": variant["overflow_flag"],
                        "work_item_count": variant["work_item_count"],
                        "output_count": variant["output_count"],
                        "producer_emit_us": vt["producer_emit"],
                        "producer_total_us": vt["producer_total"],
                        "end_to_end_us": vt["end_to_end"],
                        "persistent_bytes": vm["persistent_bytes"],
                        "transient_bytes": vm["transient_bytes"],
                        "resident_bytes": vm["resident_bytes"],
                        "stream_capacity_bytes": vm["stream_capacity_bytes"],
                        "contribution_capacity_bytes": vm[
                            "contribution_capacity_bytes"
                        ],
                        "output_capacity": vm["output_capacity"],
                        "work_capacity": vm["work_capacity"],
                        "actual_stream_bytes": vm["actual_stream_bytes"],
                        "reused_visibility_bytes": vm[
                            "reused_visibility_bytes"
                        ],
                    }
                )

            overflow = metrics["forced-overflow"]
            om = overflow["memory"]
            overflow_rows.append(
                {
                    "git_commit": commit,
                    "repeat": repeat + 1,
                    "case": case,
                    "safe": overflow["safe"],
                    "owner_capacity": overflow["owner_capacity"],
                    "attempted_visible_owners": overflow[
                        "attempted_visible_owners"
                    ],
                    "overflow_flag": overflow["overflow_flag"],
                    "clamped_work_items": overflow["clamped_work_items"],
                    "clamped_outputs": overflow["clamped_outputs"],
                    "attempt_end_to_end_us": overflow[
                        "attempt_end_to_end_us"
                    ],
                    "fallback_gpu_retry_total_us": metrics[
                        "fallback_gpu_retry_total_us"
                    ],
                    "resident_bytes": om["resident_bytes"],
                    "stream_capacity_bytes": om["stream_capacity_bytes"],
                }
            )

    with (artifact_root / "d005.csv").open(
        "w", newline="", encoding="utf-8"
    ) as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with (artifact_root / "d005-overflow.csv").open(
        "w", newline="", encoding="utf-8"
    ) as output:
        writer = csv.DictWriter(
            output, fieldnames=list(overflow_rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(overflow_rows)

    aggregate: dict[str, dict[str, dict[str, object]]] = {}
    timing_fields = (
        "producer_emit_us",
        "producer_total_us",
        "end_to_end_us",
    )

    for case in CASES:
        aggregate[case] = {}
        for variant in NORMAL_VARIANTS:
            selected = [
                row
                for row in rows
                if row["case"] == case and row["variant"] == variant
            ]
            if len(selected) != args.repeats:
                raise SystemExit(
                    f"missing D005 rows: case={case} variant={variant}"
                )
            sample = selected[0]
            aggregate[case][variant] = {
                "all_correct": all(bool(row["correct"]) for row in selected),
                "repeats": len(selected),
                "owner_capacity": sample["owner_capacity"],
                "visible_owner_count": sample["visible_owner_count"],
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
                    "resident_bytes": sample["resident_bytes"],
                    "stream_capacity_bytes": sample["stream_capacity_bytes"],
                    "contribution_capacity_bytes": sample[
                        "contribution_capacity_bytes"
                    ],
                    "output_capacity": sample["output_capacity"],
                    "work_capacity": sample["work_capacity"],
                    "actual_stream_bytes": sample["actual_stream_bytes"],
                    "reused_visibility_bytes": sample[
                        "reused_visibility_bytes"
                    ],
                },
            }

        selected_overflow = [
            row for row in overflow_rows if row["case"] == case
        ]
        aggregate[case]["forced-overflow"] = {
            "all_safe": all(bool(row["safe"]) for row in selected_overflow),
            "owner_capacity": selected_overflow[0]["owner_capacity"],
            "attempted_visible_owners": selected_overflow[0][
                "attempted_visible_owners"
            ],
            "overflow_flag_min": min(
                int(row["overflow_flag"]) for row in selected_overflow
            ),
            "clamped_work_items": selected_overflow[0][
                "clamped_work_items"
            ],
            "clamped_outputs": selected_overflow[0]["clamped_outputs"],
            "attempt_end_to_end_us_median": median(
                [
                    float(row["attempt_end_to_end_us"])
                    for row in selected_overflow
                ]
            ),
            "fallback_gpu_retry_total_us_median": median(
                [
                    float(row["fallback_gpu_retry_total_us"])
                    for row in selected_overflow
                ]
            ),
            "resident_bytes": selected_overflow[0]["resident_bytes"],
            "stream_capacity_bytes": selected_overflow[0][
                "stream_capacity_bytes"
            ],
        }

    summary = {
        "experiment": "005-stream-capacity-overflow",
        "git_commit": commit,
        "scene": args.scene,
        "iterations": args.iterations,
        "repeats": args.repeats,
        "validation": args.validation,
        "artifact_root": str(artifact_root.resolve()),
        "fallback_host_allocation_latency_measured": False,
        "aggregate": aggregate,
        "runs": raw_runs,
    }
    (artifact_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        "D005 correctness/overflow passed for "
        f"{args.repeats} repeats x {len(CASES)} cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
